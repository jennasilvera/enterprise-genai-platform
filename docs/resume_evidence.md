# Resume Evidence Matrix

A capability is not resume-ready merely because it is planned.

## Status definitions

- NOT STARTED — no implementation exists
- IMPLEMENTED — code exists but has not been sufficiently tested
- TESTED — automated or integration tests exist
- MEASURED — quantitative evaluation has been performed
- VERIFIED — repository evidence supports the intended claim

---

## Engineering Foundation

### Reproducible Python development environment

Status: VERIFIED

Evidence:

- `pyproject.toml`
- `uv.lock`
- Python 3.12 project constraint
- uv-managed development environment

Supports:

> Built a reproducible Python engineering environment with locked dependencies and automated quality checks.

---

### FastAPI service foundation

Status: VERIFIED

Evidence:

- `src/enterprise_genai/api/main.py`
- `tests/unit/test_health.py`
- `/health/live`
- `/health/ready`
- generated OpenAPI schema

Supports:

> Built a typed FastAPI service with process-level liveness and dependency-aware readiness contracts.

---

### Structured logging foundation

Status: VERIFIED

Evidence:

- `src/enterprise_genai/core/logging.py`
- structured JSON startup/shutdown events

Limitation:

This is a structured logging foundation, not yet full GenAI observability or distributed tracing.

---

### PostgreSQL + pgvector infrastructure

Status: VERIFIED

Evidence:

- `docker-compose.yml`
- `docker/postgres/init.sql`
- PostgreSQL 16 container
- pgvector 0.8.6
- validated pgvector vector-distance operation
- persistent Docker volume
- SQLAlchemy + psycopg connectivity

Supports:

> Provisioned containerized PostgreSQL with pgvector and validated database/vector operations.

Limitation:

No embedding corpus, ANN index, or semantic retrieval benchmark exists yet.

---

### Dependency readiness and failure recovery

Status: VERIFIED

Evidence:

- `src/enterprise_genai/db/session.py`
- `/health/ready`
- readiness returned HTTP 503 during a real PostgreSQL outage
- liveness remained HTTP 200 during the outage
- readiness recovered to HTTP 200 after PostgreSQL restart
- automated healthy/unhealthy readiness tests

Supports:

> Implemented dependency-aware service health checks and graceful PostgreSQL outage/recovery behavior.

---

## Dense Vector Retrieval

Status: NOT STARTED

Evidence:

- None.

---

## BM25 Lexical Retrieval

Status: NOT STARTED

Evidence:

- None.

---

## Hybrid Retrieval

Status: NOT STARTED

Evidence:

- None.

---

## Cross-Encoder Reranking

Status: NOT STARTED

Evidence:

- None.

---

## Graph Retrieval

Status: NOT STARTED

Evidence:

- None.

---

## Structured SQL Reasoning

Status: NOT STARTED

Evidence:

- None.

---

## RAG Generation and Citations

Status: NOT STARTED

Evidence:

- None.

---

## LangGraph Agent Orchestration

Status: NOT STARTED

Evidence:

- None.

---

## Human-in-the-Loop Workflows

Status: NOT STARTED

Evidence:

- None.

---

## Responsible AI Guardrails

Status: NOT STARTED

Evidence:

- None.

---

## Automated GenAI Evaluation Harness

Status: NOT STARTED

Evidence:

- None.

---

## LoRA / PEFT Fine-Tuning

Status: NOT STARTED

Evidence:

- None.

## Phase 4A — BM25 Lexical Retrieval Baseline

**Status:** MEASURED / VERIFIED

Implementation:
- deterministic Unicode-aware lexical tokenizer;
- compound identifier preservation;
- from-scratch BM25 ranker;
- deterministic score tie-breaking;
- evidence-level qrel adapter;
- Recall@k, graded nDCG@k, and canonical reciprocal-rank metrics;
- query-type and split-level benchmark reporting;
- reproducible JSON evaluation artifact.

Verified corpus:
- 80 deterministic `evidence-block-v1` retrieval chunks;
- chunk corpus fingerprint:
  `c4283f4789c83e947634b9d04b0af57f60ba77c2255604ee287cedf40c4900ea`.

Evaluation:
- 24 total evaluation cases;
- 14 standalone retrieval-eligible cases;
- 10 system-level SQL/graph/unanswerable cases excluded from pure-retrieval
  aggregates.

Fixed baseline:
- BM25 `k1=1.5`;
- BM25 `b=0.75`;
- no tuning before first measurement.

Measured retrieval-eligible results:
- canonical MRR: `0.642744`;
- Recall@1: `0.357143`;
- Recall@3: `0.642857`;
- Recall@5: `0.678571`;
- Recall@10: `0.821429`;
- nDCG@1: `0.530612`;
- nDCG@3: `0.602388`;
- nDCG@5: `0.619331`;
- nDCG@10: `0.674342`.

Lexical-query subset:
- canonical MRR: `1.000000`;
- nDCG@1: `1.000000`;
- nDCG@10: `0.972440`.

Reproducibility:
- canonical report:
  `artifacts/evaluation/bm25_baseline.json`;
- report SHA-256:
  `77398447c9a183863c6d2d29ca2fa9a493b418487d0648d378c6f46424e408c3`;
- independent rerun was byte-identical;
- quality gate: `122 passed`.

Observed limitations:
- weak multi-source lexical retrieval;
- evidence text can omit entity metadata useful for query discrimination;
- generic lexical terms can influence rankings;
- semantic seed cases retain meaningful surface-form overlap;
- mixed-tool questions confirm a need for SQL/graph routing rather than
  standalone document retrieval.

Resume-use constraint:
Do not claim dense, hybrid, reranked, or production-scale retrieval from
this milestone. Any improvement percentage must be measured in a later
controlled experiment against this frozen baseline.
