import hashlib
from collections import Counter

from enterprise_genai.data.core_corpus import build_core_corpus
from enterprise_genai.data.evaluation_seed import build_seed_evaluation
from enterprise_genai.data.evaluation_validation import (
    validate_evaluation_ground_truth,
    validate_evaluation_references,
)
from enterprise_genai.data.universe import build_universe

EXPECTED_QUERY_COUNTS = {
    "lexical": 3,
    "semantic": 3,
    "hybrid": 3,
    "sql": 4,
    "graph": 3,
    "multi_source": 3,
    "mixed_tool": 3,
    "insufficient_evidence": 2,
}


def test_seed_contains_24_cases() -> None:
    evaluation = build_seed_evaluation()

    assert len(evaluation.cases) == 24


def test_seed_has_expected_query_distribution() -> None:
    evaluation = build_seed_evaluation()

    counts = Counter(case.query_type for case in evaluation.cases)

    assert dict(counts) == EXPECTED_QUERY_COUNTS


def test_seed_split_is_16_development_8_test() -> None:
    evaluation = build_seed_evaluation()

    counts = Counter(case.split for case in evaluation.cases)

    assert counts == {
        "development": 16,
        "test": 8,
    }


def test_seed_document_references_are_valid() -> None:
    validate_evaluation_references(
        build_seed_evaluation(),
        build_core_corpus(),
    )


def test_seed_answer_ground_truth_is_valid() -> None:
    validate_evaluation_ground_truth(
        build_seed_evaluation(),
        build_universe(),
    )


def test_all_answerable_seed_cases_have_canonical_sources() -> None:
    evaluation = build_seed_evaluation()

    for case in evaluation.cases:
        if case.answerable:
            assert case.answer_source_fact_ids


def test_seed_contains_expected_anchor_answers() -> None:
    cases = {case.query_id: case for case in build_seed_evaluation().cases}

    assert cases["Q-0010"].expected_answer.value == "HelioGrid Energy"
    assert cases["Q-0011"].expected_answer.value == 735_000_000
    assert cases["Q-0014"].expected_answer.value == [
        "Alder Manufacturing",
        "NovaBio Instruments",
    ]
    assert cases["Q-0023"].expected_answer.answer_type == "abstain"


def test_seed_serialization_is_deterministic() -> None:
    first = build_seed_evaluation().model_dump_json(indent=2)
    second = build_seed_evaluation().model_dump_json(indent=2)

    first_hash = hashlib.sha256(first.encode()).hexdigest()

    second_hash = hashlib.sha256(second.encode()).hexdigest()

    assert first_hash == second_hash
