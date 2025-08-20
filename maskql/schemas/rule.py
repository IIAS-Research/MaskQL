from typing import Optional
from sqlmodel import SQLModel

class RuleCreate(SQLModel):
    schema_name: Optional[str] = None
    table_name: Optional[str] = None
    column_name: Optional[str] = None
    allow: bool
    effect: Optional[str] = None
    catalog_id: Optional[int] = None
    catalog: Optional[str] = None # Rule can be created with catalog name
    user_id: int

class RulePatch(SQLModel):
    schema_name: Optional[str] = None
    table_name: Optional[str] = None
    column_name: Optional[str] = None
    allow: Optional[bool] = None
    effect: Optional[str] = None
    catalog_id: Optional[int] = None
    user_id: Optional[int] = None

class RuleRead(SQLModel):
    id: int
    schema_name: Optional[str] = None
    table_name: Optional[str] = None
    column_name: Optional[str] = None
    allow: bool
    effect: Optional[str] = None
    catalog_id: int
    user_id: int
