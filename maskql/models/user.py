from typing import Optional, List, Sequence
from sqlalchemy import UniqueConstraint, Column, String, bindparam
from sqlmodel import SQLModel, Field, Relationship
from sqlalchemy.orm import relationship as sa_relationship
from maskql.security.password import hash_password, verify_password
from maskql.db import AsyncSessionLocal
from sqlmodel import select


from maskql.models import Rule, Catalog

class User(SQLModel, table=True):
    __tablename__ = "users"
    __table_args__ = (UniqueConstraint("username", name="uq_catalog_name"),)

    id: Optional[int] = Field(default=None, primary_key=True)
    username: str
    password: str = Field(sa_column=Column(String(256), nullable=False))
    rules: list["Rule"] = Relationship(
        sa_relationship=sa_relationship(
            "Rule",
            back_populates="user",
            cascade="all, delete-orphan",
            lazy="selectin",
        )
    )

    
    @classmethod
    def create(cls, *, username: str, password: str) -> "User":
        return cls(username=username, password=hash_password(password))

    def set_password(self, password: str) -> None:
        self.password = hash_password(password)

    def check_password(self, password: str) -> bool:
        return verify_password(password, self.password)
    
    async def is_allowed(self, values:list[str], path:tuple=None, strict=False):
        """
            Does databases parts are allowed ? 

        Args:
            values (list[str]): Names of columns|tables|schemas|catalogs we want to check
            path (tuple, optional):. Defaults to None for catalog. If you are looking for columns|tables|schemas,
                must by a tuple of the path to reach it. 
            strict (bool, optional): Defaults to False. If True, children will will not impact result
        """
        # path is something like (catalog, schema, table)
        # or (catalog)
        # or even None for catalogs
        if not path:
            path = []
            
        columns = [Catalog.name, Rule.schema_name, Rule.table_name, Rule.column_name]
        looking_for_column = columns[len(path)]
        is_column_scope = looking_for_column is Rule.column_name
        
        if looking_for_column is Catalog.name:
            to_select = select(Catalog.name).select_from(Catalog).join(Rule, Rule.catalog_id == Catalog.id)
        else:
            to_select = select(looking_for_column).select_from(Rule).join(Catalog, Rule.catalog_id == Catalog.id)
            
        # Clause to focus on subject
        def where_clause(strict):
            clauses = []
            full_path = list(path) + [values]
            for i, column in enumerate(columns):
                if len(full_path) <= i:
                    if strict:
                        clauses.append(column.is_(None))
                    else:
                        break
                elif full_path[i] == None:
                    pass # Do nothing if no data in path (sbgd without schema for example)
                elif isinstance(full_path[i], list):
                    clauses.append(column.in_(full_path[i]))
                else:
                    clauses.append(column == full_path[i])
                    
            return clauses
        
        direct_disable = []
        if not is_column_scope:
            # Direct denies only block inheritance from a parent scope.
            # A more specific explicit allow must still be able to carve out
            # an exception inside a denied catalog/schema/table.
            async with AsyncSessionLocal() as s:
                direct_disable = (await s.exec(
                    to_select.where(
                        Rule.allow.is_(False),
                        Rule.user == self,
                        *where_clause(True)
                    ).distinct())).all()
        
        # If not, allowed directly or by children ?
        async with AsyncSessionLocal() as s:
            enabled = (await s.exec(
                to_select.where(
                    Rule.allow.is_(True),
                    Rule.user == self,
                    *where_clause(strict)
                ).distinct())).all()
            
        requested_values = list(dict.fromkeys(values))
        enabled_set = set(enabled)
        direct_disable_set = set(direct_disable)
        remaining_values = [
            value for value in requested_values if value not in enabled_set
        ]
        inheritable_values = [
            value for value in remaining_values if value not in direct_disable_set
        ]
        
        # If not, allowed by parent ?
        if path and inheritable_values:
            parent_value = path[-1]
            parent_path = path[0:-1]
            parent_strict = not is_column_scope
            
            if parent_value in (
                await self.is_allowed(
                    [parent_value],
                    path=parent_path,
                    strict=parent_strict,
                )
            ):
                enabled_set.update(inheritable_values)
        
        return [value for value in requested_values if value in enabled_set]
        
    async def row_filter(self, catalog, table, schema:str=None):
        schema_where = (Rule.schema_name == schema) if schema else True
        
        async with AsyncSessionLocal() as s:
            return (await s.exec(
                select(Rule.effect).select_from(Rule).join(Catalog, Rule.catalog_id == Catalog.id)
                .where(
                    Rule.user == self,
                    Catalog.name == catalog,
                    Rule.table_name == table,
                    Rule.column_name.is_(None),
                    schema_where
                ))).one_or_none()
    
    async def mask(self, catalog, table, column, schema:str=None):
        def scope_where(scope_schema, scope_table, scope_column):
            clauses = [Rule.user == self, Catalog.name == catalog]

            if scope_schema is None:
                clauses.append(Rule.schema_name.is_(None))
            else:
                clauses.append(Rule.schema_name == scope_schema)

            if scope_table is None:
                clauses.append(Rule.table_name.is_(None))
            else:
                clauses.append(Rule.table_name == scope_table)

            if scope_column is None:
                clauses.append(Rule.column_name.is_(None))
            else:
                clauses.append(Rule.column_name == scope_column)

            return clauses

        async with AsyncSessionLocal() as s:
            column_rule = (await s.exec(
                select(Rule.allow, Rule.effect)
                .select_from(Rule)
                .join(Catalog, Rule.catalog_id == Catalog.id)
                .where(*scope_where(schema, table, column))
            )).one_or_none()

            if column_rule is not None:
                allow, effect = column_rule
                if allow is False:
                    return "NULL"
                return effect

            for scope_schema, scope_table in (
                (schema, table),
                (schema, None),
                (None, None),
            ):
                inherited_rule = (await s.exec(
                    select(Rule.allow)
                    .select_from(Rule)
                    .join(Catalog, Rule.catalog_id == Catalog.id)
                    .where(*scope_where(scope_schema, scope_table, None))
                )).one_or_none()

                if inherited_rule is None:
                    continue

                if inherited_rule is False:
                    return "NULL"

                return None

        return None
