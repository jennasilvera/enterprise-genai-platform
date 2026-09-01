import pytest

from enterprise_genai.data.corpus import build_pilot_corpus
from enterprise_genai.data.evaluation_models import (
    EvaluationCase,
    EvaluationSet,
    ExpectedAnswer,
    RelevanceJudgment,
)
from enterprise_genai.data.evaluation_validation import (
    validate_evaluation_references,
)


def _evaluation(
    *,
    document_id: str = "DOC-PC006-INCIDENT-001",
    evidence_id: str = "EVID-PC006-INCIDENT-001",
) -> EvaluationSet:
    return EvaluationSet(
        dataset_version="northstar-v1",
        evaluation_version="northstar-eval-v1",
        cases=[
            EvaluationCase(
                query_id="Q-0001",
                question=("Which company reported an incident involving ORBIS-IDX-7?"),
                query_type="lexical",
                split="development",
                difficulty="easy",
                answerable=True,
                expected_answer=ExpectedAnswer(
                    answer_type="entity",
                    value="Orbis Cybersecurity",
                ),
                required_tools=["lexical_retrieval"],
                relevance_judgments=[
                    RelevanceJudgment(
                        document_id=document_id,
                        evidence_id=evidence_id,
                        relevance_grade=3,
                        rationale="Canonical incident evidence.",
                    )
                ],
            )
        ],
    )


def test_valid_evaluation_references_pass() -> None:
    validate_evaluation_references(
        _evaluation(),
        build_pilot_corpus(),
    )


def test_unknown_document_reference_is_rejected() -> None:
    with pytest.raises(
        ValueError,
        match="unknown document",
    ):
        validate_evaluation_references(
            _evaluation(
                document_id="DOC-UNKNOWN",
            ),
            build_pilot_corpus(),
        )


def test_unknown_evidence_reference_is_rejected() -> None:
    with pytest.raises(
        ValueError,
        match="unknown evidence",
    ):
        validate_evaluation_references(
            _evaluation(
                evidence_id="EVID-UNKNOWN",
            ),
            build_pilot_corpus(),
        )


def test_evidence_parent_mismatch_is_rejected() -> None:
    with pytest.raises(
        ValueError,
        match="evidence belongs to",
    ):
        validate_evaluation_references(
            _evaluation(
                document_id="DOC-PC002-SUPPLIER-001",
                evidence_id="EVID-PC006-INCIDENT-001",
            ),
            build_pilot_corpus(),
        )


def test_dataset_version_mismatch_is_rejected() -> None:
    evaluation = _evaluation().model_copy(update={"dataset_version": "northstar-v2"})

    with pytest.raises(
        ValueError,
        match="dataset versions do not match",
    ):
        validate_evaluation_references(
            evaluation,
            build_pilot_corpus(),
        )
