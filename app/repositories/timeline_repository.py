"""Timeline repository — PostgreSQL-backed storage for TimelineIR.

Stores and retrieves TimelineIR objects as JSON in the database.
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import TimelineModel


class TimelineRepository:
    """Timeline repository backed by PostgreSQL via SQLAlchemy."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_project_id(self, project_id: UUID) -> dict | None:
        """Get timeline JSON for a project."""
        result = await self._session.execute(
            select(TimelineModel).where(TimelineModel.project_id == project_id)
        )
        model = result.scalar_one_or_none()
        if model:
            return {
                "id": model.id,
                "project_id": model.project_id,
                "timeline_json": model.timeline_json,
                "version": model.version,
            }
        return None

    async def create_or_update(
        self,
        project_id: UUID,
        timeline_json: str,
        timeline_id: UUID | None = None,
    ) -> TimelineModel:
        """Create a new timeline or update existing one."""
        result = await self._session.execute(
            select(TimelineModel).where(TimelineModel.project_id == project_id)
        )
        model = result.scalar_one_or_none()

        if model:
            # Update existing
            model.timeline_json = timeline_json
            model.version += 1
        else:
            # Create new
            model = TimelineModel(
                id=timeline_id or UUID(int=0),  # Will be overwritten by default
                project_id=project_id,
                timeline_json=timeline_json,
            )
            self._session.add(model)

        await self._session.flush()
        return model

    async def delete(self, project_id: UUID) -> bool:
        """Delete timeline for a project."""
        result = await self._session.execute(
            select(TimelineModel).where(TimelineModel.project_id == project_id)
        )
        model = result.scalar_one_or_none()
        if model is None:
            return False
        await self._session.delete(model)
        await self._session.flush()
        return True
