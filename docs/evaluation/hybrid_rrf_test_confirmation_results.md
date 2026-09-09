# Frozen Hybrid RRF Test Confirmation Results

## Status

**MEASURED / VERIFIED**

Phase 6B confirms the already-frozen Phase 6A BM25 + E5 Reciprocal Rank Fusion
retriever on the existing Northstar retrieval-eligible test split.

The result is a negative ranking-quality confirmation relative to frozen Dense
D1, while top-10 recall remains unchanged.

## Methodological Limitation

The Phase 6B test split is:

```text
previously-inspected-non-pristine
```

The retrieval-eligible test queries had already been inspected during earlier
retrieval work, including Phase 4C.

Therefore this result must be described as:

```text
test-confirmation
```

and not as a pristine unseen, untouched, blinded, or fully independent holdout.

## Preregistration Boundary

Phase 6B preregistration commit:

```text
7d86ec84c5233e568af1e634e21c5a36e0e2e620
```

Preregistration tag:

```text
phase-6b-hybrid-test-confirmation-preregistered
```

Before measurement:

```text
Phase 6B artifacts: 0
worktree:           clean
```

The configuration, four-query test scope, comparison metrics, and
interpretation rule were fixed before the canonical Phase 6B artifact was
created.

## Frozen Phase 6A Source

Selected retriever:

```text
hybrid:rrf-k60-v1
```

Source artifact:

```text
artifacts/evaluation/phase6a/rrf-k60-development.json
```

Source SHA-256:

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

## Frozen Lexical Retriever

```text
retriever              = BM25
bm25_version           = bm25-v1
tokenizer              = lexical-tokenizer-v1
representation         = document-title-text-v1
k1                     = 1.5
b                      = 0.75
zero-overlap policy    = excluded
```

The BM25 implementation excludes non-positive-score zero-overlap chunks rather
than manufacturing lexical ranks for them.

## Frozen Dense Retriever

```text
dense_version          = dense-e5-small-v2-v1
representation         = e5-document-title-text-v1
model                  = intfloat/e5-small-v2
revision               = ffb93f3bd4047442299a41ebb6fa998a38507c52
embedding dimension    = 384
normalization          = L2
similarity             = inner product of normalized embeddings
device                 = CPU
batch size             = 16
```

## Frozen Fusion

Fusion version:

```text
rrf-k60-v1
```

Formula:

```text
RRF(d) = sum(1 / (60 + rank_i(d)))
```

Fixed constant:

```text
k = 60
```

Source weights:

```text
BM25  = 1
dense = 1
```

Missing source ranks contribute:

```text
0
```

Final deterministic tie-breaking is:

```text
(-rrf_score, chunk_id)
```

No RRF parameter, representation, source weight, retriever, query-dependent
rule, or metric was changed after observing the Phase 6A development result or
Phase 6B test confirmation.

## Evaluation Scope

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

Test-split status:

```text
previously-inspected-non-pristine
```

Exactly four retrieval-eligible test cases were evaluated:

```text
Q-0003  lexical
Q-0005  semantic
Q-0007  hybrid
Q-0018  multi_source
```

No development case appears in the Phase 6B artifact.

## Frozen Dense D1 Test Reference

The frozen Dense D1 reference produced:

| Metric | Value |
| --- | ---: |
| Canonical MRR | 1.0000000000 |
| nDCG@10 | 0.9378188547 |
| Recall@10 | 1.0000000000 |

## Frozen Hybrid RRF Test Confirmation

The frozen Phase 6A RRF configuration produced:

| Metric | Value |
| --- | ---: |
| Canonical MRR | 0.7500000000 |
| nDCG@1 | 0.5000000000 |
| nDCG@3 | 0.7700698027 |
| nDCG@5 | 0.7700698027 |
| nDCG@10 | 0.8184264036 |
| Recall@1 | 0.3750000000 |
| Recall@3 | 0.8750000000 |
| Recall@5 | 0.8750000000 |
| Recall@10 | 1.0000000000 |

## Hybrid Minus Dense D1

| Metric | Absolute delta | Relative delta |
| --- | ---: | ---: |
| Canonical MRR | -0.2500000000 | -25.00% |
| nDCG@10 | -0.1193924511 | -12.73% |
| Recall@10 | 0.0000000000 | 0.00% |

The test confirmation therefore does not reproduce the Phase 6A development
ranking-quality improvement.

## Per-Query Results

| Query | Type | Dense nDCG@10 | Hybrid nDCG@10 | Dense RR | Hybrid RR | Dense R@10 | Hybrid R@10 |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Q-0003 | lexical | 1.000000 | 1.000000 | 1.0 | 1.0 | 1.0 | 1.0 |
| Q-0005 | semantic | 1.000000 | 1.000000 | 1.0 | 1.0 | 1.0 | 1.0 |
| Q-0007 | hybrid | 0.919721 | 0.693426 | 1.0 | 0.5 | 1.0 | 1.0 |
| Q-0018 | multi_source | 0.831555 | 0.580279 | 1.0 | 0.5 | 1.0 | 1.0 |

Two queries tie the dense reference and two regress under RRF.

## Diagnostic Analysis

### Q-0007

Dense D1 metrics:

```text
canonical reciprocal rank = 1.000000
nDCG@10                   = 0.919721
Recall@10                 = 1.000000
```

Hybrid RRF metrics:

```text
canonical reciprocal rank = 0.500000
nDCG@10                   = 0.693426
Recall@10                 = 1.000000
```

Dense D1 places the canonical evidence at rank 1.

The hybrid top two are:

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

The rank-1 BM25 support for `EVID-CORE-PC006-BOARD-PRIORITY`, combined with its
dense rank of 2, is sufficient under equal-weight RRF to outrank the dense
rank-1 canonical evidence.

The canonical item remains inside the top 10, so Recall@10 does not decline.

Consequences:

```text
canonical RR: 1.0 -> 0.5
nDCG@10:      0.919721 -> 0.693426
Recall@10:    1.0 -> 1.0
```

The regression is therefore primarily a ranking-order effect rather than a
top-10 coverage failure.

### Q-0018

Dense D1 metrics:

```text
canonical reciprocal rank = 1.000000
nDCG@10                   = 0.831555
Recall@10                 = 1.000000
```

Hybrid RRF metrics:

```text
canonical reciprocal rank = 0.500000
nDCG@10                   = 0.580279
Recall@10                 = 1.000000
```

Dense D1 again places canonical evidence at rank 1.

The hybrid top two are:

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

Equal-weight RRF favors the evidence item that is simultaneously BM25 rank 1
and dense rank 2 over the dense rank-1 canonical item whose lexical rank is 5.

The canonical evidence remains inside the top 10.

Consequences:

```text
canonical RR: 1.0 -> 0.5
nDCG@10:      0.831555 -> 0.580279
Recall@10:    1.0 -> 1.0
```

Again, the failure is primarily one of ordering rather than relevant-evidence
coverage.

## Development Versus Test Confirmation

Phase 6A development comparison versus Dense D1:

```text
canonical MRR:
absolute delta = +0.0333333333
relative delta = +4.26%

nDCG@10:
absolute delta = +0.0482279271
relative delta = +6.16%

Recall@10:
absolute delta = 0
relative delta = 0%
```

Phase 6B test-confirmation comparison versus Dense D1:

```text
canonical MRR:
absolute delta = -0.2500000000
relative delta = -25.00%

nDCG@10:
absolute delta = -0.1193924511
relative delta = -12.73%

Recall@10:
absolute delta = 0
relative delta = 0%
```

The direction of the ranking-quality effect reverses between development and
the four-case test confirmation.

Development:

```text
hybrid nDCG@10 relative delta = +6.16%
```

Test confirmation:

```text
hybrid nDCG@10 relative delta = -12.73%
```

Recall@10 remains unchanged relative to Dense D1 in both experiments.

This result demonstrates why development-set improvement alone is insufficient
evidence of retrieval generalization.

## Interpretation

Phase 6A established that fixed equal-weight RRF improved aggregate
development nDCG@10 and canonical MRR relative to Dense D1.

Phase 6B shows that the same frozen configuration does not reproduce that
ranking-quality advantage on the existing four-query test confirmation.

The test result is mixed at the case level:

```text
ties versus Dense D1:       2
RRF ranking regressions:    2
RRF ranking improvements:   0
```

At the aggregate level, frozen Dense D1 is stronger on canonical MRR and
nDCG@10.

Both systems retain:

```text
Recall@10 = 1.0
```

on all four confirmation cases.

The result does not trigger any Phase 6B tuning.

## No Post-Test Retuning

After observing the negative test confirmation, Phase 6B did not change:

```text
RRF k
source weights
BM25 parameters
lexical representation
dense representation
embedding model
embedding revision
query set
metrics
fusion method
```

No weighted RRF, query routing, score interpolation, alternative `k`, learned
fusion, or reranking configuration was evaluated against the Phase 6B test
cases.

The negative result is retained exactly as measured.

Any future retrieval improvement must be defined as a separate experiment.

## Reproducibility

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

Independent rerun:

```text
/tmp/rrf-k60-test-confirmation.json
```

Rerun SHA-256:

```text
21f7c2a354ca2e928b33eea6f7dfb17ff87ed0b93f3e35451fc3576c196a5843
```

Rerun size:

```text
77199 bytes
```

The canonical and rerun artifacts were:

```text
BYTE-IDENTICAL
```

The temporary rerun was removed after verification.

## Integrity Verification

The Phase 6B artifact was programmatically verified to confirm:

- confirmation version is `hybrid-rrf-test-confirmation-v1`;
- selected retriever remains `hybrid:rrf-k60-v1`;
- selection status is `frozen-before-test-confirmation`;
- scope is `test-confirmation`;
- test split status is `previously-inspected-non-pristine`;
- expected query IDs are exactly Q-0003, Q-0005, Q-0007, and Q-0018;
- all evaluated cases have split `test`;
- exactly four Dense D1 cases are present;
- exactly four hybrid cases are present;
- frozen Phase 6A source SHA-256 matches;
- fusion version is `rrf-k60-v1`;
- RRF `k` is exactly 60;
- lexical representation is `document-title-text-v1`;
- dense representation is `e5-document-title-text-v1`;
- dense model is `intfloat/e5-small-v2`;
- dense model revision is
  `ffb93f3bd4047442299a41ebb6fa998a38507c52`.

The integrity audit completed successfully.

## Final Quality Gate

After measurement and reproducibility verification:

```text
Ruff:                 passed
Formatting:           passed
Tests:                181 passed
Dependency lock:      valid
Alembic current:      8a0f69a3baf1 (head)
Alembic drift:        none
Phase 6B artifacts:   1
```

Frozen Phase 6A SHA-256 remained:

```text
c0f850e21d25f993f26c58b44d0ace057fbcd23380dce85039f2b4d6c2593c21
```

Phase 6B canonical SHA-256 remained:

```text
21f7c2a354ca2e928b33eea6f7dfb17ff87ed0b93f3e35451fc3576c196a5843
```

The source tree remained at the Phase 6B preregistration boundary throughout
measurement:

```text
7d86ec84c5233e568af1e634e21c5a36e0e2e620
```

until documentation and result freezing began.

## Scientific Conclusion

The Phase 6B confirmation does not reproduce the development-set ranking gain
from Phase 6A.

The observed pattern is:

```text
development nDCG@10 relative delta:      +6.16%
test-confirmation nDCG@10 relative delta: -12.73%
```

while:

```text
Recall@10 relative delta = 0%
```

in both experiments.

This indicates that fixed equal-weight RRF preserved broad top-10 candidate
coverage but was not consistently reliable as the final ranking function on
the current Northstar benchmark.

The confirmation set is too small and too previously exposed to support a
general conclusion about RRF versus dense retrieval beyond this benchmark.

## Engineering Lesson

The result motivates a separation between:

```text
candidate generation
```

and:

```text
final relevance ordering
```

Hybrid retrieval may remain valuable for broad candidate generation even when
its fused ordering is inferior to the dense source on some queries.

A later reranking phase can therefore test whether a cross-encoder can preserve
candidate coverage while correcting ordering mistakes such as Q-0007 and
Q-0018.

This future motivation does not alter the frozen Phase 6B result.

## Resume Evidence Policy

The Phase 6B result should primarily be retained as methodological and
interview evidence.

A resume bullet may use the positive Phase 6A development result only when it
clearly identifies it as a development-benchmark measurement.

If Phase 6B is discussed, the negative confirmation must not be concealed or
represented as a successful independent validation.

Any discussion should note that the confirmation consisted of four synthetic
Northstar retrieval queries and that the split was previously inspected.

## Claim Boundary

Phase 6B supports claims that:

- the frozen Phase 6A RRF retriever was evaluated without retuning on four
  existing Northstar retrieval-eligible test cases;
- the confirmation configuration was frozen before measurement;
- the test split was explicitly recorded as
  `previously-inspected-non-pristine`;
- Dense D1 achieved approximately `0.9378` nDCG@10 and `1.0` canonical MRR;
- frozen RRF achieved approximately `0.8184` nDCG@10 and `0.75` canonical MRR;
- RRF underperformed Dense D1 by approximately `12.73%` relative on nDCG@10
  on this four-query confirmation;
- canonical MRR declined by `25%` relative;
- both systems achieved `1.0` Recall@10;
- Q-0003 and Q-0005 tied the dense reference;
- Q-0007 and Q-0018 showed RRF ranking regressions;
- the negative confirmation was retained without post-test tuning;
- the Phase 6B artifact reproduced byte-identically.

Phase 6B does not support claims that:

- RRF is generally worse than dense retrieval;
- Dense D1 is universally superior;
- the result is statistically significant;
- the four-query test set is pristine, unseen, untouched, or blinded;
- the result generalizes to real enterprise data;
- `k=60` is optimal or suboptimal in general;
- a different RRF weight or `k` would perform better;
- learned fusion is superior;
- cross-encoder reranking has been evaluated;
- pgvector serving performance has been measured;
- production latency has been measured;
- production throughput has been measured;
- production scalability has been established;
- generation quality has been measured;
- agent quality has been measured.
