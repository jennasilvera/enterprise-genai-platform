import hashlib
import json
from collections import defaultdict
from dataclasses import dataclass
from typing import Any

from sqlalchemy import and_, func, insert, select
from sqlalchemy.orm import Session

from enterprise_genai.data.chunk_models import (
    ChunkCorpus,
    RetrievalChunk,
)
from enterprise_genai.db.models import (
    ChunkRow,
    ChunkSourceFactRow,
    DatasetVersionRow,
    EvidenceBlockRow,
    EvidenceSourceFactRow,
)


class ChunkCorpusConflictError(RuntimeError):
    """Raised when an immutable chunk strategy already differs in PostgreSQL."""


class MissingChunkEvidenceError(RuntimeError):
    """Raised when a chunk references an unavailable document/evidence pair."""


class MissingChunkProvenanceError(RuntimeError):
    """Raised when chunk provenance is not provenance of its parent evidence."""


@dataclass(frozen=True)
class ChunkIngestionResult:
    dataset_version: str
    strategy_version: str
    inserted: bool
    fingerprint: str
    row_counts: dict[str, int]


def normalized_chunk_payload(
    corpus: ChunkCorpus,
) -> dict[str, Any]:
    """Return an order-independent chunk-corpus representation.

    Top-level chunk order is normalized by chunk ID.

    source_fact_ids order is intentionally preserved because
    PostgreSQL stores it through source_ordinal.
    """

    return {
        "dataset_version": corpus.dataset_version,
        "strategy_version": corpus.strategy_version,
        "chunks": [
            chunk.model_dump(mode="json")
            for chunk in sorted(
                corpus.chunks,
                key=lambda item: item.chunk_id,
            )
        ],
    }


def chunk_corpus_fingerprint(
    corpus: ChunkCorpus,
) -> str:
    serialized = json.dumps(
        normalized_chunk_payload(corpus),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )

    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def expected_chunk_row_counts(
    corpus: ChunkCorpus,
) -> dict[str, int]:
    return {
        "chunks": len(corpus.chunks),
        "chunk_source_facts": sum(len(chunk.source_fact_ids) for chunk in corpus.chunks),
    }


def chunk_database_row_counts(
    session: Session,
    dataset_version: str,
    strategy_version: str,
) -> dict[str, int]:
    chunk_statement = (
        select(func.count())
        .select_from(ChunkRow)
        .where(
            ChunkRow.dataset_version == dataset_version,
            ChunkRow.strategy_version == strategy_version,
        )
    )

    source_statement = (
        select(func.count())
        .select_from(ChunkSourceFactRow)
        .join(
            ChunkRow,
            and_(
                ChunkSourceFactRow.dataset_version == ChunkRow.dataset_version,
                ChunkSourceFactRow.chunk_id == ChunkRow.chunk_id,
                ChunkSourceFactRow.evidence_id == ChunkRow.evidence_id,
            ),
        )
        .where(
            ChunkRow.dataset_version == dataset_version,
            ChunkRow.strategy_version == strategy_version,
        )
    )

    return {
        "chunks": session.execute(chunk_statement).scalar_one(),
        "chunk_source_facts": session.execute(source_statement).scalar_one(),
    }


def _validate_evidence_relationships(
    session: Session,
    corpus: ChunkCorpus,
) -> None:
    required = {
        (
            chunk.document_id,
            chunk.evidence_id,
        )
        for chunk in corpus.chunks
    }

    if not required:
        return

    evidence_ids = {evidence_id for _, evidence_id in required}

    available = set(
        session.execute(
            select(
                EvidenceBlockRow.document_id,
                EvidenceBlockRow.evidence_id,
            ).where(
                EvidenceBlockRow.dataset_version == corpus.dataset_version,
                EvidenceBlockRow.evidence_id.in_(evidence_ids),
            )
        ).all()
    )

    missing = required - available

    if missing:
        raise MissingChunkEvidenceError(
            f"Chunks reference unavailable document/evidence relationships: {sorted(missing)}"
        )


def _validate_provenance(
    session: Session,
    corpus: ChunkCorpus,
) -> None:
    required = {
        (
            chunk.evidence_id,
            source_fact_id,
        )
        for chunk in corpus.chunks
        for source_fact_id in chunk.source_fact_ids
    }

    if not required:
        return

    evidence_ids = {evidence_id for evidence_id, _ in required}

    available = set(
        session.execute(
            select(
                EvidenceSourceFactRow.evidence_id,
                EvidenceSourceFactRow.source_fact_id,
            ).where(
                EvidenceSourceFactRow.dataset_version == corpus.dataset_version,
                EvidenceSourceFactRow.evidence_id.in_(evidence_ids),
            )
        ).all()
    )

    missing = required - available

    if missing:
        raise MissingChunkProvenanceError(
            "Chunks reference source facts not belonging "
            f"to their parent evidence: {sorted(missing)}"
        )


def _chunk_rows(
    corpus: ChunkCorpus,
) -> list[dict[str, Any]]:
    return [
        {
            "dataset_version": corpus.dataset_version,
            "chunk_id": chunk.chunk_id,
            "document_id": chunk.document_id,
            "evidence_id": chunk.evidence_id,
            "chunk_ordinal": chunk.chunk_ordinal,
            "strategy_version": (chunk.strategy_version),
            "text": chunk.text,
            "text_sha256": chunk.text_sha256,
            "character_count": (chunk.character_count),
            "word_count": chunk.word_count,
        }
        for chunk in corpus.chunks
    ]


def _source_rows(
    corpus: ChunkCorpus,
) -> list[dict[str, Any]]:
    return [
        {
            "dataset_version": corpus.dataset_version,
            "chunk_id": chunk.chunk_id,
            "evidence_id": chunk.evidence_id,
            "source_fact_id": source_fact_id,
            "source_ordinal": source_ordinal,
        }
        for chunk in corpus.chunks
        for source_ordinal, source_fact_id in enumerate(chunk.source_fact_ids)
    ]


def load_chunk_corpus(
    session: Session,
    dataset_version: str,
    strategy_version: str,
) -> ChunkCorpus:
    """Reconstruct one chunking-strategy snapshot from PostgreSQL."""

    if (
        session.get(
            DatasetVersionRow,
            dataset_version,
        )
        is None
    ):
        raise KeyError(f"Unknown dataset version: {dataset_version}")

    chunks = list(
        session.scalars(
            select(ChunkRow)
            .where(
                ChunkRow.dataset_version == dataset_version,
                ChunkRow.strategy_version == strategy_version,
            )
            .order_by(ChunkRow.chunk_id)
        )
    )

    source_statement = (
        select(ChunkSourceFactRow)
        .join(
            ChunkRow,
            and_(
                ChunkSourceFactRow.dataset_version == ChunkRow.dataset_version,
                ChunkSourceFactRow.chunk_id == ChunkRow.chunk_id,
                ChunkSourceFactRow.evidence_id == ChunkRow.evidence_id,
            ),
        )
        .where(
            ChunkRow.dataset_version == dataset_version,
            ChunkRow.strategy_version == strategy_version,
        )
        .order_by(
            ChunkSourceFactRow.chunk_id,
            ChunkSourceFactRow.source_ordinal,
        )
    )

    source_rows = list(session.scalars(source_statement))

    sources_by_chunk: dict[
        str,
        list[str],
    ] = defaultdict(list)

    for row in source_rows:
        sources_by_chunk[row.chunk_id].append(row.source_fact_id)

    return ChunkCorpus(
        dataset_version=dataset_version,
        strategy_version=strategy_version,
        chunks=[
            RetrievalChunk(
                chunk_id=row.chunk_id,
                document_id=row.document_id,
                evidence_id=row.evidence_id,
                chunk_ordinal=row.chunk_ordinal,
                strategy_version=(row.strategy_version),
                text=row.text,
                text_sha256=row.text_sha256,
                character_count=(row.character_count),
                word_count=row.word_count,
                source_fact_ids=list(sources_by_chunk[row.chunk_id]),
            )
            for row in chunks
        ],
    )


def ingest_chunk_corpus(
    session: Session,
    corpus: ChunkCorpus,
) -> ChunkIngestionResult:
    """Persist one immutable chunk-strategy snapshot transactionally."""

    if (
        session.get(
            DatasetVersionRow,
            corpus.dataset_version,
        )
        is None
    ):
        raise KeyError("Structured dataset must exist before chunk ingestion.")

    _validate_evidence_relationships(
        session,
        corpus,
    )

    _validate_provenance(
        session,
        corpus,
    )

    expected_fingerprint = chunk_corpus_fingerprint(corpus)

    expected_counts = expected_chunk_row_counts(corpus)

    actual_counts = chunk_database_row_counts(
        session,
        corpus.dataset_version,
        corpus.strategy_version,
    )

    has_existing_state = any(count > 0 for count in actual_counts.values())

    if has_existing_state:
        if actual_counts != expected_counts:
            raise ChunkCorpusConflictError(
                f"Chunk strategy {corpus.strategy_version} "
                f"for {corpus.dataset_version} already "
                "exists with different row counts."
            )

        try:
            persisted = load_chunk_corpus(
                session,
                corpus.dataset_version,
                corpus.strategy_version,
            )
        except ValueError as exc:
            raise ChunkCorpusConflictError(
                f"Chunk strategy {corpus.strategy_version} contains invalid persisted state."
            ) from exc

        persisted_fingerprint = chunk_corpus_fingerprint(persisted)

        if persisted_fingerprint != expected_fingerprint:
            raise ChunkCorpusConflictError(
                f"Chunk strategy {corpus.strategy_version} "
                f"for {corpus.dataset_version} already "
                "exists with different persisted contents."
            )

        return ChunkIngestionResult(
            dataset_version=(corpus.dataset_version),
            strategy_version=(corpus.strategy_version),
            inserted=False,
            fingerprint=expected_fingerprint,
            row_counts=actual_counts,
        )

    chunk_rows = _chunk_rows(corpus)
    source_rows = _source_rows(corpus)

    if chunk_rows:
        session.execute(
            insert(ChunkRow),
            chunk_rows,
        )

    if source_rows:
        session.execute(
            insert(ChunkSourceFactRow),
            source_rows,
        )

    persisted = load_chunk_corpus(
        session,
        corpus.dataset_version,
        corpus.strategy_version,
    )

    persisted_fingerprint = chunk_corpus_fingerprint(persisted)

    if persisted_fingerprint != expected_fingerprint:
        raise RuntimeError(
            "PostgreSQL chunk round-trip fingerprint does not match generated chunks."
        )

    actual_counts = chunk_database_row_counts(
        session,
        corpus.dataset_version,
        corpus.strategy_version,
    )

    if actual_counts != expected_counts:
        raise RuntimeError("PostgreSQL chunk row counts do not match generated chunks.")

    return ChunkIngestionResult(
        dataset_version=corpus.dataset_version,
        strategy_version=corpus.strategy_version,
        inserted=True,
        fingerprint=expected_fingerprint,
        row_counts=actual_counts,
    )
