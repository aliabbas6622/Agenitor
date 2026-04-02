---
name: backend-orchestration
description: >
  Orchestrate backend services for the AI-native video editor: job queues,
  worker coordination, inter-service communication, and failure recovery.
  Use when implementing or debugging any async workflow involving AI inference,
  rendering, or export pipelines.
allowed-tools:
  - bash
  - read_file
  - write_file
  - search_codebase
---

# Backend Orchestration Skill

## When to Use
- Implementing any feature involving a job queue (export, render, AI generation)
- Debugging a stuck or failing background worker
- Adding a new worker type or scaling an existing one
- Designing retry/failure strategies for flaky operations (model timeouts, ffmpeg crashes)

## Stack Assumptions
- Runtime: Node.js (TypeScript) or Python (FastAPI)
- Queue: BullMQ (Redis-backed)
- Workers: Separate processes (`workers/` directory)
- IPC for ML: Python subprocess or gRPC
- Storage: Local disk (dev) / S3-compatible (prod)

## Workflow

### Step 1 — Identify the Job Boundary
Ask: what is the smallest unit of work that must be atomic?
- Export job: entire export pipeline (not per-frame)
- AI suggestion: one prompt → one result set
- Render: per-segment (allows partial resume)

Define the job payload type in `src/types/jobs.ts`:
```typescript
export type ExportJobPayload = {
  jobId: string;          // UUID
  projectId: string;
  outputFormat: 'mp4' | 'webm' | 'mov';
  resolution: '720p' | '1080p' | '4k';
  userId: string;
  requestedAt: string;    // ISO timestamp
};
```

### Step 2 — Register the Queue
```typescript
// src/queues/<job-name>.queue.ts
import { Queue } from 'bullmq';
import { redis } from '../lib/redis';

export const exportQueue = new Queue('video-export', {
  connection: redis,
  defaultJobOptions: {
    attempts: 3,
    backoff: { type: 'exponential', delay: 5000 },
    removeOnComplete: { count: 100 },
    removeOnFail: { count: 500 },
  },
});
```

### Step 3 — Implement the Worker
```typescript
// workers/export.worker.ts
import { Worker } from 'bullmq';

const worker = new Worker('video-export', async (job) => {
  const { projectId, outputFormat } = job.data as ExportJobPayload;

  await job.updateProgress(5);
  const timeline = await loadTimeline(projectId);

  await job.updateProgress(20);
  const tempPath = await renderSegments(timeline); // calls ffmpeg

  await job.updateProgress(80);
  await uploadToStorage(tempPath, job.data.jobId);

  await job.updateProgress(100);
  return { outputUrl: getPublicUrl(job.data.jobId) };
}, {
  connection: redis,
  concurrency: 2,              // max 2 export jobs in parallel per worker
  limiter: { max: 10, duration: 60_000 },
});

worker.on('failed', (job, err) => {
  console.error(`[export-worker] job ${job?.id} failed:`, err.message);
  // TODO: emit failure event to WebSocket so UI can show error
});
```

### Step 4 — Expose Job Status via WebSocket
```typescript
// On job enqueue, return jobId to client
// Client subscribes: ws.send({ type: 'subscribe', jobId })

// In WebSocket handler:
queue.on('progress', (job, progress) => {
  broadcastToUser(job.data.userId, {
    type: 'job:progress',
    jobId: job.id,
    progress,
  });
});
```

### Step 5 — Handle Failures Explicitly
For each worker, define:

| Failure Type | Strategy |
|---|---|
| ffmpeg crash (exit code != 0) | Retry up to 3x, then mark failed |
| ML model timeout (>30s) | Cancel subprocess, retry once, then fail |
| S3 upload failure | Retry with exponential backoff (max 5x) |
| Corrupt input file | Fail immediately, no retry, notify user |

Implement in worker:
```typescript
if (err.code === 'INVALID_INPUT') {
  throw new UnrecoverableError('Corrupt input: ' + err.message);
  // BullMQ will not retry UnrecoverableError
}
```

### Step 6 — Local Development Setup
```bash
# Terminal 1: Redis
docker run -p 6379:6379 redis:7-alpine

# Terminal 2: API server
pnpm dev:api

# Terminal 3: Workers (hot reload)
pnpm dev:workers

# Monitor queues
npx @bull-board/cli --redis-url redis://localhost:6379
```

### Step 7 — Health Check Endpoint
```typescript
// GET /health/workers
const counts = await exportQueue.getJobCounts();
res.json({
  status: counts.failed > 50 ? 'degraded' : 'ok',
  queues: { export: counts },
});
```

## Inputs
- Job payload type definition
- Feature spec for the async operation
- Redis connection config (`REDIS_URL` env var)

## Outputs
- `src/queues/<name>.queue.ts`
- `workers/<name>.worker.ts`
- Updated `src/types/jobs.ts`
- Health check endpoint

## Constraints
- Workers must never import from `src/api/` — no circular dependency
- Every job must emit progress events (at minimum: start, midpoint, done)
- Max worker concurrency: 2 per CPU core for CPU-bound tasks (ffmpeg), 10 for I/O-bound
- All job payloads must be serializable JSON — no class instances, no Buffers inline
- Timeouts must be set on every external call (ML, ffmpeg, S3)