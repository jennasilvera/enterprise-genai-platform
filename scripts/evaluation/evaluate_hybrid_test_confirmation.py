import argparse
import hashlib
import json
from pathlib import Path

from sqlalchemy.orm import Session

from enterprise_genai.data.core_corpus import build_core_corpus
from enterprise_genai.data.evaluation_seed import build_seed_evaluation
from enterprise_genai.db.chunk_ingestion import load_chunk_corpus
from enterprise_genai.db.session import engine
from enterprise_genai.evaluation.hybrid_confirmation import (
    run_hybrid_test_confirmation,
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

FROZEN_PHASE6A = Path("artifacts/evaluation/phase6a/rrf-k60-development.json")

FROZEN_PHASE6A_SHA256 = "c0f850e21d25f993f26c58b44d0ace057fbcd23380dce85039f2b4d6c2593c21"

DEFAULT_OUTPUT = Path("artifacts/evaluation/phase6b/rrf-k60-test-confirmation.json")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Confirm the frozen Phase 6A BM25 + E5 RRF retriever on retrieval-eligible test cases."
        )
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


def _load_frozen_phase6a():
    artifact_hash = _sha256(FROZEN_PHASE6A)

    if artifact_hash != FROZEN_PHASE6A_SHA256:
        raise ValueError("Frozen Phase 6A artifact hash does not match preregistration.")

    report = json.loads(FROZEN_PHASE6A.read_text(encoding="utf-8"))

    if report["selected_retriever"] != "hybrid:rrf-k60-v1":
        raise ValueError("Unexpected frozen Phase 6A selected retriever.")

    hybrid = report["hybrid_benchmark"]

    if hybrid["fusion"]["version"] != "rrf-k60-v1":
        raise ValueError("Unexpected frozen fusion version.")

    if hybrid["fusion"]["k"] != 60:
        raise ValueError("Unexpected frozen RRF constant.")

    if hybrid["lexical"]["representation_version"] != "document-title-text-v1":
        raise ValueError("Unexpected frozen lexical representation.")

    if hybrid["lexical"]["bm25_version"] != "bm25-v1":
        raise ValueError("Unexpected frozen BM25 version.")

    if hybrid["lexical"]["tokenizer_version"] != "lexical-tokenizer-v1":
        raise ValueError("Unexpected frozen tokenizer.")

    if hybrid["lexical"]["parameters"]["k1"] != 1.5:
        raise ValueError("Unexpected frozen BM25 k1.")

    if hybrid["lexical"]["parameters"]["b"] != 0.75:
        raise ValueError("Unexpected frozen BM25 b.")

    if hybrid["dense"]["representation_version"] != DENSE_DOCUMENT_TITLE_TEXT_VERSION:
        raise ValueError("Unexpected frozen dense representation.")

    if hybrid["dense"]["dense_version"] != "dense-e5-small-v2-v1":
        raise ValueError("Unexpected frozen dense version.")

    encoder = hybrid["dense"]["encoder"]

    if encoder["model_id"] != "intfloat/e5-small-v2":
        raise ValueError("Unexpected frozen dense model.")

    if encoder["model_revision"] != "ffb93f3bd4047442299a41ebb6fa998a38507c52":
        raise ValueError("Unexpected frozen model revision.")

    return (
        report,
        artifact_hash,
    )


def main() -> None:
    args = parse_args()

    (
        _phase6a,
        phase6a_hash,
    ) = _load_frozen_phase6a()

    documents = build_core_corpus()
    evaluation = build_seed_evaluation()

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

    report = run_hybrid_test_confirmation(
        evaluation,
        lexical_chunks,
        dense_chunks,
        encoder=encoder,
    )

    report["frozen_phase6a_source"] = {
        "path": str(FROZEN_PHASE6A),
        "sha256": phase6a_hash,
    }

    dense_summary = report["dense_reference_benchmark"]["summary"]["retrieval_eligible"]

    hybrid_summary = report["hybrid_benchmark"]["summary"]["retrieval_eligible"]

    print(
        "confirmation_version:",
        report["confirmation_version"],
    )

    print(
        "frozen_selected_retriever:",
        report["frozen_selected_retriever"],
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
        "test_split_status:",
        report["test_split_status"],
    )

    print(
        "test_cases:",
        hybrid_summary["cases"],
    )

    print("\n=== DENSE TEST REFERENCE ===")

    print(
        json.dumps(
            dense_summary,
            indent=2,
            sort_keys=True,
        )
    )

    print("\n=== HYBRID TEST CONFIRMATION ===")

    print(
        json.dumps(
            hybrid_summary,
            indent=2,
            sort_keys=True,
        )
    )

    print("\n=== HYBRID MINUS DENSE ===")

    print(
        json.dumps(
            report["comparison_vs_dense_reference"],
            indent=2,
            sort_keys=True,
        )
    )

    print("\n=== TEST CASE RESULTS ===")

    dense_cases = {case["query_id"]: case for case in report["dense_reference_benchmark"]["cases"]}

    for hybrid_case in report["hybrid_benchmark"]["cases"]:
        query_id = hybrid_case["query_id"]

        dense_case = dense_cases[query_id]

        print(
            query_id,
            hybrid_case["query_type"],
            {
                "dense_ndcg10": (dense_case["metrics"]["ndcg_at_10"]),
                "hybrid_ndcg10": (hybrid_case["metrics"]["ndcg_at_10"]),
                "dense_canonical_rr": (dense_case["metrics"]["canonical_reciprocal_rank"]),
                "hybrid_canonical_rr": (hybrid_case["metrics"]["canonical_reciprocal_rank"]),
                "dense_recall10": (dense_case["metrics"]["recall_at_10"]),
                "hybrid_recall10": (hybrid_case["metrics"]["recall_at_10"]),
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
