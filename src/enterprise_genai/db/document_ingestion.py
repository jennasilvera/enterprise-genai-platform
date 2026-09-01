import hashlib
import json
from collections import defaultdict
from dataclasses import dataclass
from typing import Any

from sqlalchemy import func, insert, select
from sqlalchemy.orm import Session

from enterprise_genai.data.document_models import (
    DocumentCorpus,
    EnterpriseDocument,
    EvidenceBlock,
)
from enterprise_genai.db.models import (
    CanonicalFactRow,
    DatasetVersionRow,
    DocumentRow,
    EvidenceBlockRow,
    EvidenceSourceFactRow,
)


class DocumentCorpusConflictError(RuntimeError):
    """Raised when persisted documents differ from an immutable corpus."""


class MissingCanonicalFactsError(RuntimeError):
    """Raised when document evidence references unavailable canonical facts."""


@dataclass(frozen=True)
class DocumentIngestionResult:
    dataset_version: str
    inserted: bool
    fingerprint: str
    row_counts: dict[str, int]


def normalized_corpus_payload(
    corpus: DocumentCorpus,
) -> dict[str, Any]:
    """Return a stable corpus representation.

    Top-level document ordering is normalized by document ID.

    Evidence ordering and source-fact ordering are intentionally
    preserved because they are represented explicitly in PostgreSQL
    using ordinal columns.
    """

    documents: list[dict[str, Any]] = []

    for document in sorted(
        corpus.documents,
        key=lambda item: item.document_id,
    ):
        document_payload = document.model_dump(
            mode="json",
            exclude={"evidence"},
        )

        document_payload["evidence"] = [
            block.model_dump(mode="json") for block in document.evidence
        ]

        documents.append(document_payload)

    return {
        "dataset_version": corpus.dataset_version,
        "documents": documents,
    }


def corpus_fingerprint(
    corpus: DocumentCorpus,
) -> str:
    """Compute a deterministic semantic fingerprint of a corpus."""

    serialized = json.dumps(
        normalized_corpus_payload(corpus),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )

    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def expected_document_row_counts(
    corpus: DocumentCorpus,
) -> dict[str, int]:
    """Return expected persistence counts for a document corpus."""

    evidence_blocks = sum(len(document.evidence) for document in corpus.documents)

    provenance_links = sum(
        len(block.source_fact_ids) for document in corpus.documents for block in document.evidence
    )

    return {
        "documents": len(corpus.documents),
        "evidence_blocks": evidence_blocks,
        "evidence_source_facts": provenance_links,
    }


DOCUMENT_COUNT_MODELS = {
    "documents": DocumentRow,
    "evidence_blocks": EvidenceBlockRow,
    "evidence_source_facts": EvidenceSourceFactRow,
}


def document_database_row_counts(
    session: Session,
    dataset_version: str,
) -> dict[str, int]:
    """Count persisted document-layer rows for one dataset version."""

    counts: dict[str, int] = {}

    for table_name, model in DOCUMENT_COUNT_MODELS.items():
        statement = (
            select(func.count()).select_from(model).where(model.dataset_version == dataset_version)
        )

        counts[table_name] = session.execute(statement).scalar_one()

    return counts


def _required_source_fact_ids(
    corpus: DocumentCorpus,
) -> set[str]:
    return {
        fact_id
        for document in corpus.documents
        for block in document.evidence
        for fact_id in block.source_fact_ids
    }


def _validate_canonical_facts_exist(
    session: Session,
    corpus: DocumentCorpus,
) -> None:
    required = _required_source_fact_ids(corpus)

    if not required:
        return

    available = set(
        session.scalars(
            select(CanonicalFactRow.fact_id).where(
                CanonicalFactRow.dataset_version == corpus.dataset_version,
                CanonicalFactRow.fact_id.in_(required),
            )
        )
    )

    missing = required - available

    if missing:
        missing_text = ", ".join(sorted(missing))

        raise MissingCanonicalFactsError(
            f"Document corpus references canonical facts not present in PostgreSQL: {missing_text}"
        )


def _document_rows(
    corpus: DocumentCorpus,
) -> list[dict[str, Any]]:
    version = corpus.dataset_version

    return [
        {
            "dataset_version": version,
            "document_id": document.document_id,
            "company_id": document.company_id,
            "document_type": document.document_type,
            "title": document.title,
            "document_date": document.document_date,
            "confidentiality": document.confidentiality,
            "version": document.version,
        }
        for document in corpus.documents
    ]


def _evidence_rows(
    corpus: DocumentCorpus,
) -> list[dict[str, Any]]:
    version = corpus.dataset_version

    return [
        {
            "dataset_version": version,
            "evidence_id": block.evidence_id,
            "document_id": document.document_id,
            "evidence_ordinal": evidence_ordinal,
            "heading": block.heading,
            "text": block.text,
        }
        for document in corpus.documents
        for evidence_ordinal, block in enumerate(document.evidence)
    ]


def _source_fact_rows(
    corpus: DocumentCorpus,
) -> list[dict[str, Any]]:
    version = corpus.dataset_version

    return [
        {
            "dataset_version": version,
            "evidence_id": block.evidence_id,
            "source_fact_id": source_fact_id,
            "source_ordinal": source_ordinal,
        }
        for document in corpus.documents
        for block in document.evidence
        for source_ordinal, source_fact_id in enumerate(block.source_fact_ids)
    ]


def load_document_corpus(
    session: Session,
    dataset_version: str,
) -> DocumentCorpus:
    """Reconstruct one document corpus from PostgreSQL."""

    dataset = session.get(
        DatasetVersionRow,
        dataset_version,
    )

    if dataset is None:
        raise KeyError(f"Unknown dataset version: {dataset_version}")

    documents = list(
        session.scalars(
            select(DocumentRow)
            .where(DocumentRow.dataset_version == dataset_version)
            .order_by(DocumentRow.document_id)
        )
    )

    evidence_rows = list(
        session.scalars(
            select(EvidenceBlockRow)
            .where(EvidenceBlockRow.dataset_version == dataset_version)
            .order_by(
                EvidenceBlockRow.document_id,
                EvidenceBlockRow.evidence_ordinal,
            )
        )
    )

    source_rows = list(
        session.scalars(
            select(EvidenceSourceFactRow)
            .where(EvidenceSourceFactRow.dataset_version == dataset_version)
            .order_by(
                EvidenceSourceFactRow.evidence_id,
                EvidenceSourceFactRow.source_ordinal,
            )
        )
    )

    evidence_by_document: dict[
        str,
        list[EvidenceBlockRow],
    ] = defaultdict(list)

    for row in evidence_rows:
        evidence_by_document[row.document_id].append(row)

    sources_by_evidence: dict[
        str,
        list[str],
    ] = defaultdict(list)

    for row in source_rows:
        sources_by_evidence[row.evidence_id].append(row.source_fact_id)

    reconstructed_documents = []

    for document in documents:
        evidence = [
            EvidenceBlock(
                evidence_id=row.evidence_id,
                heading=row.heading,
                text=row.text,
                source_fact_ids=list(sources_by_evidence[row.evidence_id]),
            )
            for row in evidence_by_document[document.document_id]
        ]

        reconstructed_documents.append(
            EnterpriseDocument(
                document_id=document.document_id,
                company_id=document.company_id,
                document_type=document.document_type,
                title=document.title,
                document_date=document.document_date,
                confidentiality=document.confidentiality,
                version=document.version,
                evidence=evidence,
            )
        )

    return DocumentCorpus(
        dataset_version=dataset_version,
        documents=reconstructed_documents,
    )


def ingest_document_corpus(
    session: Session,
    corpus: DocumentCorpus,
) -> DocumentIngestionResult:
    """Persist one immutable document corpus transactionally."""

    version = corpus.dataset_version

    if (
        session.get(
            DatasetVersionRow,
            version,
        )
        is None
    ):
        raise KeyError(f"Structured dataset must be ingested before document corpus {version}.")

    _validate_canonical_facts_exist(
        session,
        corpus,
    )

    expected_fingerprint = corpus_fingerprint(corpus)

    expected_counts = expected_document_row_counts(corpus)

    actual_counts = document_database_row_counts(
        session,
        version,
    )

    has_existing_state = any(count > 0 for count in actual_counts.values())

    if has_existing_state:
        persisted = load_document_corpus(
            session,
            version,
        )

        persisted_fingerprint = corpus_fingerprint(persisted)

        if persisted_fingerprint != expected_fingerprint or actual_counts != expected_counts:
            raise DocumentCorpusConflictError(
                f"Document corpus for {version} already exists with different persisted contents."
            )

        return DocumentIngestionResult(
            dataset_version=version,
            inserted=False,
            fingerprint=expected_fingerprint,
            row_counts=actual_counts,
        )

    session.execute(
        insert(DocumentRow),
        _document_rows(corpus),
    )

    session.execute(
        insert(EvidenceBlockRow),
        _evidence_rows(corpus),
    )

    session.execute(
        insert(EvidenceSourceFactRow),
        _source_fact_rows(corpus),
    )

    persisted = load_document_corpus(
        session,
        version,
    )

    persisted_fingerprint = corpus_fingerprint(persisted)

    if persisted_fingerprint != expected_fingerprint:
        raise RuntimeError(
            "PostgreSQL document round-trip fingerprint does not match the canonical corpus."
        )

    actual_counts = document_database_row_counts(
        session,
        version,
    )

    if actual_counts != expected_counts:
        raise RuntimeError("PostgreSQL document row counts do not match the canonical corpus.")

    return DocumentIngestionResult(
        dataset_version=version,
        inserted=True,
        fingerprint=expected_fingerprint,
        row_counts=actual_counts,
    )
