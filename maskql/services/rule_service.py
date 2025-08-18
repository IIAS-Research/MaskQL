# maskql/services/rule_service.py
from __future__ import annotations
from typing import Sequence, Optional
from sqlmodel import select
from maskql.db import AsyncSessionLocal
from maskql.models.rule import Rule
from maskql.models.catalog import Catalog
from maskql.models.user import User
from maskql.schemas.rule import RuleCreate, RulePatch


class RuleService:
    @staticmethod
    async def list_all() -> Sequence[Rule]:
        async with AsyncSessionLocal() as session:
            result = await session.exec(
                select(Rule).order_by(Rule.catalog_id, Rule.path)
            )
            return result.all()

    @staticmethod
    async def list_by_catalog(catalog_id: int) -> Sequence[Rule]:
        async with AsyncSessionLocal() as session:
            result = await session.exec(
                select(Rule)
                .where(Rule.catalog_id == catalog_id)
                .order_by(Rule.path)
            )
            return result.all()

    @staticmethod
    async def list_by_user(user_id: int) -> Sequence[Rule]:
        async with AsyncSessionLocal() as session:
            result = await session.exec(
                select(Rule)
                .where(Rule.user_id == user_id)
                .order_by(Rule.catalog_id, Rule.path)
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
            if await session.get(Catalog, data.catalog_id) is None:
                raise ValueError("Catalog not found")
            if await session.get(User, data.user_id) is None:
                raise ValueError("User not found")

            exists = await session.exec(
                select(Rule).where(
                    Rule.catalog_id == data.catalog_id,
                    Rule.path == data.path,
                )
            )
            if exists.first():
                raise ValueError("A rule with this path already exists in this catalog")

            obj = Rule(**data.model_dump())
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
            new_path = payload.get("path", obj.path)

            if "catalog_id" in payload and await session.get(Catalog, new_catalog_id) is None:
                raise ValueError("Catalog not found")
            if "user_id" in payload and await session.get(User, new_user_id) is None:
                raise ValueError("User not found")

            # Duplicate guard after potential changes
            dup = await session.exec(
                select(Rule).where(
                    Rule.id != obj.id,
                    Rule.catalog_id == new_catalog_id,
                    Rule.path == new_path,
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
