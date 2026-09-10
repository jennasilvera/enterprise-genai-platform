from collections import Counter

from enterprise_genai.data.routing_challenge_seed import (
    ANCHORS,
    FAMILIES,
    ROUTING_CHALLENGE_VERSION,
    build_routing_challenge,
    routing_challenge_sha256,
)
from enterprise_genai.data.routing_seed import (
    build_routing_seed,
)


def test_challenge_identity_and_size() -> None:
    routing = build_routing_challenge()

    assert routing.dataset_version == "northstar-v1"

    assert routing.routing_version == ROUTING_CHALLENGE_VERSION

    assert len(routing.cases) == 84


def test_challenge_is_locked_holdout_only() -> None:
    routing = build_routing_challenge()

    assert {case.split for case in routing.cases} == {"locked_holdout"}


def test_challenge_routes_are_balanced() -> None:
    routing = build_routing_challenge()

    counts = Counter(case.route_label for case in routing.cases)

    assert len(counts) == 7

    assert set(counts.values()) == {12}


def test_challenge_template_families_are_balanced() -> None:
    routing = build_routing_challenge()

    counts = Counter(case.template_family for case in routing.cases)

    assert len(counts) == 21

    assert set(counts.values()) == {4}

    assert len(FAMILIES) == 21


def test_challenge_uses_reserved_company_anchors() -> None:
    routing = build_routing_challenge()

    expected_ids = {
        "PC-003",
        "PC-004",
        "PC-006",
        "PC-007",
    }

    assert {anchor.company_id for anchor in ANCHORS} == expected_ids

    observed_ids = {entity_id for case in routing.cases for entity_id in case.source_entity_ids}

    assert observed_ids == expected_ids


def test_challenge_has_no_exact_question_overlap_with_original() -> None:
    challenge = build_routing_challenge()

    original = build_routing_seed()

    challenge_questions = {case.question for case in challenge.cases}

    original_questions = {case.question for case in original.cases}

    assert not (challenge_questions & original_questions)


def test_challenge_avoids_direct_tool_instruction_language() -> None:
    routing = build_routing_challenge()

    forbidden = (
        "use retrieval",
        "use sql",
        "use graph",
        "retrieval tool",
        "sql tool",
        "graph tool",
        "relationship network",
        "relationship path",
        "traverse from",
        "structured performance",
        "narrative evidence",
        "vector search",
        "database query",
    )

    for case in routing.cases:
        text = case.question.casefold()

        for phrase in forbidden:
            assert phrase not in text, (
                case.routing_id,
                phrase,
                case.question,
            )


def test_challenge_questions_are_unique() -> None:
    routing = build_routing_challenge()

    questions = [case.question for case in routing.cases]

    assert len(questions) == len(set(questions))


def test_challenge_is_deterministic() -> None:
    first = build_routing_challenge()

    second = build_routing_challenge()

    assert first.model_dump(mode="json") == second.model_dump(mode="json")

    assert routing_challenge_sha256(first) == routing_challenge_sha256(second)


def test_challenge_matches_frozen_fingerprint() -> None:
    routing = build_routing_challenge()

    assert (
        routing_challenge_sha256(routing)
        == "e1fc84e80e5cd27cc311da4392e3c9d46375777a27c81bdc5e35e37b5b131867"
    )
