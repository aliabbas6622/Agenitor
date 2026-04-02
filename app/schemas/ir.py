"""Intermediate Representation (IR) schemas.

These Pydantic v2 models define the universal communication format between
the AI orchestration layer (Python) and the rendering engine (C++).
Every instruction from the AI layer to the engine passes through these schemas.
"""

from __future__ import annotations

from enum import Enum
from typing import Any
from uuid import UUID, uuid4

from pathlib import Path
from pydantic import BaseModel, Field, field_validator


# ── Enums ─────────────────────────────────────────────────


class TrackType(str, Enum):
    """Type of track in a timeline."""
    VIDEO = "video"
    AUDIO = "audio"
    SUBTITLE = "subtitle"


class EffectType(str, Enum):
    """Built-in effect types supported by the engine."""
    FADE_IN = "fade_in"
    FADE_OUT = "fade_out"
    BRIGHTNESS = "brightness"
    CONTRAST = "contrast"
    SATURATION = "saturation"
    BLUR = "blur"
    CROP = "crop"
    SPEED = "speed"
    COLOR_GRADE = "color_grade"
    CUSTOM = "custom"


class TransitionType(str, Enum):
    """Transition types between clips."""
    CUT = "cut"
    CROSSFADE = "crossfade"
    DISSOLVE = "dissolve"
    WIPE_LEFT = "wipe_left"
    WIPE_RIGHT = "wipe_right"
    FADE_BLACK = "fade_black"
    FADE_WHITE = "fade_white"


class OutputFormat(str, Enum):
    """Supported export formats."""
    MP4 = "mp4"
    WEBM = "webm"
    MOV = "mov"
    MKV = "mkv"


class Resolution(str, Enum):
    """Standard resolutions."""
    HD_720 = "720p"
    FHD_1080 = "1080p"
    QHD_1440 = "1440p"
    UHD_4K = "4k"


class Codec(str, Enum):
    """Video codecs."""
    H264 = "h264"
    H265 = "h265"
    VP9 = "vp9"
    AV1 = "av1"


# ── Core IR Models ────────────────────────────────────────


class EffectIR(BaseModel):
    """An effect applied to a clip."""
    id: UUID = Field(default_factory=uuid4)
    type: EffectType
    parameters: dict[str, Any] = Field(default_factory=dict)
    start_time: float = Field(0.0, ge=0.0, description="Effect start relative to clip (seconds)")
    duration: float | None = Field(None, ge=0.0, description="None = entire clip duration")

    model_config = {"json_schema_extra": {
        "examples": [{"type": "brightness", "parameters": {"value": 1.2}, "start_time": 0.0}]
    }}


class TransitionIR(BaseModel):
    """A transition between two clips."""
    id: UUID = Field(default_factory=uuid4)
    type: TransitionType = TransitionType.CUT
    duration: float = Field(0.5, ge=0.0, le=10.0, description="Transition duration (seconds)")


class ClipIR(BaseModel):
    """A single clip on a track — the atomic unit of the timeline."""
    id: UUID = Field(default_factory=uuid4)
    source_path: str = Field(..., description="Path or URI to the source asset")
    track_id: UUID = Field(..., description="Parent track ID")
    position: float = Field(0.0, ge=0.0, description="Position on timeline (seconds)")
    in_point: float = Field(0.0, ge=0.0, description="Source start point (seconds)")
    out_point: float = Field(..., gt=0.0, description="Source end point (seconds)")
    effects: list[EffectIR] = Field(default_factory=list)
    transition_in: TransitionIR | None = None
    transition_out: TransitionIR | None = None
    volume: float = Field(1.0, ge=0.0, le=2.0, description="Audio volume multiplier")
    playback_speed: float = Field(1.0, gt=0.0, le=10.0)

    @field_validator("source_path")
    @classmethod
    def validate_source_path(cls, v: str) -> str:
        """SECURITY: Prevent path traversal attacks."""
        # Allow URI schemes (http://, https://, s3://, etc.)
        if "://" in v:
            return v

        # For local paths, reject any explicit traversal component.
        # Avoid platform-specific path attributes (e.g. WindowsPath.separator).
        path = Path(v)
        if any(part == ".." for part in path.parts):
            raise ValueError("Path traversal not allowed")

        return v

    @property
    def duration(self) -> float:
        """Effective duration accounting for in/out points and speed."""
        return (self.out_point - self.in_point) / self.playback_speed


class TrackIR(BaseModel):
    """A track (video, audio, or subtitle) in the timeline."""
    id: UUID = Field(default_factory=uuid4)
    type: TrackType
    name: str = ""
    clips: list[ClipIR] = Field(default_factory=list)
    muted: bool = False
    locked: bool = False
    opacity: float = Field(1.0, ge=0.0, le=1.0, description="Track-level opacity (video only)")


class ExportSettingsIR(BaseModel):
    """Export configuration for rendering the final output."""
    format: OutputFormat = OutputFormat.MP4
    resolution: Resolution = Resolution.FHD_1080
    codec: Codec = Codec.H264
    frame_rate: float = Field(30.0, gt=0.0, le=120.0)
    bitrate_kbps: int = Field(8000, gt=0)
    audio_bitrate_kbps: int = Field(192, gt=0)
    output_path: str = Field("output.mp4", description="Destination file path")

    @field_validator("output_path")
    @classmethod
    def validate_output_path(cls, v: str) -> str:
        """SECURITY: Prevent path traversal attacks on output."""
        path = Path(v)
        # Ensure output path doesn't contain traversal sequences
        if ".." in v:
            raise ValueError("Output path cannot contain '..'")
        # Ensure filename has valid extension
        if path.suffix.lower() not in [".mp4", ".webm", ".mov", ".mkv"]:
            raise ValueError("Output path must have valid video extension (.mp4, .webm, .mov, .mkv)")
        return v


class TimelineIR(BaseModel):
    """Top-level Intermediate Representation of a video project.

    This is the root document passed between AI decisions and the C++ engine.
    """
    id: UUID = Field(default_factory=uuid4)
    project_name: str = Field("Untitled Project", min_length=1, max_length=256)
    tracks: list[TrackIR] = Field(default_factory=list)
    duration: float = Field(0.0, ge=0.0, description="Total timeline duration (seconds)")
    export_settings: ExportSettingsIR = Field(default_factory=ExportSettingsIR)
    metadata: dict[str, Any] = Field(default_factory=dict)

    def compute_duration(self) -> float:
        """Calculate timeline duration from clip positions."""
        max_end = 0.0
        for track in self.tracks:
            for clip in track.clips:
                clip_end = clip.position + clip.duration
                if clip_end > max_end:
                    max_end = clip_end
        return max_end
