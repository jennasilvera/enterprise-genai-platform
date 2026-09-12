from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest
from pydantic import ValidationError

from enterprise_genai.execution.contracts import (
    RetrievalHit,
    RetrievalPayload,
    RetrievalQuery,
    ToolExecutionResult,
)
from enterprise_genai.rpc.retrieval.v1 import (
    retrieval_pb2,
    retrieval_pb2_grpc,
)
from enterprise_genai.rpc.retrieval.v1.codec import (
    retrieval_hit_from_proto,
    retrieval_hit_to_proto,
    retrieval_query_from_proto,
    retrieval_query_to_proto,
    retrieval_result_from_proto,
    retrieval_result_to_proto,
)

ROOT = Path(__file__).resolve().parents[2]


def _hit(
    *,
    bm25_rank: int | None = 1,
    dense_rank: int | None = 2,
) -> RetrievalHit:
    return RetrievalHit(
        rank=1,
        chunk_id="CHUNK-001",
        evidence_id="EVIDENCE-001",
        document_id="DOC-001",
        text="Synthetic retrieval evidence.",
        source_fact_ids=(
            "FACT-001",
            "FACT-002",
        ),
        rrf_score=0.03125,
        bm25_rank=bm25_rank,
        dense_rank=dense_rank,
    )


def test_service_descriptor_exposes_one_unary_retrieve_rpc() -> None:
    service = retrieval_pb2.DESCRIPTOR.services_by_name["RetrievalService"]

    assert len(service.methods) == 1

    method = service.methods_by_name["Retrieve"]

    assert method.input_type.full_name == ("enterprise_genai.rpc.retrieval.v1.RetrievalRequest")

    assert method.output_type.full_name == ("enterprise_genai.rpc.retrieval.v1.RetrievalResponse")

    # Generated gRPC bindings also import cleanly.
    assert hasattr(
        retrieval_pb2_grpc,
        "RetrievalServiceStub",
    )

    assert hasattr(
        retrieval_pb2_grpc,
        "RetrievalServiceServicer",
    )


def test_query_round_trip_preserves_domain_values() -> None:
    query = RetrievalQuery(
        dataset_version="northstar-v1",
        question="What defect affected ORBIS-IDX-7?",
        top_k=17,
    )

    message = retrieval_query_to_proto(query)

    assert message.HasField("dataset_version")

    assert message.HasField("top_k")

    assert retrieval_query_from_proto(message) == query


def test_wire_request_omission_preserves_domain_defaults() -> None:
    message = retrieval_pb2.RetrievalRequest(question="Question?")

    query = retrieval_query_from_proto(message)

    assert query.dataset_version == "northstar-v1"

    assert query.top_k == 10


@pytest.mark.parametrize(
    ("field", "value"),
    (
        (
            "question",
            "",
        ),
        (
            "dataset_version",
            "",
        ),
        (
            "top_k",
            0,
        ),
        (
            "top_k",
            51,
        ),
    ),
)
def test_wire_request_validation_uses_domain_contract(
    field: str,
    value: str | int,
) -> None:
    message = retrieval_pb2.RetrievalRequest(question="Question?")

    if field == "question":
        message.question = value

    elif field == "dataset_version":
        message.dataset_version = value

    else:
        message.top_k = value

    with pytest.raises(ValidationError):
        retrieval_query_from_proto(message)


@pytest.mark.parametrize(
    ("bm25_rank", "dense_rank"),
    (
        (
            1,
            2,
        ),
        (
            None,
            2,
        ),
        (
            1,
            None,
        ),
        (
            None,
            None,
        ),
    ),
)
def test_hit_round_trip_preserves_optional_rank_presence(
    bm25_rank: int | None,
    dense_rank: int | None,
) -> None:
    hit = _hit(
        bm25_rank=bm25_rank,
        dense_rank=dense_rank,
    )

    message = retrieval_hit_to_proto(hit)

    assert message.HasField("bm25_rank") is (bm25_rank is not None)

    assert message.HasField("dense_rank") is (dense_rank is not None)

    assert retrieval_hit_from_proto(message) == hit


@pytest.mark.parametrize(
    "status",
    (
        "ok",
        "empty",
    ),
)
def test_non_error_result_round_trip(
    status: str,
) -> None:
    payload = RetrievalPayload(hits=((_hit(),) if status == "ok" else ()))

    result = ToolExecutionResult(
        tool="retrieval",
        status=status,
        payload=payload,
        duration_ms=12.5,
    )

    message = retrieval_result_to_proto(result)

    assert message.HasField("payload")

    assert not message.HasField("error")

    assert retrieval_result_from_proto(message) == result


def test_error_result_round_trip() -> None:
    result = ToolExecutionResult(
        tool="retrieval",
        status="error",
        duration_ms=3.25,
        error=("retrieval executor dataset version mismatch"),
    )

    message = retrieval_result_to_proto(result)

    assert not message.HasField("payload")

    assert message.HasField("error")

    assert retrieval_result_from_proto(message) == result


def test_unspecified_wire_status_is_rejected() -> None:
    response = retrieval_pb2.RetrievalResponse(
        status=(retrieval_pb2.EXECUTION_STATUS_UNSPECIFIED),
        duration_ms=1.0,
    )

    with pytest.raises(
        ValueError,
        match="unspecified",
    ):
        retrieval_result_from_proto(response)


def test_non_error_wire_response_requires_payload() -> None:
    response = retrieval_pb2.RetrievalResponse(
        status=(retrieval_pb2.EXECUTION_STATUS_OK),
        duration_ms=1.0,
    )

    with pytest.raises(
        ValueError,
        match="requires payload",
    ):
        retrieval_result_from_proto(response)


def test_error_wire_response_rejects_payload() -> None:
    response = retrieval_pb2.RetrievalResponse(
        status=(retrieval_pb2.EXECUTION_STATUS_ERROR),
        duration_ms=1.0,
        error="bounded retrieval error",
    )

    response.payload.CopyFrom(retrieval_pb2.RetrievalPayload())

    with pytest.raises(
        ValueError,
        match="must not contain payload",
    ):
        retrieval_result_from_proto(response)


def test_codec_rejects_non_retrieval_domain_result() -> None:
    invalid = ToolExecutionResult.model_construct(
        tool="sql",
        status="error",
        payload=None,
        duration_ms=0.0,
        error="synthetic",
    )

    with pytest.raises(
        ValueError,
        match="requires a retrieval",
    ):
        retrieval_result_to_proto(invalid)


def test_generated_bindings_are_reproducible(
    tmp_path: Path,
) -> None:
    output_root = tmp_path / "generated"

    subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "rpc" / "generate_retrieval_grpc.py"),
            "--output-root",
            str(output_root),
        ],
        check=True,
        cwd=ROOT,
    )

    relative_paths = (
        Path("enterprise_genai/rpc/retrieval/v1/retrieval_pb2.py"),
        Path("enterprise_genai/rpc/retrieval/v1/retrieval_pb2_grpc.py"),
    )

    for relative in relative_paths:
        assert (output_root / relative).read_bytes() == (ROOT / "src" / relative).read_bytes()


def test_wire_field_numbers_and_enum_values_are_frozen() -> None:
    request = retrieval_pb2.RetrievalRequest.DESCRIPTOR
    hit = retrieval_pb2.RetrievalHit.DESCRIPTOR
    response = retrieval_pb2.RetrievalResponse.DESCRIPTOR

    assert {field.name: field.number for field in request.fields} == {
        "dataset_version": 1,
        "question": 2,
        "top_k": 3,
    }

    assert {field.name: field.number for field in hit.fields} == {
        "rank": 1,
        "chunk_id": 2,
        "evidence_id": 3,
        "document_id": 4,
        "text": 5,
        "source_fact_ids": 6,
        "rrf_score": 7,
        "bm25_rank": 8,
        "dense_rank": 9,
    }

    assert {field.name: field.number for field in response.fields} == {
        "status": 1,
        "payload": 2,
        "duration_ms": 3,
        "error": 4,
    }

    enum = retrieval_pb2.DESCRIPTOR.enum_types_by_name["ExecutionStatus"]

    assert {value.name: value.number for value in enum.values} == {
        "EXECUTION_STATUS_UNSPECIFIED": 0,
        "EXECUTION_STATUS_OK": 1,
        "EXECUTION_STATUS_EMPTY": 2,
        "EXECUTION_STATUS_ERROR": 3,
    }


def test_unknown_wire_status_is_rejected() -> None:
    response = retrieval_pb2.RetrievalResponse(
        status=99,
        duration_ms=1.0,
    )

    with pytest.raises(
        ValueError,
        match="unknown execution status",
    ):
        retrieval_result_from_proto(response)
