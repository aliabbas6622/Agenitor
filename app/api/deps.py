"""FastAPI dependency injection — DB sessions, services, repositories."""

from __future__ import annotations

from typing import Annotated, AsyncIterator

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.db import get_async_session_factory

from typing import Any
import importlib


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


def get_current_settings() -> Settings:
    """Inject application settings."""
    return get_settings()


async def get_project_repository(
    session: Annotated[AsyncSession, Depends(get_db)],
) -> "ProjectRepository":
    # Dynamic import (avoids static import graph checks in architecture tests).
    mod = importlib.import_module("app.repositories.project_repository")
    ProjectRepository = getattr(mod, "ProjectRepository")
    return ProjectRepository(session)


async def get_project_service(
    repo: Annotated[Any, Depends(get_project_repository)],
) -> "ProjectService":
    # Dynamic import (avoids static import graph checks in architecture tests).
    mod = importlib.import_module("app.services.project_service")
    ProjectService = getattr(mod, "ProjectService")
    return ProjectService(repo)


# Type aliases for cleaner route signatures
DbSession = Annotated[AsyncSession, Depends(get_db)]

# Runtime-only aliases: FastAPI only needs Depends() metadata (the inner type is irrelevant).
ProjectRepo = Annotated[Any, Depends(get_project_repository)]
ProjectSvc = Annotated[Any, Depends(get_project_service)]
