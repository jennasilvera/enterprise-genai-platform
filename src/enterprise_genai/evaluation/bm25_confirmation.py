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
    build_lexical_index_corpus,
)

CONFIRMATION_VERSION = "bm25-document-title-test-confirmation-v1"

SELECTED_REPRESENTATION = "document-title-text-v1"


def build_test_retrieval_evaluation(
    evaluation: EvaluationSet,
) -> EvaluationSet:
    cases = [
        case for case in evaluation.cases if (case.split == "test" and is_retrieval_eligible(case))
    ]

    return EvaluationSet(
        dataset_version=(evaluation.dataset_version),
        evaluation_version=(evaluation.evaluation_version),
        cases=cases,
    )


def run_bm25_test_confirmation(
    evaluation: EvaluationSet,
    chunks: ChunkCorpus,
    documents: DocumentCorpus,
    company_names: Mapping[str, str],
    *,
    config: BM25Config | None = None,
) -> dict[str, Any]:
    """Evaluate the frozen Phase 4B representation on test cases.

    Representation selection is intentionally not configurable here.
    """

    test_evaluation = build_test_retrieval_evaluation(evaluation)

    index_corpus = build_lexical_index_corpus(
        chunks,
        documents,
        company_names,
        representation_version=(SELECTED_REPRESENTATION),
    )

    benchmark = run_bm25_benchmark(
        test_evaluation,
        index_corpus,
        config=config,
    )

    lexical_cases = [case for case in benchmark["cases"] if case["query_type"] == "lexical"]

    lexical_rank_one_guardrail = all(
        case["metrics"]["canonical_reciprocal_rank"] == 1.0 for case in lexical_cases
    )

    return {
        "confirmation_version": (CONFIRMATION_VERSION),
        "selected_representation": (SELECTED_REPRESENTATION),
        "selection_status": ("frozen-before-test-confirmation"),
        "scope": "test-confirmation",
        "lexical_rank_one_guardrail": (lexical_rank_one_guardrail),
        "benchmark": benchmark,
    }
