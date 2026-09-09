# Cross-Encoder Reranker Development Results

## Status

MEASURED / VERIFIED

Phase 7A evaluated one preregistered cross-encoder reranking configuration over
the frozen Phase 6A hybrid RRF candidate generator.

The reranker was not selected.

The preregistered Recall@10 guardrail failed, and the frozen RRF retriever
remains selected.

## Experimental Boundary

Preregistration commit:

7197b85b4a7f8f61043ec5dab8e0e263dd52a92b

Preregistration tag:

phase-7a-cross-encoder-reranker-preregistered

Phase 7A artifact count before measurement:

0

Worktree before measurement:

clean

The first real Northstar cross-encoder inference occurred only after this
boundary was committed and tagged.

## Scope

Dataset:

northstar-v1

Chunk strategy:

evidence-block-v1

Corpus:

80 chunks

Evaluation split:

development

Retrieval-eligible development cases:

10

Exact query IDs:

- Q-0001
- Q-0002
- Q-0004
- Q-0006
- Q-0008
- Q-0009
- Q-0017
- Q-0019
- Q-0020
- Q-0021

The Phase 6B test split was not used.

The artifact records:

test_split_used = false

## Frozen Candidate Generator

Selected Phase 6A candidate generator:

hybrid:rrf-k60-v1

Frozen Phase 6A source artifact:

artifacts/evaluation/phase6a/rrf-k60-development.json

Frozen Phase 6A SHA-256:

c0f850e21d25f993f26c58b44d0ace057fbcd23380dce85039f2b4d6c2593c21

Lexical configuration:

- BM25 version: bm25-v1
- tokenizer: lexical-tokenizer-v1
- representation: document-title-text-v1
- k1: 1.5
- b: 0.75
- zero-overlap chunks excluded

Dense configuration:

- version: dense-e5-small-v2-v1
- representation: e5-document-title-text-v1
- model: intfloat/e5-small-v2
- revision: ffb93f3bd4047442299a41ebb6fa998a38507c52
- normalized embeddings
- inner-product similarity
- CPU execution
- batch size: 16

Fusion configuration:

- version: rrf-k60-v1
- k: 60
- equal lexical and dense rank contributions
- missing source-rank contribution: 0
- deterministic chunk_id tie-break

## Phase 6A Regeneration Verification

Before interpreting reranker metrics, Phase 7A regenerated the frozen RRF
candidate ranking from the frozen BM25 and E5 components.

Verification result:

phase6a_regeneration = true

The verifier checked:

- exact development query identities;
- exact case count;
- aggregate baseline metrics;
- per-case baseline metrics;
- frozen top-10 chunk identities;
- frozen top-10 evidence identities;
- frozen top-10 ordering;
- RRF scores.

The reranker comparison therefore uses a verified reconstruction of the frozen
Phase 6A baseline.

## Cross-Encoder Configuration

Reranker version:

cross-encoder-ms-marco-minilm-l6-v2-v1

Model:

cross-encoder/ms-marco-MiniLM-L6-v2

Immutable model revision:

233902d25c440f23af6f7d6e94d2946bac0bee0a

Representation:

cross-encoder-document-title-text-v1

Input pair:

query paired with document title plus evidence text

Backend:

torch

Device:

cpu

Batch size:

16

Candidate cutoff:

20

Cross-encoder output:

raw single-label score

Activation:

identity

Softmax:

false

No RRF, BM25, or dense score was numerically blended with the cross-encoder
score.

## Ranking Policy

Only frozen RRF ranks 1 through 20 were cross-encoder scored.

Those 20 candidates were ordered by:

1. cross-encoder score descending;
2. original RRF rank ascending;
3. chunk_id ascending.

Frozen RRF ranks 21 through 80 were appended unchanged.

The candidate set was preserved for every query.

The RRF tail order was preserved for every query.

## Preregistered Selection Policy

Baseline:

hybrid:rrf-k60-v1

Candidate:

cross-encoder reranked hybrid top 20

Guardrail:

candidate mean Recall@10 must be greater than or equal to frozen RRF mean
Recall@10.

Primary metric after guardrail:

mean nDCG@10

Secondary metric on exact nDCG@10 tie:

mean canonical reciprocal rank

Complete tie:

retain frozen RRF

No test-set selection rule was defined.

## Aggregate Results

Frozen RRF development metrics:

- canonical MRR: 0.8166666666666667
- nDCG@10: 0.8312065766811914
- Recall@10: 0.95

Cross-encoder reranked development metrics:

- canonical MRR: 0.7038690476190477
- nDCG@10: 0.709558983360721
- Recall@10: 0.90

Cross-encoder minus frozen RRF:

Canonical MRR:
- absolute delta: -0.11279761904761898
- relative delta: -0.1381195335276967
- approximately -13.81 percent relative

nDCG@10:
- absolute delta: -0.12164759332047037
- relative delta: -0.14635061455622747
- approximately -14.64 percent relative

Recall@10:
- absolute delta: -0.04999999999999993
- relative delta: -0.052631578947368356
- approximately -5.26 percent relative

## Selection Outcome

Guardrail result:

FAILED

Selection reason:

recall_at_10_guardrail_failed

Selected system:

hybrid:rrf-k60-v1

The candidate would not have been selected even without the Recall@10
guardrail because aggregate nDCG@10 also declined.

## Per-Query Outcomes

Q-0001 lexical:
- RRF nDCG@10: 0.9680147827042069
- reranked nDCG@10: 1.0
- Recall@10 unchanged at 1.0
- small improvement

Q-0002 lexical:
- nDCG@10 unchanged at 1.0
- canonical RR unchanged at 1.0
- Recall@10 unchanged at 1.0
- tie

Q-0004 semantic:
- nDCG@10 unchanged at 1.0
- canonical RR unchanged at 1.0
- Recall@10 unchanged at 1.0
- tie

Q-0006 semantic:
- RRF nDCG@10: 0.8339912323981488
- reranked nDCG@10: 0.6653152460429406
- canonical RR unchanged at 0.5
- Recall@10 unchanged at 1.0
- ranking regression

Q-0008 hybrid:
- nDCG@10 unchanged at 0.8772153153380492
- canonical RR unchanged at 1.0
- Recall@10 unchanged at 1.0
- tie

Q-0009 hybrid:
- RRF nDCG@10: 0.6131471927654584
- reranked nDCG@10: 0.8315546295836226
- canonical RR unchanged at 1.0
- RRF Recall@10: 0.5
- reranked Recall@10: 1.0
- meaningful improvement

Q-0017 multi_source:
- RRF nDCG@10: 0.3956467236022119
- reranked nDCG@10: 0.8175295903539446
- RRF canonical RR: 0.16666666666666666
- reranked canonical RR: 1.0
- Recall@10 unchanged at 1.0
- substantial ordering improvement

Q-0019 multi_source:
- RRF nDCG@10: 0.6240505200038379
- reranked nDCG@10: 0.57064171895532
- RRF canonical RR: 0.5
- reranked canonical RR: 0.3333333333333333
- Recall@10 unchanged at 1.0
- regression

Q-0020 mixed_tool:
- RRF nDCG@10: 1.0
- reranked nDCG@10: 0.33333333333333337
- RRF canonical RR: 1.0
- reranked canonical RR: 0.14285714285714285
- Recall@10 unchanged at 1.0
- major ranking regression

Q-0021 mixed_tool:
- RRF nDCG@10: 1.0
- reranked nDCG@10: 0.0
- RRF canonical RR: 1.0
- reranked canonical RR: 0.0625
- RRF Recall@10: 1.0
- reranked Recall@10: 0.0
- guardrail-breaking regression

## Movement Diagnostics

Q-0009:

EVID-CORE-PC005-QMR-SIGNAL
- relevance grade: 3
- RRF rank: 11
- reranked rank: 6
- cross-encoder score: -2.960455894470215

EVID-CORE-PC005-RISK-CONTEXT
- relevance grade: 3
- RRF rank: 1
- reranked rank: 1
- cross-encoder score: 4.930454254150391

The reranker moved a second canonical evidence item into the top 10 and raised
Recall@10 from 0.5 to 1.0.

Q-0017:

EVID-CORE-PC004-QMR-FINANCIAL
- relevance grade: 3
- RRF rank: 6
- reranked rank: 1
- cross-encoder score: 4.316257953643799

EVID-CORE-PC004-RISK-PRIMARY
- relevance grade: 3
- RRF rank: 10
- reranked rank: 7
- cross-encoder score: 0.8855957984924316

This corrected an important RRF ordering weakness and moved the canonical
reciprocal rank from 1/6 to 1.

Q-0019:

EVID-CORE-PC008-QMR-OPERATING
- relevance grade: 3
- RRF rank: 2
- reranked rank: 4
- cross-encoder score: 0.8380368947982788

EVID-CORE-PC008-RISK-PRIMARY
- relevance grade: 3
- RRF rank: 5
- reranked rank: 3
- cross-encoder score: 2.0202107429504395

One canonical item improved while another moved lower, producing a small
aggregate query regression.

Q-0020:

EVID-CORE-PC005-QMR-SIGNAL
- relevance grade: 3
- RRF rank: 1
- reranked rank: 7
- cross-encoder score: 0.8621958494186401

The reranker substantially demoted the canonical evidence despite the frozen
RRF baseline ranking it first.

Q-0021:

EVID-CORE-PC004-RISK-PRIMARY
- relevance grade: 3
- RRF rank: 1
- reranked rank: 16
- cross-encoder score: -1.6996846199035645

This demotion moved the only relevant evidence outside the evaluation top 10,
causing Recall@10 to fall from 1.0 to 0.0.

## Interpretation

The cross-encoder did not fail uniformly.

It improved several ordinary lexical, hybrid, and multi-source cases and
produced a particularly strong correction on Q-0017.

However, the fixed generic passage-ranking model behaved poorly on the
mixed-tool cases, especially Q-0021.

This suggests that generic text relevance and the benchmark's task-specific
notion of canonical evidence are not always aligned.

This is a hypothesis motivated by the measured result, not a proven causal
explanation.

No model, cutoff, representation, weighting, routing rule, or threshold was
changed after observing this result.

## No Post-Measurement Retuning

Phase 7A did not evaluate:

- another cross-encoder model;
- another model revision;
- another candidate cutoff;
- top-10-only reranking;
- top-30 reranking;
- top-50 reranking;
- score blending;
- RRF plus cross-encoder interpolation;
- query-type routing;
- mixed-tool bypass;
- task-aware routing;
- threshold tuning;
- fine-tuning;
- test-set confirmation.

The negative candidate result is retained unchanged.

Any such experiment must be defined as a new phase.

## Reproducibility

Canonical artifact:

artifacts/evaluation/phase7a/cross-encoder-reranker-development.json

Canonical SHA-256:

101e826b06efacf5f01dad237ccc64db13328308645552281b17cf9494b37ce4

Canonical size:

580704 bytes

Independent repeat execution:

/tmp/phase7a-rerun.json

Rerun SHA-256:

101e826b06efacf5f01dad237ccc64db13328308645552281b17cf9494b37ce4

Rerun size:

580704 bytes

Comparison:

BYTE-IDENTICAL

## Final Quality Gate

After measurement and reproducibility verification:

- Ruff: passed
- formatting: passed
- tests: 195 passed
- dependency lock: valid
- Alembic current: 8a0f69a3baf1 (head)
- Alembic drift: none
- Phase 7A canonical artifacts: 1

Preregistration commit remained:

7197b85b4a7f8f61043ec5dab8e0e263dd52a92b

Frozen Phase 6A SHA-256 remained:

c0f850e21d25f993f26c58b44d0ace057fbcd23380dce85039f2b4d6c2593c21

## Scientific Conclusion

One fixed pretrained MS MARCO cross-encoder reranker did not improve the
Northstar development retrieval stack under the preregistered selection
policy.

It reduced aggregate nDCG@10, canonical MRR, and Recall@10 relative to frozen
RRF.

The result nevertheless showed query-level complementarity: some ordering
failures were corrected while others were introduced.

The rejected reranker will not be tested on the already-inspected Phase 6B
test split.

## Claim Boundary

Phase 7A supports claims that:

- a pinned pretrained cross-encoder was implemented and evaluated;
- the model revision was frozen before measurement;
- the candidate cutoff was frozen at 20 before measurement;
- Phase 6A RRF regeneration was verified before comparison;
- exactly 10 development retrieval cases were evaluated;
- the candidate set and ranks 21 through 80 were preserved;
- the reranker improved some cases substantially;
- the reranker reduced aggregate development nDCG@10 by about 14.64 percent
  relative to frozen RRF;
- the reranker reduced canonical MRR by about 13.81 percent relative;
- the reranker reduced Recall@10 from 0.95 to 0.90;
- the preregistered guardrail rejected the candidate;
- the negative result was retained without retuning;
- the canonical artifact reproduced byte-identically.

Phase 7A does not support claims that:

- cross-encoders are generally inferior to RRF;
- this model is generally unsuitable for enterprise retrieval;
- mixed-tool queries always require routing;
- another reranker would perform better;
- another candidate cutoff would perform better;
- task-aware fine-tuning would improve the result;
- the result is statistically significant;
- the result generalizes to real enterprise data;
- performance on an unseen test split improved;
- production latency has been measured;
- production throughput has been measured;
- production scalability has been established;
- generation quality has been measured;
- agent quality has been measured.
