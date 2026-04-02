"""Concrete repository — PostgreSQL-backed project storage.

Returns domain objects (app/core/models/), never raw ORM rows.
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.models import Project, ProjectStatus
from app.db.models import ProjectModel
from app.repositories import BaseRepository


class ProjectRepository(BaseRepository[Project]):
    """Project repository backed by PostgreSQL via SQLAlchemy."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, id: UUID) -> Project | None:
        result = await self._session.execute(
            select(ProjectModel).where(ProjectModel.id == id)
        )
        row = result.scalar_one_or_none()
        return self._to_domain(row) if row else None

    async def list_all(self, limit: int = 100, offset: int = 0) -> list[Project]:
        result = await self._session.execute(
            select(ProjectModel).limit(limit).offset(offset)
        )
        return [self._to_domain(row) for row in result.scalars().all()]

    async def create(self, entity: Project) -> Project:
        model = ProjectModel(
            id=entity.id,
            name=entity.name,
            description=entity.description,
            status=entity.status.value,
            owner_id=entity.owner_id,
        )
        self._session.add(model)
        await self._session.flush()
        return entity

    async def update(self, entity: Project) -> Project:
        result = await self._session.execute(
            select(ProjectModel).where(ProjectModel.id == entity.id)
        )
        model = result.scalar_one_or_none()
        if model is None:
            raise ValueError(f"Project {entity.id} not found")
        model.name = entity.name
        model.description = entity.description
        model.status = entity.status.value
        model.owner_id = entity.owner_id
        await self._session.flush()
        return entity

    async def delete(self, id: UUID) -> bool:
        result = await self._session.execute(
            select(ProjectModel).where(ProjectModel.id == id)
        )
        model = result.scalar_one_or_none()
        if model is None:
            return False
        await self._session.delete(model)
        await self._session.flush()
        return True

    @staticmethod
    def _to_domain(model: ProjectModel) -> Project:
        return Project(
            id=model.id,
            name=model.name,
            description=model.description,
            status=ProjectStatus(model.status),
            owner_id=model.owner_id,
        )
