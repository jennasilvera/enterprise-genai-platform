from __future__ import annotations

from typing import Annotated

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Request,
    status,
)

from enterprise_genai.application import (
    AnsweringServiceProtocol,
    AnswerRequest,
    AnswerServiceResult,
)

router = APIRouter(
    tags=["answering"],
)


def get_answering_service(
    request: Request,
) -> AnsweringServiceProtocol:
    """Resolve the application service installed at startup."""

    service = getattr(
        request.app.state,
        "answering_service",
        None,
    )

    if service is None:
        raise HTTPException(
            status_code=(status.HTTP_503_SERVICE_UNAVAILABLE),
            detail=("answering service unavailable"),
        )

    if not isinstance(
        service,
        AnsweringServiceProtocol,
    ):
        raise RuntimeError(
            "Configured answering service does not satisfy AnsweringServiceProtocol."
        )

    return service


AnsweringServiceDependency = Annotated[
    AnsweringServiceProtocol,
    Depends(get_answering_service),
]


@router.post(
    "/answer",
    response_model=AnswerServiceResult,
    status_code=status.HTTP_200_OK,
    operation_id="answer_question",
)
def answer_question(
    request: AnswerRequest,
    service: AnsweringServiceDependency,
) -> AnswerServiceResult:
    """Return one typed grounded-answer application result."""

    return service.answer(request)
