"""Timeline command + API integration tests."""

from __future__ import annotations

import pytest


class TestCommandPattern:
    """Test the Command Pattern undo/redo mechanics on IR objects."""

    @pytest.fixture
    def timeline(self):
        from app.schemas.ir import TimelineIR
        return TimelineIR(project_name="Test Timeline")

    @pytest.fixture
    def manager(self):
        from app.core.commands import CommandManager
        return CommandManager()

    @pytest.mark.asyncio
    async def test_add_track_and_undo(self, timeline, manager):
        from app.core.commands.timeline_commands import AddTrackCommand
        from app.schemas.ir import TrackType

        cmd = AddTrackCommand(timeline, TrackType.VIDEO, "V1")
        await manager.execute(cmd)
        assert len(timeline.tracks) == 1
        assert timeline.tracks[0].name == "V1"

        await manager.undo()
        assert len(timeline.tracks) == 0

        await manager.redo()
        assert len(timeline.tracks) == 1

    @pytest.mark.asyncio
    async def test_add_clip_and_undo(self, timeline, manager):
        from app.core.commands.timeline_commands import AddClipCommand, AddTrackCommand
        from app.schemas.ir import ClipIR, TrackType

        # Add a track first
        track_cmd = AddTrackCommand(timeline, TrackType.VIDEO, "V1")
        track = await manager.execute(track_cmd)

        # Add a clip
        clip = ClipIR(source_path="/test.mp4", track_id=track.id, in_point=0, out_point=10)
        clip_cmd = AddClipCommand(timeline, track.id, clip)
        await manager.execute(clip_cmd)
        assert len(timeline.tracks[0].clips) == 1

        # Undo clip
        await manager.undo()
        assert len(timeline.tracks[0].clips) == 0

        # Redo clip
        await manager.redo()
        assert len(timeline.tracks[0].clips) == 1

    @pytest.mark.asyncio
    async def test_trim_clip(self, timeline, manager):
        from app.core.commands.timeline_commands import AddClipCommand, AddTrackCommand, TrimClipCommand
        from app.schemas.ir import ClipIR, TrackType

        track = await manager.execute(AddTrackCommand(timeline, TrackType.VIDEO))
        clip = ClipIR(source_path="/v.mp4", track_id=track.id, in_point=0, out_point=10)
        await manager.execute(AddClipCommand(timeline, track.id, clip))

        # Trim
        await manager.execute(TrimClipCommand(timeline, clip.id, new_in=2.0, new_out=8.0))
        trimmed = timeline.tracks[0].clips[0]
        assert trimmed.in_point == 2.0
        assert trimmed.out_point == 8.0

        # Undo trim
        await manager.undo()
        restored = timeline.tracks[0].clips[0]
        assert restored.in_point == 0.0
        assert restored.out_point == 10.0

    @pytest.mark.asyncio
    async def test_move_clip(self, timeline, manager):
        from app.core.commands.timeline_commands import AddClipCommand, AddTrackCommand, MoveClipCommand
        from app.schemas.ir import ClipIR, TrackType

        track = await manager.execute(AddTrackCommand(timeline, TrackType.AUDIO))
        clip = ClipIR(source_path="/a.wav", track_id=track.id, in_point=0, out_point=5)
        await manager.execute(AddClipCommand(timeline, track.id, clip))

        await manager.execute(MoveClipCommand(timeline, clip.id, 10.0))
        assert timeline.tracks[0].clips[0].position == 10.0

        await manager.undo()
        assert timeline.tracks[0].clips[0].position == 0.0

    @pytest.mark.asyncio
    async def test_add_effect(self, timeline, manager):
        from app.core.commands.timeline_commands import AddClipCommand, AddEffectCommand, AddTrackCommand
        from app.schemas.ir import ClipIR, EffectIR, EffectType, TrackType

        track = await manager.execute(AddTrackCommand(timeline, TrackType.VIDEO))
        clip = ClipIR(source_path="/v.mp4", track_id=track.id, in_point=0, out_point=5)
        await manager.execute(AddClipCommand(timeline, track.id, clip))

        effect = EffectIR(type=EffectType.BRIGHTNESS, parameters={"value": 1.5})
        await manager.execute(AddEffectCommand(timeline, clip.id, effect))
        assert len(timeline.tracks[0].clips[0].effects) == 1

        await manager.undo()
        assert len(timeline.tracks[0].clips[0].effects) == 0

    @pytest.mark.asyncio
    async def test_history_tracking(self, timeline, manager):
        from app.core.commands.timeline_commands import AddTrackCommand
        from app.schemas.ir import TrackType

        await manager.execute(AddTrackCommand(timeline, TrackType.VIDEO, "V1"))
        await manager.execute(AddTrackCommand(timeline, TrackType.AUDIO, "A1"))

        assert len(manager.history) == 2
        assert "video" in manager.history[0].lower()
        assert "audio" in manager.history[1].lower()


class TestTimelineAPI:
    """Test the timeline REST API endpoints."""

    def test_create_session(self, client):
        r = client.post("/api/v1/timeline/sessions", json={"project_name": "API Test"})
        assert r.status_code == 201
        data = r.json()
        assert "session_id" in data
        assert data["timeline"]["project_name"] == "API Test"

    def test_full_editing_flow(self, client):
        # Create session
        r = client.post("/api/v1/timeline/sessions", json={"project_name": "Flow Test"})
        sid = r.json()["session_id"]

        # Add video track
        r = client.post(f"/api/v1/timeline/sessions/{sid}/tracks",
                         json={"track_type": "video", "name": "V1"})
        assert r.status_code == 200
        track_id = r.json()["track"]["id"]

        # Add clip
        r = client.post(f"/api/v1/timeline/sessions/{sid}/clips", json={
            "track_id": track_id,
            "source_path": "/assets/intro.mp4",
            "position": 0,
            "in_point": 0,
            "out_point": 15,
        })
        assert r.status_code == 200
        clip_id = r.json()["clip"]["id"]

        # Trim clip
        r = client.post(f"/api/v1/timeline/sessions/{sid}/clips/trim", json={
            "clip_id": clip_id,
            "new_in": 2.0,
            "new_out": 12.0,
        })
        assert r.status_code == 200

        # Add effect
        r = client.post(f"/api/v1/timeline/sessions/{sid}/clips/effects", json={
            "clip_id": clip_id,
            "effect_type": "brightness",
            "parameters": {"value": 1.3},
        })
        assert r.status_code == 200

        # Undo effect
        r = client.post(f"/api/v1/timeline/sessions/{sid}/undo")
        assert r.status_code == 200
        assert "effect" in r.json()["undone"].lower()

        # Check state
        r = client.get(f"/api/v1/timeline/sessions/{sid}")
        assert r.status_code == 200
        state = r.json()
        assert state["can_undo"] is True
        assert state["can_redo"] is True
        assert len(state["timeline"]["tracks"][0]["clips"][0]["effects"]) == 0

    def test_undo_empty_returns_400(self, client):
        r = client.post("/api/v1/timeline/sessions", json={})
        sid = r.json()["session_id"]
        r = client.post(f"/api/v1/timeline/sessions/{sid}/undo")
        assert r.status_code == 400

    def test_nonexistent_session_returns_404(self, client):
        r = client.get("/api/v1/timeline/sessions/nonexistent")
        assert r.status_code == 404
