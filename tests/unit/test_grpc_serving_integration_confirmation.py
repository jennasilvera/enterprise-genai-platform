from enterprise_genai.evaluation.grpc_serving_integration_confirmation import (
    CONFIRMATION_QUESTION,
    DATASET_VERSION,
    GRPC_SERVING_INTEGRATION_CONFIRMATION_VERSION,
    stable_answer_snapshot,
)


def test_confirmation_version_is_frozen() -> None:
    assert GRPC_SERVING_INTEGRATION_CONFIRMATION_VERSION == (
        "northstar-grpc-serving-integration-confirmation-v1"
    )


def test_confirmation_dataset_is_frozen() -> None:
    assert DATASET_VERSION == "northstar-v1"


def test_confirmation_question_is_frozen() -> None:
    assert CONFIRMATION_QUESTION == ("What defect affected ORBIS-IDX-7?")


def test_stable_answer_snapshot_excludes_text() -> None:
    observed = stable_answer_snapshot(
        {
            "status": "answered",
            "text": ("nondeterministic presentation text"),
            "presentation_source": ("deterministic_fallback"),
            "generation_fidelity": ("rejected"),
            "citations": [{"record_id": ("RISK-006")}],
        }
    )

    assert observed == {
        "status": "answered",
        "presentation_source": ("deterministic_fallback"),
        "generation_fidelity": ("rejected"),
        "citation_count": 1,
    }

    assert "text" not in observed


def test_stable_answer_snapshot_handles_missing_citations() -> None:
    observed = stable_answer_snapshot(
        {
            "status": "answered",
            "presentation_source": ("model"),
            "generation_fidelity": ("accepted"),
        }
    )

    assert observed["citation_count"] == 0
