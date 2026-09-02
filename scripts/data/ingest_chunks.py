from sqlalchemy.orm import Session

from enterprise_genai.db.chunk_ingestion import (
    chunk_database_row_counts,
    ingest_chunk_corpus,
)
from enterprise_genai.db.document_ingestion import (
    load_document_corpus,
)
from enterprise_genai.db.session import engine
from enterprise_genai.retrieval.chunking import (
    EVIDENCE_BLOCK_STRATEGY,
    build_evidence_chunks,
)

DATASET_VERSION = "northstar-v1"


def main() -> None:
    with Session(engine) as session, session.begin():
        document_corpus = load_document_corpus(
            session,
            DATASET_VERSION,
        )

        chunk_corpus = build_evidence_chunks(
            document_corpus,
            strategy_version=(EVIDENCE_BLOCK_STRATEGY),
        )

        result = ingest_chunk_corpus(
            session,
            chunk_corpus,
        )

        counts = chunk_database_row_counts(
            session,
            DATASET_VERSION,
            EVIDENCE_BLOCK_STRATEGY,
        )

    action = "inserted" if result.inserted else "already_verified"

    print(f"dataset_version: {result.dataset_version}")
    print(f"strategy_version: {result.strategy_version}")
    print(f"action: {action}")
    print(f"fingerprint: {result.fingerprint}")

    for table_name, count in counts.items():
        print(f"{table_name}: {count}")

    print("chunk_ingestion: OK")


if __name__ == "__main__":
    main()
