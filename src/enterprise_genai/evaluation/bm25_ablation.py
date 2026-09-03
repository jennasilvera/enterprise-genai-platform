from collections.abc import Mapping
from typing import Any

from enterprise_genai.data.chunk_models import (
    ChunkCorpus,
)
from enterprise_genai.data.document_models import (
    DocumentCorpus,
)
from enterprise_genai.data.evaluation_models import (
    EvaluationSet,
)
from enterprise_genai.evaluation.bm25_benchmark import (
    is_retrieval_eligible,
    run_bm25_benchmark,
)
from enterprise_genai.retrieval.bm25 import (
    BM25Config,
)
from enterprise_genai.retrieval.lexical_representation import (
    LexicalRepresentationVersion,
    build_lexical_index_corpus,
)


def build_development_retrieval_evaluation(
    evaluation: EvaluationSet,
) -> EvaluationSet:
    cases = [
        case
        for case in evaluation.cases
        if (case.split == "development" and is_retrieval_eligible(case))
    ]

    return EvaluationSet(
        dataset_version=(evaluation.dataset_version),
        evaluation_version=(evaluation.evaluation_version),
        cases=cases,
    )


def run_bm25_representation_experiment(
    evaluation: EvaluationSet,
    chunks: ChunkCorpus,
    documents: DocumentCorpus,
    company_names: Mapping[str, str],
    *,
    representation_version: (LexicalRepresentationVersion),
    config: BM25Config | None = None,
) -> dict[str, Any]:
    development_evaluation = build_development_retrieval_evaluation(evaluation)

    index_corpus = build_lexical_index_corpus(
        chunks,
        documents,
        company_names,
        representation_version=(representation_version),
    )

    report = run_bm25_benchmark(
        development_evaluation,
        index_corpus,
        config=config,
    )

    lexical_cases = [case for case in report["cases"] if case["query_type"] == "lexical"]

    lexical_rank_one_guardrail = all(
        case["metrics"]["canonical_reciprocal_rank"] == 1.0 for case in lexical_cases
    )

    return {
        "experiment_version": ("bm25-lexical-representation-ablation-v1"),
        "representation_version": (representation_version),
        "scope": "development-only",
        "selection_policy": {
            "primary": ("mean_ndcg_at_10"),
            "secondary": [
                "mean_canonical_reciprocal_rank",
                "mean_recall_at_10",
            ],
            "guardrail": ("all development lexical canonical evidence remains rank 1"),
        },
        "lexical_rank_one_guardrail": (lexical_rank_one_guardrail),
        "benchmark": report,
    }
