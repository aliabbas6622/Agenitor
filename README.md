# AI-Native Video Editor

**An AI-native video editor where AI agents autonomously create, edit, and optimize videos.**

## Architecture

| Layer | Language | Purpose |
|-------|----------|---------|
| **Core Engine** | C++ | Timeline data structures, rendering pipeline, video processing |
| **AI Orchestration** | Python | FastAPI backend, Celery workers, AI strategies, IR schemas |
| **Bridge** | pybind11 | Zero-copy data sharing between C++ engine and Python |

## Quick Start

### Prerequisites
- Python 3.12+
- Docker & Docker Compose
- CMake 3.20+ and a C++20 compiler (for engine)

### 1. Infrastructure
```bash
docker compose up -d
```

### 2. Python Backend
```bash
# Install dependencies
pip install -e ".[dev]"

# Copy environment config
cp .env.example .env

# Run the API server
uvicorn app.main:app --reload --port 8000
```

### 3. C++ Engine (optional for Phase 1)
```bash
cd engine
cmake -B build -DCMAKE_BUILD_TYPE=Debug
cmake --build build
```

### 4. Run Tests
```bash
pytest tests/ -v
```

## Project Structure

```
editor/
├── app/           # Python AI orchestration (FastAPI + Celery)
├── engine/        # C++ core engine (timeline, rendering)
├── bindings/      # pybind11 Python ↔ C++ bridge
├── docs/          # Architecture documentation
├── tests/         # Python test suite
├── SKILLs/        # AI skill definitions
└── Work/          # Project documentation
```

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Basic health check |
| GET | `/health/detailed` | Infrastructure health |
| GET | `/api/v1/projects` | List projects |
| POST | `/api/v1/projects` | Create project |
