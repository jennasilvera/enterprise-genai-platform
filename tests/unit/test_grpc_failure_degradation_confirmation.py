from enterprise_genai.evaluation.grpc_failure_degradation_confirmation import (
    CONFIRMATION_QUESTION,
    GRPC_FAILURE_DEGRADATION_CONFIRMATION_VERSION,
    stable_abstention_snapshot,
)


def test_confirmation_version_is_frozen() -> None:
    assert GRPC_FAILURE_DEGRADATION_CONFIRMATION_VERSION == (
        "northstar-grpc-failure-degradation-confirmation-v1"
    )


def test_confirmation_question_is_frozen() -> None:
    assert CONFIRMATION_QUESTION == ("What defect affected ORBIS-IDX-7?")


def test_stable_abstention_snapshot_preserves_failure_contract() -> None:
    observed = stable_abstention_snapshot(
        {
            "status": ("abstained"),
            "presentation_source": ("deterministic"),
            "generation_fidelity": ("not_applicable"),
            "reason": ("execution_failed"),
            "detail": ("retrieval: retrieval rpc unavailable"),
            "citation_ids": [],
            "provenance_fact_ids": [],
            "text": ("presentation text is intentionally excluded"),
        }
    )

    assert observed == {
        "status": "abstained",
        "presentation_source": ("deterministic"),
        "generation_fidelity": ("not_applicable"),
        "reason": ("execution_failed"),
        "detail": ("retrieval: retrieval rpc unavailable"),
        "citation_ids": [],
        "provenance_fact_ids": [],
    }

    assert "text" not in observed


def test_stable_abstention_snapshot_defaults_provenance_to_empty() -> None:
    observed = stable_abstention_snapshot(
        {
            "status": ("abstained"),
            "reason": ("execution_failed"),
        }
    )

    assert observed["citation_ids"] == []

    assert observed["provenance_fact_ids"] == []
