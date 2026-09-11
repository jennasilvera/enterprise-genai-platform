from __future__ import annotations

import pytest
from pydantic import ValidationError

from enterprise_genai.evaluation.generation_comparison import (
    GENERATION_COMPARISON_PROTOCOL_VERSION,
    GenerationComparisonCase,
    GenerationComparisonProtocol,
    build_generation_comparison_protocol,
)


def test_protocol_version_is_frozen() -> None:
    assert GENERATION_COMPARISON_PROTOCOL_VERSION == "northstar-generation-comparison-v1"


def test_protocol_has_frozen_five_case_order() -> None:
    protocol = build_generation_comparison_protocol()

    assert tuple(case.query_id for case in protocol.cases) == (
        "Q-0001",
        "Q-0010",
        "Q-0011",
        "Q-0023",
        "Q-0024",
    )


def test_every_case_compares_same_three_systems() -> None:
    protocol = build_generation_comparison_protocol()

    for case in protocol.cases:
        assert case.systems == (
            "deterministic",
            "raw_llm",
            "guarded_llm",
        )


def test_numeric_case_requires_numeric_and_unit_metrics() -> None:
    protocol = build_generation_comparison_protocol()

    case = next(item for item in protocol.cases if item.query_id == "Q-0011")

    assert "numeric_literal_preserved" in case.metrics

    assert "unit_preserved" in case.metrics


def test_abstention_cases_require_abstention_metric() -> None:
    protocol = build_generation_comparison_protocol()

    for query_id in (
        "Q-0023",
        "Q-0024",
    ):
        case = next(item for item in protocol.cases if item.query_id == query_id)

        assert "abstention_preserved" in case.metrics


def test_duplicate_case_metrics_are_rejected() -> None:
    with pytest.raises(
        ValidationError,
        match="unique",
    ):
        GenerationComparisonCase(
            query_id="Q-X",
            metrics=(
                "authority_preserved",
                "authority_preserved",
            ),
            notes="duplicate metrics",
        )


def test_protocol_rejects_wrong_case_order() -> None:
    base = build_generation_comparison_protocol()

    reversed_cases = tuple(reversed(base.cases))

    with pytest.raises(
        ValidationError,
        match="frozen five-case order",
    ):
        GenerationComparisonProtocol(cases=reversed_cases)


def test_claim_boundary_excludes_general_semantic_accuracy() -> None:
    protocol = build_generation_comparison_protocol()

    joined = " ".join(protocol.claim_boundary).lower()

    assert "not general semantic accuracy" in joined

    assert "not the complete 24-case" in joined


def test_claim_boundary_discloses_posthoc_protocol() -> None:
    protocol = build_generation_comparison_protocol()

    joined = " ".join(protocol.claim_boundary).lower()

    assert "after phase 10c model behavior" in joined

    assert "not blind or preregistered" in joined
