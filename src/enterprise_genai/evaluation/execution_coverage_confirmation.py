from __future__ import annotations

import hashlib
import json
from pathlib import Path

from pydantic import ValidationError
from sqlalchemy.orm import Session

from enterprise_genai.data.evaluation_seed import (
    build_seed_evaluation,
)
from enterprise_genai.evaluation.execution_coverage import (
    DECLARATIONS,
    TARGET_QUERY_IDS,
    deterministic_execution_coverage_bytes,
    protocol_report,
)
from enterprise_genai.execution.contracts import (
    GraphPayload,
    PortfolioGraphPredicate,
    PortfolioGraphQuery,
    RetrievalPayload,
    RetrievalQuery,
    StructuredPayload,
    StructuredQuery,
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

EXECUTION_COVERAGE_CONFIRMATION_VERSION = "northstar-execution-coverage-confirmation-v1"

FROZEN_PROTOCOL_COMMIT = "8953e198df58c755dcc9894544cec62c6a554f79"

FROZEN_PROTOCOL_TAG = "phase-8e3a-execution-coverage-protocol"

FROZEN_PROTOCOL_REPORT_SHA256 = "5970e7dbff67bc4fb2e1db5d86ee1116604fd1111b682b0eb31573b73ccc103f"

EXECUTION_BOUNDARY_COMMIT = "ee1387d52655b618d7288c8cf1edbb6054564422"

EXECUTION_BOUNDARY_TAG = "phase-8e2b-portfolio-graph-execution"


def protocol_report_sha256() -> str:
    payload = deterministic_execution_coverage_bytes(protocol_report())

    return hashlib.sha256(payload).hexdigest()


def assert_frozen_protocol() -> None:
    observed = protocol_report_sha256()

    if observed != FROZEN_PROTOCOL_REPORT_SHA256:
        raise RuntimeError(
            "Frozen execution-coverage "
            "protocol fingerprint mismatch: "
            f"expected "
            f"{FROZEN_PROTOCOL_REPORT_SHA256}, "
            f"observed {observed}."
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


def _require_structured(
    result: object,
) -> StructuredPayload:
    status = getattr(
        result,
        "status",
        None,
    )

    payload = getattr(
        result,
        "payload",
        None,
    )

    if status != "ok":
        raise RuntimeError(f"Structured confirmation expected ok, observed {status!r}.")

    if not isinstance(
        payload,
        StructuredPayload,
    ):
        raise RuntimeError("Structured confirmation returned wrong payload type.")

    return payload


def _require_graph(
    result: object,
) -> GraphPayload:
    status = getattr(
        result,
        "status",
        None,
    )

    payload = getattr(
        result,
        "payload",
        None,
    )

    if status != "ok":
        raise RuntimeError(f"Graph confirmation expected ok, observed {status!r}.")

    if not isinstance(
        payload,
        GraphPayload,
    ):
        raise RuntimeError("Graph confirmation returned wrong payload type.")

    return payload


def _require_retrieval(
    result: object,
) -> RetrievalPayload:
    status = getattr(
        result,
        "status",
        None,
    )

    payload = getattr(
        result,
        "payload",
        None,
    )

    if status != "ok":
        raise RuntimeError(f"Retrieval confirmation expected ok, observed {status!r}.")

    if not isinstance(
        payload,
        RetrievalPayload,
    ):
        raise RuntimeError("Retrieval confirmation returned wrong payload type.")

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
            "evidence_id": (hit.evidence_id),
            "document_id": (hit.document_id),
            "rank": hit.rank,
            "source_fact_ids": list(hit.source_fact_ids),
        }

    raise RuntimeError(
        f"Frozen retrieval failed to recover canonical evidence {expected_evidence_id!r}."
    )


def _declaration_map() -> dict[
    str,
    object,
]:
    return {declaration.query_id: declaration for declaration in DECLARATIONS}


def run_execution_coverage_confirmation(
    *,
    session: Session,
    retrieval_executor: (FrozenHybridRetrievalExecutor | None) = None,
) -> dict[str, object]:
    assert_frozen_protocol()

    evaluation = build_seed_evaluation()

    cases = {case.query_id: case for case in evaluation.cases}

    declarations = _declaration_map()

    sql = StructuredSqlExecutor(session)

    graph = RelationalGraphExecutor(session)

    retrieval = retrieval_executor or FrozenHybridRetrievalExecutor.from_persisted_corpus(
        session,
        evaluation.dataset_version,
    )

    observations: dict[
        str,
        dict[
            str,
            object,
        ],
    ] = {}

    #
    # Q-0010
    #
    q0010 = _require_structured(
        sql.execute(
            StructuredQuery(
                period="2026Q2",
                operation=("portfolio_growth_rank"),
                metric="revenue_usd",
                comparison_period=("2025Q2"),
                rank_order="highest",
                result_limit=1,
            )
        )
    )

    _single_entity(
        q0010,
        expected_company_id="PC-004",
        expected_name=("HelioGrid Energy"),
    )

    q0010_facts = set(_structured_source_facts(q0010))

    if not {
        "FIN-PC-004-2025Q2",
        "FIN-PC-004-2026Q2",
    }.issubset(q0010_facts):
        raise RuntimeError("Q-0010 missing canonical financial provenance.")

    observations["Q-0010"] = {
        "observed_primitive_coverage": "verified",
        "observed_composition_coverage": "single_tool",
        "sql": _structured_snapshot(q0010),
    }

    #
    # Q-0011
    #
    q0011 = _require_structured(
        sql.execute(
            StructuredQuery(
                period="2026Q2",
                operation=("portfolio_metric_sum"),
                metric="revenue_usd",
            )
        )
    )

    if q0011.value != 735_000_000:
        raise RuntimeError("Q-0011 total portfolio revenue mismatch.")

    observations["Q-0011"] = {
        "observed_primitive_coverage": "verified",
        "observed_composition_coverage": "single_tool",
        "sql": _structured_snapshot(q0011),
    }

    #
    # Q-0012
    #
    q0012 = _require_structured(
        sql.execute(
            StructuredQuery(
                period="2026Q2",
                operation=("portfolio_metric_filter"),
                metric=("net_retention_pct"),
                comparator="lt",
                threshold=100,
            )
        )
    )

    _single_entity(
        q0012,
        expected_company_id="PC-005",
        expected_name=("Vantage Retail Analytics"),
    )

    observations["Q-0012"] = {
        "observed_primitive_coverage": "verified",
        "observed_composition_coverage": "single_tool",
        "sql": _structured_snapshot(q0012),
    }

    #
    # Q-0013
    #
    q0013 = _require_structured(
        sql.execute(
            StructuredQuery(
                period="2026Q2",
                operation=("portfolio_ratio_rank"),
                metric="ebitda_usd",
                denominator_metric=("revenue_usd"),
                rank_order="highest",
                result_limit=1,
            )
        )
    )

    _single_entity(
        q0013,
        expected_company_id="PC-006",
        expected_name=("Orbis Cybersecurity"),
    )

    observations["Q-0013"] = {
        "observed_primitive_coverage": "verified",
        "observed_composition_coverage": "single_tool",
        "sql": _structured_snapshot(q0013),
    }

    #
    # Q-0014
    #
    q0014 = _require_graph(
        graph.execute(
            PortfolioGraphQuery(
                predicates=(
                    PortfolioGraphPredicate(
                        relationship_type=("company_supplier"),
                        target_country=("Germany"),
                        criticality=("critical"),
                    ),
                )
            )
        )
    )

    if q0014.matched_company_ids != (
        "PC-002",
        "PC-008",
    ):
        raise RuntimeError("Q-0014 company match mismatch.")

    if {edge.relationship_id for edge in q0014.edges} != {
        "CS-003",
        "CS-011",
    }:
        raise RuntimeError("Q-0014 relationship evidence mismatch.")

    observations["Q-0014"] = {
        "observed_primitive_coverage": "verified",
        "observed_composition_coverage": "single_tool",
        "graph": _graph_snapshot(q0014),
    }

    #
    # Q-0015
    #
    q0015 = _require_graph(
        graph.execute(
            PortfolioGraphQuery(
                predicates=(
                    PortfolioGraphPredicate(
                        relationship_type=("company_customer"),
                        target_country=("Germany"),
                    ),
                )
            )
        )
    )

    if q0015.matched_company_ids != ("PC-006",):
        raise RuntimeError("Q-0015 company match mismatch.")

    observations["Q-0015"] = {
        "observed_primitive_coverage": "verified",
        "observed_composition_coverage": "single_tool",
        "graph": _graph_snapshot(q0015),
    }

    #
    # Q-0016
    #
    q0016 = _require_graph(
        graph.execute(
            PortfolioGraphQuery(
                predicates=(
                    PortfolioGraphPredicate(
                        relationship_type=("company_supplier"),
                        target_country=("Germany"),
                        criticality=("critical"),
                    ),
                    PortfolioGraphPredicate(
                        relationship_type=("company_supplier"),
                        target_country=("Switzerland"),
                    ),
                )
            )
        )
    )

    if q0016.matched_company_ids != ("PC-008",):
        raise RuntimeError("Q-0016 company match mismatch.")

    if {edge.relationship_id for edge in q0016.edges} != {
        "CS-011",
        "CS-012",
    }:
        raise RuntimeError("Q-0016 independent existential evidence mismatch.")

    observations["Q-0016"] = {
        "observed_primitive_coverage": "verified",
        "observed_composition_coverage": "single_tool",
        "graph": _graph_snapshot(q0016),
    }

    #
    # Q-0020
    #
    q0020_sql = _require_structured(
        sql.execute(
            StructuredQuery(
                period="2026Q2",
                operation=("portfolio_metric_filter"),
                metric=("net_retention_pct"),
                comparator="lt",
                threshold=100,
            )
        )
    )

    _single_entity(
        q0020_sql,
        expected_company_id="PC-005",
        expected_name=("Vantage Retail Analytics"),
    )

    if "FIN-PC-005-2026Q2" not in _structured_source_facts(q0020_sql):
        raise RuntimeError("Q-0020 SQL provenance missing Vantage Q2 fact.")

    q0020_retrieval = _require_retrieval(
        retrieval.execute(
            RetrievalQuery(
                question=(cases["Q-0020"].question),
                top_k=10,
            )
        )
    )

    q0020_canonical = _canonical_retrieval_evidence(
        q0020_retrieval,
        expected_evidence_id=("EVID-CORE-PC005-QMR-SIGNAL"),
        expected_fact_id="RISK-005",
    )

    observations["Q-0020"] = {
        "observed_primitive_coverage": "verified",
        "observed_composition_coverage": "verified_explicit",
        "composition_mode": "parallel_evidence_join",
        "sql": _structured_snapshot(q0020_sql),
        "retrieval": {
            "canonical_hit": q0020_canonical,
            "top_10_evidence_ids": [hit.evidence_id for hit in q0020_retrieval.hits],
        },
    }

    #
    # Q-0021
    #
    q0021_sql = _require_structured(
        sql.execute(
            StructuredQuery(
                period="2026Q2",
                operation=("portfolio_growth_rank"),
                metric="revenue_usd",
                comparison_period=("2025Q2"),
                rank_order="highest",
                result_limit=1,
            )
        )
    )

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

    q0021_retrieval = _require_retrieval(
        retrieval.execute(
            RetrievalQuery(
                question=(cases["Q-0021"].question),
                top_k=10,
            )
        )
    )

    q0021_canonical = _canonical_retrieval_evidence(
        q0021_retrieval,
        expected_evidence_id=("EVID-CORE-PC004-RISK-PRIMARY"),
        expected_fact_id="RISK-004",
    )

    observations["Q-0021"] = {
        "observed_primitive_coverage": "verified",
        "observed_composition_coverage": "verified_explicit",
        "composition_mode": "parallel_evidence_join",
        "sql": _structured_snapshot(q0021_sql),
        "retrieval": {
            "canonical_hit": q0021_canonical,
            "top_10_evidence_ids": [hit.evidence_id for hit in q0021_retrieval.hits],
        },
    }

    #
    # Q-0022
    #
    q0022_graph = _require_graph(
        graph.execute(
            PortfolioGraphQuery(
                predicates=(
                    PortfolioGraphPredicate(
                        relationship_type=("company_supplier"),
                        target_country=("Germany"),
                        criticality=("critical"),
                    ),
                )
            )
        )
    )

    if q0022_graph.matched_company_ids != (
        "PC-002",
        "PC-008",
    ):
        raise RuntimeError("Q-0022 graph candidate set mismatch.")

    q0022_sql = _require_structured(
        sql.execute(
            StructuredQuery(
                period="2026Q2",
                operation=("portfolio_metric_rank"),
                metric="revenue_usd",
                candidate_company_ids=(q0022_graph.matched_company_ids),
                rank_order="lowest",
                result_limit=1,
            )
        )
    )

    _single_entity(
        q0022_sql,
        expected_company_id="PC-008",
        expected_name=("NovaBio Instruments"),
    )

    q0022_sql_facts = _structured_source_facts(q0022_sql)

    if q0022_sql_facts != (
        "FIN-PC-002-2026Q2",
        "FIN-PC-008-2026Q2",
    ):
        raise RuntimeError("Q-0022 candidate-scoped SQL provenance mismatch.")

    observations["Q-0022"] = {
        "observed_primitive_coverage": "verified",
        "observed_composition_coverage": "verified_explicit",
        "composition_mode": "graph_candidates_to_sql",
        "graph": _graph_snapshot(q0022_graph),
        "sql": _structured_snapshot(q0022_sql),
    }

    #
    # Q-0024
    #
    validation_rejected = False

    try:
        StructuredQuery(
            company_id="PC-002",
            period="2026Q2",
            operation="metric_value",
            metric="customer_churn_rate",
        )
    except ValidationError as exc:
        metric_errors = [
            error
            for error in exc.errors()
            if tuple(
                error.get(
                    "loc",
                    (),
                )
            )
            == ("metric",)
        ]

        if not metric_errors:
            raise RuntimeError("Q-0024 failed validation for an unexpected field.") from exc

        validation_rejected = True

    if not validation_rejected:
        raise RuntimeError("Q-0024 unexpectedly became representable by StructuredQuery.")

    observations["Q-0024"] = {
        "observed_primitive_coverage": "unsupported_metric_by_design",
        "observed_composition_coverage": "not_applicable",
        "bounded_contract_rejected_metric": True,
        "requested_metric": "customer_churn_rate",
        "abstention_implemented": False,
    }

    if tuple(observations) != TARGET_QUERY_IDS:
        raise RuntimeError("Confirmation observations do not match target case order.")

    case_reports: list[
        dict[
            str,
            object,
        ]
    ] = []

    for query_id in TARGET_QUERY_IDS:
        declaration = declarations[query_id]

        case_reports.append(
            {
                "query_id": query_id,
                "question": cases[query_id].question,
                "required_tools": list(cases[query_id].required_tools),
                "protocol": {
                    "primitive_coverage": declaration.primitive_coverage,
                    "composition_coverage": declaration.composition_coverage,
                    "planner": declaration.planner,
                    "answer_synthesis": declaration.answer_synthesis,
                    "abstention": declaration.abstention,
                },
                "observed": observations[query_id],
            }
        )

    return {
        "confirmation_version": EXECUTION_COVERAGE_CONFIRMATION_VERSION,
        "dataset_version": evaluation.dataset_version,
        "evaluation_version": evaluation.evaluation_version,
        "protocol": {
            "commit": FROZEN_PROTOCOL_COMMIT,
            "tag": FROZEN_PROTOCOL_TAG,
            "report_sha256": FROZEN_PROTOCOL_REPORT_SHA256,
            "evaluation_payload_sha256": protocol_report()["evaluation_payload_sha256"],
        },
        "execution_boundary": {
            "commit": EXECUTION_BOUNDARY_COMMIT,
            "tag": EXECUTION_BOUNDARY_TAG,
        },
        "retrieval": retrieval.metadata,
        "summary": {
            "target_cases": 11,
            "verified_primitive_cases": 10,
            "unsupported_by_design_cases": 1,
            "single_tool_cases_verified": 7,
            "explicit_compositions_verified": 3,
            "planner_implemented": False,
            "answer_synthesis_implemented": False,
            "abstention_implemented": False,
        },
        "cases": case_reports,
    }


def deterministic_confirmation_bytes(
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


def write_execution_coverage_confirmation(
    report: dict[
        str,
        object,
    ],
    output: Path,
) -> None:
    if output.exists():
        raise FileExistsError("Execution coverage confirmation output already exists.")

    output.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    output.write_bytes(deterministic_confirmation_bytes(report))
