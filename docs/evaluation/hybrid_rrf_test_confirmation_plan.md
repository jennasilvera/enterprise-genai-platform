# Frozen Hybrid RRF Test Confirmation Plan

## Status

**PRE-MEASUREMENT / PREREGISTERED**

No Phase 6B hybrid test-confirmation result has been measured when this plan is
created.

## Purpose

Phase 6A selected the fixed BM25 + E5 Reciprocal Rank Fusion retriever on the
Northstar development set.

Phase 6B evaluates that already-frozen retriever on the existing
retrieval-eligible test split without changing:

- the lexical representation;
- the dense representation;
- the embedding model or revision;
- BM25 parameters;
- RRF formula;
- RRF constant;
- source weights;
- evaluation metrics;
- chunking;
- corpus;
- or any query-dependent behavior.

## Important Test-Split Limitation

The Northstar test split is not a pristine untouched holdout.

The retrieval-eligible test queries were previously inspected during earlier
retrieval work, including Phase 4C BM25 test confirmation.

Therefore Phase 6B is described as:

```text
test-confirmation
```

with test status:

```text
previously-inspected-non-pristine
```

It must not be described as an unseen, pristine, untouched, or fully blinded
holdout.

The Phase 6B result is useful as a frozen-configuration confirmation on a
separate split, but the prior inspection history must remain part of the
methodological record.

## Frozen Phase 6A Source

Selected retriever:

```text
hybrid:rrf-k60-v1
```

Frozen Phase 6A artifact:

```text
artifacts/evaluation/phase6a/rrf-k60-development.json
```

SHA-256:

```text
c0f850e21d25f993f26c58b44d0ace057fbcd23380dce85039f2b4d6c2593c21
```

Frozen result commit:

```text
689818d1168f46a06c7b189ab81bbfe5f168fc07
```

Frozen result tag:

```text
phase-6a-hybrid-rrf-baseline
```

Phase 6B must verify this source artifact hash before executing the
test-confirmation measurement.

## Frozen Lexical Configuration

```text
retriever              = BM25
bm25_version           = bm25-v1
tokenizer              = lexical-tokenizer-v1
representation         = document-title-text-v1
k1                     = 1.5
b                      = 0.75
zero-overlap policy    = excluded
```

The lexical representation and BM25 behavior are not configurable in Phase 6B.

## Frozen Dense Configuration

```text
dense_version          = dense-e5-small-v2-v1
representation         = e5-document-title-text-v1
model                  = intfloat/e5-small-v2
revision               = ffb93f3bd4047442299a41ebb6fa998a38507c52
embedding dimension    = 384
normalization          = L2
similarity             = inner product of L2-normalized vectors
device                 = CPU
batch size             = 16
```

The dense model, immutable revision, representation, normalization, similarity
function, device, and batch size are fixed before test confirmation.

## Frozen Fusion Configuration

Fusion version:

```text
rrf-k60-v1
```

Formula:

```text
RRF(d) = sum(1 / (60 + rank_i(d)))
```

Fixed RRF constant:

```text
k = 60
```

Missing ranking contribution:

```text
0
```

Source weights:

```text
BM25  = 1
dense = 1
```

Final deterministic tie-breaker:

```text
chunk_id
```

The hybrid does not normalize, calibrate, interpolate, average, or otherwise
combine raw BM25 scores and dense similarity scores.

Fusion uses only source ranking positions.

## BM25 Missing-Rank Semantics

The frozen BM25 implementation excludes chunks whose lexical score is
non-positive.

Therefore BM25 does not necessarily return all 80 chunks.

For a chunk absent from the BM25 ranking:

```text
BM25 RRF contribution = 0
```

Dense retrieval may still contribute a rank for that chunk.

Phase 6B must not manufacture BM25 ranks for zero-overlap chunks.

## No-Tuning Rule

Phase 6B performs no retrieval tuning.

The following are prohibited before or after observing Phase 6B results:

- changing RRF `k`;
- weighted RRF;
- changing lexical or dense source weights;
- score interpolation;
- min-max normalization;
- z-score normalization;
- learned fusion;
- query-type-specific weights;
- query routing;
- query rewriting;
- changing BM25 parameters;
- changing the lexical representation;
- changing the dense representation;
- changing the embedding model;
- changing the embedding-model revision;
- changing the evaluation metric ordering;
- cross-encoder reranking;
- LLM reranking;
- removing unfavorable test cases.

A poor Phase 6B result must be preserved as measured.

Any later retrieval experiment must be defined as a separate phase and must
not overwrite the Phase 6B result.

## Test Evaluation Scope

Dataset:

```text
northstar-v1
```

Chunk strategy:

```text
evidence-block-v1
```

Corpus:

```text
80 chunks
```

Scope:

```text
test-confirmation
```

Test split status:

```text
previously-inspected-non-pristine
```

Exact retrieval-eligible test queries:

```text
Q-0003
Q-0005
Q-0007
Q-0018
```

Exactly four retrieval-eligible test cases must be evaluated.

No development query may appear in the Phase 6B confirmation artifact.

## Test Query Types

The frozen four-case confirmation set contains:

```text
Q-0003  lexical
Q-0005  semantic
Q-0007  hybrid
Q-0018  multi_source
```

These query types are descriptive metadata only.

They do not determine routing, weights, fusion parameters, or any
query-dependent retrieval behavior.

## Frozen Dense Reference

Phase 6B also evaluates the already-selected dense representation:

```text
e5-document-title-text-v1
```

on exactly the same four retrieval-eligible test cases.

This dense result is a descriptive frozen reference.

It is not a new representation-selection experiment and cannot replace,
reselect, or retune the Phase 6A hybrid.

## Metrics

For both frozen Dense D1 and frozen Hybrid RRF, report:

```text
canonical MRR
nDCG@1
nDCG@3
nDCG@5
nDCG@10
Recall@1
Recall@3
Recall@5
Recall@10
```

The same metric definitions used in the development retrieval experiments must
be reused unchanged.

## Descriptive Comparison

Primary descriptive comparison:

```text
hybrid nDCG@10 - Dense D1 nDCG@10
```

Also report:

```text
hybrid canonical MRR - Dense D1 canonical MRR
hybrid Recall@10     - Dense D1 Recall@10
```

Absolute and relative deltas may be reported when the dense denominator is
non-zero.

These test comparisons are descriptive only.

They do not alter the already-frozen Phase 6A selection.

## Interpretation Rule

Phase 6B has no winner-selection rule.

The frozen Phase 6A selected retriever remains:

```text
hybrid:rrf-k60-v1
```

regardless of whether the Phase 6B comparison is:

```text
positive
neutral
negative
mixed
```

No Phase 6B result may trigger an in-place change to:

```text
k
weights
representations
retrievers
metrics
query set
fusion method
```

A negative or mixed confirmation result must be preserved rather than used to
retroactively modify the frozen system.

## Per-Query Reporting

The following must be reported for each of the four confirmation queries:

```text
query ID
query type
dense canonical reciprocal rank
hybrid canonical reciprocal rank
dense nDCG@10
hybrid nDCG@10
dense Recall@10
hybrid Recall@10
```

Per-query results are diagnostic.

No single query may cause configuration changes within Phase 6B.

## Frozen Configuration Verification

Before measurement, the implementation must verify that the frozen Phase 6A
artifact still records:

```text
selected retriever       = hybrid:rrf-k60-v1
fusion version           = rrf-k60-v1
RRF k                    = 60
lexical representation   = document-title-text-v1
BM25 version             = bm25-v1
tokenizer                = lexical-tokenizer-v1
BM25 k1                  = 1.5
BM25 b                   = 0.75
dense representation     = e5-document-title-text-v1
dense version            = dense-e5-small-v2-v1
model                    = intfloat/e5-small-v2
model revision           = ffb93f3bd4047442299a41ebb6fa998a38507c52
```

The frozen Phase 6A artifact SHA-256 must equal:

```text
c0f850e21d25f993f26c58b44d0ace057fbcd23380dce85039f2b4d6c2593c21
```

If any frozen identity differs, Phase 6B must stop before measurement.

## Measurement Boundary

Before the first Phase 6B measurement:

- all Phase 6B implementation code must be committed;
- this plan must be committed;
- tests must pass;
- Ruff must pass;
- formatting must pass;
- the Phase 6A source artifact hash must match;
- no Phase 6B result artifact may exist;
- the worktree must be clean;
- a Phase 6B preregistration tag must point at the exact pre-measurement commit.

The first execution that writes:

```text
artifacts/evaluation/phase6b/rrf-k60-test-confirmation.json
```

must occur only after that boundary is frozen.

## Canonical Artifact

The canonical Phase 6B result path will be:

```text
artifacts/evaluation/phase6b/rrf-k60-test-confirmation.json
```

Exactly one canonical Phase 6B measurement artifact should exist before the
phase is frozen.

## Reproducibility

After the canonical Phase 6B measurement, the identical frozen confirmation
must be rerun independently to:

```text
/tmp/rrf-k60-test-confirmation.json
```

The canonical and rerun artifacts must be compared:

```text
byte-for-byte
SHA-256
file size
```

A byte-identical rerun is the reproducibility target.

No rerun may use modified retrieval configuration.

## Expected Scientific Interpretation

Phase 6B tests whether the development-selected fixed hybrid exhibits similar,
better, worse, or mixed behavior on the existing four-case test split.

Because:

```text
n = 4 retrieval-eligible test queries
```

and because the split is:

```text
previously-inspected-non-pristine
```

the result must be interpreted cautiously.

It is an additional frozen-split confirmation, not evidence of broad
statistical generalization.

## Resume Evidence Policy

Phase 6B results may be added to resume evidence only after:

```text
measurement
integrity verification
reproducibility verification
final quality gate
result commit
result tag
```

Any test metric used in a resume or interview must explicitly be described as
coming from the synthetic Northstar benchmark.

The four-query confirmation should not be presented as large-scale empirical
validation.

## Claim Boundary

Phase 6B may support claims that:

- the already-selected Phase 6A hybrid was evaluated under a frozen
  configuration on the existing Northstar test split;
- exactly four retrieval-eligible test queries were evaluated;
- the hybrid configuration was fixed before test confirmation;
- the frozen hybrid was compared descriptively against the frozen Dense D1
  reference;
- the test-confirmation result was preserved regardless of whether it was
  favorable;
- the canonical Phase 6B artifact was reproducible, if byte-identical
  reproducibility is subsequently verified.

Phase 6B cannot establish:

- performance on a pristine unseen holdout;
- performance on an untouched or blinded test split;
- statistical significance from four queries;
- generalization to real enterprise data;
- optimal RRF parameters;
- universal superiority of hybrid retrieval;
- optimal source weights;
- superiority to learned fusion;
- cross-encoder reranking quality;
- pgvector serving performance;
- production latency;
- production throughput;
- production scalability;
- end-to-end generation quality;
- end-to-end agent performance.
