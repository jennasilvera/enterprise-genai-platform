from __future__ import annotations

from enterprise_genai.answering.contracts import (
    EvidenceBundle,
    EvidenceRecord,
    StructuredEntityEvidenceData,
    StructuredValueEvidenceData,
)
from enterprise_genai.answering.evaluation import (
    ANSWERING_EVALUATION_PROTOCOL_VERSION,
    PHASE9C4_QUERY_IDS,
    build_phase9c4_protocol,
    compare_answer_outcome,
)
from enterprise_genai.answering.evidence import (
    unsupported_request_bundle,
)
from enterprise_genai.answering.sufficiency import (
    evaluate_sufficiency,
)
from enterprise_genai.answering.synthesis import (
    SynthesisInstruction,
    synthesize_answer,
)
from enterprise_genai.data.evaluation_seed import (
    build_seed_evaluation,
)


def _inputs():
    evaluation = build_seed_evaluation()

    protocols = {item.query_id: item for item in build_phase9c4_protocol(evaluation)}

    cases = {case.query_id: case for case in evaluation.cases}

    return (
        evaluation,
        protocols,
        cases,
    )


def _sufficient_outcome(
    *,
    record: EvidenceRecord,
    protocol,
):
    bundle = EvidenceBundle(
        question="Evaluation question",
        status="completed",
        records=(record,),
    )

    assessment = evaluate_sufficiency(
        bundle=bundle,
        requirements=(protocol.requirements),
    )

    return synthesize_answer(
        assessment=assessment,
        instruction=SynthesisInstruction(
            mode=protocol.synthesis_mode,
            answer_type=(protocol.synthesis_answer_type),
            answer_record_ids=(assessment.supporting_record_ids),
        ),
    )


def test_protocol_version_is_frozen() -> None:
    assert ANSWERING_EVALUATION_PROTOCOL_VERSION == "northstar-answering-evaluation-v1"


def test_protocol_selects_exact_five_controls() -> None:
    evaluation, protocols, _ = _inputs()

    assert (
        tuple(item.query_id for item in build_phase9c4_protocol(evaluation)) == PHASE9C4_QUERY_IDS
    )

    assert tuple(protocols) == (PHASE9C4_QUERY_IDS)


def test_protocol_does_not_embed_expected_answers_or_source_facts() -> None:
    evaluation, _, _ = _inputs()

    payload = "\n".join(item.model_dump_json() for item in build_phase9c4_protocol(evaluation))

    assert "735000000" not in payload
    assert "HelioGrid Energy" not in payload

    assert "answer_source_fact_ids" not in payload

    assert "An authentication defect caused" not in payload


def test_q0001_protocol_uses_query_derived_identifier_requirement() -> None:
    _, protocols, _ = _inputs()

    protocol = protocols["Q-0001"]

    assert protocol.execution_plan is not None

    assert protocol.execution_plan.route_label == "retrieval"

    assert protocol.requirements[0].all_terms == ("ORBIS-IDX-7",)

    assert protocol.comparison_mode == "canonical_retrieval_evidence"


def test_q0023_protocol_requires_absent_exit_valuation_statement() -> None:
    _, protocols, _ = _inputs()

    protocol = protocols["Q-0023"]

    assert protocol.requirements[0].all_terms == ("2030 exit valuation",)

    assert protocol.synthesis_mode is None

    assert protocol.expected_abstention_reason == "missing_required_information"


def test_q0024_protocol_is_pre_execution_unsupported_request() -> None:
    _, protocols, _ = _inputs()

    protocol = protocols["Q-0024"]

    assert protocol.execution_kind == "unsupported_request"

    assert protocol.execution_plan is None

    assert protocol.expected_abstention_reason == "unsupported_request"


def test_text_comparison_scores_canonical_grade3_evidence_not_exact_string() -> None:
    _, protocols, cases = _inputs()

    protocol = protocols["Q-0001"]

    record = EvidenceRecord(
        record_id=("RET:001:EVID-CORE-PC006-RISK-PRIMARY"),
        tool="retrieval",
        kind="retrieval_hit",
        summary=(
            "Orbis Cybersecurity Q2 2026 Risk Review\n"
            "The ORBIS-IDX-7 service experienced "
            "an authentication defect that caused "
            "intermittent identity-validation "
            "failures for a subset of enterprise "
            "tenants."
        ),
        source_fact_ids=("RISK-006",),
        document_id=("DOC-CORE-PC006-RISK-2026Q2"),
        rank=1,
    )

    outcome = _sufficient_outcome(
        record=record,
        protocol=protocol,
    )

    result = compare_answer_outcome(
        case=cases["Q-0001"],
        protocol=protocol,
        outcome=outcome,
    )

    assert result.answer_type_correct is True

    assert result.answer_value_correct is None

    assert result.canonical_text_evidence_correct is True

    assert result.answer_source_provenance_correct is True

    assert result.case_passed is True


def test_text_comparison_rejects_noncanonical_retrieval_record() -> None:
    _, protocols, cases = _inputs()

    protocol = protocols["Q-0001"]

    record = EvidenceRecord(
        record_id=("RET:001:EVID-NONCANONICAL"),
        tool="retrieval",
        kind="retrieval_hit",
        summary=("ORBIS-IDX-7 is mentioned without the canonical defect evidence."),
        source_fact_ids=("RISK-006",),
        document_id="DOC-NONCANONICAL",
        rank=1,
    )

    outcome = _sufficient_outcome(
        record=record,
        protocol=protocol,
    )

    result = compare_answer_outcome(
        case=cases["Q-0001"],
        protocol=protocol,
        outcome=outcome,
    )

    assert result.canonical_text_evidence_correct is False

    assert result.case_passed is False


def test_entity_comparison_requires_exact_normalized_entity_value() -> None:
    _, protocols, cases = _inputs()

    protocol = protocols["Q-0010"]

    record = EvidenceRecord(
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

    outcome = _sufficient_outcome(
        record=record,
        protocol=protocol,
    )

    result = compare_answer_outcome(
        case=cases["Q-0010"],
        protocol=protocol,
        outcome=outcome,
    )

    assert result.answer_value_correct is True
    assert result.case_passed is True


def test_numeric_comparison_requires_value_unit_and_provenance() -> None:
    _, protocols, cases = _inputs()

    protocol = protocols["Q-0011"]

    source_facts = tuple(f"FIN-PC-{index:03d}-2026Q2" for index in range(1, 9))

    record = EvidenceRecord(
        record_id=("SQL:VALUE:portfolio_metric_sum"),
        tool="sql",
        kind="structured_value",
        summary="Portfolio total.",
        source_fact_ids=source_facts,
        data=StructuredValueEvidenceData(
            value=735_000_000,
            unit="USD",
        ),
    )

    outcome = _sufficient_outcome(
        record=record,
        protocol=protocol,
    )

    result = compare_answer_outcome(
        case=cases["Q-0011"],
        protocol=protocol,
        outcome=outcome,
    )

    assert result.answer_value_correct is True
    assert result.unit_correct is True

    assert result.answer_source_provenance_correct is True

    assert result.case_passed is True


def test_numeric_comparison_rejects_wrong_unit() -> None:
    _, protocols, cases = _inputs()

    protocol = protocols["Q-0011"]

    source_facts = tuple(f"FIN-PC-{index:03d}-2026Q2" for index in range(1, 9))

    record = EvidenceRecord(
        record_id=("SQL:VALUE:portfolio_metric_sum"),
        tool="sql",
        kind="structured_value",
        summary="Portfolio total.",
        source_fact_ids=source_facts,
        data=StructuredValueEvidenceData(
            value=735_000_000,
            unit="EUR",
        ),
    )

    outcome = _sufficient_outcome(
        record=record,
        protocol=protocol,
    )

    result = compare_answer_outcome(
        case=cases["Q-0011"],
        protocol=protocol,
        outcome=outcome,
    )

    assert result.answer_value_correct is True
    assert result.unit_correct is False
    assert result.case_passed is False


def test_q0023_comparison_requires_typed_missing_information_abstention() -> None:
    _, protocols, cases = _inputs()

    protocol = protocols["Q-0023"]

    record = EvidenceRecord(
        record_id=("RET:001:EVID-CORE-PC001-RISK-PRIMARY"),
        tool="retrieval",
        kind="retrieval_hit",
        summary=("Meridian customer concentration remains a material risk."),
        source_fact_ids=(
            "CC-001",
            "RISK-001",
        ),
        document_id=("DOC-CORE-PC001-RISK-2026Q2"),
        rank=1,
    )

    bundle = EvidenceBundle(
        question=cases["Q-0023"].question,
        status="completed",
        records=(record,),
    )

    assessment = evaluate_sufficiency(
        bundle=bundle,
        requirements=(protocol.requirements),
    )

    outcome = synthesize_answer(assessment=assessment)

    result = compare_answer_outcome(
        case=cases["Q-0023"],
        protocol=protocol,
        outcome=outcome,
    )

    assert result.abstention_reason_correct is True

    assert result.case_passed is True


def test_q0024_comparison_requires_typed_unsupported_abstention() -> None:
    _, protocols, cases = _inputs()

    protocol = protocols["Q-0024"]

    bundle = unsupported_request_bundle(
        question=cases["Q-0024"].question,
        detail=protocol.unsupported_detail,
    )

    assessment = evaluate_sufficiency(
        bundle=bundle,
        requirements=(),
    )

    outcome = synthesize_answer(assessment=assessment)

    result = compare_answer_outcome(
        case=cases["Q-0024"],
        protocol=protocol,
        outcome=outcome,
    )

    assert result.abstention_reason_correct is True

    assert result.case_passed is True
