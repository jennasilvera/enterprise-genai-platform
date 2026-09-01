from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Literal

import structlog
from fastapi import FastAPI, Response, status
from pydantic import BaseModel

from enterprise_genai.core.config import get_settings
from enterprise_genai.core.logging import configure_logging
from enterprise_genai.db.session import check_database

settings = get_settings()
configure_logging(settings.log_level)

logger = structlog.get_logger()


class LiveHealthResponse(BaseModel):
    status: Literal["ok"]
    service: str
    environment: str


class ReadyHealthResponse(BaseModel):
    status: Literal["ready", "not_ready"]
    database: Literal["ok", "unavailable"]


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    logger.info(
        "service_starting",
        service=settings.app_name,
        environment=settings.environment,
    )

    yield

    logger.info(
        "service_stopping",
        service=settings.app_name,
    )


app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    lifespan=lifespan,
)


@app.get("/health/live", response_model=LiveHealthResponse)
async def live_health() -> LiveHealthResponse:
    """Return process-level liveness information."""

    return LiveHealthResponse(
        status="ok",
        service=settings.app_name,
        environment=settings.environment,
    )


@app.get("/health/ready", response_model=ReadyHealthResponse)
def ready_health(response: Response) -> ReadyHealthResponse:
    """Return dependency-level readiness information."""

    try:
        check_database()
    except Exception:
        logger.exception("database_readiness_failed")

        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

        return ReadyHealthResponse(
            status="not_ready",
            database="unavailable",
        )

    return ReadyHealthResponse(
        status="ready",
        database="ok",
    )
