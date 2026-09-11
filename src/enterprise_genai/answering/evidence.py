from __future__ import annotations

from enterprise_genai.answering.contracts import (
    EvidenceBundle,
    EvidenceRecord,
    GraphEntityEvidenceData,
    GraphRelationshipEvidenceData,
    StructuredEntityEvidenceData,
    StructuredValueEvidenceData,
)
from enterprise_genai.execution.contracts import (
    GraphPayload,
    RetrievalPayload,
    StructuredPayload,
    ToolExecutionResult,
)
from enterprise_genai.orchestration.contracts import (
    OrchestrationStateSnapshot,
)


def _sorted_facts(
    values: tuple[str, ...],
) -> tuple[str, ...]:
    return tuple(sorted(set(values)))


def _retrieval_records(
    payload: RetrievalPayload,
) -> tuple[
    EvidenceRecord,
    ...,
]:
    records: list[EvidenceRecord] = []

    for hit in payload.hits:
        facts = _sorted_facts(hit.source_fact_ids)

        # The answering boundary only treats
        # canonically grounded material as evidence.
        if not facts:
            continue

        records.append(
            EvidenceRecord(
                record_id=(f"RET:{hit.rank:03d}:{hit.evidence_id}"),
                tool="retrieval",
                kind="retrieval_hit",
                summary=hit.text,
                source_fact_ids=facts,
                document_id=(hit.document_id),
                rank=hit.rank,
            )
        )

    return tuple(records)


def _structured_source_facts(
    payload: StructuredPayload,
) -> tuple[str, ...]:
    return tuple(
        sorted({fact_id for row in payload.source_rows for fact_id in row.canonical_fact_ids})
    )


def _structured_records(
    payload: StructuredPayload,
) -> tuple[
    EvidenceRecord,
    ...,
]:
    if payload.empty_reason is not None:
        return ()

    source_facts = _structured_source_facts(payload)

    if payload.value is not None:
        if not source_facts:
            return ()

        unit_suffix = f" {payload.unit}" if payload.unit else ""

        return (
            EvidenceRecord(
                record_id=(f"SQL:VALUE:{payload.operation}"),
                tool="sql",
                kind="structured_value",
                summary=(
                    "Structured operation "
                    f"{payload.operation} "
                    "returned "
                    f"{payload.value}"
                    f"{unit_suffix}."
                ),
                source_fact_ids=(source_facts),
                data=StructuredValueEvidenceData(
                    value=payload.value,
                    unit=payload.unit,
                ),
            ),
        )

    records: list[EvidenceRecord] = []

    for entity in payload.entities:
        facts = tuple(sorted(set(source_facts) | set(entity.canonical_fact_ids)))

        if not facts:
            continue

        score_suffix = f" with score {entity.score}" if entity.score is not None else ""

        records.append(
            EvidenceRecord(
                record_id=(f"SQL:ENTITY:{entity.company_id}"),
                tool="sql",
                kind="structured_entity",
                summary=(
                    f"{entity.name} "
                    f"({entity.company_id}) "
                    "was returned by "
                    f"{payload.operation}"
                    f"{score_suffix}."
                ),
                source_fact_ids=facts,
                data=StructuredEntityEvidenceData(
                    entity_id=entity.company_id,
                    entity_name=entity.name,
                    score=entity.score,
                    score_unit=(payload.unit if entity.score is not None else None),
                ),
            )
        )

    return tuple(records)


def _graph_records(
    payload: GraphPayload,
) -> tuple[
    EvidenceRecord,
    ...,
]:
    if payload.empty_reason is not None:
        return ()

    records: list[EvidenceRecord] = []

    for node in payload.nodes:
        facts = _sorted_facts(node.canonical_fact_ids)

        if not facts:
            continue

        records.append(
            EvidenceRecord(
                record_id=(f"GRAPH:NODE:{node.entity_type}:{node.entity_id}"),
                tool="graph",
                kind="graph_entity",
                summary=(f"{node.entity_type} {node.name} ({node.entity_id})."),
                source_fact_ids=facts,
                data=GraphEntityEvidenceData(
                    entity_type=node.entity_type,
                    entity_id=node.entity_id,
                    entity_name=node.name,
                ),
            )
        )

    for edge in payload.edges:
        facts = _sorted_facts(edge.canonical_fact_ids)

        if not facts:
            continue

        records.append(
            EvidenceRecord(
                record_id=(f"GRAPH:EDGE:{edge.relationship_type}:{edge.relationship_id}"),
                tool="graph",
                kind="graph_relationship",
                summary=(
                    f"{edge.source_type} "
                    f"{edge.source_id} has "
                    f"{edge.relationship_type} "
                    "relationship "
                    f"{edge.relationship_id} "
                    f"with {edge.target_type} "
                    f"{edge.target_id}."
                ),
                source_fact_ids=facts,
                data=GraphRelationshipEvidenceData(
                    relationship_type=(edge.relationship_type),
                    relationship_id=(edge.relationship_id),
                    source_type=edge.source_type,
                    source_id=edge.source_id,
                    target_type=edge.target_type,
                    target_id=edge.target_id,
                ),
            )
        )

    return tuple(records)


def _records_for_result(
    result: ToolExecutionResult,
) -> tuple[
    EvidenceRecord,
    ...,
]:
    if result.status == "error":
        return ()

    payload = result.payload

    if isinstance(
        payload,
        RetrievalPayload,
    ):
        return _retrieval_records(payload)

    if isinstance(
        payload,
        StructuredPayload,
    ):
        return _structured_records(payload)

    if isinstance(
        payload,
        GraphPayload,
    ):
        return _graph_records(payload)

    raise TypeError(f"Unexpected execution payload type: {type(payload)!r}.")


def _failure_detail(
    snapshot: OrchestrationStateSnapshot,
) -> str:
    errors = tuple(
        (f"{result.tool}: {result.error}")
        for result in snapshot.results
        if (result.status == "error" and result.error is not None)
    )

    if errors:
        return "; ".join(errors)

    return "Orchestration failed before producing a complete answerable evidence set."


def _blocked_detail(
    snapshot: OrchestrationStateSnapshot,
) -> str:
    reasons: list[str] = []

    for result in snapshot.results:
        payload = result.payload

        if isinstance(
            payload,
            StructuredPayload,
        ) and (payload.empty_reason is not None):
            reasons.append(f"sql:{payload.empty_reason}")

        if isinstance(
            payload,
            GraphPayload,
        ) and (payload.empty_reason is not None):
            reasons.append(f"graph:{payload.empty_reason}")

    if reasons:
        return "; ".join(reasons)

    return "A required orchestration dependency could not be satisfied."


def evidence_bundle_from_snapshot(
    snapshot: OrchestrationStateSnapshot,
) -> EvidenceBundle:
    """Normalize one terminal orchestration snapshot into answer evidence."""

    if snapshot.status in {
        "pending",
        "running",
    }:
        raise ValueError("Evidence normalization requires a terminal orchestration state.")

    records = tuple(record for result in snapshot.results for record in _records_for_result(result))

    if snapshot.status == "completed":
        return EvidenceBundle(
            question=(snapshot.plan.question),
            status="completed",
            records=records,
        )

    if snapshot.status == "blocked":
        return EvidenceBundle(
            question=(snapshot.plan.question),
            status="blocked",
            records=records,
            detail=(_blocked_detail(snapshot)),
        )

    if snapshot.status == "failed":
        return EvidenceBundle(
            question=(snapshot.plan.question),
            status="failed",
            records=records,
            detail=(_failure_detail(snapshot)),
        )

    raise ValueError(f"Unsupported orchestration status: {snapshot.status!r}.")


def unsupported_request_bundle(
    *,
    question: str,
    detail: str,
) -> EvidenceBundle:
    """Represent a request rejected before valid bounded execution."""

    return EvidenceBundle(
        question=question,
        status="unsupported_request",
        detail=detail,
    )
