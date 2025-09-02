# maskql/services/catalog_service.py
from __future__ import annotations
import os
from typing import Sequence, Optional
from sqlmodel import select
from maskql.db import AsyncSessionLocal
from maskql.models.catalog import Catalog
from maskql.schemas.catalog import CatalogCreate, CatalogPatch
from maskql.utils.trino import trino_sql, trino_ddl

import time
import logging
log = logging.getLogger(__name__)

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
                connector = c.sgbd
                parts = [
                    f'"connection-url" = \'{c.url}\'',
                    f'"connection-user" = \'{c.username}\'',
                    f'"connection-password" = \'{c.password}\'',
                ]
                sql = f"CREATE CATALOG {c.name} USING {connector} WITH (\n  {', '.join(parts)}\n)"
                await trino_ddl(sql)
                
                created.append(c.name)
            
            return {"dropped": trino_catalogs, "created": created}
        except:
            return {"dropped": None, "created": None}
