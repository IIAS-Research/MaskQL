from __future__ import annotations
from typing import Optional, TYPE_CHECKING
from sqlmodel import SQLModel, Field, Relationship
from sqlalchemy.orm import relationship as sa_relationship

if TYPE_CHECKING:
    from .catalog import Catalog
    from .user import User

class Rule(SQLModel, table=True):
    __tablename__ = "rules"
    id: Optional[int] = Field(default=None, primary_key=True)
    path: Optional[str]
    allow: bool
    effect: Optional[str]
    catalog_id: int = Field(foreign_key="catalogs.id", index=True)
    catalog: "Catalog" = Relationship(
        sa_relationship=sa_relationship(
            "Catalog",
            back_populates="rules",
            lazy="joined",
        )
    )
    user_id: int = Field(foreign_key="users.id", index=True)
    user: "User" = Relationship(
        sa_relationship=sa_relationship(
            "User",
            back_populates="rules",
            lazy="joined",
        )
    )
