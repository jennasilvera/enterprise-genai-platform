from __future__ import annotations

import argparse
from pathlib import Path

from sqlalchemy.orm import Session

from enterprise_genai.db.session import (
    engine,
)
from enterprise_genai.evaluation.orchestration_confirmation import (
    orchestration_confirmation_sha256,
    run_orchestration_confirmation,
    write_orchestration_confirmation,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=("Confirm frozen mixed-tool LangGraph orchestration.")
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
        report = run_orchestration_confirmation(session=session)

    write_orchestration_confirmation(
        report,
        args.output,
    )

    print(
        "confirmation_version:",
        report["confirmation_version"],
    )

    print(
        "target_cases:",
        report["summary"]["target_cases"],
    )

    print(
        "completed_cases:",
        report["summary"]["completed_cases"],
    )

    for case in report["cases"]:
        print(
            case["query_id"],
            case["mode"],
            tuple(case["execution_order"]),
            case["terminal_status"],
        )

    print(
        "report_sha256:",
        orchestration_confirmation_sha256(report),
    )

    print(
        "report_written:",
        args.output,
    )


if __name__ == "__main__":
    main()
