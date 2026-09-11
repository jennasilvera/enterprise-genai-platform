from __future__ import annotations

from collections.abc import (
    Callable,
)
from time import perf_counter
from uuid import uuid4

import structlog
from starlette.middleware.base import (
    BaseHTTPMiddleware,
    RequestResponseEndpoint,
)
from starlette.requests import Request
from starlette.responses import Response
from structlog.contextvars import (
    bind_contextvars,
    clear_contextvars,
)

from enterprise_genai.observability.metrics import (
    OperationalMetricsRegistry,
)

HTTP_REQUEST_TRACE_VERSION = "northstar-http-request-trace-v1"

REQUEST_ID_HEADER = "X-Request-ID"

logger = structlog.get_logger()


def _new_request_id() -> str:
    return str(uuid4())


def _duration_ms(
    *,
    clock: Callable[
        [],
        float,
    ],
    started_at: float,
) -> float:
    return max(
        0.0,
        (clock() - started_at) * 1000.0,
    )


class RequestObservabilityMiddleware(BaseHTTPMiddleware):
    """Emit privacy-safe structured HTTP lifecycle events.

    The middleware intentionally does not log:

    - request or response bodies;
    - query strings;
    - headers;
    - natural-language questions;
    - retrieved evidence;
    - prompts or model outputs.
    """

    def __init__(
        self,
        app,
        *,
        clock: Callable[
            [],
            float,
        ] = perf_counter,
        request_id_factory: Callable[
            [],
            str,
        ] = _new_request_id,
    ) -> None:
        super().__init__(app)

        self._clock = clock
        self._request_id_factory = request_id_factory

    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        clear_contextvars()

        request_id = self._request_id_factory()

        started_at = self._clock()

        metrics = getattr(
            request.app.state,
            "operational_metrics",
            None,
        )

        if not isinstance(
            metrics,
            OperationalMetricsRegistry,
        ):
            metrics = None

        bind_contextvars(
            request_id=request_id,
            trace_version=(HTTP_REQUEST_TRACE_VERSION),
        )

        safe_fields = {
            "request_id": request_id,
            "trace_version": (HTTP_REQUEST_TRACE_VERSION),
            "method": request.method,
            "path": request.url.path,
        }

        logger.info(
            "http_request_started",
            **safe_fields,
        )

        try:
            response = await call_next(request)

        except Exception as exc:
            elapsed_ms = _duration_ms(
                clock=self._clock,
                started_at=started_at,
            )

            if metrics is not None:
                metrics.record_http_failed(duration_ms=elapsed_ms)

            logger.error(
                "http_request_failed",
                **safe_fields,
                error_type=(type(exc).__name__),
                duration_ms=elapsed_ms,
            )

            raise

        else:
            elapsed_ms = _duration_ms(
                clock=self._clock,
                started_at=started_at,
            )

            if metrics is not None:
                metrics.record_http_completed(
                    status_code=(response.status_code),
                    duration_ms=elapsed_ms,
                )

            response.headers[REQUEST_ID_HEADER] = request_id

            logger.info(
                "http_request_completed",
                **safe_fields,
                status_code=(response.status_code),
                duration_ms=elapsed_ms,
            )

            return response

        finally:
            clear_contextvars()
