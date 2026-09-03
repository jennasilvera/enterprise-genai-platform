# BM25 Lexical Representation Ablation

## Status

**Measured development-only ablation with frozen follow-on selection.**

Phase 4B tests whether BM25 retrieval quality changes when the lexical
representation presented to the ranker includes source metadata in addition
to evidence text.

The experiment does not modify:

- the persisted retrieval chunks;
- chunk IDs;
- evidence IDs;
- provenance;
- BM25 scoring;
- BM25 parameters;
- tokenizer behavior;
- relevance judgments.

Only the ephemeral text representation supplied to BM25 changes.

## Fixed Components

- Dataset: `northstar-v1`
- Evaluation: `northstar-eval-v1-seed`
- Chunk strategy: `evidence-block-v1`
- Tokenizer: `lexical-tokenizer-v1`
- Ranker: `bm25-v1`
- BM25 `k1`: `1.5`
- BM25 `b`: `0.75`
- Experimental scope: development retrieval cases only
- Development retrieval cases: 10

Phase 4A remains the frozen text-only reference point.

## Original Preregistered Experiment

The original Phase 4B comparison contained three candidates.

### A0 — `text-only-v1`

Indexed representation:

```text
evidence text
```

### A1 — `company-text-v1`

Indexed representation:

```text
company name
evidence text
```

### A2 — `document-context-text-v1`

Indexed representation:

```text
document title
evidence heading
evidence text
```

The preregistered selection rule was:

1. maximize development mean nDCG@10;
2. use development canonical MRR and Recall@10 as secondary metrics;
3. require all development lexical queries to retain canonical evidence at
   rank 1.

No test case was used to select among A0, A1, and A2.

## Preregistered Results

| Representation | Canonical MRR | Recall@10 | nDCG@10 | Lexical rank-1 guardrail |
| --- | ---: | ---: | ---: | --- |
| `text-only-v1` | 0.633175 | 0.800000 | 0.657312 | PASS |
| `company-text-v1` | 0.636216 | 0.800000 | 0.661878 | PASS |
| `document-context-text-v1` | 0.709091 | 0.800000 | 0.712286 | PASS |

Under the preregistered rule, `document-context-text-v1` is the experimental
winner.

Relative to the frozen text-only baseline, its development nDCG@10 improves
from `0.657312` to `0.712286`, an absolute difference of approximately
`0.054974`.

## Failure Analysis

The original hypothesis was that missing company identity caused important
multi-source lexical failures.

The experiment only partially supported that hypothesis.

For Q-0017, the text-only representation ranks the first canonical evidence
item at rank 45.

Adding company identity moves canonical evidence substantially upward, but
does not place either required evidence item in the top 10.

The compound query requires evidence about both:

- financial performance; and
- operating risk.

Those facts live in separate evidence blocks. This exposes a limitation of
single-ranking lexical retrieval for multi-evidence questions.

The failure is retained as a useful target for later dense retrieval, hybrid
fusion, query decomposition, and multi-source orchestration rather than being
optimized away through increasingly aggressive BM25-specific changes.

## Post-Hoc Representation Decomposition

Because the preregistered winner combined both document-title metadata and
evidence headings, a post-hoc diagnostic decomposed those sources.

Two additional variants were evaluated on the same development-only scope.

### D1 — `document-title-text-v1`

```text
document title
evidence text
```

### H1 — `evidence-heading-text-v1`

```text
evidence heading
evidence text
```

These variants were introduced after inspection of the original A0/A1/A2
results and therefore are explicitly labeled post-hoc diagnostics rather than
preregistered competitors.

## Diagnostic Results

| Representation | Role | Canonical MRR | Recall@10 | nDCG@10 | Lexical rank-1 guardrail |
| --- | --- | ---: | ---: | ---: | --- |
| `text-only-v1` | preregistered | 0.633175 | 0.800000 | 0.657312 | PASS |
| `company-text-v1` | preregistered | 0.636216 | 0.800000 | 0.661878 | PASS |
| `document-title-text-v1` | post-hoc diagnostic | 0.659091 | 0.800000 | 0.677258 | PASS |
| `evidence-heading-text-v1` | post-hoc diagnostic | 0.716286 | 0.800000 | 0.697781 | PASS |
| `document-context-text-v1` | preregistered | 0.709091 | 0.800000 | 0.712286 | PASS |

## Interpretation of the Decomposition

Document titles provide natural source metadata available independently of
the evaluation benchmark.

For the Northstar corpus, titles encode useful information such as:

- portfolio-company identity;
- reporting period;
- document class.

For example, a title such as:

```text
HelioGrid Energy Q2 2026 Risk Review
```

can contribute entity, temporal, and document-type terms without altering the
underlying evidence text.

Evidence headings also improve several rankings, but their effect is less
stable across cases. In particular, heading-only representation improves some
risk-oriented queries substantially while making the Q-0017 multi-source case
worse.

Because the evidence headings are synthetic labels created as part of the
controlled corpus, relying on their aggregate metric improvement would make
the lexical representation more dependent on benchmark construction choices.

## Follow-On Representation Decision

The original preregistered winner remains:

```text
document-context-text-v1
```

That result is preserved and must not be rewritten post hoc.

For subsequent retrieval engineering, however, the selected representation
is:

```text
document-title-text-v1
```

This is a robustness decision made after the decomposition diagnostic.

The rationale is:

- it measurably improves over text-only BM25 on the development set;
- it preserves the lexical rank-1 guardrail;
- it uses source-level metadata naturally available at indexing time;
- its effect is easier to attribute;
- it avoids dependence on synthetic evidence-heading labels.

The development nDCG@10 change relative to the frozen text-only baseline is:

```text
0.6573117109945545 -> 0.6772581403046118
```

Absolute change:

```text
+0.0199464293100573
```

Relative change:

```text
approximately +3.03%
```

This percentage refers only to the 10-case Northstar development retrieval
benchmark. It must not be described as a general production improvement.

## Known Remaining Limitation

`document-title-text-v1` does not solve Q-0017 at Recall@10.

Under the diagnostic:

- canonical risk evidence reaches rank 11;
- canonical financial evidence reaches rank 14.

This is useful evidence that the next improvement should not simply consist
of additional lexical metadata or BM25 parameter tuning.

The case requires assembling multiple independently relevant evidence items,
which motivates later experiments involving semantic retrieval, hybrid
retrieval, query decomposition, diversification, and orchestration.

## Experimental Discipline

The test split was not used to choose:

- A0;
- A1;
- A2;
- D1;
- H1;
- the follow-on representation.

The follow-on representation must be frozen before any representation-level
test confirmation is performed.

If later test results motivate a new representation design, that design must
be treated as a new experiment and should not reuse the same test split as an
untouched model-selection set.

## Artifacts

Development-only experiment reports:

```text
artifacts/evaluation/phase4b/text-only-v1.json
artifacts/evaluation/phase4b/company-text-v1.json
artifacts/evaluation/phase4b/document-title-text-v1.json
artifacts/evaluation/phase4b/evidence-heading-text-v1.json
artifacts/evaluation/phase4b/document-context-text-v1.json
```

The reports record case-level rankings, metrics, representation versions, and
the development-only experimental scope.

## Claim Boundary

This phase supports claims that:

- BM25 lexical representations were compared under controlled conditions;
- document metadata changes lexical ranking behavior;
- the original preregistered metadata representation improved development
  retrieval metrics on the synthetic Northstar benchmark;
- a title-plus-text representation was selected for subsequent retrieval work
  after a documented robustness analysis.

This phase does **not** yet support claims that:

- the selected representation improves an untouched external test set;
- dense retrieval is implemented;
- hybrid retrieval is implemented;
- reranking is implemented;
- multi-source retrieval is solved;
- the measured improvement generalizes to external enterprise datasets.
