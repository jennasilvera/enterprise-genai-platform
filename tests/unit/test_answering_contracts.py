from __future__ import annotations

import pytest
from pydantic import ValidationError

from enterprise_genai.answering.contracts import (
    EvidenceBundle,
    EvidenceRecord,
    SufficiencyAssessment,
)


def _retrieval_record() -> EvidenceRecord:
    return EvidenceRecord(
        record_id="RET-001",
        tool="retrieval",
        kind="retrieval_hit",
        summary=("Vantage reports weakening new-customer cohort behavior."),
        source_fact_ids=(
            "FIN-PC-005-2025Q2",
            "FIN-PC-005-2026Q2",
            "RISK-005",
        ),
        document_id=("DOC-CORE-PC005-QMR-2026Q2"),
        rank=1,
    )


def test_retrieval_record_preserves_provenance() -> None:
    record = _retrieval_record()

    assert record.tool == "retrieval"

    assert record.rank == 1

    assert record.source_fact_ids == (
        "FIN-PC-005-2025Q2",
        "FIN-PC-005-2026Q2",
        "RISK-005",
    )


def test_retrieval_record_requires_rank() -> None:
    with pytest.raises(
        ValidationError,
        match="requires rank",
    ):
        EvidenceRecord(
            record_id="RET-001",
            tool="retrieval",
            kind="retrieval_hit",
            summary="Evidence text.",
            source_fact_ids=("RISK-005",),
            document_id="DOC-001",
        )


def test_sql_record_rejects_retrieval_metadata() -> None:
    with pytest.raises(
        ValidationError,
        match=("Only retrieval evidence"),
    ):
        EvidenceRecord(
            record_id="SQL-001",
            tool="sql",
            kind="structured_entity",
            summary=("Vantage Retail Analytics has NRR below 100 percent."),
            source_fact_ids=("FIN-PC-005-2026Q2",),
            document_id="DOC-001",
            rank=1,
        )


def test_source_fact_ids_require_sorted_order() -> None:
    with pytest.raises(
        ValidationError,
        match=("deterministic sorted ordering"),
    ):
        EvidenceRecord(
            record_id="SQL-001",
            tool="sql",
            kind="structured_entity",
            summary="Structured evidence.",
            source_fact_ids=(
                "RISK-005",
                "FIN-PC-005-2026Q2",
            ),
        )


def test_unsupported_request_has_no_execution_evidence() -> None:
    with pytest.raises(
        ValidationError,
        match=("must not contain execution evidence"),
    ):
        EvidenceBundle(
            question=("What was the exact customer churn rate?"),
            status="unsupported_request",
            records=(_retrieval_record(),),
            detail=("Metric is outside the bounded structured contract."),
        )


def test_bundle_rejects_duplicate_record_ids() -> None:
    record = _retrieval_record()

    with pytest.raises(
        ValidationError,
        match=("duplicate record IDs"),
    ):
        EvidenceBundle(
            question="Question",
            status="completed",
            records=(
                record,
                record,
            ),
        )


def test_sufficient_assessment_requires_known_support() -> None:
    bundle = EvidenceBundle(
        question="Question",
        status="completed",
        records=(_retrieval_record(),),
    )

    assessment = SufficiencyAssessment(
        bundle=bundle,
        status="sufficient",
        reason=("evidence_supports_answer"),
        policy_version=("northstar-sufficiency-v1"),
        supporting_record_ids=("RET-001",),
    )

    assert assessment.status == "sufficient"


def test_sufficient_assessment_rejects_unknown_support() -> None:
    bundle = EvidenceBundle(
        question="Question",
        status="completed",
        records=(_retrieval_record(),),
    )

    with pytest.raises(
        ValidationError,
        match=("unknown evidence records"),
    ):
        SufficiencyAssessment(
            bundle=bundle,
            status="sufficient",
            reason=("evidence_supports_answer"),
            policy_version=("northstar-sufficiency-v1"),
            supporting_record_ids=("RET-999",),
        )


def test_insufficient_assessment_requires_missing_information() -> None:
    bundle = EvidenceBundle(
        question=("What is Northstar's expected 2030 exit valuation?"),
        status="completed",
        records=(),
    )

    with pytest.raises(
        ValidationError,
        match=("must state what information"),
    ):
        SufficiencyAssessment(
            bundle=bundle,
            status="insufficient",
            reason=("no_relevant_evidence"),
            policy_version=("northstar-sufficiency-v1"),
        )


def test_unsupported_request_is_typed_insufficiency() -> None:
    bundle = EvidenceBundle(
        question=("What was Alder Manufacturing's exact customer churn rate in 2026 Q2?"),
        status="unsupported_request",
        detail=("customer_churn_rate is outside the bounded StructuredQuery metric set."),
    )

    assessment = SufficiencyAssessment(
        bundle=bundle,
        status="insufficient",
        reason="unsupported_request",
        policy_version=("northstar-sufficiency-v1"),
        missing_information=("A supported source for customer_churn_rate.",),
    )

    assert assessment.reason == "unsupported_request"
