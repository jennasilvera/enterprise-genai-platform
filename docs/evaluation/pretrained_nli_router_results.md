# Pretrained Zero-Shot NLI Router Baseline Results

## Status

MEASURED / REPRODUCIBLE / VERIFIED

Phase 8B1 evaluated one preregistered pretrained zero-shot NLI router against
the frozen Northstar routing development split.

The original locked holdout was not evaluated.

The routing generalization challenge was not evaluated.

## Experimental Boundary

Original routing ground-truth commit:

e0755e81d3d1fa24577dbe4e0dd7a92c00247863

Original routing ground-truth tag:

phase-8a1-routing-ground-truth

Original routing SHA-256:

995f707a4cc6393f0e916f903cc57f9aec6fbabb3c43a00a78e318ca505b6912

Routing generalization challenge commit:

bea37c093783bcbfb9f66e934f449e56fafa2e06

Routing generalization challenge SHA-256:

e1fc84e80e5cd27cc311da4392e3c9d46375777a27c81bdc5e35e37b5b131867

Phase 8B1 preregistration commit:

f86d858f10f23ddebd97544290a21d4139ff1a7f

Phase 8B1 preregistration tag:

phase-8b1-pretrained-nli-router-preregistered

Phase 8B1 artifact count before first Northstar measurement:

0

The model identity, immutable model revision, route hypotheses, route order,
scoring function, decoding rule, tie-breaking rule, question representation,
maximum length, and configuration fingerprint were committed and tagged before
the first Northstar routing prediction.

## Model

Model:

cross-encoder/nli-deberta-v3-xsmall

Immutable Hugging Face revision:

a150876415327c80daeff35ca6f68f5ed8cf5c24

Model class:

DebertaV2ForSequenceClassification

Tokenizer:

DebertaV2Tokenizer

Parameters:

70831107

Training performed in Phase 8B1:

false

Device:

CPU

CUDA:

false

## Frozen Router Configuration

Router:

pretrained-nli-router-v1

Configuration SHA-256:

72d8ce61cdce386bb189cb70698d0f899bf94fa63b8f42796f1a19eaaca3e924

Question representation:

question-text-v1

Scoring:

nli-entailment-probability-v1

Decoding:

seven-route-entailment-argmax-v1

Tie breaking:

route-order-first-v1

No threshold, heuristic score, contradiction score, neutral score, or
calibration term is used in route selection.

## Evaluation Scope

Split:

development

Cases:

28

Gold route classes:

7

Cases per gold route:

4

Original locked-holdout cases evaluated:

0

Generalization-challenge cases evaluated:

0

## Aggregate Development Metrics

Exact route-set accuracy:

0.14285714285714285

Correct cases:

4 of 28

Macro precision:

0.5714285714285714

Macro recall:

1.0

Macro F1:

0.7272727272727272

Hamming loss:

0.42857142857142855

Required-tool omission rate:

0.0

Unnecessary-tool addition rate:

1.0

Under-routing case rate:

0.0

Over-routing case rate:

0.8571428571428571

## Per-Tool Development Metrics

Retrieval:

- true positives: 16
- false positives: 12
- false negatives: 0
- precision: 0.5714285714285714
- recall: 1.0
- F1: 0.7272727272727273

SQL:

- true positives: 16
- false positives: 12
- false negatives: 0
- precision: 0.5714285714285714
- recall: 1.0
- F1: 0.7272727272727273

Graph:

- true positives: 16
- false positives: 12
- false negatives: 0
- precision: 0.5714285714285714
- recall: 1.0
- F1: 0.7272727272727273

## Failure Topology

The router predicted:

retrieval+sql+graph

for all 28 development cases.

Gold-to-predicted confusion:

- graph -> retrieval+sql+graph: 4
- retrieval -> retrieval+sql+graph: 4
- retrieval+graph -> retrieval+sql+graph: 4
- retrieval+sql -> retrieval+sql+graph: 4
- retrieval+sql+graph -> retrieval+sql+graph: 4
- sql -> retrieval+sql+graph: 4
- sql+graph -> retrieval+sql+graph: 4

Therefore the only correct cases were the four cases whose gold route was
already retrieval+sql+graph.

The observed failure mode is:

maximal-route collapse

This is systematic over-routing rather than random classification error.

## Mean Entailment Probability by Candidate Route

graph:

0.0020757199589362635

retrieval:

0.004818102910316416

retrieval+graph:

0.0019985864928457886

retrieval+sql:

0.0015204310028431272

retrieval+sql+graph:

0.05524828547744879

sql:

0.003398961903128241

sql+graph:

0.0015833111247047782

The maximal route had the highest mean entailment probability by a large
margin.

## Winning-Score Margin

Mean winner margin:

0.04985775820594946

Median winner margin:

0.016908399062231183

Minimum winner margin:

0.00007860944606363773

Maximum winner margin:

0.4572319108992815

The collapse is therefore systematic, but the confidence separation is not
uniform across cases.

## Diagnostic Interpretation

The six non-maximal route hypotheses contain explicit exclusion clauses such
as "does not require", whereas the maximal retrieval+sql+graph hypothesis is
fully affirmative.

A plausible explanation is that the generic NLI model treats the fully
affirmative maximal-capability hypothesis as semantically safer or less
contradictory than hypotheses containing explicit negative capability
statements.

This is a post-measurement diagnostic hypothesis, not a demonstrated causal
explanation.

It was not used to alter the Phase 8B1 router.

The low entailment probabilities on many cases also indicate that the
pretrained NLI model does not naturally map the routing formulation onto
ordinary textual entailment with high confidence.

## Reproducibility

Canonical artifact:

artifacts/evaluation/phase8b1/pretrained-nli-router-development.json

Canonical SHA-256:

e4ec5eb88945e259a9dba923a15c997743a4dcf4971828bcd383fd44a304e5ea

Canonical size:

89850 bytes

Independent rerun:

/tmp/phase8b1-rerun.json

Rerun SHA-256:

e4ec5eb88945e259a9dba923a15c997743a4dcf4971828bcd383fd44a304e5ea

Rerun size:

89850 bytes

Comparison:

BYTE-IDENTICAL

## Membership Verification

The canonical artifact was checked against the frozen routing sources.

Verified:

- exactly 28 frozen development routing IDs are present;
- artifact questions exactly match frozen development questions;
- gold route labels exactly match frozen labels;
- gold tool sets exactly match frozen tool sets;
- zero original locked-holdout IDs are present;
- zero routing-generalization-challenge IDs are present.

Result:

development_membership = VERIFIED

## Quality Gate

After measurement:

- Ruff: passed
- formatting: passed
- full repository tests: 256 passed
- dependency lock: valid
- Phase 8B1 preregistration unchanged
- routing challenge ground truth unchanged
- Phase 8B1 artifact count: 1
- challenge artifact count: 0

## No Post-Measurement Retuning

After observing the result, Phase 8B1 did not change:

- model ID;
- model revision;
- route hypotheses;
- route order;
- scoring function;
- input representation;
- NLI label mapping;
- maximum sequence length;
- decoding rule;
- tie-breaking rule;
- development benchmark;
- benchmark labels;
- routing metrics.

The negative result is retained unchanged.

## Comparison With Phase 8A2

The deterministic heuristic achieved development exact route-set accuracy of
1.0.

The pretrained zero-shot NLI router achieved development exact route-set
accuracy of approximately 0.1429.

This comparison is descriptive only.

The heuristic was designed with knowledge of benchmark language, while the NLI
router uses a generic pretrained semantic model and fixed zero-shot route
hypotheses.

The experiment does not establish general superiority of deterministic rules
over learned routing models.

## Scientific Value

Phase 8B1 demonstrates why router evaluation must measure both missing and
unnecessary tools.

Required-tool omission alone would make this router appear safe:

required-tool omission rate = 0.0

However, the router invoked unnecessary tools on every case where the gold
route was not already maximal:

unnecessary-tool addition rate = 1.0

over-routing case rate = 0.8571428571428571

A production agent using this router could therefore waste tool calls, increase
latency and cost, broaden data access unnecessarily, and increase the surface
area for downstream failure despite never omitting a required capability on
this benchmark.

## Implication for Phase 8C

Phase 8C will test whether supervised PEFT/LoRA adaptation can learn the
seven-route decision boundary without collapsing toward maximal tool use.

The Phase 8B1 result remains the frozen pretrained baseline.

The routing generalization challenge remains performance-locked.

## Claim Boundary

Phase 8B1 supports claims that:

- a pretrained zero-shot semantic router was implemented;
- an immutable Hugging Face model revision was pinned;
- seven route hypotheses and deterministic NLI decoding were preregistered;
- router configuration was fingerprinted and runtime-validated;
- 28 frozen development cases were evaluated;
- the baseline achieved 0.142857 exact route-set accuracy;
- macro F1 was approximately 0.727273;
- required-tool omission rate was 0.0;
- unnecessary-tool addition rate was 1.0;
- the router exhibited maximal-route collapse;
- the negative result was retained without post-measurement retuning;
- the evaluation artifact reproduced byte-identically;
- original locked-holdout and challenge performance remain unmeasured.

Phase 8B1 does not support claims that:

- the NLI router generalizes to unseen enterprise workloads;
- challenge performance is known;
- original locked-holdout performance is known;
- LoRA or PEFT improves routing;
- the heuristic is universally superior;
- SQL execution is implemented;
- graph execution is implemented;
- end-to-end agent quality has been measured;
- production latency or throughput has been measured;
- statistical significance has been established.
