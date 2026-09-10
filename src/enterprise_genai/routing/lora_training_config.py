from __future__ import annotations

import hashlib
import json

from enterprise_genai.data.routing_models import (
    RouteLabel,
)

EXPERIMENT_VERSION = "lora-router-training-v1"

MODEL_ID = "cross-encoder/nli-deberta-v3-xsmall"

MODEL_REVISION = "a150876415327c80daeff35ca6f68f5ed8cf5c24"

QUESTION_REPRESENTATION_VERSION = "question-text-v1"

ROUTE_ORDER: tuple[RouteLabel, ...] = (
    "retrieval",
    "sql",
    "graph",
    "retrieval+sql",
    "retrieval+graph",
    "sql+graph",
    "retrieval+sql+graph",
)

LABEL2ID = {route: index for index, route in enumerate(ROUTE_ORDER)}

ID2LABEL = {index: route for route, index in LABEL2ID.items()}

NUM_LABELS = 7
MAX_LENGTH = 128

DEVICE = "cpu"
DTYPE = "float32"

TORCH_NUM_THREADS = 6
TORCH_NUM_INTEROP_THREADS = 6

DETERMINISTIC_ALGORITHMS = True

PEFT_VERSION = "0.20.0"
ACCELERATE_VERSION = "1.15.0"

LORA_TASK_TYPE = "SEQ_CLS"
LORA_R = 8
LORA_ALPHA = 16
LORA_DROPOUT = 0.05

LORA_TARGET_MODULES = (
    "query_proj",
    "value_proj",
)

LORA_BIAS = "none"

LORA_MODULES_TO_SAVE = ("classifier",)

EXPECTED_BASE_PARAMETERS = 70832647
EXPECTED_PEFT_TOTAL_PARAMETERS = 70982798
EXPECTED_TRAINABLE_PARAMETERS = 150151

TRAINING_SEEDS = (
    1729,
    2718,
    31415,
)

EPOCHS = 20
BATCH_SIZE = 16

OPTIMIZER = "AdamW"
LEARNING_RATE = 2e-4
WEIGHT_DECAY = 0.01
MAX_GRAD_NORM = 1.0

SCHEDULER = "constant"

SHUFFLE_VERSION = "epoch-seeded-randperm-v1"

LOSS = "cross-entropy"
CLASS_WEIGHTS = False
LABEL_SMOOTHING = 0.0

EVALUATE_EACH_EPOCH = True

TRAIN_CASES = 112
DEVELOPMENT_CASES = 28

STEPS_PER_EPOCH = 7
TOTAL_STEPS_PER_SEED = 140

TRAIN_SPLIT = "train"
DEVELOPMENT_SPLIT = "development"

ROUTING_BENCHMARK_SHA256 = "995f707a4cc6393f0e916f903cc57f9aec6fbabb3c43a00a78e318ca505b6912"

CHALLENGE_SHA256 = "e1fc84e80e5cd27cc311da4392e3c9d46375777a27c81bdc5e35e37b5b131867"

ORIGINAL_LOCKED_HOLDOUT_EVALUATED = False
CHALLENGE_EVALUATED = False

CHECKPOINT_SELECTION_ORDER = (
    "maximize_exact_route_set_accuracy",
    "maximize_macro_f1",
    "minimize_required_tool_omission_rate",
    "minimize_unnecessary_tool_addition_rate",
    "earlier_epoch",
)

SEED_SELECTION_ORDER = (
    "maximize_exact_route_set_accuracy",
    "maximize_macro_f1",
    "minimize_required_tool_omission_rate",
    "minimize_unnecessary_tool_addition_rate",
    "earlier_seed_in_frozen_seed_order",
)

FROZEN_LORA_TRAINING_CONFIG_SHA256 = (
    "bd2f9f65decf4e5d6b8d2b7dc9908c778f081cc20b2ade3ce78e502ab50c39cf"
)


def lora_training_config_payload() -> dict[
    str,
    object,
]:
    return {
        "experiment_version": (EXPERIMENT_VERSION),
        "model_id": MODEL_ID,
        "model_revision": (MODEL_REVISION),
        "route_order": list(ROUTE_ORDER),
        "label2id": LABEL2ID,
        "question_representation_version": (QUESTION_REPRESENTATION_VERSION),
        "num_labels": (NUM_LABELS),
        "max_length": (MAX_LENGTH),
        "device": DEVICE,
        "dtype": DTYPE,
        "torch_num_threads": (TORCH_NUM_THREADS),
        "torch_num_interop_threads": (TORCH_NUM_INTEROP_THREADS),
        "deterministic_algorithms": (DETERMINISTIC_ALGORITHMS),
        "peft_version": (PEFT_VERSION),
        "accelerate_version": (ACCELERATE_VERSION),
        "lora": {
            "task_type": (LORA_TASK_TYPE),
            "r": LORA_R,
            "lora_alpha": (LORA_ALPHA),
            "lora_dropout": (LORA_DROPOUT),
            "target_modules": list(LORA_TARGET_MODULES),
            "bias": LORA_BIAS,
            "modules_to_save": list(LORA_MODULES_TO_SAVE),
        },
        "expected_base_parameters": (EXPECTED_BASE_PARAMETERS),
        "expected_peft_total_parameters": (EXPECTED_PEFT_TOTAL_PARAMETERS),
        "expected_trainable_parameters": (EXPECTED_TRAINABLE_PARAMETERS),
        "training": {
            "seeds": list(TRAINING_SEEDS),
            "epochs": EPOCHS,
            "batch_size": (BATCH_SIZE),
            "optimizer": (OPTIMIZER),
            "learning_rate": (LEARNING_RATE),
            "weight_decay": (WEIGHT_DECAY),
            "max_grad_norm": (MAX_GRAD_NORM),
            "scheduler": (SCHEDULER),
            "shuffle": (SHUFFLE_VERSION),
            "loss": LOSS,
            "class_weights": (CLASS_WEIGHTS),
            "label_smoothing": (LABEL_SMOOTHING),
            "evaluate_each_epoch": (EVALUATE_EACH_EPOCH),
            "train_cases": (TRAIN_CASES),
            "development_cases": (DEVELOPMENT_CASES),
            "steps_per_epoch": (STEPS_PER_EPOCH),
            "total_steps_per_seed": (TOTAL_STEPS_PER_SEED),
        },
        "selection": {
            "checkpoint_order": list(CHECKPOINT_SELECTION_ORDER),
            "seed_order": list(SEED_SELECTION_ORDER),
        },
        "routing_benchmark_sha256": (ROUTING_BENCHMARK_SHA256),
        "train_split": (TRAIN_SPLIT),
        "development_split": (DEVELOPMENT_SPLIT),
        "original_locked_holdout_evaluated": (ORIGINAL_LOCKED_HOLDOUT_EVALUATED),
        "challenge_sha256": (CHALLENGE_SHA256),
        "challenge_evaluated": (CHALLENGE_EVALUATED),
    }


def lora_training_config_sha256() -> str:
    payload = json.dumps(
        lora_training_config_payload(),
        sort_keys=True,
        separators=(
            ",",
            ":",
        ),
        ensure_ascii=False,
    ).encode()

    return hashlib.sha256(payload).hexdigest()
