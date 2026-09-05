import argparse
import json
from pathlib import Path

from sqlalchemy.orm import Session

from enterprise_genai.data.evaluation_seed import (
    build_seed_evaluation,
)
from enterprise_genai.db.chunk_ingestion import (
    load_chunk_corpus,
)
from enterprise_genai.db.session import engine
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

DATASET_VERSION = "northstar-v1"

DEFAULT_OUTPUT = Path("artifacts/evaluation/phase5a/e5-small-v2-development.json")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Evaluate the frozen E5-small-v2 "
            "evidence-text dense baseline on "
            "retrieval-eligible development cases."
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

    evaluation = build_development_retrieval_evaluation(build_seed_evaluation())

    with Session(engine) as session:
        chunks = load_chunk_corpus(
            session,
            DATASET_VERSION,
            EVIDENCE_BLOCK_STRATEGY,
        )

    encoder = DenseEncoder(
        config=DenseConfig(
            batch_size=16,
            device="cpu",
        )
    )

    report = run_dense_benchmark(
        evaluation,
        chunks,
        encoder=encoder,
    )

    summary = report["summary"]["retrieval_eligible"]

    print(
        "benchmark_version:",
        report["benchmark_version"],
    )
    print(
        "dense_version:",
        report["dense_version"],
    )
    print(
        "representation_version:",
        report["representation_version"],
    )
    print(
        "model_id:",
        report["encoder"]["model_id"],
    )
    print(
        "model_revision:",
        report["encoder"]["model_revision"],
    )
    print(
        "device:",
        report["encoder"]["device"],
    )
    print(
        "embedding_dimension:",
        report["encoder"]["embedding_dimension"],
    )
    print(
        "development_cases:",
        summary["cases"],
    )

    print("\n=== DEVELOPMENT SUMMARY ===")

    print(
        json.dumps(
            summary,
            indent=2,
            sort_keys=True,
        )
    )

    print("\n=== BY QUERY TYPE ===")

    print(
        json.dumps(
            report["summary"]["by_query_type"],
            indent=2,
            sort_keys=True,
        )
    )

    print("\n=== DEVELOPMENT CASES ===")

    for case in report["cases"]:
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
