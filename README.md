# Enterprise GenAI Retrieval, Agent & Evaluation Platform

A production-oriented enterprise decision-support platform being built to study,
implement, and evaluate retrieval, agentic workflows, Responsible AI,
fine-tuning, and production GenAI engineering.

The project is being developed incrementally. Capabilities are only described as
implemented after working code, tests, or measurements provide repository
evidence for the claim.

## Current Milestone

**Phase 1 — Engineering Foundation**

The current milestone establishes the reproducible application and data-system
foundation required for later retrieval, RAG, agentic, evaluation, and
fine-tuning work.

## Verified Capabilities

- Python 3.12 project environment managed with `uv`
- reproducible dependency locking with `uv.lock`
- FastAPI application
- typed environment configuration with Pydantic Settings
- structured JSON logging foundation
- Docker Desktop + WSL2 integration
- Docker Compose service orchestration
- PostgreSQL 16
- pgvector 0.8.6
- validated pgvector vector-distance operations
- persistent PostgreSQL storage
- SQLAlchemy + psycopg database connectivity
- process-level liveness checks
- dependency-aware readiness checks
- graceful database outage and recovery behavior
- Ruff linting and formatting
- pytest automated tests
- warning-clean FastAPI/Starlette test client configuration

## Architecture at the Current Milestone

```text
                 Client
                   |
                   v
              +---------+
              | FastAPI |
              +----+----+
                   |
        +----------+-----------+
        |                      |
        v                      v
 /health/live            /health/ready
                               |
                               v
                         SQLAlchemy
                               |
                               v
                         PostgreSQL 16
                               |
                               v
                          pgvector
```

This is only the Phase 1 architecture. Retrieval, generation, agents, graph
reasoning, evaluation, and model-training components will be introduced in later
milestones only when their business and technical requirements are established.

## Health Endpoints

### Liveness

```text
GET /health/live
```

Answers whether the API process itself is alive.

Example response:

```json
{
  "status": "ok",
  "service": "enterprise-genai-platform",
  "environment": "dev"
}
```

A database outage does not cause the liveness endpoint to fail because the API
process may still be functioning correctly.

### Readiness

```text
GET /health/ready
```

Answers whether the service's required database infrastructure is currently
usable.

When PostgreSQL and pgvector are available:

```json
{
  "status": "ready",
  "database": "ok"
}
```

The endpoint returns HTTP `200`.

When PostgreSQL is unavailable:

```json
{
  "status": "not_ready",
  "database": "unavailable"
}
```

The endpoint returns HTTP `503 Service Unavailable`.

This distinction allows process health and dependency health to be monitored
independently.

## Database Foundation

The local development database runs in Docker using:

```text
PostgreSQL 16
pgvector 0.8.6
```

The pgvector extension is enabled during database initialization.

A real vector-distance operation has been verified in PostgreSQL:

```sql
SELECT '[1,2,3]'::vector <-> '[4,5,6]'::vector AS l2_distance;
```

The result is:

```text
5.196152422706632
```

which corresponds to the Euclidean distance:

```text
sqrt((1 - 4)^2 + (2 - 5)^2 + (3 - 6)^2)
= sqrt(27)
≈ 5.196152
```

This verifies the vector datatype and pgvector distance operator.

It does **not** yet constitute semantic retrieval. Embeddings, vector indexes,
nearest-neighbor retrieval, and retrieval evaluation will be implemented in
later milestones.

## Failure and Recovery Behavior

The following behavior has been tested against the real running services:

```text
PostgreSQL running
    /health/live   -> HTTP 200
    /health/ready  -> HTTP 200

PostgreSQL stopped
    /health/live   -> HTTP 200
    /health/ready  -> HTTP 503

PostgreSQL restarted
    /health/ready  -> HTTP 200
```

This verifies that the application can distinguish between process availability
and dependency readiness and can recover after a database interruption.

## Local Development

### Prerequisites

- WSL2
- Python 3.12
- `uv`
- Docker Desktop with WSL integration
- Docker Compose

### Create or synchronize the environment

```bash
uv sync
```

### Start PostgreSQL

```bash
docker compose up -d postgres
```

Check service status:

```bash
docker compose ps
```

### Run the API

```bash
uv run uvicorn enterprise_genai.api.main:app \
  --host 127.0.0.1 \
  --port 8000
```

### Check liveness

```bash
curl -i http://127.0.0.1:8000/health/live
```

### Check readiness

```bash
curl -i http://127.0.0.1:8000/health/ready
```

### OpenAPI schema

```text
http://127.0.0.1:8000/openapi.json
```

## Quality Gates

Run linting:

```bash
uv run ruff check .
```

Check formatting:

```bash
uv run ruff format --check .
```

Run tests:

```bash
uv run pytest -q \
  -W error::starlette.exceptions.StarletteDeprecationWarning
```

## Configuration

Local configuration is loaded from environment variables.

The repository contains:

```text
.env.example
```

for documented development defaults.

The actual:

```text
.env
```

file is ignored by Git and must not be committed.

## Current Repository Scope

Phase 1 provides engineering infrastructure only.

The repository does **not yet** contain:

- enterprise document ingestion
- document parsing and normalization
- chunking experiments
- embedding generation
- dense vector retrieval
- HNSW or IVFFlat indexes
- BM25 lexical retrieval
- hybrid retrieval
- Reciprocal Rank Fusion
- cross-encoder reranking
- graph retrieval
- structured enterprise dataset
- SQL reasoning tools
- RAG generation
- grounded citations
- context engineering
- LangGraph agent orchestration
- tool/function calling
- persistent workflow state
- human-in-the-loop approval workflows
- prompt-injection defenses
- Responsible AI guardrails
- GenAI evaluation benchmarks
- retrieval precision/recall measurements
- generation evaluation
- agent evaluation
- latency or throughput benchmarks
- LoRA / PEFT fine-tuning
- gRPC services

These capabilities will only move into the verified-capabilities section after
they have been implemented and supported by appropriate tests or measurements.

## Evidence Policy

The project maintains:

```text
docs/resume_evidence.md
```

to map potential resume claims to concrete repository evidence.

A capability is tracked using the following statuses:

```text
NOT STARTED
IMPLEMENTED
TESTED
MEASURED
VERIFIED
```

No retrieval-quality, model-quality, hallucination, latency, throughput, cost,
or performance metric will be reported without running the corresponding
experiment.

## Project Goal

The finished system is intended to become a technically serious enterprise
GenAI decision-support platform spanning:

```text
structured + unstructured enterprise data
                  |
                  v
        lexical + dense retrieval
                  |
                  v
             hybrid fusion
                  |
                  v
              reranking
                  |
                  v
        graph + SQL reasoning
                  |
                  v
        agentic orchestration
                  |
                  v
       grounded RAG generation
                  |
                  v
       guardrails + HITL
                  |
                  v
       evaluation + observability
```

The final standard is not whether the repository contains impressive AI
terminology. The standard is whether each claimed capability is implemented,
testable, measurable where appropriate, reproducible, and defensible in a
technical interview.
