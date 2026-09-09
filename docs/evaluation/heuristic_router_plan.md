# Heuristic Router Development Baseline Plan

## Status

PRE-MEASUREMENT IMPLEMENTATION

No Phase 8 routing baseline has been measured when this plan is authored.

## Phase

Phase 8A2

## Purpose

Establish a deterministic, interpretable routing baseline before evaluating
pretrained or fine-tuned routing classifiers.

## Frozen Ground Truth

Routing benchmark:

northstar-routing-v1

Ground-truth commit:

e0755e81d3d1fa24577dbe4e0dd7a92c00247863

Ground-truth tag:

phase-8a1-routing-ground-truth

Canonical routing SHA-256:

995f707a4cc6393f0e916f903cc57f9aec6fbabb3c43a00a78e318ca505b6912

The benchmark may not be changed in response to heuristic-router performance.

## Input Representation

The router receives only raw question text.

No entity IDs, route labels, template-family identifiers, difficulty labels,
split labels, or ground-truth metadata are router inputs.

Representation version:

question-text-v1

## Router

Router version:

heuristic-router-v1

The router predicts the tool set:

- retrieval
- sql
- graph

and deterministically converts the predicted set to the canonical route label.

## Retrieval Rule

Retrieval intent is inferred from management-explanation and qualitative-risk
language.

The rule uses fixed semantic cues around:

- explanation
- concern
- worried
- highlighted
- characterization
- impact
- why

A descriptive "circumstances are described" formulation is also recognized.

## SQL Rule

SQL is not triggered by a financial noun alone.

The rule requires structured quantitative intent, using:

- a financial metric plus a period or quantitative operation; or
- an explicit customer-count request.

This prevents a phrase such as "revenue concentration" in a qualitative risk
title from automatically forcing SQL.

## Graph Rule

Graph intent is inferred from relationship questions involving customer,
supplier, and portfolio-company traversal semantics.

No graph database implementation exists yet in Phase 8A2. This phase evaluates
routing classification only.

## Fallback

If no rule matches, the fixed fallback route is:

retrieval

This rule is frozen before development measurement.

## Benchmark Visibility

The heuristic is preregistered before any routing-performance measurement.

However, it is not a linguistically blind baseline.

The routing benchmark, including development and locked-holdout question text,
was constructed and human-reviewed before the heuristic was authored.

Before this preregistration boundary:

- no train routing performance was measured;
- no development routing performance was measured;
- no locked-holdout routing performance was measured;
- no aggregate routing metric was observed;
- no per-case router prediction was generated from the frozen benchmark.

The heuristic therefore measures the performance of a fixed, interpretable
rule system designed with knowledge of the benchmark's task language, not a
rule system designed independently of the benchmark domain.

Later learned-model comparisons must preserve this distinction.

## Canonical Development Artifact

Intended canonical artifact:

artifacts/evaluation/phase8a2/heuristic-router-development.json

The deterministic artifact excludes wall-clock timing and timestamps.

## Runtime Integrity Gate

Before routing any canonical development question, the evaluation CLI must
rebuild northstar-routing-v1 and verify its SHA-256 against:

995f707a4cc6393f0e916f903cc57f9aec6fbabb3c43a00a78e318ca505b6912

A mismatch must stop execution before routing predictions are produced.

## Evaluation Split

Canonical Phase 8A2 measurement uses only:

development

Development cases:

28

Locked-holdout performance will not be measured in Phase 8A2.

The locked-holdout questions were human-reviewed during Phase 8A1 benchmark
construction, so they are not described as unseen text. Their router/model
performance remains locked.

## Metrics

Primary:

- exact route-set accuracy
- macro F1 over retrieval, sql, and graph

Critical safety metric:

- required-tool omission rate

Required-tool omission rate is:

missing required tool incidences divided by all required tool incidences.

Secondary:

- macro precision
- macro recall
- Hamming loss
- unnecessary-tool addition rate
- under-routing case rate
- over-routing case rate
- per-tool precision, recall, and F1

## No-Tuning Rule

The heuristic rules, cues, fallback, representation, benchmark fingerprint,
development split, and metric definitions are committed and tagged before any
development-set routing performance is measured.

After development measurement:

- no cue may be added;
- no cue may be removed;
- no rule ordering may change;
- no fallback may change;
- no threshold may be introduced;
- no benchmark case or label may change.

Any follow-on heuristic requires a new experiment version.

## Holdout Rule

Phase 8A2 does not evaluate locked_holdout.

The locked holdout remains reserved for a later comparison after routing-model
selection methodology is defined.

## Claim Boundary

Phase 8A2 can establish deterministic heuristic routing performance on the
28-case development split.

It cannot establish:

- locked-holdout performance;
- learned-classifier performance;
- PEFT or LoRA performance;
- SQL execution correctness;
- graph execution correctness;
- retrieval execution quality;
- end-to-end answer quality;
- agent quality;
- production latency;
- production throughput;
- statistical significance;
- real-enterprise generalization.
