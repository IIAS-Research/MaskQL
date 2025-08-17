from __future__ import annotations
from logging.config import fileConfig
from alembic import context
from sqlalchemy import create_engine, pool
import os
import sys
from pathlib import Path
from sqlmodel import SQLModel

target_metadata = SQLModel.metadata

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
from maskql.db import Base, POSTGRES_URL
from maskql.models import catalog as _catalog

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = SQLModel.metadata

def _sync_url_from_env() -> str:
    url = POSTGRES_URL
    if not url:
        # fallback to alembic.ini if defined
        url = config.get_main_option("sqlalchemy.url")
    
    if url and "+asyncpg" in url:
        url = url.replace("+asyncpg", "+psycopg")
    return url

def run_migrations_offline():
    url = _sync_url_from_env()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online():
    url = _sync_url_from_env()
    connectable = create_engine(url, poolclass=pool.NullPool, pool_pre_ping=True)

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
        )
        with context.begin_transaction():
            context.run_migrations()

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
