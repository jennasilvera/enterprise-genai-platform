from __future__ import annotations

from fastapi.testclient import TestClient

from enterprise_genai.api.main import app
from enterprise_genai.application import (
    AbstainedServiceResult,
    AnswerRequest,
    AwaitingHumanReviewResult,
    HumanReviewRejectedResult,
)
from enterprise_genai.human_review import (
    HumanReviewAlreadyExistsError,
    HumanReviewConflictError,
    HumanReviewDecision,
    HumanReviewNotFoundError,
    HumanReviewRequest,
)


def _review(
    *,
    status: str = "awaiting_review",
) -> HumanReviewRequest:
    payload: dict[str, object] = {
        "review_id": "review-1",
        "question": "What changed?",
        "answer_type": "text",
        "answer_value": "Prepared answer.",
        "supporting_record_ids": ("record-1",),
        "citation_ids": ("record-1",),
        "source_fact_ids": ("fact-1",),
        "evidence": (
            {
                "record_id": "record-1",
                "tool": "retrieval",
                "kind": "retrieval_hit",
                "content": "Prepared answer.",
                "source_fact_ids": ("fact-1",),
                "document_id": "doc-1",
            },
        ),
        "synthesis_version": "synthesis-v1",
        "sufficiency_policy_version": ("sufficiency-v1"),
    }

    if status == "approved":
        payload.update(
            {
                "status": "approved",
                "decision": "approve",
                "reviewer_identity": ("caller-reviewer"),
                "revision": 2,
            }
        )

    elif status == "rejected":
        payload.update(
            {
                "status": "rejected",
                "decision": "reject",
                "reviewer_identity": ("caller-reviewer"),
                "revision": 2,
            }
        )

    return HumanReviewRequest.model_validate(payload)


class FakeReviewedAnsweringService:
    def __init__(self) -> None:
        self.starts: list[
            tuple[
                AnswerRequest,
                str,
            ]
        ] = []

        self.inspections: list[str] = []

        self.decisions: list[HumanReviewDecision] = []

        self.resumes: list[str] = []

        self.start_result = AwaitingHumanReviewResult(review_id="review-1")

        self.inspect_result = _review()

        self.decision_result = _review(status="approved")

        self.resume_result = HumanReviewRejectedResult(
            review_id="review-1",
            reviewer_identity=("caller-reviewer"),
        )

        self.start_error: Exception | None = None
        self.inspect_error: Exception | None = None
        self.decision_error: Exception | None = None
        self.resume_error: Exception | None = None

    def start(
        self,
        request: AnswerRequest,
        *,
        review_id: str,
    ):
        self.starts.append(
            (
                request,
                review_id,
            )
        )

        if self.start_error is not None:
            raise self.start_error

        return self.start_result

    def inspect(
        self,
        review_id: str,
    ) -> HumanReviewRequest:
        self.inspections.append(review_id)

        if self.inspect_error is not None:
            raise self.inspect_error

        return self.inspect_result

    def decide(
        self,
        decision: HumanReviewDecision,
    ) -> HumanReviewRequest:
        self.decisions.append(decision)

        if self.decision_error is not None:
            raise self.decision_error

        return self.decision_result

    def resume(
        self,
        review_id: str,
    ):
        self.resumes.append(review_id)

        if self.resume_error is not None:
            raise self.resume_error

        return self.resume_result


def _clear_reviewed_service() -> None:
    if hasattr(
        app.state,
        "reviewed_answering_service",
    ):
        delattr(
            app.state,
            "reviewed_answering_service",
        )


def test_reviewed_start_requires_installed_service() -> None:
    _clear_reviewed_service()

    with TestClient(app) as client:
        response = client.post(
            "/reviewed-answers",
            json={
                "question": "Question?",
                "review_id": "review-1",
            },
        )

    assert response.status_code == 503
    assert response.json() == {"detail": ("reviewed answering service unavailable")}


def test_reviewed_start_returns_202_before_generation() -> None:
    service = FakeReviewedAnsweringService()

    app.state.reviewed_answering_service = service

    try:
        with TestClient(app) as client:
            response = client.post(
                "/reviewed-answers",
                json={
                    "question": "  What changed?  ",
                    "review_id": "review-1",
                },
            )
    finally:
        _clear_reviewed_service()

    assert response.status_code == 202

    assert response.json() == {
        "status": "awaiting_review",
        "review_id": "review-1",
        "revision": 1,
        "contract_version": ("northstar-human-review-contract-v1"),
    }

    assert len(service.starts) == 1

    request, review_id = service.starts[0]

    assert request.question == "What changed?"
    assert review_id == "review-1"


def test_reviewed_start_abstention_returns_200() -> None:
    service = FakeReviewedAnsweringService()

    service.start_result = AbstainedServiceResult(
        presentation_source="deterministic",
        generation_fidelity=("not_applicable"),
        text=("The available evidence is insufficient."),
        reason=("missing_required_information"),
        detail="Required fact missing.",
    )

    app.state.reviewed_answering_service = service

    try:
        with TestClient(app) as client:
            response = client.post(
                "/reviewed-answers",
                json={
                    "question": "Question?",
                    "review_id": "review-1",
                },
            )
    finally:
        _clear_reviewed_service()

    assert response.status_code == 200
    assert response.json()["status"] == ("abstained")


def test_duplicate_review_maps_to_conflict() -> None:
    service = FakeReviewedAnsweringService()

    service.start_error = HumanReviewAlreadyExistsError("duplicate")

    app.state.reviewed_answering_service = service

    try:
        with TestClient(app) as client:
            response = client.post(
                "/reviewed-answers",
                json={
                    "question": "Question?",
                    "review_id": "review-1",
                },
            )
    finally:
        _clear_reviewed_service()

    assert response.status_code == 409

    assert response.json() == {"detail": "human review already exists"}


def test_inspect_returns_durable_review() -> None:
    service = FakeReviewedAnsweringService()

    app.state.reviewed_answering_service = service

    try:
        with TestClient(app) as client:
            response = client.get("/reviewed-answers/review-1")
    finally:
        _clear_reviewed_service()

    assert response.status_code == 200

    body = response.json()

    assert body["review_id"] == "review-1"
    assert body["status"] == "awaiting_review"
    assert body["answer_value"] == ("Prepared answer.")

    assert service.inspections == ["review-1"]


def test_missing_review_maps_to_404() -> None:
    service = FakeReviewedAnsweringService()

    service.inspect_error = HumanReviewNotFoundError("missing")

    app.state.reviewed_answering_service = service

    try:
        with TestClient(app) as client:
            response = client.get("/reviewed-answers/missing")
    finally:
        _clear_reviewed_service()

    assert response.status_code == 404

    assert response.json() == {"detail": "human review not found"}


def test_decision_uses_path_review_id_and_caller_identity() -> None:
    service = FakeReviewedAnsweringService()

    app.state.reviewed_answering_service = service

    try:
        with TestClient(app) as client:
            response = client.post(
                "/reviewed-answers/review-1/decision",
                json={
                    "disposition": "approve",
                    "reviewer_identity": ("caller-reviewer"),
                },
            )
    finally:
        _clear_reviewed_service()

    assert response.status_code == 200
    assert response.json()["status"] == ("approved")

    assert len(service.decisions) == 1

    decision = service.decisions[0]

    assert decision.review_id == "review-1"
    assert decision.disposition == "approve"
    assert decision.reviewer_identity == ("caller-reviewer")


def test_conflicting_decision_maps_to_409() -> None:
    service = FakeReviewedAnsweringService()

    service.decision_error = HumanReviewConflictError("conflict")

    app.state.reviewed_answering_service = service

    try:
        with TestClient(app) as client:
            response = client.post(
                "/reviewed-answers/review-1/decision",
                json={
                    "disposition": "reject",
                    "reviewer_identity": ("caller-reviewer"),
                },
            )
    finally:
        _clear_reviewed_service()

    assert response.status_code == 409

    assert response.json() == {"detail": ("human review decision conflict")}


def test_resume_serializes_human_rejection() -> None:
    service = FakeReviewedAnsweringService()

    app.state.reviewed_answering_service = service

    try:
        with TestClient(app) as client:
            response = client.post("/reviewed-answers/review-1/resume")
    finally:
        _clear_reviewed_service()

    assert response.status_code == 200

    assert response.json() == {
        "status": "human_rejected",
        "review_id": "review-1",
        "reviewer_identity": ("caller-reviewer"),
        "reason": "human_rejected",
        "revision": 2,
        "contract_version": ("northstar-human-review-contract-v1"),
    }

    assert service.resumes == ["review-1"]


def test_reviewed_openapi_preserves_status_discriminators() -> None:
    with TestClient(app) as client:
        response = client.get("/openapi.json")

    assert response.status_code == 200

    schema = response.json()

    start = schema["paths"]["/reviewed-answers"]["post"]["responses"]["202"]["content"][
        "application/json"
    ]["schema"]

    assert start["discriminator"]["propertyName"] == "status"

    assert set(start["discriminator"]["mapping"]) == {
        "awaiting_review",
        "abstained",
    }

    start_200 = schema["paths"]["/reviewed-answers"]["post"]["responses"]["200"]["content"][
        "application/json"
    ]["schema"]

    assert start_200["$ref"] == "#/components/schemas/AbstainedServiceResult"

    resume = schema["paths"]["/reviewed-answers/{review_id}/resume"]["post"]["responses"]["200"][
        "content"
    ]["application/json"]["schema"]

    assert resume["discriminator"]["propertyName"] == "status"

    assert set(resume["discriminator"]["mapping"]) == {
        "awaiting_review",
        "human_rejected",
        "answered",
    }
