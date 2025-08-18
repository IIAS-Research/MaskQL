from typing import Optional
from sqlmodel import SQLModel, Field
from sqlalchemy import UniqueConstraint, Column, String
from maskql.security.password import hash_password, verify_password

class User(SQLModel, table=True):
    __tablename__ = "users"
    __table_args__ = (UniqueConstraint("username", name="uq_catalog_name"),)

    id: Optional[int] = Field(default=None, primary_key=True)
    username: str
    password: str = Field(sa_column=Column(String(256), nullable=False))

    @classmethod
    def create(cls, *, username: str, password: str) -> "User":
        return cls(username=username, password=hash_password(password))

    def set_password(self, password: str) -> None:
        self.password = hash_password(password)

    def check_password(self, password: str) -> bool:
        return verify_password(password, self.password)
