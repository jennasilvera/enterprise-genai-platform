from __future__ import annotations

import hashlib
import json
from importlib.metadata import version
from pathlib import Path

from sqlalchemy.orm import Session

from enterprise_genai.data.evaluation_seed import (
    build_seed_evaluation,
)
from enterprise_genai.evaluation.execution_coverage_confirmation import (
    FROZEN_PROTOCOL_REPORT_SHA256,
    assert_frozen_protocol,
)
from enterprise_genai.execution.contracts import (
    GraphPayload,
    PortfolioGraphPredicate,
    PortfolioGraphQuery,
    RetrievalPayload,
    RetrievalQuery,
    StructuredPayload,
    StructuredQuery,
    ToolExecutionPlan,
    ToolExecutionResult,
)
from enterprise_genai.execution.frozen_retrieval import (
    FrozenHybridRetrievalExecutor,
)
from enterprise_genai.execution.relational_graph import (
    RelationalGraphExecutor,
)
from enterprise_genai.execution.structured_sql import (
    StructuredSqlExecutor,
)
from enterprise_genai.orchestration.contracts import (
    BoundedOrchestrationPlan,
    ExecutionDependency,
    OrchestrationStateSnapshot,
)
from enterprise_genai.orchestration.langgraph_runtime import (
    BoundedLangGraphRuntime,
)

ORCHESTRATION_CONFIRMATION_VERSION = "northstar-langgraph-mixed-tool-confirmation-v1"

TARGET_QUERY_IDS = (
    "Q-0020",
    "Q-0021",
    "Q-0022",
)

FROZEN_RUNTIME_COMMIT = "476ff6ceeb37c5174183f353e8a08bfadbe0dc56"

FROZEN_RUNTIME_TAG = "phase-9b1-bounded-langgraph-runtime"

FROZEN_LANGGRAPH_VERSION = "1.2.11"

SOURCE_EXECUTION_CONFIRMATION_SHA256 = (
    "0089e0a0dabd5a4a24cb9fd9b7c39aa9c3be555add4a14377a2ac61710d3056e"
)


def _structured_source_facts(
    payload: StructuredPayload,
) -> tuple[str, ...]:
    return tuple(
        sorted({fact_id for row in payload.source_rows for fact_id in row.canonical_fact_ids})
    )


def _graph_fact_ids(
    payload: GraphPayload,
) -> tuple[str, ...]:
    facts = {fact_id for node in payload.nodes for fact_id in node.canonical_fact_ids}

    facts.update(fact_id for edge in payload.edges for fact_id in edge.canonical_fact_ids)

    return tuple(sorted(facts))


def _structured_snapshot(
    payload: StructuredPayload,
) -> dict[str, object]:
    serialized = payload.model_dump(mode="json")

    return {
        "value": serialized["value"],
        "unit": serialized["unit"],
        "entities": serialized["entities"],
        "source_fact_ids": list(_structured_source_facts(payload)),
    }


def _graph_snapshot(
    payload: GraphPayload,
) -> dict[str, object]:
    return {
        "matched_company_ids": list(payload.matched_company_ids),
        "company_node_ids": sorted(
            node.entity_id for node in payload.nodes if node.entity_type == "company"
        ),
        "customer_node_ids": sorted(
            node.entity_id for node in payload.nodes if node.entity_type == "customer"
        ),
        "supplier_node_ids": sorted(
            node.entity_id for node in payload.nodes if node.entity_type == "supplier"
        ),
        "relationship_ids": sorted(edge.relationship_id for edge in payload.edges),
        "source_fact_ids": list(_graph_fact_ids(payload)),
    }


def _canonical_retrieval_evidence(
    payload: RetrievalPayload,
    *,
    expected_evidence_id: str,
    expected_fact_id: str,
) -> dict[str, object]:
    for hit in payload.hits:
        if hit.evidence_id != expected_evidence_id:
            continue

        if expected_fact_id not in hit.source_fact_ids:
            raise RuntimeError(
                f"Canonical retrieval hit is missing expected fact {expected_fact_id!r}."
            )

        return {
            "evidence_id": hit.evidence_id,
            "document_id": hit.document_id,
            "rank": hit.rank,
            "source_fact_ids": list(hit.source_fact_ids),
        }

    raise RuntimeError(
        f"Frozen retrieval failed to recover canonical evidence {expected_evidence_id!r}."
    )


def _result_for(
    snapshot: OrchestrationStateSnapshot,
    tool: str,
) -> ToolExecutionResult:
    matches = tuple(result for result in snapshot.results if result.tool == tool)

    if len(matches) != 1:
        raise RuntimeError(f"Expected exactly one {tool!r} result.")

    result = matches[0]

    if result.status != "ok":
        raise RuntimeError(f"{tool} confirmation expected ok, observed {result.status!r}.")

    return result


def _retrieval_payload(
    snapshot: OrchestrationStateSnapshot,
) -> RetrievalPayload:
    payload = _result_for(
        snapshot,
        "retrieval",
    ).payload

    if not isinstance(
        payload,
        RetrievalPayload,
    ):
        raise RuntimeError("Retrieval confirmation returned wrong payload type.")

    return payload


def _structured_payload(
    snapshot: OrchestrationStateSnapshot,
) -> StructuredPayload:
    payload = _result_for(
        snapshot,
        "sql",
    ).payload

    if not isinstance(
        payload,
        StructuredPayload,
    ):
        raise RuntimeError("Structured confirmation returned wrong payload type.")

    return payload


def _graph_payload(
    snapshot: OrchestrationStateSnapshot,
) -> GraphPayload:
    payload = _result_for(
        snapshot,
        "graph",
    ).payload

    if not isinstance(
        payload,
        GraphPayload,
    ):
        raise RuntimeError("Graph confirmation returned wrong payload type.")

    return payload


def _single_entity(
    payload: StructuredPayload,
    *,
    expected_company_id: str,
    expected_name: str,
) -> None:
    if len(payload.entities) != 1:
        raise RuntimeError("Expected exactly one structured entity.")

    entity = payload.entities[0]

    if entity.company_id != expected_company_id or entity.name != expected_name:
        raise RuntimeError(f"Unexpected structured entity: {entity.company_id!r}, {entity.name!r}.")


def _assert_completed(
    snapshot: OrchestrationStateSnapshot,
    *,
    expected_order: tuple[str, ...],
) -> None:
    if snapshot.status != "completed":
        raise RuntimeError(
            f"Orchestration confirmation expected completed, observed {snapshot.status!r}."
        )

    observed_order = tuple(result.tool for result in snapshot.results)

    if observed_order != expected_order:
        raise RuntimeError(
            "Unexpected orchestration "
            "execution order: "
            f"expected={expected_order!r}, "
            f"observed={observed_order!r}."
        )


def run_orchestration_confirmation(
    *,
    session: Session,
    retrieval_executor: (FrozenHybridRetrievalExecutor | None) = None,
) -> dict[str, object]:
    assert_frozen_protocol()

    observed_langgraph = version("langgraph")

    if observed_langgraph != FROZEN_LANGGRAPH_VERSION:
        raise RuntimeError(
            "LangGraph version mismatch: "
            f"expected "
            f"{FROZEN_LANGGRAPH_VERSION!r}, "
            f"observed "
            f"{observed_langgraph!r}."
        )

    evaluation = build_seed_evaluation()

    cases = {case.query_id: case for case in evaluation.cases}

    sql = StructuredSqlExecutor(session)

    graph = RelationalGraphExecutor(session)

    retrieval = retrieval_executor or FrozenHybridRetrievalExecutor.from_persisted_corpus(
        session,
        evaluation.dataset_version,
    )

    runtime = BoundedLangGraphRuntime(
        retrieval_executor=retrieval,
        sql_executor=sql,
        graph_executor=graph,
    )

    observations: list[
        dict[
            str,
            object,
        ]
    ] = []

    #
    # Q-0020
    #
    q0020_case = cases["Q-0020"]

    q0020_plan = BoundedOrchestrationPlan(
        question=(q0020_case.question),
        execution_plan=(
            ToolExecutionPlan(
                route_label=("retrieval+sql"),
                retrieval=(
                    RetrievalQuery(
                        question=(q0020_case.question),
                        top_k=10,
                    )
                ),
                sql=(
                    StructuredQuery(
                        period="2026Q2",
                        operation=("portfolio_metric_filter"),
                        metric=("net_retention_pct"),
                        comparator="lt",
                        threshold=100,
                    )
                ),
            )
        ),
    )

    q0020 = runtime.execute(q0020_plan)

    _assert_completed(
        q0020,
        expected_order=(
            "retrieval",
            "sql",
        ),
    )

    if q0020.handoffs:
        raise RuntimeError("Q-0020 independent orchestration produced a dependency handoff.")

    q0020_retrieval = _retrieval_payload(q0020)

    q0020_sql = _structured_payload(q0020)

    _single_entity(
        q0020_sql,
        expected_company_id="PC-005",
        expected_name=("Vantage Retail Analytics"),
    )

    if "FIN-PC-005-2026Q2" not in _structured_source_facts(q0020_sql):
        raise RuntimeError("Q-0020 SQL provenance missing Vantage Q2 fact.")

    q0020_canonical = _canonical_retrieval_evidence(
        q0020_retrieval,
        expected_evidence_id=("EVID-CORE-PC005-QMR-SIGNAL"),
        expected_fact_id="RISK-005",
    )

    if q0020_canonical["rank"] != 1:
        raise RuntimeError("Q-0020 canonical retrieval evidence is no longer rank 1.")

    observations.append(
        {
            "query_id": "Q-0020",
            "question": q0020_case.question,
            "mode": "independent",
            "composition_mode": ("independent_sequential_evidence_join"),
            "terminal_status": q0020.status,
            "execution_order": [
                "retrieval",
                "sql",
            ],
            "handoff_count": 0,
            "retrieval": {
                "canonical_hit": q0020_canonical,
                "top_10_evidence_ids": [hit.evidence_id for hit in q0020_retrieval.hits],
            },
            "sql": _structured_snapshot(q0020_sql),
        }
    )

    #
    # Q-0021
    #
    q0021_case = cases["Q-0021"]

    q0021_plan = BoundedOrchestrationPlan(
        question=(q0021_case.question),
        execution_plan=(
            ToolExecutionPlan(
                route_label=("retrieval+sql"),
                retrieval=(
                    RetrievalQuery(
                        question=(q0021_case.question),
                        top_k=10,
                    )
                ),
                sql=(
                    StructuredQuery(
                        period="2026Q2",
                        operation=("portfolio_growth_rank"),
                        metric=("revenue_usd"),
                        comparison_period=("2025Q2"),
                        rank_order=("highest"),
                        result_limit=1,
                    )
                ),
            )
        ),
    )

    q0021 = runtime.execute(q0021_plan)

    _assert_completed(
        q0021,
        expected_order=(
            "retrieval",
            "sql",
        ),
    )

    if q0021.handoffs:
        raise RuntimeError("Q-0021 independent orchestration produced a dependency handoff.")

    q0021_retrieval = _retrieval_payload(q0021)

    q0021_sql = _structured_payload(q0021)

    _single_entity(
        q0021_sql,
        expected_company_id="PC-004",
        expected_name=("HelioGrid Energy"),
    )

    q0021_facts = set(_structured_source_facts(q0021_sql))

    if not {
        "FIN-PC-004-2025Q2",
        "FIN-PC-004-2026Q2",
    }.issubset(q0021_facts):
        raise RuntimeError("Q-0021 SQL provenance missing HelioGrid growth facts.")

    q0021_canonical = _canonical_retrieval_evidence(
        q0021_retrieval,
        expected_evidence_id=("EVID-CORE-PC004-RISK-PRIMARY"),
        expected_fact_id="RISK-004",
    )

    if q0021_canonical["rank"] != 1:
        raise RuntimeError("Q-0021 canonical retrieval evidence is no longer rank 1.")

    observations.append(
        {
            "query_id": "Q-0021",
            "question": q0021_case.question,
            "mode": "independent",
            "composition_mode": ("independent_sequential_evidence_join"),
            "terminal_status": q0021.status,
            "execution_order": [
                "retrieval",
                "sql",
            ],
            "handoff_count": 0,
            "retrieval": {
                "canonical_hit": q0021_canonical,
                "top_10_evidence_ids": [hit.evidence_id for hit in q0021_retrieval.hits],
            },
            "sql": _structured_snapshot(q0021_sql),
        }
    )

    #
    # Q-0022
    #
    q0022_case = cases["Q-0022"]

    q0022_plan = BoundedOrchestrationPlan(
        question=(q0022_case.question),
        execution_plan=(
            ToolExecutionPlan(
                route_label=("sql+graph"),
                graph=(
                    PortfolioGraphQuery(
                        predicates=(
                            PortfolioGraphPredicate(
                                relationship_type=("company_supplier"),
                                target_country=("Germany"),
                                criticality=("critical"),
                            ),
                        )
                    )
                ),
                sql=(
                    StructuredQuery(
                        period="2026Q2",
                        operation=("portfolio_metric_rank"),
                        metric=("revenue_usd"),
                        rank_order=("lowest"),
                        result_limit=1,
                    )
                ),
            )
        ),
        dependencies=(ExecutionDependency(),),
    )

    if q0022_plan.execution_plan.sql.candidate_company_ids != ():
        raise RuntimeError("Q-0022 dependent SQL must begin with unresolved candidate scope.")

    q0022 = runtime.execute(q0022_plan)

    _assert_completed(
        q0022,
        expected_order=(
            "graph",
            "sql",
        ),
    )

    if len(q0022.handoffs) != 1:
        raise RuntimeError("Q-0022 expected exactly one dependency handoff.")

    q0022_graph = _graph_payload(q0022)

    q0022_sql = _structured_payload(q0022)

    expected_candidates = (
        "PC-002",
        "PC-008",
    )

    if q0022_graph.matched_company_ids != expected_candidates:
        raise RuntimeError("Q-0022 graph candidate set mismatch.")

    handoff = q0022.handoffs[0]

    if handoff.company_ids != expected_candidates:
        raise RuntimeError("Q-0022 handoff candidate set mismatch.")

    if handoff.downstream_query.candidate_company_ids != expected_candidates:
        raise RuntimeError("Q-0022 downstream SQL scope mismatch.")

    if q0022_plan.execution_plan.sql.candidate_company_ids != ():
        raise RuntimeError("Q-0022 original SQL plan was mutated.")

    _single_entity(
        q0022_sql,
        expected_company_id="PC-008",
        expected_name=("NovaBio Instruments"),
    )

    if _structured_source_facts(q0022_sql) != (
        "FIN-PC-002-2026Q2",
        "FIN-PC-008-2026Q2",
    ):
        raise RuntimeError("Q-0022 candidate-scoped SQL provenance mismatch.")

    if {edge.relationship_id for edge in q0022_graph.edges} != {
        "CS-003",
        "CS-011",
    }:
        raise RuntimeError("Q-0022 relationship evidence mismatch.")

    observations.append(
        {
            "query_id": "Q-0022",
            "question": q0022_case.question,
            "mode": "dependent",
            "composition_mode": "graph_candidates_to_sql",
            "dependency_kind": ("graph_company_ids_to_sql_candidates"),
            "terminal_status": q0022.status,
            "execution_order": [
                "graph",
                "sql",
            ],
            "graph": _graph_snapshot(q0022_graph),
            "handoff": {
                "company_ids": list(handoff.company_ids),
                "downstream_candidate_company_ids": list(
                    handoff.downstream_query.candidate_company_ids
                ),
            },
            "original_sql_candidate_company_ids": list(
                q0022_plan.execution_plan.sql.candidate_company_ids
            ),
            "sql": _structured_snapshot(q0022_sql),
        }
    )

    observed_ids = tuple(observation["query_id"] for observation in observations)

    if observed_ids != TARGET_QUERY_IDS:
        raise RuntimeError("Orchestration confirmation case order mismatch.")

    return {
        "confirmation_version": ORCHESTRATION_CONFIRMATION_VERSION,
        "dataset_version": evaluation.dataset_version,
        "evaluation_version": evaluation.evaluation_version,
        "source_protocol": {
            "report_sha256": FROZEN_PROTOCOL_REPORT_SHA256,
            "execution_confirmation_sha256": SOURCE_EXECUTION_CONFIRMATION_SHA256,
        },
        "runtime": {
            "class": "BoundedLangGraphRuntime",
            "commit": FROZEN_RUNTIME_COMMIT,
            "tag": FROZEN_RUNTIME_TAG,
            "langgraph_version": observed_langgraph,
            "independent_execution": "sequential",
        },
        "retrieval": retrieval.metadata,
        "summary": {
            "target_cases": 3,
            "completed_cases": 3,
            "independent_cases_verified": 2,
            "dependent_cases_verified": 1,
            "planner_implemented": False,
            "answer_synthesis_implemented": False,
            "abstention_implemented": False,
            "parallel_execution_claimed": False,
        },
        "cases": observations,
    }


def deterministic_orchestration_confirmation_bytes(
    report: dict[
        str,
        object,
    ],
) -> bytes:
    payload = json.dumps(
        report,
        indent=2,
        sort_keys=True,
        ensure_ascii=False,
    )

    return (payload + "\n").encode()


def orchestration_confirmation_sha256(
    report: dict[
        str,
        object,
    ],
) -> str:
    return hashlib.sha256(deterministic_orchestration_confirmation_bytes(report)).hexdigest()


def write_orchestration_confirmation(
    report: dict[
        str,
        object,
    ],
    output: Path,
) -> None:
    if output.exists():
        raise FileExistsError("Orchestration confirmation output already exists.")

    output.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    output.write_bytes(deterministic_orchestration_confirmation_bytes(report))
