from __future__ import annotations

import pytest
from pydantic import ValidationError

from enterprise_genai.evaluation.generation_comparison import (
    GENERATION_COMPARISON_PROTOCOL_VERSION,
    GenerationComparisonCase,
    GenerationComparisonProtocol,
    build_generation_comparison_protocol,
    score_comparison_text,
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


def test_deterministic_numeric_scores_all_numeric_metrics() -> None:
    protocol = build_generation_comparison_protocol()

    case = next(item for item in protocol.cases if item.query_id == "Q-0011")

    score = score_comparison_text(
        case=case,
        system="deterministic",
        text="735000000 USD",
        authority_outcome="answer",
        authority_answer_type="number",
        authority_value=735000000,
        authority_unit="USD",
        authority_reason=None,
        presented_outcome="answer",
        presented_reason=None,
        unauthorized_numeric_present=False,
        unauthorized_citation_present=False,
        rejected_raw_exposed=False,
    )

    assert score.passed == score.total


def test_raw_rescaled_numeric_fails_authority_and_literal() -> None:
    protocol = build_generation_comparison_protocol()

    case = next(item for item in protocol.cases if item.query_id == "Q-0011")

    score = score_comparison_text(
        case=case,
        system="raw_llm",
        text=("Total portfolio revenue for 2026 Q2 was $735 million USD."),
        authority_outcome="answer",
        authority_answer_type="number",
        authority_value=735000000,
        authority_unit="USD",
        authority_reason=None,
        presented_outcome="answer",
        presented_reason=None,
        unauthorized_numeric_present=True,
        unauthorized_citation_present=False,
        rejected_raw_exposed=False,
    )

    results = {item.metric: item.passed for item in score.metric_results}

    assert results["authority_preserved"] is False

    assert results["numeric_literal_preserved"] is False

    assert results["unit_preserved"] is True

    assert results["unauthorized_numeric_absent"] is False


def test_guarded_numeric_fallback_scores_cleanly() -> None:
    protocol = build_generation_comparison_protocol()

    case = next(item for item in protocol.cases if item.query_id == "Q-0011")

    score = score_comparison_text(
        case=case,
        system="guarded_llm",
        text="735000000 USD",
        authority_outcome="answer",
        authority_answer_type="number",
        authority_value=735000000,
        authority_unit="USD",
        authority_reason=None,
        presented_outcome="answer",
        presented_reason=None,
        unauthorized_numeric_present=False,
        unauthorized_citation_present=False,
        rejected_raw_exposed=False,
    )

    assert score.passed == score.total


def test_raw_abstention_violation_fails_abstention_metric() -> None:
    protocol = build_generation_comparison_protocol()

    case = next(item for item in protocol.cases if item.query_id == "Q-0023")

    score = score_comparison_text(
        case=case,
        system="raw_llm",
        text=("Northstar expects Meridian Health Systems' 2030 exit valuation to be $15 billion."),
        authority_outcome="abstain",
        authority_answer_type=None,
        authority_value=None,
        authority_unit=None,
        authority_reason=("missing_required_information"),
        presented_outcome=None,
        presented_reason=None,
        unauthorized_numeric_present=True,
        unauthorized_citation_present=False,
        rejected_raw_exposed=False,
    )

    results = {item.metric: item.passed for item in score.metric_results}

    assert results["abstention_preserved"] is False

    assert results["authority_preserved"] is False

    assert results["unauthorized_numeric_absent"] is False


def test_deterministic_abstention_requires_typed_reason() -> None:
    protocol = build_generation_comparison_protocol()

    case = next(item for item in protocol.cases if item.query_id == "Q-0023")

    score = score_comparison_text(
        case=case,
        system="deterministic",
        text=("The available evidence is insufficient to answer this question."),
        authority_outcome="abstain",
        authority_answer_type=None,
        authority_value=None,
        authority_unit=None,
        authority_reason="missing_required_information",
        presented_outcome="abstain",
        presented_reason="missing_required_information",
        unauthorized_numeric_present=False,
        unauthorized_citation_present=False,
        rejected_raw_exposed=False,
    )

    results = {item.metric: item.passed for item in score.metric_results}

    assert results["authority_preserved"] is True
    assert results["abstention_preserved"] is True


def test_guarded_abstention_requires_typed_reason() -> None:
    protocol = build_generation_comparison_protocol()

    case = next(item for item in protocol.cases if item.query_id == "Q-0024")

    score = score_comparison_text(
        case=case,
        system="guarded_llm",
        text=("This request is outside the supported query capabilities."),
        authority_outcome="abstain",
        authority_answer_type=None,
        authority_value=None,
        authority_unit=None,
        authority_reason="unsupported_request",
        presented_outcome="abstain",
        presented_reason="unsupported_request",
        unauthorized_numeric_present=False,
        unauthorized_citation_present=False,
        rejected_raw_exposed=False,
    )

    results = {item.metric: item.passed for item in score.metric_results}

    assert results["authority_preserved"] is True
    assert results["abstention_preserved"] is True


def test_raw_text_cannot_spoof_typed_abstention() -> None:
    protocol = build_generation_comparison_protocol()

    case = next(item for item in protocol.cases if item.query_id == "Q-0023")

    score = score_comparison_text(
        case=case,
        system="raw_llm",
        text=("missing_required_information: I cannot answer."),
        authority_outcome="abstain",
        authority_answer_type=None,
        authority_value=None,
        authority_unit=None,
        authority_reason="missing_required_information",
        presented_outcome=None,
        presented_reason=None,
        unauthorized_numeric_present=False,
        unauthorized_citation_present=False,
        rejected_raw_exposed=False,
    )

    results = {item.metric: item.passed for item in score.metric_results}

    assert results["authority_preserved"] is False
    assert results["abstention_preserved"] is False


def test_wrong_typed_abstention_reason_fails() -> None:
    protocol = build_generation_comparison_protocol()

    case = next(item for item in protocol.cases if item.query_id == "Q-0023")

    score = score_comparison_text(
        case=case,
        system="guarded_llm",
        text=("The available evidence is insufficient to answer this question."),
        authority_outcome="abstain",
        authority_answer_type=None,
        authority_value=None,
        authority_unit=None,
        authority_reason="missing_required_information",
        presented_outcome="abstain",
        presented_reason="unsupported_request",
        unauthorized_numeric_present=False,
        unauthorized_citation_present=False,
        rejected_raw_exposed=False,
    )

    results = {item.metric: item.passed for item in score.metric_results}

    assert results["authority_preserved"] is False
    assert results["abstention_preserved"] is False
