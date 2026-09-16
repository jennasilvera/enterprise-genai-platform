from __future__ import annotations

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from enterprise_genai.db.models import HumanReviewRow
from enterprise_genai.human_review.contracts import (
    HumanReviewDecision,
    HumanReviewEvidence,
    HumanReviewRequest,
)
from enterprise_genai.human_review.repository import (
    HumanReviewAlreadyExistsError,
    HumanReviewConflictError,
    HumanReviewNotFoundError,
    HumanReviewRepository,
)


def _engine():
    engine = create_engine("sqlite+pysqlite:///:memory:")

    HumanReviewRow.__table__.create(engine)

    return engine


def _review(
    review_id: str = "review-1",
) -> HumanReviewRequest:
    return HumanReviewRequest(
        review_id=review_id,
        question="What changed at Orbital Systems?",
        answer_type="text",
        answer_value="Orbital Systems increased recurring revenue.",
        supporting_record_ids=("record-1",),
        citation_ids=("record-1",),
        source_fact_ids=("fact-1",),
        evidence=(
            HumanReviewEvidence(
                record_id="record-1",
                tool="retrieval",
                kind="retrieval_hit",
                content="Orbital Systems increased recurring revenue.",
                source_fact_ids=("fact-1",),
                document_id="doc-1",
            ),
        ),
        synthesis_version="synthesis-v1",
        sufficiency_policy_version="sufficiency-v1",
    )


def _decision(
    *,
    disposition: str,
    reviewer: str = "reviewer-1",
    review_id: str = "review-1",
) -> HumanReviewDecision:
    return HumanReviewDecision.model_validate(
        {
            "review_id": review_id,
            "disposition": disposition,
            "reviewer_identity": reviewer,
        }
    )


def test_create_and_reload_awaiting_review() -> None:
    engine = _engine()

    with Session(engine) as session:
        repository = HumanReviewRepository(session)

        created = repository.create(_review())

        session.commit()

    with Session(engine) as session:
        reloaded = HumanReviewRepository(session).get("review-1")

    assert created == reloaded
    assert reloaded.status == "awaiting_review"
    assert reloaded.revision == 1


def test_approval_is_terminal_and_exact_replay_is_idempotent() -> None:
    engine = _engine()

    with Session(engine) as session:
        repository = HumanReviewRepository(session)

        repository.create(_review())
        session.commit()

        decision = _decision(disposition="approve")

        approved = repository.decide(decision)
        session.commit()

        replay = repository.decide(decision)

    assert approved.status == "approved"
    assert approved.decision == "approve"
    assert approved.reviewer_identity == "reviewer-1"
    assert approved.revision == 2
    assert replay == approved


def test_rejection_is_terminal() -> None:
    engine = _engine()

    with Session(engine) as session:
        repository = HumanReviewRepository(session)

        repository.create(_review())
        session.commit()

        rejected = repository.decide(_decision(disposition="reject"))

    assert rejected.status == "rejected"
    assert rejected.decision == "reject"
    assert rejected.revision == 2


@pytest.mark.parametrize(
    (
        "first",
        "second",
    ),
    (
        (
            "approve",
            "reject",
        ),
        (
            "reject",
            "approve",
        ),
    ),
)
def test_conflicting_terminal_decision_is_rejected(
    first: str,
    second: str,
) -> None:
    engine = _engine()

    with Session(engine) as session:
        repository = HumanReviewRepository(session)

        repository.create(_review())
        session.commit()

        repository.decide(_decision(disposition=first))
        session.commit()

        with pytest.raises(
            HumanReviewConflictError,
        ):
            repository.decide(_decision(disposition=second))


def test_same_disposition_different_reviewer_is_conflict() -> None:
    engine = _engine()

    with Session(engine) as session:
        repository = HumanReviewRepository(session)

        repository.create(_review())
        session.commit()

        repository.decide(
            _decision(
                disposition="approve",
                reviewer="reviewer-1",
            )
        )
        session.commit()

        with pytest.raises(
            HumanReviewConflictError,
        ):
            repository.decide(
                _decision(
                    disposition="approve",
                    reviewer="reviewer-2",
                )
            )


def test_unknown_review_decision_is_not_found() -> None:
    engine = _engine()

    with Session(engine) as session:
        repository = HumanReviewRepository(session)

        with pytest.raises(
            HumanReviewNotFoundError,
        ):
            repository.decide(
                _decision(
                    disposition="approve",
                    review_id="missing",
                )
            )


def test_duplicate_review_id_is_rejected() -> None:
    engine = _engine()

    with Session(engine) as session:
        repository = HumanReviewRepository(session)

        repository.create(_review())
        session.commit()

        with pytest.raises(
            HumanReviewAlreadyExistsError,
        ):
            repository.create(_review())
