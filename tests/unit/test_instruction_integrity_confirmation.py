from __future__ import annotations

import ast
import hashlib
from pathlib import Path

from enterprise_genai.evaluation.instruction_integrity_confirmation import (
    BASELINE_CANONICAL_SHA256,
    BASELINE_FILE_SHA256,
    MANIFEST_CANONICAL_SHA256,
    MANIFEST_FILE_SHA256,
    PHASE12C_COMMIT,
    PHASE12C_TAG,
    PHASE12D_CONFIRMATION_VERSION,
    POLICY_CANONICAL_SHA256,
    POLICY_FILE_SHA256,
    deterministic_report_bytes,
    expected_safe_failure_paths,
    load_frozen_inputs,
    report_sha256,
)

RUNNER = Path("src/enterprise_genai/evaluation/instruction_integrity_confirmation.py")

RESULT = Path("artifacts/evaluation/phase12d/instruction_integrity_confirmation.json")


def test_confirmation_version_is_frozen() -> None:
    assert PHASE12D_CONFIRMATION_VERSION == (
        "northstar-instruction-integrity-phase12d-confirmation-v1"
    )


def test_frozen_anchor_constants() -> None:
    assert MANIFEST_CANONICAL_SHA256 == (
        "20a5fcfe0a7ab41cabe36d3503dabf9828ffa65753c8c747cdfd3974afe224b8"
    )

    assert MANIFEST_FILE_SHA256 == (
        "af91e9ede94085d8b9d1f713506520b1e882a6da64a7bcdb59a4c8352576f924"
    )

    assert BASELINE_CANONICAL_SHA256 == (
        "47a095e3c264398b7e3ed3beca1697cd9e2cb5f738ff2d955cc0ab7e80923f78"
    )

    assert BASELINE_FILE_SHA256 == (
        "a2149e2bb1b7ae248e4bc4c76dd06c323be6e12cce1d3d2278b7ce9a84e95955"
    )

    assert POLICY_CANONICAL_SHA256 == (
        "2fd50731aca34c5eab62567b77247b6c6ccafb9b4b6fd24106dc81ee099ca8c3"
    )

    assert POLICY_FILE_SHA256 == (
        "5ff4d457d6eed3ad7a240e0f85ac670ff8e1fa54cd04f08ba415bae7adba5ed2"
    )

    assert PHASE12C_COMMIT == ("4e5bc5dcee4979e6e4d8013971690211aa08ddb8")

    assert PHASE12C_TAG == ("phase-12c-instruction-integrity-policy-v1")


def test_frozen_inputs_load_without_measurement() -> None:
    manifest, baseline, policy = load_frozen_inputs()

    assert len(manifest["cases"]) == 32

    assert len(baseline["cases"]) == 32

    assert policy["safe_failure"]["reason"] == "instruction_integrity_blocked"


def test_safe_failure_path_population_is_frozen() -> None:
    manifest, baseline, _policy = load_frozen_inputs()

    paths = expected_safe_failure_paths(
        manifest=manifest,
        baseline=baseline,
    )

    assert len(paths) == 26

    assert sum(path == "preexisting_typed_abstention" for path in paths.values()) == 5

    assert sum(path == "instruction_integrity_block" for path in paths.values()) == 21

    for case_id in (
        "PH12B-B1",
        "PH12B-B2",
        "PH12B-B3",
        "PH12B-B4",
        "PH12B-E4",
    ):
        assert paths[case_id] == ("preexisting_typed_abstention")

    assert paths["PH12B-C1"] == "instruction_integrity_block"

    assert paths["PH12B-F8"] == "instruction_integrity_block"


def test_report_serialization_is_deterministic() -> None:
    report = {
        "version": "test",
        "metrics": {
            "a": 1,
            "b": 0,
        },
    }

    first = deterministic_report_bytes(report)

    second = deterministic_report_bytes(report)

    assert first == second

    assert (
        report_sha256(report)
        == hashlib.sha256(b'{"metrics":{"a":1,"b":0},"version":"test"}').hexdigest()
    )


def test_tests_do_not_execute_phase12d_measurement() -> None:
    test_text = Path(__file__).read_text(encoding="utf-8")

    tree = ast.parse(test_text)

    forbidden = {
        "_run_case",
        "run_phase12d_confirmation",
        "write_phase12d_confirmation",
        "main",
    }

    for node in ast.walk(tree):
        if not isinstance(
            node,
            ast.Call,
        ):
            continue

        called = None

        if isinstance(
            node.func,
            ast.Name,
        ):
            called = node.func.id

        elif isinstance(
            node.func,
            ast.Attribute,
        ):
            called = node.func.attr

        assert called not in forbidden


def test_runner_has_explicit_only_entrypoint() -> None:
    text = RUNNER.read_text(encoding="utf-8")

    assert 'if __name__ == "__main__":' in text

    assert "write_phase12d_confirmation" in text

    assert "Refusing to overwrite" in text

    assert "evaluate_instruction_integrity" in text

    assert "instruction_integrity_block" in text


def test_confirmation_result_is_not_created_by_tests() -> None:
    assert not RESULT.exists()


def test_preexisting_abstentions_do_not_satisfy_phase12c_safe_failure() -> None:
    text = RUNNER.read_text(encoding="utf-8")

    assert "safe_failure_pass = False" in text

    assert '"preexisting_safe_abstention_cases"' in text

    assert '"preexisting_safe_abstentions_preserved"' in text


def test_phase12c_safe_failure_checks_complete_frozen_disposition() -> None:
    text = RUNNER.read_text(encoding="utf-8")

    required = (
        '"service_status"',
        '"service_reason"',
        '"service_detail"',
        '"presentation_source"',
        '"generation_fidelity"',
        '"presentation_text"',
        "synthesis_invoked",
        "generation_authority_created",
        "generation_invoked",
        "citation_integrity_pass",
        "provenance_integrity_pass",
    )

    for token in required:
        assert token in text


def test_safe_failure_metric_is_phase12c_disposition_only() -> None:
    text = RUNNER.read_text(encoding="utf-8")

    assert "scored_against_frozen_phase12c_fail_closed_disposition" in text

    assert "phase12b_and_phase12c_" not in text

    assert '"preexisting_safe_failure_cases"' not in text
