"""Concrete timeline commands — Command Pattern implementations.

Each command captures state before execution and can fully undo.
These are the mutations that AI agents and the API layer drive.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID, uuid4

from app.core.commands import Command
from app.schemas.ir import ClipIR, EffectIR, TrackIR, TrackType, TimelineIR


class AddTrackCommand(Command):
    """Add a new track to the timeline."""

    def __init__(self, timeline: TimelineIR, track_type: TrackType, name: str = "") -> None:
        self._timeline = timeline
        self._track_type = track_type
        self._name = name
        self._track_id: UUID | None = None

    @property
    def description(self) -> str:
        return f"Add {self._track_type.value} track '{self._name}'"

    async def execute(self) -> Any:
        track = TrackIR(id=uuid4(), type=self._track_type, name=self._name)
        self._track_id = track.id
        self._timeline.tracks.append(track)
        return track

    async def undo(self) -> None:
        self._timeline.tracks = [
            t for t in self._timeline.tracks if t.id != self._track_id
        ]


class RemoveTrackCommand(Command):
    """Remove a track from the timeline."""

    def __init__(self, timeline: TimelineIR, track_id: UUID) -> None:
        self._timeline = timeline
        self._track_id = track_id
        self._snapshot: TrackIR | None = None
        self._index: int = -1

    @property
    def description(self) -> str:
        return f"Remove track {self._track_id}"

    async def execute(self) -> Any:
        for i, track in enumerate(self._timeline.tracks):
            if track.id == self._track_id:
                self._snapshot = track
                self._index = i
                self._timeline.tracks.pop(i)
                return
        raise ValueError(f"Track {self._track_id} not found")

    async def undo(self) -> None:
        if self._snapshot is not None:
            self._timeline.tracks.insert(self._index, self._snapshot)


class AddClipCommand(Command):
    """Add a clip to a specific track."""

    def __init__(self, timeline: TimelineIR, track_id: UUID, clip: ClipIR) -> None:
        self._timeline = timeline
        self._track_id = track_id
        self._clip = clip

    @property
    def description(self) -> str:
        return f"Add clip {self._clip.source_path} to track"

    async def execute(self) -> Any:
        for track in self._timeline.tracks:
            if track.id == self._track_id:
                self._clip.track_id = self._track_id
                track.clips.append(self._clip)
                return self._clip
        raise ValueError(f"Track {self._track_id} not found")

    async def undo(self) -> None:
        for track in self._timeline.tracks:
            if track.id == self._track_id:
                track.clips = [c for c in track.clips if c.id != self._clip.id]
                return


class RemoveClipCommand(Command):
    """Remove a clip from the timeline."""

    def __init__(self, timeline: TimelineIR, clip_id: UUID) -> None:
        self._timeline = timeline
        self._clip_id = clip_id
        self._snapshot: ClipIR | None = None
        self._track_id: UUID | None = None

    @property
    def description(self) -> str:
        return f"Remove clip {self._clip_id}"

    async def execute(self) -> Any:
        for track in self._timeline.tracks:
            for i, clip in enumerate(track.clips):
                if clip.id == self._clip_id:
                    self._snapshot = clip
                    self._track_id = track.id
                    track.clips.pop(i)
                    return
        raise ValueError(f"Clip {self._clip_id} not found")

    async def undo(self) -> None:
        if self._snapshot and self._track_id:
            for track in self._timeline.tracks:
                if track.id == self._track_id:
                    track.clips.append(self._snapshot)
                    return


class TrimClipCommand(Command):
    """Trim a clip's in/out points."""

    def __init__(
        self, timeline: TimelineIR, clip_id: UUID,
        new_in: float | None = None, new_out: float | None = None,
    ) -> None:
        self._timeline = timeline
        self._clip_id = clip_id
        self._new_in = new_in
        self._new_out = new_out
        self._old_in: float = 0.0
        self._old_out: float = 0.0

    @property
    def description(self) -> str:
        return f"Trim clip {self._clip_id}"

    def _find_clip(self) -> ClipIR:
        for track in self._timeline.tracks:
            for clip in track.clips:
                if clip.id == self._clip_id:
                    return clip
        raise ValueError(f"Clip {self._clip_id} not found")

    async def execute(self) -> Any:
        clip = self._find_clip()
        self._old_in = clip.in_point
        self._old_out = clip.out_point
        if self._new_in is not None:
            clip.in_point = self._new_in
        if self._new_out is not None:
            clip.out_point = self._new_out
        return clip

    async def undo(self) -> None:
        clip = self._find_clip()
        clip.in_point = self._old_in
        clip.out_point = self._old_out


class MoveClipCommand(Command):
    """Move a clip to a new position on the timeline."""

    def __init__(self, timeline: TimelineIR, clip_id: UUID, new_position: float) -> None:
        self._timeline = timeline
        self._clip_id = clip_id
        self._new_position = new_position
        self._old_position: float = 0.0

    @property
    def description(self) -> str:
        return f"Move clip {self._clip_id} to {self._new_position}s"

    def _find_clip(self) -> ClipIR:
        for track in self._timeline.tracks:
            for clip in track.clips:
                if clip.id == self._clip_id:
                    return clip
        raise ValueError(f"Clip {self._clip_id} not found")

    async def execute(self) -> Any:
        clip = self._find_clip()
        self._old_position = clip.position
        clip.position = self._new_position
        return clip

    async def undo(self) -> None:
        clip = self._find_clip()
        clip.position = self._old_position


class AddEffectCommand(Command):
    """Add an effect to a clip."""

    def __init__(self, timeline: TimelineIR, clip_id: UUID, effect: EffectIR) -> None:
        self._timeline = timeline
        self._clip_id = clip_id
        self._effect = effect

    @property
    def description(self) -> str:
        return f"Add {self._effect.type.value} effect to clip"

    def _find_clip(self) -> ClipIR:
        for track in self._timeline.tracks:
            for clip in track.clips:
                if clip.id == self._clip_id:
                    return clip
        raise ValueError(f"Clip {self._clip_id} not found")

    async def execute(self) -> Any:
        clip = self._find_clip()
        clip.effects.append(self._effect)
        return self._effect

    async def undo(self) -> None:
        clip = self._find_clip()
        clip.effects = [e for e in clip.effects if e.id != self._effect.id]


class ChangeSpeedCommand(Command):
    """Change playback speed of a clip."""

    def __init__(self, timeline: TimelineIR, clip_id: UUID, new_speed: float) -> None:
        self._timeline = timeline
        self._clip_id = clip_id
        self._new_speed = new_speed
        self._old_speed: float = 1.0

    @property
    def description(self) -> str:
        return f"Change clip speed to {self._new_speed}x"

    def _find_clip(self) -> ClipIR:
        for track in self._timeline.tracks:
            for clip in track.clips:
                if clip.id == self._clip_id:
                    return clip
        raise ValueError(f"Clip {self._clip_id} not found")

    async def execute(self) -> Any:
        clip = self._find_clip()
        self._old_speed = clip.playback_speed
        clip.playback_speed = self._new_speed
        return clip

    async def undo(self) -> None:
        clip = self._find_clip()
        clip.playback_speed = self._old_speed
