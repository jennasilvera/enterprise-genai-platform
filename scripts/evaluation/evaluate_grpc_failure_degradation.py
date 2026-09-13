from __future__ import annotations

import hashlib
import json
from pathlib import Path

import grpc

from enterprise_genai.evaluation.grpc_failure_degradation_confirmation import (
    run_grpc_failure_degradation_confirmation,
)

ARTIFACT_PATH = Path("artifacts/evaluation/phase11e1_grpc_failure_degradation.json")


def main() -> None:
    report = run_grpc_failure_degradation_confirmation()

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

    for case in report["cases"]:
        print(
            "case:",
            case["case_id"],
        )

        print(
            "http_status:",
            case["http_status"],
        )

        print(
            "answer_status:",
            case["response"]["status"],
        )

        print(
            "reason:",
            case["response"]["reason"],
        )

        print(
            "detail:",
            case["response"]["detail"],
        )

        print(
            "generation_calls:",
            case["generation_calls"],
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
