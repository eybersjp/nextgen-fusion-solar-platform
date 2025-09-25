#!/usr/bin/env python3
"""
Alembic environment configuration for Design Service database migrations.

This module configures Alembic to work with both synchronous and asynchronous
SQLAlchemy engines, supporting PostgreSQL with PostGIS extensions.
"""

import asyncio
import os
from logging.config import fileConfig
from typing import Any

from alembic import context
from sqlalchemy import engine_from_config, pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import AsyncEngine

# Import your models here to ensure they are registered with SQLAlchemy
from app.core.config import settings
from app.core.database import Base
from app.models import *  # noqa: F401,F403

# This is the Alembic Config object
config = context.config

# Interpret the config file for Python logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Add your model's MetaData object here for 'autogenerate' support
target_metadata = Base.metadata


def get_database_url() -> str:
    """Get database URL from settings or environment."""
    # Use sync URL for migrations
    db_url = settings.DATABASE_URL
    
    # Override with environment variable if set
    if "DATABASE_URL" in os.environ:
        db_url = os.environ["DATABASE_URL"]
    
    # Convert async URL to sync if needed
    if db_url.startswith("postgresql+asyncpg://"):
        db_url = db_url.replace("postgresql+asyncpg://", "postgresql://")
    
    return db_url


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.
    
    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well. By skipping the Engine creation
    we don't even need a DBAPI to be available.
    
    Calls to context.execute() here emit the given string to the
    script output.
    """
    url = get_database_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
        include_schemas=True,
    )
    
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    """Run migrations with the given connection."""
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
        compare_server_default=True,
        include_schemas=True,
        # Include custom compare functions for PostGIS types
        render_as_batch=False,
    )
    
    with context.begin_transaction():
        # Enable PostGIS extension if using PostgreSQL
        if connection.dialect.name == "postgresql":
            try:
                connection.execute("CREATE EXTENSION IF NOT EXISTS postgis;")
                connection.execute("CREATE EXTENSION IF NOT EXISTS postgis_topology;")
            except Exception as e:
                print(f"Warning: Could not create PostGIS extensions: {e}")
        
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.
    
    In this scenario we need to create an Engine
    and associate a connection with the context.
    """
    # Override the sqlalchemy.url in the alembic config
    config.set_main_option("sqlalchemy.url", get_database_url())
    
    connectable = engine_from_config(
        config.get_section(config.config_ini_section),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    
    with connectable.connect() as connection:
        do_run_migrations(connection)


async def run_async_migrations() -> None:
    """Run migrations in async mode."""
    from sqlalchemy.ext.asyncio import create_async_engine
    
    # Get async database URL
    db_url = settings.DATABASE_ASYNC_URL or settings.DATABASE_URL
    
    # Override with environment variable if set
    if "DATABASE_URL" in os.environ:
        db_url = os.environ["DATABASE_URL"]
        # Ensure it's async
        if not db_url.startswith("postgresql+asyncpg://"):
            db_url = db_url.replace("postgresql://", "postgresql+asyncpg://")
    
    connectable = create_async_engine(
        db_url,
        poolclass=pool.NullPool,
    )
    
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    
    await connectable.dispose()


def run_migrations_online_async() -> None:
    """Run migrations in async online mode."""
    asyncio.run(run_async_migrations())


# Determine which mode to run in
if context.is_offline_mode():
    run_migrations_offline()
else:
    # Check if we should run in async mode
    db_url = settings.DATABASE_ASYNC_URL or settings.DATABASE_URL
    if db_url.startswith("postgresql+asyncpg://"):
        run_migrations_online_async()
    else:
        run_migrations_online()