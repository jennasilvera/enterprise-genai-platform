from __future__ import annotations

import hashlib
import json

EXPERIMENT_VERSION = "routing-confirmation-v1"

DEVELOPMENT_RESULT_COMMIT = "9f128e89a994e90184b585bcded447e352b82e94"
DEVELOPMENT_RESULT_TAG = "phase-8c-lora-router-development-result"

TRAINING_REPORT_RELATIVE_PATH = (
    "artifacts/models/phase8c/lora-router-development/training-report.json"
)
TRAINING_REPORT_SHA256 = "afd035414008baea25aad26ce1775dc6887e6d2c51b92b603bd5346408aa34ac"

SELECTED_SEED = 1729
SELECTED_EPOCH = 19

SELECTED_ADAPTER_RELATIVE_PATH = (
    "artifacts/models/phase8c/lora-router-development/seed-1729/best_adapter"
)
SELECTED_ADAPTER_MODEL_SHA256 = "9b9e95c2122e9d233e47b7432a0ec268fc69f6ece936b7cb7dda80728020b8f0"
SELECTED_ADAPTER_CONFIG_SHA256 = "5bc3929e5bf9f8b39cb9bacf54aac0be91723d177f9774cf41b91f218ded7fd5"

ORIGINAL_ROUTING_VERSION = "northstar-routing-v1"
ORIGINAL_ROUTING_SHA256 = "995f707a4cc6393f0e916f903cc57f9aec6fbabb3c43a00a78e318ca505b6912"
ORIGINAL_ROUTING_COMMIT = "e0755e81d3d1fa24577dbe4e0dd7a92c00247863"
ORIGINAL_ROUTING_TAG = "phase-8a1-routing-ground-truth"
ORIGINAL_HOLDOUT_CASES = 28

CHALLENGE_ROUTING_VERSION = "northstar-routing-challenge-v1"
CHALLENGE_ROUTING_SHA256 = "e1fc84e80e5cd27cc311da4392e3c9d46375777a27c81bdc5e35e37b5b131867"
CHALLENGE_ROUTING_COMMIT = "bea37c093783bcbfb9f66e934f449e56fafa2e06"
CHALLENGE_ROUTING_TAG = "phase-8b0-routing-challenge-ground-truth"
CHALLENGE_CASES = 84

HEURISTIC_VERSION = "heuristic-router-v1"
HEURISTIC_RESULT_COMMIT = "109cda499184b71d74259bab7fbd352defc6ecdf"
HEURISTIC_RESULT_TAG = "phase-8a2-heuristic-router-result"

NLI_VERSION = "pretrained-nli-router-v1"
NLI_RESULT_COMMIT = "376798144c69742a652d5c3b48f9edb039bbef82"
NLI_RESULT_TAG = "phase-8b1-pretrained-nli-router-result"
NLI_CONFIG_SHA256 = "72d8ce61cdce386bb189cb70698d0f899bf94fa63b8f42796f1a19eaaca3e924"

LORA_VERSION = "lora-router-training-v1"
LORA_TRAINING_CONFIG_SHA256 = "bd2f9f65decf4e5d6b8d2b7dc9908c778f081cc20b2ade3ce78e502ab50c39cf"

METRICS = (
    "exact_route_set_accuracy",
    "macro_precision",
    "macro_recall",
    "macro_f1",
    "hamming_loss",
    "required_tool_omission_rate",
    "unnecessary_tool_addition_rate",
    "under_routing_case_rate",
    "over_routing_case_rate",
    "per_tool",
)

EVALUATION_ORDER = (
    "original_locked_holdout",
    "routing_challenge",
)

ROUTER_ORDER = (
    "heuristic",
    "pretrained_nli",
    "lora",
)

WRITE_POLICY = "write-after-all-router-dataset-evaluations-complete-v1"

RETUNING_ALLOWED = False
MODEL_SELECTION_ALLOWED = False
THRESHOLD_TUNING_ALLOWED = False


def routing_confirmation_config_payload() -> dict[str, object]:
    return {
        "experiment_version": EXPERIMENT_VERSION,
        "development_result": {
            "commit": DEVELOPMENT_RESULT_COMMIT,
            "tag": DEVELOPMENT_RESULT_TAG,
            "training_report_relative_path": (TRAINING_REPORT_RELATIVE_PATH),
            "training_report_sha256": (TRAINING_REPORT_SHA256),
            "selected_seed": SELECTED_SEED,
            "selected_epoch": SELECTED_EPOCH,
            "adapter_relative_path": (SELECTED_ADAPTER_RELATIVE_PATH),
            "adapter_model_sha256": (SELECTED_ADAPTER_MODEL_SHA256),
            "adapter_config_sha256": (SELECTED_ADAPTER_CONFIG_SHA256),
        },
        "datasets": [
            {
                "name": "original_locked_holdout",
                "routing_version": ORIGINAL_ROUTING_VERSION,
                "split": "locked_holdout",
                "cases": ORIGINAL_HOLDOUT_CASES,
                "sha256": ORIGINAL_ROUTING_SHA256,
                "source_commit": ORIGINAL_ROUTING_COMMIT,
                "source_tag": ORIGINAL_ROUTING_TAG,
                "interpretation": ("held-out-template-family-confirmation"),
                "linguistically_blind": False,
            },
            {
                "name": "routing_challenge",
                "routing_version": CHALLENGE_ROUTING_VERSION,
                "split": "locked_holdout",
                "cases": CHALLENGE_CASES,
                "sha256": CHALLENGE_ROUTING_SHA256,
                "source_commit": CHALLENGE_ROUTING_COMMIT,
                "source_tag": CHALLENGE_ROUTING_TAG,
                "interpretation": ("performance-locked-robustness-confirmation"),
                "linguistically_blind": False,
            },
        ],
        "routers": [
            {
                "name": "heuristic",
                "version": HEURISTIC_VERSION,
                "frozen_commit": HEURISTIC_RESULT_COMMIT,
                "frozen_tag": HEURISTIC_RESULT_TAG,
                "comparison_role": ("descriptive-template-informed-baseline"),
            },
            {
                "name": "pretrained_nli",
                "version": NLI_VERSION,
                "frozen_commit": NLI_RESULT_COMMIT,
                "frozen_tag": NLI_RESULT_TAG,
                "config_sha256": NLI_CONFIG_SHA256,
                "comparison_role": ("frozen-zero-shot-baseline"),
            },
            {
                "name": "lora",
                "version": LORA_VERSION,
                "frozen_commit": DEVELOPMENT_RESULT_COMMIT,
                "frozen_tag": DEVELOPMENT_RESULT_TAG,
                "training_config_sha256": (LORA_TRAINING_CONFIG_SHA256),
                "comparison_role": ("selected-primary-router"),
            },
        ],
        "metrics": list(METRICS),
        "evaluation_order": list(EVALUATION_ORDER),
        "router_order": list(ROUTER_ORDER),
        "write_policy": WRITE_POLICY,
        "retuning_allowed": RETUNING_ALLOWED,
        "model_selection_allowed": MODEL_SELECTION_ALLOWED,
        "threshold_tuning_allowed": THRESHOLD_TUNING_ALLOWED,
    }


def routing_confirmation_config_sha256() -> str:
    payload = json.dumps(
        routing_confirmation_config_payload(),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode()

    return hashlib.sha256(payload).hexdigest()


FROZEN_ROUTING_CONFIRMATION_CONFIG_SHA256 = (
    "8f18b4160e7c9d01c12dad2d65d23f1bceefccec4a146436545e0e2e7d859e91"
)
