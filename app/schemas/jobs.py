"""Job and progress schemas for the worker queue."""

from __future__ import annotations

from enum import Enum
from typing import Any
from uuid import UUID

from pydantic import BaseModel

from app.schemas.ir import TimelineIR, ExportSettingsIR


class JobStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class JobRequest(BaseModel):
    """Payload to start a render job."""
    project_id: UUID
    timeline: TimelineIR
    export_settings: ExportSettingsIR


class JobProgressEvent(BaseModel):
    """Event emitted via WebSocket during job execution."""
    job_id: str
    project_id: str
    status: JobStatus
    progress: float  # 0.0 to 1.0
    stage: str
    message: str | None = None
    result_url: str | None = None
    error: str | None = None
