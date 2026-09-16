from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Literal

import grpc
import structlog
from fastapi import (
    FastAPI,
    Request,
    Response,
    status,
)
from pydantic import BaseModel

from enterprise_genai.api.answer import (
    router as answer_router,
)
from enterprise_genai.api.reviewed_answer import (
    router as reviewed_answer_router,
)
from enterprise_genai.application.serving import (
    build_serving_assembly,
)
from enterprise_genai.core.config import (
    get_settings,
)
from enterprise_genai.core.logging import (
    configure_logging,
)
from enterprise_genai.db.session import (
    check_database,
    engine,
)
from enterprise_genai.observability import (
    OperationalMetricsRegistry,
    RequestObservabilityMiddleware,
)
from enterprise_genai.rpc.retrieval.v1 import (
    retrieval_pb2_grpc,
)
from enterprise_genai.rpc.retrieval.v1.client import (
    GrpcRetrievalExecutor,
)
from enterprise_genai.rpc.retrieval.v1.readiness import (
    grpc_channel_is_ready,
)

settings = get_settings()
configure_logging(settings.log_level)

logger = structlog.get_logger()


class LiveHealthResponse(BaseModel):
    status: Literal["ok"]

    service: str

    environment: str


class ReadyHealthResponse(BaseModel):
    status: Literal[
        "ready",
        "not_ready",
    ]

    database: Literal[
        "ok",
        "unavailable",
    ]

    answering: Literal[
        "disabled",
        "ready",
        "unavailable",
    ]


@asynccontextmanager
async def lifespan(
    _app: FastAPI,
) -> AsyncIterator[None]:
    logger.info(
        "service_starting",
        service=settings.app_name,
        environment=(settings.environment),
        answering_enabled=(settings.answering_enabled),
        retrieval_mode=(settings.retrieval_mode),
    )

    installed_answering_service = False

    grpc_channel: grpc.Channel | None = None

    metrics_registry = OperationalMetricsRegistry()

    _app.state.operational_metrics = metrics_registry

    _app.state.answering_status = "disabled"

    if settings.answering_enabled:
        logger.info("answering_service_initializing")

        try:
            if settings.retrieval_mode == "grpc":
                target = settings.retrieval_grpc_target

                if target is None:
                    raise RuntimeError("validated gRPC retrieval target is unavailable")

                grpc_channel = grpc.insecure_channel(target)

                if not grpc_channel_is_ready(
                    grpc_channel,
                    timeout_seconds=(settings.retrieval_grpc_startup_timeout_seconds),
                ):
                    raise RuntimeError("gRPC retrieval dependency unavailable during startup")

                stub = retrieval_pb2_grpc.RetrievalServiceStub(grpc_channel)

                retrieval_executor = GrpcRetrievalExecutor(
                    stub,
                    deadline_seconds=(settings.retrieval_grpc_deadline_seconds),
                )

                assembly = build_serving_assembly(
                    engine=engine,
                    metrics_registry=(metrics_registry),
                    retrieval_executor=(retrieval_executor),
                )

            else:
                assembly = build_serving_assembly(
                    engine=engine,
                    metrics_registry=(metrics_registry),
                )

        except Exception:
            if grpc_channel is not None:
                grpc_channel.close()

                grpc_channel = None

            _app.state.answering_status = "unavailable"

            logger.exception("answering_service_initialization_failed")

        else:
            _app.state.answering_assembly = assembly

            _app.state.answering_service = assembly.service

            reviewed_service = getattr(
                assembly,
                "reviewed_service",
                None,
            )

            if reviewed_service is not None:
                _app.state.reviewed_answering_service = reviewed_service

            _app.state.answering_status = "ready"

            installed_answering_service = True

            logger.info("answering_service_ready")

    try:
        yield

    finally:
        if grpc_channel is not None:
            grpc_channel.close()

        if installed_answering_service:
            if hasattr(
                _app.state,
                "answering_service",
            ):
                delattr(
                    _app.state,
                    "answering_service",
                )

            if hasattr(
                _app.state,
                "answering_assembly",
            ):
                delattr(
                    _app.state,
                    "answering_assembly",
                )

            if hasattr(
                _app.state,
                "reviewed_answering_service",
            ):
                delattr(
                    _app.state,
                    "reviewed_answering_service",
                )

        if hasattr(
            _app.state,
            "answering_status",
        ):
            delattr(
                _app.state,
                "answering_status",
            )

        if hasattr(
            _app.state,
            "operational_metrics",
        ):
            delattr(
                _app.state,
                "operational_metrics",
            )

        logger.info(
            "service_stopping",
            service=settings.app_name,
        )


app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(RequestObservabilityMiddleware)

app.include_router(answer_router)
app.include_router(reviewed_answer_router)


@app.get(
    "/health/live",
    response_model=(LiveHealthResponse),
)
async def live_health() -> LiveHealthResponse:
    """Return process-level liveness information."""

    return LiveHealthResponse(
        status="ok",
        service=settings.app_name,
        environment=(settings.environment),
    )


@app.get(
    "/health/ready",
    response_model=(ReadyHealthResponse),
)
def ready_health(
    request: Request,
    response: Response,
) -> ReadyHealthResponse:
    """Return dependency-level readiness information."""

    database_status: Literal[
        "ok",
        "unavailable",
    ] = "ok"

    ready = True

    try:
        check_database()
    except Exception:
        logger.exception("database_readiness_failed")

        database_status = "unavailable"

        ready = False

    answering_status = getattr(
        request.app.state,
        "answering_status",
        "disabled",
    )

    if answering_status not in {
        "disabled",
        "ready",
        "unavailable",
    }:
        raise RuntimeError(f"Unexpected answering readiness state: {answering_status!r}.")

    if answering_status == "unavailable":
        ready = False

    if not ready:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    return ReadyHealthResponse(
        status=("ready" if ready else "not_ready"),
        database=database_status,
        answering=answering_status,
    )
