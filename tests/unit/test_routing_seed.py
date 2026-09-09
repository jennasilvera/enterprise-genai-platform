from collections import Counter

from enterprise_genai.data.evaluation_seed import (
    build_seed_evaluation,
)
from enterprise_genai.data.routing_models import (
    VALID_ROUTE_LABELS,
    canonical_route_label,
    normalize_legacy_required_tools,
)
from enterprise_genai.data.routing_seed import (
    ROUTING_VERSION,
    build_routing_seed,
    routing_seed_sha256,
)


def test_routing_seed_identity() -> None:
    routing = build_routing_seed()

    assert routing.dataset_version == "northstar-v1"

    assert routing.routing_version == ROUTING_VERSION

    assert len(routing.cases) == 168


def test_split_counts_are_fixed() -> None:
    routing = build_routing_seed()

    counts = Counter(case.split for case in routing.cases)

    assert counts == {
        "train": 112,
        "development": 28,
        "locked_holdout": 28,
    }


def test_route_classes_are_balanced() -> None:
    routing = build_routing_seed()

    overall = Counter(case.route_label for case in routing.cases)

    assert set(overall) == set(VALID_ROUTE_LABELS)

    assert set(overall.values()) == {24}

    for split, expected in (
        (
            "train",
            16,
        ),
        (
            "development",
            4,
        ),
        (
            "locked_holdout",
            4,
        ),
    ):
        counts = Counter(case.route_label for case in routing.cases if case.split == split)

        assert set(counts.values()) == {expected}

        assert set(counts) == set(VALID_ROUTE_LABELS)


def test_template_families_are_split_disjoint() -> None:
    routing = build_routing_seed()

    family_to_splits: dict[
        str,
        set[str],
    ] = {}

    for case in routing.cases:
        family_to_splits.setdefault(
            case.template_family,
            set(),
        ).add(case.split)

    assert len(family_to_splits) == 42

    assert all(len(splits) == 1 for splits in family_to_splits.values())


def test_routing_questions_are_not_existing_eval_questions() -> None:
    routing = build_routing_seed()

    evaluation = build_seed_evaluation()

    routing_questions = {case.question for case in routing.cases}

    evaluation_questions = {case.question for case in evaluation.cases}

    assert not (routing_questions & evaluation_questions)


def test_existing_eval_tools_normalize_to_valid_routes() -> None:
    evaluation = build_seed_evaluation()

    for case in evaluation.cases:
        normalized = normalize_legacy_required_tools(case.required_tools)

        label = canonical_route_label(normalized)

        assert label in VALID_ROUTE_LABELS


def test_routing_seed_is_deterministic() -> None:
    first = build_routing_seed()
    second = build_routing_seed()

    assert first.model_dump(mode="json") == second.model_dump(mode="json")

    assert routing_seed_sha256(first) == routing_seed_sha256(second)


def test_development_and_holdout_avoid_direct_tool_instruction_cues() -> None:
    routing = build_routing_seed()

    forbidden_phrases = (
        "narrative evidence",
        "written evidence",
        "written materials",
        "structured performance",
        "relationship network",
        "relationship path",
        "use the relationship",
        "using the relationship",
        "traverse from",
        "calculate ",
    )

    for case in routing.cases:
        if case.split not in {
            "development",
            "locked_holdout",
        }:
            continue

        text = case.question.casefold()

        for phrase in forbidden_phrases:
            assert phrase not in text, (
                case.routing_id,
                case.route_label,
                phrase,
                case.question,
            )


def test_routing_seed_matches_frozen_fingerprint() -> None:
    routing = build_routing_seed()

    assert (
        routing_seed_sha256(routing)
        == "995f707a4cc6393f0e916f903cc57f9aec6fbabb3c43a00a78e318ca505b6912"
    )
