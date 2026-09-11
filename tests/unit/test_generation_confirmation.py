from __future__ import annotations

import json

import pytest

from enterprise_genai.evaluation.generation_confirmation import (
    EXPECTED_PRESENTATION_SOURCES,
    GUARDED_GENERATION_CONFIRMATION_VERSION,
    GUARDED_GENERATION_QUERY_IDS,
    build_guarded_generation_report,
    canonical_report_bytes,
)
from enterprise_genai.generation.contracts import (
    GenerationProviderMetadata,
)


def _metadata() -> GenerationProviderMetadata:
    return GenerationProviderMetadata(
        provider_id=("northstar-hf-causal-generation-provider-v1"),
        model_id=("Qwen/Qwen2.5-0.5B-Instruct"),
        model_revision=("7ae557604adf67be50417f59c2c2f167def9a775"),
        device="cpu",
        dtype="float32",
    )


def _observations():
    values = []

    for query_id in GUARDED_GENERATION_QUERY_IDS:
        source = EXPECTED_PRESENTATION_SOURCES[query_id]

        accepted = source == "model_generation"

        values.append(
            {
                "query_id": query_id,
                "fidelity_status": ("accepted" if accepted else "rejected"),
                "presentation_source": (source),
                "presentation_text": ("approved" if accepted else "fallback"),
                "rejected_raw_exposed": False,
            }
        )

    return values


def test_confirmation_version_is_frozen() -> None:
    assert GUARDED_GENERATION_CONFIRMATION_VERSION == "northstar-guarded-generation-confirmation-v1"


def test_confirmation_query_order_is_frozen() -> None:
    assert GUARDED_GENERATION_QUERY_IDS == (
        "Q-0001",
        "Q-0010",
        "Q-0011",
        "Q-0023",
        "Q-0024",
    )


def test_expected_presentation_sources_are_frozen() -> None:
    assert EXPECTED_PRESENTATION_SOURCES == {
        "Q-0001": ("deterministic_fallback"),
        "Q-0010": ("model_generation"),
        "Q-0011": ("deterministic_fallback"),
        "Q-0023": ("deterministic_fallback"),
        "Q-0024": ("deterministic_fallback"),
    }


def test_report_summary_counts_guarded_paths() -> None:
    report = build_guarded_generation_report(
        dataset_version="northstar-v1",
        evaluation_version=("northstar-eval-v1-seed"),
        provider_metadata=_metadata(),
        observations=_observations(),
    )

    assert report["summary"] == {
        "cases": 5,
        "fidelity_accepted": 1,
        "fidelity_rejected": 4,
        "model_generation": 1,
        "deterministic_fallback": 4,
        "rejected_raw_exposed": 0,
        "all_guarded": True,
    }


def test_report_rejects_exposed_rejected_generation() -> None:
    observations = _observations()

    observations[0]["rejected_raw_exposed"] = True

    with pytest.raises(
        ValueError,
        match=("crossed the presentation boundary"),
    ):
        build_guarded_generation_report(
            dataset_version="northstar-v1",
            evaluation_version=("northstar-eval-v1-seed"),
            provider_metadata=_metadata(),
            observations=observations,
        )


def test_canonical_report_bytes_are_stable() -> None:
    report = {
        "b": 2,
        "a": 1,
    }

    raw = canonical_report_bytes(report)

    assert raw == (b'{"a":1,"b":2}\n')

    assert json.loads(raw) == report
