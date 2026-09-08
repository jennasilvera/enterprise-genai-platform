# Dense Representation Ablation Plan

## Status

**Pre-measurement experimental plan.**

No Phase 5B candidate result has been measured at the time this plan is
created.

## Purpose

Phase 5A established an evidence-text-only dense retrieval baseline using
E5-small-v2.

Phase 5B changes exactly one experimental variable: the text supplied as the
passage representation.

The experiment asks:

> Does adding legitimate document-title context improve dense retrieval over
> evidence-text-only passages on the fixed Northstar development benchmark?

## Frozen Baseline

Phase 5A commit:

```text
38361142f73f71b1f99be9e7fb39b1f038ca9b0a
```

Phase 5A tag:

```text
phase-5a-dense-baseline
```

Baseline artifact:

```text
artifacts/evaluation/phase5a/e5-small-v2-development.json
```

Baseline SHA-256:

```text
b388e10207467018434a26c54cf5002953c698a9988b7a23d2194919e43fa11a
```

Baseline representation:

```text
e5-evidence-text-v1
```

Representation:

```text
passage: <evidence text>
```

## Candidate Representation

Candidate version:

```text
e5-document-title-text-v1
```

Representation:

```text
passage: <document title>
<evidence text>
```

Document title is the only new retrieval content.

No evidence heading, company-name field, synthetic metadata, generated text,
or additional provenance text is added.

## Fixed Variables

The following remain fixed from Phase 5A:

```text
dataset                 northstar-v1
chunk strategy          evidence-block-v1
corpus                   80 chunks
evaluation split         development only
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

No BM25 scores are fused into either dense representation.

No reranker is used.

No query decomposition is used.

No LLM or agent participates in retrieval.

## Development Cases

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

No seed test case will be used for Phase 5B representation selection.

## Selection Policy

The selected representation is determined using development metrics only.

Primary criterion:

```text
mean nDCG@10
```

If the primary metric is exactly tied, use:

```text
canonical MRR
```

If both are exactly tied, use:

```text
Recall@10
```

If all three are exactly tied, retain the simpler frozen baseline:

```text
e5-evidence-text-v1
```

There is no minimum-improvement threshold.

The measured result is preserved even if the candidate is worse than the
baseline.

## Diagnostic Cases

Q-0017 and Q-0021 are important diagnostic cases because Phase 5A exposed
different failure behavior on them.

They are not selection criteria.

A candidate cannot be selected solely because it improves one of those
queries.

## Interpretation Boundary

If title context improves retrieval, the supported conclusion will be that
source-level document title metadata improved development retrieval under the
fixed E5 configuration.

It will not establish that:

- dense retrieval generalizes to production data;
- dense retrieval is superior to BM25;
- hybrid fusion is beneficial;
- pgvector improves retrieval quality;
- reranking is beneficial;
- test-set performance improved.

Those questions remain separate experiments.
