# Routing Generalization Challenge Protocol

## Status

GROUND-TRUTH CONSTRUCTION / PRE-MODEL-EVALUATION

No router has been evaluated on the routing generalization challenge when this
protocol is created.

## Phase

Phase 8B0

## Motivation

The Phase 8A2 deterministic heuristic router achieved perfect performance on
the 28-case routing development split.

That development split is therefore saturated and cannot demonstrate whether a
later pretrained or PEFT/LoRA router generalizes better.

A separate routing generalization challenge is frozen before pretrained-model
or LoRA development.

## Relationship to Phase 8A

Phase 8A1 froze:

northstar-routing-v1

Phase 8A2 measured the deterministic heuristic only on the 28 development
cases.

The Phase 8A2 heuristic was not evaluated on this challenge before challenge
construction.

## Challenge Version

northstar-routing-challenge-v1

Dataset version:

northstar-v1

## Frozen Challenge Fingerprint

Canonical deterministic SHA-256:

e1fc84e80e5cd27cc311da4392e3c9d46375777a27c81bdc5e35e37b5b131867

The fingerprint is computed from the canonical JSON serialization of the full
RoutingSet.

The test suite asserts this exact fingerprint after the Phase 8B0
ground-truth freeze.

Any semantic change after this freeze requires a new challenge benchmark
version rather than silently modifying northstar-routing-challenge-v1.

## Challenge Scope

Total cases:

84

Canonical route labels:

7

Cases per route label:

12

Template families:

21

Families per route:

3

Cases per family:

4

Split label:

locked_holdout

The split label means model performance is reserved from iterative tuning.

It does not mean the benchmark text is hidden from the developer.

## Entity Separation

The original routing benchmark was instantiated using four primary entity
anchors:

- PC-001 Meridian Health Systems
- PC-002 Alder Manufacturing
- PC-005 Vantage Retail Analytics
- PC-008 NovaBio Instruments

The challenge uses the complementary four portfolio-company anchors:

- PC-003 BluePeak Logistics
- PC-004 HelioGrid Energy
- PC-006 Orbis Cybersecurity
- PC-007 Cedar Financial Technologies

This adds entity-name separation in addition to linguistic-family separation.

## Challenge Design

Each canonical route has three challenge families emphasizing:

1. synonym substitution;
2. linguistic reframing or clause reordering;
3. more implicit capability intent.

The challenge avoids direct implementation instructions such as:

- use retrieval;
- use SQL;
- use graph;
- relationship network;
- relationship path;
- traverse from;
- vector search;
- database query.

Natural business language remains visible.

Examples include:

- sales as a contextual synonym for revenue;
- buyers for customers;
- vendors for suppliers;
- rationale, record, cause, and concern for qualitative evidence requests.

## Tool Semantics

Retrieval:

qualitative evidence from portfolio documents.

SQL:

deterministic structured filtering, comparison, aggregation, or arithmetic.

Graph:

relationship traversal across enterprise entities.

Multi-tool labels require every capability necessary to satisfy the full
question.

## Challenge Purpose

The challenge tests whether a frozen router maps paraphrased business intent
to the correct capability set rather than merely matching the exact linguistic
families used in the original routing benchmark.

## Performance Lock

No router performance may be measured on northstar-routing-challenge-v1 during
challenge construction.

In particular, do not evaluate:

- heuristic-router-v1;
- a pretrained classifier;
- a PEFT/LoRA classifier;
- any later learned router.

## Learned-Model Development

The original routing benchmark remains the development environment for learned
routers.

Its 112 train cases may be used for fitting where appropriate.

Its 28 development cases may be used for model selection according to a
separately preregistered Phase 8B/8C protocol.

The routing generalization challenge may not be used for:

- feature selection;
- cue design;
- model selection;
- hyperparameter selection;
- checkpoint selection;
- threshold selection;
- prompt selection;
- label-description selection;
- early stopping.

## Final Comparison

After the relevant routers are independently frozen, the project may run one
planned comparison on northstar-routing-challenge-v1.

The comparison should include, at minimum:

- frozen deterministic heuristic;
- frozen pretrained baseline;
- frozen PEFT/LoRA router.

The challenge comparison protocol and model identities must be committed before
the first challenge performance is observed.

## Existing Locked Holdout

The original northstar-routing-v1 locked_holdout remains unmeasured by the
heuristic.

It is not consumed by Phase 8B0.

Its text was human-reviewed during benchmark construction, so it must not be
described as unseen text.

## Intended Metrics

Primary:

- exact route-set accuracy
- macro F1

Critical:

- required-tool omission rate

Secondary:

- macro precision
- macro recall
- Hamming loss
- unnecessary-tool addition rate
- under-routing case rate
- over-routing case rate
- per-tool precision, recall, and F1

## Freeze Rule

northstar-routing-challenge-v1 must be:

- implemented;
- semantically reviewed;
- tested;
- fingerprinted;
- committed;
- tagged;

before any pretrained-router or LoRA experiment is measured.

After the freeze, changing challenge language or labels requires a new
challenge benchmark version.

## Claim Boundary

Phase 8B0 establishes a routing robustness evaluation protocol and challenge
ground truth only.

It establishes no router performance.

It does not establish:

- heuristic challenge performance;
- pretrained-router performance;
- PEFT/LoRA performance;
- locked-holdout performance;
- statistical significance;
- real-enterprise generalization;
- SQL execution quality;
- graph execution quality;
- end-to-end agent quality.
