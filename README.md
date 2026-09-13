# Enterprise GenAI Retrieval, Agent & Evaluation Platform

A production-oriented enterprise decision-support platform for implementing and
evaluating retrieval, bounded agentic execution, grounded generation,
observability, and serving architecture.

The repository is developed incrementally. Capabilities are described as
implemented, measured, verified, or frozen only after corresponding code,
tests, experiments, or reproducible repository evidence exist.

## Current Milestone

**Phase 11 — Application Serving, Observability, and gRPC Retrieval Integration**

The repository is complete through:

**Phase 11E2 — gRPC Dependency Readiness Semantics**

Phase 11 established the application-serving layer on top of the previously
frozen retrieval, execution, orchestration, evidence, and generation
components.

The current serving architecture includes:

- a typed application answering boundary;
- bounded answer specifications;
- a grounded answering application service;
- FastAPI answer transport;
- managed application startup and shutdown;
- privacy-safe HTTP request observability;
- application-stage answering observability;
- bounded process-local operational metrics;
- a measured localhost serving-latency protocol and confirmation;
- a versioned gRPC retrieval contract;
- a gRPC servicer adapter;
- a gRPC retrieval client executor;
- a verified real localhost gRPC retrieval boundary;
- opt-in application integration of the gRPC retrieval executor;
- fail-closed required-retrieval failure semantics;
- bounded startup reachability gating for the configured gRPC dependency.

Local retrieval remains the default serving mode.

## Verified Capability Areas

### Data and persistence

- Python 3.12 environment managed with `uv`
- reproducible dependency locking with `uv.lock`
- PostgreSQL 16
- pgvector 0.8.6
- SQLAlchemy + psycopg
- versioned relational schema
- deterministic structured-data ingestion
- immutable document provenance ingestion
- deterministic provenance-aware chunking
- synthetic Northstar Capital enterprise ground truth

### Retrieval

- BM25 lexical retrieval
- dense retrieval
- dense-representation ablation
- hybrid Reciprocal Rank Fusion
- frozen hybrid test confirmation
- cross-encoder reranking
- persisted frozen retrieval execution

### Tool routing and execution

- deterministic heuristic routing
- pretrained NLI routing evaluation
- PEFT/LoRA supervised routing evaluation
- typed tool-execution contracts
- structured SQL execution
- relational graph execution
- multi-tool execution coordination

### Agentic orchestration and evidence

- bounded LangGraph runtime
- mixed-tool orchestration
- execution-evidence normalization
- deterministic evidence sufficiency
- explicit abstention semantics
- typed grounded-answer contracts
- provenance-preserving synthesis

### Generation

- grounded-generation authority boundary
- pinned local causal-LM provider
- guarded generation with deterministic fallback
- mechanical generation-comparison protocol and scorer
- frozen generation-comparison confirmation

### Application serving and operations

- FastAPI grounded-answer endpoint
- application lifespan ownership of expensive serving resources
- process liveness and dependency-aware readiness
- privacy-safe request observability
- answering-stage observability
- process-local operational metrics
- measured localhost serving latency
- opt-in gRPC retrieval backend
- fail-closed runtime handling of required retrieval failures
- bounded gRPC dependency reachability checking during application startup

Detailed implementation evidence and claim boundaries are maintained in:

```text
docs/resume_evidence.md
```

## Current Architecture

```text
                              Client
                                |
                                v
                         +-------------+
                         |   FastAPI   |
                         +------+------+
                                |
                   +------------+------------+
                   |                         |
                   v                         v
            /health/live              /health/ready
                                             |
                                             |
                                database + answering
                                      readiness
                                             |
                                             v
                              GroundedAnsweringService
                                             |
                                             v
                           Bounded Answer Specification
                                             |
                                             v
                         RequestScopedExecutionRuntime
                             /        |         \
                            /         |          \
                           v          v           v
                     Retrieval      SQL        Graph
                        |
              +---------+----------+
              |                    |
              v                    v
        Local frozen          gRPC-backed
        hybrid retrieval      retrieval executor
                                   |
                                   v
                          versioned gRPC contract
                                   |
                                   v
                         RetrievalGrpcServicer

        execution results
               |
               v
      evidence normalization
               |
               v
     deterministic sufficiency
               |
        +------+------+
        |             |
        v             v
   grounded       deterministic
   generation      abstention
        |
        v
 typed grounded answer
```

This is deliberately a modular application with one meaningful gRPC retrieval
boundary.

The repository does **not** claim a general microservices architecture.

## Serving Modes

The application supports two retrieval modes.

### Local retrieval

Default:

```text
RETRIEVAL_MODE=local
```

The serving assembly uses the persisted frozen hybrid retriever and retains the
existing local retrieval behavior.

### gRPC retrieval

Opt-in:

```text
RETRIEVAL_MODE=grpc
RETRIEVAL_GRPC_TARGET=127.0.0.1:50051
```

When gRPC mode is enabled, application startup:

1. creates one gRPC channel;
2. waits for that channel to become reachable within a bounded startup timeout;
3. constructs the generated retrieval stub;
4. constructs `GrpcRetrievalExecutor`;
5. injects that executor into the existing serving assembly.

If the configured endpoint does not become reachable within the startup
timeout, answering is marked unavailable and the answering service is not
installed.

This startup check establishes transport/channel reachability only. It is not
continuous runtime health polling and does not itself invoke a semantic
retrieval RPC.

## Health Endpoints

### Liveness

```text
GET /health/live
```

Example:

```json
{
  "status": "ok",
  "service": "enterprise-genai-platform",
  "environment": "dev"
}
```

Liveness reports whether the API process itself is alive.

A database or answering dependency failure does not make process liveness fail.

### Readiness

```text
GET /health/ready
```

Readiness reports:

- overall application readiness;
- database readiness;
- answering-service state.

With a healthy database and answering disabled:

```json
{
  "status": "ready",
  "database": "ok",
  "answering": "disabled"
}
```

With a healthy database and successfully initialized answering service:

```json
{
  "status": "ready",
  "database": "ok",
  "answering": "ready"
}
```

If a required dependency prevents answering initialization:

```json
{
  "status": "not_ready",
  "database": "ok",
  "answering": "unavailable"
}
```

the endpoint returns:

```text
HTTP 503 Service Unavailable
```

A database outage also makes readiness fail while process liveness remains
independent.

The readiness endpoint does not continuously poll the gRPC dependency.
For gRPC serving, it reflects the answering state established during startup.

## Answer Endpoint

When answering has been successfully initialized:

```text
POST /answer
```

routes a bounded request through the existing grounded-answering service,
request-scoped execution runtime, evidence/sufficiency policies, and synthesis
boundary.

When answering is unavailable, the endpoint fails closed with HTTP `503`
instead of silently falling back to another retrieval mode.

Required-tool execution failures that occur after successful startup remain
governed by the frozen fail-closed execution semantics and can produce a typed
deterministic abstention rather than an unsupported answer.

## Configuration

Application configuration is loaded through Pydantic Settings.

Relevant environment variables include:

```text
APP_NAME
ENVIRONMENT
LOG_LEVEL

ANSWERING_ENABLED

RETRIEVAL_MODE
RETRIEVAL_GRPC_TARGET
RETRIEVAL_GRPC_DEADLINE_SECONDS
RETRIEVAL_GRPC_STARTUP_TIMEOUT_SECONDS

DATABASE_URL
```

### gRPC timeout semantics

`RETRIEVAL_GRPC_DEADLINE_SECONDS`

bounds an actual retrieval RPC.

`RETRIEVAL_GRPC_STARTUP_TIMEOUT_SECONDS`

bounds the startup wait for the configured gRPC channel to become reachable.

These are independent settings and both must be finite and greater than zero.

## Local Development

### Prerequisites

- WSL2 (verified local development environment)
- Python 3.12
- `uv`
- Docker
- Docker Compose

The checked project configuration uses the CPU PyTorch package index.

### Synchronize the environment

```bash
uv sync
```

### Start PostgreSQL

```bash
docker compose up -d postgres
```

Check database container status:

```bash
docker compose ps
```

### Run the API

The default configuration leaves answering disabled:

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

## Database Foundation

Local PostgreSQL development uses:

```text
PostgreSQL 16
pgvector 0.8.6
```

The database is managed by Docker Compose and uses a persistent named volume.

The repository has progressed beyond the original pgvector connectivity
foundation: the persisted enterprise corpus now supports the frozen retrieval,
structured SQL, graph, orchestration, and answering workflows described in the
evidence matrix.

## Quality Gates

Run the full test suite:

```bash
uv run pytest -q
```

Run linting:

```bash
uv run ruff check .
```

Check formatting:

```bash
uv run ruff format --check .
```

Check Git whitespace errors:

```bash
git diff --check
```

Milestone-specific confirmations and immutable evidence artifacts are retained
under the repository's evaluation and artifact directories.

## Evidence and Reproducibility Policy

The project maintains:

```text
docs/resume_evidence.md
```

to map technical claims to concrete repository evidence.

Capability states distinguish among:

```text
NOT STARTED
IMPLEMENTED
TESTED
MEASURED
VERIFIED
FROZEN
```

Performance or quality claims are not reported without the corresponding
experiment or measurement.

Historical milestone tags preserve the code and evidence associated with
verified phases.

## Current Claim Boundaries

The repository does not currently establish:

- TLS for the gRPC retrieval boundary;
- authentication or authorization for the gRPC retrieval boundary;
- service discovery;
- remote-host deployment behavior;
- independently supervised retrieval-service processes;
- containerized retrieval-service deployment;
- continuous runtime gRPC dependency polling;
- automatic gRPC retry or backoff policy;
- circuit breaking;
- automatic fallback from gRPC retrieval to local retrieval;
- automatic recovery semantics when a failed retrieval service returns;
- production SLOs;
- production-scale latency or throughput;
- production-scale fault tolerance;
- Kubernetes deployment semantics;
- a microservices architecture.

The verified gRPC confirmations use real localhost TCP/gRPC transport where
explicitly documented.

## Project Standard

The goal is not to accumulate AI terminology or infrastructure for its own
sake.

A capability belongs in the repository's verified surface only when its
implementation and evidence make the claim reproducible and defensible in a
technical interview.
