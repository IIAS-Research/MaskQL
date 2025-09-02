from __future__ import annotations
from typing import Optional
from sqlmodel import SQLModel, Field, Relationship
from sqlalchemy.orm import relationship as sa_relationship
from pydantic import field_validator, ConfigDict

class Rule(SQLModel, table=True):
    __tablename__ = "rules"

    model_config = ConfigDict(validate_assignment=True)

    id: Optional[int] = Field(default=None, primary_key=True)
    schema_name: Optional[str] = Field(default=None, nullable=True)
    table_name: Optional[str] = Field(default=None, nullable=True)
    column_name: Optional[str] = Field(default=None, nullable=True)
    allow: bool
    effect: Optional[str] = Field(default=None, nullable=True)

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

    @field_validator("schema_name", "table_name", "column_name", "effect", mode="before")
    @classmethod
    def empty_str_to_none(cls, v):
        if isinstance(v, str) and v.strip() == "":
            return None
        return v
