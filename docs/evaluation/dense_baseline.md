# Dense Retrieval Baseline

## Status

**Measured / development-verified dense retrieval baseline.**

Phase 5A establishes the first independent dense retrieval system for the
Northstar benchmark.

The dense baseline is intentionally evaluated before:

- dense representation ablation;
- BM25+dense fusion;
- reciprocal-rank fusion;
- cross-encoder reranking;
- query decomposition;
- LLM generation;
- agent orchestration.

## Experimental Question

The Phase 5A question is:

> How well does an independently implemented dense semantic retriever perform
> on the existing evidence-block corpus before metadata enrichment, hybrid
> fusion, or reranking?

This phase is a baseline measurement rather than a model-selection
competition.

## Fixed Dataset and Retrieval Scope

Dataset:

```text
northstar-v1
```

Chunk strategy:

```text
evidence-block-v1
```

Corpus size:

```text
80 chunks
```

Evaluation scope:

```text
10 retrieval-eligible development cases
```

Development cases:

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

No test cases are evaluated in Phase 5A.

## Dense Model

Model:

```text
intfloat/e5-small-v2
```

Pinned model revision:

```text
ffb93f3bd4047442299a41ebb6fa998a38507c52
```

Embedding dimension:

```text
384
```

Maximum sequence length observed at runtime:

```text
512
```

Execution device:

```text
CPU
```

The Phase 5A implementation does not claim CUDA or GPU execution.

## Runtime Dependency Tuple

Direct project dependencies:

```text
numpy==2.5.2
sentence-transformers==6.0.1
torch==2.13.0
```

Observed runtime versions:

```text
numpy                 2.5.2
torch                 2.13.0+cpu
transformers          5.16.1
sentence-transformers 6.0.1
```

PyTorch runtime observation:

```text
cuda_available: False
cuda_device_count: 0
execution_device: cpu
```

## Representation

Dense representation version:

```text
e5-evidence-text-v1
```

Query representation:

```text
query: <evaluation question>
```

Passage representation:

```text
passage: <evidence text>
```

The document title is deliberately excluded from Phase 5A.

This isolates the behavior of evidence-text semantic retrieval from the title
metadata enrichment previously studied for BM25.

A title-enriched dense representation is therefore a separate experimental
variable and is not part of this baseline.

## Embedding and Similarity Policy

Embeddings are generated with:

```text
normalize_embeddings=True
```

The implementation verifies that output vectors are finite and L2 normalized.

Similarity is:

```text
inner product of L2-normalized vectors
```

For unit-normalized vectors this produces cosine-equivalent ranking.

Search ordering is deterministic:

```text
(-similarity_score, chunk_id)
```

The stable chunk ID is used as the tie-breaker.

Dense retrieval returns every corpus item unless `top_k` is explicitly
provided. Unlike BM25, there is no lexical zero-overlap rule.

## Implementation Validation

The standard test suite after implementation contains:

```text
150 passing tests
```

Tests cover:

- dense configuration validation;
- non-empty index enforcement;
- inner-product ranking;
- deterministic chunk-ID tie-breaking;
- `top_k` validation;
- rejection of non-normalized embeddings;
- rejection of incorrect embedding shapes;
- empty-query behavior;
- development-only evaluation scoping;
- exact development query IDs;
- benchmark metadata recording.

The ordinary unit-test suite uses deterministic fake encoders rather than
requiring Hugging Face downloads.

## Real-Model Invariance Probe

The full 80-chunk corpus was encoded with E5 using batch sizes 1 and 16.

Observed shapes:

```text
batch_size_1:  (80, 384)
batch_size_16: (80, 384)
```

Maximum absolute difference between batch-size executions:

```text
1.7136335372924805e-07
```

Batch-size comparison:

```text
allclose(atol=1e-6, rtol=1e-6): True
```

Repeated batch-size-16 encoding maximum absolute difference:

```text
0.0
```

Repeated execution comparison:

```text
allclose(atol=1e-7, rtol=1e-7): True
```

Observed embedding norm range:

```text
minimum: 0.9999999403953552
maximum: 1.0000001192092896
```

The experiment therefore supports stable normalized CPU embedding behavior
for this corpus and environment.

## Development Results

The Phase 5A dense baseline produced:

| Metric | Value |
| --- | ---: |
| Canonical MRR | 0.611003 |
| nDCG@1 | 0.500000 |
| nDCG@3 | 0.507133 |
| nDCG@5 | 0.530853 |
| nDCG@10 | 0.608430 |
| Recall@1 | 0.300000 |
| Recall@3 | 0.500000 |
| Recall@5 | 0.550000 |
| Recall@10 | 0.800000 |

## Results by Query Type

### Lexical

Two cases:

```text
canonical MRR: 1.000000
nDCG@10:       0.978384
Recall@10:     1.000000
```

### Semantic

Two cases:

```text
canonical MRR: 0.750000
nDCG@10:       0.810573
Recall@10:     1.000000
```

### Hybrid-labeled queries

Two cases:

```text
canonical MRR: 1.000000
nDCG@10:       0.722351
Recall@10:     0.750000
```

The `hybrid` label describes the evaluation query type. Phase 5A itself does
not implement hybrid retrieval.

### Multi-source

Two cases:

```text
canonical MRR: 0.222222
nDCG@10:       0.364174
Recall@10:     0.750000
```

### Mixed-tool

Two cases:

```text
canonical MRR: 0.082792
nDCG@10:       0.166667
Recall@10:     0.500000
```

The `mixed_tool` label describes the expected information requirement.
Phase 5A does not implement tool routing or multiple tools.

## Diagnostic Cases

### Q-0017 — multi-source

Dense baseline:

```text
canonical reciprocal rank: 0.111111
Recall@10:                0.500000
nDCG@10:                  0.184576
```

The canonical evidence reaches rank 9, giving partial top-10 recovery.

This is diagnostically different from the previously selected
title-plus-text BM25 representation, for which the relevant evidence remained
outside the top 10.

The result suggests that semantic retrieval can recover evidence that a
lexical ranker misses, but it does not solve the full multi-source query.

### Q-0021 — mixed-tool

Dense baseline:

```text
canonical reciprocal rank: 0.022727
Recall@10:                0.000000
nDCG@10:                  0.000000
```

The canonical item is far below the top 10.

Top-ranked results are generic financial evidence from other companies.

This is consistent with a hypothesis that evidence-text-only dense retrieval
can lose entity or source context when the required identity is not explicit
enough in the evidence text.

That hypothesis motivates a controlled title-metadata experiment in a later
phase. It is not treated as proven by this single case.

## Comparison with Frozen BM25 Development Reference

The comparison reference is the Phase 4B
`document-title-text-v1` BM25 representation.

Important experimental qualification:

`document-title-text-v1` was the post-hoc robustness-selected follow-on
representation after the preregistered Phase 4B experiment. It was not the
preregistered Phase 4B winner.

Frozen BM25 development metrics:

| Metric | BM25 | Dense |
| --- | ---: | ---: |
| Canonical MRR | 0.659091 | 0.611003 |
| nDCG@10 | 0.677258 | 0.608430 |
| Recall@10 | 0.800000 | 0.800000 |

Dense-minus-BM25 absolute changes:

```text
Canonical MRR: -0.048088
nDCG@10:       -0.068829
Recall@10:      0.000000
```

Approximate relative changes:

```text
Canonical MRR: -7.30%
nDCG@10:       -10.16%
Recall@10:      0.00%
```

The dense baseline therefore does not outperform the frozen BM25 development
reference in aggregate MRR or nDCG@10.

However, aggregate equality in Recall@10 and differing case-level behavior
show that the two retrieval modes do not make identical errors.

Phase 5A therefore supports investigating complementarity rather than
replacing BM25 with dense retrieval based on this benchmark.

## Reproducibility

Canonical artifact:

```text
artifacts/evaluation/phase5a/e5-small-v2-development.json
```

SHA-256:

```text
b388e10207467018434a26c54cf5002953c698a9988b7a23d2194919e43fa11a
```

Size:

```text
68512 bytes
```

A second CPU execution routed to a separate `/tmp` output produced a
byte-identical JSON artifact with the same SHA-256 and size.

The evaluation CLI exposes `--output` but does not expose model, revision,
representation, device, split, or retrieval configuration as selection
arguments.

## Interpretation

The initial dense retriever is meaningfully capable but not uniformly
superior to the mature lexical baseline.

It performs strongly on the benchmark's lexical and semantic development
cases, partially recovers a difficult BM25 multi-source failure, and performs
poorly on mixed-tool cases where entity/source context can matter.

The measured behavior motivates two later questions:

```text
1. Does legitimate source metadata improve dense retrieval?
2. Are lexical and dense errors complementary enough for hybrid fusion?
```

Those questions are intentionally deferred rather than answered by tuning
Phase 5A after observing its result.

## Claim Boundary

Phase 5A supports claims that:

- a pinned E5-small-v2 dense retriever was implemented and evaluated;
- inference was performed on CPU using 384-dimensional normalized embeddings;
- deterministic inner-product retrieval with stable tie-breaking was
  implemented;
- batch-size embedding differences were below a defined numerical tolerance;
- repeated benchmark execution produced a byte-identical report;
- the 10-case development baseline achieved approximately `0.6110`
  canonical MRR, `0.6084` nDCG@10, and `0.80` Recall@10;
- dense retrieval exhibited behavior different from BM25 on specific
  development cases.

Phase 5A does **not** support claims that:

- dense retrieval outperforms BM25 overall;
- dense retrieval was evaluated on the seed test split;
- hybrid retrieval is implemented;
- reciprocal-rank fusion is implemented;
- pgvector retrieval is implemented;
- cross-encoder reranking is implemented;
- query routing or agent orchestration is implemented;
- production-scale retrieval performance has been established;
- the synthetic benchmark establishes generalization to real enterprise data.
