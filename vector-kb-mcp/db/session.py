from contextlib import asynccontextmanager
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from core.config import settings

# Initialize high-performance async engine with asyncpg and connection pooling
engine: AsyncEngine = create_async_engine(
    settings.DATABASE_URL,
    echo=getattr(settings, "DEBUG", False),
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,
    pool_recycle=3600,
)

# Thread-safe async session factory
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


@asynccontextmanager
async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Async context manager providing transaction-managed DB sessions with
    auto-rollback. Commits changes automatically on clean exit, rolls back on
    exceptions, and guarantees session closure.
    """
    session: AsyncSession = AsyncSessionLocal()
    try:
        yield session
        await session.commit()
    except Exception:
        await session.rollback()
        raise
    finally:
        await session.close()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Async generator for dependency injection or manual iteration
    yielding AsyncSession.
    """
    session: AsyncSession = AsyncSessionLocal()
    try:
        yield session
    finally:
        await session.close()


async def close_db_engine() -> None:
    """
    Gracefully dispose of database connection pools.
    """
    await engine.dispose()
