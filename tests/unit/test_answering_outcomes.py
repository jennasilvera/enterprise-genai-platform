from __future__ import annotations

import pytest
from pydantic import (
    TypeAdapter,
    ValidationError,
)

from enterprise_genai.answering.contracts import (
    EvidenceBundle,
    EvidenceRecord,
    SufficiencyAssessment,
)
from enterprise_genai.answering.outcomes import (
    AbstentionOutcome,
    AnswerOutcome,
    GroundedAnswer,
)


def _retrieval_record() -> EvidenceRecord:
    return EvidenceRecord(
        record_id=("RET:001:EVID-CORE-PC006-RISK-PRIMARY"),
        tool="retrieval",
        kind="retrieval_hit",
        summary=("ORBIS-IDX-7 experienced an authentication defect."),
        source_fact_ids=("RISK-006",),
        document_id=("DOC-CORE-PC006-RISK-2026Q2"),
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


def _sufficient_retrieval_assessment() -> SufficiencyAssessment:
    record = _retrieval_record()

    bundle = EvidenceBundle(
        question=("What defect affected ORBIS-IDX-7?"),
        status="completed",
        records=(record,),
    )

    return SufficiencyAssessment(
        bundle=bundle,
        status="sufficient",
        reason=("evidence_supports_answer"),
        policy_version=("northstar-deterministic-sufficiency-v1"),
        supporting_record_ids=(record.record_id,),
    )


def _sufficient_sql_assessment() -> SufficiencyAssessment:
    record = _sql_record()

    bundle = EvidenceBundle(
        question=("What was total portfolio revenue in 2026 Q2?"),
        status="completed",
        records=(record,),
    )

    return SufficiencyAssessment(
        bundle=bundle,
        status="sufficient",
        reason=("evidence_supports_answer"),
        policy_version=("northstar-deterministic-sufficiency-v1"),
        supporting_record_ids=(record.record_id,),
    )


def _insufficient_assessment() -> SufficiencyAssessment:
    bundle = EvidenceBundle(
        question=("What is Northstar's expected 2030 exit valuation?"),
        status="completed",
        records=(_retrieval_record(),),
    )

    return SufficiencyAssessment(
        bundle=bundle,
        status="insufficient",
        reason=("missing_required_information"),
        policy_version=("northstar-deterministic-sufficiency-v1"),
        missing_information=("Evidence explicitly stating the expected 2030 exit valuation.",),
    )


def test_grounded_text_answer_preserves_exact_provenance() -> None:
    assessment = _sufficient_retrieval_assessment()

    answer = GroundedAnswer(
        assessment=assessment,
        answer_type="text",
        value=("An authentication defect affected ORBIS-IDX-7."),
        supporting_record_ids=(assessment.supporting_record_ids),
        source_fact_ids=("RISK-006",),
        synthesis_version=("northstar-bounded-synthesis-v1"),
    )

    assert answer.outcome == "answer"

    assert answer.source_fact_ids == ("RISK-006",)


def test_numeric_answer_preserves_typed_value_and_unit() -> None:
    assessment = _sufficient_sql_assessment()

    answer = GroundedAnswer(
        assessment=assessment,
        answer_type="number",
        value=735_000_000,
        unit="USD",
        supporting_record_ids=(assessment.supporting_record_ids),
        source_fact_ids=(
            "FIN-PC-001-2026Q2",
            "FIN-PC-002-2026Q2",
        ),
        synthesis_version=("northstar-bounded-synthesis-v1"),
    )

    assert answer.value == 735_000_000

    assert answer.unit == "USD"


def test_entity_list_answer_requires_unique_entities() -> None:
    assessment = _sufficient_retrieval_assessment()

    answer = GroundedAnswer(
        assessment=assessment,
        answer_type="entities",
        value=(
            "Alder Manufacturing",
            "NovaBio Instruments",
        ),
        supporting_record_ids=(assessment.supporting_record_ids),
        source_fact_ids=("RISK-006",),
        synthesis_version=("northstar-bounded-synthesis-v1"),
    )

    assert isinstance(
        answer.value,
        tuple,
    )


def test_answer_type_rejects_wrong_value_shape() -> None:
    assessment = _sufficient_sql_assessment()

    with pytest.raises(
        ValidationError,
        match=("number answers require an int or float"),
    ):
        GroundedAnswer(
            assessment=assessment,
            answer_type="number",
            value="735000000",
            unit="USD",
            supporting_record_ids=(assessment.supporting_record_ids),
            source_fact_ids=(
                "FIN-PC-001-2026Q2",
                "FIN-PC-002-2026Q2",
            ),
            synthesis_version=("northstar-bounded-synthesis-v1"),
        )


def test_nonnumeric_answer_rejects_unit() -> None:
    assessment = _sufficient_retrieval_assessment()

    with pytest.raises(
        ValidationError,
        match=("Only numeric grounded answers may define a unit"),
    ):
        GroundedAnswer(
            assessment=assessment,
            answer_type="text",
            value="Authentication defect.",
            unit="USD",
            supporting_record_ids=(assessment.supporting_record_ids),
            source_fact_ids=("RISK-006",),
            synthesis_version=("northstar-bounded-synthesis-v1"),
        )


def test_grounded_answer_requires_sufficient_assessment() -> None:
    assessment = _insufficient_assessment()

    with pytest.raises(
        ValidationError,
        match=("requires a sufficient assessment"),
    ):
        GroundedAnswer(
            assessment=assessment,
            answer_type="text",
            value="Unsupported answer.",
            supporting_record_ids=(),
            source_fact_ids=("RISK-006",),
            synthesis_version=("northstar-bounded-synthesis-v1"),
        )


def test_grounded_answer_rejects_support_drift() -> None:
    assessment = _sufficient_retrieval_assessment()

    with pytest.raises(
        ValidationError,
        match=("supporting record IDs must exactly match"),
    ):
        GroundedAnswer(
            assessment=assessment,
            answer_type="text",
            value="Authentication defect.",
            supporting_record_ids=("RET:999:OTHER",),
            source_fact_ids=("RISK-006",),
            synthesis_version=("northstar-bounded-synthesis-v1"),
        )


def test_grounded_answer_rejects_source_fact_drift() -> None:
    assessment = _sufficient_retrieval_assessment()

    with pytest.raises(
        ValidationError,
        match=("must exactly equal the canonical provenance"),
    ):
        GroundedAnswer(
            assessment=assessment,
            answer_type="text",
            value="Authentication defect.",
            supporting_record_ids=(assessment.supporting_record_ids),
            source_fact_ids=("FIN-PC-001-2026Q2",),
            synthesis_version=("northstar-bounded-synthesis-v1"),
        )


def test_abstention_mirrors_insufficient_assessment() -> None:
    assessment = _insufficient_assessment()

    outcome = AbstentionOutcome(
        assessment=assessment,
        reason=assessment.reason,
        missing_information=(assessment.missing_information),
        supporting_record_ids=(assessment.supporting_record_ids),
        policy_version=(assessment.policy_version),
    )

    assert outcome.outcome == "abstain"

    adapter = TypeAdapter(AnswerOutcome)

    roundtrip = adapter.validate_python(outcome.model_dump(mode="python"))

    assert isinstance(
        roundtrip,
        AbstentionOutcome,
    )


def test_abstention_rejects_assessment_drift() -> None:
    assessment = _insufficient_assessment()

    with pytest.raises(
        ValidationError,
        match=("Abstention reason must exactly match"),
    ):
        AbstentionOutcome(
            assessment=assessment,
            reason="execution_failed",
            missing_information=(assessment.missing_information),
            supporting_record_ids=(assessment.supporting_record_ids),
            policy_version=(assessment.policy_version),
        )
