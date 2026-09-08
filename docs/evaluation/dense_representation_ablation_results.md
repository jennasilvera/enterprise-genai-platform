# Dense Representation Ablation Results

## Status

**MEASURED / VERIFIED**

Phase 5B evaluates the preregistered dense representation experiment defined
before candidate measurement.

The experiment compares:

```text
D0: e5-evidence-text-v1
D1: e5-document-title-text-v1
```

The candidate was measured only after the experimental design, implementation,
tests, and selection policy were committed and tagged.

## Preregistration Boundary

Pre-measurement commit:

```text
c51d88d2b5ec2062a0d28aaeb5484499d541631f
```

Pre-measurement tag:

```text
phase-5b-dense-ablation-preregistered
```

At the preregistration boundary:

- 162 tests passed;
- the Phase 5A baseline reproduced byte-identically;
- no Phase 5B measurement artifact existed;
- the experiment CLI exposed only `--output`;
- the representation candidates and selection policy were fixed.

## Experimental Question

The experiment asks:

> Does adding legitimate document-title context to an E5 passage
> representation improve dense retrieval over evidence-text-only passages on
> the fixed Northstar development benchmark?

## Fixed Variables

The following were held constant:

```text
dataset                 northstar-v1
chunk strategy          evidence-block-v1
corpus                   80 chunks
evaluation scope         development only
eligible cases           10
model                    intfloat/e5-small-v2
model revision           ffb93f3bd4047442299a41ebb6fa998a38507c52
embedding dimension      384
device                   CPU
query prefix             query:
passage prefix           passage:
normalization            L2
similarity               normalized inner product
batch size               16
tie breaking             (-score, chunk_id)
```

No BM25 fusion, reranking, query decomposition, LLM generation, or agent
orchestration participated in this experiment.

## Experimental Variable

Baseline:

```text
e5-evidence-text-v1
```

Passage:

```text
passage: <evidence text>
```

Candidate:

```text
e5-document-title-text-v1
```

Passage:

```text
passage: <document title>
<evidence text>
```

Document title was the only added retrieval content.

No synthetic heading, generated metadata, explicit company field, or
additional provenance field was introduced.

## Preregistered Selection Policy

Primary:

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

If all three are exactly tied:

```text
retain D0
```

No minimum improvement threshold was defined.

Diagnostic cases were not permitted to override this aggregate selection
policy.

## Development Results

### D0 — evidence text

| Metric | Value |
| --- | ---: |
| Canonical MRR | 0.6110028860 |
| nDCG@10 | 0.6084296075 |
| Recall@10 | 0.8000000000 |

### D1 — document title + evidence text

| Metric | Value |
| --- | ---: |
| Canonical MRR | 0.7833333333 |
| nDCG@1 | 0.6428571429 |
| nDCG@3 | 0.7092233169 |
| nDCG@5 | 0.7406996662 |
| nDCG@10 | 0.7829786496 |
| Recall@1 | 0.4000000000 |
| Recall@3 | 0.7500000000 |
| Recall@5 | 0.8500000000 |
| Recall@10 | 0.9500000000 |

## Candidate Improvement over Baseline

D1 minus D0:

| Metric | Absolute delta | Relative delta |
| --- | ---: | ---: |
| Canonical MRR | +0.1723304473 | +28.20% |
| nDCG@10 | +0.1745490421 | +28.69% |
| Recall@10 | +0.1500000000 | +18.75% |

Because nDCG@10 is the preregistered primary criterion, D1 is selected without
requiring a tie-breaker.

Selected representation:

```text
e5-document-title-text-v1
```

## Diagnostic Behavior

### Q-0017

Under D0:

```text
canonical reciprocal rank: 0.111111
Recall@10:                0.500000
nDCG@10:                  0.184576
```

Under D1:

```text
canonical reciprocal rank: 1.000000
Recall@10:                0.500000
nDCG@10:                  0.613147
```

The canonical evidence moves from rank 9 to rank 1.

Recall@10 remains 0.5, so document-title context repairs canonical ranking but
does not recover every relevant evidence item.

### Q-0021

Under D0:

```text
canonical reciprocal rank: 0.022727
Recall@10:                0.000000
nDCG@10:                  0.000000
```

Under D1:

```text
canonical reciprocal rank: 0.500000
Recall@10:                1.000000
nDCG@10:                  0.630930
```

The canonical evidence moves from approximately rank 44 to rank 2 and relevant
top-10 coverage is restored.

This behavior is consistent with the preregistered hypothesis that
evidence-text-only semantic retrieval can lose useful source/entity context,
while document title provides legitimate contextual information.

The experiment does not establish that this mechanism explains every query or
every improvement.

## Non-Uniform Effects

D1 does not improve every metric for every individual query.

For example, Q-0006 canonical reciprocal rank decreases from:

```text
0.500000
```

to:

```text
0.333333
```

while its overall relevant-ranking quality remains strong.

The selected representation is therefore an aggregate development winner, not
a claim of universal per-query dominance.

## Descriptive Comparison with Frozen BM25

For context only, the selected dense representation was compared with the
previously frozen BM25 `document-title-text-v1` development result.

| Metric | BM25 | Dense D1 | Dense minus BM25 |
| --- | ---: | ---: | ---: |
| Canonical MRR | 0.659091 | 0.783333 | +0.124242 |
| nDCG@10 | 0.677258 | 0.782979 | +0.105721 |
| Recall@10 | 0.800000 | 0.950000 | +0.150000 |

Relative differences:

```text
Canonical MRR: +18.85%
nDCG@10:       +15.61%
Recall@10:     +18.75%
```

This comparison was not part of the Phase 5B selection policy and was
performed only after D1 had already been selected under the preregistered
D0-versus-D1 experiment.

It does not establish general superiority of dense retrieval over lexical
retrieval.

## Reproducibility

Canonical result artifact:

```text
artifacts/evaluation/phase5b/e5-document-title-text-v1-development.json
```

SHA-256:

```text
ed406dacfec38bd97de7ccb42ad84b6d2ab6e00332e3b52b1cec171593d67f87
```

Size:

```text
76204 bytes
```

An independent CPU rerun written to a separate `/tmp` path produced a
byte-identical artifact with the same SHA-256 and size.

## Integrity Verification

The measured artifact was programmatically checked to confirm:

- experiment version is `dense-representation-ablation-v1`;
- scope is `development-only`;
- baseline is `e5-evidence-text-v1`;
- candidate is `e5-document-title-text-v1`;
- selected representation is `e5-document-title-text-v1`;
- the primary selection metric is `mean_ndcg_at_10`;
- canonical MRR is the secondary metric;
- Recall@10 is the tertiary metric;
- exact ties retain D0;
- candidate benchmark metadata records the correct representation;
- model is `intfloat/e5-small-v2`;
- model revision is
  `ffb93f3bd4047442299a41ebb6fa998a38507c52`;
- exactly the ten preregistered development query IDs are evaluated;
- every evaluated case is marked as development.

The audit completed successfully.

## Quality Gate

After measurement:

```text
Ruff:                 passed
Formatting:           passed
Tests:                162 passed
Alembic current:      8a0f69a3baf1 (head)
Alembic drift:        none
Phase 5B artifacts:   1
```

## Interpretation

The experiment provides evidence that document-title metadata materially
improves dense retrieval quality on this benchmark when the embedding model
and all other retrieval variables are held fixed.

The result is especially useful because it identifies representation design,
rather than model replacement, as a major source of retrieval quality.

It also shows why embedding only isolated evidence text can be insufficient in
enterprise corpora: a semantically appropriate passage can still lack enough
source identity or document-level context to rank correctly.

## Claim Boundary

Phase 5B supports claims that:

- a controlled dense representation ablation was preregistered before
  candidate measurement;
- the experiment changed document-title context while holding the dense model
  and retrieval configuration fixed;
- `e5-document-title-text-v1` was selected under a preregistered development
  nDCG@10 criterion;
- the selected representation achieved approximately `0.7833` canonical MRR,
  `0.7830` nDCG@10, and `0.95` Recall@10;
- title enrichment improved development nDCG@10 by approximately `28.69%`
  relative to the evidence-text baseline;
- the candidate artifact reproduced byte-identically;
- the selected dense representation exceeded the frozen BM25 development
  reference on the three reported aggregate metrics.

Phase 5B does not support claims that:

- dense retrieval is generally superior to BM25;
- the selected representation has been confirmed on the seed test split;
- the result generalizes to real enterprise data;
- hybrid fusion is implemented or superior;
- pgvector retrieval has been implemented;
- cross-encoder reranking has been implemented;
- production latency, throughput, or scalability has been established;
- agent behavior or end-to-end RAG quality has been established.
