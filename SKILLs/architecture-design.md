---
name: architecture-design
description: >
  Design and validate the system architecture for the AI-native video editor.
  Use when starting a new subsystem, refactoring a module boundary, or making
  decisions about service decomposition, data flow, or storage strategy.
allowed-tools:
  - read_file
  - write_file
  - bash
  - search_codebase
---

# Architecture Design Skill

## When to Use
- Initializing a new subsystem (e.g., timeline engine, AI inference pipeline, export service)
- When a module exceeds 800 LOC and needs decomposition
- When adding a new external integration (GPU service, cloud storage, ML model API)
- When data flow between two systems is undefined or ambiguous

## Workflow

### Step 1 — Audit Existing Structure
```bash
find ./src -type d | sort
cat ./docs/architecture.md 2>/dev/null || echo "No architecture doc found"
```
Read `src/` directory tree. Identify existing layers:
- `core/` — domain logic (timeline, clip, track, effect)
- `services/` — AI inference, export, render
- `api/` — REST/WebSocket handlers
- `workers/` — background jobs (ffmpeg, model inference)

### Step 2 — Define the Module Contract
Before writing any code, produce a contract file:
```bash
mkdir -p ./docs/architecture
touch ./docs/architecture/<module-name>.contract.md
```

Contract must contain:
```markdown
## Module: <name>
### Responsibilities (max 3)
1. ...
### Public Interface
- Inputs: { type, schema }
- Outputs: { type, schema }
- Side Effects: none | [list]
### Dependencies
- Allowed: [list of modules this can import]
- Forbidden: [modules this must never import — enforce layering]
### Storage
- Reads from: ...
- Writes to: ...
```

### Step 3 — Choose Communication Pattern
Decision tree (apply strictly):

| Scenario | Pattern |
|---|---|
| Real-time UI update (timeline scrub, playhead) | WebSocket / event bus |
| Long job (export, render, AI generation) | Job queue (BullMQ) + polling |
| Fast read (clip metadata, project state) | In-memory store (Zustand / Redis) |
| Cross-service data | REST with typed DTOs |
| ML model call | gRPC or direct Python subprocess via IPC |

### Step 4 — Draw the Data Flow (ASCII is fine)
Write to `./docs/architecture/<module-name>.flow.md`:
```
[User Action] → [API Layer] → [Service] → [Worker/Model] → [Event Bus] → [UI]
```
Every arrow must have a named payload type. No "data" or "object" — be explicit.

### Step 5 — Validate Against Rules
Run this checklist before finalizing:
- [ ] No circular imports between layers
- [ ] No domain logic in API handlers
- [ ] No direct DB calls from `core/` — only through repository interfaces
- [ ] All AI calls are async and cancellable
- [ ] File I/O only in `workers/` or `services/`

### Step 6 — Update Root Architecture Doc
```bash
echo "\n## <module-name> — $(date +%Y-%m-%d)" >> ./docs/architecture.md
# Append 3-line summary of the decision made
```

## Inputs
- Existing codebase structure
- Feature requirement or bug report triggering this skill
- `./docs/architecture.md` (if exists)

## Outputs
- `./docs/architecture/<module-name>.contract.md`
- `./docs/architecture/<module-name>.flow.md`
- Updated `./docs/architecture.md`

## Constraints
- A module may only import from layers below it (strict layering — no skipping)
- AI inference must never block the main thread or event loop
- No module should own more than one of: storage, compute, or UI state
- Architecture decisions must be written down before implementation begins

## Example
Feature: "Add AI-generated B-roll suggestions"
- New module: `services/ai-broll`
- Contract: input = `{ transcript: string, projectId: string }`, output = `{ clips: BRollSuggestion[] }`
- Pattern: Job queue (heavy ML call), result pushed via WebSocket
- Dependencies: allowed = `[core/clip, workers/model-runner]`, forbidden = `[api/, ui/]`