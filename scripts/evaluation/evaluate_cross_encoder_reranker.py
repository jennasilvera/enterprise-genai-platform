import argparse
import hashlib
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
from enterprise_genai.evaluation.reranker_benchmark import (
    run_reranker_development_benchmark,
    verify_phase6a_regeneration,
)
from enterprise_genai.evaluation.reranker_selection import (
    select_reranker,
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
from enterprise_genai.retrieval.reranker import (
    CrossEncoderReranker,
)

EXPERIMENT_VERSION = "cross-encoder-reranker-development-v1"

DATASET_VERSION = "northstar-v1"

FROZEN_PHASE6A = Path("artifacts/evaluation/phase6a/rrf-k60-development.json")

FROZEN_PHASE6A_SHA256 = "c0f850e21d25f993f26c58b44d0ace057fbcd23380dce85039f2b4d6c2593c21"

DEFAULT_OUTPUT = Path("artifacts/evaluation/phase7a/cross-encoder-reranker-development.json")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Evaluate one preregistered "
            "cross-encoder reranker over the "
            "frozen Phase 6A RRF candidate "
            "generator on development cases."
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


def _load_frozen_phase6a() -> tuple[
    dict[str, Any],
    str,
]:
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
        raise ValueError("Unexpected frozen RRF k.")

    if hybrid["lexical"]["representation_version"] != "document-title-text-v1":
        raise ValueError("Unexpected frozen lexical representation.")

    if hybrid["dense"]["representation_version"] != DENSE_DOCUMENT_TITLE_TEXT_VERSION:
        raise ValueError("Unexpected frozen dense representation.")

    encoder = hybrid["dense"]["encoder"]

    if encoder["model_id"] != "intfloat/e5-small-v2":
        raise ValueError("Unexpected frozen E5 model.")

    if encoder["model_revision"] != "ffb93f3bd4047442299a41ebb6fa998a38507c52":
        raise ValueError("Unexpected frozen E5 revision.")

    return (
        report,
        artifact_hash,
    )


def _comparison(
    baseline: dict[str, Any],
    candidate: dict[str, Any],
) -> dict[str, dict[str, float]]:
    metrics = (
        "mean_canonical_reciprocal_rank",
        "mean_ndcg_at_10",
        "mean_recall_at_10",
    )

    result = {}

    for metric in metrics:
        baseline_value = float(baseline[metric])

        candidate_value = float(candidate[metric])

        absolute_delta = candidate_value - baseline_value

        relative_delta = absolute_delta / baseline_value if baseline_value != 0.0 else 0.0

        result[metric] = {
            "baseline": (baseline_value),
            "candidate": (candidate_value),
            "absolute_delta": (absolute_delta),
            "relative_delta": (relative_delta),
        }

    return result


def main() -> None:
    args = parse_args()

    (
        frozen_phase6a,
        phase6a_hash,
    ) = _load_frozen_phase6a()

    documents = build_core_corpus()
    evaluation = build_seed_evaluation()
    universe = build_universe()

    company_names = {company.company_id: (company.name) for company in universe.companies}

    with Session(engine) as session:
        chunks = load_chunk_corpus(
            session,
            DATASET_VERSION,
            EVIDENCE_BLOCK_STRATEGY,
        )

    lexical_chunks = build_lexical_index_corpus(
        chunks,
        documents,
        company_names,
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

    reranker = CrossEncoderReranker()

    benchmark = run_reranker_development_benchmark(
        evaluation,
        lexical_chunks,
        dense_chunks,
        encoder=encoder,
        reranker=reranker,
    )

    regeneration = verify_phase6a_regeneration(
        frozen_phase6a,
        benchmark,
    )

    baseline_summary = benchmark["baseline_benchmark"]["summary"]["retrieval_eligible"]

    candidate_summary = benchmark["reranked_benchmark"]["summary"]["retrieval_eligible"]

    selection = select_reranker(
        baseline_summary,
        candidate_summary,
    )

    report = {
        "experiment_version": (EXPERIMENT_VERSION),
        "scope": ("development-selection"),
        "test_split_used": False,
        "frozen_phase6a_source": {
            "path": str(FROZEN_PHASE6A),
            "sha256": (phase6a_hash),
        },
        "phase6a_regeneration": (regeneration),
        "selection_policy": {
            "guardrail": ("mean_recall_at_10 candidate >= baseline"),
            "primary_metric": ("mean_ndcg_at_10"),
            "secondary_metric": ("mean_canonical_reciprocal_rank"),
            "full_tie": ("retain_frozen_rrf"),
        },
        "selection": selection,
        "comparison_vs_frozen_rrf": (
            _comparison(
                baseline_summary,
                candidate_summary,
            )
        ),
        "benchmark": benchmark,
    }

    print(
        "experiment_version:",
        report["experiment_version"],
    )

    print(
        "scope:",
        report["scope"],
    )

    print(
        "phase6a_regeneration:",
        regeneration["verified"],
    )

    print(
        "selected:",
        selection["selected"],
    )

    print(
        "selection_reason:",
        selection["reason"],
    )

    print(
        "guardrail_passed:",
        selection["guardrail_passed"],
    )

    print("\n=== FROZEN RRF DEVELOPMENT ===")

    print(
        json.dumps(
            baseline_summary,
            indent=2,
            sort_keys=True,
        )
    )

    print("\n=== RERANKED DEVELOPMENT ===")

    print(
        json.dumps(
            candidate_summary,
            indent=2,
            sort_keys=True,
        )
    )

    print("\n=== RERANKER MINUS RRF ===")

    print(
        json.dumps(
            report["comparison_vs_frozen_rrf"],
            indent=2,
            sort_keys=True,
        )
    )

    print("\n=== PER QUERY ===")

    baseline_cases = {case["query_id"]: case for case in benchmark["baseline_benchmark"]["cases"]}

    for candidate_case in benchmark["reranked_benchmark"]["cases"]:
        query_id = candidate_case["query_id"]

        baseline_case = baseline_cases[query_id]

        print(
            query_id,
            candidate_case["query_type"],
            {
                "rrf_ndcg10": (baseline_case["metrics"]["ndcg_at_10"]),
                "reranked_ndcg10": (candidate_case["metrics"]["ndcg_at_10"]),
                "rrf_rr": (baseline_case["metrics"]["canonical_reciprocal_rank"]),
                "reranked_rr": (candidate_case["metrics"]["canonical_reciprocal_rank"]),
                "rrf_recall10": (baseline_case["metrics"]["recall_at_10"]),
                "reranked_recall10": (candidate_case["metrics"]["recall_at_10"]),
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
