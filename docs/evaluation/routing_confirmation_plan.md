# Locked Routing Confirmation Plan

## Status

PRE-CONFIRMATION / PRE-MEASUREMENT

No router performance on either locked confirmation set is measured by this
phase before the protocol implementation is committed and tagged.

## Phase

Phase 8C confirmation.

## Primary Question

Does the frozen selected PEFT/LoRA router retain useful routing quality outside
the development split on:

1. the original northstar-routing-v1 locked holdout; and
2. the separate northstar-routing-challenge-v1 robustness set?

## Frozen Selected LoRA Router

Development-result commit:

9f128e89a994e90184b585bcded447e352b82e94

Development-result tag:

phase-8c-lora-router-development-result

Training report SHA-256:

afd035414008baea25aad26ce1775dc6887e6d2c51b92b603bd5346408aa34ac

Selected seed:

1729

Selected epoch:

19

Selected adapter weight SHA-256:

9b9e95c2122e9d233e47b7432a0ec268fc69f6ece936b7cb7dda80728020b8f0

Selected adapter configuration SHA-256:

5bc3929e5bf9f8b39cb9bacf54aac0be91723d177f9774cf41b91f218ded7fd5

No model, checkpoint, epoch, seed, threshold, representation, or hyperparameter
may be changed based on confirmation performance.

## Frozen Evaluation Sets

### Original Locked Holdout

Routing version:

northstar-routing-v1

Cases:

28

Split:

locked_holdout

SHA-256:

995f707a4cc6393f0e916f903cc57f9aec6fbabb3c43a00a78e318ca505b6912

Interpretation:

held-out-template-family confirmation.

### Routing Generalization Challenge

Routing version:

northstar-routing-challenge-v1

Cases:

84

Split:

locked_holdout

SHA-256:

e1fc84e80e5cd27cc311da4392e3c9d46375777a27c81bdc5e35e37b5b131867

Interpretation:

performance-locked robustness confirmation.

The challenge was constructed after observing the heuristic development
behavior and its text and labels were human reviewed. It therefore is not a
linguistically blind or pristine external benchmark.

## Frozen Routers

Exactly three routers are evaluated.

### Heuristic

heuristic-router-v1

This comparison is descriptive and template-informed. It must not be framed as
an unbiased learned-model baseline.

### Frozen Zero-Shot NLI

pretrained-nli-router-v1

Configuration SHA-256:

72d8ce61cdce386bb189cb70698d0f899bf94fa63b8f42796f1a19eaaca3e924

This is the frozen zero-shot baseline that exhibited maximal-route collapse on
development.

### Selected LoRA

lora-router-training-v1

Training configuration SHA-256:

bd2f9f65decf4e5d6b8d2b7dc9908c778f081cc20b2ade3ce78e502ab50c39cf

This is the primary selected router.

## Evaluation Order

Datasets:

1. original_locked_holdout
2. routing_challenge

Routers within each dataset:

1. heuristic
2. pretrained_nli
3. lora

No result is written until all six router-dataset evaluations complete.

## Metrics

For every router and dataset:

- exact route-set accuracy;
- macro precision;
- macro recall;
- macro F1;
- Hamming loss;
- required-tool omission rate;
- unnecessary-tool addition rate;
- under-routing case rate;
- over-routing case rate;
- per-tool precision, recall, F1, TP, FP, and FN.

All case-level predictions are retained.

NLI entailment scores, heuristic matched rules, and LoRA route probabilities are
also retained.

## No Confirmation Tuning

The confirmation results may not be used for:

- model selection;
- seed selection;
- epoch selection;
- threshold tuning;
- hypothesis rewriting;
- LoRA hyperparameter changes;
- representation changes;
- heuristic-rule changes;
- router fusion;
- calibration;
- benchmark editing.

Poor results are retained.

Any later changed system must be a new experiment and may not replace this
confirmation result.

## Interpretation Boundary

The original locked holdout can support a claim about performance on held-out
template families within northstar-routing-v1.

The routing challenge can support a robustness-confirmation claim only.

Neither set establishes real-enterprise generalization, production performance,
or statistical significance.

The heuristic comparison remains descriptive because the heuristic was authored
with knowledge of benchmark language.

## Frozen Confirmation Configuration

Canonical SHA-256:

8f18b4160e7c9d01c12dad2d65d23f1bceefccec4a146436545e0e2e7d859e91
