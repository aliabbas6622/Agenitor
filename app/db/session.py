"""Database session dependency for FastAPI — async context manager."""

from __future__ import annotations

from typing import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_async_session_factory


async def get_db() -> AsyncIterator[AsyncSession]:
    """Yield an async DB session, auto-closing on exit."""
    factory = get_async_session_factory()
    async with factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
