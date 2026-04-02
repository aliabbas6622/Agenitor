# Changelog

## Phase 7 — Production Hardening & Real Rendering (2026-04-02)

### Security Fixes
- Updated `.env.example` with placeholder credentials (`CHANGE_ME_STRONG_PASSWORD`) and added security comments
- Restricted CORS methods to explicit list (GET, POST, PUT, PATCH, DELETE, OPTIONS) and specific headers
- Added path traversal validation to `ClipIR.source_path` and `ExportSettingsIR.output_path` using Pydantic validators
- Added empty API key placeholders for OpenAI, ElevenLabs, Pexels, and Pixabay

### Reliability Improvements
- Implemented `retry_with_backoff()` utility with exponential backoff and jitter in `app/services/ai/strategy.py`
- Added retry logic to LLM calls for RateLimitError, APIConnectionError, Timeout, and APIError
- Replaced print statements with proper logging throughout (`app/main.py`, `app/workers/export_worker.py`)
- Created centralized `app/logging_config.py` module for structured logging configuration

### Data Persistence
- Added `TimelineModel` ORM for database-backed timeline storage (`app/db/models.py`)
- Implemented `TimelineRepository` with create/update/delete operations (`app/repositories/timeline_repository.py`)
- Updated all timeline endpoints to persist to PostgreSQL instead of in-memory dict (`app/api/routes/timeline.py`)
- CommandManager now only holds transient undo/redo state; timeline data is always persisted

### AI Agent Fixes
- Fixed `AgentService.edit_timeline()` to actually apply mutations via `_execute_action()` method
- Added support for all command types: AddTrack, AddClip, RemoveClip, TrimClip, MoveClip, AddEffect, ChangeSpeed
- Proper error handling with continue-on-failure for partial batch operations

### WebSocket Progress
- Updated `_emit_progress_sync()` in export worker to broadcast via WebSocket manager
- Progress events now flow from Celery workers to connected frontend clients

---

## Phase 8 — Editor Usability Improvements (2026-04-02)
### Output Distribution
- Mounted `GET /exports/*` by serving the repository-level `exports/` directory via FastAPI `StaticFiles`, so Celery export results are downloadable by clients.

### Real-Time Progress Delivery (Celery -> WS)
- Added a Redis pub/sub bridge so `export_worker` progress events reach WebSocket clients even when Celery runs in a separate process from the API server.

## Phase 9 — Media Library APIs (2026-04-02)
### Asset Upload & Listing
- Added `POST /api/v1/assets/upload` and `GET /api/v1/assets?project_id=...` for ingesting media files into projects and returning stable `file_path` values for timeline clips.

## Phase 10 — Session-Based Export (2026-04-02)
### Export From Timeline Session
- Added `POST /api/v1/timeline/sessions/{session_id}/export` to enqueue a Celery export job using the persisted timeline for that session.

## Phase 11 — Job Progress Payload Consistency (2026-04-02)
### Success/Failure Fields
- Updated WebSocket/Redis job progress events to include `result_url` on `completed` and `error` on `failed`, matching `JobProgressEvent`.

## Phase 12 — Native Module Build Robustness (2026-04-02)
### Optional FFmpeg Toolchain
- Made FFmpeg toolchain optional in the CMake configuration (Windows-friendly) and added `HAVE_FFMPEG` guards/stubs so the engine + bindings can compile even when FFmpeg dev libraries are missing.
- Fixed pybind bindings by adding the missing `IFrameGrabber` base-class binding, enabling `FrameGrabber` to import correctly in Python.
- Updated export worker to avoid selecting `FFmpegRenderer` under pytest so tests don’t depend on FFmpeg availability.

## Phase 13 — Downloadable Uploads (2026-04-02)
### Static Asset Serving
- Mounted `GET /uploads/*` for the repository-level `uploads/` directory.
- `AssetResponse` now includes `download_url` (e.g. `/uploads/<project_id>/<asset_id>_<filename>`) so clients don’t have to use local filesystem paths.

## Phase 14 — Asset Details Endpoint (2026-04-02)
### Single-Asset Fetch
- Added `GET /api/v1/assets/{asset_id}` to fetch asset metadata and `download_url` by ID.

## Phase 6 — C++ Engine Integration (Pybind11 Bridge)
- Configured **Pybind11** via `CMake` to compile the C++ `engine` and `bindings` modules into a native Python extension
- Implemented `app/core/bridge.py` featuring the `TimelineBuilder` utility to map Pydantic `TimelineIR` models directly to C++ memory structures
- Refactored `app/workers/export_worker.py` to utilize the native `ExportController` and `DummyRenderer` (C++ implementation) for the export pipeline
- Successfully verified the Python-to-C++ memory threshold traversal with `tests/test_native_integration.py`

---

## Phase 5 — Extending AI Tools (Functions)
- Integrated `LiteLLM` Native Tool-Calling mechanism recursively resolving tool executions before generating TimelineIR results
- Configured a Strategy Pattern `ITTSStrategy` dynamically resolving Voiceover generations via `elevenlabs`, `openai`, or `mock` dependencies and API variables
- Exposed `generate_voiceover_track` to the Agent ecosystem saving audio files securely inside `/tmp/assets/audio/`
- Implemented `search_broll` tool to fetch external Video Assets mapping to `Pexels`, `Pixabay`, and `Mock` `IAssetSearchStrategy` providers
- Built `transcribe_media` tool permitting Whisper audio analysis inside `ITranscriptionStrategy` utilizing OpenAI algorithms

---

## Phase 4 — AI Layer & Agent Orchestration
- Integrated `litellm` and `openai` libraries for universal LLM provider support (Ollama, OpenAI, Anthropic)
- Implemented `app/services/ai/strategy.py` using Strategy Pattern for flexible AI model usage
- Built `AgentService` logic matching structural JSON arrays to Timeline mutations and `CommandManager`

---

## Phase 3 — Backend Orchestration & Rendering
- Configured real-time WebSocket connection manager and endpoint for client progress updates
- Implemented `ffmpeg-python` baseline renderer via Celery utilizing the Pipeline Pattern

---

## Phase 2 — Core Domain & Storage
- Configured Alembic migrations with autogenerate against our ORM models
- Implemented ProjectRepository and AssetRepository (PostgreSQL-backed, returns domain objects)
- Built ProjectService with event emission on create
- Implemented 8 undoable timeline commands (AddTrack, RemoveTrack, AddClip, RemoveClip, TrimClip, MoveClip, AddEffect, ChangeSpeed)
- Wired full project CRUD API with DI chain (session → repo → service)
- Built timeline editing REST API with session management and undo/redo endpoints
- Full DI chain in deps.py with type aliases (DbSession, ProjectSvc, etc.)

---

## Phase 1 — Project Scaffold
- Initialized Python project with FastAPI, SQLAlchemy, Celery, Pydantic v2
- Created C++ engine scaffold with CMake (timeline, clip, track, renderer, export headers + implementations)
- Added pybind11 bindings exposing all C++ engine types to Python
- Set up Docker Compose for PostgreSQL 16 and Redis 7
- Defined Pydantic IR schemas (TimelineIR, TrackIR, ClipIR, EffectIR, TransitionIR, ExportSettingsIR)
- Built health check endpoints and OpenAPI docs
- Created architecture documentation with layer rules
