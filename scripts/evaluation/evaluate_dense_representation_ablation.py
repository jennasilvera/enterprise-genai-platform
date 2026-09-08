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
from enterprise_genai.db.chunk_ingestion import (
    load_chunk_corpus,
)
from enterprise_genai.db.session import engine
from enterprise_genai.evaluation.dense_ablation import (
    compare_dense_reports,
)
from enterprise_genai.evaluation.dense_benchmark import (
    build_development_retrieval_evaluation,
    run_dense_benchmark,
)
from enterprise_genai.retrieval.chunking import (
    EVIDENCE_BLOCK_STRATEGY,
)
from enterprise_genai.retrieval.dense import (
    DenseConfig,
    DenseEncoder,
)
from enterprise_genai.retrieval.dense_representation import (
    DENSE_DOCUMENT_TITLE_TEXT_VERSION,
    build_dense_index_corpus,
)

DATASET_VERSION = "northstar-v1"

FROZEN_BASELINE = Path("artifacts/evaluation/phase5a/e5-small-v2-development.json")

DEFAULT_OUTPUT = Path("artifacts/evaluation/phase5b/e5-document-title-text-v1-development.json")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Evaluate the preregistered "
            "document-title-plus-evidence "
            "E5 representation on development."
        )
    )

    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
    )

    return parser.parse_args()


def main() -> None:
    args = parse_args()

    documents = build_core_corpus()

    evaluation = build_development_retrieval_evaluation(build_seed_evaluation())

    with Session(engine) as session:
        chunks = load_chunk_corpus(
            session,
            DATASET_VERSION,
            EVIDENCE_BLOCK_STRATEGY,
        )

    represented = build_dense_index_corpus(
        chunks,
        documents,
        representation_version=(DENSE_DOCUMENT_TITLE_TEXT_VERSION),
    )

    encoder = DenseEncoder(
        config=DenseConfig(
            batch_size=16,
            device="cpu",
            representation_version=(DENSE_DOCUMENT_TITLE_TEXT_VERSION),
        )
    )

    candidate = run_dense_benchmark(
        evaluation,
        represented,
        encoder=encoder,
        representation_version=(DENSE_DOCUMENT_TITLE_TEXT_VERSION),
    )

    baseline = json.loads(FROZEN_BASELINE.read_text(encoding="utf-8"))

    experiment = compare_dense_reports(
        baseline,
        candidate,
    )

    report = {
        **experiment,
        "candidate_benchmark": (candidate),
    }

    print(
        "experiment_version:",
        report["experiment_version"],
    )

    print(
        "baseline_representation:",
        report["baseline_representation"],
    )

    print(
        "candidate_representation:",
        report["candidate_representation"],
    )

    print(
        "selected_representation:",
        report["selected_representation"],
    )

    print("\n=== COMPARISON ===")

    print(
        json.dumps(
            report["comparison"],
            indent=2,
            sort_keys=True,
        )
    )

    print("\n=== CANDIDATE SUMMARY ===")

    print(
        json.dumps(
            candidate["summary"]["retrieval_eligible"],
            indent=2,
            sort_keys=True,
        )
    )

    print("\n=== CANDIDATE CASES ===")

    for case in candidate["cases"]:
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
