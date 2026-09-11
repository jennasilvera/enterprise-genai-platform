from __future__ import annotations

from concurrent.futures import (
    ThreadPoolExecutor,
)

import pytest

from enterprise_genai.observability.metrics import (
    OPERATIONAL_METRICS_VERSION,
    OperationalMetricsRegistry,
)


def _pairs(
    values,
) -> dict[
    str,
    int,
]:
    return dict(values)


def test_operational_metrics_version_is_frozen() -> None:
    assert OPERATIONAL_METRICS_VERSION == "northstar-operational-metrics-v1"


def test_registry_records_bounded_http_and_answer_metrics() -> None:
    metrics = OperationalMetricsRegistry(
        latency_buckets_ms=(
            10.0,
            100.0,
        )
    )

    metrics.record_http_completed(
        status_code=200,
        duration_ms=7.0,
    )

    metrics.record_http_completed(
        status_code=503,
        duration_ms=150.0,
    )

    metrics.record_answer_completed(
        status="answered",
        presentation_source=("deterministic_fallback"),
        generation_fidelity="rejected",
        abstention_reason=None,
        generation_invoked=True,
        stage_durations_ms={
            "generation": 80.0,
        },
        tool_durations_ms={
            "retrieval": 6.0,
        },
        total_duration_ms=95.0,
    )

    metrics.record_answer_completed(
        status="abstained",
        presentation_source="deterministic",
        generation_fidelity=("not_applicable"),
        abstention_reason=("missing_required_information"),
        generation_invoked=False,
        stage_durations_ms={},
        tool_durations_ms={
            "sql": 3.0,
        },
        total_duration_ms=8.0,
    )

    snapshot = metrics.snapshot()

    assert snapshot.http_requests_total == 2
    assert snapshot.http_failures_total == 0

    assert _pairs(snapshot.http_status_classes) == {
        "2xx": 1,
        "5xx": 1,
    }

    assert snapshot.answer_requests_total == 2
    assert snapshot.answers_total == 1
    assert snapshot.abstentions_total == 1
    assert snapshot.answer_failures_total == 0

    assert snapshot.generation_invocations_total == 1

    assert snapshot.generation_accepted_total == 0

    assert snapshot.generation_rejected_total == 1

    assert snapshot.deterministic_fallback_total == 1

    assert _pairs(snapshot.abstention_reasons) == {
        "missing_required_information": 1,
    }

    assert _pairs(snapshot.tool_invocations) == {
        "retrieval": 1,
        "sql": 1,
    }

    assert snapshot.http_latency_ms.count == 2

    assert snapshot.http_latency_ms.cumulative_counts == (
        1,
        1,
    )

    assert snapshot.http_latency_ms.overflow_count == 1

    assert snapshot.generation_latency_ms.count == 1

    tool_latency = dict(snapshot.tool_latency_ms)

    assert tool_latency["retrieval"].count == 1

    assert tool_latency["sql"].count == 1

    assert tool_latency["graph"].count == 0


def test_registry_records_failure_paths() -> None:
    metrics = OperationalMetricsRegistry()

    metrics.record_http_failed(duration_ms=12.0)

    metrics.record_answer_failed(
        stage="generation",
        generation_invoked=True,
        total_duration_ms=15.0,
    )

    snapshot = metrics.snapshot()

    assert snapshot.http_requests_total == 1
    assert snapshot.http_failures_total == 1

    assert _pairs(snapshot.http_status_classes) == {
        "5xx": 1,
    }

    assert snapshot.answer_requests_total == 1
    assert snapshot.answer_failures_total == 1

    assert snapshot.generation_invocations_total == 1

    assert _pairs(snapshot.answer_failure_stages) == {
        "generation": 1,
    }


def test_registry_rejects_invalid_metric_inputs() -> None:
    metrics = OperationalMetricsRegistry()

    with pytest.raises(
        ValueError,
        match="HTTP status",
    ):
        metrics.record_http_completed(
            status_code=700,
            duration_ms=1.0,
        )

    with pytest.raises(
        ValueError,
        match="non-negative",
    ):
        metrics.record_http_failed(duration_ms=-1.0)

    with pytest.raises(
        ValueError,
        match="Unsupported tool",
    ):
        metrics.record_answer_completed(
            status="answered",
            presentation_source=("model_generation"),
            generation_fidelity=("accepted"),
            abstention_reason=None,
            generation_invoked=True,
            stage_durations_ms={
                "generation": 1.0,
            },
            tool_durations_ms={
                "unknown": 1.0,
            },
            total_duration_ms=2.0,
        )


def test_registry_updates_are_thread_safe() -> None:
    metrics = OperationalMetricsRegistry()

    def record_one(
        _index: int,
    ) -> None:
        metrics.record_http_completed(
            status_code=200,
            duration_ms=2.0,
        )

        metrics.record_answer_completed(
            status="answered",
            presentation_source=("model_generation"),
            generation_fidelity=("accepted"),
            abstention_reason=None,
            generation_invoked=True,
            stage_durations_ms={
                "generation": 1.0,
            },
            tool_durations_ms={
                "retrieval": 0.5,
            },
            total_duration_ms=2.0,
        )

    count = 200

    with ThreadPoolExecutor(max_workers=8) as executor:
        tuple(
            executor.map(
                record_one,
                range(count),
            )
        )

    snapshot = metrics.snapshot()

    assert snapshot.http_requests_total == count

    assert snapshot.answer_requests_total == count

    assert snapshot.answers_total == count

    assert snapshot.generation_invocations_total == count

    assert snapshot.generation_accepted_total == count

    assert _pairs(snapshot.tool_invocations) == {
        "retrieval": count,
    }

    assert snapshot.http_latency_ms.count == count

    assert snapshot.answer_service_latency_ms.count == count

    assert snapshot.generation_latency_ms.count == count
