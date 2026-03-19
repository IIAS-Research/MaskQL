from __future__ import annotations
from typing import Optional
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
