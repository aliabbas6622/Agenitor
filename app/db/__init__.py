"""Database session management."""

from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import get_settings


class Base(DeclarativeBase):
    """SQLAlchemy declarative base for all ORM models."""
    pass


def get_async_engine():
    """Create async engine for FastAPI request handling."""
    settings = get_settings()
    return create_async_engine(
        settings.database_url,
        echo=settings.app_debug,
        pool_size=20,
        max_overflow=10,
    )


def get_sync_engine():
    """Create sync engine for Celery workers and migrations."""
    settings = get_settings()
    return create_engine(
        settings.database_url_sync,
        echo=settings.app_debug,
        pool_size=10,
        max_overflow=5,
    )


def get_async_session_factory() -> async_sessionmaker[AsyncSession]:
    """Async session factory for use in FastAPI dependency injection."""
    engine = get_async_engine()
    return async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


def get_sync_session_factory() -> sessionmaker[Session]:
    """Sync session factory for Celery workers."""
    engine = get_sync_engine()
    return sessionmaker(engine, expire_on_commit=False)
