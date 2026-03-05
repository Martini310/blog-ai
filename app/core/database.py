"""
Async SQLAlchemy 2.0 engine and session factory.

Usage in routes / services:
    async with get_db() as session:
        ...

Or via FastAPI dependency injection:
    async def endpoint(db: AsyncSession = Depends(get_db_session)):
        ...
"""
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings


# ---------------------------------------------------------------------------
# Engine – single engine shared across the entire process lifetime.
# pool_pre_ping keeps idle connections healthy.
# ---------------------------------------------------------------------------
engine = create_async_engine(
    settings.DATABASE_URL,
    pool_size=settings.DB_POOL_SIZE,
    max_overflow=settings.DB_MAX_OVERFLOW,
    pool_recycle=settings.DB_POOL_RECYCLE,
    pool_pre_ping=True,
    echo=settings.DEBUG,
)

# ---------------------------------------------------------------------------
# Session factory – expire_on_commit=False is important for async contexts
# where the session may be closed before lazy-loaded attributes are accessed.
# ---------------------------------------------------------------------------
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)


# ---------------------------------------------------------------------------
# Declarative base used by all models
# ---------------------------------------------------------------------------
class Base(DeclarativeBase):
    pass


# ---------------------------------------------------------------------------
# Dependency for FastAPI routes
# ---------------------------------------------------------------------------
async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency – yields a session and commits/rolls back on exit."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


# ---------------------------------------------------------------------------
# Context-manager variant used in services / tasks (outside request context)
# ---------------------------------------------------------------------------
@asynccontextmanager
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Async context manager for use in Celery tasks and standalone scripts."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
