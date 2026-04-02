"""Domain event definitions.

Event names follow the convention: <entity>:<past-tense-verb>
No future tense. No generic names like 'update'.

Examples:
  - clip:trimmed
  - project:created
  - export:completed
  - track:added
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import UUID, uuid4


@dataclass(frozen=True)
class DomainEvent:
    """Base event — all domain events inherit from this."""
    event_id: UUID = field(default_factory=uuid4)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass(frozen=True)
class ProjectCreated(DomainEvent):
    project_id: UUID = field(default_factory=uuid4)
    project_name: str = ""


@dataclass(frozen=True)
class ClipTrimmed(DomainEvent):
    clip_id: UUID = field(default_factory=uuid4)
    project_id: UUID = field(default_factory=uuid4)
    old_duration: float = 0.0
    new_duration: float = 0.0


@dataclass(frozen=True)
class TrackAdded(DomainEvent):
    track_id: UUID = field(default_factory=uuid4)
    project_id: UUID = field(default_factory=uuid4)
    track_type: str = "video"


@dataclass(frozen=True)
class ExportStarted(DomainEvent):
    project_id: UUID = field(default_factory=uuid4)
    job_id: UUID = field(default_factory=uuid4)
    format: str = "mp4"


@dataclass(frozen=True)
class ExportCompleted(DomainEvent):
    project_id: UUID = field(default_factory=uuid4)
    job_id: UUID = field(default_factory=uuid4)
    output_url: str = ""


@dataclass(frozen=True)
class ExportFailed(DomainEvent):
    project_id: UUID = field(default_factory=uuid4)
    job_id: UUID = field(default_factory=uuid4)
    error: str = ""
