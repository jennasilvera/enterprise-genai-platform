from __future__ import annotations

import hashlib
import json
from pathlib import Path

import grpc

from enterprise_genai.db.session import (
    check_database,
    engine,
)
from enterprise_genai.evaluation.grpc_serving_integration_confirmation import (
    run_grpc_serving_integration_confirmation,
)

ARTIFACT_PATH = Path("artifacts/evaluation/phase11d5_grpc_serving_integration.json")


def main() -> None:
    check_database()

    report = run_grpc_serving_integration_confirmation(engine=engine)

    canonical = json.dumps(
        report,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")

    canonical_sha256 = hashlib.sha256(canonical).hexdigest()

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
        "transport_path:",
        report["transport_path"],
    )

    print(
        "http_status:",
        report["http"]["status_code"],
    )

    print(
        "answer_status:",
        report["http"]["answer"]["status"],
    )

    print(
        "retrieval_executor:",
        report["retrieval"]["executor_type"],
    )

    print(
        "remote_retrieval_calls:",
        report["retrieval"]["remote_call_count"],
    )

    print(
        "lifecycle_cleanup:",
        report["lifecycle"]["cleanup_verified"],
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
        canonical_sha256,
    )


if __name__ == "__main__":
    main()
