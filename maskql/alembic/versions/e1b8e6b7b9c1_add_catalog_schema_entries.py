"""add catalog schema entries

Revision ID: e1b8e6b7b9c1
Revises: d51ba73b550a
Create Date: 2026-03-19 13:05:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "e1b8e6b7b9c1"
down_revision: Union[str, Sequence[str], None] = "d51ba73b550a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "catalog_schema_entries",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("schema_name", sa.String(), nullable=False),
        sa.Column("table_name", sa.String(), nullable=True),
        sa.Column("column_name", sa.String(), nullable=True),
        sa.Column("catalog_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["catalog_id"], ["catalogs.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "catalog_id",
            "schema_name",
            "table_name",
            "column_name",
            name="uq_catalog_schema_entries_path",
        ),
    )
    op.create_index(
        op.f("ix_catalog_schema_entries_catalog_id"),
        "catalog_schema_entries",
        ["catalog_id"],
        unique=False,
    )
    op.create_check_constraint(
        "ck_catalog_schema_column_requires_table",
        "catalog_schema_entries",
        "column_name IS NULL OR table_name IS NOT NULL",
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_catalog_schema_column_requires_table",
        "catalog_schema_entries",
        type_="check",
    )
    op.drop_index(op.f("ix_catalog_schema_entries_catalog_id"), table_name="catalog_schema_entries")
    op.drop_table("catalog_schema_entries")
