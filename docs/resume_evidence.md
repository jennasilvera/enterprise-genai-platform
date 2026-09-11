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

Status: VERIFIED

Evidence:

- `src/enterprise_genai/routing/lora_training_config.py`
- `src/enterprise_genai/routing/lora_trainer.py`
- `src/enterprise_genai/evaluation/lora_routing_benchmark.py`
- `docs/evaluation/lora_router_plan.md`
- `docs/evaluation/lora_router_results.md`
- `docs/evaluation/routing_confirmation_plan.md`
- `artifacts/models/phase8c/lora-router-development/training-report.json`
- `artifacts/models/phase8c/lora-router-development/seed-1729/best_adapter/`
- `artifacts/evaluation/phase8c/routing-confirmation.json`
- deterministic three-seed CPU training and byte-identical full-tree reproduction
- frozen development and locked-confirmation protocols

Supports:

> Built and evaluated a PEFT/LoRA seven-class tool router across retrieval, SQL,
> and graph execution paths; fine-tuned 150K parameters (~0.21% of the model)
> in deterministic multi-seed CPU experiments, achieving 82.1% development and
> 78.6% held-out exact routing accuracy.

Limitation:

The separate 84-case robustness challenge reached 32.1% exact route-set
accuracy and exposed materially weaker out-of-template retrieval/graph
generalization. The experiment also does not isolate the causal contribution of
LoRA adapters from the effect of supervised seven-class task adaptation.

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

## Phase 8B1 — Pretrained Zero-Shot NLI Router

**Status:** MEASURED / REPRODUCIBLE / VERIFIED

Implemented and evaluated a frozen pretrained zero-shot semantic router using:

cross-encoder/nli-deberta-v3-xsmall

Immutable model revision:

a150876415327c80daeff35ca6f68f5ed8cf5c24

Router configuration SHA-256:

72d8ce61cdce386bb189cb70698d0f899bf94fa63b8f42796f1a19eaaca3e924

Training performed:

false

Routing formulation:

seven-way NLI classification over the canonical retrieval / SQL / graph route
sets.

Development cases:

28

Original locked-holdout cases evaluated:

0

Generalization-challenge cases evaluated:

0

Measured development performance:

- exact route-set accuracy: 0.14285714285714285
- macro precision: 0.5714285714285714
- macro recall: 1.0
- macro F1: 0.7272727272727272
- Hamming loss: 0.42857142857142855
- required-tool omission rate: 0.0
- unnecessary-tool addition rate: 1.0
- under-routing case rate: 0.0
- over-routing case rate: 0.8571428571428571

Observed failure mode:

maximal-route collapse

All 28 development cases were predicted as:

retrieval+sql+graph

Canonical artifact:

artifacts/evaluation/phase8b1/pretrained-nli-router-development.json

Artifact SHA-256:

e4ec5eb88945e259a9dba923a15c997743a4dcf4971828bcd383fd44a304e5ea

Artifact size:

89850 bytes

Reproducibility:

BYTE-IDENTICAL independent rerun

Membership verification:

- development cases: 28
- original locked holdout: 0
- generalization challenge: 0

Interview evidence:

- pinned immutable pretrained model revision;
- implemented zero-shot semantic tool routing;
- fingerprinted complete model-routing configuration;
- used deterministic seven-route entailment argmax;
- separated required-tool omission from unnecessary-tool addition;
- diagnosed systematic maximal-route collapse;
- preserved a negative experimental result without post-hoc retuning;
- generated byte-reproducible evaluation artifacts;
- maintained locked-holdout and challenge isolation.

Important interpretation:

Zero required-tool omission did not mean the router was good. It over-routed
24 of 28 cases and predicted all three tools for every question. This
demonstrates why routing systems must evaluate unnecessary tool invocation as
well as missing capabilities.

Do not claim:

- strong zero-shot routing performance;
- challenge performance;
- original locked-holdout performance;
- LoRA/PEFT improvement;
- production generalization;
- SQL execution correctness;
- graph execution correctness;
- production latency or throughput.

## Phase 8C — PEFT/LoRA Supervised Tool Router

**Status:** MEASURED / REPRODUCIBLE / CONFIRMED / VERIFIED / FROZEN

Model:

- `cross-encoder/nli-deberta-v3-xsmall`
- immutable revision:
  `a150876415327c80daeff35ca6f68f5ed8cf5c24`

Task:

- direct seven-class route classification;
- route space covers all non-empty combinations of retrieval, SQL, and graph;
- question text only is provided to the classifier.

PEFT configuration:

- PEFT 0.20.0;
- LoRA rank: 8;
- LoRA alpha: 16;
- LoRA dropout: 0.05;
- target modules: `query_proj`, `value_proj`;
- explicit saved classifier head;
- training configuration SHA-256:
  `bd2f9f65decf4e5d6b8d2b7dc9908c778f081cc20b2ade3ce78e502ab50c39cf`.

Parameter audit:

- seven-class base parameters: 70,832,647;
- PEFT-wrapped total parameters: 70,982,798;
- trainable parameters: 150,151;
- trainable share: approximately 0.2115%;
- 24 LoRA-A tensors;
- 24 LoRA-B tensors;
- 2 classifier tensors;
- unexpected trainable tensors: 0;
- trainable pooler tensors: 0.

Runtime:

- CPU;
- FP32;
- CUDA: false;
- deterministic PyTorch algorithms enabled;
- six intra-op and six inter-op threads.

Frozen experiment:

- training cases: 112;
- development cases: 28;
- 16 training cases per route;
- 4 development cases per route;
- train/development template-family overlap: 0;
- training seeds: 1729, 2718, 31415;
- 20 epochs per seed;
- 140 optimizer steps per seed;
- AdamW;
- learning rate: 0.0002;
- weight decay: 0.01;
- gradient-norm cap: 1.0;
- no early stopping;
- no hyperparameter sweep after measurement.

Checkpoint selection:

1. maximize exact route-set accuracy;
2. maximize macro F1;
3. minimize required-tool omission;
4. minimize unnecessary-tool addition;
5. prefer earlier epoch.

Seed selection used the same frozen metric hierarchy, then the earlier seed in
the preregistered seed order.

Selected model:

- seed: 1729;
- epoch: 19.

Development performance:

- exact route-set accuracy: 0.8214285714285714;
- correct exact routes: 23 of 28;
- macro precision: 0.9298245614035089;
- macro recall: 0.9791666666666666;
- macro F1: 0.9523809523809524;
- Hamming loss: 0.05952380952380952;
- required-tool omission rate: 0.020833333333333332;
- unnecessary-tool addition rate: 0.1111111111111111;
- under-routing case rate: 0.03571428571428571;
- over-routing case rate: 0.14285714285714285.

Development per-tool F1:

- retrieval: 1.0;
- SQL: 1.0;
- graph: 0.8571428571428572.

Development failure topology:

- five non-exact cases;
- four SQL-only cases over-routed to `sql+graph`;
- one `retrieval+sql+graph` case omitted graph;
- all remaining development errors were therefore concentrated at the graph
  decision boundary.

Canonical development artifact:

`artifacts/models/phase8c/lora-router-development/training-report.json`

SHA-256:

`afd035414008baea25aad26ce1775dc6887e6d2c51b92b603bd5346408aa34ac`

Selected adapter weights SHA-256:

`9b9e95c2122e9d233e47b7432a0ec268fc69f6ece936b7cb7dda80728020b8f0`

Selected adapter configuration SHA-256:

`5bc3929e5bf9f8b39cb9bacf54aac0be91723d177f9774cf41b91f218ded7fd5`

Reproducibility:

- synthetic full-loop training preflight passed before any Northstar gradient;
- independent post-freeze full three-seed rerun completed;
- all three adapter configurations reproduced byte-identically;
- all three adapter weight files reproduced byte-identically;
- complete training report reproduced byte-identically;
- selected seed and epoch reproduced exactly;
- all development metrics reproduced exactly.

Original locked-holdout confirmation:

- cases: 28;
- exact route-set accuracy: 0.7857142857142857;
- correct exact routes: 22 of 28;
- macro precision: 0.9629629629629629;
- macro recall: 0.9166666666666666;
- macro F1: 0.9327731092436974;
- Hamming loss: 0.07142857142857142;
- required-tool omission rate: 0.08333333333333333;
- unnecessary-tool addition rate: 0.05555555555555555;
- under-routing case rate: 0.14285714285714285;
- over-routing case rate: 0.07142857142857142.

Original holdout per-tool F1:

- retrieval: 1.0;
- SQL: 0.9411764705882353;
- graph: 0.8571428571428571.

Original holdout interpretation:

The selected classifier retained most of its development performance across
held-out template families within `northstar-routing-v1`.

Routing-generalization challenge:

- version: `northstar-routing-challenge-v1`;
- cases: 84;
- exact route-set accuracy: 0.32142857142857145;
- correct exact routes: 27 of 84;
- macro precision: 0.8132214594457157;
- macro recall: 0.6666666666666666;
- macro F1: 0.6981797082358107;
- Hamming loss: 0.3055555555555556;
- required-tool omission rate: 0.3333333333333333;
- unnecessary-tool addition rate: 0.26851851851851855;
- under-routing case rate: 0.5357142857142857;
- over-routing case rate: 0.34523809523809523.

Challenge per-tool F1:

- retrieval: 0.5074626865671642;
- SQL: 0.9574468085106383;
- graph: 0.6296296296296297.

Challenge interpretation:

The robustness challenge exposed limited out-of-template compositional
generalization, particularly for retrieval and graph intent. SQL intent remained
comparatively robust.

Frozen comparison results:

Original 28-case holdout exact route-set accuracy:

- heuristic: 1.0;
- pretrained NLI: 0.14285714285714285;
- LoRA: 0.7857142857142857.

84-case challenge exact route-set accuracy:

- heuristic: 0.2857142857142857;
- pretrained NLI: 0.14285714285714285;
- LoRA: 0.32142857142857145.

The pretrained NLI router predicted `retrieval+sql+graph` for:

- 28 of 28 original holdout cases;
- 84 of 84 challenge cases.

Its maximal-route collapse therefore reproduced on both confirmation sets.

The heuristic comparison is descriptive because its rules were authored with
knowledge of benchmark language. Its original-holdout 1.0 result must not be
presented as unbiased generalization evidence.

Canonical confirmation artifact:

`artifacts/evaluation/phase8c/routing-confirmation.json`

Confirmation artifact SHA-256:

`95196035d5b47b1f8e741d3fdb0c8ba5997284049dc24964d76b8e499b550829`

Confirmation result commit:

`6ee3e03d8ac96c6f4e9f1a076547409b9686eeab`

Confirmation result tag:

`phase-8c-routing-confirmation-result`

Interview evidence:

- implemented PEFT/LoRA sequence-classification fine-tuning;
- replaced a pretrained NLI head with a seven-class routing head;
- targeted attention query/value projections with LoRA;
- audited trainable parameter identity and count;
- trained only approximately 0.21% of the wrapped model;
- built deterministic multi-seed CPU training;
- implemented frozen checkpoint and seed selection;
- serialized and reloaded PEFT adapters;
- reproduced the full three-seed experiment byte-for-byte;
- separated model development from locked confirmation;
- evaluated exact route sets and individual tool decisions;
- measured omission and unnecessary invocation separately;
- diagnosed graph-specific and retrieval-specific generalization failures;
- retained a negative robustness result without post-hoc retuning.

Supports:

> Built and evaluated a PEFT/LoRA seven-class tool router across retrieval, SQL,
> and graph execution paths; fine-tuned 150K parameters (~0.21% of the model)
> in deterministic multi-seed CPU experiments, achieving 82.1% development and
> 78.6% held-out exact routing accuracy while identifying out-of-template
> robustness limitations on a separate 84-case challenge.

Important causal limitation:

The improvement over the frozen zero-shot NLI router cannot be attributed to
LoRA adapters alone. Phase 8C combines supervised seven-class task adaptation,
a newly initialized classifier head, and LoRA backbone adaptation. A
frozen-backbone classifier-head-only control would be required to isolate the
incremental contribution of LoRA.

Do not claim:

- production routing performance;
- real-enterprise generalization;
- statistical significance;
- linguistically blind external validation;
- strong challenge generalization;
- causal LoRA superiority over a supervised frozen-backbone head-only model;
- GPU/CUDA training;
- production latency or throughput;
- SQL execution correctness;
- graph execution correctness;
- end-to-end agent quality.

## Phase 8E — Bounded Portfolio Execution Coverage

**Status:** IMPLEMENTED / TESTED / MEASURED / REPRODUCIBLE / VERIFIED / FROZEN

Phase 8E extended the typed execution layer from known-entity operations to
bounded portfolio-wide structured and graph operations, then measured benchmark
primitive coverage before introducing an agent state machine.

### Phase 8E1 — Portfolio Structured SQL

Implemented bounded portfolio-level structured operations:

- portfolio metric sum;
- portfolio metric filtering;
- portfolio metric ranking;
- year-over-year growth ranking;
- ratio ranking;
- optional candidate-company scoping for upstream-tool handoff.

Execution remains parameterized SQLAlchemy rather than free-form SQL.

Behavior includes:

- deterministic ordering and company-ID tie-breaking;
- strict candidate-scope validation;
- typed empty states;
- rejection of non-additive percentage summation;
- relational source-row provenance;
- winning-entity canonical fact provenance.

Verified against real PostgreSQL for the benchmark semantics corresponding to:

- Q-0010: highest 2026 Q2 year-over-year revenue growth → HelioGrid Energy;
- Q-0011: total 2026 Q2 portfolio revenue → $735 million;
- Q-0012: net retention below 100% → Vantage Retail Analytics;
- Q-0013: highest EBITDA margin → Orbis Cybersecurity;
- Q-0022 SQL stage: candidate-scoped lower 2026 Q2 revenue.

Frozen Phase 8E1B boundary:

`phase-8e1b-portfolio-structured-sql`

### Phase 8E2 — Portfolio Relationship-Graph Execution

Implemented bounded portfolio existential graph predicates over the relational
Northstar relationship model.

Supported relationship families:

- company → supplier;
- company → customer.

Supported predicate fields include:

- target country;
- supplier criticality;
- supplier single-source status;
- relationship status.

Multiple predicates use independent existential semantics: each predicate may
be satisfied by a different relationship while all predicates must hold for the
same company. This is required for benchmark questions such as a company having
both a critical German supplier and a separate Swiss supplier.

The executor returns only the matched subgraph, including:

- deterministic matched company IDs;
- matched company / supplier / customer nodes;
- matched canonical relationship edges;
- direct node and relationship provenance.

`ToolExecutionPlan.graph` and the execution coordinator accept both bounded
known-start `GraphQuery` requests and portfolio-wide `PortfolioGraphQuery`
requests.

Verified against real PostgreSQL:

- Q-0014 → Alder Manufacturing and NovaBio Instruments;
- Q-0015 → Orbis Cybersecurity;
- Q-0016 → NovaBio Instruments using distinct qualifying supplier
  relationships;
- Q-0022 graph stage → candidate companies Alder Manufacturing and NovaBio
  Instruments.

Q-0022 was additionally verified by explicitly passing the graph-discovered
candidate IDs into bounded structured SQL, which selected NovaBio Instruments
at $83 million of 2026 Q2 revenue.

Frozen Phase 8E2B boundary:

`phase-8e2b-portfolio-graph-execution`

### Phase 8E3 — Execution-Coverage Confirmation

A coverage protocol was frozen before final mixed-tool confirmation.

Frozen protocol boundary:

`phase-8e3a-execution-coverage-protocol`

Frozen protocol report SHA-256:

`5970e7dbff67bc4fb2e1db5d86ee1116604fd1111b682b0eb31573b73ccc103f`

The confirmation evaluates 11 benchmark cases requiring SQL and/or graph
execution:

- 10 cases have verified executable primitive paths;
- 1 case is intentionally unsupported by the bounded metric vocabulary;
- 7 single-tool cases were verified;
- 3 explicit multi-tool compositions were verified.

Explicit mixed-tool confirmations:

Q-0020:

- bounded SQL identifies Vantage Retail Analytics from 2026 Q2 net retention;
- frozen Phase 6A RRF retrieval recovers
  `EVID-CORE-PC005-QMR-SIGNAL` at rank 1;
- the canonical retrieval evidence carries `RISK-005`.

Q-0021:

- bounded SQL identifies HelioGrid Energy from the highest 2026 Q2
  year-over-year revenue growth;
- frozen Phase 6A RRF retrieval recovers
  `EVID-CORE-PC004-RISK-PRIMARY` at rank 1;
- the canonical retrieval evidence carries `RISK-004`.

Q-0022:

- portfolio graph execution identifies `PC-002` and `PC-008`;
- those IDs are explicitly passed into candidate-scoped structured SQL;
- the SQL stage selects NovaBio Instruments at $83 million.

Q-0024:

- `customer_churn_rate` is not part of the bounded `StructuredMetric` contract;
- the request is rejected at typed validation;
- this demonstrates a bounded execution guardrail, not an implemented
  abstention decision.

Canonical confirmation artifact:

`artifacts/evaluation/phase8e3/execution-coverage-confirmation.json`

Canonical confirmation SHA-256:

`0089e0a0dabd5a4a24cb9fd9b7c39aa9c3be555add4a14377a2ac61710d3056e`

Reproducibility:

- canonical run used real persisted PostgreSQL data;
- retrieval used the frozen Phase 6A hybrid RRF stack;
- dense retrieval used pinned `intfloat/e5-small-v2`;
- dense model revision:
  `ffb93f3bd4047442299a41ebb6fa998a38507c52`;
- runtime device: CPU;
- an independent post-fix rerun reproduced the confirmation artifact
  byte-identically;
- independent rerun SHA-256 exactly matched the canonical artifact.

Interview evidence:

- designed typed bounded SQL and relationship-graph execution contracts;
- implemented parameterized portfolio aggregation, filtering, ranking, growth,
  and ratio operations;
- implemented candidate-scoped structured execution for upstream-tool handoff;
- implemented bounded portfolio existential graph predicates;
- implemented deterministic direct relational provenance;
- preserved frozen RRF retrieval semantics in mixed-tool execution tests;
- verified SQL, graph, retrieval+SQL, and graph→SQL primitive compositions
  against persisted PostgreSQL data;
- froze the execution-coverage protocol before mixed-tool confirmation;
- generated a deterministic byte-reproducible execution-coverage artifact;
- retained an unsupported-metric case as a documented system limitation rather
  than converting it into a false success.

Supports:

> Built typed, bounded retrieval, SQL, and relational-graph execution primitives
> with deterministic provenance and verified portfolio-level aggregation,
> ranking, graph predicates, and explicit multi-tool composition against
> persisted PostgreSQL data; confirmed 10 of 11 scoped benchmark cases had
> executable primitive paths while preserving an unsupported metric as a
> documented guardrail.

Important limitations:

The execution coordinator consumes an already-populated execution plan. It does
not yet infer dependencies between tools or dynamically feed one tool's result
into another.

The Q-0020 and Q-0021 confirmations are explicit parallel SQL/retrieval evidence
composition, not autonomous agent planning.

The Q-0022 confirmation explicitly passes graph output into SQL, but that
handoff is not yet selected or scheduled by an agent state machine.

No final answer-synthesis component has been implemented.

No downstream abstention node or abstention policy has been implemented.
Rejecting an unsupported `StructuredMetric` is therefore not equivalent to
producing a correct agent abstention.

Do not claim:

- autonomous agent planning;
- dependency-aware dynamic orchestration;
- LangGraph execution;
- autonomous graph-to-SQL chaining;
- implemented answer synthesis;
- implemented abstention behavior;
- free-form SQL generation;
- Neo4j execution;
- general enterprise benchmark coverage;
- production latency or throughput;
- GPU/CUDA execution.

## Phase 9B2 — Mixed-Tool LangGraph Orchestration Confirmation

**Status:** IMPLEMENTED / TESTED / MEASURED / REPRODUCIBLE / VERIFIED / FROZEN

### Scope

Confirmed the frozen Phase 9B1 `BoundedLangGraphRuntime`
against the existing Northstar mixed-tool benchmark cases using
persisted PostgreSQL data and the frozen hybrid retrieval stack.

Runtime boundary:

- Phase 9B1 commit:
  `476ff6ceeb37c5174183f353e8a08bfadbe0dc56`
- Phase 9B1 tag:
  `phase-9b1-bounded-langgraph-runtime`
- LangGraph:
  `1.2.11`
- Independent execution is intentionally sequential.
- No parallel-execution claim is made.

### Verified mixed-tool cases

**Q-0020 — independent retrieval + SQL**

- Execution order:
  `retrieval -> sql`
- Terminal status:
  `completed`
- SQL result:
  `PC-005` — Vantage Retail Analytics
- SQL provenance includes:
  `FIN-PC-005-2026Q2`
- Canonical retrieval evidence:
  `EVID-CORE-PC005-QMR-SIGNAL`
- Canonical retrieval rank:
  `1`
- Retrieval provenance includes:
  `RISK-005`
- No dependency handoff is produced.

**Q-0021 — independent retrieval + SQL**

- Execution order:
  `retrieval -> sql`
- Terminal status:
  `completed`
- SQL result:
  `PC-004` — HelioGrid Energy
- SQL provenance includes:
  `FIN-PC-004-2025Q2`,
  `FIN-PC-004-2026Q2`
- Canonical retrieval evidence:
  `EVID-CORE-PC004-RISK-PRIMARY`
- Canonical retrieval rank:
  `1`
- Retrieval provenance includes:
  `RISK-004`
- No dependency handoff is produced.

**Q-0022 — dependent graph -> SQL**

- Execution order:
  `graph -> sql`
- Terminal status:
  `completed`
- Graph candidates:
  `PC-002`, `PC-008`
- Materialized dependency handoff:
  `PC-002`, `PC-008`
- Downstream SQL candidate scope exactly equals the handoff.
- Original frozen SQL request remains unmodified with an empty
  candidate scope before dependency materialization.
- SQL result:
  `PC-008` — NovaBio Instruments
- SQL score:
  `83000000`
- Relationship evidence includes:
  `CS-003`, `CS-011`
- Candidate-scoped SQL provenance:
  `FIN-PC-002-2026Q2`,
  `FIN-PC-008-2026Q2`

### Reproducibility

Canonical artifact:

`artifacts/evaluation/phase9b2/orchestration-confirmation.json`

SHA-256:

`35c47a4f635cb7ac0dddff4adab42625e64fa365fe7b3a1b4fe86b0f361033d8`

Three independently executed confirmation runs produced
byte-identical JSON artifacts with the same SHA-256.

Source Phase 8E3B execution-confirmation artifact SHA-256:

`0089e0a0dabd5a4a24cb9fd9b7c39aa9c3be555add4a14377a2ac61710d3056e`

Frozen execution-coverage protocol report SHA-256:

`5970e7dbff67bc4fb2e1db5d86ee1116604fd1111b682b0eb31573b73ccc103f`

### Validation

- Phase 9B2 confirmation tests: `2 passed`
- Phase 9A + Phase 9B1 orchestration regression tests:
  `19 passed`
- Combined focused orchestration/evaluation tests:
  `21 passed`
- Full repository:
  `382 passed`
- Ruff:
  clean
- `git diff --check`:
  clean

### Claim boundary

Safe claim:

> Implemented and verified deterministic LangGraph orchestration
> across independent retrieval+SQL evidence workflows and a
> data-dependent graph-to-SQL candidate handoff, preserving typed
> execution contracts and provenance against persisted PostgreSQL
> data and the frozen hybrid retrieval stack; repeated evaluation
> produced byte-identical artifacts.

Do not claim:

- autonomous planning
- autonomous tool selection
- LLM-generated execution plans
- parallel execution
- arbitrary DAG execution
- arbitrary agent loops
- retries
- answer synthesis
- downstream sufficiency assessment
- abstention policy
- production latency or throughput
- GPU/CUDA execution

## Phase 9C1 — Evidence and Sufficiency Contracts

**Status:** IMPLEMENTED / TESTED / VERIFIED / FROZEN

### Scope

Introduced the typed answering boundary that separates tool execution
from later evidence-sufficiency decisions and answer synthesis.

This milestone defines contracts only. It does not implement a
sufficiency evaluator, abstention policy, or answer generator.

### Contracts

`EvidenceRecord`

- Normalizes one provenance-bearing unit of answering evidence.
- Supports retrieval, SQL, and relational-graph evidence.
- Requires canonical source fact IDs.
- Enforces deterministic sorted provenance.
- Retrieval evidence additionally requires document identity and rank.
- SQL and graph evidence cannot carry retrieval-only metadata.

`EvidenceBundle`

- Groups normalized evidence for one question.
- Represents four execution-side states:
  `completed`, `blocked`, `failed`, and `unsupported_request`.
- Allows a completed bundle with zero records so execution success is
  not incorrectly equated with answerability.
- Represents unsupported requests separately from execution failure.

`SufficiencyAssessment`

- Represents the later answerability decision as a typed outcome.
- Separates `sufficient` from `insufficient`.
- Requires exact supporting evidence IDs for sufficient decisions.
- Requires missing-information declarations for insufficient decisions.
- Prevents references to evidence records outside the bundle.
- Carries an explicit policy version.

### Abstention-boundary design

The contracts preserve two distinct insufficient-evidence paths:

- Post-execution insufficiency:
  execution may complete but fail to produce evidence sufficient to
  answer the requested fact.
- Unsupported request:
  the requested information cannot be represented by the bounded
  execution contract before valid execution occurs.

This distinction is intended to support the existing Northstar
insufficient-evidence cases without collapsing abstention into tool
failure or empty retrieval alone.

### Validation

- Phase 9C1 contract tests: `10 passed`
- Phase 9B orchestration regression tests: `21 passed`
- Full repository: `392 passed`
- Pydantic JSON round-trip:
  verified
- Ruff:
  clean
- `git diff --check`:
  clean

### Claim boundary

Safe claim:

> Designed and tested immutable typed evidence and sufficiency
> contracts that preserve canonical provenance across retrieval, SQL,
> and relational-graph evidence while distinguishing completed
> execution, blocked/failed execution, and unsupported requests.

Do not claim yet:

- an implemented sufficiency evaluator
- production abstention behavior
- Q-0023 abstention verification
- Q-0024 end-to-end abstention verification
- answer synthesis
- LLM-grounded generation
- confidence calibration
- autonomous planning
- autonomous tool selection

## Phase 9C2A — Execution Evidence Normalization

**Status:** IMPLEMENTED / TESTED / VERIFIED / FROZEN

### Scope

Implemented the deterministic adapter from terminal orchestration
snapshots into typed `EvidenceBundle` objects.

This milestone normalizes executor output only. It does not decide
whether the resulting evidence is sufficient to answer the question.

### Normalization behavior

Retrieval:

- Converts canonically grounded retrieval hits into
  `EvidenceRecord(kind="retrieval_hit")`.
- Preserves document identity, retrieval rank, source fact IDs, and
  evidence text.
- Sorts and deduplicates canonical fact provenance deterministically.
- Retrieved text without canonical provenance is not promoted into
  answering evidence.

SQL:

- Converts scalar structured results into `structured_value` records.
- Converts selected structured entities into `structured_entity`
  records.
- Preserves exact relational source-row provenance and entity-level
  canonical fact IDs.
- Empty structured payloads do not fabricate evidence.

Relational graph:

- Converts graph nodes into `graph_entity` records.
- Converts graph relationships into `graph_relationship` records.
- Preserves canonical graph-node and relationship provenance.
- Empty graph payloads do not fabricate evidence.

Terminal orchestration state:

- `completed` -> completed evidence bundle
- `blocked` -> blocked evidence bundle with typed detail
- `failed` -> failed evidence bundle with executor error detail
- non-terminal snapshots are rejected by the adapter

Unsupported bounded requests:

- Requests rejected before valid executor construction are represented
  separately through `unsupported_request_bundle`.
- Unsupported requests contain no execution evidence.

### Real-data verification

**Q-0023**

Question:

`What is Northstar's expected 2030 exit valuation for Meridian Health Systems?`

Observed behavior:

- Frozen LangGraph retrieval execution completed successfully.
- Frozen hybrid retrieval returned 10 grounded Meridian records.
- Evidence normalization produced:
  `EvidenceBundle(status="completed")`
- Normalized record count:
  `10`
- The records contain real Meridian operating, financial, risk,
  customer, and investment-thesis facts.
- No sufficiency decision was made in this milestone.

This case demonstrates that successful retrieval and non-empty,
entity-relevant evidence are not equivalent to answerability.

**Q-0024**

Question:

`What was Alder Manufacturing's exact customer churn rate in 2026 Q2?`

Observed behavior:

- `customer_churn_rate` remains outside the bounded
  `StructuredQuery` metric contract.
- The request was represented as:
  `EvidenceBundle(status="unsupported_request")`
- Record count:
  `0`
- The bundle carries an explicit unsupported-metric detail.

### Validation

- Phase 9C2A evidence normalization tests: `8 passed`
- Phase 9C1 contract regression tests: `10 passed`
- Phase 9B orchestration regression tests: `21 passed`
- Combined regression gate: `31 passed`
- Full repository: `400 passed`
- Ruff: clean
- `git diff --check`: clean

### Claim boundary

Safe claim:

> Implemented and tested a deterministic evidence-normalization layer
> that converts typed retrieval, SQL, and relational-graph execution
> results into immutable provenance-bearing evidence bundles, including
> explicit blocked, failed, and unsupported-request states.

Do not claim yet:

- an implemented sufficiency evaluator
- an implemented abstention policy
- Q-0023 abstention
- answer synthesis
- LLM-grounded generation
- confidence calibration
- autonomous planning
- autonomous tool selection

## Phase 9C2B — Deterministic Sufficiency and Abstention

**Status:** IMPLEMENTED / TESTED / MEASURED / VERIFIED / FROZEN

### Scope

Implemented a deterministic evidence-sufficiency policy over the typed
`EvidenceBundle` layer introduced in Phase 9C2A.

The evaluator operates over explicit, prevalidated
`EvidenceRequirement` objects.

It does not infer requirements from arbitrary natural-language
questions and does not use benchmark `answer_source_fact_ids` as
inference-time oracle information.

### Policy

Policy version:

`northstar-deterministic-sufficiency-v1`

Each `EvidenceRequirement` may constrain:

- allowed evidence tools
- allowed evidence kinds
- terms that must all occur
- terms for which at least one must occur

Each completed evidence bundle must be evaluated against at least one
explicit requirement.

A requirement is satisfied only when at least one normalized evidence
record satisfies all of its bounded constraints.

Different requirements may be satisfied by different evidence records.

The evaluator does not perform arbitrary semantic inference, learned
confidence scoring, or retrieval-score thresholding.

### Typed outcomes

Sufficient:

- status: `sufficient`
- reason: `evidence_supports_answer`
- exact supporting evidence record IDs are preserved

Insufficient:

- `no_relevant_evidence`
- `missing_required_information`
- `unsupported_request`
- `execution_failed`
- `blocked_dependency`

Unsupported, blocked, and failed bundles are converted directly into
typed insufficient outcomes without fabricating answering evidence.

### Real persisted verification

**Q-0001 — positive retrieval control**

Observed:

- sufficiency status: `sufficient`
- reason: `evidence_supports_answer`
- supporting record:
  `RET:001:EVID-CORE-PC006-RISK-PRIMARY`

This verified that a canonical retrieval record explicitly containing
the ORBIS-IDX-7 authentication-defect evidence satisfies the bounded
retrieval requirement.

**Q-0011 — positive structured control**

Observed:

- sufficiency status: `sufficient`
- reason: `evidence_supports_answer`
- supporting record:
  `SQL:VALUE:portfolio_metric_sum`

This verified that a structured portfolio revenue aggregate is accepted
when the evidence requirement explicitly requests a structured scalar
value.

**Q-0023 — post-execution insufficiency**

Question:

`What is Northstar's expected 2030 exit valuation for Meridian Health Systems?`

Observed:

- retrieval execution completed successfully
- the evidence bundle contained 10 grounded Meridian records
- sufficiency status: `insufficient`
- reason: `missing_required_information`
- supporting record IDs: none
- missing requirement:
  explicit evidence of Northstar's expected 2030 exit valuation

This verifies that non-empty, entity-relevant, canonically grounded
retrieval evidence is not automatically treated as sufficient.

**Q-0024 — unsupported bounded request**

Question:

`What was Alder Manufacturing's exact customer churn rate in 2026 Q2?`

Observed:

- `customer_churn_rate` remained outside the bounded
  `StructuredQuery` metric contract
- sufficiency status: `insufficient`
- reason: `unsupported_request`
- supporting record IDs: none

This verifies a separate pre-execution abstention path for requests that
cannot be represented by the bounded execution contract.

### Validation

- Phase 9C2B sufficiency tests: `10 passed`
- Phase 9C2A evidence-normalization regression tests: `8 passed`
- Phase 9C1 contract regression tests: `10 passed`
- Phase 9B orchestration regression tests: `21 passed`
- Full repository: `410 passed`
- Ruff: clean
- `git diff --check`: clean
- real persisted sufficiency check:
  `VERIFIED`

### Claim boundary

Safe claim:

> Implemented and verified a deterministic evidence-sufficiency and
> abstention layer over typed retrieval, SQL, and relational-graph
> evidence, preserving exact supporting provenance and distinguishing
> missing evidence, unsupported requests, execution failure, and blocked
> dependencies; verified both answerable controls and two distinct
> insufficient-evidence paths against persisted project data.

Also safe when more compact:

> Built a deterministic provenance-aware abstention layer that rejects
> unsupported or insufficiently evidenced answers rather than treating
> successful retrieval as sufficient evidence.

Do not claim yet:

- autonomous natural-language requirement generation
- learned sufficiency classification
- calibrated probabilistic confidence
- answer synthesis
- grounded natural-language answer generation
- LLM-generated final answers
- autonomous planning
- autonomous tool selection
- arbitrary agent loops

## Phase 9C3A — Grounded Answer and Abstention Contracts

**Status:** IMPLEMENTED / TESTED / VERIFIED / FROZEN

### Scope

Defined the immutable typed outcome boundary consumed by the later
grounded-synthesis layer.

Phase 9C3A introduces two mutually exclusive production outcomes:

- `GroundedAnswer`
- `AbstentionOutcome`

No answer-generation algorithm is implemented in this milestone.

### Grounded answer contract

A `GroundedAnswer` requires:

- a `SufficiencyAssessment(status="sufficient")`
- a typed answer form
- an answer value
- exact supporting evidence record IDs
- exact canonical source fact IDs
- an explicit synthesis-version identifier

Supported grounded answer types are:

- `text`
- `entity`
- `entities`
- `number`
- `boolean`

`abstain` is deliberately not a grounded-answer type.

Abstention is represented through a separate typed outcome.

### Provenance invariants

A grounded answer cannot change the evidence selected by the
sufficiency layer.

Its `supporting_record_ids` must exactly equal:

`SufficiencyAssessment.supporting_record_ids`

Its `source_fact_ids` must exactly equal the deterministic union of the
canonical source fact IDs attached to those selected records.

The contract therefore rejects:

- unknown or substituted supporting records
- added provenance
- removed provenance
- unrelated canonical fact IDs
- answers built from an insufficient assessment

This preserves the chain:

`executor provenance`
→ `EvidenceRecord`
→ `SufficiencyAssessment.supporting_record_ids`
→ `GroundedAnswer.source_fact_ids`

### Typed answer values

Structured values remain typed rather than being prematurely converted
to prose.

For example, a portfolio revenue result may remain:

- `answer_type="number"`
- `value=735000000`
- `unit="USD"`

Non-numeric answers cannot define units.

Numeric answers reject string-encoded numbers.

Entity-list answers require a non-empty tuple of unique entity strings.

Boolean answers require a real boolean value.

### Abstention contract

`AbstentionOutcome` requires:

- an insufficient sufficiency assessment
- the exact assessment reason
- the exact missing-information entries
- the exact supporting-record IDs, if any
- the exact sufficiency-policy version

The abstention contract therefore cannot drift from the previously
validated insufficiency decision.

### Discriminated outcome boundary

`AnswerOutcome` is a discriminated union over:

- `outcome="answer"` → `GroundedAnswer`
- `outcome="abstain"` → `AbstentionOutcome`

This keeps a typed non-answer distinct from a nullable or fabricated
answer value.

### Validation

- Phase 9C3A outcome-contract tests: `10 passed`
- Phase 9C2 regression tests: `18 passed`
- Phase 9C1 regression tests: `10 passed`
- Phase 9B regression tests: `21 passed`
- Full repository: `420 passed`
- Ruff: clean
- `git diff --check`: clean

### Claim boundary

Safe claim:

> Designed and tested immutable grounded-answer and abstention contracts
> that enforce exact provenance continuity from sufficiency-selected
> retrieval, SQL, and relational-graph evidence into typed answer
> outcomes.

Also safe:

> Enforced a typed answering boundary in which final-answer provenance
> must exactly match evidence selected by the sufficiency layer, while
> insufficient cases remain explicit abstention outcomes.

Do not claim yet:

- answer synthesis is implemented
- grounded answers are generated automatically
- natural-language generation
- LLM answer generation
- autonomous natural-language requirement generation
- learned sufficiency classification
- confidence calibration
- autonomous planning
- autonomous tool selection

## Phase 9C3B0 — Typed Synthesis Evidence Substrate

**Status:** IMPLEMENTED / TESTED / MEASURED / VERIFIED / FROZEN

### Scope

Extended the normalized answering-evidence boundary with optional,
machine-readable synthesis data while preserving the existing
human-readable evidence summaries and canonical provenance.

This milestone does not implement final answer synthesis.

Its purpose is to ensure typed executor outputs remain typed after
normalization so later answer construction does not have to reverse-parse
internally generated prose.

### Typed evidence substrate

Structured scalar evidence now preserves:

- scalar value
- unit

Structured entity evidence now preserves:

- entity ID
- entity name
- operation score when present
- score unit when present

Graph entity evidence now preserves:

- entity type
- entity ID
- entity name

Graph relationship evidence now preserves:

- relationship type
- relationship ID
- source type and ID
- target type and ID

Retrieval evidence deliberately does not receive a parallel structured
payload. Its canonically grounded source text remains the authoritative
answering substrate.

### Backward compatibility

`EvidenceRecord.data` is optional.

Existing evidence records constructed before this milestone remain valid
without typed synthesis data.

The new normalization path populates typed data for structured SQL and
relational-graph evidence.

### Validation invariants

Typed evidence data must match the containing `EvidenceRecord.kind`.

Retrieval records reject structured synthesis data entirely.

Canonical source fact provenance remains unchanged and continues to be
validated independently of the typed synthesis payload.

### Persisted verification

Real PostgreSQL execution verified preservation of:

**Portfolio revenue aggregate**

- evidence kind: `structured_value`
- value: `735000000`
- unit: `USD`

**Highest year-over-year revenue growth**

- evidence kind: `structured_entity`
- entity ID: `PC-004`
- entity name: `HelioGrid Energy`
- score unit: `ratio`

Marker:

`phase9c3b0_typed_substrate: VERIFIED`

### Validation

- Phase 9C3B0 substrate tests: `6 passed`
- Phase 9C3A regression tests: `10 passed`
- Phase 9C2 regression tests: `18 passed`
- Phase 9C1 regression tests: `10 passed`
- Phase 9B regression tests: `21 passed`
- Full repository: `426 passed`
- Ruff: clean
- `git diff --check`: clean
- persisted PostgreSQL typed-substrate verification: `VERIFIED`

### Claim boundary

Safe claim:

> Preserved machine-readable scalar, entity, and graph identity data
> through the normalized evidence layer while retaining exact canonical
> provenance, eliminating the need to reverse-parse internally generated
> prose during downstream answer construction.

Also safe:

> Added a typed synthesis substrate that carries structured SQL and
> relational-graph results through evidence normalization without losing
> their machine-readable values or identities.

Do not claim yet:

- final answer synthesis is implemented
- natural-language answer generation
- LLM answer generation
- autonomous planning
- autonomous tool selection
- autonomous natural-language requirement generation
- learned sufficiency classification
- probabilistic confidence calibration

## Phase 9C3B1 — Deterministic Grounded Synthesis

**Status:** IMPLEMENTED / TESTED / VERIFIED / FROZEN

### Scope

Implemented a bounded deterministic synthesis layer over the previously
verified evidence and sufficiency boundaries.

The synthesizer consumes:

- a `SufficiencyAssessment`
- an explicit validated `SynthesisInstruction`
- only evidence records selected by
  `SufficiencyAssessment.supporting_record_ids`

It produces either:

- a typed `GroundedAnswer`
- a typed `AbstentionOutcome`

This milestone does not infer synthesis instructions from arbitrary
natural-language questions.

### Synthesis modes

Version:

`northstar-deterministic-grounded-synthesis-v1`

Supported bounded modes are:

- `retrieval_text`
- `structured_value`
- `entity_name`
- `entity_names`

`retrieval_text` returns the exact selected grounded retrieval text.

`structured_value` consumes machine-readable structured evidence and
supports bounded typed scalar answers.

`entity_name` returns one machine-readable SQL or graph entity name.

`entity_names` returns a deterministic tuple of selected entity names.

### Evidence boundary

A synthesis instruction cannot reference an evidence record that was not
selected by the sufficiency layer.

The implementation therefore enforces:

`sufficiency-selected evidence`
→ `explicit synthesis instruction`
→ `typed grounded outcome`

Evidence present in the bundle but absent from
`supporting_record_ids` cannot become answer material.

### Provenance continuity

Final `GroundedAnswer.supporting_record_ids` exactly matches the
sufficiency assessment.

Final `GroundedAnswer.source_fact_ids` is the deterministic union of
canonical fact IDs from all sufficiency-selected supporting records.

This is deliberately broader than the subset of records used to render
the answer value.

That distinction preserves provenance for multi-source or dependent
workflows in which one selected record may provide the displayed answer
while additional selected records establish the evidence chain.

### Structured-value safety

Numeric answer construction requires a machine-readable numeric value.

String values such as `"123"` are not parsed into numbers.

The synthesizer therefore does not recover typed answers by parsing
`EvidenceRecord.summary`.

Units are preserved for numeric structured values.

Boolean and text scalar modes reject incompatible values or units rather
than silently coercing them.

### Abstention

An insufficient `SufficiencyAssessment` does not require a synthesis
instruction.

It deterministically produces an `AbstentionOutcome` preserving:

- insufficiency reason
- missing-information entries
- supporting-record IDs, if any
- sufficiency-policy version

No answer value is fabricated when evidence is insufficient or the
request is unsupported.

### Verification

#### Persisted SQL controls

Real PostgreSQL-backed bounded execution verified:

**Q0011 — portfolio revenue**

- answer type: `number`
- value: `735000000`
- unit: `USD`

**Q0010 — highest year-over-year revenue growth**

- answer type: `entity`
- value: `HelioGrid Energy`

These controls exercised:

SQL execution
→ normalized typed evidence
→ deterministic sufficiency
→ deterministic synthesis
→ typed grounded answer.

#### Abstention-boundary controls

Explicit answering-boundary controls verified:

**Q0023**

- outcome: `abstain`
- reason: `missing_required_information`

**Q0024**

- outcome: `abstain`
- reason: `unsupported_request`

These two controls verify synthesis/abstention semantics.

They are not claimed here as end-to-end persisted retrieval or routing
executions.

Marker:

`phase9c3b1_grounded_synthesis: VERIFIED`

### Validation

- Phase 9C3B1 synthesis tests: `11 passed`
- Phase 9C3B0 regression tests: `6 passed`
- Phase 9C3A regression tests: `10 passed`
- Phase 9C2 regression tests: `18 passed`
- Phase 9C1 regression tests: `10 passed`
- Phase 9B regression tests: `21 passed`
- Full repository: `437 passed`
- Ruff: clean
- `git diff --check`: clean
- persisted SQL synthesis controls: `VERIFIED`
- explicit abstention-boundary controls: `VERIFIED`

### Claim boundary

Safe claim:

> Implemented and tested a deterministic grounded-synthesis layer that
> constructs typed answers exclusively from sufficiency-selected
> retrieval, SQL, or relational-graph evidence while preserving exact
> canonical provenance and explicit abstention semantics.

Also safe:

> Enforced a bounded answer-construction boundary that preserves typed
> structured values and entity identities, rejects evidence outside the
> sufficiency-selected support set, and abstains rather than fabricating
> unsupported answers.

Also safe:

> Verified PostgreSQL-backed structured numeric and entity answers across
> execution, evidence normalization, sufficiency, and deterministic
> synthesis.

Do not claim yet:

- free-form natural-language answer generation
- LLM answer generation
- autonomous synthesis-instruction generation
- autonomous natural-language requirement generation
- autonomous planning
- autonomous tool selection
- learned sufficiency classification
- probabilistic confidence calibration
- Q0023 end-to-end retrieval verification in this milestone
- full benchmark answer-generation accuracy

## Phase 9C4A — End-to-End Answering Evaluation Protocol

**Status:** IMPLEMENTED / TESTED / VERIFIED / REPRODUCIBLE / FROZEN

### Scope

Frozen a five-case stage-resolved evaluation protocol for the answering
pipeline introduced in Phase 9C.

Protocol version:

`northstar-answering-evaluation-v1`

Dataset version:

`northstar-v1`

Evaluation seed:

`northstar-eval-v1-seed`

Selected cases:

- `Q-0001` — lexical retrieval / grounded text
- `Q-0010` — SQL / entity
- `Q-0011` — SQL / numeric value with unit
- `Q-0023` — real retrieval / insufficient evidence
- `Q-0024` — bounded unsupported structured request

The protocol freezes execution plans, deterministic evidence
requirements, synthesis modes, comparison modes, and expected typed
abstention reasons.

It does not contain benchmark expected-answer values, benchmark
answer-source fact IDs, or benchmark relevance judgments.

### Non-oracular construction boundary

Execution and answering specifications are built independently of the
benchmark answer oracle.

The frozen protocol serialization excludes:

- `expected_answer`
- `answer_source_fact_ids`
- `relevance_judgments`
- `answerable`

An independent audit also verified that the serialized protocol contains
none of the selected benchmark expected-answer literals or canonical
answer-source fact IDs.

Marker:

`phase9c4a_oracle_leak_audit: VERIFIED`

### Text-answer comparison rule

`Q-0001` intentionally does not use exact string equality against the
benchmark's concise canonical text answer.

The deterministic synthesizer's `retrieval_text` mode returns the exact
selected grounded retrieval evidence rather than generating or rewriting
a concise natural-language answer.

A retrieval-text answer therefore passes only when:

- the observed answer type is `text`
- the selected evidence record is a benchmark grade-3 canonical
  retrieval judgment
- final provenance contains the benchmark canonical answer-source fact
  IDs
- supporting record IDs are valid
- final source-fact provenance exactly matches the selected evidence

This scores retrieval grounding rather than unimplemented free-form
natural-language rewriting.

Benchmark relevance judgments and answer-source facts are used only
during post-hoc scoring; they do not influence retrieval, sufficiency,
or synthesis.

### Structured-answer comparison

`Q-0010` uses normalized exact entity comparison.

`Q-0011` uses numeric comparison with the benchmark tolerance plus exact
unit comparison.

Both additionally require:

- valid sufficiency-selected support
- exact internal source-fact provenance
- inclusion of the benchmark canonical answer-source facts

### Abstention comparison

`Q-0023` expects typed:

`missing_required_information`

after successful frozen retrieval fails the explicit evidence
requirement for an expected 2030 exit valuation.

`Q-0024` expects typed:

`unsupported_request`

for a metric outside the bounded `StructuredQuery` contract.

### Frozen artifact

Artifact:

`artifacts/answering/phase9c4a_answering_evaluation_protocol.json`

Canonical SHA-256:

`31a2c3e2294e1b6954cf5955e8467fa012869e10d789055bdbc6b75ca6232ad6`

The artifact was regenerated independently and verified byte-identical.

Marker:

`phase9c4a_reproducibility: VERIFIED`

### Validation

- Phase 9C4A protocol/comparator tests: `13 passed`
- Phase 9C3B1 regression tests: `11 passed`
- Phase 9C3B0 regression tests: `6 passed`
- Phase 9C3A regression tests: `10 passed`
- Phase 9C2 regression tests: `18 passed`
- Phase 9B regression tests: `21 passed`
- Full repository: `450 passed`
- Ruff: clean
- `git diff --check`: clean
- oracle-leak audit: `VERIFIED`
- canonical protocol regeneration: byte-identical

### Claim boundary

Safe claim:

> Designed and froze a reproducible, non-oracular end-to-end answering
> evaluation protocol spanning retrieval grounding, structured numeric
> and entity answers, provenance validation, and typed abstention.

Also safe:

> Implemented stage-resolved answer evaluation that separates answer
> type, value or canonical evidence correctness, unit correctness,
> support validity, provenance validity, and abstention-reason
> correctness.

Do not claim yet:

- the five-case end-to-end protocol has been executed as one formal
  confirmation artifact
- full benchmark answering accuracy
- free-form natural-language answer generation
- LLM answer generation
- autonomous synthesis-instruction generation
- autonomous requirement generation
- autonomous planning or tool selection
- learned sufficiency classification
- probabilistic confidence calibration

## Phase 9C4B — End-to-End Answering Confirmation

**Status:** IMPLEMENTED / TESTED / MEASURED / VERIFIED / REPRODUCIBLE

### Scope

Executed the frozen Phase 9C4A five-case answering protocol against the
real persisted Northstar dataset and the frozen production execution
components.

The confirmation exercised:

- frozen BM25 + E5 + reciprocal-rank-fusion retrieval
- persisted PostgreSQL structured execution
- bounded LangGraph orchestration
- typed evidence normalization
- deterministic evidence sufficiency
- deterministic grounded synthesis
- typed abstention
- post-hoc benchmark comparison
- canonical provenance validation

Confirmation version:

`northstar-answering-confirmation-v1`

Frozen protocol version:

`northstar-answering-evaluation-v1`

Frozen protocol canonical SHA-256:

`31a2c3e2294e1b6954cf5955e8467fa012869e10d789055bdbc6b75ca6232ad6`

### Result

Formal selected-case result:

- cases: `5`
- passed: `5`
- failed: `0`
- selected-case pass rate: `5/5`

This is a five-case integration confirmation, not a claim of full
24-case benchmark answering accuracy.

### Q-0001 — grounded retrieval answer

Real frozen retrieval returned the canonical Orbis risk evidence as the
first hit.

The answering pipeline produced:

- execution: `completed`
- tool: `retrieval`
- evidence: `completed`
- sufficiency: `sufficient`
- outcome: `answer`
- answer type: `text`
- selected support:
  `RET:001:EVID-CORE-PC006-RISK-PRIMARY`
- canonical source fact: `RISK-006`

Post-hoc evaluation verified:

- answer type correctness
- canonical grade-3 retrieval evidence correctness
- support validity
- exact internal source-fact provenance
- benchmark answer-source provenance inclusion

### Q-0010 — structured entity answer

Real PostgreSQL execution produced:

`HelioGrid Energy`

The path was:

SQL
→ LangGraph terminal snapshot
→ typed structured entity evidence
→ deterministic sufficiency
→ deterministic entity synthesis
→ exact normalized entity comparison.

The selected answer passed value, support, and provenance checks.

### Q-0011 — structured numeric answer

Real PostgreSQL execution produced:

`735000000 USD`

The final evidence preserved all eight canonical Q2 2026 portfolio
revenue fact IDs.

The answer passed:

- numeric value comparison
- exact unit comparison
- support validation
- internal provenance validation
- benchmark answer-source provenance validation

### Q-0023 — retrieval insufficiency

Real frozen retrieval completed successfully and returned ten grounded
Meridian evidence records.

None satisfied the explicit requirement for Northstar's expected 2030
exit valuation.

The deterministic answering layer therefore produced:

- sufficiency: `insufficient`
- reason: `missing_required_information`
- outcome: `abstain`

This verifies a real retrieval-to-abstention path rather than a
hand-constructed insufficiency bundle.

### Q-0024 — unsupported bounded request

The requested `customer_churn_rate` metric was independently verified to
be rejected by the bounded `StructuredQuery` contract.

The answering layer produced:

- evidence status: `unsupported_request`
- sufficiency: `insufficient`
- reason: `unsupported_request`
- outcome: `abstain`

No SQL was executed and no unsupported value was fabricated.

### Frozen retrieval configuration observed during confirmation

- retriever: `hybrid:rrf-k60-v1`
- BM25 representation: `document-title-text-v1`
- dense representation: `e5-document-title-text-v1`
- dense model: `intfloat/e5-small-v2`
- model revision:
  `ffb93f3bd4047442299a41ebb6fa998a38507c52`
- embedding dimension: `384`
- RRF k: `60`
- device: `cpu`
- batch size: `16`
- persisted evidence chunks: `80`

### Reproducibility

Formal artifact:

`artifacts/answering/phase9c4b_answering_confirmation.json`

Exact artifact-file SHA-256:

`dabd7446984fd5d405c90a0c3d29b26df1b7578a9c30f1983476c88f8bb63668`

The persisted report was regenerated in a separate real execution and
verified byte-identical.

Execution-duration fields are intentionally excluded from the artifact
because wall-clock timing is nondeterministic and is not part of answer
correctness.

Markers:

`phase9c4b2_real_persisted_confirmation: VERIFIED`

`phase9c4b_reproducibility: VERIFIED`

### Validation

- Phase 9C4B1 confirmation-runner tests: `6 passed`
- Phase 9C4A protocol/comparator tests: `13 passed`
- Phase 9C3B1 synthesis tests: `11 passed`
- Phase 9C2 regression tests: `18 passed`
- Phase 9B regression tests: `21 passed`
- Full repository: `456 passed`
- Ruff: clean
- `git diff --check`: clean
- real persisted selected-case confirmation: `5/5`
- formal artifact regeneration: byte-identical

### Claim boundary

Safe claim:

> Built and verified a reproducible end-to-end grounded-answering
> pipeline spanning frozen hybrid retrieval, PostgreSQL structured
> execution, LangGraph orchestration, deterministic evidence
> sufficiency, grounded synthesis, exact provenance validation, and
> typed abstention.

Also safe:

> Achieved 5/5 on a frozen, non-oracular integration control set covering
> retrieval grounding, structured entity and numeric answers, missing
> evidence abstention, and unsupported-request abstention.

Also safe:

> Verified the selected integration controls against persisted data and a
> frozen CPU E5/BM25/RRF retrieval stack, with byte-reproducible
> stage-resolved evaluation artifacts.

Do not claim:

- 100% accuracy on the complete 24-case benchmark
- full benchmark answer-generation accuracy
- free-form natural-language generation
- LLM answer generation
- autonomous planning
- autonomous tool selection
- autonomous evidence-requirement generation
- autonomous synthesis-instruction generation
- learned sufficiency or confidence calibration

## Phase 10A — Grounded Generation Authority Boundary

**Status:** IMPLEMENTED / TESTED / VERIFIED / REPRODUCIBLE / FROZEN

### Scope

Introduced an explicit authority boundary between the deterministic
answering system and future probabilistic language generation.

Generation policy version:

`northstar-grounded-generation-policy-v1`

The boundary preserves the deterministic answering outcome as the
authoritative source of:

- answer versus abstention state
- answer type
- typed answer value
- numeric unit
- abstention reason
- missing-information detail
- sufficiency-selected supporting records
- canonical source-fact provenance
- allowed citation IDs

The generation provider is not permitted to expand any of those fields.

### Selected-evidence boundary

Generation does not receive the full retrieval result set.

Only records selected by deterministic sufficiency are exposed through
`GroundedGenerationRequest`.

Real persisted verification demonstrated:

- `Q-0001`: 10 retrieval records → 1 generation record
- `Q-0010`: 1 structured evidence record → 1 generation record
- `Q-0011`: 1 structured evidence record → 1 generation record
- `Q-0023`: 10 retrieval records → 0 generation records
- `Q-0024`: 0 evidence records → 0 generation records

For `Q-0001`, the only generation-visible record was:

`RET:001:EVID-CORE-PC006-RISK-PRIMARY`

with canonical source fact:

`RISK-006`

The other nine retrieved records were excluded from serialized generation
context.

### Structured authority

For `Q-0011`, the deterministic authority crossing the generation boundary
remained exactly:

`735000000 USD`

with all eight canonical 2026 Q2 portfolio revenue fact IDs.

The generation layer therefore cannot redefine the authoritative numeric
value without violating the contract.

### Abstention authority

For `Q-0023`, real retrieval produced ten grounded records, but
deterministic sufficiency selected none.

The generation request therefore contained:

- outcome: `abstain`
- reason: `missing_required_information`
- generation evidence: none
- citation IDs: none

For `Q-0024`, the unsupported structured request crossed the boundary as:

- outcome: `abstain`
- reason: `unsupported_request`
- generation evidence: none
- citation IDs: none

A future language model cannot turn either abstention into an authorized
answer.

### Contract hardening

The boundary rejects:

- answer-type / authoritative-value mismatches
- generation questions that differ from the deterministic outcome question
- evidence outside sufficiency-selected support
- citation IDs outside sufficiency-selected support
- canonical provenance mismatches
- grounding-policy version overrides
- answer fields attached to abstention authority

### Formal artifact

Artifact:

`artifacts/generation/phase10a_generation_authority_confirmation.json`

Exact artifact-file SHA-256:

`94225514dee475b5a29d0297f522399bff105ab993e536e75a5df27c51686769`

The artifact was independently regenerated and verified byte-identical.

### Validation

- Phase 10A contract tests: `13 passed`
- Phase 9C4B regression tests: `6 passed`
- Phase 9C4A regression tests: `13 passed`
- answering regression tests: `49 passed`
- full repository: `469 passed`
- Ruff: clean
- `git diff --check`: clean
- real persisted authority-boundary probe: `VERIFIED`
- formal artifact regeneration: byte-identical

### Claim boundary

Safe claim:

> Designed and verified a deterministic authority boundary that restricts
> probabilistic generation to sufficiency-selected evidence while
> preserving typed answer values, canonical provenance, citation
> allowlists, and abstention decisions.

Also safe:

> Verified on persisted retrieval and SQL execution that unselected
> retrieval candidates are excluded from generation context; one case
> reduced 10 retrieved records to 1 authorized generation record, while
> an insufficient-evidence case reduced 10 grounded records to zero.

Do not claim yet:

- a generative language model is implemented
- LLM output has been validated
- hallucination rate has been measured
- generated citations have been validated
- free-form generated answer quality has been benchmarked

## Phase 10B1 — Pinned Local Causal-LM Provider

**Status:** IMPLEMENTED / TESTED / VERIFIED / FROZEN

### Scope

Implemented a real local Hugging Face causal-language-model provider behind
the frozen Phase 10A deterministic generation-authority boundary.

Direct runtime dependency:

`transformers==5.16.1`

Pinned model:

`Qwen/Qwen2.5-0.5B-Instruct`

Pinned immutable model revision:

`7ae557604adf67be50417f59c2c2f167def9a775`

Provider version:

`northstar-hf-causal-generation-provider-v1`

### Runtime configuration

Verified real model execution with:

- model class: `Qwen2ForCausalLM`
- total parameters: `494032768`
- execution device: `cpu`
- parameter dtype: `torch.float32`
- Torch intra-op threads: `6`
- Torch inter-op threads: `6`
- CUDA available: `False`
- greedy decoding: `do_sample=False`
- pinned immutable model revision
- model chat template enabled

No GPU or CUDA execution claim is made.

### Provider boundary

`HuggingFaceCausalGenerationProvider`:

1. accepts only a frozen `GroundedGenerationRequest`
2. renders deterministic authority and sufficiency-selected evidence
3. loads the pinned local causal LM
4. performs greedy CPU generation
5. returns `RawGeneration`
6. attaches provider/model/revision/device/dtype metadata

`RawGeneration` remains explicitly untrusted.

The provider does not:

- select tools
- retrieve evidence
- perform sufficiency assessment
- change deterministic answer authority
- validate its own factual fidelity
- decide whether generated text is safe to return

Those responsibilities remain outside the probabilistic model.

### Real persisted provider probe

The provider was executed against the same five persisted controls used by
the grounded-answering integration confirmation.

#### Q-0001 — retrieval text answer

Authority:

`RISK-006`

Observed raw generation preserved the ORBIS-IDX-7 authentication-defect
content without introducing a conflicting fact.

#### Q-0010 — structured entity answer

Authority:

`HelioGrid Energy`

Observed raw generation:

`HelioGrid Energy (PC-004) had the highest year-over-year revenue growth in 2026 Q2.`

The authoritative entity remained present.

#### Q-0011 — structured numeric answer

Authority:

`735000000 USD`

Observed raw generation:

`Total portfolio revenue for 2026 Q2 was $735 million USD.`

`735 million` is mathematically equivalent to `735000000`, but the raw model
did not preserve the authoritative numeric representation exactly.

Under the planned strict generation-fidelity policy, raw output is not
automatically trusted merely because it appears semantically equivalent.

#### Q-0023 — missing-information abstention

Authority:

- outcome: `abstain`
- reason: `missing_required_information`
- generation evidence: none

Observed raw generation:

`Northstar expects Meridian Health Systems' 2030 exit valuation to be $15 billion.`

This is a direct hallucination and an explicit violation of deterministic
abstention authority.

#### Q-0024 — unsupported-request abstention

Authority:

- outcome: `abstain`
- reason: `unsupported_request`
- generation evidence: none

Observed raw generation:

`Alder Manufacturing had no known customer churn rate for Q2 2026.`

This changes an unsupported-query condition into an unsupported substantive
claim about company data and therefore cannot be trusted.

### Engineering conclusion

Prompt instructions alone are insufficient to preserve deterministic
authority.

A real greedy local instruct model violated:

- abstention semantics
- unsupported-request semantics
- strict numeric representation preservation

even though the prompt explicitly described the authority object as
immutable.

Therefore generated text must be treated as hostile/untrusted output and
validated after generation.

Phase 10C will implement deterministic generation-fidelity validation and
fallback behavior rather than relying on prompt compliance.

### Validation

- Phase 10B1 provider tests: `5 passed`
- Phase 10A regression tests: `13 passed`
- full repository: `474 passed`
- Ruff: clean
- `git diff --check`: clean
- real pinned causal-LM provider probe: `COMPLETED`
- Phase 10A remains an ancestor

### Claim boundary

Safe claim:

> Implemented a pinned local Hugging Face causal-LM provider using
> Qwen2.5-0.5B-Instruct on CPU with deterministic greedy decoding and
> reproducibility metadata, behind a deterministic evidence-and-authority
> boundary.

Also safe:

> Empirically demonstrated that raw LLM generation can violate deterministic
> abstention and numeric-preservation constraints, motivating explicit
> post-generation fidelity validation and deterministic fallback.

Do not claim yet:

- LLM-generated answers are grounded
- generated answers are safe to return directly
- hallucination prevention is implemented
- generated citations are validated
- generation fidelity has been formally measured
- bad generations are automatically rejected
- deterministic fallback after generation is implemented

## Phase 10C — Grounded Generation Fidelity & Deterministic Fallback

**Status:** VERIFIED / REPRODUCIBLE / FROZEN pending commit/tag

### Scope

Implemented a guarded local-LLM presentation layer on top of the existing
deterministic execution, evidence, sufficiency, synthesis, provenance, and
abstention pipeline.

The probabilistic model does not control retrieval, SQL/graph execution,
sufficiency, deterministic authority, provenance, or abstention. It receives
only the frozen `GroundedGenerationRequest` authority and its
sufficiency-selected evidence.

### Local generation provider

- Model: `Qwen/Qwen2.5-0.5B-Instruct`
- Immutable revision:
  `7ae557604adf67be50417f59c2c2f167def9a775`
- Provider:
  `northstar-hf-causal-generation-provider-v1`
- Runtime: CPU
- dtype: float32
- CUDA observed: false
- Decoding: deterministic greedy generation

### Fidelity validation

Policy:

`northstar-generation-fidelity-v1`

Raw model text is treated as untrusted.

The deterministic validator mechanically checks properties including:

- deterministic abstention authority,
- strict authoritative text preservation for text answers,
- exact authoritative entity preservation,
- exact numeric-literal preservation,
- unit preservation,
- boolean preservation,
- unauthorized numeric literals,
- citation IDs outside the frozen allowlist.

Rejected model output has `safe_text=None`.

The validator intentionally does **not** claim general semantic equivalence,
semantic hallucination detection, or factual verification of arbitrary
free-form prose.

### Guarded presentation boundary

Policy:

`northstar-safe-generation-presentation-v1`

`resolve_safe_generation(...)` enforces:

- accepted fidelity assessment -> exact approved model text may cross the
  presentation boundary;
- rejected fidelity assessment -> raw model text is not presentation-eligible
  and exact deterministic authority is rendered instead.

`SafeGenerationResult` validates that rejected text cannot be mislabeled as
approved model output and that fallback text cannot be replaced with arbitrary
content.

### Real persisted five-case confirmation

Formal confirmation version:

`northstar-guarded-generation-confirmation-v1`

Cases:

- `Q-0001` — retrieval-backed Orbis risk answer
- `Q-0010` — PostgreSQL-backed highest-growth entity answer
- `Q-0011` — PostgreSQL-backed portfolio revenue numeric answer
- `Q-0023` — missing-required-information abstention
- `Q-0024` — unsupported-request abstention

Observed results:

- cases: 5
- fidelity accepted: 1
- fidelity rejected: 4
- model generation presented: 1
- deterministic fallback presented: 4
- rejected raw generations exposed: 0

Case behavior:

- `Q-0001`
  - Qwen paraphrased the authoritative retrieval text.
  - Rejected under strict text-preservation policy.
  - Presentation used the exact deterministic authority text.

- `Q-0010`
  - Qwen preserved `HelioGrid Energy` and stayed within the mechanical
    fidelity constraints.
  - Accepted and presented as model generation.

- `Q-0011`
  - Deterministic authority: `735000000 USD`.
  - Qwen produced `$735 million USD`.
  - Rejected for exact numeric-literal preservation and unauthorized numeric
    literal introduction.
  - Presentation fell back to `735000000 USD`.

- `Q-0023`
  - Deterministic authority required abstention for missing evidence.
  - Qwen hallucinated a `$15 billion` 2030 exit valuation.
  - Rejected for abstention-semantics violation and unauthorized numeric claim.
  - Presentation used deterministic missing-information abstention and did not
    expose `$15 billion`.

- `Q-0024`
  - Deterministic authority marked the requested churn metric unsupported.
  - Qwen converted this into a substantive "no known customer churn rate"
    statement.
  - Rejected for abstention-semantics violation.
  - Presentation used deterministic unsupported-request fallback and did not
    expose the substantive model claim.

### Reproducibility artifact

Artifact:

`artifacts/generation/phase10c_guarded_generation_confirmation.json`

Exact file SHA-256:

`471f99f0f9df37363dcdff5c51e5ee6d0a4454215a115870239b3f330db751bf`

The report was independently regenerated through the persisted PostgreSQL /
frozen retrieval / deterministic answering / pinned Qwen / fidelity /
presentation pipeline and was byte-identical to the persisted artifact.

### Verification

At the Phase 10C freeze candidate:

- Phase 10C fidelity/guarded tests: 27 passing
- Formal confirmation tests: 6 passing
- Full repository: 507 passing
- Ruff: clean
- `git diff --check`: clean
- Phase 10B1 frozen ancestor remained unchanged before the Phase 10C commit

### Claim boundary

Supported claim:

> Implemented a pinned local Hugging Face causal-LM generation layer with
> deterministic fidelity checks and fail-closed presentation fallback. On a
> five-case persisted integration control set spanning retrieval, structured
> numeric/entity answers, missing-evidence abstention, and unsupported-request
> abstention, four noncompliant model generations were rejected and replaced by
> deterministic authority, with zero rejected raw generations crossing the
> presentation boundary.

Do **not** claim:

- general hallucination prevention,
- semantic correctness of arbitrary free-form generations,
- 100% generation accuracy,
- evaluation on the complete 24-case benchmark,
- learned factuality or confidence scoring,
- autonomous LLM planning or tool selection,
- autonomous sufficiency decisions,
- autonomous provenance generation,
- that deterministic lexical guardrails prove semantic faithfulness.

This phase establishes a conservative mechanical safety boundary and verified
fallback behavior, not a general-purpose semantic factuality guarantee.

## Phase 10D1 — Deterministic vs Raw-LLM vs Guarded-LLM Comparison Protocol

**Status:** VERIFIED / FROZEN pending commit/tag

### Purpose

Frozen comparison protocol for evaluating three presentation paths:

1. `deterministic`
2. `raw_llm`
3. `guarded_llm`

The protocol is frozen before comparative scores are computed.

### Protocol

Version:

`northstar-generation-comparison-v1`

Frozen five-case integration control set:

- `Q-0001`
- `Q-0010`
- `Q-0011`
- `Q-0023`
- `Q-0024`

Mechanical metrics include:

- authority preservation,
- abstention preservation,
- exact numeric-literal preservation,
- unit preservation,
- entity preservation,
- absence of unauthorized numeric literals,
- absence of unauthorized citation IDs,
- rejected raw-generation non-exposure.

The five cases define 25 applicable case/metric checks across each of the
three systems.

### Methodological boundary

This protocol is **not blind or preregistered**.

The individual Phase 10C model behaviors had already been observed before this
Phase 10D comparison protocol was defined. The defensible methodological claim
is narrower: the metric matrix and scoring rules are frozen before comparative
scores are computed.

The protocol evaluates deterministic mechanical fidelity properties. It does
not establish general semantic answer accuracy, factuality of arbitrary
free-form prose, or performance on the complete 24-case benchmark.

### Verification

At the Phase 10D1 freeze candidate:

- comparison protocol tests: 9 passing
- Phase 10C regression tests: 33 passing
- full repository: 516 passing
- Ruff: clean
- `git diff --check`: clean
- Phase 10C frozen boundary remained unchanged

No comparative score has been computed as part of Phase 10D1.

## Phase 10D2 — Mechanical Generation Comparison Scorer

**Status:** VERIFIED / FROZEN pending commit/tag

### Purpose

Implemented the scorer for the frozen Phase 10D1 comparison protocol before
running the real three-system comparison.

The scorer compares:

1. `deterministic`
2. `raw_llm`
3. `guarded_llm`

against the mechanical case/metric matrix frozen in Phase 10D1.

### Scoring model

The scorer produces typed:

- `MechanicalMetricResult`
- `GenerationSystemScore`

and evaluates only the metrics declared by each frozen comparison case.

Metrics include:

- authority preservation,
- abstention preservation,
- exact numeric-literal preservation,
- unit preservation,
- entity preservation,
- absence of unauthorized numeric literals,
- absence of unauthorized citation IDs,
- rejected raw-generation non-exposure.

### Abstention hardening

Abstention scoring does not grant credit based on the system name.

Instead, the scorer requires explicit typed presentation metadata:

- `presented_outcome`
- `presented_reason`

For deterministic and guarded deterministic-fallback outputs, these values are
derived from the typed deterministic authority.

For raw LLM prose, no typed abstention outcome or reason is inferred from text;
the values remain `None`.

This prevents raw prose from receiving abstention credit merely by emitting a
machine-looking reason string, and prevents deterministic or guarded systems
from receiving credit merely because of their system labels.

### Methodological boundary

The Phase 10D1 protocol was frozen before this scorer was used to compute any
comparative result.

The scorer itself is frozen before the real Qwen comparison is executed.

The scoring rules remain deterministic mechanical checks. They do not establish
general semantic equivalence, arbitrary free-form factuality, or semantic answer
accuracy.

No real three-system comparative score has been computed as part of Phase 10D2.

### Verification

At the Phase 10D2 freeze candidate:

- generation comparison tests: 17 passing
- Phase 10C regression tests: 33 passing
- full repository: 524 passing
- Ruff: clean
- `git diff --check`: clean
- Phase 10D1 protocol tag remained unchanged

The next phase executes the frozen scorer against the real deterministic,
raw-Qwen, and guarded-Qwen presentation paths.

## Phase 10E — Formal Generation Comparison Confirmation

**Status:** VERIFIED / REPRODUCIBLE / FROZEN

### Purpose

Formalized and persisted the real three-system generation comparison executed
against the Phase 10D1 frozen comparison protocol and Phase 10D2 frozen
mechanical scorer.

Systems:

1. `deterministic`
2. `raw_llm`
3. `guarded_llm`

### Frozen experimental boundaries

Phase 10D1 comparison protocol:

`16b67e3d5b6f5011664f63a0c6f4c7da1448bd92`

Phase 10D2 mechanical scorer:

`d9c8cf862ff70184dd812af6d33dfca88fc14b8b`

Both were frozen before the formal three-system measurement.

### Runtime

- Model: `Qwen/Qwen2.5-0.5B-Instruct`
- Immutable revision:
  `7ae557604adf67be50417f59c2c2f167def9a775`
- Runtime: CPU
- dtype: float32
- CUDA observed: false
- Decoding: deterministic greedy generation

### Five-case integration control set

- `Q-0001` — retrieval-backed Orbis risk answer
- `Q-0010` — structured highest-growth entity answer
- `Q-0011` — structured portfolio revenue numeric answer
- `Q-0023` — missing-required-information abstention
- `Q-0024` — unsupported-request abstention

Each system received exactly 25 applicable frozen mechanical checks across the
five cases.

### Measured result

- deterministic: `25 / 25` = `1.00`
- raw LLM: `12 / 25` = `0.48`
- guarded LLM: `25 / 25` = `1.00`

These are mechanical fidelity scores, not semantic answer-accuracy scores.

### Observed comparison behavior

`Q-0001`

- deterministic: 4/4
- raw LLM: 2/4
- guarded LLM: 4/4
- raw generation failed strict authoritative-text preservation and exposed a
  generation the fidelity layer classified as rejected.
- guarded presentation substituted deterministic authority.

`Q-0010`

- deterministic: 5/5
- raw LLM: 5/5
- guarded LLM: 5/5
- the raw entity generation passed the frozen fidelity constraints and was
  retained by the guarded path.

`Q-0011`

- deterministic: 6/6
- raw LLM: 2/6
- guarded LLM: 6/6
- raw Qwen transformed authoritative `735000000 USD` into
  `$735 million USD`.
- this failed exact numeric-literal preservation and introduced an
  unauthorized numeric literal under the frozen mechanical policy.
- guarded presentation returned deterministic `735000000 USD`.

`Q-0023`

- deterministic: 5/5
- raw LLM: 1/5
- guarded LLM: 5/5
- raw Qwen replaced the deterministic missing-information abstention with an
  invented `$15 billion` valuation.
- guarded presentation restored the deterministic abstention.

`Q-0024`

- deterministic: 5/5
- raw LLM: 2/5
- guarded LLM: 5/5
- raw Qwen converted an unsupported-query condition into a substantive
  "no known customer churn rate" claim.
- guarded presentation restored the deterministic unsupported-request outcome.

### Methodological boundary

The comparison protocol was not blind or preregistered: Phase 10C behavior had
already been observed before the Phase 10D1 metric matrix was defined.

The stronger ordering guarantee is:

1. the Phase 10D1 metric matrix was frozen before comparative scoring;
2. the Phase 10D2 scorer implementation was frozen before the real
   three-system comparison;
3. Phase 10D3 then measured the real outputs;
4. Phase 10E persisted and independently reproduced that measurement.

The `rejected_raw_not_exposed` metric includes an architectural safety
property. In particular, the deterministic path cannot expose rejected Qwen
output because it does not present probabilistic output. Therefore `25/25`
must not be interpreted as a generic generation-quality or semantic-accuracy
score.

### Reproducibility artifact

Artifact:

`artifacts/generation/phase10e_generation_comparison_confirmation.json`

Exact file SHA-256:

`f5d9c5784ca7c288f7455da08438b4074f25bdfc5592f7692492316605d9a99f`

The report was independently regenerated through the persisted PostgreSQL /
frozen retrieval / deterministic answering / pinned local Qwen / frozen
fidelity guard / frozen comparison scorer pipeline and was byte-identical to
the persisted artifact.

### Verification

At the Phase 10E freeze candidate:

- Phase 10E confirmation tests: 6 passing
- Phase 10D comparison regression tests: 17 passing
- full repository: 530 passing
- Ruff: clean
- `git diff --check`: clean
- Phase 10D1 and 10D2 frozen tags remained unchanged

### Safe claim

> Built and evaluated a fail-closed local-LLM presentation layer over a
> deterministic retrieval/structured-execution grounding stack. On a frozen
> five-case integration control set, the unguarded local Qwen path passed
> 12/25 mechanical fidelity checks, while the guarded path passed 25/25 by
> accepting compliant generation and replacing rejected generation with
> deterministic authority.

### Do not claim

- 100% semantic answer accuracy,
- general hallucination elimination,
- semantic factuality of arbitrary generated prose,
- evaluation on the complete 24-case benchmark,
- blind or preregistered comparison,
- learned factuality/confidence scoring,
- that 25/25 mechanical fidelity implies perfect generation quality.

## Phase 11A — Typed Application Answering Boundary

**Status:** VERIFIED / FROZEN pending commit/tag

### Purpose

Introduced a typed application-service boundary between the existing FastAPI
application and the grounded answering/generation stack.

No HTTP answering route, database wiring, model initialization, or gRPC service
was added in this phase.

### Public application contract

Request:

- `AnswerRequest`
- normalized nonblank `question`
- closed Pydantic schema (`additionalProperties: false`)

Result union:

- `AnsweredServiceResult`
- `AbstainedServiceResult`

Top-level discriminator:

`status`

with:

- `answered`
- `abstained`

Answered payload discriminator:

`answer_type`

with:

- `text`
- `entity`
- `entities`
- `number`
- `boolean`

### Presentation safety boundary

The public result exposes:

- presentation text,
- typed answer or abstention state,
- presentation source,
- generation-fidelity disposition,
- citation IDs,
- provenance fact IDs.

It deliberately exposes no raw model generation, provider prompt, generation
prompt, or other untrusted internal generation object.

Presentation-source / fidelity consistency is enforced at runtime:

- deterministic -> `not_applicable`
- model generation -> `accepted`
- deterministic fallback -> `rejected`

The OpenAPI schema exposes the enum values but does not itself encode this
cross-field conditional invariant; Pydantic validation enforces it.

### Service abstraction

`AnsweringServiceProtocol` defines the application boundary consumed by the
future HTTP route:

`answer(AnswerRequest) -> AnswerServiceResult`

This keeps orchestration, evidence sufficiency, deterministic synthesis, and
guarded generation out of FastAPI route handlers.

### OpenAPI verification

Verified that:

- `AnswerServiceResult` emits a discriminated `oneOf` on `status`;
- `AnsweredServiceResult.payload` emits a discriminated `oneOf` on
  `answer_type`;
- FastAPI preserves the top-level discriminator in the `/answer` response
  schema;
- no raw-generation or prompt fields appear in the public schema.

### Verification

At the Phase 11A freeze candidate:

- application contract/schema tests: 16 passing
- health regression tests: 3 passing
- Phase 10 comparison regression tests: 23 passing
- full repository: 546 passing
- Ruff: clean
- `git diff --check`: clean
- Phase 10E remained a frozen ancestor

### Safe claim

> Designed and verified a typed application-service boundary for grounded
> answering, including discriminated answer/abstention schemas, typed
> provenance/citations, presentation-fidelity metadata, and an OpenAPI surface
> that excludes raw model generation.

### Do not claim

- a production `/answer` endpoint yet,
- live request handling through PostgreSQL or Qwen,
- API latency or throughput measurements,
- authentication or authorization,
- gRPC or microservice deployment,
- distributed tracing,
- production serving readiness.

## Phase 11B0 — Bounded Answer Specification Contract

**Status:** VERIFIED / FROZEN

### Purpose

Introduced an explicit typed specification boundary between an incoming
application `AnswerRequest` and grounded execution.

The contract prevents the application service from silently inferring execution
plans, evidence requirements, synthesis instructions, or unsupported-request
decisions from arbitrary natural-language questions.

### Executable specification

`ExecutableAnswerSpecification` contains:

- the exact normalized question,
- a preconstructed `BoundedOrchestrationPlan`,
- one or more explicit `EvidenceRequirement` objects,
- optional bounded synthesis metadata.

The specification enforces exact equality between the specification question
and the orchestration-plan question.

Evidence requirement IDs must be unique and at least one requirement is
mandatory.

### Synthesis specification

`AnswerSynthesisSpecification` contains:

- deterministic `SynthesisMode`,
- typed `GroundedAnswerType`.

It does not contain generated text and does not infer synthesis behavior from
natural language.

### Unsupported specification

`UnsupportedAnswerSpecification` explicitly represents a request that is
outside the bounded execution contract and carries a typed explanatory detail.

This makes unsupported handling an explicit application decision rather than a
fallback invented during answer generation.

### Provider abstraction

`AnswerSpecificationProviderProtocol` defines:

`prepare(AnswerRequest) -> AnswerExecutionSpecification`

The protocol deliberately makes no claim about how a specification is
produced.

Any future deterministic compiler, learned router/planner, or other
implementation behind this boundary must be evaluated independently before
claims are made about its behavior.

### Architectural boundary

The intended application flow is:

`AnswerRequest`
→ `AnswerSpecificationProviderProtocol`
→ `AnswerExecutionSpecification`
→ bounded execution
→ evidence normalization
→ deterministic sufficiency
→ deterministic synthesis
→ guarded generation
→ `AnswerServiceResult`

The grounded answering service itself therefore does not need to become an
autonomous natural-language planner.

### Verification

At the Phase 11B0 freeze candidate:

- specification contract tests: 6 passing
- Phase 11A application regression tests: 16 passing
- Phase 10 comparison regression tests: 23 passing
- full repository: 552 passing
- Ruff: clean
- `git diff --check`: clean
- Phase 11A remained a frozen ancestor

### Safe claim

> Designed and verified a bounded answer-specification contract that separates
> natural-language request intake from explicit orchestration plans, evidence
> requirements, synthesis metadata, and unsupported-request decisions.

### Do not claim

- autonomous natural-language planning,
- learned or LLM-based plan generation,
- arbitrary question-to-tool compilation,
- production `/answer` execution,
- live PostgreSQL/Qwen serving through the application service,
- gRPC or distributed service deployment.

## Phase 11B1 — Grounded Answering Application Service

**Status:** VERIFIED / REPRODUCIBLE / FROZEN

### Purpose

Implemented the application-level `GroundedAnsweringService` that composes the
previously frozen bounded execution, evidence, sufficiency, synthesis, and
guarded-generation layers behind the Phase 11A service contract.

The service is a composition boundary. It does not infer tool selection,
execution plans, evidence requirements, or synthesis instructions from arbitrary
natural-language questions.

### Service dependencies

The service consumes:

- `AnswerSpecificationProviderProtocol`
- `AnswerExecutionRuntimeProtocol`
- `GenerationProvider`

The specification provider supplies the already-bounded execution intent.

### Execution flow

For executable requests:

`AnswerRequest`
→ bounded answer specification
→ `BoundedLangGraphRuntime`
→ terminal orchestration snapshot
→ evidence normalization
→ deterministic sufficiency assessment
→ deterministic grounded synthesis
→ grounded generation request
→ generation provider
→ deterministic fidelity assessment
→ guarded model text or deterministic fallback
→ `AnswerServiceResult`

For explicitly unsupported requests:

`AnswerRequest`
→ unsupported answer specification
→ typed unsupported evidence bundle
→ deterministic insufficiency/abstention
→ deterministic presentation

No orchestration or probabilistic generation is invoked for that path.

### Boundary invariants

The service verifies:

- returned specification question exactly equals the incoming request question;
- runtime snapshot plan exactly equals the requested orchestration plan;
- sufficient evidence cannot be synthesized without explicit synthesis metadata;
- accepted model output may cross the presentation boundary only after the
  frozen fidelity assessment accepts it;
- rejected model output is replaced with deterministic authority;
- deterministic abstentions bypass the generation provider entirely.

Generation-provider exceptions currently propagate rather than being
misclassified as fidelity failures. Failure/degradation policy is deferred to a
later serving-resilience phase.

### Unit verification

Phase 11B1 added 9 application-service tests covering:

- frozen service version;
- protocol compatibility;
- request/specification question consistency;
- runtime-plan consistency;
- explicit synthesis requirement;
- accepted model presentation;
- rejected-generation deterministic fallback;
- deterministic unsupported-request abstention with no runtime/model call;
- generation-provider failure propagation.

### Real persisted integration confirmation

The service was exercised against the persisted Northstar dataset using:

- frozen Phase 9C4 bounded control specifications;
- persisted hybrid retrieval;
- persisted structured SQL;
- `BoundedLangGraphRuntime`;
- pinned `Qwen/Qwen2.5-0.5B-Instruct`;
- immutable model revision
  `7ae557604adf67be50417f59c2c2f167def9a775`;
- CPU;
- float32;
- CUDA unavailable.

Observed five-case control behavior:

- Q-0001: answered / deterministic fallback / generation rejected
- Q-0010: answered / model generation / generation accepted
- Q-0011: answered / deterministic fallback / generation rejected
- Q-0023: abstained / deterministic / generation not applicable
- Q-0024: abstained / deterministic / generation not applicable

Additional confirmed authority values:

- Q-0001 provenance included `RISK-006`;
- Q-0010 authoritative entity was `HelioGrid Energy`;
- Q-0011 authoritative value was `735000000 USD`;
- Q-0023 abstained with `missing_required_information`;
- Q-0024 abstained with `unsupported_request`.

The generation provider was invoked exactly 3 times for Q-0001, Q-0010, and
Q-0011.

Q-0023 and Q-0024 were deterministic abstentions and did not invoke the
generation provider.

Rejected raw model text for Q-0001 and Q-0011 did not cross the public
presentation boundary. The accepted Q-0010 model generation was retained.

### Verification

At the Phase 11B1 freeze candidate:

- Phase 11B1 service tests: 9 passing
- Phase 11B0 regression tests: 6 passing
- Phase 11A regression tests: 16 passing
- Phase 10 comparison regression tests: 23 passing
- full repository: 561 passing
- Ruff: clean
- `git diff --check`: clean
- Phase 11B0 remained a frozen ancestor

### Safe claim

> Implemented and verified a composition-only grounded answering service over
> bounded execution, deterministic evidence/sufficiency/synthesis, and guarded
> local LLM presentation. On a frozen five-case persisted integration control
> set, three answer cases traversed the model path while two deterministic
> abstentions skipped generation; rejected model output was replaced by
> deterministic authority and accepted model output was retained.

### Claim boundary

This milestone does not establish:

- arbitrary natural-language planning;
- general question-to-tool compilation;
- general semantic accuracy;
- hallucination-free generation;
- full 24-case benchmark accuracy;
- provider outage recovery;
- retry or timeout policy;
- HTTP request serving;
- authentication or authorization;
- gRPC or distributed deployment;
- production latency or throughput.

## Phase 11B2 — FastAPI Grounded Answer Transport

**Status:** VERIFIED / FROZEN

### Purpose

Added a thin FastAPI transport boundary for the previously verified grounded
answering application service.

This phase intentionally does not construct the real retrieval runtime, model,
or specification provider inside the HTTP layer.

### HTTP contract

Added:

`POST /answer`

Request:

- `AnswerRequest`
- normalized nonblank question
- unknown request fields rejected by the closed Pydantic contract

Response:

- `AnswerServiceResult`
- discriminated answered/abstained response union
- typed answer payloads
- presentation source
- generation-fidelity disposition
- citation IDs
- provenance fact IDs

### Service resolution

The endpoint resolves an `AnsweringServiceProtocol` implementation from:

`app.state.answering_service`

The HTTP route performs no tool selection, retrieval, SQL, orchestration,
sufficiency evaluation, synthesis, or model generation itself.

Its responsibility is limited to:

HTTP validation
→ application-service invocation
→ typed HTTP serialization.

### Unavailable-service behavior

If no answering service has been installed in application state, `POST /answer`
returns HTTP 503 with:

`answering service unavailable`

This is intentional.

At this milestone the default FastAPI application does not pretend to support
arbitrary natural-language answering before a truthful serving assembly and
specification-provider implementation have been installed.

### Validation behavior

Verified that:

- valid answered results serialize through HTTP;
- valid abstention results serialize through HTTP;
- outer whitespace in questions is normalized before service invocation;
- blank questions are rejected with HTTP 422;
- unknown request fields are rejected with HTTP 422;
- invalid requests do not invoke the application service;
- an absent application service returns HTTP 503.

### OpenAPI verification

The real application OpenAPI document contains `POST /answer` with operation ID:

`answer_question`

The HTTP 200 response preserves the top-level `status` discriminator and
two-member `oneOf` mapping for:

- `answered`
- `abstained`

The endpoint therefore exposes the same typed result boundary previously
verified in Phase 11A.

### Resource-lifecycle boundary

This phase deliberately does not initialize heavyweight dependencies inside the
route.

In particular:

- `FrozenHybridRetrievalExecutor.from_persisted_corpus(...)` is not called per
  request;
- `HuggingFaceCausalGenerationProvider.from_pretrained()` is not called per
  request;
- no database-backed runtime is constructed per request;
- no model is loaded per request.

Real resource assembly and lifecycle management are deferred to the next
serving milestone.

### Verification

At the Phase 11B2 freeze:

- Phase 11B2 API tests: 7 passing
- health regression tests: 3 passing
- Phase 11B1 service regression tests: 9 passing
- Phase 11A contract/schema regression tests: 16 passing
- full repository: 568 passing
- Ruff: clean
- `git diff --check`: clean
- Phase 11B1 remained a frozen ancestor
- real application OpenAPI `/answer` discriminator verified

### Safe claim

> Implemented and verified a thin FastAPI `POST /answer` transport over a typed
> grounded-answering service boundary, including strict request validation,
> discriminated answer/abstention responses, OpenAPI schema preservation, and
> explicit HTTP 503 behavior when no answering service is installed.

### Claim boundary

This milestone does not establish:

- live persisted answering through the default HTTP application;
- arbitrary natural-language planning;
- a production specification provider;
- model or retrieval initialization during application startup;
- request-time PostgreSQL integration through the HTTP endpoint;
- provider outage recovery;
- authentication or authorization;
- HTTP latency or throughput measurements;
- gRPC or distributed deployment.

## Phase 11B3 — Bounded FastAPI Serving Assembly and Lifecycle

**Status:** VERIFIED / REPRODUCIBLE / FROZEN

### Purpose

Completed the live serving assembly behind the Phase 11B2 `POST /answer`
transport.

This phase added:

- a deterministic bounded Northstar specification provider;
- request-scoped SQLAlchemy execution state;
- process-lifetime persisted retrieval resources;
- process-lifetime pinned local generation resources;
- serialized access to shared CPU inference resources;
- opt-in serving lifecycle configuration;
- answering-aware readiness;
- real persisted HTTP confirmation.

### Deterministic serving specification

Implemented:

`NorthstarBoundedSpecificationProvider`

Version:

`northstar-bounded-serving-specification-v1`

The provider is deliberately not described as an autonomous planner.

It compiles only explicit supported natural-language query families into
`AnswerExecutionSpecification` objects and returns
`UnsupportedAnswerSpecification` for requests outside that grammar.

Verified supported families include:

- qualitative defect lookup by explicit identifier;
- highest/lowest year-over-year portfolio revenue growth;
- total portfolio revenue for a quarter;
- expected exit-valuation retrieval with explicit evidence requirements.

Unsupported questions are not guessed into tool calls.

### Request-scoped execution

Implemented:

`RequestScopedExecutionRuntime`

Version:

`northstar-request-scoped-execution-runtime-v1`

Database-backed SQL and graph execution use a fresh SQLAlchemy `Session` for
each bounded execution requiring relational state.

Retrieval-only plans do not open a database session.

This avoids sharing one mutable ORM session across concurrent HTTP requests.

### Process-lifetime serving assembly

Implemented:

`ServingAssembly`

Version:

`northstar-serving-assembly-v1`

At enabled application startup:

- the persisted hybrid retrieval corpus/index is constructed once;
- the pinned Qwen generation provider is loaded once;
- the bounded specification provider is constructed once;
- the request-scoped runtime is constructed once;
- the composed `GroundedAnsweringService` is installed in FastAPI application
  state.

The SQL and graph executors themselves remain request scoped.

### Shared inference locking

Added explicit locking wrappers for:

- the shared retrieval executor;
- the shared generation provider.

Unit concurrency tests verified that two concurrent calls do not enter the
wrapped shared inference delegate simultaneously.

This is an explicit CPU-serving policy for the current implementation, not a
throughput optimization claim.

### Configuration

Added:

`answering_enabled: bool = False`

Default behavior keeps heavyweight answering resources disabled.

When answering is disabled:

- the service remains lightweight;
- the answering stack is not initialized;
- readiness may still report ready if the database is available;
- `POST /answer` remains unavailable because no answering service is installed.

When explicitly enabled:

- serving resources initialize during FastAPI lifespan startup;
- successful initialization installs the answering service;
- failed initialization keeps the process alive but marks answering
  `unavailable`.

### Readiness

`GET /health/ready` now reports:

- database readiness;
- answering state: `disabled`, `ready`, or `unavailable`.

Enabled initialization failure produces HTTP 503 readiness without pretending
the answering service is operational.

### Real enabled HTTP confirmation

A fresh process was run with:

`ANSWERING_ENABLED=true`

The application successfully initialized the persisted serving stack and
reported:

- HTTP readiness: `ready`;
- database: `ok`;
- answering: `ready`.

Generation model:

- model: `Qwen/Qwen2.5-0.5B-Instruct`;
- revision:
  `7ae557604adf67be50417f59c2c2f167def9a775`;
- device: CPU;
- dtype: float32;
- CUDA available: false.

Five real requests were sent through `POST /answer`.

Observed:

- Q-0001:
  answered / deterministic fallback / generation rejected
- Q-0010:
  answered / model generation / generation accepted
- Q-0011:
  answered / deterministic fallback / generation rejected
- Q-0023:
  abstained / deterministic / generation not applicable
- Q-0024:
  abstained / deterministic / generation not applicable

Authority confirmation:

- Q-0001 preserved `ORBIS-IDX-7` and provenance `RISK-006`;
- Q-0010 returned `HelioGrid Energy`;
- Q-0011 returned `735000000 USD`;
- Q-0023 returned `missing_required_information`;
- Q-0024 returned `unsupported_request`.

Q-0023 is a supported retrieval-family request that executed retrieval before
abstaining because its required evidence was absent.

Q-0024 is a distinct pre-execution unsupported-capability path.

### Resource-count confirmation

During the five-case enabled HTTP run:

- persisted retrieval builds: 1
- generation-model loads: 1
- retrieval executions: 2
- SQL executions: 2
- graph executions: 0
- generation calls: 3

Q-0023 and Q-0024 did not invoke probabilistic generation.

### Startup network caveat

The enabled startup contacted Hugging Face Hub while resolving/loading pinned
model resources.

Therefore this milestone establishes serving under the observed
environment/cache/network configuration.

It does not establish offline or fully self-contained model packaging.

### Verification

At the Phase 11B3 freeze candidate:

- serving assembly tests: 4 passing
- serving lifecycle tests: 4 passing
- health tests: 3 passing
- Phase 11B3A tests: 10 passing
- Phase 11B2 transport tests: 7 passing
- Phase 11B1 service tests: 9 passing
- full repository: 586 passing
- Ruff: clean
- `git diff --check`: clean
- Phase 11B2 remained a frozen ancestor
- live enabled HTTP serving confirmation: verified

### Safe claim

> Implemented and verified bounded live FastAPI serving over persisted
> retrieval, request-scoped PostgreSQL execution, deterministic
> evidence/sufficiency/synthesis, and guarded local Qwen presentation.
> Heavyweight retrieval and generation resources are initialized once at
> enabled startup, while database execution uses request-scoped sessions. A
> five-case persisted HTTP control run reproduced the expected answer,
> fallback, and abstention behavior.

### Claim boundary

This milestone does not establish:

- arbitrary natural-language planning;
- unrestricted question-to-tool compilation;
- general semantic correctness;
- hallucination-free generation;
- offline model packaging;
- production latency or throughput;
- multi-process model sharing;
- authentication or authorization;
- retry or timeout policy;
- gRPC or distributed deployment.

## Phase 11C1 — Privacy-Safe HTTP Request Observability

**Status:** VERIFIED / FROZEN

### Purpose

Added a privacy-safe HTTP observability boundary to the live FastAPI
application without changing the answering API contract.

### Trace contract

Implemented:

`northstar-http-request-trace-v1`

Every HTTP request receives a server-generated UUID request identifier.

The identifier is:

- bound into structured logging context;
- shared across request start/completion or failure events;
- returned to the caller in `X-Request-ID`.

Caller-supplied request identifiers are not trusted as the canonical server
request ID.

### Structured HTTP events

Successful requests emit:

- `http_request_started`
- `http_request_completed`

Unhandled failures emit:

- `http_request_started`
- `http_request_failed`

Operational fields include:

- request ID;
- trace version;
- HTTP method;
- URL path without query string;
- HTTP status code for completed requests;
- elapsed duration in milliseconds;
- exception class name for failed requests.

### Privacy boundary

The HTTP observability layer intentionally does not log:

- request bodies;
- natural-language questions;
- query strings;
- request headers;
- authorization material;
- retrieved evidence;
- model prompts;
- model output;
- response bodies.

Failure events record only the exception type rather than the exception message,
because exception messages can contain user-controlled or sensitive content.

### Timing

HTTP request duration uses `perf_counter` and is reported as non-negative
milliseconds.

This is operational timing instrumentation only.

No latency or throughput performance claim is made by this milestone.

### Verification

At the Phase 11C1 freeze candidate:

- Phase 11C1 tests: 4 passing
- Phase 11B3 serving regression: 8 passing
- HTTP/health regression: 10 passing
- full repository: 590 passing
- Ruff: clean
- `git diff --check`: clean
- OpenAPI answering and health surfaces unchanged
- Phase 11B3 remained a frozen ancestor

Tests verified:

- unique server-generated UUID request IDs;
- `X-Request-ID` response propagation;
- request-start and request-completion correlation;
- question text excluded from logs;
- query-string content excluded from logs;
- sensitive exception messages excluded from logs;
- exception class retained for operational diagnosis.

### Safe claim

> Added structured, privacy-safe HTTP request observability to the FastAPI
> serving layer with server-generated correlation IDs, request lifecycle
> events, response correlation headers, and monotonic request-duration
> measurement.

### Claim boundary

This milestone does not establish:

- distributed tracing;
- OpenTelemetry integration;
- Prometheus metrics;
- service-level objectives;
- production latency or throughput;
- application-stage tracing;
- per-generation latency;
- persistent log aggregation;
- cross-process correlation.

## Phase 11C2 — Application-Stage Answering Observability

**Status:** VERIFIED / REPRODUCIBLE / FROZEN

### Purpose

Extended Phase 11C1 HTTP request observability through the grounded-answering
application service.

The application-service trace exposes operational taxonomy and monotonic timing
without logging natural-language questions, evidence contents, prompts, model
output, answer text, missing-information prose, or exception messages.

### Trace contract

Implemented:

`northstar-answer-service-trace-v1`

The trace inherits the server-generated request ID established by the HTTP
middleware through structlog context variables.

This allows one request to be correlated across:

- HTTP request start;
- answering-service start;
- specification preparation;
- bounded execution;
- sufficiency evaluation;
- generation or generation skip;
- fidelity validation;
- answering-service completion;
- HTTP request completion.

### Application-stage events

Implemented structured events including:

- `answer_service_started`
- `answer_specification_prepared`
- `answer_execution_completed`
- `answer_sufficiency_evaluated`
- `answer_generation_completed`
- `answer_generation_skipped`
- `answer_service_completed`
- `answer_service_failed`

Operational taxonomy includes:

- specification kind;
- route label;
- planned tool families;
- orchestration status;
- per-tool execution status;
- sufficiency status and typed reason;
- whether generation was invoked;
- generation fidelity disposition;
- presentation source;
- typed abstention reason;
- failure stage;
- exception class name.

### Timing

The service now records monotonic durations for applicable stages:

- specification preparation;
- bounded execution;
- evidence conversion;
- sufficiency evaluation;
- deterministic synthesis / generation-request construction;
- probabilistic generation;
- generation-fidelity validation;
- total answering-service duration.

Existing executor-native `duration_ms` values are preserved separately for
retrieval, SQL, and graph tool execution.

The service does not reinterpret those tool-level measurements.

### Privacy boundary

Static AST-based inspection verified that structured logger keyword arguments do
not include prohibited content-bearing fields such as:

- question;
- text;
- prompt;
- evidence;
- request body;
- response body;
- headers;
- query string;
- detail;
- exception message;
- raw generation;
- model output.

Runtime capture over real enabled HTTP requests additionally verified that
captured operational events did not contain:

- the five control questions;
- `ORBIS-IDX-7`;
- `RISK-006`;
- `HelioGrid Energy`;
- `735000000`;
- `Meridian Health Systems`;
- `Alder Manufacturing`;
- retrieved identity-validation text.

Failure traces retain only the exception class, not the exception message.

### Real enabled HTTP correlation confirmation

A real process was run with:

`ANSWERING_ENABLED=true`

Five requests were sent through `POST /answer`.

Five unique UUID request IDs were returned and each request ID was observed in
both HTTP middleware events and answering-service events.

Observed control behavior:

- Q-0001:
  retrieval / generation invoked / deterministic fallback / rejected
- Q-0010:
  SQL / generation invoked / model generation / accepted
- Q-0011:
  SQL / generation invoked / deterministic fallback / rejected
- Q-0023:
  retrieval / no generation / deterministic abstention
- Q-0024:
  no execution tool / no generation / deterministic unsupported abstention

Q-0023 retained an execution-stage duration, confirming post-execution
insufficiency.

Q-0024 had no execution-stage duration, confirming pre-execution unsupported
handling.

### Observed single-run service timings

The five-case confirmation produced these service-level observations:

- Q-0001: approximately 9065 ms
- Q-0010: approximately 8079 ms
- Q-0011: approximately 5190 ms
- Q-0023: approximately 74 ms
- Q-0024: approximately 0.2 ms

These values are individual observations from the current CPU/WSL environment.

They are not a benchmark, throughput result, service-level objective, or
production-performance claim.

The generation-backed cases are substantially slower than the deterministic
abstention paths in this observed run, which motivates a separately controlled
latency experiment in a later milestone.

### Verification

At the Phase 11C2 freeze candidate:

- Phase 11C2 observability tests: 4 passing
- full application-service suite: 13 passing
- Phase 11C1 regression: 4 passing
- Phase 11B3 serving regression: 8 passing
- HTTP/health regression: 10 passing
- full repository: 594 passing
- Ruff: clean
- `git diff --check`: clean
- static log privacy inspection: verified
- runtime log privacy confirmation: verified
- five unique HTTP/application request correlations: verified
- Phase 11C1 remained a frozen ancestor

### Safe claim

> Added privacy-safe application-stage tracing to the grounded-answering
> service, propagating server-generated request IDs across the FastAPI and
> synchronous application-service boundaries while recording specification,
> execution, sufficiency, generation, fidelity, tool, and total-service timing
> metadata without logging question, evidence, prompt, model-output, or answer
> content.

### Claim boundary

This milestone does not establish:

- distributed tracing;
- OpenTelemetry integration;
- Prometheus metrics;
- persistent metrics storage;
- production latency or throughput;
- service-level objectives;
- statistical latency benchmarking;
- concurrency scalability;
- multi-process trace propagation;
- external log aggregation.

## Phase 11C3 — Bounded Process-Local Operational Metrics

**Status:** VERIFIED / REPRODUCIBLE / FROZEN pending commit/tag

### Purpose

Added bounded, thread-safe, process-local operational metrics over the already
verified HTTP and grounded-answering observability boundaries.

The metrics layer intentionally avoids retaining request content or arbitrary
individual latency samples.

### Metrics contract

Implemented:

`northstar-operational-metrics-v1`

The registry records bounded operational aggregates including:

- HTTP request count;
- unhandled HTTP middleware failure count;
- HTTP status-class counts;
- answering request count;
- answered and abstained outcome counts;
- answering-service failure count;
- generation invocation count;
- accepted and rejected generation counts;
- deterministic fallback count;
- typed abstention-reason counts;
- typed answer-failure-stage counts;
- retrieval, SQL, and graph tool invocation counts;
- fixed-bucket HTTP latency histograms;
- fixed-bucket answering-service latency histograms;
- fixed-bucket generation latency histograms;
- fixed-bucket per-tool latency histograms.

`http_failures_total` represents unhandled middleware request failures.
Ordinary returned HTTP error responses are represented independently through
HTTP status-class accounting.

### Bounded storage

Latency aggregation uses fixed histogram buckets:

- 1 ms
- 5 ms
- 10 ms
- 25 ms
- 50 ms
- 100 ms
- 250 ms
- 500 ms
- 1,000 ms
- 2,500 ms
- 5,000 ms
- 10,000 ms
- 30,000 ms
- overflow

The registry stores:

- cumulative counters;
- count and sum aggregates;
- fixed-bucket histogram counts.

It does not retain an unbounded list of individual latency samples.

### Concurrency

Registry mutation and snapshots are protected by a process-local lock.

A concurrent unit test executed 200 updates through an eight-worker thread
pool and verified exact counter and histogram totals.

This establishes thread-safe behavior for the tested in-process registry.

It is not a distributed, multi-process, or external metrics backend.

### Serving integration

FastAPI lifespan now creates one process-local operational metrics registry.

That same registry is passed to the serving assembly and grounded-answering
service.

HTTP middleware obtains the registry from FastAPI application state.

The enabled integration confirmation verified object identity across:

- `app.state.operational_metrics`;
- `ServingAssembly.metrics_registry`;
- the metrics registry used by `GroundedAnsweringService`.

The registry is removed from app state at lifespan shutdown.

### Five-case enabled FastAPI/ASGI confirmation

The existing five-case answering control set was executed through `POST
/answer` using an enabled FastAPI TestClient lifecycle with the persisted
Northstar data and pinned local generation layer.

This was an in-process ASGI integration confirmation, not a Uvicorn/TCP network
benchmark.

Exact operational counts after the five requests were:

- HTTP requests: 5
- unhandled HTTP middleware failures: 0
- HTTP 2xx responses: 5
- answering requests: 5
- answered outcomes: 3
- abstentions: 2
- answering-service failures: 0
- generation invocations: 3
- generation accepted: 1
- generation rejected: 2
- deterministic fallbacks: 2
- retrieval invocations: 2
- SQL invocations: 2
- graph invocations: 0

Abstention reasons were:

- `missing_required_information`: 1
- `unsupported_request`: 1

Histogram observation counts were:

- HTTP: 5
- answering service: 5
- generation: 3
- retrieval: 2
- SQL: 2
- graph: 0

### Control behavior

The five cases preserved the previously verified answering behavior:

- Q-0001:
  answered / deterministic fallback / generation rejected
- Q-0010:
  answered / model generation / generation accepted
- Q-0011:
  answered / deterministic fallback / generation rejected
- Q-0023:
  abstained / deterministic / generation not applicable
- Q-0024:
  abstained / deterministic / generation not applicable

### Privacy boundary

The metrics snapshot schema contains no fields for:

- question text;
- evidence text;
- prompts;
- request or response bodies;
- raw model generations;
- generated answer text.

The confirmation artifact additionally asserts that it does not store:

- question text;
- evidence text;
- prompt text;
- model output;
- answer text;
- individual latency samples.

A runtime artifact self-check also verified that the five control questions and
selected canonical evidence/answer strings were absent from the persisted
artifact.

### Confirmation artifact

Artifact:

`artifacts/evaluation/phase11c3/operational-metrics-confirmation.json`

Confirmation version:

`northstar-operational-metrics-confirmation-v1`

SHA-256:

`bc0c82a84c7f83579318a83ca8a1ed040a455c66dd0f73da8df544afc1896357`

The artifact intentionally excludes raw observed timing values and histogram
bucket occupancy from the five-case run.

It records only deterministic configuration, exact aggregate counts, bounded
outcome taxonomy, runtime metadata, and histogram observation counts.

### Runtime note

The enabled confirmation loaded the pinned E5 retrieval model and pinned Qwen
generation model on CPU.

Model initialization contacted Hugging Face Hub endpoints during the run.

Therefore this milestone does not establish offline packaging or offline model
startup.

### Verification

At the Phase 11C3 freeze candidate:

- operational-registry tests: 5 passing
- application-service tests: 15 passing
- HTTP observability tests: 5 passing
- serving/lifecycle tests: 10 passing
- health/transport tests: 10 passing
- full repository: 604 passing
- Ruff: clean
- `git diff --check`: clean
- fixed-bucket bounded storage: verified
- metrics snapshot privacy shape: verified
- shared registry identity: verified
- five-case enabled ASGI operational accounting: verified
- confirmation artifact privacy check: verified
- Phase 11C2 remained a frozen ancestor

### Safe claim

> Implemented a thread-safe, process-local operational metrics layer for a
> grounded GenAI serving stack, with bounded counters and fixed-bucket latency
> histograms spanning HTTP, answering, generation, and retrieval/SQL/graph
> execution. Verified shared registry wiring and exact operational accounting
> across a five-case enabled FastAPI/ASGI integration control set.

### Claim boundary

This milestone does not establish:

- Prometheus integration;
- OpenTelemetry metrics;
- distributed aggregation;
- multi-process aggregation;
- persistent metrics storage;
- production monitoring;
- service-level objectives;
- production latency or throughput;
- statistical latency benchmarking;
- Uvicorn/TCP network performance;
- concurrency scalability of model inference;
- offline model packaging.
