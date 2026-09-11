from __future__ import annotations

import pytest
from pydantic import ValidationError

from enterprise_genai.answering.contracts import (
    EvidenceBundle,
    EvidenceRecord,
    SufficiencyAssessment,
)
from enterprise_genai.answering.outcomes import (
    AbstentionOutcome,
    GroundedAnswer,
)
from enterprise_genai.generation.contracts import (
    GROUNDING_POLICY_VERSION,
    GenerationAuthority,
    GenerationEvidence,
    GroundedGenerationRequest,
    generation_request_from_outcome,
)


def _record(
    *,
    record_id: str,
    summary: str,
    fact_id: str,
) -> EvidenceRecord:
    return EvidenceRecord(
        record_id=record_id,
        tool="retrieval",
        kind="retrieval_hit",
        summary=summary,
        source_fact_ids=(fact_id,),
        document_id=(f"DOC-{record_id}"),
        rank=1,
    )


def _answer() -> GroundedAnswer:
    selected = _record(
        record_id="RET:001:EVID-A",
        summary=("Authoritative selected evidence."),
        fact_id="FACT-A",
    )

    unselected = _record(
        record_id="RET:002:EVID-B",
        summary=("Retrieved but unselected evidence."),
        fact_id="FACT-B",
    )

    bundle = EvidenceBundle(
        question="Question?",
        status="completed",
        records=(
            selected,
            unselected,
        ),
    )

    assessment = SufficiencyAssessment(
        bundle=bundle,
        status="sufficient",
        reason=("evidence_supports_answer"),
        policy_version=("northstar-test-policy"),
        supporting_record_ids=("RET:001:EVID-A",),
    )

    return GroundedAnswer(
        assessment=assessment,
        answer_type="number",
        value=735_000_000,
        unit="USD",
        supporting_record_ids=("RET:001:EVID-A",),
        source_fact_ids=("FACT-A",),
        synthesis_version=("northstar-test-synthesis"),
    )


def _abstention(
    *,
    with_support: bool,
) -> AbstentionOutcome:
    record = _record(
        record_id="RET:001:EVID-A",
        summary="Partial evidence.",
        fact_id="FACT-A",
    )

    support = ("RET:001:EVID-A",) if with_support else ()

    bundle = EvidenceBundle(
        question="Missing fact?",
        status="completed",
        records=(record,),
    )

    assessment = SufficiencyAssessment(
        bundle=bundle,
        status="insufficient",
        reason=("missing_required_information"),
        policy_version=("northstar-test-policy"),
        supporting_record_ids=support,
        missing_information=("Required future valuation.",),
    )

    return AbstentionOutcome(
        assessment=assessment,
        reason=(assessment.reason),
        missing_information=(assessment.missing_information),
        supporting_record_ids=(assessment.supporting_record_ids),
        policy_version=(assessment.policy_version),
    )


def test_grounding_policy_version_is_frozen() -> None:
    assert GROUNDING_POLICY_VERSION == "northstar-grounded-generation-policy-v1"


def test_answer_request_exposes_only_selected_support() -> None:
    request = generation_request_from_outcome(
        question="Question?",
        outcome=_answer(),
    )

    assert tuple(record.record_id for record in request.evidence) == ("RET:001:EVID-A",)

    assert "Retrieved but unselected evidence." not in request.model_dump_json()


def test_answer_authority_preserves_value_unit_and_provenance() -> None:
    request = generation_request_from_outcome(
        question="Question?",
        outcome=_answer(),
    )

    assert request.authority.outcome == "answer"

    assert request.authority.answer_type == "number"

    assert request.authority.value == 735_000_000

    assert request.authority.unit == "USD"

    assert request.authority.source_fact_ids == ("FACT-A",)


def test_answer_citation_allowlist_equals_selected_support() -> None:
    request = generation_request_from_outcome(
        question="Question?",
        outcome=_answer(),
    )

    assert (
        request.allowed_citation_ids
        == request.authority.supporting_record_ids
        == ("RET:001:EVID-A",)
    )


def test_abstention_authority_cannot_become_an_answer() -> None:
    request = generation_request_from_outcome(
        question="Missing fact?",
        outcome=_abstention(with_support=False),
    )

    assert request.authority.outcome == "abstain"

    assert request.authority.answer_type is None

    assert request.authority.value is None
    assert request.authority.unit is None

    assert request.authority.reason == "missing_required_information"


def test_partial_abstention_exposes_only_selected_partial_support() -> None:
    request = generation_request_from_outcome(
        question="Missing fact?",
        outcome=_abstention(with_support=True),
    )

    assert request.authority.supporting_record_ids == ("RET:001:EVID-A",)

    assert request.authority.source_fact_ids == ("FACT-A",)

    assert len(request.evidence) == 1


def test_request_rejects_evidence_outside_authority_support() -> None:
    evidence = GenerationEvidence(
        record_id="RET:002:EVID-B",
        tool="retrieval",
        kind="retrieval_hit",
        content="Unapproved evidence.",
        source_fact_ids=("FACT-B",),
        document_id="DOC-B",
    )

    authority = GenerationAuthority(
        outcome="answer",
        answer_type="entity",
        value="HelioGrid Energy",
        supporting_record_ids=("RET:001:EVID-A",),
        source_fact_ids=("FACT-A",),
    )

    with pytest.raises(
        ValidationError,
        match=("must exactly match authority-selected support"),
    ):
        GroundedGenerationRequest(
            question="Company?",
            authority=authority,
            evidence=(evidence,),
            allowed_citation_ids=("RET:001:EVID-A",),
        )


def test_request_rejects_citation_allowlist_expansion() -> None:
    evidence = GenerationEvidence(
        record_id="RET:001:EVID-A",
        tool="retrieval",
        kind="retrieval_hit",
        content="Selected evidence.",
        source_fact_ids=("FACT-A",),
        document_id="DOC-A",
    )

    authority = GenerationAuthority(
        outcome="answer",
        answer_type="entity",
        value="HelioGrid Energy",
        supporting_record_ids=("RET:001:EVID-A",),
        source_fact_ids=("FACT-A",),
    )

    with pytest.raises(
        ValidationError,
        match=("Allowed citation IDs must exactly match"),
    ):
        GroundedGenerationRequest(
            question="Company?",
            authority=authority,
            evidence=(evidence,),
            allowed_citation_ids=(
                "RET:001:EVID-A",
                "RET:999:EVID-Z",
            ),
        )


def test_request_rejects_provenance_mismatch() -> None:
    evidence = GenerationEvidence(
        record_id="RET:001:EVID-A",
        tool="retrieval",
        kind="retrieval_hit",
        content="Selected evidence.",
        source_fact_ids=("FACT-B",),
        document_id="DOC-A",
    )

    authority = GenerationAuthority(
        outcome="answer",
        answer_type="entity",
        value="HelioGrid Energy",
        supporting_record_ids=("RET:001:EVID-A",),
        source_fact_ids=("FACT-A",),
    )

    with pytest.raises(
        ValidationError,
        match=("provenance must exactly match"),
    ):
        GroundedGenerationRequest(
            question="Company?",
            authority=authority,
            evidence=(evidence,),
            allowed_citation_ids=("RET:001:EVID-A",),
        )


def test_abstention_authority_rejects_answer_value() -> None:
    with pytest.raises(
        ValidationError,
        match=("Abstention authority cannot define an answer type"),
    ):
        GenerationAuthority(
            outcome="abstain",
            answer_type="text",
            value="Fabricated answer.",
            reason=("missing_required_information"),
            missing_information=("Required information.",),
        )


def test_answer_authority_rejects_value_type_mismatch() -> None:
    with pytest.raises(
        ValidationError,
        match=("number authority requires an int or float value"),
    ):
        GenerationAuthority(
            outcome="answer",
            answer_type="number",
            value="735 million",
            unit="USD",
            supporting_record_ids=("RET:001:EVID-A",),
            source_fact_ids=("FACT-A",),
        )


def test_generation_request_rejects_question_mismatch() -> None:
    with pytest.raises(
        ValueError,
        match=("Generation question must exactly match"),
    ):
        generation_request_from_outcome(
            question="Different question?",
            outcome=_answer(),
        )


def test_request_rejects_policy_version_override() -> None:
    evidence = GenerationEvidence(
        record_id="RET:001:EVID-A",
        tool="retrieval",
        kind="retrieval_hit",
        content="Selected evidence.",
        source_fact_ids=("FACT-A",),
        document_id="DOC-A",
    )

    authority = GenerationAuthority(
        outcome="answer",
        answer_type="entity",
        value="HelioGrid Energy",
        supporting_record_ids=("RET:001:EVID-A",),
        source_fact_ids=("FACT-A",),
    )

    with pytest.raises(
        ValidationError,
        match=("requires the frozen grounding policy version"),
    ):
        GroundedGenerationRequest(
            question="Company?",
            authority=authority,
            evidence=(evidence,),
            allowed_citation_ids=("RET:001:EVID-A",),
            policy_version=("northstar-grounded-generation-policy-v999"),
        )
