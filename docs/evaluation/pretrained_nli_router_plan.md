# Pretrained Zero-Shot NLI Router Baseline Plan

## Status

PRE-MEASUREMENT IMPLEMENTATION

No Northstar routing case has been scored by the pretrained NLI router when
this plan is authored.

## Phase

Phase 8B1

## Purpose

Establish a frozen pretrained semantic routing baseline before PEFT/LoRA
training.

## Model

Model:

cross-encoder/nli-deberta-v3-xsmall

Immutable Hugging Face revision:

a150876415327c80daeff35ca6f68f5ed8cf5c24

Model class observed during preflight:

DebertaV2ForSequenceClassification

Tokenizer class:

DebertaV2Tokenizer

Parameters observed during preflight:

70831107

Maximum sequence length:

512

## Runtime

PyTorch:

2.13.0+cpu

Device:

CPU

CUDA available:

false

PyTorch intra-op threads:

6

PyTorch inter-op threads:

6

The model is used under inference-only torch.no_grad() execution.

No model parameter is updated in Phase 8B1.

## Preflight Label Mapping

Observed immutable model label mapping:

- contradiction: 0
- entailment: 1
- neutral: 2

The implementation validates this mapping at runtime and fails closed if the
mapping differs.

## Model Selection

Exactly one pretrained model is evaluated.

There is:

- no model sweep;
- no checkpoint sweep;
- no prompt sweep after Northstar measurement;
- no threshold sweep;
- no heuristic fusion;
- no supervised training;
- no PEFT/LoRA training.

The model was selected before any Northstar prediction was generated.

## Input Representation

The model receives raw normalized question text as the NLI premise.

Representation:

question-text-v1

No route label, split label, template-family identifier, entity metadata,
difficulty metadata, or ground-truth tool annotation is included in the
premise.

## Classification Formulation

The router performs direct seven-way route classification through NLI.

Each user question is paired with exactly seven frozen hypotheses, one for each
canonical route:

- retrieval
- sql
- graph
- retrieval+sql
- retrieval+graph
- sql+graph
- retrieval+sql+graph

For each pair, the router computes the model's softmax probability assigned to
the entailment label.

The route with the highest entailment probability is selected.

## Frozen Route Hypotheses

### retrieval

Answering the user request requires qualitative evidence from unstructured
documents, but does not require structured numerical computation or traversal
of relationships between entities.

### sql

Answering the user request requires structured numerical data, filtering,
comparison, aggregation, or arithmetic, but does not require qualitative
document evidence or traversal of relationships between entities.

### graph

Answering the user request requires following relationships between entities
such as companies, customers, or suppliers, but does not require qualitative
document evidence or structured numerical computation.

### retrieval+sql

Answering the user request requires both qualitative evidence from unstructured
documents and structured numerical computation, but does not require traversal
of relationships between entities.

### retrieval+graph

Answering the user request requires both qualitative evidence from unstructured
documents and traversal of relationships between entities, but does not require
structured numerical computation.

### sql+graph

Answering the user request requires both structured numerical computation and
traversal of relationships between entities, but does not require qualitative
evidence from unstructured documents.

### retrieval+sql+graph

Answering the user request requires qualitative evidence from unstructured
documents, structured numerical computation, and traversal of relationships
between entities.

## Score

Score:

softmax probability of the entailment label for each premise/hypothesis pair.

Scoring version:

nli-entailment-probability-v1

No contradiction score, neutral score, margin, calibration transformation, or
heuristic score is blended into route selection.

## Tie Breaking

Canonical route order:

1. retrieval
2. sql
3. graph
4. retrieval+sql
5. retrieval+graph
6. sql+graph
7. retrieval+sql+graph

An exact numerical tie is resolved by retaining the earliest route in this
order.

The order is fixed before Northstar measurement.

## Frozen Router Configuration

Canonical router-configuration SHA-256:

72d8ce61cdce386bb189cb70698d0f899bf94fa63b8f42796f1a19eaaca3e924

This fingerprint covers:

- router version;
- model ID;
- immutable model revision;
- question representation;
- scoring version;
- decoding version;
- tie-breaking version;
- maximum length;
- expected NLI label mapping;
- canonical route order;
- all seven route hypotheses.

The runtime fails closed if this configuration fingerprint changes.

## Benchmark Visibility

The zero-shot route hypotheses were authored after the Northstar routing
ontology and benchmark language had been constructed and human-reviewed.

However, before the Phase 8B1 preregistration boundary:

- no pretrained-router Northstar prediction has been generated;
- no train routing performance has been observed;
- no development routing performance has been observed;
- no original locked-holdout routing performance has been observed;
- no routing-challenge performance has been observed.

Phase 8B1 is therefore zero-shot with respect to routing-model training, but
not linguistically blind to the benchmark domain.

## Development Evaluation

The first canonical Phase 8B1 measurement will use only the 28-case
development split of:

northstar-routing-v1

Frozen routing SHA-256:

995f707a4cc6393f0e916f903cc57f9aec6fbabb3c43a00a78e318ca505b6912

The development result is a baseline measurement, not model selection from a
set of alternatives.

## Original Locked Holdout

The original northstar-routing-v1 locked_holdout is not evaluated in Phase
8B1.

## Generalization Challenge

Challenge:

northstar-routing-challenge-v1

Challenge commit:

bea37c093783bcbfb9f66e934f449e56fafa2e06

Challenge SHA-256:

e1fc84e80e5cd27cc311da4392e3c9d46375777a27c81bdc5e35e37b5b131867

Challenge cases:

84

No Phase 8B1 challenge performance will be measured during pretrained-router
development.

The challenge remains performance-locked until the pretrained and PEFT/LoRA
routers required for the planned final comparison are independently frozen.

## Metrics

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

## No-Tuning Rule

After the first Northstar development measurement, Phase 8B1 may not change:

- model ID;
- model revision;
- route hypotheses;
- route order;
- scoring function;
- label mapping;
- input representation;
- maximum length;
- decoding rule;
- tie-breaking rule.

Any changed zero-shot formulation requires a new experiment version and may
not replace this baseline result.

## Interpretation Boundary

The Phase 8A2 heuristic already achieved perfect development performance.

Therefore Phase 8B1 development accuracy is not intended to prove superiority
over the heuristic.

Its purpose is to establish the behavior of a frozen pretrained semantic model
before supervised PEFT/LoRA adaptation.

## Claim Boundary

Phase 8B1 can establish pretrained zero-shot routing performance on the
28-case development split after measurement.

It cannot establish:

- routing challenge performance;
- original locked-holdout performance;
- PEFT/LoRA performance;
- superiority over the heuristic;
- real-enterprise generalization;
- SQL execution correctness;
- graph execution correctness;
- end-to-end agent quality;
- production latency;
- production throughput;
- statistical significance.
