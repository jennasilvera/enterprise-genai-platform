from __future__ import annotations

import pytest
from pydantic import ValidationError

from enterprise_genai.answering.contracts import (
    EvidenceRecord,
    GraphEntityEvidenceData,
    GraphRelationshipEvidenceData,
    StructuredEntityEvidenceData,
    StructuredValueEvidenceData,
)
from enterprise_genai.answering.evidence import (
    _graph_records,
    _retrieval_records,
    _structured_records,
)
from enterprise_genai.execution.contracts import (
    DatabaseRowReference,
    GraphEdge,
    GraphNode,
    GraphPayload,
    RetrievalHit,
    RetrievalPayload,
    StructuredEntity,
    StructuredPayload,
)


def _row(
    fact_id: str,
) -> DatabaseRowReference:
    return DatabaseRowReference(
        table="financial_metrics",
        primary_key={
            "company_id": "PC-001",
            "period": "2026Q2",
        },
        canonical_fact_ids=(fact_id,),
    )


def test_structured_scalar_preserves_value_and_unit() -> None:
    records = _structured_records(
        StructuredPayload(
            operation="portfolio_metric_sum",
            value=735_000_000,
            unit="USD",
            source_rows=(_row("FIN-PC-001-2026Q2"),),
        )
    )

    assert len(records) == 1

    data = records[0].data

    assert isinstance(
        data,
        StructuredValueEvidenceData,
    )

    assert data.value == 735_000_000
    assert data.unit == "USD"


def test_structured_entity_preserves_identity_score_and_unit() -> None:
    records = _structured_records(
        StructuredPayload(
            operation="portfolio_growth_rank",
            value=None,
            entities=(
                StructuredEntity(
                    company_id="PC-004",
                    name="HelioGrid Energy",
                    score=("0.3529411764705882352941176471"),
                    canonical_fact_ids=(
                        "FIN-PC-004-2025Q2",
                        "FIN-PC-004-2026Q2",
                    ),
                ),
            ),
            unit="ratio",
            source_rows=(_row("FIN-PC-004-2026Q2"),),
        )
    )

    data = records[0].data

    assert isinstance(
        data,
        StructuredEntityEvidenceData,
    )

    assert data.entity_id == "PC-004"
    assert data.entity_name == "HelioGrid Energy"
    assert data.score == ("0.3529411764705882352941176471")
    assert data.score_unit == "ratio"


def test_graph_records_preserve_node_and_relationship_identity() -> None:
    records = _graph_records(
        GraphPayload(
            nodes=(
                GraphNode(
                    entity_type="company",
                    entity_id="PC-002",
                    name="Alder Manufacturing",
                    canonical_fact_ids=("PC-002",),
                ),
                GraphNode(
                    entity_type="supplier",
                    entity_id="SUP-005",
                    name="TitaniumWorks GmbH",
                    canonical_fact_ids=("SUP-005",),
                ),
            ),
            edges=(
                GraphEdge(
                    relationship_type=("company_supplier"),
                    relationship_id="CS-003",
                    source_type="company",
                    source_id="PC-002",
                    target_type="supplier",
                    target_id="SUP-005",
                    canonical_fact_ids=("CS-003",),
                ),
            ),
            matched_company_ids=("PC-002",),
        )
    )

    company_data = records[0].data
    relationship_data = records[-1].data

    assert isinstance(
        company_data,
        GraphEntityEvidenceData,
    )

    assert company_data.entity_name == "Alder Manufacturing"

    assert isinstance(
        relationship_data,
        GraphRelationshipEvidenceData,
    )

    assert relationship_data.relationship_id == "CS-003"

    assert relationship_data.source_id == "PC-002"

    assert relationship_data.target_id == "SUP-005"


def test_retrieval_continues_to_use_source_text_without_structured_data() -> None:
    records = _retrieval_records(
        RetrievalPayload(
            hits=(
                RetrievalHit(
                    rank=1,
                    chunk_id="CHUNK-001",
                    evidence_id="EVID-001",
                    document_id="DOC-001",
                    text=("Canonical retrieval source text."),
                    source_fact_ids=("RISK-001",),
                    rrf_score=0.03,
                    bm25_rank=1,
                    dense_rank=1,
                ),
            )
        )
    )

    assert records[0].data is None

    assert records[0].summary == ("Canonical retrieval source text.")


def test_evidence_data_kind_must_match_record_kind() -> None:
    with pytest.raises(
        ValidationError,
        match=("Evidence data kind must match the evidence record kind"),
    ):
        EvidenceRecord(
            record_id="SQL:VALUE:test",
            tool="sql",
            kind="structured_value",
            summary="Structured value.",
            source_fact_ids=("FIN-001",),
            data=StructuredEntityEvidenceData(
                entity_id="PC-001",
                entity_name="Company",
            ),
        )


def test_retrieval_rejects_structured_synthesis_data() -> None:
    with pytest.raises(
        ValidationError,
        match=("Retrieval evidence must not contain structured synthesis data"),
    ):
        EvidenceRecord(
            record_id="RET:001:EVID-001",
            tool="retrieval",
            kind="retrieval_hit",
            summary="Source text.",
            source_fact_ids=("RISK-001",),
            document_id="DOC-001",
            rank=1,
            data=StructuredValueEvidenceData(
                value=1,
            ),
        )
