"""Project management endpoints — full CRUD."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.api.deps import ProjectSvc
from app.core.models import ProjectStatus

router = APIRouter(prefix="/api/v1/projects", tags=["projects"])


# ── Request / Response schemas ────────────────────────────


class ProjectCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=256)
    description: str = ""


class ProjectUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=256)
    description: str | None = None


class ProjectResponse(BaseModel):
    id: UUID
    name: str
    description: str
    status: str
    owner_id: str


class ProjectListResponse(BaseModel):
    projects: list[ProjectResponse]
    count: int


# ── Endpoints ──────────────────────────────────────────────


@router.get("", response_model=ProjectListResponse)
async def list_projects(
    svc: ProjectSvc,
    limit: int = 100,
    offset: int = 0,
):
    """List all projects."""
    projects = await svc.list_projects(limit=limit, offset=offset)
    return ProjectListResponse(
        projects=[
            ProjectResponse(
                id=p.id, name=p.name, description=p.description,
                status=p.status.value, owner_id=p.owner_id,
            )
            for p in projects
        ],
        count=len(projects),
    )


@router.post("", response_model=ProjectResponse, status_code=201)
async def create_project(data: ProjectCreate, svc: ProjectSvc):
    """Create a new project."""
    project = await svc.create_project(name=data.name, description=data.description)
    return ProjectResponse(
        id=project.id, name=project.name, description=project.description,
        status=project.status.value, owner_id=project.owner_id,
    )


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(project_id: UUID, svc: ProjectSvc):
    """Get a single project by ID."""
    project = await svc.get_project(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    return ProjectResponse(
        id=project.id, name=project.name, description=project.description,
        status=project.status.value, owner_id=project.owner_id,
    )


@router.patch("/{project_id}", response_model=ProjectResponse)
async def update_project(project_id: UUID, data: ProjectUpdate, svc: ProjectSvc):
    """Update a project."""
    try:
        project = await svc.update_project(
            project_id, name=data.name, description=data.description,
        )
    except ValueError:
        raise HTTPException(status_code=404, detail="Project not found")
    return ProjectResponse(
        id=project.id, name=project.name, description=project.description,
        status=project.status.value, owner_id=project.owner_id,
    )


@router.delete("/{project_id}", status_code=204)
async def delete_project(project_id: UUID, svc: ProjectSvc):
    """Delete a project."""
    deleted = await svc.delete_project(project_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Project not found")
