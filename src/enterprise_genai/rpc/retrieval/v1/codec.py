from __future__ import annotations

from enterprise_genai.execution.contracts import (
    ExecutionStatus,
    RetrievalHit,
    RetrievalPayload,
    RetrievalQuery,
    ToolExecutionResult,
)

from . import retrieval_pb2

_STATUS_TO_PROTO: dict[
    ExecutionStatus,
    int,
] = {
    "ok": (retrieval_pb2.EXECUTION_STATUS_OK),
    "empty": (retrieval_pb2.EXECUTION_STATUS_EMPTY),
    "error": (retrieval_pb2.EXECUTION_STATUS_ERROR),
}

_PROTO_TO_STATUS: dict[
    int,
    ExecutionStatus,
] = {value: key for key, value in _STATUS_TO_PROTO.items()}


def retrieval_query_to_proto(
    query: RetrievalQuery,
) -> retrieval_pb2.RetrievalRequest:
    request = retrieval_pb2.RetrievalRequest(
        question=query.question,
    )

    request.dataset_version = query.dataset_version

    request.top_k = query.top_k

    return request


def retrieval_query_from_proto(
    request: retrieval_pb2.RetrievalRequest,
) -> RetrievalQuery:
    values: dict[
        str,
        object,
    ] = {
        "question": request.question,
    }

    if request.HasField("dataset_version"):
        values["dataset_version"] = request.dataset_version

    if request.HasField("top_k"):
        values["top_k"] = request.top_k

    return RetrievalQuery.model_validate(values)


def retrieval_hit_to_proto(
    hit: RetrievalHit,
) -> retrieval_pb2.RetrievalHit:
    message = retrieval_pb2.RetrievalHit(
        rank=hit.rank,
        chunk_id=hit.chunk_id,
        evidence_id=hit.evidence_id,
        document_id=hit.document_id,
        text=hit.text,
        source_fact_ids=hit.source_fact_ids,
        rrf_score=hit.rrf_score,
    )

    if hit.bm25_rank is not None:
        message.bm25_rank = hit.bm25_rank

    if hit.dense_rank is not None:
        message.dense_rank = hit.dense_rank

    return message


def retrieval_hit_from_proto(
    message: retrieval_pb2.RetrievalHit,
) -> RetrievalHit:
    return RetrievalHit(
        rank=message.rank,
        chunk_id=message.chunk_id,
        evidence_id=message.evidence_id,
        document_id=message.document_id,
        text=message.text,
        source_fact_ids=tuple(message.source_fact_ids),
        rrf_score=message.rrf_score,
        bm25_rank=(message.bm25_rank if message.HasField("bm25_rank") else None),
        dense_rank=(message.dense_rank if message.HasField("dense_rank") else None),
    )


def retrieval_payload_to_proto(
    payload: RetrievalPayload,
) -> retrieval_pb2.RetrievalPayload:
    message = retrieval_pb2.RetrievalPayload()

    message.hits.extend(retrieval_hit_to_proto(hit) for hit in payload.hits)

    return message


def retrieval_payload_from_proto(
    message: retrieval_pb2.RetrievalPayload,
) -> RetrievalPayload:
    return RetrievalPayload(hits=tuple(retrieval_hit_from_proto(hit) for hit in message.hits))


def retrieval_result_to_proto(
    result: ToolExecutionResult,
) -> retrieval_pb2.RetrievalResponse:
    if result.tool != "retrieval":
        raise ValueError("retrieval RPC codec requires a retrieval ToolExecutionResult")

    response = retrieval_pb2.RetrievalResponse(
        status=_STATUS_TO_PROTO[result.status],
        duration_ms=(result.duration_ms),
    )

    if result.status == "error":
        if result.error is None:
            raise ValueError("retrieval error result requires error text")

        response.error = result.error

        return response

    payload = result.payload

    if not isinstance(
        payload,
        RetrievalPayload,
    ):
        raise ValueError("retrieval non-error result requires RetrievalPayload")

    response.payload.CopyFrom(retrieval_payload_to_proto(payload))

    return response


def retrieval_result_from_proto(
    response: retrieval_pb2.RetrievalResponse,
) -> ToolExecutionResult:
    try:
        status = _PROTO_TO_STATUS[response.status]

    except KeyError as exc:
        raise ValueError(
            "retrieval RPC response contains unspecified or unknown execution status"
        ) from exc

    if status == "error":
        if response.HasField("payload"):
            raise ValueError("retrieval error response must not contain payload")

        if not response.HasField("error"):
            raise ValueError("retrieval error response requires error text")

        return ToolExecutionResult(
            tool="retrieval",
            status="error",
            duration_ms=(response.duration_ms),
            error=response.error,
        )

    if response.HasField("error"):
        raise ValueError("retrieval non-error response must not contain error text")

    if not response.HasField("payload"):
        raise ValueError("retrieval non-error response requires payload")

    return ToolExecutionResult(
        tool="retrieval",
        status=status,
        payload=(retrieval_payload_from_proto(response.payload)),
        duration_ms=(response.duration_ms),
    )
