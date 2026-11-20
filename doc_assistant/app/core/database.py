"""SQLAlchemy 2.0 async engine, session factory, and declarative base."""

from __future__ import annotations

import logging
from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

logger = logging.getLogger(__name__)

# Register pgvector Vector type if installed
try:
    import pgvector.sqlalchemy  # noqa: F401
except ImportError:
    logger.debug("pgvector.sqlalchemy not found; vector queries will use fallback.")

from doc_assistant.app.core.config import settings

# ── Safe database engine creation ───────────────────────────────────────────
db_url = settings.DATABASE_URL
engine = None
async_session_factory = None

try:
    engine = create_async_engine(
        db_url,
        echo=False,
        future=True,
        pool_pre_ping=True,
    )
    async_session_factory = async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
except Exception as exc:
    logger.warning(
        "Async database engine could not be initialized at module import (%s). "
        "Engine will be initialized when dependencies (asyncpg/aiosqlite) are present.",
        exc,
    )


# ── Declarative base ───────────────────────────────────────────────────────
class Base(DeclarativeBase):
    """Shared declarative base for all ORM models."""
    pass


# ── Dependency ──────────────────────────────────────────────────────────────
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency that yields an async database session."""
    if async_session_factory is None:
        raise RuntimeError(
            "Database session factory is not configured. "
            "Please ensure asyncpg is installed and DATABASE_URL is set."
        )
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
