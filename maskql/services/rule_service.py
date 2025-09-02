# maskql/services/rule_service.py
from __future__ import annotations
from typing import Sequence, Optional
from sqlmodel import select
from maskql.db import AsyncSessionLocal
from maskql.models.rule import Rule
from maskql.models.catalog import Catalog
from maskql.services.catalog_service import CatalogService
from maskql.models.user import User
from maskql.schemas.rule import RuleCreate, RulePatch

import logging
logger = logging.getLogger(__name__)

class RuleService:
    @staticmethod
    async def list_all() -> Sequence[Rule]:
        async with AsyncSessionLocal() as session:
            result = await session.exec(
                select(Rule)
            )
            return result.all()
        
    @staticmethod
    async def list_filtered(
        *,
        user_id: Optional[int] = None,
        catalog_id: Optional[int] = None,
        schema_name: Optional[str] = None,
        table_name: Optional[str] = None,
        column_name: Optional[str] = None,
        allow: Optional[bool] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
    ) -> Sequence[Rule]:
        async with AsyncSessionLocal() as session:
            stmt = select(Rule)
            conditions = []
            if user_id is not None:
                conditions.append(Rule.user_id == user_id)
            if catalog_id is not None:
                conditions.append(Rule.catalog_id == catalog_id)
            if schema_name is not None:
                conditions.append(Rule.schema_name == schema_name)
            if table_name is not None:
                conditions.append(Rule.table_name == table_name)
            if column_name is not None:
                conditions.append(Rule.column_name == column_name)
            if allow is not None:
                conditions.append(Rule.allow == allow)

            if conditions:
                stmt = stmt.where(*conditions)
            if offset is not None:
                stmt = stmt.offset(offset)
            if limit is not None:
                stmt = stmt.limit(limit)

            result = await session.exec(stmt)
            return result.all()

    @staticmethod
    async def list_by_catalog(catalog_id: int) -> Sequence[Rule]:
        async with AsyncSessionLocal() as session:
            result = await session.exec(
                select(Rule)
                .where(Rule.catalog_id == catalog_id)
            )
            return result.all()

    @staticmethod
    async def list_by_user(user_id: int) -> Sequence[Rule]:
        async with AsyncSessionLocal() as session:
            result = await session.exec(
                select(Rule)
                .where(Rule.user_id == user_id)
            )
            return result.all()

    @staticmethod
    async def get(rule_id: int) -> Optional[Rule]:
        async with AsyncSessionLocal() as session:
            return await session.get(Rule, rule_id)

    @staticmethod
    async def create(data: RuleCreate) -> Rule:
        async with AsyncSessionLocal() as session:
            # FK existence checks
            if not data.catalog_id:
                if data.catalog:
                    data.catalog_id = (await CatalogService.get_by_name(data.catalog)).id
                    del data.catalog
                else:
                    raise ValueError("One of catalog_id and catalog is required")
                
            if data.catalog_id is None or (await session.get(Catalog, data.catalog_id) is None):
                raise ValueError("Catalog not found")
            
            if await session.get(User, data.user_id) is None:
                raise ValueError("User not found")

            exists = await session.exec(
                select(Rule).where(
                    Rule.catalog_id == data.catalog_id,
                    Rule.column_name == data.column_name,
                    Rule.table_name == data.table_name,
                    Rule.schema_name == data.schema_name,
                    Rule.user_id == data.user_id,
                )
            )
            if exists.first():
                raise ValueError("A rule with this path already exists in this catalog")
            
            obj = Rule(**data.model_dump(exclude={"catalog"}))
            session.add(obj)
            await session.commit()
            await session.refresh(obj)
            return obj

    @staticmethod
    async def patch(rule_id: int, patch: RulePatch) -> Optional[Rule]:
        async with AsyncSessionLocal() as session:
            obj = await session.get(Rule, rule_id)
            if not obj:
                return None

            payload = patch.model_dump(exclude_unset=True)

            # If catalog_id/user_id are changing, validate they exist
            new_catalog_id = payload.get("catalog_id", obj.catalog_id)
            new_user_id = payload.get("user_id", obj.user_id)
            new_table = payload.get("table_name", obj.table_name)
            new_column = payload.get("column_name", obj.column_name)
            new_schema = payload.get("schema", obj.schema_name)

            if "catalog_id" in payload and await session.get(Catalog, new_catalog_id) is None:
                raise ValueError("Catalog not found")
            if "user_id" in payload and await session.get(User, new_user_id) is None:
                raise ValueError("User not found")

            # Duplicate guard after potential changes
            dup = await session.exec(
                select(Rule).where(
                    Rule.id != obj.id,
                    Rule.catalog_id == new_catalog_id,
                    Rule.table_name == new_table,
                    Rule.column_name == new_column,
                    Rule.schema_name == new_schema,
                )
            )
            if dup.first():
                raise ValueError("A rule with this path already exists in this catalog")

            for k, v in payload.items():
                setattr(obj, k, v)

            await session.commit()
            await session.refresh(obj)
            return obj

    @staticmethod
    async def delete(rule_id: int) -> bool:
        async with AsyncSessionLocal() as session:
            obj = await session.get(Rule, rule_id)
            if not obj:
                return False
            await session.delete(obj)
            await session.commit()
            return True
