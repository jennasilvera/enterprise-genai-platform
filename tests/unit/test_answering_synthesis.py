from __future__ import annotations

import pytest
from pydantic import ValidationError

from enterprise_genai.answering.contracts import (
    EvidenceBundle,
    EvidenceRecord,
    GraphEntityEvidenceData,
    StructuredEntityEvidenceData,
    StructuredValueEvidenceData,
    SufficiencyAssessment,
)
from enterprise_genai.answering.outcomes import (
    AbstentionOutcome,
    GroundedAnswer,
)
from enterprise_genai.answering.synthesis import (
    SYNTHESIS_VERSION,
    SynthesisInstruction,
    synthesize_answer,
)


def _assessment(
    *records: EvidenceRecord,
    supporting_record_ids: tuple[
        str,
        ...,
    ],
) -> SufficiencyAssessment:
    return SufficiencyAssessment(
        bundle=EvidenceBundle(
            question="Bounded test question?",
            status="completed",
            records=records,
        ),
        status="sufficient",
        reason="evidence_supports_answer",
        policy_version=("northstar-deterministic-sufficiency-v1"),
        supporting_record_ids=(supporting_record_ids),
    )


def _retrieval() -> EvidenceRecord:
    return EvidenceRecord(
        record_id="RET:001:EVID-001",
        tool="retrieval",
        kind="retrieval_hit",
        summary=("An authentication defect affected ORBIS-IDX-7."),
        source_fact_ids=("RISK-006",),
        document_id="DOC-001",
        rank=1,
    )


def _scalar() -> EvidenceRecord:
    return EvidenceRecord(
        record_id=("SQL:VALUE:portfolio_metric_sum"),
        tool="sql",
        kind="structured_value",
        summary="Structured total.",
        source_fact_ids=(
            "FIN-PC-001-2026Q2",
            "FIN-PC-002-2026Q2",
        ),
        data=StructuredValueEvidenceData(
            value=735_000_000,
            unit="USD",
        ),
    )


def _sql_entity() -> EvidenceRecord:
    return EvidenceRecord(
        record_id="SQL:ENTITY:PC-004",
        tool="sql",
        kind="structured_entity",
        summary="HelioGrid result.",
        source_fact_ids=(
            "FIN-PC-004-2025Q2",
            "FIN-PC-004-2026Q2",
        ),
        data=StructuredEntityEvidenceData(
            entity_id="PC-004",
            entity_name="HelioGrid Energy",
            score=0.35294117647058826,
            score_unit="ratio",
        ),
    )


def _graph_entity(
    *,
    company_id: str,
    name: str,
) -> EvidenceRecord:
    return EvidenceRecord(
        record_id=(f"GRAPH:NODE:company:{company_id}"),
        tool="graph",
        kind="graph_entity",
        summary=(f"company {name} ({company_id})."),
        source_fact_ids=(company_id,),
        data=GraphEntityEvidenceData(
            entity_type="company",
            entity_id=company_id,
            entity_name=name,
        ),
    )


def test_insufficient_assessment_returns_typed_abstention() -> None:
    assessment = SufficiencyAssessment(
        bundle=EvidenceBundle(
            question="Unsupported question?",
            status="completed",
            records=(_retrieval(),),
        ),
        status="insufficient",
        reason=("missing_required_information"),
        policy_version=("northstar-deterministic-sufficiency-v1"),
        missing_information=("Required evidence is absent.",),
    )

    outcome = synthesize_answer(assessment=assessment)

    assert isinstance(
        outcome,
        AbstentionOutcome,
    )

    assert outcome.reason == "missing_required_information"


def test_sufficient_assessment_requires_instruction() -> None:
    record = _retrieval()

    assessment = _assessment(
        record,
        supporting_record_ids=(record.record_id,),
    )

    with pytest.raises(
        ValueError,
        match=("requires an explicit synthesis instruction"),
    ):
        synthesize_answer(assessment=assessment)


def test_retrieval_text_is_exact_selected_source_text() -> None:
    record = _retrieval()

    assessment = _assessment(
        record,
        supporting_record_ids=(record.record_id,),
    )

    outcome = synthesize_answer(
        assessment=assessment,
        instruction=SynthesisInstruction(
            mode="retrieval_text",
            answer_type="text",
            answer_record_ids=(record.record_id,),
        ),
    )

    assert isinstance(
        outcome,
        GroundedAnswer,
    )

    assert outcome.value == record.summary

    assert outcome.source_fact_ids == ("RISK-006",)

    assert outcome.synthesis_version == SYNTHESIS_VERSION


def test_structured_number_preserves_machine_readable_value_and_unit() -> None:
    record = _scalar()

    assessment = _assessment(
        record,
        supporting_record_ids=(record.record_id,),
    )

    outcome = synthesize_answer(
        assessment=assessment,
        instruction=SynthesisInstruction(
            mode="structured_value",
            answer_type="number",
            answer_record_ids=(record.record_id,),
        ),
    )

    assert isinstance(
        outcome,
        GroundedAnswer,
    )

    assert outcome.value == 735_000_000
    assert outcome.unit == "USD"


def test_structured_entity_returns_entity_name() -> None:
    record = _sql_entity()

    assessment = _assessment(
        record,
        supporting_record_ids=(record.record_id,),
    )

    outcome = synthesize_answer(
        assessment=assessment,
        instruction=SynthesisInstruction(
            mode="entity_name",
            answer_type="entity",
            answer_record_ids=(record.record_id,),
        ),
    )

    assert isinstance(
        outcome,
        GroundedAnswer,
    )

    assert outcome.value == "HelioGrid Energy"


def test_graph_entities_return_deterministic_entity_tuple() -> None:
    alder = _graph_entity(
        company_id="PC-002",
        name="Alder Manufacturing",
    )

    nova = _graph_entity(
        company_id="PC-008",
        name="NovaBio Instruments",
    )

    assessment = _assessment(
        alder,
        nova,
        supporting_record_ids=(
            alder.record_id,
            nova.record_id,
        ),
    )

    outcome = synthesize_answer(
        assessment=assessment,
        instruction=SynthesisInstruction(
            mode="entity_names",
            answer_type="entities",
            answer_record_ids=(
                alder.record_id,
                nova.record_id,
            ),
        ),
    )

    assert isinstance(
        outcome,
        GroundedAnswer,
    )

    assert outcome.value == (
        "Alder Manufacturing",
        "NovaBio Instruments",
    )


def test_answer_record_must_be_sufficiency_selected() -> None:
    retrieval = _retrieval()
    scalar = _scalar()

    assessment = _assessment(
        retrieval,
        scalar,
        supporting_record_ids=(retrieval.record_id,),
    )

    with pytest.raises(
        ValueError,
        match=("records not selected by the sufficiency assessment"),
    ):
        synthesize_answer(
            assessment=assessment,
            instruction=SynthesisInstruction(
                mode="structured_value",
                answer_type="number",
                answer_record_ids=(scalar.record_id,),
            ),
        )


def test_provenance_uses_all_selected_support_not_only_answer_record() -> None:
    graph = _graph_entity(
        company_id="PC-008",
        name="NovaBio Instruments",
    )

    sql = EvidenceRecord(
        record_id="SQL:ENTITY:PC-008",
        tool="sql",
        kind="structured_entity",
        summary="NovaBio lower revenue.",
        source_fact_ids=(
            "FIN-PC-002-2026Q2",
            "FIN-PC-008-2026Q2",
        ),
        data=StructuredEntityEvidenceData(
            entity_id="PC-008",
            entity_name="NovaBio Instruments",
        ),
    )

    assessment = _assessment(
        graph,
        sql,
        supporting_record_ids=tuple(
            sorted(
                (
                    graph.record_id,
                    sql.record_id,
                )
            )
        ),
    )

    outcome = synthesize_answer(
        assessment=assessment,
        instruction=SynthesisInstruction(
            mode="entity_name",
            answer_type="entity",
            answer_record_ids=(sql.record_id,),
        ),
    )

    assert isinstance(
        outcome,
        GroundedAnswer,
    )

    assert outcome.value == "NovaBio Instruments"

    assert outcome.source_fact_ids == (
        "FIN-PC-002-2026Q2",
        "FIN-PC-008-2026Q2",
        "PC-008",
    )


def test_retrieval_mode_rejects_structured_record() -> None:
    record = _scalar()

    assessment = _assessment(
        record,
        supporting_record_ids=(record.record_id,),
    )

    with pytest.raises(
        ValueError,
        match=("requires retrieval evidence"),
    ):
        synthesize_answer(
            assessment=assessment,
            instruction=SynthesisInstruction(
                mode="retrieval_text",
                answer_type="text",
                answer_record_ids=(record.record_id,),
            ),
        )


def test_numeric_synthesis_does_not_parse_string_values() -> None:
    record = EvidenceRecord(
        record_id="SQL:VALUE:test",
        tool="sql",
        kind="structured_value",
        summary="Returned 123.",
        source_fact_ids=("FACT-001",),
        data=StructuredValueEvidenceData(
            value="123",
        ),
    )

    assessment = _assessment(
        record,
        supporting_record_ids=(record.record_id,),
    )

    with pytest.raises(
        ValueError,
        match=("machine-readable numeric value"),
    ):
        synthesize_answer(
            assessment=assessment,
            instruction=SynthesisInstruction(
                mode="structured_value",
                answer_type="number",
                answer_record_ids=(record.record_id,),
            ),
        )


def test_instruction_rejects_mode_answer_type_mismatch() -> None:
    with pytest.raises(
        ValidationError,
        match=("requires answer_type='entity'"),
    ):
        SynthesisInstruction(
            mode="entity_name",
            answer_type="text",
            answer_record_ids=("SQL:ENTITY:PC-004",),
        )
