import pytest

from enterprise_genai.execution.contracts import (
    GraphEdge,
    GraphNode,
    GraphPayload,
    PortfolioGraphPredicate,
    PortfolioGraphQuery,
)


def _company_node(
    company_id: str,
    name: str,
) -> GraphNode:
    return GraphNode(
        entity_type="company",
        entity_id=company_id,
        name=name,
    )


def _supplier_node() -> GraphNode:
    return GraphNode(
        entity_type="supplier",
        entity_id="SUP-005",
        name="TitaniumWorks GmbH",
        attributes={
            "country": "Germany",
        },
    )


def _supplier_edge() -> GraphEdge:
    return GraphEdge(
        relationship_type="company_supplier",
        relationship_id="CS-003",
        source_type="company",
        source_id="PC-002",
        target_type="supplier",
        target_id="SUP-005",
        attributes={
            "criticality": "critical",
            "single_source": True,
            "relationship_status": "at_risk",
        },
    )


def test_supplier_predicate_supports_country_and_criticality() -> None:
    predicate = PortfolioGraphPredicate(
        relationship_type="company_supplier",
        target_country="Germany",
        criticality="critical",
    )

    assert predicate.target_country == "Germany"
    assert predicate.criticality == "critical"


def test_customer_predicate_rejects_supplier_only_fields() -> None:
    with pytest.raises(
        ValueError,
        match="supplier-only",
    ):
        PortfolioGraphPredicate(
            relationship_type="company_customer",
            target_country="Germany",
            criticality="critical",
        )


def test_predicate_requires_at_least_one_filter() -> None:
    with pytest.raises(
        ValueError,
        match="at least one filter",
    ):
        PortfolioGraphPredicate(
            relationship_type="company_supplier",
        )


def test_query_supports_distinct_existential_supplier_predicates() -> None:
    query = PortfolioGraphQuery(
        predicates=(
            PortfolioGraphPredicate(
                relationship_type=("company_supplier"),
                target_country="Germany",
                criticality="critical",
            ),
            PortfolioGraphPredicate(
                relationship_type=("company_supplier"),
                target_country=("Switzerland"),
            ),
        )
    )

    assert len(query.predicates) == 2

    assert query.predicates[0].target_country == "Germany"

    assert query.predicates[1].target_country == "Switzerland"


def test_query_supports_optional_candidate_company_scope() -> None:
    query = PortfolioGraphQuery(
        predicates=(
            PortfolioGraphPredicate(
                relationship_type=("company_customer"),
                target_country="Germany",
            ),
        ),
        candidate_company_ids=(
            "PC-002",
            "PC-006",
        ),
    )

    assert query.candidate_company_ids == (
        "PC-002",
        "PC-006",
    )


def test_query_rejects_duplicate_predicates_and_candidates() -> None:
    predicate = PortfolioGraphPredicate(
        relationship_type=("company_supplier"),
        target_country="Germany",
    )

    with pytest.raises(
        ValueError,
        match="duplicate predicates",
    ):
        PortfolioGraphQuery(
            predicates=(
                predicate,
                predicate,
            )
        )

    with pytest.raises(
        ValueError,
        match="candidate_company_ids",
    ):
        PortfolioGraphQuery(
            predicates=(predicate,),
            candidate_company_ids=(
                "PC-002",
                "PC-002",
            ),
        )


def test_graph_payload_exposes_matched_company_ids() -> None:
    payload = GraphPayload(
        nodes=(
            _company_node(
                "PC-002",
                "Alder Manufacturing",
            ),
            _supplier_node(),
        ),
        edges=(_supplier_edge(),),
        matched_company_ids=("PC-002",),
    )

    assert payload.matched_company_ids == ("PC-002",)


def test_graph_payload_rejects_invalid_matched_company_set() -> None:
    with pytest.raises(
        ValueError,
        match="company node",
    ):
        GraphPayload(
            nodes=(_supplier_node(),),
            edges=(_supplier_edge(),),
            matched_company_ids=("PC-002",),
        )

    with pytest.raises(
        ValueError,
        match="deterministic",
    ):
        GraphPayload(
            nodes=(
                _company_node(
                    "PC-008",
                    "NovaBio Instruments",
                ),
                _company_node(
                    "PC-002",
                    "Alder Manufacturing",
                ),
                _supplier_node(),
            ),
            edges=(_supplier_edge(),),
            matched_company_ids=(
                "PC-008",
                "PC-002",
            ),
        )


def test_no_matches_is_distinct_empty_state() -> None:
    payload = GraphPayload(
        nodes=(),
        edges=(),
        matched_company_ids=(),
        empty_reason="no_matches",
    )

    assert payload.empty_reason == "no_matches"

    with pytest.raises(
        ValueError,
        match="no graph nodes",
    ):
        GraphPayload(
            nodes=(
                _company_node(
                    "PC-002",
                    "Alder Manufacturing",
                ),
            ),
            edges=(),
            matched_company_ids=(),
            empty_reason="no_matches",
        )
