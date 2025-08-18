from __future__ import annotations
from typing import Optional, List
from sqlmodel import SQLModel, Field, Relationship
from sqlalchemy import UniqueConstraint, Column, String
from sqlalchemy.orm import relationship as sa_relationship

class Catalog(SQLModel, table=True):
    __tablename__ = "catalogs"
    __table_args__ = (UniqueConstraint("name", name="uq_catalog_name"),)

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    url: str
    sgbd: str  # ex: postgresql, mysql…
    username: str
    # Password not hashed, must be used to connect to databases.
    # TODO Encrypt it
    password: str = Field(sa_column=Column(String, nullable=False), repr=False)
    rules: list["Rule"] = Relationship(
        sa_relationship=sa_relationship(
            "Rule",
            back_populates="catalog",
            cascade="all, delete-orphan",
            lazy="selectin",
        )
    )

