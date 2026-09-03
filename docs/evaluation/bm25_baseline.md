# BM25 Lexical Retrieval Baseline

## Status

**Measured and reproducible baseline.**

This experiment establishes the first standalone retrieval baseline for the
Northstar Capital portfolio-intelligence corpus.

It is intentionally limited to lexical retrieval. It does not use:

- embeddings;
- dense retrieval;
- query rewriting;
- metadata enrichment;
- reranking;
- reciprocal-rank fusion;
- an LLM;
- SQL;
- graph traversal.

This isolation is deliberate so later retrieval approaches can be compared
against a stable lexical reference point.

## Dataset

- Dataset version: `northstar-v1`
- Evaluation version: `northstar-eval-v1-seed`
- Chunk strategy: `evidence-block-v1`
- Persisted retrieval chunks: 80
- Chunk corpus SHA-256 fingerprint:
  `c4283f4789c83e947634b9d04b0af57f60ba77c2255604ee287cedf40c4900ea`

Every evidence block currently maps to one deterministic retrieval chunk.

The evaluation set contains 24 total cases. Fourteen are eligible for
standalone document-retrieval evaluation because they are answerable and
contain evidence-level relevance judgments.

The other ten cases are retained as system-level evaluation cases but are
not included in standalone BM25 retrieval aggregates because they are
unanswerable or require structured SQL/graph reasoning without document
qrels.

## Tokenization

Tokenizer version: `lexical-tokenizer-v1`

The baseline uses deterministic Unicode NFKC normalization and case folding.

Compound identifiers containing separators are preserved as single tokens,
for example:

```text
ORBIS-IDX-7 -> orbis-idx-7
```

The baseline intentionally does not apply:

- stemming;
- lemmatization;
- stop-word removal;
- synonym expansion;
- possessive normalization;
- query expansion.

Any such changes must be evaluated as explicit experiments rather than
silently modifying the baseline.

## BM25

Implementation version: `bm25-v1`

The ranker is implemented in the repository rather than delegated to a
third-party BM25 package.

Baseline parameters:

```text
k1 = 1.5
b  = 0.75
```

The score follows the standard BM25 form:

\[
\operatorname{BM25}(D,q)
=
\sum_{t \in q}
\operatorname{IDF}(t)
\frac{
f(t,D)(k_1+1)
}{
f(t,D)+k_1
\left(
1-b+b\frac{|D|}{\operatorname{avgdl}}
\right)
}.
\]

Only positive-score chunks are returned. Equal-score results use
`chunk_id` as a deterministic secondary sort key.

## Metrics

The benchmark reports:

- Recall@1, @3, @5, and @10;
- graded nDCG@1, @3, @5, and @10;
- canonical reciprocal rank.

Recall treats every evidence judgment with positive relevance as relevant.

nDCG uses the evaluation set's graded relevance labels.

Canonical reciprocal rank measures the reciprocal rank of the first
grade-3 evidence item, where grade 3 represents evidence sufficient to
ground the canonical answer.

## Baseline Results

Across the 14 retrieval-eligible cases:

| Metric | Value |
| --- | ---: |
| Canonical MRR | 0.642744 |
| Recall@1 | 0.357143 |
| Recall@3 | 0.642857 |
| Recall@5 | 0.678571 |
| Recall@10 | 0.821429 |
| nDCG@1 | 0.530612 |
| nDCG@3 | 0.602388 |
| nDCG@5 | 0.619331 |
| nDCG@10 | 0.674342 |

### By query type

| Query type | Cases | Canonical MRR | Recall@3 | Recall@10 | nDCG@10 |
| --- | ---: | ---: | ---: | ---: | ---: |
| Lexical | 3 | 1.000000 | 0.833333 | 0.833333 | 0.972440 |
| Semantic | 3 | 0.833333 | 1.000000 | 1.000000 | 0.929941 |
| Hybrid | 3 | 0.833333 | 0.666667 | 0.833333 | 0.712709 |
| Mixed-tool | 2 | 0.238095 | 0.500000 | 1.000000 | 0.416667 |
| Multi-source | 3 | 0.174074 | 0.166667 | 0.500000 | 0.254060 |

## Interpretation

The lexical cases establish a strong exact-term baseline: canonical
grade-3 evidence was ranked first for all three lexical queries.

The apparently strong semantic-query performance should not be interpreted
as evidence that lexical retrieval solves semantic search. Several semantic
queries retain substantial lexical overlap with their relevant evidence.

The largest weakness appears in multi-source retrieval. Queries that name a
specific portfolio company can rank evidence from other companies highly
when the evidence text itself does not repeat the parent company name.
This motivates a later controlled comparison between text-only BM25 and
metadata-enriched lexical representations.

The diagnostics also show generic terms and possessive fragments such as
`and`, `is`, `the`, and `s` contributing to lexical matching. Tokenizer
normalization and stop-word handling are therefore candidates for later
ablation experiments.

Mixed-tool cases also demonstrate why structured predicates should not be
forced through standalone document retrieval. Those cases ultimately require
SQL or graph reasoning in addition to retrieval.

## Experimental Discipline

The original baseline used fixed conventional parameters before any tuning:

```text
k1 = 1.5
b  = 0.75
```

No parameter was selected based on benchmark performance.

Future lexical configuration choices must be made using development cases
only. The existing test cases have already been inspected during baseline
analysis and therefore should not be repeatedly optimized against.

A fresh held-out evaluation version should be created before final
portfolio-level model selection if a stronger untouched holdout is needed.

## Reproducibility

Canonical report:

```text
artifacts/evaluation/bm25_baseline.json
```

SHA-256:

```text
77398447c9a183863c6d2d29ca2fa9a493b418487d0648d378c6f46424e408c3
```

A second independent execution generated a byte-identical report with the
same SHA-256.

Reproduction command:

```bash
uv run python scripts/evaluation/evaluate_bm25.py \
  --output artifacts/evaluation/bm25_baseline.json
```

Quality gate at baseline freeze:

```text
122 passed
```

## Current Claim Boundary

The measured results support claims about a deterministic, evaluated BM25
lexical baseline on the synthetic Northstar benchmark.

They do **not** yet support claims that:

- hybrid retrieval is implemented;
- dense retrieval is implemented;
- retrieval quality improved by a particular percentage;
- reranking improves retrieval;
- the system achieves production-scale latency or throughput;
- the results generalize to external enterprise datasets.

Those claims require later experiments.
