from __future__ import annotations

from typing import (
    Annotated,
    Protocol,
    runtime_checkable,
)

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Request,
    Response,
    status,
)
from pydantic import Field

from enterprise_genai.answering.contracts import (
    FrozenAnsweringModel,
    NonEmptyStr,
)
from enterprise_genai.application import (
    AbstainedServiceResult,
    AnsweredServiceResult,
    AnswerRequest,
    AwaitingHumanReviewResult,
    HumanReviewRejectedResult,
    ReviewedAnswerResumeResult,
    ReviewedAnswerStartResult,
)
from enterprise_genai.human_review import (
    HumanReviewAlreadyExistsError,
    HumanReviewConflictError,
    HumanReviewDecision,
    HumanReviewDisposition,
    HumanReviewNotFoundError,
    HumanReviewRequest,
)


class ReviewedAnswerStartRequest(FrozenAnsweringModel):
    """Public request for deterministic preparation plus durable review pause."""

    question: NonEmptyStr

    review_id: NonEmptyStr


class HumanReviewDecisionRequest(FrozenAnsweringModel):
    """Caller-asserted human disposition.

    reviewer_identity is metadata supplied by the caller. This API does
    not authenticate or authorize that identity.
    """

    disposition: HumanReviewDisposition

    reviewer_identity: NonEmptyStr


ReviewedAnswerStartResponse = Annotated[
    (AwaitingHumanReviewResult | AbstainedServiceResult),
    Field(discriminator="status"),
]

ReviewedAnswerResumeResponse = Annotated[
    (AwaitingHumanReviewResult | HumanReviewRejectedResult | AnsweredServiceResult),
    Field(discriminator="status"),
]


@runtime_checkable
class ReviewedAnsweringServiceProtocol(Protocol):
    """Structural API dependency for the reviewed-answer workflow."""

    def start(
        self,
        request: AnswerRequest,
        *,
        review_id: str,
    ) -> ReviewedAnswerStartResult: ...

    def inspect(
        self,
        review_id: str,
    ) -> HumanReviewRequest: ...

    def decide(
        self,
        decision: HumanReviewDecision,
    ) -> HumanReviewRequest: ...

    def resume(
        self,
        review_id: str,
    ) -> ReviewedAnswerResumeResult: ...


router = APIRouter(
    prefix="/reviewed-answers",
    tags=["human-review"],
)


def get_reviewed_answering_service(
    request: Request,
) -> ReviewedAnsweringServiceProtocol:
    """Resolve the reviewed workflow service installed at startup."""

    service = getattr(
        request.app.state,
        "reviewed_answering_service",
        None,
    )

    if service is None:
        raise HTTPException(
            status_code=(status.HTTP_503_SERVICE_UNAVAILABLE),
            detail=("reviewed answering service unavailable"),
        )

    if not isinstance(
        service,
        ReviewedAnsweringServiceProtocol,
    ):
        raise RuntimeError(
            "Configured reviewed answering service "
            "does not satisfy "
            "ReviewedAnsweringServiceProtocol."
        )

    return service


ReviewedAnsweringServiceDependency = Annotated[
    ReviewedAnsweringServiceProtocol,
    Depends(get_reviewed_answering_service),
]


def _review_http_error(
    exc: Exception,
) -> HTTPException:
    if isinstance(
        exc,
        HumanReviewNotFoundError,
    ):
        return HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="human review not found",
        )

    if isinstance(
        exc,
        HumanReviewAlreadyExistsError,
    ):
        return HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="human review already exists",
        )

    if isinstance(
        exc,
        HumanReviewConflictError,
    ):
        return HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="human review decision conflict",
        )

    raise TypeError("unsupported human-review repository error")


@router.post(
    "",
    response_model=ReviewedAnswerStartResponse,
    status_code=status.HTTP_202_ACCEPTED,
    responses={
        status.HTTP_200_OK: {
            "model": AbstainedServiceResult,
            "description": (
                "Deterministic pre-review abstention; no human-review record is created."
            ),
        },
    },
    operation_id="start_reviewed_answer",
)
def start_reviewed_answer(
    request: ReviewedAnswerStartRequest,
    response: Response,
    service: ReviewedAnsweringServiceDependency,
) -> ReviewedAnswerStartResponse:
    """Prepare an answer and return control before generation."""

    try:
        result = service.start(
            AnswerRequest(question=request.question),
            review_id=request.review_id,
        )
    except HumanReviewAlreadyExistsError as exc:
        raise _review_http_error(exc) from exc

    if isinstance(
        result,
        AbstainedServiceResult,
    ):
        response.status_code = status.HTTP_200_OK

    return result


@router.get(
    "/{review_id}",
    response_model=HumanReviewRequest,
    status_code=status.HTTP_200_OK,
    operation_id="inspect_reviewed_answer",
)
def inspect_reviewed_answer(
    review_id: str,
    service: ReviewedAnsweringServiceDependency,
) -> HumanReviewRequest:
    """Return the durable prepared review and its lifecycle state."""

    try:
        return service.inspect(review_id)
    except HumanReviewNotFoundError as exc:
        raise _review_http_error(exc) from exc


@router.post(
    "/{review_id}/decision",
    response_model=HumanReviewRequest,
    status_code=status.HTTP_200_OK,
    operation_id="decide_reviewed_answer",
)
def decide_reviewed_answer(
    review_id: str,
    request: HumanReviewDecisionRequest,
    service: ReviewedAnsweringServiceDependency,
) -> HumanReviewRequest:
    """Persist a separately supplied caller-asserted human decision."""

    decision = HumanReviewDecision(
        review_id=review_id,
        disposition=request.disposition,
        reviewer_identity=(request.reviewer_identity),
    )

    try:
        return service.decide(decision)
    except (
        HumanReviewNotFoundError,
        HumanReviewConflictError,
    ) as exc:
        raise _review_http_error(exc) from exc


@router.post(
    "/{review_id}/resume",
    response_model=ReviewedAnswerResumeResponse,
    status_code=status.HTTP_200_OK,
    operation_id="resume_reviewed_answer",
)
def resume_reviewed_answer(
    review_id: str,
    service: ReviewedAnsweringServiceDependency,
) -> ReviewedAnswerResumeResponse:
    """Resume only from durable review state after an external decision."""

    try:
        return service.resume(review_id)
    except HumanReviewNotFoundError as exc:
        raise _review_http_error(exc) from exc
