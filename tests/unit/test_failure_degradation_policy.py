from __future__ import annotations

from enterprise_genai.answering.contracts import (
    EvidenceBundle,
    EvidenceRecord,
    StructuredValueEvidenceData,
)
from enterprise_genai.answering.sufficiency import (
    EvidenceRequirement,
    evaluate_sufficiency,
)
from enterprise_genai.answering.synthesis import (
    synthesize_answer,
)


def _successful_sql_record() -> EvidenceRecord:
    return EvidenceRecord(
        record_id=("SQL:VALUE:portfolio_revenue"),
        tool="sql",
        kind="structured_value",
        summary=("Structured operation portfolio_revenue returned 735000000 USD."),
        source_fact_ids=("FACT-REVENUE-001",),
        data=(
            StructuredValueEvidenceData(
                value=735000000,
                unit="USD",
            )
        ),
    )


def _sql_requirement() -> EvidenceRequirement:
    return EvidenceRequirement(
        requirement_id="REQ-SQL-001",
        description=("Portfolio revenue."),
        allowed_tools=("sql",),
        allowed_kinds=("structured_value",),
        all_terms=("735000000",),
    )


def test_completed_successful_evidence_can_authorize_answer() -> None:
    bundle = EvidenceBundle(
        question=("What was portfolio revenue?"),
        status="completed",
        records=(_successful_sql_record(),),
    )

    assessment = evaluate_sufficiency(
        bundle=bundle,
        requirements=(_sql_requirement(),),
    )

    assert assessment.status == "sufficient"

    assert assessment.reason == "evidence_supports_answer"

    assert assessment.supporting_record_ids == ("SQL:VALUE:portfolio_revenue",)


def test_failed_bundle_blocks_otherwise_sufficient_surviving_evidence() -> None:
    bundle = EvidenceBundle(
        question=("What happened and what was portfolio revenue?"),
        status="failed",
        records=(_successful_sql_record(),),
        detail=("retrieval: retrieval rpc unavailable"),
    )

    assessment = evaluate_sufficiency(
        bundle=bundle,
        requirements=(_sql_requirement(),),
    )

    assert assessment.status == "insufficient"

    assert assessment.reason == "execution_failed"

    assert assessment.supporting_record_ids == ()

    assert assessment.missing_information == ("retrieval: retrieval rpc unavailable",)


def test_failed_bundle_synthesizes_deterministic_abstention() -> None:
    bundle = EvidenceBundle(
        question=("What happened and what was portfolio revenue?"),
        status="failed",
        records=(_successful_sql_record(),),
        detail=("retrieval: retrieval rpc deadline exceeded"),
    )

    assessment = evaluate_sufficiency(
        bundle=bundle,
        requirements=(_sql_requirement(),),
    )

    outcome = synthesize_answer(assessment=assessment)

    assert outcome.outcome == "abstain"

    assert outcome.reason == "execution_failed"

    assert outcome.supporting_record_ids == ()

    assert outcome.missing_information == ("retrieval: retrieval rpc deadline exceeded",)


def test_failed_status_precedes_requirement_matching() -> None:
    """
    A successful sibling record must never weaken a failed execution
    into a partial answer, even when that record individually satisfies
    every bounded evidence requirement.
    """

    record = _successful_sql_record()

    completed = EvidenceBundle(
        question="Question",
        status="completed",
        records=(record,),
    )

    failed = EvidenceBundle(
        question="Question",
        status="failed",
        records=(record,),
        detail=("graph: simulated graph dependency failure"),
    )

    requirement = _sql_requirement()

    completed_assessment = evaluate_sufficiency(
        bundle=completed,
        requirements=(requirement,),
    )

    failed_assessment = evaluate_sufficiency(
        bundle=failed,
        requirements=(requirement,),
    )

    assert completed_assessment.status == "sufficient"

    assert failed_assessment.status == "insufficient"

    assert failed_assessment.reason == "execution_failed"

    assert failed_assessment.supporting_record_ids == ()


def test_blocked_dependency_also_fails_closed() -> None:
    bundle = EvidenceBundle(
        question="Question",
        status="blocked",
        records=(),
        detail=("graph dependency returned no candidates"),
    )

    assessment = evaluate_sufficiency(
        bundle=bundle,
        requirements=(),
    )

    outcome = synthesize_answer(assessment=assessment)

    assert assessment.status == "insufficient"

    assert assessment.reason == "blocked_dependency"

    assert outcome.outcome == "abstain"

    assert outcome.reason == "blocked_dependency"
