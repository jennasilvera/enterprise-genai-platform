from __future__ import annotations

import json

import pytest

from enterprise_genai.evaluation.generation_comparison_confirmation import (
    FROZEN_COMPARISON_QUERY_IDS,
    GENERATION_COMPARISON_CONFIRMATION_VERSION,
    build_comparison_confirmation_report,
    canonical_comparison_report_bytes,
)


def _score(
    system: str,
    passed: int,
) -> dict:
    return {
        "system": system,
        "text": "example",
        "passed": passed,
        "total": 5,
        "metrics": [],
    }


def _cases() -> list[dict]:
    values = []

    for query_id in FROZEN_COMPARISON_QUERY_IDS:
        values.append(
            {
                "query_id": query_id,
                "systems": [
                    _score(
                        "deterministic",
                        5,
                    ),
                    _score(
                        "raw_llm",
                        2,
                    ),
                    _score(
                        "guarded_llm",
                        5,
                    ),
                ],
            }
        )

    return values


def test_confirmation_version_is_frozen() -> None:
    assert GENERATION_COMPARISON_CONFIRMATION_VERSION == (
        "northstar-generation-comparison-confirmation-v1"
    )


def test_confirmation_query_order_is_frozen() -> None:
    assert FROZEN_COMPARISON_QUERY_IDS == (
        "Q-0001",
        "Q-0010",
        "Q-0011",
        "Q-0023",
        "Q-0024",
    )


def test_report_aggregates_three_systems() -> None:
    report = build_comparison_confirmation_report(
        dataset_version="northstar-v1",
        evaluation_version=("northstar-eval-v1-seed"),
        provider_metadata={
            "provider_id": "provider",
        },
        cases=_cases(),
    )

    assert report["summary"] == {
        "deterministic": {
            "passed": 25,
            "total": 25,
            "rate": 1.0,
        },
        "raw_llm": {
            "passed": 10,
            "total": 25,
            "rate": 0.4,
        },
        "guarded_llm": {
            "passed": 25,
            "total": 25,
            "rate": 1.0,
        },
    }


def test_report_rejects_wrong_case_order() -> None:
    cases = list(reversed(_cases()))

    with pytest.raises(
        ValueError,
        match="five-case order",
    ):
        build_comparison_confirmation_report(
            dataset_version="northstar-v1",
            evaluation_version=("northstar-eval-v1-seed"),
            provider_metadata={},
            cases=cases,
        )


def test_report_rejects_wrong_system_order() -> None:
    cases = _cases()

    cases[0]["systems"] = list(reversed(cases[0]["systems"]))

    with pytest.raises(
        ValueError,
        match="three-system order",
    ):
        build_comparison_confirmation_report(
            dataset_version="northstar-v1",
            evaluation_version=("northstar-eval-v1-seed"),
            provider_metadata={},
            cases=cases,
        )


def test_canonical_bytes_are_stable() -> None:
    report = {
        "b": 2,
        "a": 1,
    }

    raw = canonical_comparison_report_bytes(report)

    assert raw == (b'{"a":1,"b":2}\n')

    assert json.loads(raw) == report
