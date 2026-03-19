"""add manual flags to catalog schema entries

Revision ID: 7c0d6f4f2f1a
Revises: e1b8e6b7b9c1
Create Date: 2026-03-19 18:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "7c0d6f4f2f1a"
down_revision: Union[str, Sequence[str], None] = "e1b8e6b7b9c1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "catalog_schema_entries",
        sa.Column(
            "manually_added",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )
    op.add_column(
        "catalog_schema_entries",
        sa.Column(
            "present_in_database",
            sa.Boolean(),
            nullable=False,
            server_default=sa.true(),
        ),
    )
    op.alter_column("catalog_schema_entries", "manually_added", server_default=None)
    op.alter_column("catalog_schema_entries", "present_in_database", server_default=None)


def downgrade() -> None:
    op.drop_column("catalog_schema_entries", "present_in_database")
    op.drop_column("catalog_schema_entries", "manually_added")
