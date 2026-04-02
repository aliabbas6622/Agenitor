"""Core domain models — pure Python, no ORM dependencies.

These represent business concepts. ORM models in app/db/models.py
map to these for persistence. Domain models never import from db/.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from uuid import UUID, uuid4


class ProjectStatus(str, Enum):
    DRAFT = "draft"
    PROCESSING = "processing"
    READY = "ready"
    EXPORTED = "exported"
    FAILED = "failed"


@dataclass
class Project:
    """A video editing project."""
    id: UUID = field(default_factory=uuid4)
    name: str = "Untitled Project"
    description: str = ""
    status: ProjectStatus = ProjectStatus.DRAFT
    owner_id: str = ""

    def can_export(self) -> bool:
        return self.status in (ProjectStatus.DRAFT, ProjectStatus.READY)


@dataclass
class Asset:
    """A media asset (video, audio, image) used in projects."""
    id: UUID = field(default_factory=uuid4)
    filename: str = ""
    content_type: str = ""
    file_path: str = ""
    file_size_bytes: int = 0
    duration_seconds: float = 0.0
    project_id: UUID | None = None
