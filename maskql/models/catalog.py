from __future__ import annotations
import os
from typing import Optional
from sqlmodel import SQLModel, Field, select
from sqlalchemy import UniqueConstraint
from maskql.db import AsyncSessionLocal
from maskql.utils.trino import trino_sql, trino_ddl
import re

class CatalogBase(SQLModel):
    name: str
    url: str
    sgbd: str
    user: str
    password: str
    
class Catalog(SQLModel, table=True):
    __tablename__ = "catalog"
    __table_args__ = (UniqueConstraint("name", name="uq_catalog_name"),)

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    url: str
    sgbd: str  # ex: postgresql, mysql…
    user: str
    password: str

    @classmethod
    async def refresh_in_trino(cls) -> dict:
        # Get all catalogs
        async with AsyncSessionLocal() as session:
            rows = (await session.execute(select(cls).order_by(cls.name))).scalars().all()
        desired_names = {c.name for c in rows}

        # Drop old catalogs
        
        res = await trino_sql("SHOW CATALOGS")
        existing = {r[0] for r in (res.get("data") or []) if r}
        protected = {
            s.strip() for s in os.getenv("TRINO_PROTECTED_CATALOGS", "system,jmx,tpch,tpcds").split(",") if s.strip()
        }
        to_drop = sorted((existing & desired_names) - protected)
        for cat in to_drop:
            try:
                await trino_ddl(f'DROP CATALOG {cat}')
            except Exception:
                pass

        # Create new catalogs verisons
        created = []
        for c in rows:
            connector = c.sgbd
            parts = [
                f'"connection-url" = \'{c.url}\'',
                f'"connection-user" = \'{c.user}\'',
                f'"connection-password" = \'{c.password}\''
            ]
            sql = f'CREATE CATALOG {c.name} USING {connector} WITH (\n  {", ".join(parts)}\n)'
            await trino_ddl(sql)
            created.append(c.name)

        return {"dropped": to_drop, "created": created}

# Input (POST/PUT)
class CatalogCreate(CatalogBase):
    pass

# Partial input (PATCH)
class CatalogPatch(SQLModel):
    name: Optional[str] = None
    url: Optional[str] = None
    sgbd: Optional[str] = None
    user: Optional[str] = None
    password: Optional[str] = None
