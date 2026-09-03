import argparse
import json
from pathlib import Path

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
from enterprise_genai.evaluation.bm25_ablation import (
    run_bm25_representation_experiment,
)
from enterprise_genai.retrieval.chunking import (
    EVIDENCE_BLOCK_STRATEGY,
)
from enterprise_genai.retrieval.lexical_representation import (
    LEXICAL_REPRESENTATION_VERSIONS,
)

DATASET_VERSION = "northstar-v1"

FROZEN_BASELINE = Path("artifacts/evaluation/bm25_baseline.json")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=("Run a development-only BM25 lexical representation experiment.")
    )

    parser.add_argument(
        "--representation",
        choices=(LEXICAL_REPRESENTATION_VERSIONS),
        required=True,
    )

    parser.add_argument(
        "--output",
        type=Path,
    )

    return parser.parse_args()


def _verify_text_only_equivalence(
    report: dict,
) -> None:
    frozen = json.loads(FROZEN_BASELINE.read_text(encoding="utf-8"))

    expected_summary = frozen["summary"]["by_split"]["development"]

    actual_summary = report["benchmark"]["summary"]["retrieval_eligible"]

    if actual_summary != expected_summary:
        raise RuntimeError("Text-only development summary does not match frozen Phase 4A.")

    expected_cases = [case for case in frozen["cases"] if case["split"] == "development"]

    actual_cases = report["benchmark"]["cases"]

    if actual_cases != expected_cases:
        raise RuntimeError("Text-only development case behavior does not match frozen Phase 4A.")

    print("text_only_behavioral_equivalence: OK")


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

    report = run_bm25_representation_experiment(
        evaluation,
        chunks,
        documents,
        company_names,
        representation_version=(args.representation),
    )

    summary = report["benchmark"]["summary"]["retrieval_eligible"]

    print(
        "experiment_version:",
        report["experiment_version"],
    )
    print(
        "representation_version:",
        report["representation_version"],
    )
    print(
        "scope:",
        report["scope"],
    )
    print(
        "development_cases:",
        summary["cases"],
    )
    print(
        "lexical_rank_one_guardrail:",
        report["lexical_rank_one_guardrail"],
    )

    print("\n=== DEVELOPMENT SUMMARY ===")

    print(
        json.dumps(
            summary,
            indent=2,
            sort_keys=True,
        )
    )

    print("\n=== DEVELOPMENT CASES ===")

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

    if args.representation == "text-only-v1":
        _verify_text_only_equivalence(report)

    if args.output is not None:
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
            "report_written:",
            args.output,
        )


if __name__ == "__main__":
    main()
