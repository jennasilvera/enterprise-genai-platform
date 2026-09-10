from pathlib import Path

from enterprise_genai.data.routing_challenge_seed import (
    build_routing_challenge,
    routing_challenge_sha256,
)
from enterprise_genai.data.routing_seed import (
    build_routing_seed,
    routing_seed_sha256,
)
from enterprise_genai.evaluation.lora_routing_benchmark import (
    sha256_file,
)
from enterprise_genai.evaluation.routing_confirmation import (
    deterministic_confirmation_report_bytes,
)
from enterprise_genai.evaluation.routing_confirmation_config import (
    CHALLENGE_CASES,
    CHALLENGE_ROUTING_SHA256,
    FROZEN_ROUTING_CONFIRMATION_CONFIG_SHA256,
    ORIGINAL_HOLDOUT_CASES,
    ORIGINAL_ROUTING_SHA256,
    SELECTED_ADAPTER_CONFIG_SHA256,
    SELECTED_ADAPTER_MODEL_SHA256,
    SELECTED_ADAPTER_RELATIVE_PATH,
    TRAINING_REPORT_RELATIVE_PATH,
    TRAINING_REPORT_SHA256,
    routing_confirmation_config_sha256,
)


def test_confirmation_configuration_sha() -> None:
    assert (
        routing_confirmation_config_sha256()
        == FROZEN_ROUTING_CONFIRMATION_CONFIG_SHA256
        == ("8f18b4160e7c9d01c12dad2d65d23f1bceefccec4a146436545e0e2e7d859e91")
    )


def test_locked_dataset_fingerprints() -> None:
    original = build_routing_seed()

    assert routing_seed_sha256(original) == ORIGINAL_ROUTING_SHA256

    original_holdout = [case for case in original.cases if case.split == "locked_holdout"]

    assert len(original_holdout) == ORIGINAL_HOLDOUT_CASES == 28

    challenge = build_routing_challenge()

    assert routing_challenge_sha256(challenge) == CHALLENGE_ROUTING_SHA256

    challenge_holdout = [case for case in challenge.cases if case.split == "locked_holdout"]

    assert len(challenge_holdout) == CHALLENGE_CASES == 84


def test_selected_lora_artifact_hashes() -> None:
    root = Path(".")

    report = root / TRAINING_REPORT_RELATIVE_PATH

    adapter = root / SELECTED_ADAPTER_RELATIVE_PATH

    assert sha256_file(report) == TRAINING_REPORT_SHA256

    assert sha256_file(adapter / "adapter_config.json") == SELECTED_ADAPTER_CONFIG_SHA256

    assert sha256_file(adapter / "adapter_model.safetensors") == SELECTED_ADAPTER_MODEL_SHA256


def test_confirmation_report_bytes_are_deterministic() -> None:
    payload = {
        "b": 2,
        "a": 1,
    }

    first = deterministic_confirmation_report_bytes(payload)

    second = deterministic_confirmation_report_bytes(payload)

    assert first == second

    assert first.endswith(b"\n")
