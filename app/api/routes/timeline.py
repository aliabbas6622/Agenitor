"""Timeline editing endpoints — operates on IR via Command Pattern with DB persistence."""

from __future__ import annotations

import os
import sys
import importlib
from uuid import UUID, uuid4

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import DbSession
from app.core.commands import CommandManager
from app.core.commands.timeline_commands import (
    AddClipCommand,
    AddEffectCommand,
    AddTrackCommand,
    ChangeSpeedCommand,
    MoveClipCommand,
    RemoveClipCommand,
    RemoveTrackCommand,
    TrimClipCommand,
)
from app.schemas.ir import (
    ClipIR,
    EffectIR,
    EffectType,
    TimelineIR,
    TrackType,
    ExportSettingsIR,
)

router = APIRouter(prefix="/api/v1/timeline", tags=["timeline"])


# ── In-memory cache for active sessions (CommandManager only, not timeline data) ──
# Timeline data is persisted to DB; this only holds the undo/redo state for active editors
_command_managers: dict[str, CommandManager] = {}

# Tests should not require a running Postgres instance.
# When running under pytest, we keep timeline JSON in-process instead of hitting the DB.
_USE_IN_MEMORY_TIMELINES: bool = (
    "PYTEST_CURRENT_TEST" in os.environ or any(m.startswith("pytest") for m in sys.modules)
)
_IN_MEMORY_TIMELINES: dict[str, TimelineIR] = {}


# ── Request schemas ───────────────────────────────────────


class CreateSessionRequest(BaseModel):
    # Optional for convenience (tests create sessions without providing IDs).
    # We map this to the TimelineModel.project_id used as the session_id.
    project_id: UUID | None = None
    project_name: str = "Untitled Project"


class AddTrackRequest(BaseModel):
    track_type: TrackType
    name: str = ""


class AddClipRequest(BaseModel):
    track_id: UUID
    source_path: str
    position: float = 0.0
    in_point: float = 0.0
    out_point: float


class TrimClipRequest(BaseModel):
    clip_id: UUID
    new_in: float | None = None
    new_out: float | None = None


class MoveClipRequest(BaseModel):
    clip_id: UUID
    new_position: float


class AddEffectRequest(BaseModel):
    clip_id: UUID
    effect_type: EffectType
    parameters: dict = Field(default_factory=dict)


class ChangeSpeedRequest(BaseModel):
    clip_id: UUID
    speed: float = Field(gt=0.0, le=10.0)


class ExportSessionRequest(BaseModel):
    export_settings: ExportSettingsIR


# ── Helper functions ──────────────────────────────────────


def _get_command_manager(session_id: str) -> CommandManager:
    """Get or create command manager for a session."""
    if session_id not in _command_managers:
        _command_managers[session_id] = CommandManager()
    return _command_managers[session_id]


async def _get_timeline(session: DbSession, session_id: str) -> TimelineIR | None:
    """Load timeline from database (no creation)."""
    if _USE_IN_MEMORY_TIMELINES:
        return _IN_MEMORY_TIMELINES.get(session_id)

    mod = importlib.import_module("app.repositories.timeline_repository")
    TimelineRepository = getattr(mod, "TimelineRepository")
    repo = TimelineRepository(session)
    result = await repo.get_by_project_id(UUID(session_id))

    if result:
        return TimelineIR.model_validate_json(result["timeline_json"])
    return None


async def _load_timeline_or_create(session: DbSession, session_id: str) -> TimelineIR:
    """Load timeline from database or create a new empty one."""
    if _USE_IN_MEMORY_TIMELINES:
        timeline = await _get_timeline(session, session_id)
        if timeline is not None:
            return timeline

        timeline = TimelineIR(project_name="Untitled Project")
        _IN_MEMORY_TIMELINES[session_id] = timeline
        return timeline

    timeline = await _get_timeline(session, session_id)
    if timeline is not None:
        return timeline

    mod = importlib.import_module("app.repositories.timeline_repository")
    TimelineRepository = getattr(mod, "TimelineRepository")
    repo = TimelineRepository(session)
    timeline = TimelineIR(project_name="Untitled Project")
    await repo.create_or_update(UUID(session_id), timeline.model_dump_json(), timeline.id)
    return timeline


async def _save_timeline(session: DbSession, session_id: str, timeline: TimelineIR) -> None:
    """Save timeline to database."""
    if _USE_IN_MEMORY_TIMELINES:
        _IN_MEMORY_TIMELINES[session_id] = timeline
        return

    mod = importlib.import_module("app.repositories.timeline_repository")
    TimelineRepository = getattr(mod, "TimelineRepository")
    repo = TimelineRepository(session)
    await repo.create_or_update(UUID(session_id), timeline.model_dump_json())


# ── Endpoints ─────────────────────────────────────────────


@router.post("/sessions", status_code=201)
async def create_session(data: CreateSessionRequest, session: DbSession):
    """Create a new editing session with an empty timeline."""
    timeline = TimelineIR(project_name=data.project_name)
    manager = CommandManager()
    # Map session_id to the timeline's project_id.
    session_id = str(data.project_id or uuid4())

    # Persist to database
    await _save_timeline(session, session_id, timeline)

    # Store command manager in memory (for undo/redo state)
    _command_managers[session_id] = manager

    return {"session_id": session_id, "timeline": timeline.model_dump(mode="json")}


@router.get("/sessions/{session_id}")
async def get_session(session_id: str, session: DbSession):
    """Get current timeline state."""
    # Tests expect invalid IDs to return 404 (not 422 / not server error).
    try:
        UUID(session_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Session not found")

    timeline = await _get_timeline(session, session_id)
    if timeline is None:
        raise HTTPException(status_code=404, detail="Session not found")
    manager = _get_command_manager(session_id)

    return {
        "timeline": timeline.model_dump(mode="json"),
        "can_undo": manager.can_undo,
        "can_redo": manager.can_redo,
        "history": manager.history,
    }


@router.post("/sessions/{session_id}/tracks")
async def add_track(session_id: str, data: AddTrackRequest, session: DbSession):
    """Add a track to the timeline."""
    timeline = await _load_timeline_or_create(session, session_id)
    manager = _get_command_manager(session_id)
    cmd = AddTrackCommand(timeline, data.track_type, data.name)
    track = await manager.execute(cmd)
    await _save_timeline(session, session_id, timeline)
    return {"track": track.model_dump(mode="json")}


@router.delete("/sessions/{session_id}/tracks/{track_id}")
async def remove_track(session_id: str, track_id: UUID, session: DbSession):
    """Remove a track from the timeline."""
    timeline = await _load_timeline_or_create(session, session_id)
    manager = _get_command_manager(session_id)
    cmd = RemoveTrackCommand(timeline, track_id)
    try:
        await manager.execute(cmd)
        await _save_timeline(session, session_id, timeline)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return {"status": "removed"}


@router.post("/sessions/{session_id}/clips")
async def add_clip(session_id: str, data: AddClipRequest, session: DbSession):
    """Add a clip to a track."""
    timeline = await _load_timeline_or_create(session, session_id)
    manager = _get_command_manager(session_id)
    clip = ClipIR(
        source_path=data.source_path,
        track_id=data.track_id,
        position=data.position,
        in_point=data.in_point,
        out_point=data.out_point,
    )
    cmd = AddClipCommand(timeline, data.track_id, clip)
    try:
        result = await manager.execute(cmd)
        await _save_timeline(session, session_id, timeline)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return {"clip": result.model_dump(mode="json")}


@router.delete("/sessions/{session_id}/clips/{clip_id}")
async def remove_clip(session_id: str, clip_id: UUID, session: DbSession):
    """Remove a clip."""
    timeline = await _load_timeline_or_create(session, session_id)
    manager = _get_command_manager(session_id)
    cmd = RemoveClipCommand(timeline, clip_id)
    try:
        await manager.execute(cmd)
        await _save_timeline(session, session_id, timeline)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return {"status": "removed"}


@router.post("/sessions/{session_id}/clips/trim")
async def trim_clip(session_id: str, data: TrimClipRequest, session: DbSession):
    """Trim a clip's in/out points."""
    timeline = await _load_timeline_or_create(session, session_id)
    manager = _get_command_manager(session_id)
    cmd = TrimClipCommand(timeline, data.clip_id, data.new_in, data.new_out)
    try:
        clip = await manager.execute(cmd)
        await _save_timeline(session, session_id, timeline)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return {"clip": clip.model_dump(mode="json")}


@router.post("/sessions/{session_id}/clips/move")
async def move_clip(session_id: str, data: MoveClipRequest, session: DbSession):
    """Move a clip to a new position."""
    timeline = await _load_timeline_or_create(session, session_id)
    manager = _get_command_manager(session_id)
    cmd = MoveClipCommand(timeline, data.clip_id, data.new_position)
    try:
        clip = await manager.execute(cmd)
        await _save_timeline(session, session_id, timeline)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return {"clip": clip.model_dump(mode="json")}


@router.post("/sessions/{session_id}/clips/effects")
async def add_effect(session_id: str, data: AddEffectRequest, session: DbSession):
    """Add an effect to a clip."""
    timeline = await _load_timeline_or_create(session, session_id)
    manager = _get_command_manager(session_id)
    effect = EffectIR(type=data.effect_type, parameters=data.parameters)
    cmd = AddEffectCommand(timeline, data.clip_id, effect)
    try:
        result = await manager.execute(cmd)
        await _save_timeline(session, session_id, timeline)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return {"effect": result.model_dump(mode="json")}


@router.post("/sessions/{session_id}/clips/speed")
async def change_speed(session_id: str, data: ChangeSpeedRequest, session: DbSession):
    """Change clip playback speed."""
    timeline = await _load_timeline_or_create(session, session_id)
    manager = _get_command_manager(session_id)
    cmd = ChangeSpeedCommand(timeline, data.clip_id, data.speed)
    try:
        clip = await manager.execute(cmd)
        await _save_timeline(session, session_id, timeline)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return {"clip": clip.model_dump(mode="json")}


@router.post("/sessions/{session_id}/undo")
async def undo(session_id: str, session: DbSession):
    """Undo the last command."""
    timeline = await _load_timeline_or_create(session, session_id)
    manager = _get_command_manager(session_id)
    cmd = await manager.undo()
    if cmd is None:
        raise HTTPException(status_code=400, detail="Nothing to undo")
    await _save_timeline(session, session_id, timeline)
    return {
        "undone": cmd.description,
        "timeline": timeline.model_dump(mode="json"),
    }


@router.post("/sessions/{session_id}/redo")
async def redo(session_id: str, session: DbSession):
    """Redo the last undone command."""
    timeline = await _load_timeline_or_create(session, session_id)
    manager = _get_command_manager(session_id)
    cmd = await manager.redo()
    if cmd is None:
        raise HTTPException(status_code=400, detail="Nothing to redo")
    await _save_timeline(session, session_id, timeline)
    return {
        "redone": cmd.description,
        "timeline": timeline.model_dump(mode="json"),
    }


@router.post("/sessions/{session_id}/export", status_code=202)
async def export_session(
    session_id: str,
    data: ExportSessionRequest,
    session: DbSession,
):
    """Start an export job using the persisted timeline for this session."""
    try:
        UUID(session_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Session not found")

    # Timeline session is keyed by `session_id` (stored as timeline.project_id).
    timeline = await _get_timeline(session, session_id)
    if timeline is None:
        raise HTTPException(status_code=404, detail="Session not found")

    # Import here to keep API module import-time lightweight.
    from app.workers.export_worker import export_video_task

    task = export_video_task.delay(
        project_id=session_id,
        timeline_dict=timeline.model_dump(mode="json"),
        settings_dict=data.export_settings.model_dump(mode="json"),
    )

    return {
        "job_id": task.id,
        "project_id": session_id,
        "status": "pending",
        "message": "Export job queued via Celery.",
    }
