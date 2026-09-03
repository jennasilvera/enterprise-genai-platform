import json
from pathlib import Path

from enterprise_genai.data.core_corpus import (
    build_core_corpus,
)
from enterprise_genai.data.evaluation_seed import (
    build_seed_evaluation,
)
from enterprise_genai.data.universe import (
    build_universe,
)
from enterprise_genai.evaluation.bm25_ablation import (
    build_development_retrieval_evaluation,
    run_bm25_representation_experiment,
)
from enterprise_genai.retrieval.chunking import (
    build_evidence_chunks,
)

BASELINE_PATH = Path("artifacts/evaluation/bm25_baseline.json")


def _run_text_only():
    documents = build_core_corpus()

    chunks = build_evidence_chunks(documents)

    universe = build_universe()

    company_names = {company.company_id: company.name for company in universe.companies}

    return run_bm25_representation_experiment(
        build_seed_evaluation(),
        chunks,
        documents,
        company_names,
        representation_version=("text-only-v1"),
    )


def test_ablation_scope_is_development_only() -> None:
    evaluation = build_development_retrieval_evaluation(build_seed_evaluation())

    assert len(evaluation.cases) == 10

    assert all(case.split == "development" for case in evaluation.cases)


def test_text_only_matches_frozen_development_summary() -> None:
    experiment = _run_text_only()

    actual = experiment["benchmark"]["summary"]["retrieval_eligible"]

    frozen = json.loads(BASELINE_PATH.read_text(encoding="utf-8"))

    expected = frozen["summary"]["by_split"]["development"]

    assert actual == expected


def test_text_only_matches_frozen_development_cases() -> None:
    experiment = _run_text_only()

    actual = experiment["benchmark"]["cases"]

    frozen = json.loads(BASELINE_PATH.read_text(encoding="utf-8"))

    expected = [case for case in frozen["cases"] if case["split"] == "development"]

    assert actual == expected


def test_text_only_preserves_lexical_rank_one_guardrail() -> None:
    experiment = _run_text_only()

    assert experiment["lexical_rank_one_guardrail"]
