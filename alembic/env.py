"""Alembic environment configuration for async PostgreSQL."""
import asyncio
from logging.config import fileConfig
import sys
from pathlib import Path

from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context

# Add project root to Python path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Import app configuration and models
from app.core.config import settings
from app.db.base import Base

# Import all models to ensure they're registered with SQLAlchemy
from app.models.user import User
from app.models.task import Task
from app.models.payment import PaymentOrder
from app.models.credit import CreditTransaction

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Override sqlalchemy.url with the one from settings
# Use synchronous URL for Alembic (replace asyncpg with psycopg2)
sync_url = settings.DATABASE_URL_MASTER.replace("postgresql+asyncpg://", "postgresql://")
# Don't set in config to avoid ConfigParser % escaping issues
# We'll use sync_url directly in run_migrations_online()

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    # Use our sync_url instead of config
    context.configure(
        url=sync_url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    """Execute migrations."""
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
        compare_server_default=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    from sqlalchemy import engine_from_config

    # Use synchronous engine for Alembic migrations
    connectable = engine_from_config(
        {
            "sqlalchemy.url": sync_url,
            "sqlalchemy.pool_pre_ping": True,
            "sqlalchemy.echo": False,
        },
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        do_run_migrations(connection)

    connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
