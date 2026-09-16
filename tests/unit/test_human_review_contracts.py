from __future__ import annotations

import pytest
from pydantic import ValidationError

from enterprise_genai.human_review.contracts import (
    HUMAN_REVIEW_CONTRACT_VERSION,
    HumanReviewDecision,
    HumanReviewEvidence,
    HumanReviewRequest,
)


def _evidence() -> HumanReviewEvidence:
    return HumanReviewEvidence(
        record_id="record-1",
        tool="retrieval",
        kind="retrieval_hit",
        content="Orbital Systems increased recurring revenue.",
        source_fact_ids=("fact-1",),
        document_id="doc-1",
    )


def _review(
    **updates: object,
) -> HumanReviewRequest:
    payload: dict[str, object] = {
        "review_id": "review-1",
        "question": "What changed at Orbital Systems?",
        "answer_type": "text",
        "answer_value": "Orbital Systems increased recurring revenue.",
        "unit": None,
        "supporting_record_ids": ("record-1",),
        "citation_ids": ("record-1",),
        "source_fact_ids": ("fact-1",),
        "evidence": (_evidence(),),
        "synthesis_version": "synthesis-v1",
        "sufficiency_policy_version": "sufficiency-v1",
    }

    payload.update(updates)

    return HumanReviewRequest.model_validate(payload)


def test_awaiting_review_contract_is_frozen_and_bounded() -> None:
    review = _review()

    assert review.status == "awaiting_review"
    assert review.decision is None
    assert review.reviewer_identity is None
    assert review.revision == 1
    assert review.contract_version == HUMAN_REVIEW_CONTRACT_VERSION


def test_terminal_approval_requires_matching_decision_and_reviewer() -> None:
    review = _review(
        status="approved",
        decision="approve",
        reviewer_identity="reviewer-1",
        revision=2,
    )

    assert review.status == "approved"
    assert review.decision == "approve"


@pytest.mark.parametrize(
    "updates",
    (
        {"citation_ids": ("record-other",)},
        {"source_fact_ids": ("fact-other",)},
        {
            "status": "approved",
            "decision": "reject",
            "reviewer_identity": "reviewer-1",
            "revision": 2,
        },
        {
            "status": "rejected",
            "decision": "reject",
            "reviewer_identity": None,
            "revision": 2,
        },
    ),
)
def test_review_contract_rejects_invalid_authority_or_lifecycle(
    updates: dict[str, object],
) -> None:
    with pytest.raises(ValidationError):
        _review(**updates)


def test_review_evidence_requires_sorted_provenance() -> None:
    with pytest.raises(
        ValidationError,
        match="deterministic sorted ordering",
    ):
        HumanReviewEvidence(
            record_id="record-1",
            tool="retrieval",
            kind="retrieval_hit",
            content="Selected evidence.",
            source_fact_ids=(
                "fact-2",
                "fact-1",
            ),
            document_id="doc-1",
        )


def test_review_decision_requires_nonempty_caller_asserted_identity() -> None:
    with pytest.raises(ValidationError):
        HumanReviewDecision(
            review_id="review-1",
            disposition="approve",
            reviewer_identity=" ",
        )
