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

## Phase 6B — Frozen Hybrid Test Confirmation

**Status:** MEASURED / VERIFIED

Purpose:
Evaluate the already-selected Phase 6A BM25 + E5 RRF retriever on the existing
retrieval-eligible Northstar test split without retrieval retuning.

Methodological limitation:

```text
test_split_status = previously-inspected-non-pristine
```

The retrieval-eligible test queries had already been inspected during earlier
retrieval work, including Phase 4C.

Therefore Phase 6B is a frozen test confirmation, not a pristine unseen,
untouched, blinded, or fully independent holdout.

Preregistration boundary:

```text
7d86ec84c5233e568af1e634e21c5a36e0e2e620
```

Preregistration tag:

```text
phase-6b-hybrid-test-confirmation-preregistered
```

Before measurement:
- Phase 6B artifact count: `0`;
- worktree: clean;
- retrieval configuration: frozen;
- exact four-query confirmation scope: frozen.

Frozen Phase 6A source:

```text
artifacts/evaluation/phase6a/rrf-k60-development.json
```

Frozen Phase 6A SHA-256:

```text
c0f850e21d25f993f26c58b44d0ace057fbcd23380dce85039f2b4d6c2593c21
```

Frozen Phase 6A result commit:

```text
689818d1168f46a06c7b189ab81bbfe5f168fc07
```

Frozen Phase 6A result tag:

```text
phase-6a-hybrid-rrf-baseline
```

Frozen retriever:

```text
hybrid:rrf-k60-v1
```

Frozen lexical configuration:
- retriever: `BM25`;
- BM25 version: `bm25-v1`;
- tokenizer: `lexical-tokenizer-v1`;
- representation: `document-title-text-v1`;
- `k1=1.5`;
- `b=0.75`;
- zero-overlap chunks excluded;
- absent BM25 ranks contribute zero to RRF.

Frozen dense configuration:
- dense version: `dense-e5-small-v2-v1`;
- representation: `e5-document-title-text-v1`;
- model: `intfloat/e5-small-v2`;
- immutable model revision:
  `ffb93f3bd4047442299a41ebb6fa998a38507c52`;
- embedding dimension: `384`;
- normalized embeddings;
- inner-product similarity;
- device: CPU;
- batch size: `16`.

Frozen fusion configuration:
- fusion version: `rrf-k60-v1`;
- fixed RRF constant: `k=60`;
- lexical rank weight: `1`;
- dense rank weight: `1`;
- missing source-rank contribution: `0`;
- deterministic final ordering:
  `(-rrf_score, chunk_id)`;
- no raw-score interpolation;
- no score normalization;
- no query-type routing;
- no learned fusion;
- no post-test parameter tuning.

Exact retrieval-eligible test cases:

```text
Q-0003  lexical
Q-0005  semantic
Q-0007  hybrid
Q-0018  multi_source
```

Exactly four test cases were evaluated.

Frozen Dense D1 test metrics:
- canonical MRR: `1.000000`;
- nDCG@10: `0.9378188547`;
- Recall@10: `1.000000`.

Frozen Hybrid RRF test metrics:
- canonical MRR: `0.750000`;
- nDCG@1: `0.500000`;
- nDCG@3: `0.7700698027`;
- nDCG@5: `0.7700698027`;
- nDCG@10: `0.8184264036`;
- Recall@1: `0.375000`;
- Recall@3: `0.875000`;
- Recall@5: `0.875000`;
- Recall@10: `1.000000`.

Hybrid versus frozen Dense D1:
- canonical MRR absolute delta: `-0.250000`;
- canonical MRR relative delta: `-25.00%`;
- nDCG@10 absolute delta: `-0.1193924511`;
- nDCG@10 relative delta: approximately `-12.73%`;
- Recall@10 absolute delta: `0.0`;
- Recall@10 relative delta: `0.0%`.

Per-query outcome:
- Q-0003: tie versus Dense D1;
- Q-0005: tie versus Dense D1;
- Q-0007: RRF ranking regression;
- Q-0018: RRF ranking regression.

Q-0003:
- dense nDCG@10: `1.0`;
- hybrid nDCG@10: `1.0`;
- dense canonical RR: `1.0`;
- hybrid canonical RR: `1.0`;
- dense Recall@10: `1.0`;
- hybrid Recall@10: `1.0`.

Q-0005:
- dense nDCG@10: `1.0`;
- hybrid nDCG@10: `1.0`;
- dense canonical RR: `1.0`;
- hybrid canonical RR: `1.0`;
- dense Recall@10: `1.0`;
- hybrid Recall@10: `1.0`.

Q-0007 diagnostic:
- dense canonical rank: `1`;
- hybrid canonical rank: `2`;
- dense nDCG@10: approximately `0.919721`;
- hybrid nDCG@10: approximately `0.693426`;
- dense Recall@10: `1.0`;
- hybrid Recall@10: `1.0`.

Q-0007 hybrid top-two explanation:

```text
rank 1:
EVID-CORE-PC006-BOARD-PRIORITY
BM25 rank  = 1
dense rank = 2
RRF score  = 0.03252247488101534

rank 2:
EVID-CORE-PC006-RISK-PRIMARY
BM25 rank  = 3
dense rank = 1
RRF score  = 0.032266458495966696
```

Interpretation for Q-0007:
The lexical rank-1 support for the board-priority evidence, combined with dense
rank 2, was enough under equal-weight RRF to displace the dense-rank-1
canonical evidence.

The canonical evidence remained in the top 10, so Recall@10 stayed at `1.0`.
The regression was primarily in ordering, not candidate coverage.

Q-0018 diagnostic:
- dense canonical rank: `1`;
- hybrid canonical rank: `2`;
- dense nDCG@10: approximately `0.831555`;
- hybrid nDCG@10: approximately `0.580279`;
- dense Recall@10: `1.0`;
- hybrid Recall@10: `1.0`.

Q-0018 hybrid top-two explanation:

```text
rank 1:
EVID-CORE-PC007-BOARD-PRIORITY
BM25 rank  = 1
dense rank = 2
RRF score  = 0.03252247488101534

rank 2:
EVID-CORE-PC007-QMR-FINANCIAL
BM25 rank  = 5
dense rank = 1
RRF score  = 0.03177805800756621
```

Interpretation for Q-0018:
Equal-weight RRF favored the evidence item with BM25 rank 1 and dense rank 2
over the dense-rank-1 canonical evidence whose lexical rank was 5.

Again, the canonical evidence remained in the top 10, so the failure was
primarily in final ordering.

Development/test contrast:

Phase 6A development:
- canonical MRR delta versus Dense D1:
  `+0.0333333333` absolute;
- canonical MRR relative delta:
  approximately `+4.26%`;
- nDCG@10 delta versus Dense D1:
  `+0.0482279271` absolute;
- nDCG@10 relative delta:
  approximately `+6.16%`;
- Recall@10 delta:
  `0.0`.

Phase 6B test confirmation:
- canonical MRR delta versus Dense D1:
  `-0.2500000000` absolute;
- canonical MRR relative delta:
  `-25.00%`;
- nDCG@10 delta versus Dense D1:
  `-0.1193924511` absolute;
- nDCG@10 relative delta:
  approximately `-12.73%`;
- Recall@10 delta:
  `0.0`.

Key contrast:

```text
development nDCG@10 relative delta:       +6.16%
test-confirmation nDCG@10 relative delta: -12.73%
```

Recall@10 remained unchanged relative to Dense D1 in both experiments.

Scientific interpretation:
The development-selected equal-weight RRF improvement did not reproduce on the
four-case test confirmation.

The negative confirmation was retained exactly as measured.

No Phase 6B retuning was performed.

No change was made to:
- RRF `k`;
- lexical weight;
- dense weight;
- BM25 parameters;
- lexical representation;
- dense representation;
- embedding model;
- embedding revision;
- query set;
- evaluation metrics;
- fusion formula.

No weighted RRF, alternative `k`, score interpolation, query routing, learned
fusion, or reranking experiment was run against the Phase 6B test cases.

Engineering lesson:
Equal-weight hybrid fusion can preserve broad candidate coverage while
degrading final ordering.

This motivates separating:

```text
candidate generation
```

from:

```text
final relevance ordering
```

A later cross-encoder reranking experiment can test whether broad retrieval
coverage can be retained while correcting ordering failures such as Q-0007
and Q-0018.

This future motivation does not alter the frozen Phase 6B result.

Canonical artifact:

```text
artifacts/evaluation/phase6b/rrf-k60-test-confirmation.json
```

Canonical SHA-256:

```text
21f7c2a354ca2e928b33eea6f7dfb17ff87ed0b93f3e35451fc3576c196a5843
```

Canonical size:

```text
77199 bytes
```

Reproducibility:
- independent CPU rerun completed;
- rerun path:
  `/tmp/rrf-k60-test-confirmation.json`;
- canonical and rerun artifacts were byte-identical;
- rerun SHA-256 matched canonical SHA-256 exactly;
- rerun file size matched canonical size exactly;
- temporary rerun was removed after verification.

Integrity verification:
- confirmation version:
  `hybrid-rrf-test-confirmation-v1`;
- frozen selected retriever:
  `hybrid:rrf-k60-v1`;
- selection status:
  `frozen-before-test-confirmation`;
- scope:
  `test-confirmation`;
- test split status:
  `previously-inspected-non-pristine`;
- exact expected test query IDs verified;
- exactly four dense cases verified;
- exactly four hybrid cases verified;
- all cases verified as split `test`;
- frozen Phase 6A source SHA-256 verified;
- fusion version `rrf-k60-v1` verified;
- fixed `k=60` verified;
- lexical representation verified;
- dense representation verified;
- E5 model verified;
- immutable E5 revision verified.

Quality:
- Ruff clean;
- formatting clean;
- `181` tests passing;
- dependency lock valid;
- Alembic current:
  `8a0f69a3baf1 (head)`;
- no schema drift;
- exactly one Phase 6B canonical artifact.

Phase 6B preregistration boundary remained:

```text
7d86ec84c5233e568af1e634e21c5a36e0e2e620
```

throughout measurement and reproducibility verification.

Interview-use lesson:
A development-set retrieval gain is not sufficient evidence of generalization.

The Phase 6A development result was positive, while the frozen Phase 6B
confirmation reversed direction on ranking quality.

This is useful evidence of:
- controlled experimental design;
- preregistration discipline;
- split-aware evaluation;
- negative-result retention;
- diagnostic retrieval analysis;
- separation of recall from ranking quality;
- avoidance of test-set retuning.

Resume-use constraint:
The positive Phase 6A metric may be used only when explicitly described as a
development-benchmark result on the synthetic Northstar benchmark.

The Phase 6B result must not be represented as successful validation.

The four-query test confirmation must not be described as pristine, unseen,
untouched, blinded, statistically representative, or large-scale.

Supported interview claims:
- implemented deterministic BM25 + E5 RRF;
- froze the RRF configuration before test confirmation;
- evaluated exactly four retrieval-eligible test cases;
- retained a negative confirmation rather than retuning against test queries;
- observed unchanged top-10 recall despite worse final ordering;
- reproduced the Phase 6B artifact byte-identically;
- diagnosed concrete rank-fusion failure modes.

Do not claim:
- statistical significance;
- universal Dense superiority;
- universal RRF inferiority;
- optimal RRF `k`;
- optimal source weights;
- real-enterprise generalization;
- pristine holdout validation;
- learned-fusion results;
- cross-encoder reranking results;
- pgvector serving performance;
- production latency;
- production throughput;
- production scalability;
- generation quality;
- agent quality.

## Phase 7A — Cross-Encoder Reranker Development Baseline

**Status:** MEASURED / VERIFIED

Experiment:
One preregistered cross-encoder reranker over the frozen Phase 6A hybrid RRF
candidate generator.

Preregistration commit:

7197b85b4a7f8f61043ec5dab8e0e263dd52a92b

Preregistration tag:

phase-7a-cross-encoder-reranker-preregistered

Model:

cross-encoder/ms-marco-MiniLM-L6-v2

Immutable revision:

233902d25c440f23af6f7d6e94d2946bac0bee0a

Representation:

cross-encoder-document-title-text-v1

Fixed candidate cutoff:

20

Device:

CPU

Evaluation:
- synthetic Northstar benchmark;
- 10 retrieval-eligible development cases;
- test split not used;
- full corpus: 80 chunks;
- RRF ranks 1 through 20 reranked;
- ranks 21 through 80 preserved;
- no score blending;
- no model or cutoff sweep.

Frozen Phase 6A regeneration:

VERIFIED

Frozen RRF development:
- canonical MRR: 0.816667;
- nDCG@10: 0.831207;
- Recall@10: 0.950000.

Cross-encoder reranked development:
- canonical MRR: 0.703869;
- nDCG@10: 0.709559;
- Recall@10: 0.900000.

Relative change versus frozen RRF:
- canonical MRR: approximately -13.81 percent;
- nDCG@10: approximately -14.64 percent;
- Recall@10: approximately -5.26 percent.

Preregistered selection result:

REJECTED

Selection reason:

recall_at_10_guardrail_failed

Selected retriever remains:

hybrid:rrf-k60-v1

Important positive diagnostics:
- Q-0009 nDCG@10 improved from approximately 0.6131 to 0.8316 and Recall@10
  improved from 0.5 to 1.0;
- Q-0017 nDCG@10 improved from approximately 0.3956 to 0.8175;
- Q-0017 canonical reciprocal rank improved from 1/6 to 1;
- canonical financial evidence for Q-0017 moved from RRF rank 6 to reranked
  rank 1.

Important negative diagnostics:
- Q-0020 canonical evidence moved from RRF rank 1 to reranked rank 7;
- Q-0021 canonical evidence moved from RRF rank 1 to reranked rank 16;
- Q-0021 Recall@10 fell from 1.0 to 0.0.

Interpretation:
The fixed generic cross-encoder demonstrated query-level complementarity but
did not provide reliable aggregate ordering for the Northstar development
benchmark.

The result was retained without post-measurement retuning.

The rejected candidate was not evaluated on the Phase 6B test split.

Canonical artifact:

artifacts/evaluation/phase7a/cross-encoder-reranker-development.json

SHA-256:

101e826b06efacf5f01dad237ccc64db13328308645552281b17cf9494b37ce4

Size:

580704 bytes

Reproducibility:
- repeat execution completed;
- canonical and repeat artifacts were byte-identical;
- SHA-256 matched exactly;
- size matched exactly.

Quality:
- Ruff clean;
- formatting clean;
- 195 tests passing;
- dependency lock valid;
- Alembic current at 8a0f69a3baf1;
- no schema drift;
- exactly one canonical Phase 7A artifact.

Interview evidence:
- implemented second-stage cross-encoder reranking;
- pinned immutable pretrained model revision;
- enforced candidate-set and tail-order invariants;
- preregistered candidate cutoff and selection policy;
- verified frozen baseline regeneration;
- separated Recall@10 guardrail from ranking-quality metrics;
- retained a negative model result instead of tuning against it;
- diagnosed query-level model failures;
- reproduced the measured artifact byte-identically.

Do not claim:
- cross-encoders are generally inferior;
- the reranker improved the retrieval stack overall;
- unseen-test improvement;
- statistical significance;
- optimal model or candidate cutoff;
- production serving performance;
- real-enterprise generalization;
- generation quality;
- agent quality.

## Phase 8A2 — Deterministic Heuristic Tool Router

**Status:** MEASURED / REPRODUCIBLE / VERIFIED

Implemented a deterministic multi-label enterprise tool router over three
canonical tool families:

- retrieval
- sql
- graph

Supported route combinations:

- retrieval
- sql
- graph
- retrieval+sql
- retrieval+graph
- sql+graph
- retrieval+sql+graph

Frozen routing benchmark:

northstar-routing-v1

Frozen routing SHA-256:

995f707a4cc6393f0e916f903cc57f9aec6fbabb3c43a00a78e318ca505b6912

Ground-truth commit:

e0755e81d3d1fa24577dbe4e0dd7a92c00247863

Phase 8A2 preregistration commit:

331c7f7aa1a637411d5a842530c7f10008052a5b

Input representation:

question-text-v1

Router:

heuristic-router-v1

Development cases:

28

Locked-holdout cases evaluated:

0

Measured development performance:

- exact route-set accuracy: 1.0000
- macro precision: 1.0000
- macro recall: 1.0000
- macro F1: 1.0000
- Hamming loss: 0.0000
- required-tool omission rate: 0.0000
- unnecessary-tool addition rate: 0.0000
- under-routing case rate: 0.0000
- over-routing case rate: 0.0000
- error cases: 0 of 28

Per-tool development performance:

- retrieval precision / recall / F1: 1.0 / 1.0 / 1.0
- SQL precision / recall / F1: 1.0 / 1.0 / 1.0
- graph precision / recall / F1: 1.0 / 1.0 / 1.0

Canonical artifact:

artifacts/evaluation/phase8a2/heuristic-router-development.json

SHA-256:

222b731e602cfa6a5d38fd9c2c86d87fc8017caac56131b18ce4292628142c40

Size:

22077 bytes

Reproducibility:

BYTE-IDENTICAL independent rerun

Development membership:

VERIFIED

Holdout membership:

0 cases

Methodological limitation:

The heuristic was preregistered before any routing-performance measurement,
but the routing benchmark language had been constructed and human-reviewed
before the heuristic rules were authored.

Therefore the 1.0 development result must not be presented as evidence of
perfect out-of-sample generalization.

Interview evidence:

- designed a multi-label tool-routing ontology;
- distinguished routing from downstream abstention;
- implemented deterministic retrieval / SQL / graph intent detection;
- prevented qualitative financial terminology from automatically forcing SQL;
- implemented exact-set and per-tool routing metrics;
- measured required-tool omission and unnecessary-tool addition separately;
- enforced frozen benchmark fingerprint verification before canonical
  evaluation;
- preregistered rules before development measurement;
- verified exact development-set membership;
- preserved locked-holdout performance;
- generated deterministic byte-reproducible evaluation artifacts.

Do not claim:

- perfect generalization;
- locked-holdout performance;
- learned-router superiority;
- pretrained-classifier performance;
- LoRA / PEFT performance;
- SQL execution correctness;
- graph execution correctness;
- production serving performance;
- end-to-end agent quality.
