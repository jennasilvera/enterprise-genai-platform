from sqlalchemy.orm import Session

from enterprise_genai.data.core_corpus import build_core_corpus
from enterprise_genai.data.provenance import (
    validate_document_provenance,
    validate_document_temporality,
)
from enterprise_genai.data.universe import build_universe
from enterprise_genai.db.document_ingestion import (
    corpus_fingerprint,
    document_database_row_counts,
    ingest_document_corpus,
)
from enterprise_genai.db.session import engine


def main() -> None:
    universe = build_universe()
    corpus = build_core_corpus()

    validate_document_provenance(
        corpus,
        universe,
    )
    validate_document_temporality(
        corpus,
        universe,
    )

    with Session(engine) as session, session.begin():
        result = ingest_document_corpus(
            session,
            corpus,
        )

        counts = document_database_row_counts(
            session,
            corpus.dataset_version,
        )

    action = "inserted" if result.inserted else "already_verified"

    print(f"dataset_version: {result.dataset_version}")
    print(f"action: {action}")
    print(
        "fingerprint:",
        corpus_fingerprint(corpus),
    )

    for table_name, count in counts.items():
        print(f"{table_name}: {count}")

    print("document_ingestion: OK")


if __name__ == "__main__":
    main()
