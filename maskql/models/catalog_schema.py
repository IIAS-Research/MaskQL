from __future__ import annotations

from typing import Optional

from pydantic import ConfigDict, field_validator
from sqlalchemy import CheckConstraint, UniqueConstraint
from sqlalchemy.orm import relationship as sa_relationship
from sqlmodel import Field, Relationship, SQLModel


class CatalogSchemaEntry(SQLModel, table=True):
    __tablename__ = "catalog_schema_entries"
    __table_args__ = (
        UniqueConstraint(
            "catalog_id",
            "schema_name",
            "table_name",
            "column_name",
            name="uq_catalog_schema_entries_path",
        ),
        CheckConstraint(
            "column_name IS NULL OR table_name IS NOT NULL",
            name="ck_catalog_schema_column_requires_table",
        ),
    )

    model_config = ConfigDict(validate_assignment=True)

    id: Optional[int] = Field(default=None, primary_key=True)
    schema_name: str
    table_name: Optional[str] = Field(default=None, nullable=True)
    column_name: Optional[str] = Field(default=None, nullable=True)

    catalog_id: int = Field(foreign_key="catalogs.id", index=True)
    catalog: "Catalog" = Relationship(
        sa_relationship=sa_relationship(
            "Catalog",
            back_populates="schema_entries",
            lazy="joined",
        )
    )

    @field_validator("schema_name", "table_name", "column_name", mode="before")
    @classmethod
    def empty_str_to_none(cls, value):
        if isinstance(value, str):
            value = value.strip()
            return value or None
        return value
