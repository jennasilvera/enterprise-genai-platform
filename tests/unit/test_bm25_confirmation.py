from enterprise_genai.data.core_corpus import (
    build_core_corpus,
)
from enterprise_genai.data.evaluation_seed import (
    build_seed_evaluation,
)
from enterprise_genai.data.universe import (
    build_universe,
)
from enterprise_genai.evaluation.bm25_confirmation import (
    SELECTED_REPRESENTATION,
    build_test_retrieval_evaluation,
    run_bm25_test_confirmation,
)
from enterprise_genai.retrieval.chunking import (
    build_evidence_chunks,
)


def _run_confirmation():
    documents = build_core_corpus()

    chunks = build_evidence_chunks(documents)

    universe = build_universe()

    company_names = {company.company_id: company.name for company in universe.companies}

    return run_bm25_test_confirmation(
        build_seed_evaluation(),
        chunks,
        documents,
        company_names,
    )


def test_confirmation_representation_is_frozen() -> None:
    assert SELECTED_REPRESENTATION == ("document-title-text-v1")


def test_confirmation_scope_contains_only_test_cases() -> None:
    evaluation = build_test_retrieval_evaluation(build_seed_evaluation())

    assert len(evaluation.cases) == 4

    assert all(case.split == "test" for case in evaluation.cases)


def test_confirmation_has_expected_test_queries() -> None:
    evaluation = build_test_retrieval_evaluation(build_seed_evaluation())

    assert {case.query_id for case in evaluation.cases} == {
        "Q-0003",
        "Q-0005",
        "Q-0007",
        "Q-0018",
    }


def test_confirmation_report_records_frozen_selection() -> None:
    report = _run_confirmation()

    assert report["selected_representation"] == "document-title-text-v1"

    assert report["selection_status"] == ("frozen-before-test-confirmation")

    assert report["scope"] == ("test-confirmation")

    assert report["benchmark"]["summary"]["retrieval_eligible"]["cases"] == 4
