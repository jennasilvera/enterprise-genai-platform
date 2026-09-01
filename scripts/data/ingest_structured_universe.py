from sqlalchemy.orm import Session

from enterprise_genai.data.universe import build_universe
from enterprise_genai.db.ingestion import (
    database_row_counts,
    ingest_universe,
    universe_fingerprint,
)
from enterprise_genai.db.session import engine


def main() -> None:
    universe = build_universe()

    with Session(engine) as session, session.begin():
        result = ingest_universe(
            session,
            universe,
        )

        counts = database_row_counts(
            session,
            universe.metadata.dataset_version,
        )

    action = "inserted" if result.inserted else "already_verified"

    print(f"dataset_version: {result.dataset_version}")
    print(f"action: {action}")
    print(
        "fingerprint:",
        universe_fingerprint(universe),
    )

    for table_name, count in counts.items():
        print(f"{table_name}: {count}")

    print("structured_ingestion: OK")


if __name__ == "__main__":
    main()
