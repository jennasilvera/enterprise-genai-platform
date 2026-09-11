from __future__ import annotations

from enterprise_genai.generation.contracts import (
    GenerationAuthority,
    GenerationEvidence,
    GenerationProviderMetadata,
    GroundedGenerationRequest,
    RawGeneration,
)
from enterprise_genai.generation.validation import (
    assess_generation_fidelity,
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


def _numeric_request() -> GroundedGenerationRequest:
    facts = (
        "FIN-PC-001-2026Q2",
        "FIN-PC-002-2026Q2",
        "FIN-PC-003-2026Q2",
        "FIN-PC-004-2026Q2",
        "FIN-PC-005-2026Q2",
        "FIN-PC-006-2026Q2",
        "FIN-PC-007-2026Q2",
        "FIN-PC-008-2026Q2",
    )

    record_id = "SQL:VALUE:portfolio_metric_sum"

    return GroundedGenerationRequest(
        question=("What was total portfolio revenue in 2026 Q2?"),
        authority=GenerationAuthority(
            outcome="answer",
            answer_type="number",
            value=735_000_000,
            unit="USD",
            supporting_record_ids=(record_id,),
            source_fact_ids=facts,
        ),
        evidence=(
            GenerationEvidence(
                record_id=record_id,
                tool="sql",
                kind="structured_value",
                content=("Structured operation portfolio_metric_sum returned 735000000 USD."),
                source_fact_ids=facts,
            ),
        ),
        allowed_citation_ids=(record_id,),
    )


def _entity_request() -> GroundedGenerationRequest:
    record_id = "SQL:ENTITY:PC-004"

    facts = (
        "FIN-PC-004-2025Q2",
        "FIN-PC-004-2026Q2",
    )

    return GroundedGenerationRequest(
        question=(
            "Which portfolio company had the highest year-over-year revenue growth in 2026 Q2?"
        ),
        authority=GenerationAuthority(
            outcome="answer",
            answer_type="entity",
            value="HelioGrid Energy",
            supporting_record_ids=(record_id,),
            source_fact_ids=facts,
        ),
        evidence=(
            GenerationEvidence(
                record_id=record_id,
                tool="sql",
                kind="structured_entity",
                content=("HelioGrid Energy (PC-004) was returned by portfolio_growth_rank."),
                source_fact_ids=facts,
            ),
        ),
        allowed_citation_ids=(record_id,),
    )


def _abstention_request(
    *,
    reason: str,
    question: str,
    detail: str,
) -> GroundedGenerationRequest:
    return GroundedGenerationRequest(
        question=question,
        authority=GenerationAuthority(
            outcome="abstain",
            reason=reason,
            missing_information=(detail,),
        ),
    )


def test_exact_numeric_authority_is_accepted() -> None:
    assessment = assess_generation_fidelity(
        request=_numeric_request(),
        raw_generation=_raw("Total portfolio revenue for 2026 Q2 was 735000000 USD."),
    )

    assert assessment.status == "accepted"

    assert assessment.safe_text is not None

    assert assessment.violations == ()


def test_real_q0011_rescaled_number_is_rejected() -> None:
    assessment = assess_generation_fidelity(
        request=_numeric_request(),
        raw_generation=_raw("Total portfolio revenue for 2026 Q2 was $735 million USD."),
    )

    assert assessment.status == "rejected"

    codes = {violation.code for violation in assessment.violations}

    assert "authority_numeric_violation" in codes

    assert "unauthorized_numeric_claim" in codes

    assert assessment.safe_text is None


def test_missing_numeric_unit_is_rejected() -> None:
    assessment = assess_generation_fidelity(
        request=_numeric_request(),
        raw_generation=_raw("Total portfolio revenue for 2026 Q2 was 735000000."),
    )

    assert assessment.status == "rejected"

    assert assessment.violations[0].code == "authority_unit_violation"


def test_real_q0010_entity_generation_is_accepted() -> None:
    assessment = assess_generation_fidelity(
        request=_entity_request(),
        raw_generation=_raw(
            "HelioGrid Energy (PC-004) had the highest year-over-year revenue growth in 2026 Q2."
        ),
    )

    assert assessment.status == "accepted"


def test_wrong_entity_is_rejected() -> None:
    assessment = assess_generation_fidelity(
        request=_entity_request(),
        raw_generation=_raw("Alder Manufacturing had the highest revenue growth in 2026 Q2."),
    )

    assert assessment.status == "rejected"

    assert {violation.code for violation in assessment.violations} == {"authority_entity_violation"}


def test_real_q0023_abstention_hallucination_is_rejected() -> None:
    request = _abstention_request(
        reason=("missing_required_information"),
        question=("What is Northstar's expected 2030 exit valuation for Meridian Health Systems?"),
        detail=(
            "Evidence explicitly stating "
            "Northstar's expected 2030 "
            "exit valuation for Meridian "
            "Health Systems."
        ),
    )

    assessment = assess_generation_fidelity(
        request=request,
        raw_generation=_raw(
            "Northstar expects Meridian Health Systems' 2030 exit valuation to be $15 billion."
        ),
    )

    assert assessment.status == "rejected"

    codes = {violation.code for violation in assessment.violations}

    assert "abstention_semantics_violation" in codes

    assert "unauthorized_numeric_claim" in codes


def test_real_q0024_unsupported_claim_is_rejected() -> None:
    request = _abstention_request(
        reason="unsupported_request",
        question=("What was Alder Manufacturing's exact customer churn rate in 2026 Q2?"),
        detail=("customer_churn_rate is outside the bounded StructuredQuery metric set."),
    )

    assessment = assess_generation_fidelity(
        request=request,
        raw_generation=_raw("Alder Manufacturing had no known customer churn rate for Q2 2026."),
    )

    assert assessment.status == "rejected"

    assert {violation.code for violation in assessment.violations} == {
        "abstention_semantics_violation"
    }


def test_unauthorized_citation_is_rejected() -> None:
    assessment = assess_generation_fidelity(
        request=_entity_request(),
        raw_generation=_raw("HelioGrid Energy was the highest-growth company [SQL:ENTITY:PC-999]."),
    )

    assert assessment.status == "rejected"

    assert "unauthorized_citation" in {violation.code for violation in assessment.violations}


def test_allowlisted_citation_is_permitted() -> None:
    assessment = assess_generation_fidelity(
        request=_entity_request(),
        raw_generation=_raw("HelioGrid Energy was the highest-growth company SQL:ENTITY:PC-004."),
    )

    assert assessment.status == "accepted"
