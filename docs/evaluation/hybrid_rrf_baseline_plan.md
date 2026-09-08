# Hybrid Reciprocal Rank Fusion Baseline Plan

## Status

**PRE-MEASUREMENT / PREREGISTERED DESIGN**

No Phase 6A hybrid result has been measured at the time this plan is created.

## Purpose

Phase 4 established a lexical BM25 retriever.

Phase 5 established a dense E5 retriever and selected a title-enriched passage
representation through a preregistered development experiment.

Phase 6A asks whether combining the two already-frozen retrieval signals
improves retrieval quality without retraining either retriever and without
introducing a learned fusion model.

## Experimental Question

> Does fixed Reciprocal Rank Fusion of the frozen BM25 and dense rankings
> improve development retrieval quality over the strongest frozen standalone
> retriever?

## Frozen Lexical Input

Retriever:

```text
BM25
```

Representation:

```text
document-title-text-v1
```

Tokenizer:

```text
lexical-tokenizer-v1
```

BM25 version:

```text
bm25-v1
```

Parameters:

```text
k1 = 1.5
b  = 0.75
```

The lexical representation and parameters are inherited unchanged from the
frozen Phase 4 development result.

## Frozen Dense Input

Retriever:

```text
intfloat/e5-small-v2
```

Representation:

```text
e5-document-title-text-v1
```

Model revision:

```text
ffb93f3bd4047442299a41ebb6fa998a38507c52
```

Embedding dimension:

```text
384
```

Normalization:

```text
L2
```

Similarity:

```text
inner product of L2-normalized embeddings
```

Device:

```text
CPU
```

The dense representation and retrieval configuration are inherited unchanged
from frozen Phase 5B.

## Fusion Method

Fusion version:

```text
rrf-k60-v1
```

For document or chunk `d`:

```text
RRF(d) =
    contribution_from_bm25(d)
    +
    contribution_from_dense(d)
```

where:

```text
contribution(d) = 1 / (60 + rank(d))
```

for each retriever in which `d` is ranked.

The RRF constant is fixed at:

```text
k = 60
```

No RRF parameter search is permitted in Phase 6A.

## Ranking Inputs

Fusion operates on ranking positions, not raw retrieval scores.

BM25 scores and dense cosine-equivalent similarity scores are not normalized,
rescaled, calibrated, averaged, or otherwise treated as directly comparable.

Each input retriever preserves its own previously frozen ranking behavior.

The dense retriever supplies its full ranking of the 80-chunk corpus.

The frozen BM25 implementation excludes chunks with non-positive lexical
scores rather than assigning arbitrary ranks to zero-overlap chunks.
Therefore, BM25 contributes to RRF only for chunks it actually returns.

For a chunk absent from an input ranking, that retriever contributes zero to
the fused score.

Phase 6A does not manufacture BM25 ranks for zero-overlap chunks because doing
so would alter the frozen lexical retriever's semantics.

## Deterministic Ordering

Hybrid candidates are ordered by:

```text
(-rrf_score, chunk_id)
```

The stable chunk ID is the deterministic tie-breaker.

## Fixed Evaluation Scope

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

Evaluation:

```text
development only
```

Retrieval-eligible cases:

```text
10
```

Query IDs:

```text
Q-0001
Q-0002
Q-0004
Q-0006
Q-0008
Q-0009
Q-0017
Q-0019
Q-0020
Q-0021
```

No seed test query will be used for Phase 6A development measurement.

## Standalone References

The strongest frozen standalone development reference before Phase 6A is
Dense D1:

```text
e5-document-title-text-v1
```

Development metrics:

```text
canonical MRR = 0.7833333333
nDCG@10       = 0.7829786496
Recall@10     = 0.9500000000
```

The frozen BM25 `document-title-text-v1` result remains a secondary descriptive
reference.

## Evaluation Metrics

The standard retrieval metrics remain:

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

The primary metric for judging whether the hybrid improves on the strongest
standalone development retriever is:

```text
mean nDCG@10
```

If hybrid and Dense D1 are exactly tied on development nDCG@10, compare:

```text
canonical MRR
```

If still exactly tied, compare:

```text
Recall@10
```

If all three are exactly tied, retain Dense D1 as the simpler selected
retriever.

The Phase 6A RRF artifact is preserved regardless of whether hybrid wins.

## No-Tuning Rule

Phase 6A permits exactly one hybrid candidate:

```text
equal-weight two-retriever RRF with k=60
```

The following are explicitly excluded:

- tuning `k`;
- weighted RRF;
- score interpolation;
- min-max score normalization;
- z-score normalization;
- learned fusion;
- query-type-specific weights;
- query routing;
- cross-encoder reranking;
- LLM-based reranking;
- test-set parameter selection.

If the fixed RRF baseline motivates one of those experiments, it must be
defined separately after Phase 6A is frozen.

## Diagnostic Analysis

Per-query behavior will be reported after aggregate measurement.

Previously difficult queries such as Q-0017 and Q-0021 may be discussed as
diagnostics, but no individual query can override the preregistered aggregate
selection rule.

Analysis should specifically identify:

- cases where both retrievers already agree;
- cases where BM25 rescues a dense miss;
- cases where dense retrieval rescues a BM25 miss;
- cases where fusion degrades a strong standalone ordering;
- remaining relevant items outside the top 10.

## Interpretation Boundary

Phase 6A can establish whether fixed equal-weight RRF improves development
retrieval on the synthetic Northstar benchmark.

It cannot establish:

- test-set confirmation;
- production generalization;
- optimal RRF hyperparameters;
- superiority of RRF to every fusion method;
- reranker quality;
- pgvector serving behavior;
- generation quality;
- agent quality;
- production latency or throughput.
