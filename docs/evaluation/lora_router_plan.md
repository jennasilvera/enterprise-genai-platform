# PEFT/LoRA Routing Classifier Plan

## Status

PRE-TRAINING / PRE-MEASUREMENT

No supervised Northstar gradient step has occurred when this protocol is
authored.

## Phase

Phase 8C

## Scientific Question

Can lightweight supervised PEFT/LoRA adaptation learn the seven-route
retrieval / SQL / graph decision boundary without the maximal-route collapse
observed in the frozen zero-shot NLI baseline?

## Base Model

Model:

cross-encoder/nli-deberta-v3-xsmall

Immutable revision:

a150876415327c80daeff35ca6f68f5ed8cf5c24

The pretrained three-class NLI classifier head is replaced by a newly
initialized seven-class sequence-classification head.

The transformer backbone retains the pretrained NLI weights.

## Route Classes

Frozen class order:

1. retrieval
2. sql
3. graph
4. retrieval+sql
5. retrieval+graph
6. sql+graph
7. retrieval+sql+graph

The model performs direct seven-class classification.

No independent per-tool probability threshold is used.

## PEFT Configuration

PEFT:

0.20.0

Accelerate:

1.15.0

Task type:

SEQ_CLS

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

Explicit module to save:

classifier

The PEFT implementation may internally report additional sequence-classifier
module aliases. The authoritative trainability check is the actual
requires_grad parameter audit.

## Parameter Budget

Seven-class base model parameters:

70832647

PEFT-wrapped total parameters:

70982798

Trainable parameters:

150151

Trainable percentage:

approximately 0.2115 percent

Trainable tensors consist only of:

- LoRA A matrices;
- LoRA B matrices;
- seven-class classifier weight;
- seven-class classifier bias.

The pooler remains frozen.

## Reproducibility Preflight

Before any Northstar training:

- same-seed one-step training produced identical loss;
- same-seed resulting logits were byte-equivalent numerically;
- frozen parameters received no gradients;
- adapter save/reload succeeded;
- reloaded logits exactly matched pre-save logits;
- the seven-class label mapping survived adapter reload.

These checks used only generic synthetic text.

## Input

Representation:

question-text-v1

Maximum tokenized length:

128

Input consists only of normalized question text.

No split identifier, template-family identifier, ground-truth tool metadata,
difficulty label, entity ID, or benchmark label is included in model input.

## Frozen Data

Routing benchmark:

northstar-routing-v1

SHA-256:

995f707a4cc6393f0e916f903cc57f9aec6fbabb3c43a00a78e318ca505b6912

Training:

112 cases

Development:

28 cases

Original locked holdout:

28 cases, not used in Phase 8C model development

Training route balance:

16 cases per route

Development route balance:

4 cases per route

Train/development template-family overlap:

0

## Seeds

Exactly three training seeds are run:

- 1729
- 2718
- 31415

These are stochastic replications of one fixed model and hyperparameter
configuration.

They are not a hyperparameter sweep.

Each seed controls:

- seven-class classifier initialization;
- LoRA initialization;
- model dropout;
- training-order permutation.

## Determinism

Runtime:

CPU FP32

PyTorch intra-op threads:

6

PyTorch inter-op threads:

6

Deterministic algorithms:

enabled

Training examples are shuffled once per epoch using a deterministic
epoch-specific permutation derived from the frozen training seed.

## Optimization

Epochs:

20

Batch size:

16

Steps per epoch:

7

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

Gradient accumulation:

none

Mixed precision:

none

## Checkpoint Evaluation

Development performance is measured after every completed epoch.

All 20 epochs are run.

There is no performance-based early stopping.

The best checkpoint within each seed is selected using, in order:

1. maximize exact route-set accuracy;
2. maximize macro F1;
3. minimize required-tool omission rate;
4. minimize unnecessary-tool addition rate;
5. prefer the earlier epoch.

## Seed Selection

After each seed's best checkpoint is established, the final Phase 8C model is
selected across the three seeds using:

1. maximize exact route-set accuracy;
2. maximize macro F1;
3. minimize required-tool omission rate;
4. minimize unnecessary-tool addition rate;
5. prefer the earlier seed in the frozen seed order.

All three seed results remain in the evaluation record regardless of which
checkpoint is selected.

## Metrics

Primary:

- exact route-set accuracy
- macro F1

Critical safety/cost diagnostic:

- required-tool omission rate
- unnecessary-tool addition rate

Secondary:

- macro precision
- macro recall
- Hamming loss
- under-routing case rate
- over-routing case rate
- per-tool precision / recall / F1

## Comparison Baselines

Frozen heuristic development result:

exact route-set accuracy = 1.0

Frozen zero-shot NLI development result:

exact route-set accuracy = 0.14285714285714285

The zero-shot model exhibited maximal-route collapse.

Phase 8C does not alter either baseline.

## Benchmark Visibility

The Northstar routing benchmark and routing-generalization challenge text and
labels were constructed and human-reviewed before the Phase 8C training
configuration was authored.

Therefore Phase 8C is not linguistically blind to the benchmark domain or
challenge language.

Before the Phase 8C preregistration boundary:

- no supervised Northstar gradient step has occurred;
- no Phase 8C training performance has been observed;
- no Phase 8C development performance has been observed;
- no Phase 8C original locked-holdout performance has been observed;
- no Phase 8C routing-challenge performance has been observed.

The original locked holdout and the 84-case challenge are performance-locked,
but neither should be described as pristine, human-unseen, or linguistically
blind.

Any later challenge evaluation should therefore be interpreted as a
no-performance-tuning robustness confirmation rather than a fully blind
external test.

## Generalization Challenge Lock

Challenge:

northstar-routing-challenge-v1

Challenge SHA-256:

e1fc84e80e5cd27cc311da4392e3c9d46375777a27c81bdc5e35e37b5b131867

Challenge cases:

84

The challenge remains performance-locked throughout Phase 8C training and
development selection.

It may not be used for:

- epoch selection;
- seed selection;
- learning-rate selection;
- LoRA-rank selection;
- target-module selection;
- dropout selection;
- prompt or representation selection;
- debugging model quality.

The challenge may be evaluated only after the selected LoRA router has been
independently frozen.

## Original Locked Holdout

The original northstar-routing-v1 locked_holdout is also not used for Phase
8C model selection.

## No Hyperparameter Tuning

The following are frozen before the first Northstar gradient step:

- base model;
- model revision;
- route order;
- LoRA rank;
- LoRA alpha;
- LoRA dropout;
- LoRA target modules;
- trainable classifier;
- maximum sequence length;
- seeds;
- epoch count;
- batch size;
- optimizer;
- learning rate;
- weight decay;
- gradient clipping;
- scheduler;
- loss;
- checkpoint-selection rule;
- seed-selection rule.

If this fixed experiment performs poorly, the result is retained.

Any later changed configuration must use a new experiment version and may not
replace this baseline.

## Frozen Configuration Fingerprint

Canonical SHA-256:

bd2f9f65decf4e5d6b8d2b7dc9908c778f081cc20b2ade3ce78e502ab50c39cf

The runtime implementation must verify this fingerprint before the first
Northstar training step.


## Full-Loop Synthetic Training Preflight

Before the first supervised Northstar gradient step, the complete Phase 8C
training path was exercised using only synthetic execution-test fixtures.

Synthetic fixture:

- training cases: 14;
- development cases: 7;
- route classes: 7;
- Northstar cases used: 0;
- seed: 1729;
- epochs executed: 20.

The smoke test exercised:

- immutable pretrained model loading;
- seven-class classifier initialization;
- PEFT/LoRA wrapping;
- parameter-trainability auditing;
- CPU FP32 runtime enforcement;
- deterministic epoch shuffling;
- forward and backward propagation;
- AdamW optimization;
- gradient clipping;
- development evaluation after each epoch;
- preregistered best-epoch selection;
- adapter checkpoint replacement;
- adapter serialization;
- adapter manifest hashing;
- fresh-base adapter reload;
- complete development-output reproduction after reload.

Observed structural checks:

- trainable parameters: 150151;
- LoRA A tensors: 24;
- LoRA B tensors: 24;
- classifier tensors: 2;
- parameter devices: CPU only;
- parameter dtype: torch.float32 only;
- unexpected trainable tensors: 0;
- trainable pooler tensors: 0;
- finite epoch losses: 20;
- selected synthetic epoch: 7;
- complete development output after adapter reload: exact match.

The synthetic routing metrics are execution-test values only and are not
Northstar performance evidence. They must not be reported as routing quality
results or used to alter the frozen Phase 8C training configuration.

The synthetic adapter and all associated files were stored only under /tmp and
deleted before Phase 8C preregistration.

## Claim Boundary

After measurement, Phase 8C may support claims about:

- PEFT/LoRA implementation;
- the exact trainable-parameter budget;
- deterministic supervised routing training;
- development performance across three fixed seeds;
- checkpoint selection under a preregistered metric hierarchy;
- whether LoRA reduced maximal-route collapse;
- adapter serialization and reproducibility.

Until the experiment is run, Phase 8C establishes no routing-performance
claim.

Phase 8C does not establish:

- routing-challenge performance;
- original locked-holdout performance;
- real-enterprise generalization;
- SQL execution correctness;
- graph execution correctness;
- end-to-end agent quality;
- production latency;
- production throughput;
- statistical significance.
