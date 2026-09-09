# Heuristic Router Development Baseline Results

## Status

MEASURED / REPRODUCIBLE / VERIFIED

Phase 8A2 measured one preregistered deterministic heuristic router against
the frozen Northstar routing development split.

The locked holdout was not evaluated.

## Experimental Boundary

Frozen routing ground-truth commit:

e0755e81d3d1fa24577dbe4e0dd7a92c00247863

Frozen routing ground-truth tag:

phase-8a1-routing-ground-truth

Frozen routing benchmark SHA-256:

995f707a4cc6393f0e916f903cc57f9aec6fbabb3c43a00a78e318ca505b6912

Phase 8A2 preregistration commit:

331c7f7aa1a637411d5a842530c7f10008052a5b

Phase 8A2 preregistration tag:

phase-8a2-heuristic-router-preregistered

Phase 8A2 artifact count before measurement:

0

Worktree before canonical measurement:

clean

The heuristic rules, cue lists, fallback behavior, input representation,
metric definitions, and development split were committed and tagged before
the first routing-performance measurement.

## Benchmark Visibility

The heuristic was preregistered before any routing-performance measurement,
but it was not linguistically blind.

The routing benchmark, including development and locked-holdout question text,
had been constructed and human-reviewed before the heuristic was authored.

Before the Phase 8A2 preregistration boundary:

- no train routing performance was measured;
- no development routing performance was measured;
- no locked-holdout routing performance was measured;
- no aggregate routing metric was observed;
- no per-case frozen-benchmark router prediction was generated.

The result therefore measures a fixed interpretable ruleset designed with
knowledge of the benchmark's task language.

It must not be interpreted as evidence of perfect generalization.

## Router

Router version:

heuristic-router-v1

Question representation:

question-text-v1

Router input:

raw question text only

Canonical tool families:

- retrieval
- sql
- graph

Canonical route labels:

- retrieval
- sql
- graph
- retrieval+sql
- retrieval+graph
- sql+graph
- retrieval+sql+graph

Fallback route:

retrieval

## Rule Design

Retrieval intent is inferred from management-explanation and qualitative-risk
language.

SQL intent is inferred from structured quantitative requests involving
financial metrics, periods, comparisons, thresholds, arithmetic, or customer
counts.

A financial noun alone does not force SQL.

Graph intent is inferred from customer, supplier, and portfolio-company
relationship semantics.

The router emits every detected tool family and converts the resulting set to
the canonical route label.

No learned model is used in Phase 8A2.

## Evaluation Scope

Split:

development

Development cases:

28

Route labels:

7

Cases per route label:

4

Locked-holdout cases evaluated:

0

Artifact field:

locked_holdout_used = false

## Aggregate Metrics

Exact route-set accuracy:

1.0

Macro precision:

1.0

Macro recall:

1.0

Macro F1:

1.0

Hamming loss:

0.0

Required-tool omission rate:

0.0

Unnecessary-tool addition rate:

0.0

Under-routing case rate:

0.0

Over-routing case rate:

0.0

Development errors:

0 of 28

## Per-Tool Metrics

Retrieval:

- true positives: 16
- false positives: 0
- false negatives: 0
- precision: 1.0
- recall: 1.0
- F1: 1.0

SQL:

- true positives: 16
- false positives: 0
- false negatives: 0
- precision: 1.0
- recall: 1.0
- F1: 1.0

Graph:

- true positives: 16
- false positives: 0
- false negatives: 0
- precision: 1.0
- recall: 1.0
- F1: 1.0

## Route Distribution

Gold development distribution:

- graph: 4
- retrieval: 4
- retrieval+graph: 4
- retrieval+sql: 4
- retrieval+sql+graph: 4
- sql: 4
- sql+graph: 4

Predicted development distribution:

- graph: 4
- retrieval: 4
- retrieval+graph: 4
- retrieval+sql: 4
- retrieval+sql+graph: 4
- sql: 4
- sql+graph: 4

Gold and predicted route distributions were identical.

## Development Membership Verification

The canonical artifact was checked against the frozen routing benchmark.

Verification established:

- artifact routing IDs exactly equal the frozen development routing IDs;
- every artifact question matches the frozen development question;
- every gold route label matches the frozen benchmark;
- every gold tool set matches the frozen benchmark;
- exactly 28 development cases are present;
- zero locked-holdout routing IDs are present.

Result:

development_case_membership = VERIFIED

## Artifact

Canonical artifact:

artifacts/evaluation/phase8a2/heuristic-router-development.json

Canonical SHA-256:

222b731e602cfa6a5d38fd9c2c86d87fc8017caac56131b18ce4292628142c40

Canonical size:

22077 bytes

Canonical Phase 8A2 artifact count:

1

## Reproducibility

A second independent execution wrote:

/tmp/phase8a2-rerun.json

Rerun SHA-256:

222b731e602cfa6a5d38fd9c2c86d87fc8017caac56131b18ce4292628142c40

Rerun size:

22077 bytes

Comparison:

BYTE-IDENTICAL

The deterministic artifact excludes timestamps and wall-clock timing.

## Quality Gate

After canonical measurement and reproducibility verification:

- Ruff: passed
- formatting: passed
- tests: 222 passed
- dependency lock: valid
- frozen routing ground-truth commit unchanged
- Phase 8A2 preregistration commit unchanged
- canonical artifact count: 1
- no source or configuration changes occurred after measurement

## Interpretation

The fixed heuristic exactly recovered the development routing contract on all
28 cases.

This demonstrates that the frozen development benchmark's tool-selection
semantics can be represented by a compact deterministic ruleset.

It does not demonstrate that heuristic routing generalizes perfectly.

The result is especially limited by the fact that the benchmark language was
known during heuristic design, even though no benchmark predictions or
performance metrics were observed before preregistration.

The perfect development result also saturates this split: another model cannot
show higher development exact accuracy or macro F1 on these same 28 cases.

Therefore later learned-router evaluation must not be framed merely as an
attempt to outperform this development score.

## No Post-Measurement Retuning

After observing the development result, Phase 8A2 did not change:

- retrieval cues;
- SQL cues;
- graph cues;
- fallback behavior;
- rule ordering;
- question representation;
- benchmark cases;
- benchmark labels;
- metric definitions;
- development split.

The locked holdout was not evaluated.

## Implication for Later Routing Experiments

Phase 8B and Phase 8C require a stronger methodology than comparison on the
already-saturated development split.

Before measuring a pretrained or PEFT/LoRA classifier, the project must define
how learned models are selected and how generalization is evaluated without
using the locked holdout for iterative tuning.

Possible later methodology may include a new independently constructed
challenge set, controlled robustness transformations, or a separately frozen
validation protocol.

Those designs are not part of Phase 8A2 and must be preregistered separately.

## Claim Boundary

Phase 8A2 supports claims that:

- a deterministic multi-tool router was implemented;
- retrieval, SQL, and graph intent can be predicted jointly;
- routing rules were committed before performance measurement;
- the frozen routing benchmark fingerprint was checked at runtime;
- exactly 28 frozen development cases were evaluated;
- zero locked-holdout cases were evaluated;
- exact development route-set accuracy was 1.0;
- development macro F1 was 1.0;
- required-tool omission rate was 0.0;
- unnecessary-tool addition rate was 0.0;
- all three tool families achieved development precision, recall, and F1 of
  1.0;
- the canonical artifact reproduced byte-identically;
- the negative/positive result boundary was preserved without post-measurement
  tuning.

Phase 8A2 does not support claims that:

- heuristic routing generalizes perfectly;
- locked-holdout accuracy is 1.0;
- the heuristic was designed independently of benchmark language;
- the heuristic is superior to a learned classifier;
- a pretrained classifier has been evaluated;
- PEFT or LoRA has been evaluated;
- SQL execution has been implemented;
- graph execution has been implemented;
- end-to-end tool execution has been evaluated;
- agent quality has been measured;
- production latency has been measured;
- production throughput has been measured;
- statistical significance has been established;
- performance generalizes to real enterprise workloads.
