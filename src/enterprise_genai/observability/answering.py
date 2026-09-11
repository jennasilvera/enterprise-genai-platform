from __future__ import annotations

from collections.abc import Callable

from structlog.contextvars import (
    get_contextvars,
)

ANSWER_SERVICE_TRACE_VERSION = "northstar-answer-service-trace-v1"


def duration_ms(
    *,
    clock: Callable[
        [],
        float,
    ],
    started_at: float,
) -> float:
    """Return a non-negative monotonic stage duration."""

    return max(
        0.0,
        (clock() - started_at) * 1000.0,
    )


def request_trace_fields() -> dict[
    str,
    object,
]:
    """Return only safe correlation metadata from contextvars."""

    context = get_contextvars()

    fields: dict[
        str,
        object,
    ] = {
        "answer_trace_version": (ANSWER_SERVICE_TRACE_VERSION),
    }

    request_id = context.get("request_id")

    if (
        isinstance(
            request_id,
            str,
        )
        and request_id.strip()
    ):
        fields["request_id"] = request_id

    return fields
