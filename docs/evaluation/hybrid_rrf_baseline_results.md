# Hybrid Reciprocal Rank Fusion Baseline Results

## Status

**MEASURED / VERIFIED**

Phase 6A evaluates the preregistered hybrid retrieval baseline combining the
frozen BM25 and dense E5 retrievers using deterministic Reciprocal Rank Fusion.

The measured candidate is:

```text
hybrid:rrf-k60-v1
```

The comparison reference is:

```text
dense:e5-document-title-text-v1
```

## Preregistration Boundary

Original preregistration commit:

```text
f21a5895a6060e20ede4f3c175055a0765369029
```

Original preregistration tag:

```text
phase-6a-hybrid-rrf-preregistered
```

A lint-only import-order correction was made before any Phase 6A measurement.

Quality-clean preregistration commit:

```text
2f11268a3e17e02d5fd8f2e9cedccc5358dc52ed
```

Quality-clean preregistration tag:

```text
phase-6a-hybrid-rrf-preregistered-clean
```

The only change between the original and clean preregistration boundaries was
import ordering in:

```text
src/enterprise_genai/evaluation/hybrid_rrf.py
```

No retrieval behavior, formula, parameter, evaluation case, metric, selection
policy, artifact path, or source-retriever configuration changed.

At the clean pre-measurement boundary:

```text
Ruff:                 clean
Formatting:           clean
Tests:                177 passed
Phase 6A artifacts:   0
Worktree:             clean
```

## Experimental Question

The experiment asks:

> Does fixed equal-weight Reciprocal Rank Fusion of the frozen BM25 and dense
> rankings improve development retrieval quality over the strongest frozen
> standalone dense retriever?

## Frozen Lexical Input

Retriever:

```text
BM25
```

Representation:

```text
document-title-text-v1
```

BM25 implementation:

```text
bm25-v1
```

Tokenizer:

```text
lexical-tokenizer-v1
```

Parameters:

```text
k1 = 1.5
b  = 0.75
```

Frozen development artifact:

```text
artifacts/evaluation/phase4b/document-title-text-v1.json
```

Frozen SHA-256:

```text
c1d36faf093d18053a733beb868933da71e902d741ae81ed885efb8f0104b3c2
```

The frozen BM25 implementation excludes non-positive-score zero-overlap chunks
instead of assigning arbitrary ranks to them.

## Frozen Dense Input

Retriever:

```text
intfloat/e5-small-v2
```

Dense version:

```text
dense-e5-small-v2-v1
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

Frozen development artifact:

```text
artifacts/evaluation/phase5b/e5-document-title-text-v1-development.json
```

Frozen SHA-256:

```text
ed406dacfec38bd97de7ccb42ad84b6d2ab6e00332e3b52b1cec171593d67f87
```

## Fusion Method

Fusion version:

```text
rrf-k60-v1
```

The fusion score for chunk `d` is:

```text
RRF(d) =
    BM25 contribution
    +
    dense contribution
```

where each available ranking contributes:

```text
1 / (60 + rank(d))
```

The fixed RRF constant is:

```text
k = 60
```

A chunk absent from one retriever's ranking receives:

```text
0
```

contribution from that retriever.

No raw BM25 score and dense similarity score normalization, calibration, or
interpolation was performed.

Final ordering is deterministic:

```text
(-rrf_score, chunk_id)
```

No parameter sweep was performed.

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

Scope:

```text
development-only
```

Retrieval-eligible development cases:

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

No seed test query was used for Phase 6A measurement.

## Preregistered Selection Policy

The strongest frozen standalone reference before Phase 6A was:

```text
dense:e5-document-title-text-v1
```

Primary selection metric:

```text
mean nDCG@10
```

If exactly tied:

```text
canonical MRR
```

If still exactly tied:

```text
Recall@10
```

If all three were exactly tied:

```text
retain dense:e5-document-title-text-v1
```

No diagnostic case could override this aggregate selection rule.

## Dense Reference Results

Frozen Dense D1 development metrics:

| Metric | Value |
| --- | ---: |
| Canonical MRR | 0.7833333333 |
| nDCG@10 | 0.7829786496 |
| Recall@10 | 0.9500000000 |

## Hybrid RRF Results

Measured Phase 6A development metrics:

| Metric | Value |
| --- | ---: |
| Canonical MRR | 0.8166666667 |
| nDCG@1 | 0.7428571429 |
| nDCG@3 | 0.7364457838 |
| nDCG@5 | 0.7916419043 |
| nDCG@10 | 0.8312065767 |
| Recall@1 | 0.5500000000 |
| Recall@3 | 0.7000000000 |
| Recall@5 | 0.8500000000 |
| Recall@10 | 0.9500000000 |

## Hybrid Improvement over Dense Reference

Hybrid minus Dense D1:

| Metric | Absolute delta | Relative delta |
| --- | ---: | ---: |
| Canonical MRR | +0.0333333333 | +4.26% |
| nDCG@10 | +0.0482279271 | +6.16% |
| Recall@10 | +0.0000000000 | +0.00% |

Because hybrid improved the preregistered primary metric, nDCG@10, it was
selected without requiring either tie-breaker.

Selected retriever:

```text
hybrid:rrf-k60-v1
```

## Per-Query Complementarity

Compared with frozen Dense D1 on development nDCG@10:

```text
hybrid wins:   5
ties:          3
hybrid losses: 2
```

Per-query outcomes:

| Query | Type | Dense nDCG@10 | Hybrid nDCG@10 | Outcome |
| --- | --- | ---: | ---: | --- |
| Q-0001 | lexical | 0.968015 | 0.968015 | tie |
| Q-0002 | lexical | 1.000000 | 1.000000 | tie |
| Q-0004 | semantic | 0.955831 | 1.000000 | hybrid win |
| Q-0006 | semantic | 0.730929 | 0.833991 | hybrid win |
| Q-0008 | hybrid | 0.877215 | 0.877215 | tie |
| Q-0009 | hybrid | 0.817530 | 0.613147 | hybrid loss |
| Q-0017 | multi_source | 0.613147 | 0.395647 | hybrid loss |
| Q-0019 | multi_source | 0.605260 | 0.624051 | hybrid win |
| Q-0020 | mixed_tool | 0.630930 | 1.000000 | hybrid win |
| Q-0021 | mixed_tool | 0.630930 | 1.000000 | hybrid win |

The aggregate improvement is therefore not produced by uniform per-query
dominance.

## Diagnostic Behavior

### Q-0006

Dense D1:

```text
canonical reciprocal rank = 0.333333
nDCG@10                   = 0.730929
Recall@10                 = 1.000000
```

Hybrid:

```text
canonical reciprocal rank = 0.500000
nDCG@10                   = 0.833991
Recall@10                 = 1.000000
```

The hybrid improves ordering while maintaining complete top-10 relevant
coverage.

### Q-0009

Dense D1:

```text
canonical reciprocal rank = 1.000000
nDCG@10                   = 0.817530
Recall@10                 = 1.000000
```

Hybrid:

```text
canonical reciprocal rank = 1.000000
nDCG@10                   = 0.613147
Recall@10                 = 0.500000
```

This is a clear hybrid regression. The canonical result remains first, but one
relevant item falls outside the top 10.

### Q-0017

Dense D1:

```text
canonical reciprocal rank = 1.000000
nDCG@10                   = 0.613147
Recall@10                 = 0.500000
```

Hybrid:

```text
canonical reciprocal rank = 0.166667
nDCG@10                   = 0.395647
Recall@10                 = 1.000000
```

Fusion increases relevant top-10 coverage from 0.5 to 1.0 but pushes the
canonical evidence from rank 1 to rank 6.

This case demonstrates a real fusion tradeoff between coverage and canonical
ordering.

### Q-0019

Dense D1:

```text
canonical reciprocal rank = 0.500000
nDCG@10                   = 0.605260
Recall@10                 = 1.000000
```

Hybrid:

```text
canonical reciprocal rank = 0.500000
nDCG@10                   = 0.624051
Recall@10                 = 1.000000
```

Fusion provides a modest ordering gain while preserving canonical rank and
coverage.

### Q-0020

Dense D1:

```text
canonical reciprocal rank = 0.500000
nDCG@10                   = 0.630930
Recall@10                 = 1.000000
```

Hybrid:

```text
canonical reciprocal rank = 1.000000
nDCG@10                   = 1.000000
Recall@10                 = 1.000000
```

Fusion improves both canonical ordering and ranked relevance quality to the
maximum measured value.

### Q-0021

Dense D1:

```text
canonical reciprocal rank = 0.500000
nDCG@10                   = 0.630930
Recall@10                 = 1.000000
```

Hybrid:

```text
canonical reciprocal rank = 1.000000
nDCG@10                   = 1.000000
Recall@10                 = 1.000000
```

This is another strong complementary-fusion case.

## Interpretation

The Phase 6A result supports the hypothesis that lexical and dense retrieval
contain complementary ranking information on the Northstar development set.

Fixed equal-weight RRF improved aggregate nDCG@10 and canonical MRR relative
to the strongest frozen standalone retriever without changing either source
retriever.

The experiment also shows that fusion is not uniformly beneficial. In
particular, Q-0009 and Q-0017 regress on nDCG@10, and Q-0017 exposes a
coverage-versus-canonical-ordering tradeoff.

These regressions are retained as part of the measured result rather than
being used to retune `k` after observing outcomes.

## Reproducibility

Canonical artifact:

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

An independent CPU rerun written to:

```text
/tmp/rrf-k60-development.json
```

produced a byte-identical artifact with the same SHA-256 and size.

## Integrity Verification

The measured artifact was programmatically verified to confirm:

- experiment version is `hybrid-rrf-baseline-v1`;
- scope is `development-only`;
- dense reference is `dense:e5-document-title-text-v1`;
- hybrid candidate is `hybrid:rrf-k60-v1`;
- primary metric is `mean_ndcg_at_10`;
- secondary metric is canonical MRR;
- tertiary metric is Recall@10;
- exact ties retain Dense D1;
- frozen BM25 artifact SHA-256 matches the preregistration;
- frozen dense artifact SHA-256 matches the preregistration;
- benchmark version is `northstar-hybrid-rrf-baseline-v1`;
- fusion version is `rrf-k60-v1`;
- RRF `k` is exactly `60`;
- absent rankings contribute zero;
- deterministic tie-breaker is `chunk_id`;
- BM25 version is `bm25-v1`;
- tokenizer is `lexical-tokenizer-v1`;
- lexical representation is `document-title-text-v1`;
- BM25 parameters remain `k1=1.5`, `b=0.75`;
- BM25 zero-overlap policy remains excluded;
- dense version is `dense-e5-small-v2-v1`;
- dense representation is `e5-document-title-text-v1`;
- E5 model is `intfloat/e5-small-v2`;
- E5 revision is
  `ffb93f3bd4047442299a41ebb6fa998a38507c52`;
- corpus contains exactly 80 chunks;
- exactly 10 retrieval-eligible development cases are evaluated;
- the exact preregistered development query IDs are present;
- dense retrieval returns all 80 chunks;
- fused retrieval returns all 80 chunks.

The integrity audit completed successfully.

## Final Quality Gate

After measurement and reproducibility verification:

```text
Ruff:                 passed
Formatting:           passed
Tests:                177 passed
Dependency lock:      valid
Alembic current:      8a0f69a3baf1 (head)
Alembic drift:        none
Phase 6A artifacts:   1
Frozen input hashes:  unchanged
```

The source tree remained at the clean preregistration commit throughout
measurement:

```text
2f11268a3e17e02d5fd8f2e9cedccc5358dc52ed
```

until the measured result was ready to be documented and frozen.

## Claim Boundary

Phase 6A supports claims that:

- deterministic Reciprocal Rank Fusion was implemented for frozen BM25 and E5
  rankings;
- the experiment used fixed equal-weight RRF with `k=60`;
- the formula, source retrievers, development query set, metric ordering, and
  selection policy were frozen before measurement;
- the hybrid achieved approximately `0.8167` canonical MRR, `0.8312`
  nDCG@10, and `0.95` Recall@10 on 10 synthetic Northstar development
  retrieval cases;
- the hybrid improved development nDCG@10 by approximately `6.16%` relative
  to the strongest frozen standalone dense reference;
- the hybrid improved development canonical MRR by approximately `4.26%`
  relative;
- Recall@10 remained unchanged at `0.95`;
- the hybrid won 5, tied 3, and lost 2 development queries on nDCG@10 versus
  Dense D1;
- the Phase 6A artifact reproduced byte-identically.

Phase 6A does not support claims that:

- the hybrid has been confirmed on the seed test split;
- `k=60` is the optimal RRF constant;
- RRF is universally superior to dense or lexical retrieval;
- the result generalizes to real enterprise corpora;
- weighted RRF or learned fusion is superior;
- cross-encoder reranking is implemented;
- pgvector serving behavior is measured;
- production latency, throughput, or scale has been established;
- generation quality has been measured;
- end-to-end agent performance has been measured.
