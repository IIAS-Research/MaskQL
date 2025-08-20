from typing import Optional
from sqlmodel import SQLModel

class UserCreate(SQLModel):
    username: str
    password: str

class UserPatch(SQLModel):
    username: Optional[str] = None
    password: Optional[str] = None

class UserRead(SQLModel):
    id: int
    username: str
