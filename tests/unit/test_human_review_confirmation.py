from __future__ import annotations

import ast
import hashlib
from pathlib import Path

from enterprise_genai.evaluation.human_review_confirmation import (
    DEFAULT_CASE_MANIFEST_PATH,
    DEFAULT_FREEZE_MANIFEST_PATH,
    DEFAULT_RESULT_PATH,
    PHASE13E_CONFIRMATION_VERSION,
    RUNNER_PATH,
    deterministic_report_bytes,
    load_frozen_inputs,
    report_sha256,
)


def test_confirmation_version_is_frozen() -> None:
    assert PHASE13E_CONFIRMATION_VERSION == ("northstar-human-review-phase13e-confirmation-v1")


def test_result_path_is_frozen() -> None:
    assert (
        Path("artifacts/evaluation/phase13e1/human_review_confirmation.json") == DEFAULT_RESULT_PATH
    )


def test_frozen_inputs_load_without_measurement() -> None:
    manifest, freeze = load_frozen_inputs()

    assert manifest["protocol_status"] == "preregistered_unmeasured"

    assert len(manifest["ordinary_controls"]) == 3

    assert len(manifest["reviewed_cases"]) == 6

    assert len(manifest["pre_review_failures"]) == 3

    assert len(manifest["decision_cases"]) == 5

    assert freeze["result_path"] == str(DEFAULT_RESULT_PATH)


def test_locked_metric_populations_are_exact() -> None:
    manifest, _freeze = load_frozen_inputs()

    expected = {
        "review_creation_accuracy": 6,
        "pre_decision_generation_suppression": 6,
        "approval_continuation_accuracy": 3,
        "rejection_enforcement_rate": 3,
        "pre_review_failure_preservation": 3,
        "citation_integrity": 6,
        "provenance_integrity": 6,
        "decision_conflict_enforcement": 2,
        "restart_resume_accuracy": 1,
    }

    assert set(manifest["locked_metrics"]) == set(expected)

    for name, denominator in expected.items():
        spec = manifest["locked_metrics"][name]

        assert spec["denominator"] == denominator

        assert len(spec["case_ids"]) == denominator

        assert spec["threshold"] == 1.0


def test_reviewed_population_is_three_approve_three_reject() -> None:
    manifest, _freeze = load_frozen_inputs()

    dispositions = [case["disposition"] for case in manifest["reviewed_cases"]]

    assert dispositions.count("approve") == 3

    assert dispositions.count("reject") == 3

    restart = [case for case in manifest["reviewed_cases"] if case["restart_before_decision"]]

    assert len(restart) == 1


def test_reviewed_fixtures_have_route_diversity() -> None:
    manifest, _freeze = load_frozen_inputs()

    kinds = {case["fixture"]["kind"] for case in manifest["reviewed_cases"]}

    assert kinds == {
        "retrieval",
        "sql_value",
        "sql_entity",
    }


def test_pre_review_failure_families_are_frozen() -> None:
    manifest, _freeze = load_frozen_inputs()

    reasons = {case["expected"]["reason"] for case in manifest["pre_review_failures"]}

    assert reasons == {
        "no_relevant_evidence",
        "unsupported_request",
        "instruction_integrity_blocked",
    }


def test_decision_behavior_population_is_frozen() -> None:
    manifest, _freeze = load_frozen_inputs()

    kinds = {case["kind"] for case in manifest["decision_cases"]}

    assert kinds == {
        "duplicate_approval",
        "duplicate_rejection",
        "approve_then_reject",
        "reject_then_approve",
        "unknown_review_id",
    }


def test_freeze_anchors_phase13_history() -> None:
    _manifest, freeze = load_frozen_inputs()

    assert freeze["phase13a"]["commit"] == ("ae96fbdeef0919b46cc7479cdcd0d5aff2fb44c9")

    assert freeze["phase13b"]["commit"] == ("b15e66277ad0dbc3b42875813891186c36e8aa9b")

    assert freeze["phase13c"]["commit"] == ("7cfb50fba42bc373a9cae8dc0196ff5269f52cfa")

    assert freeze["phase13d"]["commit"] == ("c282142a480cbb210472dd9004bbbff42562f186")

    assert freeze["phase13b"]["schema_revision"] == ("7b1c0e2f4a91")


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

    expected = hashlib.sha256(b'{"metrics":{"a":1,"b":0},"version":"test"}').hexdigest()

    assert report_sha256(report) == expected


def test_tests_do_not_execute_phase13e1_measurement() -> None:
    test_text = Path(__file__).read_text(encoding="utf-8")

    tree = ast.parse(test_text)

    forbidden = {
        "_run_ordinary_case",
        "_run_reviewed_case",
        "_run_pre_review_failure",
        "_run_unknown_decision",
        "run_phase13e1_confirmation",
        "write_phase13e1_confirmation",
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
    text = RUNNER_PATH.read_text(encoding="utf-8")

    assert 'if __name__ == "__main__":' in text

    assert "write_phase13e1_confirmation" in text

    assert "Refusing to overwrite" in text

    assert "human_review_requests" in text

    assert "deterministic_confirmation_provider" in text


def test_case_and_freeze_manifest_paths_are_distinct() -> None:
    assert DEFAULT_CASE_MANIFEST_PATH != DEFAULT_FREEZE_MANIFEST_PATH


def test_phase13e1_result_is_not_created_by_tests() -> None:
    assert not (DEFAULT_RESULT_PATH.exists())
