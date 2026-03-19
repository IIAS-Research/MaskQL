# maskql/services/catalog_service.py
from __future__ import annotations
import asyncio
import logging
import secrets
import string
from typing import Optional, Sequence
from sqlmodel import select
from maskql.db import AsyncSessionLocal
from maskql.models.catalog import Catalog
from maskql.models.catalog_schema import CatalogSchemaEntry
from maskql.schemas.catalog import (
    CatalogConnectionStatusRead,
    CatalogCreate,
    CatalogPatch,
    CatalogSchemaEntryCreate,
    CatalogSchemaEntryRead,
    CatalogSchemaSyncRead,
)
from maskql.utils.trino import trino_sql, trino_ddl
log = logging.getLogger(__name__)

SchemaPath = tuple[str, Optional[str], Optional[str]]


def _sql_literal(value: str) -> str:
    return value.replace("'", "''")


def _sql_identifier(value: str) -> str:
    return '"' + value.replace('"', '""') + '"'


def _schema_path_sort_key(path: SchemaPath) -> tuple[str, str, str]:
    schema_name, table_name, column_name = path
    return (
        schema_name,
        table_name or "",
        column_name or "",
    )


def _should_skip_schema(catalog: Catalog, schema_name: str) -> bool:
    normalized = (schema_name or "").strip()
    if not normalized:
        return True
    lowered = normalized.lower()

    if lowered == "information_schema":
        return True

    if catalog.sgbd == "postgresql":
        if lowered == "pg_catalog":
            return True
        if lowered.startswith("pg_toast") or lowered.startswith("pg_temp_"):
            return True

    if catalog.sgbd == "sqlserver":
        if lowered in {"guest", "sys"}:
            return True
        if lowered.startswith("db_"):
            return True

    return False


def _schema_filter_sql(catalog: Catalog, column_name: str) -> str:
    lowered = f"lower({column_name})"
    clauses = [f"{lowered} <> 'information_schema'"]

    if catalog.sgbd == "postgresql":
        clauses.extend(
            [
                f"{lowered} <> 'pg_catalog'",
                f"{lowered} NOT LIKE 'pg_toast%'",
                f"{lowered} NOT LIKE 'pg_temp_%'",
            ]
        )
    elif catalog.sgbd == "sqlserver":
        clauses.extend(
            [
                f"{lowered} <> 'guest'",
                f"{lowered} <> 'sys'",
                f"{lowered} NOT LIKE 'db_%'",
            ]
        )

    return " AND ".join(clauses)


def _catalog_connection_parts(catalog: Catalog) -> list[str]:
    return [
        f'"connection-url" = \'{_sql_literal(catalog.url)}\'',
        f'"connection-user" = \'{_sql_literal(catalog.username)}\'',
        f'"connection-password" = \'{_sql_literal(catalog.password)}\'',
    ]


def _temp_catalog_name(prefix: str = "healthcheck") -> str:
    suffix = "".join(secrets.choice(string.ascii_lowercase) for _ in range(10))
    return f"{prefix}{suffix}"


class CatalogService:
    @staticmethod
    async def list_all() -> Sequence[Catalog]:
        async with AsyncSessionLocal() as session:
            result = await session.exec(select(Catalog).order_by(Catalog.name))
            return result.all()
        
    @staticmethod
    async def get(catalog_id: int) -> Optional[Catalog]:
        async with AsyncSessionLocal() as session:
            return await session.get(Catalog, catalog_id)
        
    @staticmethod
    async def get_by_name(name: int) -> Optional[Catalog]:
        async with AsyncSessionLocal() as session:
            return (await session.exec(select(Catalog).where(Catalog.name == name))).one_or_none()

    @staticmethod
    async def create(data: CatalogCreate) -> Catalog:
        async with AsyncSessionLocal() as session:
            exists = await session.exec(select(Catalog).where(Catalog.name == data.name))
            if exists.first():
                raise ValueError("Catalog name already exists")
            obj = Catalog(**data.model_dump())
            session.add(obj)
            await session.commit()
            await session.refresh(obj)
            await CatalogService.refresh_in_trino()
            try:
                await CatalogService.sync_schema(obj.id)
            except Exception:
                log.exception("Unable to scan schema for catalog %s after creation", obj.name)
            return obj

    @staticmethod
    async def patch(catalog_id: int, patch: CatalogPatch) -> Catalog | None:
        async with AsyncSessionLocal() as session:
            obj = await session.get(Catalog, catalog_id)
            if not obj:
                return None
            data = patch.model_dump(exclude_unset=True)
            for k, v in data.items():
                setattr(obj, k, v)
            await session.commit()
            await session.refresh(obj)
            await CatalogService.refresh_in_trino()
            try:
                await CatalogService.sync_schema(obj.id)
            except Exception:
                log.exception("Unable to scan schema for catalog %s after update", obj.name)
            return obj

    @staticmethod
    async def delete(catalog_id: int) -> bool:
        async with AsyncSessionLocal() as session:
            obj = await session.get(Catalog, catalog_id)
            if not obj:
                return False
            await session.delete(obj)
            await session.commit()
            await CatalogService.refresh_in_trino()
            return True

    @staticmethod
    async def refresh_in_trino() -> dict:
            
        # Force Trino to scan catalogs, it will crash but that's ok
        # TODO -> It must have something better to do...
        try: 
            await trino_ddl("CREATE CATALOG _noop USING tpch")
            await trino_ddl("DROP CATALOG _noop")
        except:
            pass
        try:     
            # Drop old catalogs
            protected_catalogs = {'jmx', 'memory', 'system', 'tpcds', 'tpch'}
            
            trino_catalogs = {row[0] for row in  (await trino_sql("SHOW CATALOGS"))['rows']}
            for cat in (trino_catalogs - protected_catalogs):
                try:
                    await trino_ddl(f"DROP CATALOG {cat}")
                except Exception:
                    pass
            

            # Create catalogs
            rows = await CatalogService.list_all()
            
            created: list[str] = []
            for c in rows:
                await CatalogService._upsert_catalog_in_trino(c)
                created.append(c.name)
            
            return {"dropped": trino_catalogs, "created": created}
        except:
            return {"dropped": None, "created": None}

    @staticmethod
    async def connection_status(catalog: Catalog, *, timeout: float = 10.0) -> CatalogConnectionStatusRead:
        if catalog.id is None:
            raise ValueError("Catalog ID is required to compute connection status")

        try:
            temp_catalog = await CatalogService._create_temp_catalog(catalog, prefix="healthcheck", timeout=timeout)
            # `SHOW SCHEMAS` is blocked by the current Trino ACL plugin.
            # Querying information_schema still proves the connector can load metadata.
            await trino_sql(
                f"SELECT schema_name FROM {temp_catalog}.information_schema.schemata LIMIT 1",
                timeout=timeout,
            )
            return CatalogConnectionStatusRead(
                catalog_id=catalog.id,
                state="ok",
                message="Connexion valide",
            )
        except Exception as exc:
            detail = str(exc).strip() or "Connexion impossible"
            return CatalogConnectionStatusRead(
                catalog_id=catalog.id,
                state="error",
                message=detail[:300],
            )
        finally:
            try:
                await CatalogService._drop_temp_catalog(temp_catalog, timeout=timeout)
            except UnboundLocalError:
                pass

    @staticmethod
    async def list_connection_statuses() -> list[CatalogConnectionStatusRead]:
        rows = list(await CatalogService.list_all())
        if not rows:
            return []

        semaphore = asyncio.Semaphore(4)

        async def _check(catalog: Catalog) -> CatalogConnectionStatusRead:
            async with semaphore:
                return await CatalogService.connection_status(catalog)

        return await asyncio.gather(*(_check(catalog) for catalog in rows))

    @staticmethod
    async def list_schema_entries(catalog_id: int) -> list[CatalogSchemaEntryRead]:
        async with AsyncSessionLocal() as session:
            rows = await session.exec(
                select(CatalogSchemaEntry)
                .where(CatalogSchemaEntry.catalog_id == catalog_id)
                .order_by(
                    CatalogSchemaEntry.schema_name,
                    CatalogSchemaEntry.table_name,
                    CatalogSchemaEntry.column_name,
                )
            )
            return [CatalogSchemaEntryRead.model_validate(row) for row in rows.all()]

    @staticmethod
    async def create_manual_schema_entry(
        catalog_id: int,
        payload: CatalogSchemaEntryCreate,
    ) -> CatalogSchemaEntryRead:
        schema_name = (payload.schema_name or "").strip()
        table_name = payload.table_name.strip() if payload.table_name else None
        column_name = payload.column_name.strip() if payload.column_name else None

        if not schema_name:
            raise ValueError("Schema name is required")
        if column_name and not table_name:
            raise ValueError("Column name requires table name")

        async with AsyncSessionLocal() as session:
            existing = await session.exec(
                select(CatalogSchemaEntry).where(
                    CatalogSchemaEntry.catalog_id == catalog_id,
                    CatalogSchemaEntry.schema_name == schema_name,
                    CatalogSchemaEntry.table_name == table_name,
                    CatalogSchemaEntry.column_name == column_name,
                )
            )
            if existing.first():
                raise ValueError("Schema path already exists")

            entry = CatalogSchemaEntry(
                catalog_id=catalog_id,
                schema_name=schema_name,
                table_name=table_name,
                column_name=column_name,
                manually_added=True,
                present_in_database=False,
            )
            session.add(entry)
            await session.commit()
            await session.refresh(entry)
            return CatalogSchemaEntryRead.model_validate(entry)

    @staticmethod
    async def delete_manual_schema_entry(catalog_id: int, entry_id: int) -> bool:
        async with AsyncSessionLocal() as session:
            entry = await session.get(CatalogSchemaEntry, entry_id)
            if not entry or entry.catalog_id != catalog_id:
                return False
            if not entry.manually_added:
                raise ValueError("Only manual schema entries can be removed")

            if entry.present_in_database:
                entry.manually_added = False
            else:
                await session.delete(entry)

            await session.commit()
            return True

    @staticmethod
    async def sync_schema(catalog_id: int, *, timeout: float = 30.0) -> CatalogSchemaSyncRead:
        catalog = await CatalogService.get(catalog_id)
        if not catalog:
            raise ValueError("Catalog not found")

        await CatalogService._upsert_catalog_in_trino(catalog, timeout=timeout)
        desired_paths = await CatalogService._scan_schema_paths(catalog, timeout=timeout)
        desired_schemas = {schema_name for schema_name, table_name, column_name in desired_paths if not table_name and not column_name}
        desired_tables = {
            (schema_name, table_name)
            for schema_name, table_name, column_name in desired_paths
            if table_name and not column_name
        }
        desired_columns = {
            (schema_name, table_name, column_name)
            for schema_name, table_name, column_name in desired_paths
            if table_name and column_name
        }

        async with AsyncSessionLocal() as session:
            entry_rows = await session.exec(
                select(CatalogSchemaEntry).where(CatalogSchemaEntry.catalog_id == catalog_id)
            )
            existing_entries = entry_rows.all()
            existing_by_path = {
                (entry.schema_name, entry.table_name, entry.column_name): entry
                for entry in existing_entries
            }

            desired_set = set(desired_paths)
            created_entries = 0
            deleted_entries = 0

            for path, entry in existing_by_path.items():
                if path in desired_set:
                    entry.present_in_database = True
                    continue

                if entry.manually_added:
                    entry.present_in_database = False
                    continue

                await session.delete(entry)
                deleted_entries += 1

            for schema_name, table_name, column_name in sorted(
                desired_set - set(existing_by_path),
                key=_schema_path_sort_key,
            ):
                session.add(
                    CatalogSchemaEntry(
                        catalog_id=catalog_id,
                        schema_name=schema_name,
                        table_name=table_name,
                        column_name=column_name,
                        manually_added=False,
                        present_in_database=True,
                    )
                )
                created_entries += 1

            # Rules can now be managed manually and may legitimately target paths
            # that are absent from the latest schema scan.
            deleted_rules = 0
            await session.commit()

        return CatalogSchemaSyncRead(
            catalog_id=catalog_id,
            schemas=len(desired_schemas),
            tables=len(desired_tables),
            columns=len(desired_columns),
            created_entries=created_entries,
            deleted_entries=deleted_entries,
            deleted_rules=deleted_rules,
        )

    @staticmethod
    async def _scan_schema_paths(catalog: Catalog, *, timeout: float = 30.0) -> set[SchemaPath]:
        try:
            return await CatalogService._scan_schema_paths_via_information_schema(
                catalog,
                timeout=timeout,
            )
        except Exception:
            log.exception(
                "Information schema scan failed for catalog %s, falling back to SHOW queries",
                catalog.name,
            )
            return await CatalogService._scan_schema_paths_via_show(catalog, timeout=timeout)

    @staticmethod
    async def _scan_schema_paths_via_information_schema(
        catalog: Catalog,
        *,
        timeout: float = 30.0,
    ) -> set[SchemaPath]:
        paths: set[SchemaPath] = set()
        catalog_ident = _sql_identifier(catalog.name)
        schema_filter = _schema_filter_sql(catalog, "schema_name")
        relation_filter = _schema_filter_sql(catalog, "table_schema")

        schema_rows = await trino_sql(
            f"SELECT schema_name FROM {catalog_ident}.information_schema.schemata "
            f"WHERE {schema_filter}",
            timeout=timeout,
        )
        for row in schema_rows["rows"]:
            schema_name = row[0]
            if _should_skip_schema(catalog, schema_name):
                continue
            paths.add((schema_name, None, None))

        table_rows = await trino_sql(
            f"SELECT table_schema, table_name FROM {catalog_ident}.information_schema.tables "
            f"WHERE {relation_filter}",
            timeout=timeout,
        )
        for row in table_rows["rows"]:
            schema_name, table_name = row[0], row[1]
            if _should_skip_schema(catalog, schema_name) or not table_name:
                continue

            paths.add((schema_name, None, None))
            paths.add((schema_name, table_name, None))

        column_rows = await trino_sql(
            f"SELECT table_schema, table_name, column_name "
            f"FROM {catalog_ident}.information_schema.columns "
            f"WHERE {relation_filter}",
            timeout=timeout,
        )
        for row in column_rows["rows"]:
            schema_name, table_name, column_name = row[0], row[1], row[2]
            if _should_skip_schema(catalog, schema_name) or not table_name or not column_name:
                continue

            paths.add((schema_name, None, None))
            paths.add((schema_name, table_name, None))
            paths.add((schema_name, table_name, column_name))

        return paths

    @staticmethod
    async def _scan_schema_paths_via_show(
        catalog: Catalog,
        *,
        timeout: float = 30.0,
    ) -> set[SchemaPath]:
        paths: set[SchemaPath] = set()
        catalog_ident = _sql_identifier(catalog.name)

        schema_rows = await trino_sql(
            f"SHOW SCHEMAS FROM {catalog_ident}",
            timeout=timeout,
        )
        for row in schema_rows["rows"]:
            schema_name = row[0]
            if _should_skip_schema(catalog, schema_name):
                continue

            paths.add((schema_name, None, None))
            schema_ident = _sql_identifier(schema_name)
            table_rows = await trino_sql(
                f"SHOW TABLES FROM {catalog_ident}.{schema_ident}",
                timeout=timeout,
            )

            for table_row in table_rows["rows"]:
                table_name = table_row[0]
                if not table_name:
                    continue

                paths.add((schema_name, table_name, None))
                table_ident = _sql_identifier(table_name)
                column_rows = await trino_sql(
                    f"SHOW COLUMNS FROM {catalog_ident}.{schema_ident}.{table_ident}",
                    timeout=timeout,
                )
                for column_row in column_rows["rows"]:
                    column_name = column_row[0]
                    if not column_name:
                        continue
                    paths.add((schema_name, table_name, column_name))

        return paths

    @staticmethod
    async def _create_temp_catalog(
        catalog: Catalog,
        *,
        prefix: str,
        timeout: float,
    ) -> str:
        temp_catalog = _temp_catalog_name(prefix)
        create_sql = (
            f"CREATE CATALOG {temp_catalog} USING {catalog.sgbd} WITH "
            f"(\n  {', '.join(_catalog_connection_parts(catalog))}\n)"
        )
        await trino_ddl(create_sql, timeout=timeout)
        return temp_catalog

    @staticmethod
    async def _drop_temp_catalog(temp_catalog: str, *, timeout: float) -> None:
        await trino_ddl(f"DROP CATALOG {temp_catalog}", timeout=timeout)

    @staticmethod
    async def _upsert_catalog_in_trino(catalog: Catalog, *, timeout: float = 30.0) -> None:
        try:
            await trino_ddl(f"DROP CATALOG {catalog.name}", timeout=timeout)
        except Exception:
            pass

        await trino_ddl(
            f"CREATE CATALOG {catalog.name} USING {catalog.sgbd} WITH "
            f"(\n  {', '.join(_catalog_connection_parts(catalog))}\n)",
            timeout=timeout,
        )
