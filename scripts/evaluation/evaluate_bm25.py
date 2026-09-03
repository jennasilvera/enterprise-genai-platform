import argparse
import json
from pathlib import Path

from sqlalchemy.orm import Session

from enterprise_genai.data.evaluation_seed import (
    build_seed_evaluation,
)
from enterprise_genai.db.chunk_ingestion import (
    chunk_corpus_fingerprint,
    load_chunk_corpus,
)
from enterprise_genai.db.session import engine
from enterprise_genai.evaluation.bm25_benchmark import (
    run_bm25_benchmark,
)
from enterprise_genai.retrieval.bm25 import (
    BM25Config,
)
from enterprise_genai.retrieval.chunking import (
    EVIDENCE_BLOCK_STRATEGY,
)

DATASET_VERSION = "northstar-v1"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=("Run the deterministic Northstar BM25 retrieval baseline.")
    )

    parser.add_argument(
        "--k1",
        type=float,
        default=1.5,
    )

    parser.add_argument(
        "--b",
        type=float,
        default=0.75,
    )

    parser.add_argument(
        "--output",
        type=Path,
    )

    return parser.parse_args()


def main() -> None:
    args = parse_args()

    evaluation = build_seed_evaluation()

    with Session(engine) as session:
        chunks = load_chunk_corpus(
            session,
            DATASET_VERSION,
            EVIDENCE_BLOCK_STRATEGY,
        )

    fingerprint = chunk_corpus_fingerprint(chunks)

    report = run_bm25_benchmark(
        evaluation,
        chunks,
        config=BM25Config(
            k1=args.k1,
            b=args.b,
        ),
    )

    report["chunk_corpus_fingerprint"] = fingerprint

    print(
        "benchmark_version:",
        report["benchmark_version"],
    )

    print(
        "dataset_version:",
        report["dataset_version"],
    )

    print(
        "evaluation_version:",
        report["evaluation_version"],
    )

    print(
        "chunk_strategy_version:",
        report["chunk_strategy_version"],
    )

    print(
        "chunk_corpus_fingerprint:",
        fingerprint,
    )

    print(
        "bm25_parameters:",
        report["bm25_parameters"],
    )

    print(
        "corpus:",
        report["corpus"],
    )

    print(
        "evaluation:",
        {
            "all_cases": report["evaluation"]["all_cases"],
            "retrieval_eligible_cases": (report["evaluation"]["retrieval_eligible_cases"]),
            "excluded_cases": len(report["evaluation"]["excluded_cases"]),
        },
    )

    print("\n=== OVERALL ===")

    print(
        json.dumps(
            report["summary"]["retrieval_eligible"],
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

    print("\n=== BY SPLIT ===")

    print(
        json.dumps(
            report["summary"]["by_split"],
            indent=2,
            sort_keys=True,
        )
    )

    print("\n=== CASE RESULTS ===")

    for case in report["cases"]:
        print(
            case["query_id"],
            case["query_type"],
            case["split"],
            case["metrics"],
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
            "\nreport_written:",
            args.output,
        )


if __name__ == "__main__":
    main()
