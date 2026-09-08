import argparse
import hashlib
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
from enterprise_genai.evaluation.dense_benchmark import (
    build_development_retrieval_evaluation,
)
from enterprise_genai.evaluation.hybrid_rrf import (
    run_hybrid_rrf_benchmark,
)
from enterprise_genai.evaluation.hybrid_selection import (
    compare_hybrid_to_dense,
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
from enterprise_genai.retrieval.lexical_representation import (
    build_lexical_index_corpus,
)

DATASET_VERSION = "northstar-v1"

FROZEN_BM25_ARTIFACT = Path("artifacts/evaluation/phase4b/document-title-text-v1.json")

FROZEN_BM25_SHA256 = "c1d36faf093d18053a733beb868933da71e902d741ae81ed885efb8f0104b3c2"

FROZEN_DENSE_ARTIFACT = Path(
    "artifacts/evaluation/phase5b/e5-document-title-text-v1-development.json"
)

FROZEN_DENSE_SHA256 = "ed406dacfec38bd97de7ccb42ad84b6d2ab6e00332e3b52b1cec171593d67f87"

DEFAULT_OUTPUT = Path("artifacts/evaluation/phase6a/rrf-k60-development.json")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=("Evaluate the preregistered BM25 + dense RRF k=60 development baseline.")
    )

    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
    )

    return parser.parse_args()


def _sha256(
    path: Path,
) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as handle:
        for block in iter(
            lambda: handle.read(1024 * 1024),
            b"",
        ):
            digest.update(block)

    return digest.hexdigest()


def _load_frozen_sources():
    bm25_hash = _sha256(FROZEN_BM25_ARTIFACT)

    dense_hash = _sha256(FROZEN_DENSE_ARTIFACT)

    if bm25_hash != FROZEN_BM25_SHA256:
        raise ValueError("Frozen BM25 artifact hash does not match preregistration.")

    if dense_hash != FROZEN_DENSE_SHA256:
        raise ValueError("Frozen dense artifact hash does not match preregistration.")

    bm25 = json.loads(FROZEN_BM25_ARTIFACT.read_text(encoding="utf-8"))

    dense = json.loads(FROZEN_DENSE_ARTIFACT.read_text(encoding="utf-8"))

    if bm25["representation_version"] != "document-title-text-v1":
        raise ValueError("Unexpected frozen BM25 representation.")

    if bm25["benchmark"]["bm25_version"] != "bm25-v1":
        raise ValueError("Unexpected frozen BM25 version.")

    if dense["selected_representation"] != DENSE_DOCUMENT_TITLE_TEXT_VERSION:
        raise ValueError("Unexpected frozen dense selected representation.")

    return (
        bm25,
        dense,
        bm25_hash,
        dense_hash,
    )


def main() -> None:
    args = parse_args()

    (
        _bm25_reference,
        dense_reference,
        bm25_hash,
        dense_hash,
    ) = _load_frozen_sources()

    documents = build_core_corpus()

    evaluation = build_development_retrieval_evaluation(build_seed_evaluation())

    with Session(engine) as session:
        chunks = load_chunk_corpus(
            session,
            DATASET_VERSION,
            EVIDENCE_BLOCK_STRATEGY,
        )

    lexical_chunks = build_lexical_index_corpus(
        chunks,
        documents,
        {},
        representation_version=("document-title-text-v1"),
    )

    dense_chunks = build_dense_index_corpus(
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

    hybrid = run_hybrid_rrf_benchmark(
        evaluation,
        lexical_chunks,
        dense_chunks,
        encoder=encoder,
    )

    selection = compare_hybrid_to_dense(
        dense_reference,
        hybrid,
    )

    report = {
        **selection,
        "source_artifacts": {
            "bm25": {
                "path": str(FROZEN_BM25_ARTIFACT),
                "sha256": bm25_hash,
            },
            "dense": {
                "path": str(FROZEN_DENSE_ARTIFACT),
                "sha256": dense_hash,
            },
        },
        "hybrid_benchmark": (hybrid),
    }

    print(
        "experiment_version:",
        report["experiment_version"],
    )

    print(
        "hybrid_candidate:",
        report["hybrid_candidate"],
    )

    print(
        "dense_reference:",
        report["dense_reference"],
    )

    print(
        "selected_retriever:",
        report["selected_retriever"],
    )

    print("\n=== COMPARISON ===")

    print(
        json.dumps(
            report["comparison"],
            indent=2,
            sort_keys=True,
        )
    )

    print("\n=== HYBRID SUMMARY ===")

    print(
        json.dumps(
            hybrid["summary"]["retrieval_eligible"],
            indent=2,
            sort_keys=True,
        )
    )

    print("\n=== HYBRID CASES ===")

    for case in hybrid["cases"]:
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
                    result["rrf_score"],
                    8,
                ),
                result["evidence_id"],
                {
                    "bm25_rank": (result["bm25_rank"]),
                    "dense_rank": (result["dense_rank"]),
                },
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
