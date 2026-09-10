from __future__ import annotations

from collections.abc import Callable
from time import perf_counter

from sqlalchemy import Select, and_, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from enterprise_genai.db.models import (
    CanonicalFactRow,
    CompanyCustomerRow,
    CompanyRow,
    CompanySupplierRow,
    CustomerRow,
    SupplierRow,
)
from enterprise_genai.execution.contracts import (
    GraphEdge,
    GraphEntityType,
    GraphNode,
    GraphPayload,
    GraphQuery,
    GraphRelation,
    JsonScalar,
    PortfolioGraphPredicate,
    PortfolioGraphQuery,
    ToolExecutionResult,
)


class GraphDataIntegrityError(RuntimeError):
    """Persisted relationship graph violates its provenance contract."""


_ENTITY_FACT_TYPES: dict[
    GraphEntityType,
    str,
] = {
    "company": "company",
    "customer": "customer",
    "supplier": "supplier",
}


_ENTITY_MODELS: dict[
    GraphEntityType,
    type[CompanyRow | CustomerRow | SupplierRow],
] = {
    "company": CompanyRow,
    "customer": CustomerRow,
    "supplier": SupplierRow,
}


_RELATION_TARGET_TYPE: dict[
    GraphRelation,
    GraphEntityType,
] = {
    "company_customers": "customer",
    "company_suppliers": "supplier",
    "customer_company": "company",
    "supplier_company": "company",
}


def _relationship_model(
    relation: GraphRelation,
) -> type[CompanyCustomerRow | CompanySupplierRow]:
    if relation in (
        "company_customers",
        "customer_company",
    ):
        return CompanyCustomerRow

    return CompanySupplierRow


def build_relationship_statement(
    *,
    dataset_version: str,
    relation: GraphRelation,
    frontier_ids: tuple[str, ...],
) -> Select[tuple[CompanyCustomerRow | CompanySupplierRow]]:
    """Build deterministic parameterized expansion SQL."""

    if not frontier_ids:
        raise ValueError("Graph frontier must not be empty.")

    model = _relationship_model(relation)

    if relation == "company_customers":
        lookup_column = CompanyCustomerRow.company_id

    elif relation == "customer_company":
        lookup_column = CompanyCustomerRow.customer_id

    elif relation == "company_suppliers":
        lookup_column = CompanySupplierRow.company_id

    else:
        lookup_column = CompanySupplierRow.supplier_id

    return (
        select(model)
        .where(
            model.dataset_version == dataset_version,
            lookup_column.in_(frontier_ids),
        )
        .order_by(
            lookup_column,
            model.relationship_id,
        )
    )


def build_portfolio_company_statement(
    query: PortfolioGraphQuery,
) -> Select[tuple[CompanyRow]]:
    """Resolve the bounded portfolio company scope."""

    statement = select(CompanyRow).where(CompanyRow.dataset_version == query.dataset_version)

    if query.candidate_company_ids:
        statement = statement.where(CompanyRow.company_id.in_(query.candidate_company_ids))

    return statement.order_by(CompanyRow.company_id)


def build_portfolio_predicate_statement(
    *,
    dataset_version: str,
    predicate: PortfolioGraphPredicate,
    company_ids: tuple[str, ...],
) -> Select[tuple[CompanyCustomerRow | CompanySupplierRow]]:
    """Build one bounded existential predicate query."""

    if not company_ids:
        raise ValueError("Portfolio graph company scope must not be empty.")

    if predicate.relationship_type == "company_customer":
        statement = (
            select(CompanyCustomerRow)
            .join(
                CustomerRow,
                and_(
                    CustomerRow.dataset_version == CompanyCustomerRow.dataset_version,
                    CustomerRow.customer_id == CompanyCustomerRow.customer_id,
                ),
            )
            .where(
                CompanyCustomerRow.dataset_version == dataset_version,
                CompanyCustomerRow.company_id.in_(company_ids),
            )
        )

        if predicate.target_country is not None:
            statement = statement.where(CustomerRow.country == predicate.target_country)

        if predicate.relationship_status is not None:
            statement = statement.where(
                CompanyCustomerRow.relationship_status == predicate.relationship_status
            )

        return statement.order_by(
            CompanyCustomerRow.company_id,
            CompanyCustomerRow.relationship_id,
        )

    statement = (
        select(CompanySupplierRow)
        .join(
            SupplierRow,
            and_(
                SupplierRow.dataset_version == CompanySupplierRow.dataset_version,
                SupplierRow.supplier_id == CompanySupplierRow.supplier_id,
            ),
        )
        .where(
            CompanySupplierRow.dataset_version == dataset_version,
            CompanySupplierRow.company_id.in_(company_ids),
        )
    )

    if predicate.target_country is not None:
        statement = statement.where(SupplierRow.country == predicate.target_country)

    if predicate.criticality is not None:
        statement = statement.where(CompanySupplierRow.criticality == predicate.criticality)

    if predicate.single_source is not None:
        statement = statement.where(CompanySupplierRow.single_source == predicate.single_source)

    if predicate.relationship_status is not None:
        statement = statement.where(
            CompanySupplierRow.relationship_status == predicate.relationship_status
        )

    return statement.order_by(
        CompanySupplierRow.company_id,
        CompanySupplierRow.relationship_id,
    )


def _next_entity_id(
    relation: GraphRelation,
    row: (CompanyCustomerRow | CompanySupplierRow),
) -> str:
    if relation == "company_customers":
        if not isinstance(
            row,
            CompanyCustomerRow,
        ):
            raise GraphDataIntegrityError("company_customers returned unexpected row type.")

        return row.customer_id

    if relation == "customer_company":
        if not isinstance(
            row,
            CompanyCustomerRow,
        ):
            raise GraphDataIntegrityError("customer_company returned unexpected row type.")

        return row.company_id

    if relation == "company_suppliers":
        if not isinstance(
            row,
            CompanySupplierRow,
        ):
            raise GraphDataIntegrityError("company_suppliers returned unexpected row type.")

        return row.supplier_id

    if not isinstance(
        row,
        CompanySupplierRow,
    ):
        raise GraphDataIntegrityError("supplier_company returned unexpected row type.")

    return row.company_id


def _node_sort_key(
    node: GraphNode,
) -> tuple[
    int,
    str,
]:
    order = {
        "company": 0,
        "customer": 1,
        "supplier": 2,
    }

    return (
        order[node.entity_type],
        node.entity_id,
    )


def _edge_sort_key(
    edge: GraphEdge,
) -> tuple[
    int,
    str,
]:
    order = {
        "company_customer": 0,
        "company_supplier": 1,
    }

    return (
        order[edge.relationship_type],
        edge.relationship_id,
    )


class RelationalGraphExecutor:
    """Bounded graph traversal over canonical relational truth."""

    def __init__(
        self,
        session: Session,
        *,
        clock: Callable[
            [],
            float,
        ] = perf_counter,
    ) -> None:
        self._session = session
        self._clock = clock

    def _duration_ms(
        self,
        started_at: float,
    ) -> float:
        return max(
            0.0,
            (self._clock() - started_at) * 1000.0,
        )

    def _validate_fact(
        self,
        *,
        dataset_version: str,
        fact_id: str,
        expected_type: str,
    ) -> None:
        fact = self._session.get(
            CanonicalFactRow,
            (
                dataset_version,
                fact_id,
            ),
        )

        if fact is None:
            raise GraphDataIntegrityError(
                f"Graph object is missing canonical fact registry entry: {fact_id}."
            )

        if fact.fact_type != expected_type:
            raise GraphDataIntegrityError(
                "Canonical fact has unexpected "
                "fact_type: "
                f"{fact_id!r} expected "
                f"{expected_type!r}, observed "
                f"{fact.fact_type!r}."
            )

    def _load_node(
        self,
        *,
        dataset_version: str,
        entity_type: GraphEntityType,
        entity_id: str,
    ) -> GraphNode | None:
        model = _ENTITY_MODELS[entity_type]

        row = self._session.get(
            model,
            (
                dataset_version,
                entity_id,
            ),
        )

        if row is None:
            return None

        self._validate_fact(
            dataset_version=(dataset_version),
            fact_id=entity_id,
            expected_type=(_ENTITY_FACT_TYPES[entity_type]),
        )

        if entity_type == "company":
            if not isinstance(
                row,
                CompanyRow,
            ):
                raise GraphDataIntegrityError("Company lookup returned unexpected row type.")

            attributes: dict[
                str,
                JsonScalar,
            ] = {
                "fund_id": row.fund_id,
                "industry": row.industry,
                "headquarters_country": (row.headquarters_country),
                "investment_date": (row.investment_date.isoformat()),
                "ownership_pct": (row.ownership_pct),
            }

            name = row.name

        elif entity_type == "customer":
            if not isinstance(
                row,
                CustomerRow,
            ):
                raise GraphDataIntegrityError("Customer lookup returned unexpected row type.")

            attributes = {
                "industry": row.industry,
                "country": row.country,
            }

            name = row.name

        else:
            if not isinstance(
                row,
                SupplierRow,
            ):
                raise GraphDataIntegrityError("Supplier lookup returned unexpected row type.")

            attributes = {
                "category": row.category,
                "country": row.country,
            }

            name = row.name

        return GraphNode(
            entity_type=entity_type,
            entity_id=entity_id,
            name=name,
            attributes=attributes,
            canonical_fact_ids=(entity_id,),
        )

    def _edge(
        self,
        *,
        dataset_version: str,
        row: (CompanyCustomerRow | CompanySupplierRow),
    ) -> GraphEdge:
        if isinstance(
            row,
            CompanyCustomerRow,
        ):
            self._validate_fact(
                dataset_version=(dataset_version),
                fact_id=(row.relationship_id),
                expected_type=("company_customer"),
            )

            return GraphEdge(
                relationship_type=("company_customer"),
                relationship_id=(row.relationship_id),
                source_type="company",
                source_id=row.company_id,
                target_type="customer",
                target_id=row.customer_id,
                attributes={
                    "revenue_share_pct": (row.revenue_share_pct),
                    "relationship_start_date": (row.relationship_start_date.isoformat()),
                    "relationship_status": (row.relationship_status),
                },
                canonical_fact_ids=(row.relationship_id,),
            )

        if isinstance(
            row,
            CompanySupplierRow,
        ):
            self._validate_fact(
                dataset_version=(dataset_version),
                fact_id=(row.relationship_id),
                expected_type=("company_supplier"),
            )

            return GraphEdge(
                relationship_type=("company_supplier"),
                relationship_id=(row.relationship_id),
                source_type="company",
                source_id=row.company_id,
                target_type="supplier",
                target_id=row.supplier_id,
                attributes={
                    "spend_share_pct": (row.spend_share_pct),
                    "criticality": (row.criticality),
                    "single_source": (row.single_source),
                    "relationship_status": (row.relationship_status),
                },
                canonical_fact_ids=(row.relationship_id,),
            )

        raise GraphDataIntegrityError("Unexpected relationship row type.")

    def _expand(
        self,
        *,
        dataset_version: str,
        relation: GraphRelation,
        frontier_ids: tuple[
            str,
            ...,
        ],
    ) -> tuple[
        list[CompanyCustomerRow | CompanySupplierRow],
        tuple[
            str,
            ...,
        ],
    ]:
        statement = build_relationship_statement(
            dataset_version=(dataset_version),
            relation=relation,
            frontier_ids=(frontier_ids),
        )

        rows = list(self._session.scalars(statement))

        next_ids = tuple(
            sorted(
                {
                    _next_entity_id(
                        relation,
                        row,
                    )
                    for row in rows
                }
            )
        )

        return (
            rows,
            next_ids,
        )

    def _load_portfolio_companies(
        self,
        query: PortfolioGraphQuery,
    ) -> tuple[
        CompanyRow,
        ...,
    ]:
        rows = tuple(self._session.scalars(build_portfolio_company_statement(query)))

        observed_ids = [row.company_id for row in rows]

        if len(set(observed_ids)) != len(observed_ids):
            raise GraphDataIntegrityError(
                "Portfolio graph company scope contains duplicate companies."
            )

        if query.candidate_company_ids:
            expected = set(query.candidate_company_ids)

            observed = set(observed_ids)

            missing = sorted(expected - observed)

            if missing:
                raise GraphDataIntegrityError(
                    f"Portfolio graph candidate scope contains unknown company IDs: {missing}."
                )

        return rows

    def _portfolio_predicate_rows(
        self,
        *,
        query: PortfolioGraphQuery,
        predicate: PortfolioGraphPredicate,
        company_ids: tuple[
            str,
            ...,
        ],
    ) -> tuple[
        CompanyCustomerRow | CompanySupplierRow,
        ...,
    ]:
        rows = tuple(
            self._session.scalars(
                build_portfolio_predicate_statement(
                    dataset_version=(query.dataset_version),
                    predicate=predicate,
                    company_ids=company_ids,
                )
            )
        )

        expected_type = (
            CompanyCustomerRow
            if predicate.relationship_type == "company_customer"
            else CompanySupplierRow
        )

        for row in rows:
            if not isinstance(
                row,
                expected_type,
            ):
                raise GraphDataIntegrityError(
                    "Portfolio graph predicate returned unexpected relationship row type."
                )

        return rows

    @staticmethod
    def _portfolio_target_identity(
        row: (CompanyCustomerRow | CompanySupplierRow),
    ) -> tuple[
        GraphEntityType,
        str,
    ]:
        if isinstance(
            row,
            CompanyCustomerRow,
        ):
            return (
                "customer",
                row.customer_id,
            )

        if isinstance(
            row,
            CompanySupplierRow,
        ):
            return (
                "supplier",
                row.supplier_id,
            )

        raise GraphDataIntegrityError("Unexpected portfolio graph relationship row type.")

    def _execute_portfolio_payload(
        self,
        query: PortfolioGraphQuery,
    ) -> tuple[
        str,
        GraphPayload,
    ]:
        companies = self._load_portfolio_companies(query)

        if not companies:
            return (
                "empty",
                GraphPayload(
                    nodes=(),
                    edges=(),
                    matched_company_ids=(),
                    empty_reason="no_matches",
                ),
            )

        company_ids = tuple(company.company_id for company in companies)

        predicate_rows: list[
            tuple[
                CompanyCustomerRow | CompanySupplierRow,
                ...,
            ]
        ] = []

        matched_company_ids = set(company_ids)

        for predicate in query.predicates:
            rows = self._portfolio_predicate_rows(
                query=query,
                predicate=predicate,
                company_ids=company_ids,
            )

            predicate_rows.append(rows)

            predicate_company_ids = {row.company_id for row in rows}

            matched_company_ids.intersection_update(predicate_company_ids)

        ordered_matched_ids = tuple(sorted(matched_company_ids))

        if not ordered_matched_ids:
            return (
                "empty",
                GraphPayload(
                    nodes=(),
                    edges=(),
                    matched_company_ids=(),
                    empty_reason="no_matches",
                ),
            )

        nodes: dict[
            tuple[
                GraphEntityType,
                str,
            ],
            GraphNode,
        ] = {}

        edges: dict[
            tuple[
                str,
                str,
            ],
            GraphEdge,
        ] = {}

        for company_id in ordered_matched_ids:
            company_node = self._load_node(
                dataset_version=(query.dataset_version),
                entity_type="company",
                entity_id=company_id,
            )

            if company_node is None:
                raise GraphDataIntegrityError(
                    f"Portfolio graph scope references missing company: {company_id}."
                )

            nodes[
                (
                    company_node.entity_type,
                    company_node.entity_id,
                )
            ] = company_node

        matched_id_set = set(ordered_matched_ids)

        for rows in predicate_rows:
            for row in rows:
                if row.company_id not in matched_id_set:
                    continue

                edge = self._edge(
                    dataset_version=(query.dataset_version),
                    row=row,
                )

                edges[
                    (
                        edge.relationship_type,
                        edge.relationship_id,
                    )
                ] = edge

                (
                    target_type,
                    target_id,
                ) = self._portfolio_target_identity(row)

                target_node = self._load_node(
                    dataset_version=(query.dataset_version),
                    entity_type=target_type,
                    entity_id=target_id,
                )

                if target_node is None:
                    raise GraphDataIntegrityError(
                        "Portfolio graph "
                        "relationship references "
                        "missing endpoint: "
                        f"{target_type}:"
                        f"{target_id}."
                    )

                nodes[
                    (
                        target_node.entity_type,
                        target_node.entity_id,
                    )
                ] = target_node

        ordered_nodes = tuple(
            sorted(
                nodes.values(),
                key=_node_sort_key,
            )
        )

        ordered_edges = tuple(
            sorted(
                edges.values(),
                key=_edge_sort_key,
            )
        )

        if not ordered_edges:
            raise GraphDataIntegrityError(
                "Portfolio graph matched companies without supporting relationship evidence."
            )

        return (
            "ok",
            GraphPayload(
                nodes=ordered_nodes,
                edges=ordered_edges,
                matched_company_ids=(ordered_matched_ids),
            ),
        )

    def _execute_payload(
        self,
        query: GraphQuery,
    ) -> tuple[
        str,
        GraphPayload,
    ]:
        start = self._load_node(
            dataset_version=(query.dataset_version),
            entity_type=(query.start_entity_type),
            entity_id=(query.start_entity_id),
        )

        if start is None:
            return (
                "empty",
                GraphPayload(
                    nodes=(),
                    edges=(),
                    empty_reason=("start_entity_not_found"),
                ),
            )

        nodes: dict[
            tuple[
                GraphEntityType,
                str,
            ],
            GraphNode,
        ] = {
            (
                start.entity_type,
                start.entity_id,
            ): start
        }

        edges: dict[
            tuple[
                str,
                str,
            ],
            GraphEdge,
        ] = {}

        for path in query.paths:
            frontier_ids = (query.start_entity_id,)

            current_type = query.start_entity_type

            for relation in path.hops:
                rows, next_ids = self._expand(
                    dataset_version=(query.dataset_version),
                    relation=relation,
                    frontier_ids=(frontier_ids),
                )

                target_type = _RELATION_TARGET_TYPE[relation]

                for row in rows:
                    edge = self._edge(
                        dataset_version=(query.dataset_version),
                        row=row,
                    )

                    edges[
                        (
                            edge.relationship_type,
                            edge.relationship_id,
                        )
                    ] = edge

                loaded_next_ids: list[str] = []

                for entity_id in next_ids:
                    node = self._load_node(
                        dataset_version=(query.dataset_version),
                        entity_type=(target_type),
                        entity_id=(entity_id),
                    )

                    if node is None:
                        raise GraphDataIntegrityError(
                            f"Relationship references missing endpoint: {target_type}:{entity_id}."
                        )

                    nodes[
                        (
                            node.entity_type,
                            node.entity_id,
                        )
                    ] = node

                    loaded_next_ids.append(entity_id)

                frontier_ids = tuple(loaded_next_ids)

                current_type = target_type

                if not frontier_ids:
                    break

            del current_type

        ordered_nodes = tuple(
            sorted(
                nodes.values(),
                key=_node_sort_key,
            )
        )

        ordered_edges = tuple(
            sorted(
                edges.values(),
                key=_edge_sort_key,
            )
        )

        if not ordered_edges:
            return (
                "empty",
                GraphPayload(
                    nodes=(ordered_nodes),
                    edges=(),
                    empty_reason=("no_relationships"),
                ),
            )

        return (
            "ok",
            GraphPayload(
                nodes=ordered_nodes,
                edges=ordered_edges,
            ),
        )

    def execute(
        self,
        query: GraphQuery | PortfolioGraphQuery,
    ) -> ToolExecutionResult:
        """Execute one validated bounded graph request."""

        started_at = self._clock()

        try:
            if isinstance(
                query,
                PortfolioGraphQuery,
            ):
                (
                    status,
                    payload,
                ) = self._execute_portfolio_payload(query)
            else:
                (
                    status,
                    payload,
                ) = self._execute_payload(query)

        except GraphDataIntegrityError as exc:
            return ToolExecutionResult(
                tool="graph",
                status="error",
                duration_ms=(self._duration_ms(started_at)),
                error=(f"graph data integrity failure: {exc}"),
            )

        except SQLAlchemyError as exc:
            return ToolExecutionResult(
                tool="graph",
                status="error",
                duration_ms=(self._duration_ms(started_at)),
                error=(f"relational graph SQL execution failed: {type(exc).__name__}"),
            )

        return ToolExecutionResult(
            tool="graph",
            status=status,
            payload=payload,
            duration_ms=(self._duration_ms(started_at)),
        )
