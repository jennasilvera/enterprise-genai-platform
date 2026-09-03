import argparse
import json
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from enterprise_genai.data.core_corpus import (
    build_core_corpus,
)
from enterprise_genai.data.evaluation_seed import (
    build_seed_evaluation,
)
from enterprise_genai.data.universe import (
    build_universe,
)
from enterprise_genai.db.chunk_ingestion import (
    load_chunk_corpus,
)
from enterprise_genai.db.session import engine
from enterprise_genai.evaluation.bm25_confirmation import (
    SELECTED_REPRESENTATION,
    run_bm25_test_confirmation,
)
from enterprise_genai.retrieval.chunking import (
    EVIDENCE_BLOCK_STRATEGY,
)

DATASET_VERSION = "northstar-v1"

FROZEN_BASELINE = Path("artifacts/evaluation/bm25_baseline.json")

DEFAULT_OUTPUT = Path("artifacts/evaluation/phase4c/document-title-text-v1-test.json")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Confirm the frozen Phase 4B "
            "document-title BM25 representation "
            "on retrieval-eligible test cases."
        )
    )

    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
    )

    return parser.parse_args()


def _test_summary(
    baseline: dict[str, Any],
) -> dict[str, Any]:
    return baseline["summary"]["by_split"]["test"]


def _comparison(
    selected: dict[str, Any],
    baseline: dict[str, Any],
) -> dict[str, float]:
    return {
        "delta_canonical_mrr": (
            selected["mean_canonical_reciprocal_rank"] - baseline["mean_canonical_reciprocal_rank"]
        ),
        "delta_recall_at_10": (selected["mean_recall_at_10"] - baseline["mean_recall_at_10"]),
        "delta_ndcg_at_10": (selected["mean_ndcg_at_10"] - baseline["mean_ndcg_at_10"]),
    }


def main() -> None:
    args = parse_args()

    documents = build_core_corpus()
    evaluation = build_seed_evaluation()
    universe = build_universe()

    company_names = {company.company_id: company.name for company in universe.companies}

    with Session(engine) as session:
        chunks = load_chunk_corpus(
            session,
            DATASET_VERSION,
            EVIDENCE_BLOCK_STRATEGY,
        )

    report = run_bm25_test_confirmation(
        evaluation,
        chunks,
        documents,
        company_names,
    )

    frozen = json.loads(FROZEN_BASELINE.read_text(encoding="utf-8"))

    baseline_summary = _test_summary(frozen)

    selected_summary = report["benchmark"]["summary"]["retrieval_eligible"]

    report["frozen_text_only_test_reference"] = baseline_summary

    report["comparison_vs_frozen_text_only"] = _comparison(
        selected_summary,
        baseline_summary,
    )

    print(
        "confirmation_version:",
        report["confirmation_version"],
    )

    print(
        "selected_representation:",
        SELECTED_REPRESENTATION,
    )

    print(
        "selection_status:",
        report["selection_status"],
    )

    print(
        "scope:",
        report["scope"],
    )

    print(
        "test_cases:",
        selected_summary["cases"],
    )

    print(
        "lexical_rank_one_guardrail:",
        report["lexical_rank_one_guardrail"],
    )

    print("\n=== FROZEN TEXT-ONLY TEST REFERENCE ===")

    print(
        json.dumps(
            baseline_summary,
            indent=2,
            sort_keys=True,
        )
    )

    print("\n=== SELECTED REPRESENTATION TEST ===")

    print(
        json.dumps(
            selected_summary,
            indent=2,
            sort_keys=True,
        )
    )

    print("\n=== DELTAS VS FROZEN TEXT-ONLY ===")

    print(
        json.dumps(
            report["comparison_vs_frozen_text_only"],
            indent=2,
            sort_keys=True,
        )
    )

    print("\n=== TEST CASE RESULTS ===")

    for case in report["benchmark"]["cases"]:
        print(
            case["query_id"],
            case["query_type"],
            {
                "canonical_rr": (case["metrics"]["canonical_reciprocal_rank"]),
                "recall_at_10": (case["metrics"]["recall_at_10"]),
                "ndcg_at_10": (case["metrics"]["ndcg_at_10"]),
            },
        )

        for result in case["top_results"][:3]:
            print(
                "  ",
                result["rank"],
                round(
                    result["score"],
                    6,
                ),
                result["evidence_id"],
                result["matched_terms"],
            )

    args.output.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    args.output.write_text(
        json.dumps(
            report,
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    print(
        "\nreport_written:",
        args.output,
    )


if __name__ == "__main__":
    main()
