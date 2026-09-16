from __future__ import annotations

import json
from typing import Any

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from enterprise_genai.db.models import HumanReviewRow
from enterprise_genai.human_review.contracts import (
    HumanReviewDecision,
    HumanReviewEvidence,
    HumanReviewRequest,
)


class HumanReviewRepositoryError(RuntimeError):
    """Base error for durable human-review state."""


class HumanReviewNotFoundError(HumanReviewRepositoryError):
    """Requested review ID does not exist."""


class HumanReviewAlreadyExistsError(HumanReviewRepositoryError):
    """A review with the requested stable ID already exists."""


class HumanReviewConflictError(HumanReviewRepositoryError):
    """A conflicting terminal review decision was attempted."""


def _canonical_json(
    value: Any,
) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        separators=(
            ",",
            ":",
        ),
        sort_keys=True,
    )


def _load_json(
    value: str,
) -> Any:
    return json.loads(value)


def _row_to_review(
    row: HumanReviewRow,
) -> HumanReviewRequest:
    evidence_payload = _load_json(row.evidence_json)

    return HumanReviewRequest(
        review_id=row.review_id,
        question=row.question,
        status=row.status,
        answer_type=row.answer_type,
        answer_value=_load_json(row.answer_value_json),
        unit=row.unit,
        supporting_record_ids=tuple(_load_json(row.supporting_record_ids_json)),
        citation_ids=tuple(_load_json(row.citation_ids_json)),
        source_fact_ids=tuple(_load_json(row.source_fact_ids_json)),
        evidence=tuple(HumanReviewEvidence.model_validate(item) for item in evidence_payload),
        synthesis_version=row.synthesis_version,
        sufficiency_policy_version=(row.sufficiency_policy_version),
        decision=row.decision,
        reviewer_identity=row.reviewer_identity,
        revision=row.revision,
        contract_version=row.contract_version,
    )


def _new_row(
    review: HumanReviewRequest,
) -> HumanReviewRow:
    return HumanReviewRow(
        review_id=review.review_id,
        contract_version=review.contract_version,
        question=review.question,
        status=review.status,
        answer_type=review.answer_type,
        answer_value_json=_canonical_json(review.answer_value),
        unit=review.unit,
        supporting_record_ids_json=_canonical_json(review.supporting_record_ids),
        citation_ids_json=_canonical_json(review.citation_ids),
        source_fact_ids_json=_canonical_json(review.source_fact_ids),
        evidence_json=_canonical_json([item.model_dump(mode="json") for item in review.evidence]),
        synthesis_version=review.synthesis_version,
        sufficiency_policy_version=(review.sufficiency_policy_version),
        decision=review.decision,
        reviewer_identity=review.reviewer_identity,
        revision=review.revision,
    )


class HumanReviewRepository:
    """Transactional SQLAlchemy repository for human-review lifecycle state."""

    def __init__(
        self,
        session: Session,
    ) -> None:
        self._session = session

    def _load_row(
        self,
        review_id: str,
    ) -> HumanReviewRow | None:
        statement = (
            select(HumanReviewRow)
            .where(HumanReviewRow.review_id == review_id)
            .execution_options(populate_existing=True)
        )

        return self._session.execute(statement).scalar_one_or_none()

    def create(
        self,
        review: HumanReviewRequest,
    ) -> HumanReviewRequest:
        if review.status != "awaiting_review":
            raise ValueError("New human-review records must begin awaiting_review.")

        if self._load_row(review.review_id) is not None:
            raise HumanReviewAlreadyExistsError(
                f"Human review {review.review_id!r} already exists."
            )

        self._session.add(_new_row(review))

        self._session.flush()

        return self.get(review.review_id)

    def get(
        self,
        review_id: str,
    ) -> HumanReviewRequest:
        row = self._load_row(review_id)

        if row is None:
            raise HumanReviewNotFoundError(f"Human review {review_id!r} was not found.")

        return _row_to_review(row)

    def decide(
        self,
        decision: HumanReviewDecision,
    ) -> HumanReviewRequest:
        terminal_status = "approved" if decision.disposition == "approve" else "rejected"

        statement = (
            update(HumanReviewRow)
            .where(
                HumanReviewRow.review_id == decision.review_id,
                HumanReviewRow.status == "awaiting_review",
                HumanReviewRow.revision == 1,
            )
            .values(
                status=terminal_status,
                decision=decision.disposition,
                reviewer_identity=(decision.reviewer_identity),
                revision=2,
            )
            .execution_options(synchronize_session=False)
        )

        result = self._session.execute(statement)

        if result.rowcount == 1:
            self._session.flush()

            return self.get(decision.review_id)

        existing = self._load_row(decision.review_id)

        if existing is None:
            raise HumanReviewNotFoundError(f"Human review {decision.review_id!r} was not found.")

        persisted = _row_to_review(existing)

        if (
            persisted.decision == decision.disposition
            and persisted.reviewer_identity == decision.reviewer_identity
        ):
            return persisted

        raise HumanReviewConflictError("Human review already has a conflicting terminal decision.")
