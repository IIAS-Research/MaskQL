from typing import Optional
from sqlmodel import SQLModel

class RuleCreate(SQLModel):
    schema: Optional[str] = None
    table_name: Optional[str] = None
    column_name: Optional[str] = None
    allow: bool
    effect: Optional[str] = None
    catalog_id: int
    user_id: int

class RulePatch(SQLModel):
    schema: Optional[str] = None
    table_name: Optional[str] = None
    column_name: Optional[str] = None
    allow: Optional[bool] = None
    effect: Optional[str] = None
    catalog_id: Optional[int] = None
    user_id: Optional[int] = None

class RuleRead(SQLModel):
    id: int
    schema: Optional[str] = None
    table_name: Optional[str] = None
    column_name: Optional[str] = None
    allow: bool
    effect: Optional[str] = None
    catalog_id: int
    user_id: int
