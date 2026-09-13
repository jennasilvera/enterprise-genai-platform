from __future__ import annotations

import hashlib
import json
from pathlib import Path

import grpc

from enterprise_genai.db.session import (
    check_database,
    engine,
)
from enterprise_genai.evaluation.grpc_retrieval_confirmation import (
    run_grpc_retrieval_confirmation,
)

ARTIFACT_PATH = Path("artifacts/evaluation/phase11d4_grpc_retrieval_confirmation.json")


def main() -> None:
    check_database()

    report = run_grpc_retrieval_confirmation(engine=engine)

    canonical = json.dumps(
        report,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")

    sha256 = hashlib.sha256(canonical).hexdigest()

    ARTIFACT_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    ARTIFACT_PATH.write_text(
        json.dumps(
            report,
            indent=2,
            sort_keys=True,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )

    print(
        "confirmation_version:",
        report["confirmation_version"],
    )

    print(
        "grpc_version:",
        grpc.__version__,
    )

    print(
        "transport:",
        report["transport"],
    )

    print(
        "parity_cases:",
        report["parity"]["case_count"],
    )

    print(
        "semantic_parity:",
        report["parity"]["all_semantically_equal"],
    )

    print(
        "deadline_verified:",
        report["deadline"]["verified"],
    )

    print(
        "unavailable_verified:",
        report["unavailable"]["verified"],
    )

    print(
        "all_passed:",
        report["summary"]["all_passed"],
    )

    print(
        "artifact:",
        ARTIFACT_PATH,
    )

    print(
        "canonical_sha256:",
        sha256,
    )


if __name__ == "__main__":
    main()
