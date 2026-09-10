from __future__ import annotations

from decimal import Decimal
from typing import (
    Annotated,
    Literal,
)

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    model_validator,
)

from enterprise_genai.data.routing_models import (
    RouteLabel,
    ToolFamily,
    canonical_route_label,
)

NonEmptyStr = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        min_length=1,
    ),
]

Quarter = Annotated[
    str,
    StringConstraints(
        pattern=r"^20\d{2}Q[1-4]$",
    ),
]

type JsonScalar = str | int | float | bool | Decimal | None

StructuredMetric = Literal[
    "revenue_usd",
    "ebitda_usd",
    "gross_margin_pct",
    "net_retention_pct",
    "customer_count",
    "employee_count",
]

StructuredOperation = Literal[
    "metric_value",
    "metric_difference",
    "metric_ratio",
    "metric_threshold",
    "portfolio_metric_sum",
    "portfolio_metric_filter",
    "portfolio_metric_rank",
    "portfolio_growth_rank",
    "portfolio_ratio_rank",
]

StructuredRankOrder = Literal[
    "highest",
    "lowest",
]


ThresholdComparator = Literal[
    "lt",
    "lte",
    "gt",
    "gte",
    "eq",
]

GraphEntityType = Literal[
    "company",
    "customer",
    "supplier",
]

GraphRelation = Literal[
    "company_customers",
    "company_suppliers",
    "customer_company",
    "supplier_company",
]

ExecutionStatus = Literal[
    "ok",
    "empty",
    "error",
]

StructuredEmptyReason = Literal[
    "row_not_found",
    "metric_is_null",
    "zero_denominator",
]

GraphEmptyReason = Literal[
    "start_entity_not_found",
    "no_relationships",
]


class FrozenContractModel(BaseModel):
    """Strict immutable base for execution contracts."""

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
    )


class RetrievalQuery(FrozenContractModel):
    """Request for the frozen retrieval stack."""

    dataset_version: NonEmptyStr = "northstar-v1"
    question: NonEmptyStr
    top_k: int = Field(
        default=10,
        ge=1,
        le=50,
    )


class StructuredQuery(FrozenContractModel):
    """Bounded structured-data request.

    This is intentionally not arbitrary SQL.
    The SQL executor translates these operations
    into parameterized SQLAlchemy queries.

    Empty candidate_company_ids means the full
    persisted portfolio for dataset_version.
    """

    dataset_version: NonEmptyStr = "northstar-v1"

    company_id: NonEmptyStr | None = None

    period: Quarter
    operation: StructuredOperation
    metric: StructuredMetric

    comparison_period: Quarter | None = None

    denominator_metric: StructuredMetric | None = None

    comparator: ThresholdComparator | None = None

    threshold: Decimal | None = None

    candidate_company_ids: tuple[
        NonEmptyStr,
        ...,
    ] = ()

    rank_order: StructuredRankOrder | None = None

    result_limit: int | None = Field(
        default=None,
        ge=1,
        le=50,
    )

    @model_validator(mode="after")
    def validate_operation_arguments(
        self,
    ) -> StructuredQuery:
        if len(set(self.candidate_company_ids)) != len(self.candidate_company_ids):
            raise ValueError("candidate_company_ids must not contain duplicates.")

        per_company_operations = {
            "metric_value",
            "metric_difference",
            "metric_ratio",
            "metric_threshold",
        }

        if self.operation in per_company_operations:
            if self.company_id is None:
                raise ValueError("Per-company structured operations require company_id.")

            if self.candidate_company_ids:
                raise ValueError(
                    "Per-company structured operations do not accept candidate_company_ids."
                )

            if self.rank_order is not None or self.result_limit is not None:
                raise ValueError(
                    "Per-company structured operations do not accept ranking arguments."
                )

            if self.operation == "metric_value":
                if any(
                    value is not None
                    for value in (
                        self.comparison_period,
                        self.denominator_metric,
                        self.comparator,
                        self.threshold,
                    )
                ):
                    raise ValueError("metric_value does not accept comparison arguments.")

            elif self.operation == "metric_difference":
                if self.comparison_period is None:
                    raise ValueError("metric_difference requires comparison_period.")

                if self.comparison_period == self.period:
                    raise ValueError("metric_difference requires distinct periods.")

                if any(
                    value is not None
                    for value in (
                        self.denominator_metric,
                        self.comparator,
                        self.threshold,
                    )
                ):
                    raise ValueError("metric_difference accepts only comparison_period.")

            elif self.operation == "metric_ratio":
                if self.denominator_metric is None:
                    raise ValueError("metric_ratio requires denominator_metric.")

                if any(
                    value is not None
                    for value in (
                        self.comparison_period,
                        self.comparator,
                        self.threshold,
                    )
                ):
                    raise ValueError("metric_ratio accepts only denominator_metric.")

                if self.denominator_metric == self.metric:
                    raise ValueError("metric_ratio numerator and denominator must differ.")

            elif self.operation == "metric_threshold":
                if self.comparator is None or self.threshold is None:
                    raise ValueError("metric_threshold requires comparator and threshold.")

                if self.comparison_period is not None or self.denominator_metric is not None:
                    raise ValueError(
                        "metric_threshold does not accept comparison_period or denominator_metric."
                    )

            return self

        if self.company_id is not None:
            raise ValueError(
                "Portfolio structured "
                "operations do not accept "
                "company_id; use "
                "candidate_company_ids to "
                "constrain the portfolio."
            )

        if self.operation == "portfolio_metric_sum":
            if any(
                value is not None
                for value in (
                    self.comparison_period,
                    self.denominator_metric,
                    self.comparator,
                    self.threshold,
                    self.rank_order,
                    self.result_limit,
                )
            ):
                raise ValueError(
                    "portfolio_metric_sum "
                    "accepts only period, "
                    "metric, and optional "
                    "candidate_company_ids."
                )

        elif self.operation == "portfolio_metric_filter":
            if self.comparator is None or self.threshold is None:
                raise ValueError("portfolio_metric_filter requires comparator and threshold.")

            if any(
                value is not None
                for value in (
                    self.comparison_period,
                    self.denominator_metric,
                    self.rank_order,
                    self.result_limit,
                )
            ):
                raise ValueError(
                    "portfolio_metric_filter "
                    "does not accept comparison, "
                    "ratio, or ranking arguments."
                )

        elif self.operation == "portfolio_metric_rank":
            if self.rank_order is None or self.result_limit is None:
                raise ValueError("portfolio_metric_rank requires rank_order and result_limit.")

            if any(
                value is not None
                for value in (
                    self.comparison_period,
                    self.denominator_metric,
                    self.comparator,
                    self.threshold,
                )
            ):
                raise ValueError(
                    "portfolio_metric_rank "
                    "does not accept comparison, "
                    "ratio, or threshold arguments."
                )

        elif self.operation == "portfolio_growth_rank":
            if (
                self.comparison_period is None
                or self.rank_order is None
                or self.result_limit is None
            ):
                raise ValueError(
                    "portfolio_growth_rank "
                    "requires comparison_period, "
                    "rank_order, and result_limit."
                )

            if self.comparison_period == self.period:
                raise ValueError("portfolio_growth_rank requires distinct periods.")

            if any(
                value is not None
                for value in (
                    self.denominator_metric,
                    self.comparator,
                    self.threshold,
                )
            ):
                raise ValueError(
                    "portfolio_growth_rank does not accept ratio or threshold arguments."
                )

        elif self.operation == "portfolio_ratio_rank":
            if (
                self.denominator_metric is None
                or self.rank_order is None
                or self.result_limit is None
            ):
                raise ValueError(
                    "portfolio_ratio_rank "
                    "requires denominator_metric, "
                    "rank_order, and result_limit."
                )

            if self.denominator_metric == self.metric:
                raise ValueError("portfolio_ratio_rank numerator and denominator must differ.")

            if any(
                value is not None
                for value in (
                    self.comparison_period,
                    self.comparator,
                    self.threshold,
                )
            ):
                raise ValueError(
                    "portfolio_ratio_rank does not accept comparison period or threshold arguments."
                )

        return self


_GRAPH_TRANSITIONS: dict[
    GraphRelation,
    tuple[
        GraphEntityType,
        GraphEntityType,
    ],
] = {
    "company_customers": (
        "company",
        "customer",
    ),
    "company_suppliers": (
        "company",
        "supplier",
    ),
    "customer_company": (
        "customer",
        "company",
    ),
    "supplier_company": (
        "supplier",
        "company",
    ),
}


class GraphPath(FrozenContractModel):
    """One bounded graph traversal path."""

    hops: tuple[
        GraphRelation,
        ...,
    ] = Field(
        min_length=1,
        max_length=2,
    )


class GraphQuery(FrozenContractModel):
    """One or more bounded relationship paths.

    Multiple paths allow branching requests such
    as "customers and suppliers of company X".
    """

    dataset_version: NonEmptyStr = "northstar-v1"
    start_entity_type: GraphEntityType
    start_entity_id: NonEmptyStr

    paths: tuple[
        GraphPath,
        ...,
    ] = Field(
        min_length=1,
        max_length=4,
    )

    @model_validator(mode="after")
    def validate_path_transitions(
        self,
    ) -> GraphQuery:
        serialized_paths: set[tuple[GraphRelation, ...]] = set()

        for path in self.paths:
            if path.hops in serialized_paths:
                raise ValueError("Graph query contains duplicate traversal paths.")

            serialized_paths.add(path.hops)

            current_type = self.start_entity_type

            for relation in path.hops:
                (
                    expected_source,
                    target_type,
                ) = _GRAPH_TRANSITIONS[relation]

                if current_type != expected_source:
                    raise ValueError(
                        "Invalid graph transition: "
                        f"{relation!r} requires "
                        f"{expected_source!r}, "
                        "but current entity type is "
                        f"{current_type!r}."
                    )

                current_type = target_type

        return self


class ToolExecutionPlan(FrozenContractModel):
    """Validated executable form of a route."""

    route_label: RouteLabel

    retrieval: RetrievalQuery | None = None
    sql: StructuredQuery | None = None
    graph: GraphQuery | None = None

    def required_tools(
        self,
    ) -> tuple[ToolFamily, ...]:
        tools: list[ToolFamily] = []

        if self.retrieval is not None:
            tools.append("retrieval")

        if self.sql is not None:
            tools.append("sql")

        if self.graph is not None:
            tools.append("graph")

        return tuple(tools)

    @model_validator(mode="after")
    def validate_route_contract(
        self,
    ) -> ToolExecutionPlan:
        tools = self.required_tools()

        if not tools:
            raise ValueError("Execution plan requires at least one tool request.")

        actual_route = canonical_route_label(tools)

        if actual_route != self.route_label:
            raise ValueError(
                "Execution request set does not "
                "match route_label: "
                f"route_label={self.route_label!r}, "
                f"requests={actual_route!r}."
            )

        versions = {
            request.dataset_version
            for request in (
                self.retrieval,
                self.sql,
                self.graph,
            )
            if request is not None
        }

        if len(versions) != 1:
            raise ValueError("All tool requests in one plan must use the same dataset version.")

        return self


class RetrievalHit(FrozenContractModel):
    rank: int = Field(
        ge=1,
    )

    chunk_id: NonEmptyStr
    evidence_id: NonEmptyStr
    document_id: NonEmptyStr

    text: NonEmptyStr

    source_fact_ids: tuple[
        NonEmptyStr,
        ...,
    ]

    rrf_score: float = Field(
        ge=0.0,
    )

    bm25_rank: int | None = Field(
        default=None,
        ge=1,
    )

    dense_rank: int | None = Field(
        default=None,
        ge=1,
    )


class RetrievalPayload(FrozenContractModel):
    hits: tuple[
        RetrievalHit,
        ...,
    ]


class DatabaseRowReference(FrozenContractModel):
    """Exact relational provenance reference."""

    table: NonEmptyStr

    primary_key: dict[
        str,
        JsonScalar,
    ]

    canonical_fact_ids: tuple[
        NonEmptyStr,
        ...,
    ] = ()


class StructuredEntity(FrozenContractModel):
    """One company selected by a structured operation."""

    company_id: NonEmptyStr
    name: NonEmptyStr

    score: JsonScalar = None


class StructuredPayload(FrozenContractModel):
    """Structured result plus exact source rows."""

    operation: StructuredOperation

    value: JsonScalar

    entities: tuple[
        StructuredEntity,
        ...,
    ] = ()

    unit: NonEmptyStr | None = None

    empty_reason: StructuredEmptyReason | None = None

    source_rows: tuple[
        DatabaseRowReference,
        ...,
    ]

    @model_validator(mode="after")
    def validate_empty_semantics(
        self,
    ) -> StructuredPayload:
        if self.empty_reason is not None:
            if self.value is not None or self.entities:
                raise ValueError(
                    "Empty structured payload must not contain a scalar value or entities."
                )

            return self

        if self.value is None and not self.entities:
            raise ValueError(
                "Non-empty structured payload "
                "requires either a scalar value "
                "or at least one entity."
            )

        if self.value is not None and self.entities:
            raise ValueError(
                "Structured payload cannot contain both a scalar value and entity results."
            )

        return self


class GraphNode(FrozenContractModel):
    entity_type: GraphEntityType
    entity_id: NonEmptyStr
    name: NonEmptyStr

    attributes: dict[
        str,
        JsonScalar,
    ] = Field(
        default_factory=dict,
    )

    canonical_fact_ids: tuple[
        NonEmptyStr,
        ...,
    ] = ()


class GraphEdge(FrozenContractModel):
    """Canonical persisted relationship orientation."""

    relationship_type: Literal[
        "company_customer",
        "company_supplier",
    ]

    relationship_id: NonEmptyStr

    source_type: GraphEntityType
    source_id: NonEmptyStr

    target_type: GraphEntityType
    target_id: NonEmptyStr

    attributes: dict[
        str,
        JsonScalar,
    ] = Field(
        default_factory=dict,
    )

    canonical_fact_ids: tuple[
        NonEmptyStr,
        ...,
    ] = ()


class GraphPayload(FrozenContractModel):
    nodes: tuple[
        GraphNode,
        ...,
    ]

    edges: tuple[
        GraphEdge,
        ...,
    ]

    empty_reason: GraphEmptyReason | None = None

    @model_validator(mode="after")
    def validate_empty_semantics(
        self,
    ) -> GraphPayload:
        if self.empty_reason is None:
            if not self.edges:
                raise ValueError("Non-empty graph payload requires at least one edge.")

            if not self.nodes:
                raise ValueError("Non-empty graph payload requires graph nodes.")

            return self

        if self.edges:
            raise ValueError("Empty graph payload must not contain edges.")

        if self.empty_reason == "start_entity_not_found" and self.nodes:
            raise ValueError("Missing start entity must produce no graph nodes.")

        if self.empty_reason == "no_relationships" and not self.nodes:
            raise ValueError("no_relationships requires the existing start node.")

        return self


type ToolPayload = RetrievalPayload | StructuredPayload | GraphPayload


class ToolExecutionResult(FrozenContractModel):
    """One executor's typed result envelope."""

    tool: ToolFamily
    status: ExecutionStatus

    payload: ToolPayload | None = None

    duration_ms: float = Field(
        ge=0.0,
    )

    error: NonEmptyStr | None = None

    @model_validator(mode="after")
    def validate_result_contract(
        self,
    ) -> ToolExecutionResult:
        expected_payload_type: dict[
            ToolFamily,
            type[RetrievalPayload | StructuredPayload | GraphPayload],
        ] = {
            "retrieval": RetrievalPayload,
            "sql": StructuredPayload,
            "graph": GraphPayload,
        }

        if self.status == "error":
            if self.error is None:
                raise ValueError("Error result requires an error message.")

            if self.payload is not None:
                raise ValueError("Error result must not contain a payload.")

            return self

        if self.error is not None:
            raise ValueError("Non-error result must not contain an error message.")

        if self.payload is None:
            raise ValueError("Successful or empty result requires a typed payload.")

        expected = expected_payload_type[self.tool]

        if not isinstance(
            self.payload,
            expected,
        ):
            raise ValueError(f"Tool result payload type does not match {self.tool!r}.")

        return self


class ToolExecutionBatch(FrozenContractModel):
    """Complete execution outcome for one plan."""

    plan: ToolExecutionPlan

    results: tuple[
        ToolExecutionResult,
        ...,
    ]

    @model_validator(mode="after")
    def validate_complete_result_set(
        self,
    ) -> ToolExecutionBatch:
        expected = self.plan.required_tools()

        observed = tuple(result.tool for result in self.results)

        if observed != expected:
            raise ValueError(
                "Execution results must contain "
                "exactly one result for every "
                "planned tool in canonical order: "
                f"expected={expected!r}, "
                f"observed={observed!r}."
            )

        return self
