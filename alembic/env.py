"""
Alembic environment configuration.

Supports both offline (SQL generation) and online (direct DB) migration modes.
Uses the synchronous psycopg2 driver for compatibility with Alembic's run_migrations_online.

Import all models via app.models so autogenerate detects schema changes.
"""
import sys
from pathlib import Path

# Ensure the project root (/app in Docker) is on sys.path so that
# `import app.*` works regardless of how Alembic loads this file.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.ext.asyncio import create_async_engine

from app.core.config import settings
from app.core.database import Base

# Import all models to populate Base.metadata
import app.models  # noqa: F401

# Alembic Config object (gives access to alembic.ini values)
config = context.config

# Setup Python logging from alembic.ini if present
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# The metadata object that autogenerate inspects
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """
    Offline mode: emit SQL to stdout/file without connecting to DB.
    Useful for generating migration scripts for review.
    """
    url = settings.DATABASE_URL
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


def do_run_migrations(connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
        compare_server_default=True,
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    """
    Online mode: connect to DB and run migrations directly.
    Uses async engine to stay consistent with the rest of the app.
    """
    connectable = create_async_engine(settings.DATABASE_URL, poolclass=pool.NullPool)

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
