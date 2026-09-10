# PEFT/LoRA Routing Classifier Results

## Status

MEASURED / REPRODUCIBLE / CONFIRMED / VERIFIED / FROZEN

Phase 8C trained and evaluated one frozen supervised PEFT/LoRA routing
configuration over the seven canonical retrieval / SQL / graph route sets.

The selected model was established entirely from the frozen training and
development splits before either confirmation set was evaluated.

## Scientific Question

Can lightweight supervised PEFT/LoRA adaptation learn the seven-route
retrieval / SQL / graph decision boundary without the maximal-route collapse
observed in the frozen zero-shot NLI baseline?

Result:

Yes on the original Northstar routing benchmark, with a substantial limitation:
the selected model generalized well to held-out template families but degraded
materially on the separate out-of-template robustness challenge.

## Experimental Lineage

### LoRA preregistration

Commit:

4fa4eb61121aa43f848dca10bd40a6f622279c39

Tag:

phase-8c-lora-router-preregistered

### Frozen development result

Commit:

9f128e89a994e90184b585bcded447e352b82e94

Tag:

phase-8c-lora-router-development-result

### Locked-confirmation preregistration

Commit:

1f32ed14ce5d414e0d040ecba58f347deac56cba

Tag:

phase-8c-routing-confirmation-preregistered

### Frozen locked-confirmation result

Commit:

6ee3e03d8ac96c6f4e9f1a076547409b9686eeab

Tag:

phase-8c-routing-confirmation-result

The development-result commit is an ancestor of the confirmation
preregistration, and the confirmation preregistration is an ancestor of the
frozen confirmation result.

## Base Model

Model:

cross-encoder/nli-deberta-v3-xsmall

Immutable revision:

a150876415327c80daeff35ca6f68f5ed8cf5c24

The pretrained three-class NLI classification head was replaced with a newly
initialized seven-class sequence-classification head.

The pretrained transformer backbone was adapted with PEFT/LoRA.

## Route Classes

Frozen route order:

1. retrieval
2. sql
3. graph
4. retrieval+sql
5. retrieval+graph
6. sql+graph
7. retrieval+sql+graph

The task is direct seven-class classification.

No independent per-tool threshold is used.

## PEFT Configuration

PEFT version:

0.20.0

Accelerate version:

1.15.0

LoRA rank:

8

LoRA alpha:

16

LoRA dropout:

0.05

Target modules:

- query_proj
- value_proj

Bias:

none

Explicit module saved:

classifier

Training configuration SHA-256:

bd2f9f65decf4e5d6b8d2b7dc9908c778f081cc20b2ade3ce78e502ab50c39cf

## Parameter Budget

Seven-class base model parameters:

70832647

PEFT-wrapped total parameters:

70982798

Trainable parameters:

150151

Trainable percentage:

0.2115315319072094 percent

Approximately:

0.21 percent

Trainable tensors:

- 24 LoRA A tensors;
- 24 LoRA B tensors;
- classifier weight;
- classifier bias.

Unexpected trainable tensors:

0

Trainable pooler tensors:

0

Runtime:

CPU FP32

CUDA used:

false

## Frozen Training Data

Routing benchmark:

northstar-routing-v1

Routing benchmark SHA-256:

995f707a4cc6393f0e916f903cc57f9aec6fbabb3c43a00a78e318ca505b6912

Training cases:

112

Development cases:

28

Original locked-holdout cases excluded from development:

28

Training cases per route:

16

Development cases per route:

4

Training/development template-family overlap:

0

## Frozen Training Procedure

Seeds:

- 1729
- 2718
- 31415

These are stochastic replications of one frozen configuration, not a
hyperparameter sweep.

Epochs per seed:

20

Batch size:

16

Optimizer steps per seed:

140

Optimizer:

AdamW

Learning rate:

0.0002

Weight decay:

0.01

Maximum gradient norm:

1.0

Scheduler:

constant

Loss:

cross entropy

Class weighting:

none

Label smoothing:

0.0

Mixed precision:

none

Development performance was measured after every epoch.

All 20 epochs were run for every seed.

No performance-based early stopping was used.

## Frozen Checkpoint Selection

Within each seed, checkpoints were ranked by:

1. maximize exact route-set accuracy;
2. maximize macro F1;
3. minimize required-tool omission rate;
4. minimize unnecessary-tool addition rate;
5. prefer the earlier epoch.

Across seeds, the corresponding frozen hierarchy was used, with the earlier
seed in the preregistered seed order resolving a complete metric tie.

## Per-Seed Best Development Results

### Seed 1729

Best epoch:

19

Exact route-set accuracy:

0.8214285714285714

Macro F1:

0.9523809523809524

Required-tool omission rate:

0.020833333333333332

Unnecessary-tool addition rate:

0.1111111111111111

### Seed 2718

Best epoch:

15

Exact route-set accuracy:

0.6428571428571429

Macro F1:

0.8425925925925926

Required-tool omission rate:

0.125

Unnecessary-tool addition rate:

0.2777777777777778

### Seed 31415

Best epoch:

18

Exact route-set accuracy:

0.8214285714285714

Macro F1:

0.9523809523809524

Required-tool omission rate:

0.020833333333333332

Unnecessary-tool addition rate:

0.1111111111111111

Seeds 1729 and 31415 tied on all frozen seed-selection metrics.

Seed 1729 was selected because it appears earlier in the frozen seed order.

This was not a post-hoc model choice.

## Selected Development Result

Selected seed:

1729

Selected epoch:

19

Cases:

28

Correct exact routes:

23 of 28

Exact route-set accuracy:

0.8214285714285714

Macro precision:

0.9298245614035089

Macro recall:

0.9791666666666666

Macro F1:

0.9523809523809524

Hamming loss:

0.05952380952380952

Required-tool omission rate:

0.020833333333333332

Unnecessary-tool addition rate:

0.1111111111111111

Under-routing case rate:

0.03571428571428571

Over-routing case rate:

0.14285714285714285

## Development Per-Tool Results

### Retrieval

True positives:

16

False positives:

0

False negatives:

0

Precision / recall / F1:

1.0 / 1.0 / 1.0

### SQL

True positives:

16

False positives:

0

False negatives:

0

Precision / recall / F1:

1.0 / 1.0 / 1.0

### Graph

True positives:

15

False positives:

4

False negatives:

1

Precision:

0.7894736842105263

Recall:

0.9375

F1:

0.8571428571428572

## Development Error Topology

Five of 28 development cases were not exact matches.

Four errors were:

sql -> sql+graph

These were graph false positives.

One error was:

retrieval+sql+graph -> retrieval+sql

This was a graph false negative.

The selected development model therefore learned retrieval and SQL perfectly at
the tool-decision level on this split, while the remaining development errors
were concentrated entirely at the graph decision boundary.

## Development Artifact

Canonical training report:

artifacts/models/phase8c/lora-router-development/training-report.json

SHA-256:

afd035414008baea25aad26ce1775dc6887e6d2c51b92b603bd5346408aa34ac

Selected adapter:

artifacts/models/phase8c/lora-router-development/seed-1729/best_adapter

Selected adapter weight SHA-256:

9b9e95c2122e9d233e47b7432a0ec268fc69f6ece936b7cb7dda80728020b8f0

Selected adapter configuration SHA-256:

5bc3929e5bf9f8b39cb9bacf54aac0be91723d177f9774cf41b91f218ded7fd5

## Reproducibility

Before Northstar training, a synthetic full-loop execution preflight exercised:

- real model loading;
- seven-class head construction;
- PEFT wrapping;
- forward and backward propagation;
- AdamW optimization;
- gradient clipping;
- checkpoint selection;
- adapter serialization;
- fresh-base adapter reload;
- exact development-output reproduction.

No Northstar case was used in that synthetic execution preflight.

After the canonical Northstar development result was frozen, an independent
full three-seed training rerun was executed to a separate temporary directory.

All seven generated files were byte-identical to the canonical experiment:

- three adapter_config.json files;
- three adapter_model.safetensors files;
- training-report.json.

The independent rerun reproduced:

- selected seed 1729;
- selected epoch 19;
- all development metrics;
- all adapter bytes;
- complete report bytes.

The rerun training-report SHA-256 was exactly:

afd035414008baea25aad26ce1775dc6887e6d2c51b92b603bd5346408aa34ac

Result:

BYTE-IDENTICAL full-tree reproduction.

## Frozen Zero-Shot NLI Development Reference

Frozen zero-shot router:

pretrained-nli-router-v1

Development exact route-set accuracy:

0.14285714285714285

Development macro F1:

0.7272727272727272

Required-tool omission rate:

0.0

Unnecessary-tool addition rate:

1.0

Over-routing case rate:

0.8571428571428571

All 28 development questions were predicted as:

retrieval+sql+graph

Observed failure mode:

maximal-route collapse

The supervised Phase 8C model therefore materially corrected the zero-shot
router's universal over-routing failure on the development benchmark.

This comparison does not isolate the causal contribution of the LoRA adapters
alone. Phase 8C changes both the learning formulation to supervised seven-class
classification and adapts the model with LoRA. A frozen-backbone
classifier-head-only control would be required to attribute an improvement
specifically to LoRA rather than supervised task adaptation more generally.

## Locked Confirmation Protocol

Confirmation configuration SHA-256:

8f18b4160e7c9d01c12dad2d65d23f1bceefccec4a146436545e0e2e7d859e91

Exactly three frozen routers were evaluated:

- heuristic-router-v1;
- pretrained-nli-router-v1;
- selected Phase 8C LoRA router.

Exactly two frozen datasets were evaluated:

- 28-case original locked holdout;
- 84-case routing generalization challenge.

No model selection, threshold tuning, seed selection, epoch selection,
hypothesis rewriting, heuristic modification, representation change,
calibration, router fusion, or benchmark editing was permitted after observing
confirmation performance.

## Original Locked-Holdout Result

Dataset:

northstar-routing-v1

Cases:

28

Interpretation:

held-out-template-family confirmation within the original benchmark.

### LoRA

Correct exact routes:

22 of 28

Exact route-set accuracy:

0.7857142857142857

Macro precision:

0.9629629629629629

Macro recall:

0.9166666666666666

Macro F1:

0.9327731092436974

Hamming loss:

0.07142857142857142

Required-tool omission rate:

0.08333333333333333

Unnecessary-tool addition rate:

0.05555555555555555

Under-routing case rate:

0.14285714285714285

Over-routing case rate:

0.07142857142857142

Per-tool F1:

- retrieval: 1.0;
- SQL: 0.9411764705882353;
- graph: 0.8571428571428571.

The selected model retained most of its development performance on held-out
template families.

### Heuristic Reference

Exact route-set accuracy:

1.0

Macro F1:

1.0

This result is descriptive only.

The heuristic was authored with knowledge of the original benchmark language
and must not be presented as an unbiased learned-model generalization result.

### Zero-Shot NLI Reference

Exact route-set accuracy:

0.14285714285714285

Macro F1:

0.7272727272727272

Predicted retrieval+sql+graph:

28 of 28 cases

The maximal-route collapse reproduced exactly on the original locked holdout.

## Original Holdout LoRA Error Topology

Six of 28 cases were not exact matches.

Two:

retrieval+graph -> retrieval+sql+graph

These added an unnecessary SQL tool.

Four:

sql+graph -> sql

These omitted graph.

The graph decision boundary therefore remained the main weakness on the
original held-out template families.

## Routing Generalization Challenge

Dataset:

northstar-routing-challenge-v1

Cases:

84

Dataset SHA-256:

e1fc84e80e5cd27cc311da4392e3c9d46375777a27c81bdc5e35e37b5b131867

Interpretation:

performance-locked robustness confirmation.

This challenge was created after observing the heuristic-development behavior.
Its text and labels were human reviewed before Phase 8C training.

It is not linguistically blind, pristine, or an independent real-enterprise
benchmark.

### LoRA

Correct exact routes:

27 of 84

Exact route-set accuracy:

0.32142857142857145

Macro precision:

0.8132214594457157

Macro recall:

0.6666666666666666

Macro F1:

0.6981797082358107

Hamming loss:

0.3055555555555556

Required-tool omission rate:

0.3333333333333333

Unnecessary-tool addition rate:

0.26851851851851855

Under-routing case rate:

0.5357142857142857

Over-routing case rate:

0.34523809523809523

Per-tool results:

Retrieval:

- precision: 0.8947368421052632;
- recall: 0.3541666666666667;
- F1: 0.5074626865671642.

SQL:

- precision: 0.9782608695652174;
- recall: 0.9375;
- F1: 0.9574468085106383.

Graph:

- precision: 0.5666666666666667;
- recall: 0.7083333333333334;
- F1: 0.6296296296296297.

The challenge exposes materially weaker out-of-template compositional
generalization, especially for retrieval and graph intent.

SQL intent remained comparatively robust.

### Heuristic Reference

Exact route-set accuracy:

0.2857142857142857

Macro F1:

0.530961791831357

Graph recall:

0.0

The heuristic predicted only retrieval or SQL routes and never selected graph.

This demonstrates that its perfect performance on the original holdout does not
translate into robust coverage under the challenge wording.

### Zero-Shot NLI Reference

Exact route-set accuracy:

0.14285714285714285

Macro F1:

0.7272727272727272

Required-tool omission rate:

0.0

Unnecessary-tool addition rate:

1.0

Predicted retrieval+sql+graph:

84 of 84 cases

The zero-shot maximal-route collapse therefore reproduced on every challenge
case.

Its macro F1 should not be interpreted in isolation as superior routing quality:
predicting every tool yields perfect recall while creating systematic
unnecessary-tool invocation.

## Challenge Interpretation

Exact route-set accuracy:

- LoRA: 0.32142857142857145;
- heuristic: 0.2857142857142857;
- zero-shot NLI: 0.14285714285714285.

The selected LoRA router had the highest exact route-set accuracy of the three
frozen routers on the robustness challenge.

However, 32.14 percent exact accuracy is not evidence of strong broad
generalization.

The challenge is retained as a negative robustness finding and is not used to
rewrite or replace the Phase 8C model.

Any later routing improvement must be a separate experiment.

## Confirmation Artifact

Canonical artifact:

artifacts/evaluation/phase8c/routing-confirmation.json

Canonical SHA-256:

95196035d5b47b1f8e741d3fdb0c8ba5997284049dc24964d76b8e499b550829

Frozen result commit:

6ee3e03d8ac96c6f4e9f1a076547409b9686eeab

Frozen result tag:

phase-8c-routing-confirmation-result

## What Phase 8C Demonstrates

Repository evidence supports the ability to:

- formulate tool routing as a direct supervised classification problem;
- use a pinned pretrained transformer backbone;
- replace a pretrained classification head for a new task;
- configure and train PEFT/LoRA adapters;
- audit exactly which parameters are trainable;
- enforce a small trainable-parameter budget;
- run deterministic CPU training;
- execute multi-seed experiments under a frozen protocol;
- select checkpoints and seeds by preregistered metrics;
- serialize and reload PEFT adapters;
- reproduce a complete training experiment byte-for-byte;
- separate development selection from locked confirmation;
- measure exact-set and per-tool routing behavior;
- distinguish omission from unnecessary-tool invocation;
- diagnose route-specific failure topology;
- preserve negative robustness findings;
- avoid post-hoc tuning against locked confirmation performance.

## Resume-Safe Claim

A defensible concise claim is:

> Built and evaluated a PEFT/LoRA seven-class tool router across retrieval, SQL,
> and graph execution paths; fine-tuned 150K parameters (~0.21% of the model)
> in deterministic multi-seed CPU experiments, achieving 82.1% development and
> 78.6% held-out exact routing accuracy while identifying out-of-template
> robustness limitations on a separate 84-case challenge.

A more technical interview version is:

> Adapted a pinned DeBERTa-v3 NLI backbone into a seven-class retrieval / SQL /
> graph router with PEFT LoRA (r=8, 150,151 trainable parameters), preregistered
> checkpoint and seed selection, reproduced the complete three-seed CPU
> experiment byte-for-byte, and measured 78.6% exact routing accuracy on frozen
> held-out template families; a separate 84-case robustness challenge exposed
> weaker retrieval/graph compositional generalization.

## Claim Boundaries

Do not claim:

- production routing performance;
- real-enterprise generalization;
- statistical significance;
- linguistically blind external validation;
- perfect generalization;
- that the heuristic is an unbiased baseline;
- that LoRA challenge performance is strong;
- that macro F1 alone establishes operational routing quality;
- that LoRA adapters alone causally produced the improvement;
- GPU or CUDA training;
- production latency, throughput, or cost results;
- SQL execution correctness;
- graph execution correctness;
- end-to-end agent quality.

Those require separate evidence.
