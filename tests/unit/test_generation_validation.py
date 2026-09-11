from __future__ import annotations

import pytest
from pydantic import ValidationError

from enterprise_genai.generation.contracts import (
    GenerationAuthority,
    GenerationEvidence,
    GenerationProviderMetadata,
    GroundedGenerationRequest,
    RawGeneration,
)
from enterprise_genai.generation.validation import (
    GENERATION_FIDELITY_POLICY_VERSION,
    GenerationFidelityAssessment,
    GenerationViolation,
)


def _request() -> GroundedGenerationRequest:
    return GroundedGenerationRequest(
        question=("What was total portfolio revenue in 2026 Q2?"),
        authority=GenerationAuthority(
            outcome="answer",
            answer_type="number",
            value=735_000_000,
            unit="USD",
            supporting_record_ids=("SQL:VALUE:portfolio_metric_sum",),
            source_fact_ids=("FIN-PC-001-2026Q2",),
        ),
        evidence=(
            GenerationEvidence(
                record_id=("SQL:VALUE:portfolio_metric_sum"),
                tool="sql",
                kind="structured_value",
                content=("Structured operation portfolio_metric_sum returned 735000000 USD."),
                source_fact_ids=("FIN-PC-001-2026Q2",),
            ),
        ),
        allowed_citation_ids=("SQL:VALUE:portfolio_metric_sum",),
    )


def _raw(
    text: str = ("Total portfolio revenue was 735000000 USD."),
) -> RawGeneration:
    return RawGeneration(
        text=text,
        metadata=(
            GenerationProviderMetadata(
                provider_id=("northstar-hf-causal-generation-provider-v1"),
                model_id=("Qwen/Qwen2.5-0.5B-Instruct"),
                model_revision=("7ae557604adf67be50417f59c2c2f167def9a775"),
                device="cpu",
                dtype="float32",
            )
        ),
    )


def _violation(
    *,
    code: str = ("authority_numeric_violation"),
    detail: str = ("Authoritative numeric value was not preserved."),
) -> GenerationViolation:
    return GenerationViolation(
        code=code,
        detail=detail,
        expected="735000000",
        observed="735 million",
    )


def test_fidelity_policy_version_is_frozen() -> None:
    assert GENERATION_FIDELITY_POLICY_VERSION == "northstar-generation-fidelity-v1"


def test_accepted_assessment_exposes_safe_text() -> None:
    request = _request()

    raw = _raw()

    assessment = GenerationFidelityAssessment(
        request=request,
        raw_generation=raw,
        status="accepted",
    )

    assert assessment.request == request

    assert assessment.raw_generation == raw

    assert assessment.safe_text == raw.text

    assert assessment.violations == ()


def test_rejected_assessment_hides_raw_text() -> None:
    assessment = GenerationFidelityAssessment(
        request=_request(),
        raw_generation=_raw("Total portfolio revenue was $735 billion."),
        status="rejected",
        violations=(_violation(),),
    )

    assert assessment.safe_text is None

    assert len(assessment.violations) == 1


def test_accepted_assessment_rejects_violations() -> None:
    with pytest.raises(
        ValidationError,
        match=("Accepted generation cannot contain violations"),
    ):
        GenerationFidelityAssessment(
            request=_request(),
            raw_generation=_raw(),
            status="accepted",
            violations=(_violation(),),
        )


def test_rejected_assessment_requires_violation() -> None:
    with pytest.raises(
        ValidationError,
        match=("Rejected generation requires at least one violation"),
    ):
        GenerationFidelityAssessment(
            request=_request(),
            raw_generation=_raw(),
            status="rejected",
        )


def test_fidelity_policy_override_is_rejected() -> None:
    with pytest.raises(
        ValidationError,
        match=("requires the frozen fidelity policy version"),
    ):
        GenerationFidelityAssessment(
            request=_request(),
            raw_generation=_raw(),
            status="accepted",
            policy_version=("northstar-generation-fidelity-v999"),
        )


def test_duplicate_violations_are_rejected() -> None:
    violation = _violation()

    with pytest.raises(
        ValidationError,
        match=("Generation violations must be unique"),
    ):
        GenerationFidelityAssessment(
            request=_request(),
            raw_generation=_raw(),
            status="rejected",
            violations=(
                violation,
                violation,
            ),
        )


def test_violation_order_must_be_deterministic() -> None:
    numeric = _violation(
        code=("unauthorized_numeric_claim"),
        detail=("Unauthorized numeric claim was introduced."),
    )

    abstention = _violation(
        code=("abstention_semantics_violation"),
        detail=("Generation answered despite abstention authority."),
    )

    with pytest.raises(
        ValidationError,
        match=("deterministic sorted ordering"),
    ):
        GenerationFidelityAssessment(
            request=_request(),
            raw_generation=_raw(),
            status="rejected",
            violations=(
                numeric,
                abstention,
            ),
        )
