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

## Phase 4B — BM25 Lexical Representation Ablation

**Status:** MEASURED / DEVELOPMENT-VERIFIED

Controlled variables:
- `bm25-v1` unchanged;
- `lexical-tokenizer-v1` unchanged;
- BM25 `k1=1.5`, `b=0.75` unchanged;
- `evidence-block-v1` chunks unchanged;
- 10 development retrieval cases used for representation selection;
- test cases excluded from representation selection.

Preregistered representations:
- `text-only-v1`;
- `company-text-v1`;
- `document-context-text-v1`.

Preregistered development winner:
- `document-context-text-v1`;
- canonical MRR: `0.709091`;
- Recall@10: `0.800000`;
- nDCG@10: `0.712286`;
- lexical rank-1 guardrail: PASS.

Frozen text-only development reference:
- canonical MRR: `0.633175`;
- Recall@10: `0.800000`;
- nDCG@10: `0.657312`.

Post-hoc decomposition:
- `document-title-text-v1`:
  canonical MRR `0.659091`,
  Recall@10 `0.800000`,
  nDCG@10 `0.677258`;
- `evidence-heading-text-v1`:
  canonical MRR `0.716286`,
  Recall@10 `0.800000`,
  nDCG@10 `0.697781`.

Follow-on representation:
- `document-title-text-v1`.

Reason for follow-on selection:
- legitimate source-level metadata;
- measurable development improvement over text-only retrieval;
- preserved lexical rank-1 behavior;
- cleaner attribution than synthetic evidence-heading enrichment.

Development nDCG@10 change for selected follow-on representation:
- absolute: `+0.019946`;
- relative: approximately `+3.03%`.

Known limitation:
- Q-0017 remains outside Recall@10;
- title-plus-text places its two canonical evidence blocks at ranks 11 and 14;
- further lexical tuning is not assumed to be the correct solution.

Resume-use constraint:
Any percentage must be described as a development-set result on the synthetic
Northstar benchmark. Do not claim test-set, production, dense, hybrid, or
reranker improvement from this phase.

## Phase 4C — BM25 Representation Test Confirmation

**Status:** MEASURED / TEST-CONFIRMED

Frozen before confirmation:
- Phase 4B commit:
  `d767c3775b8c7de1a024d6dcff3799f6bbe11fc5`;
- representation: `document-title-text-v1`;
- tokenizer: `lexical-tokenizer-v1`;
- BM25: `bm25-v1`;
- `k1=1.5`, `b=0.75`.

Confirmation scope:
- 4 retrieval-eligible seed test cases;
- no representation-selection argument exposed by the confirmation API or CLI.

Frozen text-only test reference:
- canonical MRR: `0.666667`;
- nDCG@10: `0.716916`;
- Recall@5: `0.750000`;
- Recall@10: `0.875000`.

Selected representation test result:
- canonical MRR: `0.675000`;
- nDCG@10: `0.721614`;
- Recall@5: `0.875000`;
- Recall@10: `0.875000`.

Absolute changes versus text-only:
- canonical MRR: `+0.008333`;
- nDCG@10: `+0.004698`;
- Recall@10: `0.000000`.

Relative nDCG@10 change:
- approximately `+0.66%`.

Artifact:
- `artifacts/evaluation/phase4c/document-title-text-v1-test.json`;
- SHA-256:
  `72666dbd40d60061d33775a285b06e45eb3826f3ea121f8a7476c6f73d9786b3`;
- size: `37199` bytes.

Known limitation:
- Q-0018 multi-source Recall@10 remains `0.5`;
- multi-source retrieval is not considered solved.

Evaluation qualification:
The seed test split was not used to select the Phase 4B follow-on
representation, but Phase 4A had exposed seed test results earlier. Therefore
describe Phase 4C as a test-split confirmation, not a pristine unseen external
holdout.

Resume-use constraint:
Do not generalize the small test improvement beyond the synthetic Northstar
benchmark. Do not attribute it to dense retrieval, hybrid fusion, reranking,
LLMs, or agents.

## Phase 5A — Dense Retrieval Baseline

**Status:** MEASURED / DEVELOPMENT-VERIFIED

Implemented:
- independent dense retrieval index;
- `intfloat/e5-small-v2`;
- immutable model revision
  `ffb93f3bd4047442299a41ebb6fa998a38507c52`;
- 384-dimensional embeddings;
- E5 `query:` / `passage:` asymmetric representation;
- evidence-text-only passage representation;
- L2 normalization;
- normalized inner-product similarity;
- deterministic `(-score, chunk_id)` ordering;
- CPU execution;
- development-only benchmark integration.

Runtime:
- NumPy `2.5.2`;
- PyTorch `2.13.0+cpu`;
- Transformers `5.16.1`;
- Sentence Transformers `6.0.1`;
- CUDA unavailable.

Real-model invariance:
- corpus shape: `(80, 384)`;
- batch-size-1 vs batch-size-16 maximum absolute difference:
  `1.7136335372924805e-07`;
- batch comparison passes `1e-6` tolerance;
- repeated batch-size-16 maximum difference: `0.0`;
- embedding norms remain approximately `1.0`.

Development evaluation:
- cases: `10`;
- canonical MRR: `0.611003`;
- nDCG@10: `0.608430`;
- Recall@10: `0.800000`.

Frozen Phase 4B BM25 development reference:
- representation: `document-title-text-v1`;
- canonical MRR: `0.659091`;
- nDCG@10: `0.677258`;
- Recall@10: `0.800000`.

Dense-minus-BM25:
- canonical MRR: approximately `-7.30%` relative;
- nDCG@10: approximately `-10.16%` relative;
- Recall@10: unchanged.

Diagnostic behavior:
- Q-0017 gains partial top-10 recovery under dense retrieval;
- Q-0021 remains a severe evidence-text-only dense failure;
- the observed error differences motivate controlled dense metadata testing and
  later hybrid retrieval rather than post-hoc tuning of this baseline.

Artifact:
- `artifacts/evaluation/phase5a/e5-small-v2-development.json`;
- SHA-256:
  `b388e10207467018434a26c54cf5002953c698a9988b7a23d2194919e43fa11a`;
- size: `68512` bytes;
- independent `/tmp` rerun: byte-identical.

Tests:
- `150` passing.

Resume-use constraint:
Describe these as development-set measurements on the synthetic Northstar
benchmark. Do not claim test-set performance, production generalization,
hybrid retrieval, pgvector search, reranking, or agent behavior from Phase 5A.

## Phase 5B — Dense Representation Ablation

**Status:** MEASURED / VERIFIED

Experimental design:
- preregistered before candidate measurement;
- baseline: `e5-evidence-text-v1`;
- candidate: `e5-document-title-text-v1`;
- only document-title context changed;
- E5 model, immutable revision, normalization, scorer, corpus, development
  cases, and retrieval configuration held fixed;
- primary selection metric: development nDCG@10;
- canonical MRR and Recall@10 used only as ordered tie-breakers;
- exact tie retained D0.

Pre-measurement boundary:
- commit:
  `c51d88d2b5ec2062a0d28aaeb5484499d541631f`;
- tag:
  `phase-5b-dense-ablation-preregistered`;
- 162 tests passing;
- Phase 5A baseline reproduced byte-identically;
- zero Phase 5B measurement artifacts existed before candidate measurement;
- the experiment CLI exposed only `--output`;
- representation candidates and the selection policy were frozen before D1
  was measured.

Selected representation:

```text
e5-document-title-text-v1
```

Development metrics:
- canonical MRR: `0.783333`;
- nDCG@10: `0.782979`;
- Recall@10: `0.950000`.

Improvement over frozen evidence-text dense baseline:
- canonical MRR absolute delta: `+0.172330`;
- canonical MRR relative delta: approximately `+28.20%`;
- nDCG@10 absolute delta: `+0.174549`;
- nDCG@10 relative delta: approximately `+28.69%`;
- Recall@10 absolute delta: `+0.150000`;
- Recall@10 relative delta: approximately `+18.75%`.

Preregistered selection result:
- primary criterion was development nDCG@10;
- D1 exceeded D0 on the primary criterion;
- no tie-breaker was required;
- selected representation:
  `e5-document-title-text-v1`.

Diagnostic behavior:
- Q-0017 canonical evidence moved from rank 9 under D0 to rank 1 under D1;
- Q-0017 Recall@10 remained `0.5`, so title enrichment repaired canonical
  ordering without recovering every relevant item;
- Q-0021 canonical evidence moved from approximately rank 44 under D0 to rank
  2 under D1;
- Q-0021 Recall@10 moved from `0.0` to `1.0`;
- Q-0021 nDCG@10 moved from `0.0` to approximately `0.630930`;
- not all individual query metrics improved, so the result is an aggregate
  development-set selection rather than universal per-query dominance.

Descriptive comparison with frozen BM25 `document-title-text-v1`:
- BM25 canonical MRR: `0.659091`;
- dense D1 canonical MRR: `0.783333`;
- dense relative improvement: approximately `+18.85%`;
- BM25 nDCG@10: `0.677258`;
- dense D1 nDCG@10: `0.782979`;
- dense relative improvement: approximately `+15.61%`;
- BM25 Recall@10: `0.800000`;
- dense D1 Recall@10: `0.950000`;
- dense relative improvement: approximately `+18.75%`.

This BM25 comparison was descriptive only and was performed after D1 had
already been selected under the preregistered dense representation experiment.
It was not part of the Phase 5B selection policy.

Artifact:
- `artifacts/evaluation/phase5b/e5-document-title-text-v1-development.json`;
- SHA-256:
  `ed406dacfec38bd97de7ccb42ad84b6d2ab6e00332e3b52b1cec171593d67f87`;
- size: `76204` bytes;
- independent CPU rerun: byte-identical.

Reproducibility:
- canonical artifact and independent `/tmp` rerun were byte-identical;
- both artifacts produced SHA-256
  `ed406dacfec38bd97de7ccb42ad84b6d2ab6e00332e3b52b1cec171593d67f87`;
- both artifacts were `76204` bytes.

Integrity:
- experiment version verified as
  `dense-representation-ablation-v1`;
- scope verified as `development-only`;
- baseline verified as `e5-evidence-text-v1`;
- candidate verified as `e5-document-title-text-v1`;
- selected representation verified as `e5-document-title-text-v1`;
- primary selection metric verified as `mean_ndcg_at_10`;
- secondary selection metric verified as
  `mean_canonical_reciprocal_rank`;
- tertiary selection metric verified as `mean_recall_at_10`;
- exact-tie policy verified to retain `e5-evidence-text-v1`;
- exact 10 development query IDs verified;
- every evaluated case verified as development;
- model verified as `intfloat/e5-small-v2`;
- immutable model revision verified as
  `ffb93f3bd4047442299a41ebb6fa998a38507c52`;
- candidate and encoder representation metadata verified.

Quality:
- 162 tests passing;
- Ruff clean;
- formatting clean;
- dependency lock valid;
- Alembic head current at `8a0f69a3baf1`;
- no schema drift;
- exactly one Phase 5B evaluation artifact.

Resume-use constraint:
Describe these as controlled development-set measurements on the synthetic
Northstar benchmark.

Supported resume/interview claims include:
- implemented and evaluated a controlled dense retrieval representation
  ablation;
- preregistered the candidate and metric-selection policy before measurement;
- held model, revision, embedding configuration, corpus, scorer, and
  evaluation cases fixed while changing document-title context;
- selected `e5-document-title-text-v1` using development nDCG@10;
- measured approximately `0.7833` canonical MRR, `0.7830` nDCG@10, and
  `0.95` Recall@10;
- measured approximately `28.69%` relative nDCG@10 improvement over the
  evidence-text-only dense baseline;
- reproduced the measured artifact byte-identically.

Do not claim from Phase 5B:
- test-set confirmation;
- production or real-enterprise generalization;
- that dense retrieval is universally superior to BM25;
- hybrid retrieval or reciprocal-rank fusion;
- pgvector serving;
- cross-encoder reranking;
- production latency, throughput, or scalability;
- end-to-end RAG or agent performance.

## Phase 6A — Hybrid Reciprocal Rank Fusion

**Status:** MEASURED / VERIFIED

Experiment:
- preregistered fixed equal-weight Reciprocal Rank Fusion;
- lexical input:
  `BM25 document-title-text-v1`;
- dense input:
  `E5 e5-document-title-text-v1`;
- fixed fusion constant:
  `k=60`;
- deterministic final ordering:
  `(-rrf_score, chunk_id)`;
- absent retriever ranks contribute zero;
- no score interpolation or normalization;
- no parameter sweep;
- development-only measurement.

Clean preregistration boundary:

```text
2f11268a3e17e02d5fd8f2e9cedccc5358dc52ed
```

Tag:

```text
phase-6a-hybrid-rrf-preregistered-clean
```

Frozen lexical artifact SHA-256:

```text
c1d36faf093d18053a733beb868933da71e902d741ae81ed885efb8f0104b3c2
```

Frozen dense artifact SHA-256:

```text
ed406dacfec38bd97de7ccb42ad84b6d2ab6e00332e3b52b1cec171593d67f87
```

Selected retriever:

```text
hybrid:rrf-k60-v1
```

Development metrics:
- canonical MRR: `0.816667`;
- nDCG@10: `0.831207`;
- Recall@10: `0.950000`.

Improvement versus frozen Dense D1:
- canonical MRR absolute delta: `+0.033333`;
- canonical MRR relative delta: approximately `+4.26%`;
- nDCG@10 absolute delta: `+0.048228`;
- nDCG@10 relative delta: approximately `+6.16%`;
- Recall@10 delta: `0.0`.

Per-query primary-metric comparison versus Dense D1:
- hybrid wins: `5`;
- ties: `3`;
- hybrid losses: `2`.

Diagnostics:
- Q-0006 improved nDCG@10 from approximately `0.730929` to `0.833991`;
- Q-0009 regressed from approximately `0.817530` to `0.613147` and
  Recall@10 decreased from `1.0` to `0.5`;
- Q-0017 Recall@10 increased from `0.5` to `1.0`, but canonical reciprocal
  rank decreased from `1.0` to approximately `0.166667`;
- Q-0019 produced a modest nDCG@10 improvement while preserving coverage;
- Q-0020 improved nDCG@10 from approximately `0.630930` to `1.0`;
- Q-0021 improved nDCG@10 from approximately `0.630930` to `1.0`.

The negative cases are retained and were not used to retune `k`.

Artifact:

```text
artifacts/evaluation/phase6a/rrf-k60-development.json
```

SHA-256:

```text
c0f850e21d25f993f26c58b44d0ace057fbcd23380dce85039f2b4d6c2593c21
```

Size:

```text
103859 bytes
```

Reproducibility:
- independent CPU rerun completed;
- rerun was byte-identical;
- rerun SHA-256 matched canonical artifact exactly;
- rerun size matched canonical artifact exactly.

Integrity:
- exact 10 development query IDs verified;
- exact frozen source hashes verified;
- exact `k=60` verified;
- BM25 and dense representation identities verified;
- E5 model and immutable revision verified;
- 80-chunk corpus verified;
- dense and fused rankings both return 80 chunks;
- no seed test case was used.

Quality:
- Ruff clean;
- formatting clean;
- 177 tests passing;
- dependency lock valid;
- Alembic head current;
- no schema drift;
- exactly one Phase 6A measurement artifact.

Supported resume/interview claim:
Implemented deterministic BM25 + E5 Reciprocal Rank Fusion and, in a
preregistered development experiment with fixed `k=60`, improved nDCG@10 from
approximately `0.7830` to `0.8312` (`+6.16%` relative) over the strongest
frozen standalone dense retriever while maintaining `0.95` Recall@10.

Resume-use constraint:
Describe the metrics as measurements on the 10 retrieval-eligible development
queries of the synthetic Northstar benchmark.

Do not claim:
- test-set confirmation;
- optimal RRF hyperparameters;
- universal superiority of hybrid retrieval;
- real-enterprise generalization;
- cross-encoder reranking;
- pgvector serving performance;
- production latency or throughput;
- generation quality;
- end-to-end agent performance.
