"""IR schema validation tests."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.schemas.ir import (
    ClipIR,
    EffectIR,
    EffectType,
    ExportSettingsIR,
    OutputFormat,
    Resolution,
    TimelineIR,
    TrackIR,
    TrackType,
    TransitionIR,
    TransitionType,
)


class TestEffectIR:
    def test_valid_effect(self):
        effect = EffectIR(type=EffectType.BRIGHTNESS, parameters={"value": 1.5})
        assert effect.type == EffectType.BRIGHTNESS
        assert effect.parameters["value"] == 1.5

    def test_effect_defaults(self):
        effect = EffectIR(type=EffectType.BLUR)
        assert effect.start_time == 0.0
        assert effect.duration is None
        assert effect.parameters == {}


class TestTransitionIR:
    def test_default_transition(self):
        t = TransitionIR()
        assert t.type == TransitionType.CUT
        assert t.duration == 0.5

    def test_custom_transition(self):
        t = TransitionIR(type=TransitionType.CROSSFADE, duration=1.5)
        assert t.duration == 1.5


class TestClipIR:
    def test_valid_clip(self):
        from uuid import uuid4
        track_id = uuid4()
        clip = ClipIR(
            source_path="/assets/video.mp4",
            track_id=track_id,
            in_point=0.0,
            out_point=10.0,
        )
        assert clip.duration == 10.0
        assert clip.volume == 1.0
        assert clip.playback_speed == 1.0

    def test_clip_duration_with_speed(self):
        from uuid import uuid4
        clip = ClipIR(
            source_path="/assets/video.mp4",
            track_id=uuid4(),
            in_point=2.0,
            out_point=12.0,
            playback_speed=2.0,
        )
        assert clip.duration == 5.0  # (12-2) / 2.0

    def test_clip_rejects_negative_position(self):
        from uuid import uuid4
        with pytest.raises(ValidationError):
            ClipIR(
                source_path="/a.mp4",
                track_id=uuid4(),
                position=-1.0,
                in_point=0.0,
                out_point=5.0,
            )

    def test_clip_rejects_zero_out_point(self):
        from uuid import uuid4
        with pytest.raises(ValidationError):
            ClipIR(
                source_path="/a.mp4",
                track_id=uuid4(),
                in_point=0.0,
                out_point=0.0,  # must be > 0
            )


class TestTrackIR:
    def test_empty_track(self):
        track = TrackIR(type=TrackType.VIDEO, name="V1")
        assert track.clips == []
        assert track.muted is False
        assert track.opacity == 1.0

    def test_track_with_clips(self):
        from uuid import uuid4
        track_id = uuid4()
        clips = [
            ClipIR(source_path="/a.mp4", track_id=track_id, in_point=0, out_point=5),
            ClipIR(source_path="/b.mp4", track_id=track_id, in_point=0, out_point=3),
        ]
        track = TrackIR(id=track_id, type=TrackType.VIDEO, clips=clips)
        assert len(track.clips) == 2


class TestExportSettingsIR:
    def test_defaults(self):
        settings = ExportSettingsIR()
        assert settings.format == OutputFormat.MP4
        assert settings.resolution == Resolution.FHD_1080
        assert settings.frame_rate == 30.0

    def test_custom_settings(self):
        settings = ExportSettingsIR(
            format=OutputFormat.WEBM,
            resolution=Resolution.UHD_4K,
            frame_rate=60.0,
            bitrate_kbps=20000,
        )
        assert settings.format == OutputFormat.WEBM
        assert settings.frame_rate == 60.0


class TestTimelineIR:
    def test_empty_timeline(self):
        tl = TimelineIR()
        assert tl.project_name == "Untitled Project"
        assert tl.tracks == []
        assert tl.compute_duration() == 0.0

    def test_timeline_compute_duration(self):
        from uuid import uuid4
        track_id = uuid4()
        clip = ClipIR(
            source_path="/v.mp4",
            track_id=track_id,
            position=5.0,
            in_point=0.0,
            out_point=10.0,
        )
        track = TrackIR(id=track_id, type=TrackType.VIDEO, clips=[clip])
        tl = TimelineIR(tracks=[track])
        assert tl.compute_duration() == 15.0  # position(5) + duration(10)

    def test_timeline_json_roundtrip(self):
        tl = TimelineIR(project_name="Test Project")
        json_str = tl.model_dump_json()
        restored = TimelineIR.model_validate_json(json_str)
        assert restored.project_name == "Test Project"
        assert restored.id == tl.id
