import asyncio
import concurrent.futures
from logging.config import fileConfig
import sys
import os
from sqlalchemy import pool, engine_from_config
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config
from alembic import context

# Ensure vector-kb-mcp directory is on sys.path
sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
)

from core.config import settings  # noqa: E402
from models.base import Base  # noqa: E402
# Import all models to ensure metadata registration
from models import (  # noqa: E402, F401
    KnowledgeBase,
    Document,
    DocumentChunk,
    ProcessingTask,
)

target_metadata = Base.metadata


def include_object(object, name, type_, reflected, compare_to):
    """Ensure vector-kb alembic only touches vkb_ tables."""
    if type_ == "table":
        return name.startswith("vkb_")
    return True


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    config = context.config
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        version_table="alembic_version_vkb",
        include_object=include_object,
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        version_table="alembic_version_vkb",
        include_object=include_object,
    )

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Run migrations in 'online' async mode."""
    config = context.config
    configuration = config.get_section(config.config_ini_section) or {}
    configuration["sqlalchemy.url"] = config.get_main_option("sqlalchemy.url")

    connectable = async_engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode (handling async & sync engines)."""
    config = context.config
    current_url = config.get_main_option("sqlalchemy.url")
    is_async = "+asyncpg" in current_url or "+aiosqlite" in current_url

    if is_async:
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop and loop.is_running():
            # If called within an event loop, run in dedicated thread
            with concurrent.futures.ThreadPoolExecutor(
                max_workers=1
            ) as executor:
                executor.submit(asyncio.run, run_async_migrations()).result()
        else:
            asyncio.run(run_async_migrations())
    else:
        configuration = config.get_section(config.config_ini_section) or {}
        configuration["sqlalchemy.url"] = current_url
        connectable = engine_from_config(
            configuration,
            prefix="sqlalchemy.",
            poolclass=pool.NullPool,
        )

        with connectable.connect() as connection:
            do_run_migrations(connection)

        connectable.dispose()


# Only execute migration runner if running inside Alembic context
if hasattr(context, "config") and context.config is not None:
    config = context.config
    if config.config_file_name is not None:
        fileConfig(config.config_file_name)

    db_url = config.get_main_option("sqlalchemy.url") or settings.DATABASE_URL
    config.set_main_option("sqlalchemy.url", db_url)

    if context.is_offline_mode():
        run_migrations_offline()
    else:
        run_migrations_online()
