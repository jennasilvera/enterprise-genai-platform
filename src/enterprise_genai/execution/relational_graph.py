from __future__ import annotations

from collections.abc import Callable
from time import perf_counter

from sqlalchemy import Select, select
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
        query: GraphQuery,
    ) -> ToolExecutionResult:
        """Execute one validated bounded graph request."""

        started_at = self._clock()

        try:
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
