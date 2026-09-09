# Cross-Encoder Reranker Development Plan

## Status

PRE-MEASUREMENT / PREREGISTERED

No Phase 7A Northstar cross-encoder score has been produced when this plan is
created.

## Purpose

Phase 7A evaluates whether a second-stage cross-encoder can improve final
relevance ordering over the frozen Phase 6A hybrid RRF candidate generator
while preserving its development-set top-10 recall.

Phase 6B showed that equal-weight RRF preserved top-10 coverage on its four
confirmation queries but degraded ordering on two of them.

Phase 7A is a new development-only experiment.

The Phase 6B test queries are not used for Phase 7A selection or tuning.

## Frozen Candidate Generator

Candidate generator:

hybrid:rrf-k60-v1

Frozen Phase 6A artifact:

artifacts/evaluation/phase6a/rrf-k60-development.json

Frozen Phase 6A SHA-256:

c0f850e21d25f993f26c58b44d0ace057fbcd23380dce85039f2b4d6c2593c21

Frozen BM25:
- version: bm25-v1
- tokenizer: lexical-tokenizer-v1
- representation: document-title-text-v1
- k1: 1.5
- b: 0.75
- zero-overlap chunks excluded

Frozen dense retriever:
- version: dense-e5-small-v2-v1
- representation: e5-document-title-text-v1
- model: intfloat/e5-small-v2
- revision: ffb93f3bd4047442299a41ebb6fa998a38507c52
- device: CPU
- normalized embeddings
- inner-product similarity

Frozen fusion:
- version: rrf-k60-v1
- k: 60
- equal source contributions
- missing source rank contribution: 0
- deterministic chunk_id tie-break

No Phase 7A change to the candidate generator is permitted.

## Candidate Regeneration

The frozen Phase 6A artifact serializes only the first 10 fused results per
query even though the runtime RRF implementation computes the complete fused
ranking.

Phase 7A therefore regenerates the frozen RRF ranking from the same frozen
BM25 and E5 components.

Before reranking, the regenerated ranking must be checked against the frozen
Phase 6A artifact.

For every development query:
- aggregate baseline metrics must match;
- the serialized Phase 6A top-10 chunk identities must match;
- top-10 evidence identities must match;
- top-10 RRF ordering must match.

If regeneration does not match the frozen Phase 6A reference, Phase 7A must
stop before cross-encoder measurement.

## Reranker

Reranker version:

cross-encoder-ms-marco-minilm-l6-v2-v1

Model:

cross-encoder/ms-marco-MiniLM-L6-v2

Immutable revision:

233902d25c440f23af6f7d6e94d2946bac0bee0a

Library:

sentence-transformers

Backend:

torch

Device:

cpu

Batch size:

16

Cross-encoder output used for ordering:

raw single-label score

The prediction call uses an identity activation and does not apply softmax.

No cross-encoder score is combined numerically with BM25, E5, or RRF scores.

## Reranker Input Representation

Each cross-encoder pair is:

query

paired with:

document title + newline + evidence text

This is the same represented text already used by the frozen Dense D1 corpus.

Representation version:

cross-encoder-document-title-text-v1

No synthetic evidence heading is added.

## Candidate Cutoff

Only the first 20 frozen RRF candidates are cross-encoder scored.

candidate_k = 20

The value 20 is fixed before Northstar cross-encoder measurement.

There is no cutoff sweep.

The experiment does not evaluate:
- top 10;
- top 30;
- top 50;
- top 80;
- or any adaptive cutoff.

## Final Ranking Construction

Frozen RRF positions 1 through 20 are reordered using cross-encoder scores.

Within those 20 candidates, deterministic ordering is:

1. cross-encoder score descending;
2. original RRF rank ascending;
3. chunk_id ascending.

Frozen RRF positions 21 through 80 are appended unchanged in their original
RRF order.

The candidate set is therefore unchanged.

Only ordering is modified.

## Evaluation Scope

Dataset:

northstar-v1

Chunk strategy:

evidence-block-v1

Corpus:

80 chunks

Split:

development

Exact retrieval-eligible development cases:

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

Exactly 10 development cases are evaluated.

No test case may appear in the Phase 7A artifact.

## Metrics

Reuse the existing retrieval metric definitions without modification:

- canonical reciprocal rank;
- Recall@1;
- Recall@3;
- Recall@5;
- Recall@10;
- nDCG@1;
- nDCG@3;
- nDCG@5;
- nDCG@10.

## Selection Policy

Baseline:

frozen hybrid:rrf-k60-v1

Candidate:

cross-encoder reranked hybrid top 20

Guardrail:

candidate mean Recall@10 must be greater than or equal to frozen RRF mean
Recall@10.

If the guardrail fails, retain frozen RRF regardless of ranking-quality
metrics.

If the guardrail passes, the primary selection metric is:

mean nDCG@10

If candidate nDCG@10 is greater, select the reranked candidate.

If candidate nDCG@10 is lower, retain frozen RRF.

If nDCG@10 is exactly equal, compare:

mean canonical reciprocal rank

If candidate canonical MRR is greater, select the reranked candidate.

Otherwise retain frozen RRF.

A complete tie retains frozen RRF.

There is no test-set selection rule in Phase 7A.

## No-Tuning Rule

Phase 7A evaluates exactly one reranker configuration.

Prohibited during this phase:
- model sweep;
- model revision sweep;
- candidate-cutoff sweep;
- reranker representation sweep;
- cross-encoder/RRF score interpolation;
- weighted score blending;
- query-type routing;
- threshold tuning;
- post-hoc candidate filtering;
- using the Phase 6B test queries to select parameters;
- removing unfavorable development queries.

A negative result must be retained.

## Reproducibility

The canonical Phase 7A artifact will later be rerun to /tmp using the same
frozen configuration.

Canonical and rerun artifacts will be compared byte-for-byte and by SHA-256.

## Claim Boundary

Phase 7A may support claims about one fixed cross-encoder reranking experiment
on 10 retrieval-eligible development queries from the synthetic Northstar
benchmark.

Phase 7A cannot establish:
- performance on an unseen test set;
- statistical significance;
- superiority on real enterprise data;
- optimal candidate cutoff;
- optimal cross-encoder model;
- production latency;
- production throughput;
- production scalability;
- generation quality;
- agent quality.
