# BM25 Representation Test Confirmation

## Status

**Measured test-split confirmation of a representation frozen before this run.**

Phase 4C evaluates the lexical representation selected for follow-on work at
the end of Phase 4B:

```text
document-title-text-v1
```

The representation was frozen in Git before this confirmation was executed.

Phase 4C does not select among lexical representations.

## Experimental Boundary

Frozen Phase 4B commit:

```text
d767c3775b8c7de1a024d6dcff3799f6bbe11fc5
```

Frozen Phase 4B tag:

```text
phase-4b-bm25-representation-ablation
```

Selected representation:

```text
document-title-text-v1
```

The Phase 4C evaluation API and CLI intentionally expose no representation
selection argument.

The confirmation therefore cannot choose among:

- `text-only-v1`;
- `company-text-v1`;
- `document-title-text-v1`;
- `evidence-heading-text-v1`;
- `document-context-text-v1`.

## Fixed Components

- Dataset: `northstar-v1`
- Evaluation: `northstar-eval-v1-seed`
- Chunk strategy: `evidence-block-v1`
- Tokenizer: `lexical-tokenizer-v1`
- Ranker: `bm25-v1`
- BM25 `k1`: `1.5`
- BM25 `b`: `0.75`
- Representation: `document-title-text-v1`
- Test retrieval cases: 4

## Important Holdout Qualification

This is a test-split confirmation of a representation selected without using
the test cases during Phase 4B representation selection.

However, the Phase 4A text-only benchmark had already exposed the seed test
results earlier in development.

Therefore this split must not be described as a pristine untouched external
holdout.

The correct description is:

```text
test-split confirmation of a development-selected representation
```

## Frozen Text-Only Test Reference

The Phase 4A text-only test metrics were:

| Metric | Value |
| --- | ---: |
| Canonical MRR | 0.666667 |
| nDCG@1 | 0.500000 |
| nDCG@3 | 0.662314 |
| nDCG@5 | 0.662314 |
| nDCG@10 | 0.716916 |
| Recall@1 | 0.375000 |
| Recall@3 | 0.750000 |
| Recall@5 | 0.750000 |
| Recall@10 | 0.875000 |

## Selected Representation Test Result

`document-title-text-v1` produced:

| Metric | Value |
| --- | ---: |
| Canonical MRR | 0.675000 |
| nDCG@1 | 0.500000 |
| nDCG@3 | 0.662314 |
| nDCG@5 | 0.721614 |
| nDCG@10 | 0.721614 |
| Recall@1 | 0.375000 |
| Recall@3 | 0.750000 |
| Recall@5 | 0.875000 |
| Recall@10 | 0.875000 |

## Comparison to Frozen Text-Only Reference

Absolute changes:

```text
Canonical MRR   +0.008333333333333415
nDCG@10         +0.004697568987782952
Recall@10        0.0
```

The nDCG@10 change is approximately a `+0.66%` relative improvement over the
frozen text-only test reference.

Recall@5 improves from:

```text
0.750000 -> 0.875000
```

while Recall@10 remains unchanged.

This indicates that title enrichment moved some relevant evidence earlier in
the ranking without increasing total relevant-evidence coverage at rank 10.

## Case-Level Result

### Q-0003 — lexical

```text
canonical reciprocal rank: 1.0
Recall@10:                1.0
nDCG@10:                  1.0
```

The canonical NovaBio supplier-risk evidence ranks first.

### Q-0005 — semantic

```text
canonical reciprocal rank: 1.0
Recall@10:                1.0
nDCG@10:                  0.955831
```

The canonical HelioGrid operating-signal evidence ranks first.

### Q-0007 — hybrid

```text
canonical reciprocal rank: 0.5
Recall@10:                1.0
nDCG@10:                  0.693426
```

The query retrieves both required evidence items within the evaluated range,
but the canonical evidence does not rank first.

### Q-0018 — multi-source

```text
canonical reciprocal rank: 0.2
Recall@10:                0.5
nDCG@10:                  0.237198
```

This remains the weakest test case.

Only half of the relevant evidence is retrieved within the top 10, providing
additional evidence that multi-source information needs remain a limitation
of the current lexical retriever.

## Interpretation

The Phase 4B follow-on representation shows a small positive transfer from
development to test.

The result does not justify claiming a large retrieval improvement.

It does support the narrower conclusion that adding document-title metadata:

- did not degrade aggregate test retrieval quality;
- slightly improved canonical MRR;
- slightly improved nDCG@10;
- improved Recall@5;
- preserved Recall@10;
- preserved the lexical rank-1 guardrail.

The remaining multi-source weakness supports moving to a fundamentally
different retrieval capability rather than continuing to optimize lexical
metadata against the seed benchmark.

## Artifact

Canonical result:

```text
artifacts/evaluation/phase4c/document-title-text-v1-test.json
```

SHA-256:

```text
72666dbd40d60061d33775a285b06e45eb3826f3ea121f8a7476c6f73d9786b3
```

Size:

```text
37199 bytes
```

## Claim Boundary

This phase supports claims that:

- the BM25 representation was frozen before its test-split confirmation;
- the selected title-enriched representation showed a small positive
  confirmation relative to the frozen text-only reference;
- test nDCG@10 changed from approximately `0.7169` to `0.7216`;
- test Recall@5 changed from `0.75` to `0.875`;
- test Recall@10 remained `0.875`;
- multi-source retrieval remains an identified weakness.

This phase does **not** support claims that:

- the seed test split is a pristine external holdout;
- the result generalizes to production enterprise datasets;
- title enrichment meaningfully solves multi-source retrieval;
- dense retrieval is implemented;
- hybrid retrieval is implemented;
- reranking is implemented;
- an LLM or agent caused these retrieval improvements.
