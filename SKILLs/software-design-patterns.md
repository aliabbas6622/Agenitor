---
name: software-design-patterns
description: >
  Apply concrete design patterns to the AI-native video editor codebase.
  Use when designing a new feature, reviewing a PR, or refactoring tangled code.
  Covers patterns specific to media processing, AI pipelines, and real-time UIs.
allowed-tools:
  - read_file
  - write_file
  - search_codebase
---

# Software Design Patterns Skill

## When to Use
- A component is doing more than one thing (God object smell)
- AI model calls are scattered across multiple layers
- UI is tightly coupled to backend data shapes
- Adding a new effect/filter requires modifying 4+ files
- State management is unpredictable or hard to trace

## Pattern Catalogue (Video Editor Specific)

---

### Pattern 1 — Command Pattern (Timeline Operations)
**Use for:** Every user action that mutates the timeline (cut, trim, add clip, apply effect)
```typescript
// src/core/commands/base.command.ts
export interface Command {
  execute(): Promise<void>;
  undo(): Promise<void>;
  description: string;
}

// src/core/commands/trim-clip.command.ts
export class TrimClipCommand implements Command {
  description = 'Trim clip';
  private previousDuration: number;

  constructor(
    private clipId: string,
    private newDuration: number,
    private timeline: TimelineStore,
  ) {}

  async execute() {
    const clip = this.timeline.getClip(this.clipId);
    this.previousDuration = clip.duration;     // snapshot for undo
    this.timeline.updateClip(this.clipId, { duration: this.newDuration });
  }

  async undo() {
    this.timeline.updateClip(this.clipId, { duration: this.previousDuration });
  }
}

// Usage in command manager (maintains undo stack)
await commandManager.execute(new TrimClipCommand(id, duration, timeline));
```

**Rule:** Every timeline mutation goes through a Command. No direct state mutation from UI handlers.

---

### Pattern 2 — Strategy Pattern (AI Provider Abstraction)
**Use for:** Swappable AI backends (OpenAI, local model, Anthropic, custom)
```typescript
// src/services/ai/strategy.interface.ts
export interface AITranscriptionStrategy {
  transcribe(audioPath: string): Promise<Transcript>;
  isAvailable(): Promise<boolean>;
}

// src/services/ai/strategies/whisper-local.strategy.ts
export class WhisperLocalStrategy implements AITranscriptionStrategy {
  async transcribe(audioPath: string) {
    // calls local whisper subprocess
  }
  async isAvailable() {
    return checkBinaryExists('whisper');
  }
}

// src/services/ai/transcription.service.ts
export class TranscriptionService {
  constructor(private strategy: AITranscriptionStrategy) {}

  async run(audioPath: string) {
    if (!await this.strategy.isAvailable()) {
      throw new Error('Transcription strategy unavailable');
    }
    return this.strategy.transcribe(audioPath);
  }
}

// Inject strategy based on env
const strategy = process.env.WHISPER_LOCAL === 'true'
  ? new WhisperLocalStrategy()
  : new OpenAIWhisperStrategy(process.env.OPENAI_KEY);
```

---

### Pattern 3 — Observer / Event Bus (Cross-Module Sync)
**Use for:** Timeline changes that need to trigger multiple independent reactions (auto-save, AI re-analysis, thumbnail regen)
```typescript
// src/lib/event-bus.ts
import EventEmitter from 'eventemitter3';
export const editorEvents = new EventEmitter();

// Emitter (timeline store)
editorEvents.emit('clip:trimmed', { clipId, newDuration, projectId });

// Listener 1 — auto-save
editorEvents.on('clip:trimmed', ({ projectId }) => autoSave(projectId));

// Listener 2 — thumbnail regeneration
editorEvents.on('clip:trimmed', ({ clipId }) => queueThumbnailRegen(clipId));

// Listener 3 — AI re-analysis
editorEvents.on('clip:trimmed', ({ projectId }) => {
  if (aiAnalysisEnabled) aiAnalysisQueue.add({ projectId });
});
```

**Rule:** Events are named `<entity>:<past-tense-verb>`. No future tense. No generic names like `update`.

---

### Pattern 4 — Repository Pattern (Data Access)
**Use for:** All database or storage access
```typescript
// src/repositories/project.repository.ts
export interface IProjectRepository {
  findById(id: string): Promise<Project | null>;
  save(project: Project): Promise<void>;
  delete(id: string): Promise<void>;
  listByUser(userId: string): Promise<ProjectSummary[]>;
}

// Concrete implementation (swap DB without changing service layer)
export class PostgresProjectRepository implements IProjectRepository {
  async findById(id: string) {
    return db.query.projects.findFirst({ where: eq(projects.id, id) });
  }
  // ...
}
```

---

### Pattern 5 — Pipeline Pattern (Export/Render)
**Use for:** Multi-stage processing where each stage has clear input/output
```typescript
// src/workers/export/pipeline.ts
type PipelineStage<TIn, TOut> = (input: TIn, ctx: PipelineContext) => Promise<TOut>;

const exportPipeline = createPipeline([
  validateProjectStage,       // Project → ValidatedProject
  resolveAssetsStage,         // ValidatedProject → ResolvedAssets
  renderSegmentsStage,        // ResolvedAssets → RenderedSegments
  concatenateStage,           // RenderedSegments → SingleFile
  uploadToStorageStage,       // SingleFile → StorageURL
]);

// Each stage is independently testable, replaceable, and loggable
await exportPipeline.run(projectId, { onProgress: job.updateProgress });
```

## Applying a Pattern — Decision Guide

| Symptom | Apply Pattern |
|---|---|
| UI directly mutates timeline | Command |
| AI provider hardcoded | Strategy |
| Module A calls Module B calls Module C for one action | Event Bus |
| Services call DB directly | Repository |
| Worker function is 300+ lines | Pipeline |

## Constraints
- Never use Singleton for anything that has external state (DB, ML model) — use DI instead
- Repositories must return domain objects, not raw DB rows
- Event names must be documented in `./docs/events.md`
- Pipelines must log each stage duration to support performance profiling