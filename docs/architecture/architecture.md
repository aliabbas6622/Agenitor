# System Architecture — AI-Native Video Editor

> Last updated: 2026-04-02

## Overview

A dual-language video editing platform designed for AI agents. The C++ engine handles all performance-critical operations (timeline manipulation, rendering, codec work), while Python handles AI orchestration, business logic, and API serving.

## Layer Diagram

```
┌─────────────────────────────────────────────────────────┐
│                    API Layer (FastAPI)                   │
│              REST + WebSocket endpoints                  │
├─────────────────────────────────────────────────────────┤
│                  Services Layer (Python)                 │
│        Business logic, AI strategies, job mgmt          │
├───────────────────────┬─────────────────────────────────┤
│  Repositories (Python)│    Workers (Celery)              │
│  Data access via ORM  │    Background processing         │
├───────────────────────┴─────────────────────────────────┤
│               pybind11 Bridge Layer                      │
│         Zero-copy Python ↔ C++ communication            │
├─────────────────────────────────────────────────────────┤
│               C++ Core Engine                            │
│   Timeline │ Clip │ Track │ Renderer │ ExportController  │
├─────────────────────────────────────────────────────────┤
│              Infrastructure                              │
│       PostgreSQL │ Redis │ FFmpeg │ File System          │
└─────────────────────────────────────────────────────────┘
```

## Layer Rules (Strict)

| Layer | May Import | Must Never Import |
|-------|-----------|-------------------|
| `api/` | `services/`, `schemas/` | `db/`, `core/`, `workers/` |
| `services/` | `repositories/`, `core/`, `schemas/` | `api/`, `db/` directly |
| `repositories/` | `db/` | `api/`, `services/` |
| `workers/` | `services/`, `core/` | `api/` |
| `core/` | Nothing external | `api/`, `db/`, `workers/` |

## Communication Patterns

| Scenario | Pattern |
|----------|---------|
| Real-time UI update | WebSocket + Event Bus |
| Long job (export, render, AI gen) | Celery queue + progress polling |
| Fast read (clip metadata) | In-memory / Redis cache |
| Cross-service data | REST with Pydantic DTOs |
| AI model call | Strategy Pattern → Celery worker |
| Timeline mutation | Command Pattern (undo/redo) |

## Design Patterns In Use

1. **Command Pattern** — All timeline mutations (supports undo/redo)
2. **Strategy Pattern** — Swappable AI backends
3. **Observer / Event Bus** — Cross-module reactivity
4. **Repository Pattern** — Data access abstraction
5. **Pipeline Pattern** — Multi-stage export rendering

## Intermediate Representation (IR)

The IR is the universal format between AI decisions and the engine:

```
TimelineIR
├── TrackIR[]
│   ├── ClipIR[]
│   │   ├── EffectIR[]
│   │   ├── TransitionIR (in/out)
│   │   ├── source_path, position, in/out points
│   │   └── volume, playback_speed
│   ├── type (video/audio/subtitle)
│   └── muted, locked, opacity
└── ExportSettingsIR
    └── format, resolution, codec, frame_rate, bitrate
```
