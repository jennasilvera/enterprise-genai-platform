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
from enterprise_genai.generation.guarded import (
    SAFE_GENERATION_POLICY_VERSION,
    SafeGenerationResult,
    render_deterministic_authority,
    resolve_safe_generation,
)
from enterprise_genai.generation.validation import (
    GenerationFidelityAssessment,
    GenerationViolation,
)


def _metadata() -> GenerationProviderMetadata:
    return GenerationProviderMetadata(
        provider_id=("northstar-hf-causal-generation-provider-v1"),
        model_id=("Qwen/Qwen2.5-0.5B-Instruct"),
        model_revision=("7ae557604adf67be50417f59c2c2f167def9a775"),
        device="cpu",
        dtype="float32",
    )


def _raw(
    text: str,
) -> RawGeneration:
    return RawGeneration(
        text=text,
        metadata=_metadata(),
    )


def _number_request() -> GroundedGenerationRequest:
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
                record_id="SQL:VALUE:portfolio_metric_sum",
                tool="sql",
                kind="structured_value",
                content=("Structured operation portfolio_metric_sum returned 735000000 USD."),
                source_fact_ids=("FIN-PC-001-2026Q2",),
            ),
        ),
        allowed_citation_ids=("SQL:VALUE:portfolio_metric_sum",),
    )


def _rejected(
    *,
    request: GroundedGenerationRequest,
    raw_text: str,
    code: str = ("authority_numeric_violation"),
) -> GenerationFidelityAssessment:
    return GenerationFidelityAssessment(
        request=request,
        raw_generation=_raw(raw_text),
        status="rejected",
        violations=(
            GenerationViolation(
                code=code,
                detail=("Generation violated deterministic authority."),
                expected="authority",
                observed=raw_text,
            ),
        ),
    )


def test_safe_generation_policy_version_is_frozen() -> None:
    assert SAFE_GENERATION_POLICY_VERSION == "northstar-safe-generation-presentation-v1"


def test_accepted_model_generation_is_preserved() -> None:
    request = _number_request()

    raw = _raw("Total portfolio revenue was 735000000 USD.")

    fidelity = GenerationFidelityAssessment(
        request=request,
        raw_generation=raw,
        status="accepted",
    )

    result = resolve_safe_generation(fidelity)

    assert result.source == "model_generation"

    assert result.text == raw.text

    assert result.citation_ids == request.allowed_citation_ids


def test_rejected_numeric_generation_falls_back_exactly() -> None:
    request = _number_request()

    fidelity = _rejected(
        request=request,
        raw_text=("Total portfolio revenue was $735 million USD."),
    )

    result = resolve_safe_generation(fidelity)

    assert result.source == "deterministic_fallback"

    assert result.text == "735000000 USD"

    assert "$735 million" not in result.text


def test_rejected_text_generation_returns_exact_authority() -> None:
    authority_text = (
        "Orbis Cybersecurity Q2 2026 "
        "Risk Review\n"
        "The ORBIS-IDX-7 service "
        "experienced an authentication "
        "defect."
    )

    request = GroundedGenerationRequest(
        question=("What defect affected ORBIS-IDX-7?"),
        authority=GenerationAuthority(
            outcome="answer",
            answer_type="text",
            value=authority_text,
            supporting_record_ids=("RET:001:EVID-CORE",),
            source_fact_ids=("RISK-006",),
        ),
        evidence=(
            GenerationEvidence(
                record_id="RET:001:EVID-CORE",
                tool="retrieval",
                kind="retrieval_hit",
                content=authority_text,
                source_fact_ids=("RISK-006",),
            ),
        ),
        allowed_citation_ids=("RET:001:EVID-CORE",),
    )

    fidelity = _rejected(
        request=request,
        raw_text=("A paraphrased Orbis answer."),
        code="authority_text_violation",
    )

    result = resolve_safe_generation(fidelity)

    assert result.text == authority_text

    assert result.source == "deterministic_fallback"


def test_missing_information_abstention_hides_hallucination() -> None:
    request = GroundedGenerationRequest(
        question=("What is Northstar's expected 2030 exit valuation for Meridian Health Systems?"),
        authority=GenerationAuthority(
            outcome="abstain",
            reason=("missing_required_information"),
            missing_information=(
                "Evidence explicitly stating "
                "Northstar's expected 2030 "
                "exit valuation for Meridian "
                "Health Systems.",
            ),
        ),
    )

    raw_text = "Northstar expects Meridian Health Systems' 2030 exit valuation to be $15 billion."

    fidelity = _rejected(
        request=request,
        raw_text=raw_text,
        code=("abstention_semantics_violation"),
    )

    result = resolve_safe_generation(fidelity)

    assert result.source == "deterministic_fallback"

    assert "$15 billion" not in result.text

    assert "insufficient to answer" in result.text

    assert "Evidence explicitly stating" in result.text


def test_unsupported_request_fallback_makes_no_data_claim() -> None:
    request = GroundedGenerationRequest(
        question=("What was Alder Manufacturing's exact customer churn rate in 2026 Q2?"),
        authority=GenerationAuthority(
            outcome="abstain",
            reason="unsupported_request",
            missing_information=(
                "customer_churn_rate is outside the bounded StructuredQuery metric set.",
            ),
        ),
    )

    fidelity = _rejected(
        request=request,
        raw_text=("Alder Manufacturing had no known customer churn rate for Q2 2026."),
        code=("abstention_semantics_violation"),
    )

    result = resolve_safe_generation(fidelity)

    assert "outside the supported query capabilities" in result.text

    assert "no known customer churn rate" not in result.text


def test_entities_render_deterministically() -> None:
    authority = GenerationAuthority(
        outcome="answer",
        answer_type="entities",
        value=(
            "Alder Manufacturing",
            "NovaBio Instruments",
        ),
        supporting_record_ids=("GRAPH:NODES",),
        source_fact_ids=(
            "CS-003",
            "CS-011",
        ),
    )

    assert render_deterministic_authority(authority) == ("Alder Manufacturing, NovaBio Instruments")


def test_boolean_renders_deterministically() -> None:
    authority = GenerationAuthority(
        outcome="answer",
        answer_type="boolean",
        value=True,
        supporting_record_ids=("SQL:VALUE:test",),
        source_fact_ids=("FACT-001",),
    )

    assert render_deterministic_authority(authority) == "true"


def test_rejected_model_text_cannot_be_marked_as_model_generation() -> None:
    request = _number_request()

    fidelity = _rejected(
        request=request,
        raw_text=("$735 million USD"),
    )

    with pytest.raises(
        ValidationError,
        match=("Model generation can be presented only after"),
    ):
        SafeGenerationResult(
            request=request,
            fidelity=fidelity,
            source="model_generation",
            text=(fidelity.raw_generation.text),
            citation_ids=(request.allowed_citation_ids),
        )


def test_fallback_cannot_be_replaced_with_arbitrary_text() -> None:
    request = _number_request()

    fidelity = _rejected(
        request=request,
        raw_text="$735 million USD",
    )

    with pytest.raises(
        ValidationError,
        match=("fallback text must equal"),
    ):
        SafeGenerationResult(
            request=request,
            fidelity=fidelity,
            source=("deterministic_fallback"),
            text="Something else",
            citation_ids=(request.allowed_citation_ids),
        )
