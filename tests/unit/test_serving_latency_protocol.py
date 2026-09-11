from __future__ import annotations

import pytest

from enterprise_genai.evaluation.serving_latency_protocol import (
    CONTROL_CASE_IDS,
    CONTROL_CASES,
    MEASUREMENT_ROUNDS,
    MEASUREMENT_SAMPLE_COUNT,
    P95_QUANTILE,
    SERVING_LATENCY_PROTOCOL_VERSION,
    WARMUP_ROUNDS,
    latency_protocol_payload,
    nearest_rank_percentile,
    summarize_latency_samples,
)


def test_serving_latency_protocol_version_is_frozen() -> None:
    assert SERVING_LATENCY_PROTOCOL_VERSION == "northstar-localhost-serving-latency-protocol-v1"


def test_serving_latency_protocol_has_fixed_control_order() -> None:
    assert CONTROL_CASE_IDS == (
        "Q-0001",
        "Q-0010",
        "Q-0011",
        "Q-0023",
        "Q-0024",
    )

    assert len(set(CONTROL_CASE_IDS)) == len(CONTROL_CASE_IDS)

    assert WARMUP_ROUNDS == 1

    assert MEASUREMENT_ROUNDS == 5

    assert MEASUREMENT_SAMPLE_COUNT == 25


def test_control_cases_freeze_expected_answering_behavior() -> None:
    observed = {
        case.query_id: (
            case.expected_status,
            case.expected_presentation_source,
            case.expected_generation_fidelity,
        )
        for case in CONTROL_CASES
    }

    assert observed == {
        "Q-0001": (
            "answered",
            "deterministic_fallback",
            "rejected",
        ),
        "Q-0010": (
            "answered",
            "model_generation",
            "accepted",
        ),
        "Q-0011": (
            "answered",
            "deterministic_fallback",
            "rejected",
        ),
        "Q-0023": (
            "abstained",
            "deterministic",
            "not_applicable",
        ),
        "Q-0024": (
            "abstained",
            "deterministic",
            "not_applicable",
        ),
    }


def test_nearest_rank_p95_definition_is_frozen() -> None:
    values = tuple(
        float(value)
        for value in range(
            1,
            26,
        )
    )

    assert P95_QUANTILE == 0.95

    assert (
        nearest_rank_percentile(
            values,
            0.95,
        )
        == 24.0
    )

    assert (
        nearest_rank_percentile(
            (
                1.0,
                2.0,
                3.0,
                4.0,
                5.0,
            ),
            0.95,
        )
        == 5.0
    )


def test_latency_summary_uses_frozen_statistics() -> None:
    result = summarize_latency_samples(
        (
            1.0,
            2.0,
            3.0,
            4.0,
            5.0,
        )
    )

    assert result == {
        "n": 5,
        "min_ms": 1.0,
        "median_ms": 3.0,
        "p95_ms": 5.0,
        "max_ms": 5.0,
    }


@pytest.mark.parametrize(
    "values",
    [
        (),
        (-1.0,),
        (float("inf"),),
        (float("nan"),),
    ],
)
def test_latency_summary_rejects_invalid_samples(
    values,
) -> None:
    with pytest.raises(
        ValueError,
    ):
        summarize_latency_samples(values)


def test_protocol_payload_contains_no_measured_results() -> None:
    protocol = latency_protocol_payload()

    assert protocol["version"] == SERVING_LATENCY_PROTOCOL_VERSION

    assert protocol["measurement"]["total_requests"] == 25

    assert protocol["server"]["workers"] == 1

    assert protocol["server"]["host"] == "127.0.0.1"

    assert protocol["client"]["concurrency"] == 1

    assert "results" not in protocol

    assert "observed_latency" not in protocol

    assert protocol["result_artifact_policy"]["store_question_text"] is False
