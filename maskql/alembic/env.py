from __future__ import annotations

import os
import sys
from pathlib import Path
from logging.config import fileConfig

from alembic import context
from sqlalchemy import create_engine, pool
from sqlalchemy.engine.url import make_url
from sqlalchemy.schema import MetaData
from sqlmodel import SQLModel

# Make sure project can be imported
REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

# Alembic config
config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Import models so Alembic sees them
# (Side effect only; names are unused.)
from maskql.models import catalog as _catalog
from maskql.models import catalog_schema as _catalog_schema
from maskql.models import user as _user
from maskql.models import rule as _rule

# Import project Base and optional URL
from maskql.db import Base, POSTGRES_URL


def _resolve_sync_url() -> str:
    """
    Get the database URL for a *sync* driver.
    Try common env var names, then alembic.ini, then POSTGRES_URL from maskql.db.
    Normalize to psycopg and validate that a host exists.
    """
    candidates = [
        os.getenv("DATABASE_URL"),
        os.getenv("SQLALCHEMY_DATABASE_URL"),
        os.getenv("POSTGRES_URL"),
        os.getenv("SQLALCHEMY_URL"),
        POSTGRES_URL,  # from maskql.db
        config.get_main_option("sqlalchemy.url"),
    ]
    url = next((u for u in candidates if u), None)

    if not url:
        raise RuntimeError(
            "No database URL found. Set DATABASE_URL (or SQLALCHEMY_DATABASE_URL, "
            "POSTGRES_URL) or define sqlalchemy.url in alembic.ini."
        )

    # Normalize scheme/driver
    if url.startswith("postgres://"):
        # Old style -> explicit SQLAlchemy dialect/driver
        url = url.replace("postgres://", "postgresql+psycopg://", 1)
    if "+asyncpg" in url:
        # Alembic runs sync migrations, so use psycopg (sync)
        url = url.replace("+asyncpg", "+psycopg")

    # Validate URL can be parsed and has a host
    try:
        parsed = make_url(url)
    except Exception as e:
        raise RuntimeError(f"Invalid database URL: {e}") from e

    if not getattr(parsed, "host", None):
        raise RuntimeError(
            "Database URL has no host. Check your env vars and password encoding "
            "(encode special chars like @ : / # ? %)."
        )

    return parsed.render_as_string(hide_password=False)


def _choose_target_metadata():
    """
    Return metadata for autogenerate.
    If SQLModel.metadata and Base.metadata share table names, return only one
    to avoid "Duplicate table keys across multiple MetaData objects".
    Preference: SQLModel.metadata.
    """
    sqlmodel_meta: MetaData = SQLModel.metadata
    base_meta: MetaData | None = getattr(Base, "metadata", None)

    if base_meta is None or base_meta is sqlmodel_meta:
        # Only SQLModel is present (or both are the same)
        return sqlmodel_meta

    sql_tables = set(sqlmodel_meta.tables.keys())
    base_tables = set(base_meta.tables.keys())
    overlap = sql_tables & base_tables

    if overlap:
        return sqlmodel_meta

    # No overlap: it is safe to pass both
    return [sqlmodel_meta, base_meta]


target_metadata = _choose_target_metadata()


def run_migrations_offline():
    """Run migrations in 'offline' mode (no DB connection)."""
    url = _resolve_sync_url()
    config.set_main_option("sqlalchemy.url", url)

    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    """Run migrations in 'online' mode (connect to the DB)."""
    args = context.get_x_argument(as_dictionary=True)
    seed = args.get("seed")

    url = _resolve_sync_url()
    connectable = create_engine(url, poolclass=pool.NullPool, pool_pre_ping=True)

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            compare_server_default=True,
        )

        with context.begin_transaction():
            context.run_migrations()

        if seed == "test":
            from maskql.alembic.seeds import seed_test_data
            seed_test_data(connection)


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
