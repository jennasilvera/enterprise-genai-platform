from sqlalchemy import (
    ForeignKeyConstraint,
    UniqueConstraint,
)

from enterprise_genai.db.models import (
    ChunkRow,
    ChunkSourceFactRow,
    EvidenceBlockRow,
)


def _foreign_key_names(table) -> set[str]:
    return {
        constraint.name
        for constraint in table.constraints
        if isinstance(
            constraint,
            ForeignKeyConstraint,
        )
    }


def _unique_names(table) -> set[str]:
    return {
        constraint.name
        for constraint in table.constraints
        if isinstance(
            constraint,
            UniqueConstraint,
        )
    }


def test_chunk_primary_key_is_versioned() -> None:
    assert [column.name for column in ChunkRow.__table__.primary_key] == [
        "dataset_version",
        "chunk_id",
    ]


def test_chunks_bind_document_and_evidence_together() -> None:
    assert "fk_chunks_evidence" in _foreign_key_names(ChunkRow.__table__)


def test_evidence_has_composite_chunk_fk_target() -> None:
    assert "uq_evidence_blocks_document_evidence" in _unique_names(EvidenceBlockRow.__table__)


def test_chunk_source_fact_requires_real_evidence_provenance() -> None:
    names = _foreign_key_names(ChunkSourceFactRow.__table__)

    assert "fk_chunk_source_facts_chunk" in names
    assert "fk_chunk_source_facts_evidence_fact" in names


def test_chunk_position_is_unique_per_strategy() -> None:
    assert "uq_chunks_evidence_strategy_ordinal" in _unique_names(ChunkRow.__table__)


def test_chunk_source_order_is_unique() -> None:
    assert "uq_chunk_source_facts_ordinal" in _unique_names(ChunkSourceFactRow.__table__)
