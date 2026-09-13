from enterprise_genai.evaluation.grpc_retrieval_confirmation import (
    CONFIRMATION_CASES,
    DATASET_VERSION,
    GRPC_RETRIEVAL_CONFIRMATION_VERSION,
    semantic_retrieval_result,
)
from enterprise_genai.execution.contracts import (
    RetrievalHit,
    RetrievalPayload,
    ToolExecutionResult,
)


def _result(
    *,
    duration_ms: float,
) -> ToolExecutionResult:
    return ToolExecutionResult(
        tool="retrieval",
        status="ok",
        payload=RetrievalPayload(
            hits=(
                RetrievalHit(
                    rank=1,
                    chunk_id="CHUNK-001",
                    evidence_id="EVIDENCE-001",
                    document_id="DOC-001",
                    text="Synthetic evidence.",
                    source_fact_ids=("FACT-001",),
                    rrf_score=0.03125,
                    bm25_rank=1,
                    dense_rank=2,
                ),
            )
        ),
        duration_ms=duration_ms,
    )


def test_confirmation_version_is_frozen() -> None:
    assert GRPC_RETRIEVAL_CONFIRMATION_VERSION == ("northstar-grpc-retrieval-confirmation-v1")


def test_confirmation_dataset_is_frozen() -> None:
    assert DATASET_VERSION == "northstar-v1"


def test_confirmation_case_ids_are_frozen() -> None:
    assert [
        case_id
        for (
            case_id,
            _,
        ) in CONFIRMATION_CASES
    ] == [
        "orbis_lexical",
        "alder_supplier_risk",
        "vantage_renewal_risk",
        "dataset_version_error",
    ]


def test_semantic_projection_excludes_duration() -> None:
    first = semantic_retrieval_result(_result(duration_ms=1.0))

    second = semantic_retrieval_result(_result(duration_ms=999.0))

    assert first == second

    assert "duration_ms" not in first


def test_semantic_projection_preserves_provenance_and_ranks() -> None:
    observed = semantic_retrieval_result(_result(duration_ms=5.0))

    payload = observed["payload"]

    assert isinstance(
        payload,
        dict,
    )

    hits = payload["hits"]

    assert isinstance(
        hits,
        list,
    )

    assert hits == [
        {
            "rank": 1,
            "chunk_id": "CHUNK-001",
            "evidence_id": ("EVIDENCE-001"),
            "document_id": "DOC-001",
            "text": ("Synthetic evidence."),
            "source_fact_ids": [
                "FACT-001",
            ],
            "rrf_score": 0.03125,
            "bm25_rank": 1,
            "dense_rank": 2,
        }
    ]


def test_semantic_projection_preserves_typed_error() -> None:
    result = ToolExecutionResult(
        tool="retrieval",
        status="error",
        duration_ms=12.0,
        error=("retrieval executor dataset version mismatch"),
    )

    assert semantic_retrieval_result(result) == {
        "status": "error",
        "error": ("retrieval executor dataset version mismatch"),
        "payload": None,
    }
