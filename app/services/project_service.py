"""Project service — business logic for project management.

Sits between API and repositories. May emit domain events.
"""

from __future__ import annotations

from uuid import UUID, uuid4

from app.core.events import ProjectCreated
from app.core.models import Project, ProjectStatus
from app.lib.event_bus import event_bus
from app.repositories.project_repository import ProjectRepository


class ProjectService:
    """Project lifecycle management."""

    def __init__(self, repo: ProjectRepository) -> None:
        self._repo = repo

    async def create_project(self, name: str, description: str = "", owner_id: str = "") -> Project:
        project = Project(
            id=uuid4(),
            name=name,
            description=description,
            status=ProjectStatus.DRAFT,
            owner_id=owner_id,
        )
        await self._repo.create(project)
        await event_bus.emit(
            "project:created",
            project_id=str(project.id),
            project_name=project.name,
        )
        return project

    async def get_project(self, project_id: UUID) -> Project | None:
        return await self._repo.get_by_id(project_id)

    async def list_projects(self, limit: int = 100, offset: int = 0) -> list[Project]:
        return await self._repo.list_all(limit=limit, offset=offset)

    async def update_project(
        self, project_id: UUID, name: str | None = None, description: str | None = None
    ) -> Project:
        project = await self._repo.get_by_id(project_id)
        if project is None:
            raise ValueError(f"Project {project_id} not found")
        if name is not None:
            project.name = name
        if description is not None:
            project.description = description
        return await self._repo.update(project)

    async def delete_project(self, project_id: UUID) -> bool:
        return await self._repo.delete(project_id)

    async def set_status(self, project_id: UUID, status: ProjectStatus) -> Project:
        project = await self._repo.get_by_id(project_id)
        if project is None:
            raise ValueError(f"Project {project_id} not found")
        project.status = status
        return await self._repo.update(project)
