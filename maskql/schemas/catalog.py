from __future__ import annotations
from typing import Any, Optional
from pydantic import field_validator
from sqlmodel import SQLModel

class CatalogCreate(SQLModel):
    name: str
    url: str
    sgbd: str
    username: str
    password: str

class CatalogPatch(SQLModel):
    name: Optional[str] = None
    url: Optional[str] = None
    sgbd: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None

class CatalogRead(SQLModel):
    id: int
    name: str
    url: str
    sgbd: str
    username: str


class CatalogConnectionStatusRead(SQLModel):
    catalog_id: int
    state: str
    message: str


class CatalogSchemaEntryRead(SQLModel):
    id: int
    catalog_id: int
    schema_name: str
    table_name: Optional[str] = None
    column_name: Optional[str] = None
    manually_added: bool
    present_in_database: bool


class CatalogSchemaEntryCreate(SQLModel):
    schema_name: str
    table_name: Optional[str] = None
    column_name: Optional[str] = None

    @field_validator("schema_name", "table_name", "column_name", mode="before")
    @classmethod
    def empty_str_to_none(cls, value):
        if isinstance(value, str):
            value = value.strip()
            return value or None
        return value


class CatalogSchemaSyncRead(SQLModel):
    catalog_id: int
    schemas: int
    tables: int
    columns: int
    created_entries: int
    deleted_entries: int
    deleted_rules: int


class CatalogTablePreviewRequest(SQLModel):
    user_id: int
    schema_name: str
    table_name: str
    limit: int = 5

    @field_validator("schema_name", "table_name", mode="before")
    @classmethod
    def strip_required_names(cls, value):
        if isinstance(value, str):
            return value.strip()
        return value

    @field_validator("limit")
    @classmethod
    def clamp_limit(cls, value: int) -> int:
        return max(1, min(int(value), 50))


class CatalogPreviewDatasetRead(SQLModel):
    columns: list[str]
    rows: list[dict[str, Any]]
    error: Optional[str] = None


class CatalogTablePreviewRead(SQLModel):
    catalog_id: int
    schema_name: str
    table_name: str
    limit: int
    before_maskql: CatalogPreviewDatasetRead
    after_maskql: CatalogPreviewDatasetRead
