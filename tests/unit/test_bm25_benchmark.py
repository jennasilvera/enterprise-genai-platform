from enterprise_genai.data.core_corpus import (
    build_core_corpus,
)
from enterprise_genai.data.evaluation_seed import (
    build_seed_evaluation,
)
from enterprise_genai.evaluation.bm25_benchmark import (
    run_bm25_benchmark,
)
from enterprise_genai.retrieval.chunking import (
    build_evidence_chunks,
)


def _report():
    evaluation = build_seed_evaluation()

    chunks = build_evidence_chunks(build_core_corpus())

    return run_bm25_benchmark(
        evaluation,
        chunks,
    )


def test_benchmark_has_expected_case_scope() -> None:
    report = _report()

    assert report["evaluation"]["all_cases"] == 24

    assert report["evaluation"]["retrieval_eligible_cases"] == 14

    assert len(report["evaluation"]["excluded_cases"]) == 10


def test_benchmark_has_expected_retrieval_groups() -> None:
    report = _report()

    by_type = report["summary"]["by_query_type"]

    assert {query_type: summary["cases"] for query_type, summary in by_type.items()} == {
        "hybrid": 3,
        "lexical": 3,
        "mixed_tool": 2,
        "multi_source": 3,
        "semantic": 3,
    }
