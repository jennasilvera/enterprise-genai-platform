from __future__ import annotations

import argparse
import hashlib
from pathlib import Path

from sqlalchemy.orm import Session

from enterprise_genai.db.session import (
    engine,
)
from enterprise_genai.evaluation.execution_coverage_confirmation import (
    deterministic_confirmation_bytes,
    run_execution_coverage_confirmation,
    write_execution_coverage_confirmation,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Confirm bounded execution coverage against the frozen Northstar benchmark protocol."
        )
    )

    parser.add_argument(
        "--output",
        type=Path,
        required=True,
    )

    return parser.parse_args()


def main() -> None:
    args = parse_args()

    with Session(engine) as session:
        report = run_execution_coverage_confirmation(session=session)

    write_execution_coverage_confirmation(
        report,
        args.output,
    )

    payload = deterministic_confirmation_bytes(report)

    print(
        "confirmation_version:",
        report["confirmation_version"],
    )

    print(
        "target_cases:",
        report["summary"]["target_cases"],
    )

    print(
        "verified_primitive_cases:",
        report["summary"]["verified_primitive_cases"],
    )

    print(
        "explicit_compositions_verified:",
        report["summary"]["explicit_compositions_verified"],
    )

    for case in report["cases"]:
        observed = case["observed"]

        print(
            case["query_id"],
            observed["observed_primitive_coverage"],
            observed["observed_composition_coverage"],
        )

    print(
        "report_sha256:",
        hashlib.sha256(payload).hexdigest(),
    )

    print(
        "report_written:",
        args.output,
    )


if __name__ == "__main__":
    main()
