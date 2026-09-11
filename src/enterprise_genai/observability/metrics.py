from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from threading import Lock

OPERATIONAL_METRICS_VERSION = "northstar-operational-metrics-v1"

DEFAULT_LATENCY_BUCKETS_MS = (
    1.0,
    5.0,
    10.0,
    25.0,
    50.0,
    100.0,
    250.0,
    500.0,
    1000.0,
    2500.0,
    5000.0,
    10000.0,
    30000.0,
)

_TOOL_FAMILIES = (
    "retrieval",
    "sql",
    "graph",
)


@dataclass(
    frozen=True,
    slots=True,
)
class HistogramSnapshot:
    """Immutable fixed-bucket histogram snapshot."""

    bounds_ms: tuple[
        float,
        ...,
    ]

    cumulative_counts: tuple[
        int,
        ...,
    ]

    overflow_count: int

    count: int

    sum_ms: float


@dataclass(
    frozen=True,
    slots=True,
)
class OperationalMetricsSnapshot:
    """Immutable process-local operational metrics snapshot."""

    version: str

    http_requests_total: int

    http_failures_total: int

    http_status_classes: tuple[
        tuple[
            str,
            int,
        ],
        ...,
    ]

    answer_requests_total: int

    answers_total: int

    abstentions_total: int

    answer_failures_total: int

    generation_invocations_total: int

    generation_accepted_total: int

    generation_rejected_total: int

    deterministic_fallback_total: int

    abstention_reasons: tuple[
        tuple[
            str,
            int,
        ],
        ...,
    ]

    answer_failure_stages: tuple[
        tuple[
            str,
            int,
        ],
        ...,
    ]

    tool_invocations: tuple[
        tuple[
            str,
            int,
        ],
        ...,
    ]

    http_latency_ms: HistogramSnapshot

    answer_service_latency_ms: HistogramSnapshot

    generation_latency_ms: HistogramSnapshot

    tool_latency_ms: tuple[
        tuple[
            str,
            HistogramSnapshot,
        ],
        ...,
    ]


class _FixedHistogram:
    def __init__(
        self,
        bounds_ms: tuple[
            float,
            ...,
        ],
    ) -> None:
        if not bounds_ms:
            raise ValueError("Histogram requires at least one bound.")

        if any(bound <= 0.0 for bound in bounds_ms):
            raise ValueError("Histogram bounds must be positive.")

        if tuple(sorted(set(bounds_ms))) != bounds_ms:
            raise ValueError("Histogram bounds must be strictly increasing and unique.")

        self._bounds_ms = bounds_ms

        self._bucket_counts = [0 for _bound in bounds_ms]

        self._overflow_count = 0

        self._count = 0

        self._sum_ms = 0.0

    def observe(
        self,
        value_ms: float,
    ) -> None:
        if value_ms < 0.0:
            raise ValueError("Histogram observations must be non-negative.")

        self._count += 1
        self._sum_ms += value_ms

        for index, bound in enumerate(self._bounds_ms):
            if value_ms <= bound:
                self._bucket_counts[index] += 1

                return

        self._overflow_count += 1

    def snapshot(
        self,
    ) -> HistogramSnapshot:
        running = 0

        cumulative: list[int] = []

        for count in self._bucket_counts:
            running += count

            cumulative.append(running)

        return HistogramSnapshot(
            bounds_ms=(self._bounds_ms),
            cumulative_counts=(tuple(cumulative)),
            overflow_count=(self._overflow_count),
            count=self._count,
            sum_ms=self._sum_ms,
        )


def _status_class(
    status_code: int,
) -> str:
    if not (100 <= status_code <= 599):
        raise ValueError("HTTP status code must be between 100 and 599.")

    return f"{status_code // 100}xx"


def _counter_snapshot(
    counter: Counter[str],
) -> tuple[
    tuple[
        str,
        int,
    ],
    ...,
]:
    return tuple(sorted(counter.items()))


class OperationalMetricsRegistry:
    """Thread-safe bounded operational metrics registry.

    This registry stores only counters and fixed-bucket latency
    aggregates. It does not retain request text, evidence, prompts,
    model output, answer text, or individual latency samples.
    """

    def __init__(
        self,
        *,
        latency_buckets_ms: tuple[
            float,
            ...,
        ] = DEFAULT_LATENCY_BUCKETS_MS,
    ) -> None:
        self._lock = Lock()

        self._http_requests_total = 0
        self._http_failures_total = 0

        self._http_status_classes: Counter[str] = Counter()

        self._answer_requests_total = 0
        self._answers_total = 0
        self._abstentions_total = 0
        self._answer_failures_total = 0

        self._generation_invocations_total = 0
        self._generation_accepted_total = 0
        self._generation_rejected_total = 0
        self._deterministic_fallback_total = 0

        self._abstention_reasons: Counter[str] = Counter()

        self._answer_failure_stages: Counter[str] = Counter()

        self._tool_invocations: Counter[str] = Counter()

        self._http_latency = _FixedHistogram(latency_buckets_ms)

        self._answer_service_latency = _FixedHistogram(latency_buckets_ms)

        self._generation_latency = _FixedHistogram(latency_buckets_ms)

        self._tool_latency = {tool: _FixedHistogram(latency_buckets_ms) for tool in _TOOL_FAMILIES}

    def record_http_completed(
        self,
        *,
        status_code: int,
        duration_ms: float,
    ) -> None:
        status_class = _status_class(status_code)

        with self._lock:
            self._http_requests_total += 1

            self._http_status_classes[status_class] += 1

            self._http_latency.observe(duration_ms)

    def record_http_failed(
        self,
        *,
        duration_ms: float,
    ) -> None:
        with self._lock:
            self._http_requests_total += 1
            self._http_failures_total += 1

            self._http_status_classes["5xx"] += 1

            self._http_latency.observe(duration_ms)

    def record_answer_completed(
        self,
        *,
        status: str,
        presentation_source: str,
        generation_fidelity: str,
        abstention_reason: str | None,
        generation_invoked: bool,
        stage_durations_ms: dict[
            str,
            float,
        ],
        tool_durations_ms: dict[
            str,
            float,
        ],
        total_duration_ms: float,
    ) -> None:
        if status not in {
            "answered",
            "abstained",
        }:
            raise ValueError("Unsupported answer status.")

        if status == "answered" and abstention_reason is not None:
            raise ValueError("Answered result cannot define an abstention reason.")

        if status == "abstained" and abstention_reason is None:
            raise ValueError("Abstained result requires an abstention reason.")

        if generation_invoked:
            if generation_fidelity not in {
                "accepted",
                "rejected",
            }:
                raise ValueError("Invoked generation requires accepted or rejected fidelity.")
        elif generation_fidelity != "not_applicable":
            raise ValueError("Skipped generation requires not_applicable fidelity.")

        for duration in (
            *stage_durations_ms.values(),
            *tool_durations_ms.values(),
            total_duration_ms,
        ):
            if duration < 0.0:
                raise ValueError("Metric durations must be non-negative.")

        unknown_tools = set(tool_durations_ms) - set(_TOOL_FAMILIES)

        if unknown_tools:
            raise ValueError(f"Unsupported tool metrics: {sorted(unknown_tools)!r}.")

        with self._lock:
            self._answer_requests_total += 1

            if status == "answered":
                self._answers_total += 1

            else:
                self._abstentions_total += 1

                assert abstention_reason is not None

                self._abstention_reasons[abstention_reason] += 1

            if generation_invoked:
                self._generation_invocations_total += 1

                if generation_fidelity == "accepted":
                    self._generation_accepted_total += 1

                else:
                    self._generation_rejected_total += 1

            if presentation_source == "deterministic_fallback":
                self._deterministic_fallback_total += 1

            self._answer_service_latency.observe(total_duration_ms)

            generation_duration = stage_durations_ms.get("generation")

            if generation_duration is not None:
                self._generation_latency.observe(generation_duration)

            for (
                tool,
                duration,
            ) in tool_durations_ms.items():
                self._tool_invocations[tool] += 1

                self._tool_latency[tool].observe(duration)

    def record_answer_failed(
        self,
        *,
        stage: str,
        generation_invoked: bool,
        total_duration_ms: float,
    ) -> None:
        if not stage.strip():
            raise ValueError("Failure stage must be non-empty.")

        if total_duration_ms < 0.0:
            raise ValueError("Metric durations must be non-negative.")

        with self._lock:
            self._answer_requests_total += 1
            self._answer_failures_total += 1

            self._answer_failure_stages[stage] += 1

            if generation_invoked:
                self._generation_invocations_total += 1

            self._answer_service_latency.observe(total_duration_ms)

    def snapshot(
        self,
    ) -> OperationalMetricsSnapshot:
        with self._lock:
            return OperationalMetricsSnapshot(
                version=(OPERATIONAL_METRICS_VERSION),
                http_requests_total=(self._http_requests_total),
                http_failures_total=(self._http_failures_total),
                http_status_classes=(_counter_snapshot(self._http_status_classes)),
                answer_requests_total=(self._answer_requests_total),
                answers_total=(self._answers_total),
                abstentions_total=(self._abstentions_total),
                answer_failures_total=(self._answer_failures_total),
                generation_invocations_total=(self._generation_invocations_total),
                generation_accepted_total=(self._generation_accepted_total),
                generation_rejected_total=(self._generation_rejected_total),
                deterministic_fallback_total=(self._deterministic_fallback_total),
                abstention_reasons=(_counter_snapshot(self._abstention_reasons)),
                answer_failure_stages=(_counter_snapshot(self._answer_failure_stages)),
                tool_invocations=(_counter_snapshot(self._tool_invocations)),
                http_latency_ms=(self._http_latency.snapshot()),
                answer_service_latency_ms=(self._answer_service_latency.snapshot()),
                generation_latency_ms=(self._generation_latency.snapshot()),
                tool_latency_ms=tuple(
                    (
                        tool,
                        self._tool_latency[tool].snapshot(),
                    )
                    for tool in _TOOL_FAMILIES
                ),
            )
