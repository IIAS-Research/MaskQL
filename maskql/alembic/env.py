from __future__ import annotations
from logging.config import fileConfig
from alembic import context
from sqlalchemy import create_engine, pool
import os
import sys
from pathlib import Path
from sqlmodel import SQLModel

# --- Resolve PYTHONPATH to import models
REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

# --- Config Alembic
config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# --- import models
from maskql.models import catalog as _catalog
from maskql.models import user as _user


from maskql.db import Base, POSTGRES_URL


target_metadata = [SQLModel.metadata, getattr(Base, "metadata", None)]
target_metadata = [m for m in target_metadata if m is not None]

def _sync_url_from_env() -> str:
    url = POSTGRES_URL
    if not url:
        url = config.get_main_option("sqlalchemy.url")

    if url and "+asyncpg" in url:
        url = url.replace("+asyncpg", "+psycopg")
    return url

def run_migrations_offline():
    url = _sync_url_from_env()
    if url:
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
    args = context.get_x_argument(as_dictionary=True)
    seed = args.get("seed")

    url = _sync_url_from_env()
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
