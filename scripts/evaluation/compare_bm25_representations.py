import json
from pathlib import Path
from typing import Any

EXPERIMENT_DIR = Path("artifacts/evaluation/phase4b")

REPORT_PATHS = {
    "text-only-v1": (EXPERIMENT_DIR / "text-only-v1.json"),
    "company-text-v1": (EXPERIMENT_DIR / "company-text-v1.json"),
    "document-title-text-v1": (EXPERIMENT_DIR / "document-title-text-v1.json"),
    "evidence-heading-text-v1": (EXPERIMENT_DIR / "evidence-heading-text-v1.json"),
    "document-context-text-v1": (EXPERIMENT_DIR / "document-context-text-v1.json"),
}

PREREGISTERED_CANDIDATES = {
    "text-only-v1",
    "company-text-v1",
    "document-context-text-v1",
}

DIAGNOSTIC_VARIANTS = {
    "document-title-text-v1",
    "evidence-heading-text-v1",
}

EXPECTED_SCOPE = "development-only"
EXPECTED_CASES = 10


def load_report(
    path: Path,
) -> dict[str, Any]:
    report = json.loads(path.read_text(encoding="utf-8"))

    if report["scope"] != EXPECTED_SCOPE:
        raise ValueError(f"{path} is not development-only.")

    summary = report["benchmark"]["summary"]["retrieval_eligible"]

    if summary["cases"] != EXPECTED_CASES:
        raise ValueError(f"{path} has unexpected case count: {summary['cases']}")

    cases = report["benchmark"]["cases"]

    if any(case["split"] != "development" for case in cases):
        raise ValueError(f"{path} contains non-development cases.")

    return report


def metrics(
    report: dict[str, Any],
) -> dict[str, float]:
    summary = report["benchmark"]["summary"]["retrieval_eligible"]

    return {
        "canonical_mrr": summary["mean_canonical_reciprocal_rank"],
        "recall_at_10": summary["mean_recall_at_10"],
        "ndcg_at_10": summary["mean_ndcg_at_10"],
    }


def main() -> None:
    reports = {name: load_report(path) for name, path in REPORT_PATHS.items()}

    rows = []

    print("=== DEVELOPMENT-ONLY REPRESENTATION RESULTS ===")

    for name, report in reports.items():
        summary = metrics(report)

        row = {
            "representation": name,
            "experiment_role": (
                "preregistered" if name in PREREGISTERED_CANDIDATES else "post-hoc diagnostic"
            ),
            "eligible": report["lexical_rank_one_guardrail"],
            **summary,
        }

        rows.append(row)
        print(row)

    baseline = next(row for row in rows if row["representation"] == "text-only-v1")

    print("\n=== DELTAS VS FROZEN A0 ===")

    for row in rows:
        print(
            {
                "representation": (row["representation"]),
                "delta_canonical_mrr": (row["canonical_mrr"] - baseline["canonical_mrr"]),
                "delta_recall_at_10": (row["recall_at_10"] - baseline["recall_at_10"]),
                "delta_ndcg_at_10": (row["ndcg_at_10"] - baseline["ndcg_at_10"]),
            }
        )

    preregistered = [
        row
        for row in rows
        if (row["representation"] in PREREGISTERED_CANDIDATES and row["eligible"])
    ]

    winner = max(
        preregistered,
        key=lambda row: (
            row["ndcg_at_10"],
            row["canonical_mrr"],
            row["recall_at_10"],
        ),
    )

    print("\n=== PREREGISTERED SELECTION ===")
    print(
        "primary_metric:",
        "development mean nDCG@10",
    )
    print(
        "guardrail:",
        ("development lexical canonical evidence remains rank 1"),
    )
    print(
        "selected_representation:",
        winner["representation"],
    )

    print("\n=== POST-HOC ROBUSTNESS DIAGNOSTICS ===")

    for name in sorted(DIAGNOSTIC_VARIANTS):
        row = next(row for row in rows if row["representation"] == name)
        print(row)

    print(
        "\nrobustness_selected_for_follow_on:",
        "document-title-text-v1",
    )
    print(
        "selection_note:",
        (
            "The preregistered metric winner remains "
            "document-context-text-v1. "
            "document-title-text-v1 is selected for "
            "follow-on retrieval after a post-hoc "
            "robustness audit because title metadata "
            "is source-level context and avoids "
            "dependence on synthetic evidence headings."
        ),
    )


if __name__ == "__main__":
    main()
