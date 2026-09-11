from __future__ import annotations

import pytest
from pydantic import ValidationError

from enterprise_genai.answering.contracts import (
    EvidenceBundle,
    EvidenceRecord,
)
from enterprise_genai.answering.sufficiency import (
    SUFFICIENCY_POLICY_VERSION,
    EvidenceRequirement,
    evaluate_sufficiency,
)


def _retrieval_record(
    *,
    record_id: str = "RET:001:EVID-001",
    summary: str = ("ORBIS-IDX-7 experienced an authentication defect."),
) -> EvidenceRecord:
    return EvidenceRecord(
        record_id=record_id,
        tool="retrieval",
        kind="retrieval_hit",
        summary=summary,
        source_fact_ids=("RISK-006",),
        document_id="DOC-001",
        rank=1,
    )


def _sql_record() -> EvidenceRecord:
    return EvidenceRecord(
        record_id=("SQL:VALUE:portfolio_metric_sum"),
        tool="sql",
        kind="structured_value",
        summary=("Structured operation portfolio_metric_sum returned 735000000 USD."),
        source_fact_ids=(
            "FIN-PC-001-2026Q2",
            "FIN-PC-002-2026Q2",
        ),
    )


def test_requirement_requires_bounded_constraint() -> None:
    with pytest.raises(
        ValidationError,
        match=("at least one bounded matching constraint"),
    ):
        EvidenceRequirement(
            requirement_id="REQ-001",
            description=("Required information."),
        )


def test_requirement_rejects_duplicate_terms_case_insensitively() -> None:
    with pytest.raises(
        ValidationError,
        match="must not contain duplicates",
    ):
        EvidenceRequirement(
            requirement_id="REQ-001",
            description="Incident identifier.",
            all_terms=(
                "ORBIS-IDX-7",
                "orbis-idx-7",
            ),
        )


def test_retrieval_requirement_can_be_sufficient() -> None:
    bundle = EvidenceBundle(
        question=("What defect affected ORBIS-IDX-7?"),
        status="completed",
        records=(_retrieval_record(),),
    )

    requirement = EvidenceRequirement(
        requirement_id="REQ-DEFECT",
        description=("Evidence identifying the ORBIS-IDX-7 defect."),
        allowed_tools=("retrieval",),
        allowed_kinds=("retrieval_hit",),
        all_terms=(
            "ORBIS-IDX-7",
            "authentication defect",
        ),
    )

    assessment = evaluate_sufficiency(
        bundle=bundle,
        requirements=(requirement,),
    )

    assert assessment.status == "sufficient"

    assert assessment.reason == "evidence_supports_answer"

    assert assessment.supporting_record_ids == ("RET:001:EVID-001",)

    assert assessment.policy_version == SUFFICIENCY_POLICY_VERSION


def test_nonempty_retrieval_can_still_be_insufficient() -> None:
    bundle = EvidenceBundle(
        question=("What is the expected 2030 exit valuation?"),
        status="completed",
        records=(
            _retrieval_record(summary=("Meridian reported $98 million of revenue in 2026 Q2.")),
        ),
    )

    requirement = EvidenceRequirement(
        requirement_id=("REQ-2030-EXIT-VALUE"),
        description=("Evidence explicitly stating the expected 2030 exit valuation."),
        allowed_tools=("retrieval",),
        allowed_kinds=("retrieval_hit",),
        all_terms=(
            "2030",
            "exit",
            "valuation",
        ),
    )

    assessment = evaluate_sufficiency(
        bundle=bundle,
        requirements=(requirement,),
    )

    assert assessment.status == "insufficient"

    assert assessment.reason == "missing_required_information"

    assert assessment.supporting_record_ids == ()

    assert assessment.missing_information == (
        ("Evidence explicitly stating the expected 2030 exit valuation."),
    )


def test_empty_completed_bundle_is_no_relevant_evidence() -> None:
    bundle = EvidenceBundle(
        question="Question",
        status="completed",
        records=(),
    )

    requirement = EvidenceRequirement(
        requirement_id="REQ-001",
        description="Required fact.",
        allowed_tools=("retrieval",),
    )

    assessment = evaluate_sufficiency(
        bundle=bundle,
        requirements=(requirement,),
    )

    assert assessment.status == "insufficient"

    assert assessment.reason == "no_relevant_evidence"


def test_unsupported_request_is_typed_insufficiency() -> None:
    bundle = EvidenceBundle(
        question=("What was the customer churn rate?"),
        status="unsupported_request",
        detail=("customer_churn_rate is outside the bounded structured metric set."),
    )

    assessment = evaluate_sufficiency(
        bundle=bundle,
        requirements=(),
    )

    assert assessment.status == "insufficient"

    assert assessment.reason == "unsupported_request"

    assert "customer_churn_rate" in assessment.missing_information[0]


def test_failed_bundle_is_typed_insufficiency() -> None:
    bundle = EvidenceBundle(
        question="Question",
        status="failed",
        detail="retrieval unavailable",
    )

    assessment = evaluate_sufficiency(
        bundle=bundle,
        requirements=(),
    )

    assert assessment.reason == "execution_failed"


def test_blocked_bundle_is_typed_insufficiency() -> None:
    bundle = EvidenceBundle(
        question="Question",
        status="blocked",
        detail=("graph dependency returned no candidates"),
    )

    assessment = evaluate_sufficiency(
        bundle=bundle,
        requirements=(),
    )

    assert assessment.reason == "blocked_dependency"


def test_multiple_requirements_may_use_different_records() -> None:
    bundle = EvidenceBundle(
        question=("What happened and what structured value was observed?"),
        status="completed",
        records=(
            _retrieval_record(),
            _sql_record(),
        ),
    )

    retrieval_requirement = EvidenceRequirement(
        requirement_id=("REQ-INCIDENT"),
        description=("Incident evidence."),
        allowed_tools=("retrieval",),
        all_terms=("ORBIS-IDX-7",),
    )

    sql_requirement = EvidenceRequirement(
        requirement_id=("REQ-STRUCTURED"),
        description=("Structured value evidence."),
        allowed_tools=("sql",),
        allowed_kinds=("structured_value",),
    )

    assessment = evaluate_sufficiency(
        bundle=bundle,
        requirements=(
            retrieval_requirement,
            sql_requirement,
        ),
    )

    assert assessment.status == "sufficient"

    assert assessment.supporting_record_ids == (
        "RET:001:EVID-001",
        ("SQL:VALUE:portfolio_metric_sum"),
    )


def test_completed_bundle_requires_requirements() -> None:
    bundle = EvidenceBundle(
        question="Question",
        status="completed",
        records=(_retrieval_record(),),
    )

    with pytest.raises(
        ValueError,
        match=("requires at least one explicit evidence requirement"),
    ):
        evaluate_sufficiency(
            bundle=bundle,
            requirements=(),
        )
