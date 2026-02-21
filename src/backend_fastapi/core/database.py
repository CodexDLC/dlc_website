from collections.abc import AsyncGenerator
from typing import Any
from urllib.parse import urlparse, urlunparse

from loguru import logger
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from ..database.models.base import Base
from .config import settings

# --- Connection Configuration ---

# Schema isolation: FastAPI uses its own schema (default: fastapi_app).
# This allows sharing one DB (e.g. Neon) with Django/Bot
# without table name conflicts.
connect_args: dict[str, Any] = {
    "prepared_statement_cache_size": 0,
    "server_settings": {
        "search_path": f"{settings.DB_SCHEMA},public",
    },
}

db_url = settings.DATABASE_URL

# Handle SSL mode for asyncpg
if "sslmode" in db_url:
    connect_args["ssl"] = "require"
    try:
        parsed = urlparse(db_url)
        # Remove query params (like sslmode) from URL as they are handled in connect_args
        db_url = urlunparse(parsed._replace(query=""))
    except Exception as parse_exc:
        logger.warning(f"Database | action=parse_url_failed error={parse_exc}")

pool_settings: dict[str, Any] = {
    "pool_size": 20,
    "max_overflow": 10,
    "pool_pre_ping": True,
}

async_engine = create_async_engine(
    db_url,
    echo=False,
    connect_args=connect_args,
    **pool_settings,
)

async_session_factory = async_sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


async def get_db() -> AsyncGenerator[AsyncSession]:
    """
    Dependency for getting async database session.
    """
    async with async_session_factory() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def create_db_tables() -> None:
    """
    Create all tables defined in SQLAlchemy models.
    """
    try:
        async with async_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database | action=create_tables status=success")
    except SQLAlchemyError as db_exc:
        logger.error(f"Database | action=create_tables status=failed error={db_exc}")


# Explicitly export Base for mypy
__all__ = ["Base", "get_db", "create_db_tables", "async_engine"]
