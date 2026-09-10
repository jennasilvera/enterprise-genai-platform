from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Literal

from enterprise_genai.data.evaluation_models import (
    EvaluationCase,
)
from enterprise_genai.data.evaluation_seed import (
    build_seed_evaluation,
)

EXECUTION_COVERAGE_VERSION = "northstar-execution-coverage-v1"

TARGET_QUERY_IDS = (
    "Q-0010",
    "Q-0011",
    "Q-0012",
    "Q-0013",
    "Q-0014",
    "Q-0015",
    "Q-0016",
    "Q-0020",
    "Q-0021",
    "Q-0022",
    "Q-0024",
)

CanonicalTool = Literal[
    "retrieval",
    "sql",
    "graph",
]

PrimitiveCoverage = Literal[
    "verified",
    "unsupported_metric_by_design",
]

CompositionCoverage = Literal[
    "single_tool",
    "pending_explicit_verification",
    "verified_explicit",
    "not_applicable",
]

CapabilityStatus = Literal[
    "not_implemented",
    "not_applicable",
]


@dataclass(
    frozen=True,
)
class CoverageDeclaration:
    query_id: str

    primitive_coverage: PrimitiveCoverage

    composition_coverage: CompositionCoverage

    planner: CapabilityStatus

    answer_synthesis: CapabilityStatus

    abstention: CapabilityStatus


DECLARATIONS = (
    CoverageDeclaration(
        query_id="Q-0010",
        primitive_coverage="verified",
        composition_coverage="single_tool",
        planner="not_implemented",
        answer_synthesis="not_implemented",
        abstention="not_applicable",
    ),
    CoverageDeclaration(
        query_id="Q-0011",
        primitive_coverage="verified",
        composition_coverage="single_tool",
        planner="not_implemented",
        answer_synthesis="not_implemented",
        abstention="not_applicable",
    ),
    CoverageDeclaration(
        query_id="Q-0012",
        primitive_coverage="verified",
        composition_coverage="single_tool",
        planner="not_implemented",
        answer_synthesis="not_implemented",
        abstention="not_applicable",
    ),
    CoverageDeclaration(
        query_id="Q-0013",
        primitive_coverage="verified",
        composition_coverage="single_tool",
        planner="not_implemented",
        answer_synthesis="not_implemented",
        abstention="not_applicable",
    ),
    CoverageDeclaration(
        query_id="Q-0014",
        primitive_coverage="verified",
        composition_coverage="single_tool",
        planner="not_implemented",
        answer_synthesis="not_implemented",
        abstention="not_applicable",
    ),
    CoverageDeclaration(
        query_id="Q-0015",
        primitive_coverage="verified",
        composition_coverage="single_tool",
        planner="not_implemented",
        answer_synthesis="not_implemented",
        abstention="not_applicable",
    ),
    CoverageDeclaration(
        query_id="Q-0016",
        primitive_coverage="verified",
        composition_coverage="single_tool",
        planner="not_implemented",
        answer_synthesis="not_implemented",
        abstention="not_applicable",
    ),
    CoverageDeclaration(
        query_id="Q-0020",
        primitive_coverage="verified",
        composition_coverage=("pending_explicit_verification"),
        planner="not_implemented",
        answer_synthesis="not_implemented",
        abstention="not_applicable",
    ),
    CoverageDeclaration(
        query_id="Q-0021",
        primitive_coverage="verified",
        composition_coverage=("pending_explicit_verification"),
        planner="not_implemented",
        answer_synthesis="not_implemented",
        abstention="not_applicable",
    ),
    CoverageDeclaration(
        query_id="Q-0022",
        primitive_coverage="verified",
        composition_coverage="verified_explicit",
        planner="not_implemented",
        answer_synthesis="not_implemented",
        abstention="not_applicable",
    ),
    CoverageDeclaration(
        query_id="Q-0024",
        primitive_coverage=("unsupported_metric_by_design"),
        composition_coverage="not_applicable",
        planner="not_implemented",
        answer_synthesis="not_implemented",
        abstention="not_implemented",
    ),
)


def normalize_required_tools(
    case: EvaluationCase,
) -> tuple[CanonicalTool, ...]:
    normalized: set[CanonicalTool] = set()

    for tool in case.required_tools:
        if tool in {
            "lexical_retrieval",
            "dense_retrieval",
            "hybrid_retrieval",
            "retrieval",
        }:
            normalized.add("retrieval")
        elif tool == "sql":
            normalized.add("sql")
        elif tool == "graph":
            normalized.add("graph")
        else:
            raise RuntimeError(f"Unexpected benchmark tool: {tool!r}.")

    canonical_order: tuple[
        CanonicalTool,
        ...,
    ] = (
        "retrieval",
        "sql",
        "graph",
    )

    return tuple(tool for tool in canonical_order if tool in normalized)


EXPECTED_TOOL_SETS: dict[
    str,
    tuple[
        CanonicalTool,
        ...,
    ],
] = {
    "Q-0010": ("sql",),
    "Q-0011": ("sql",),
    "Q-0012": ("sql",),
    "Q-0013": ("sql",),
    "Q-0014": ("graph",),
    "Q-0015": ("graph",),
    "Q-0016": ("graph",),
    "Q-0020": (
        "retrieval",
        "sql",
    ),
    "Q-0021": (
        "retrieval",
        "sql",
    ),
    "Q-0022": (
        "sql",
        "graph",
    ),
    "Q-0024": ("sql",),
}


def evaluation_payload_sha256() -> str:
    evaluation = build_seed_evaluation()

    payload = json.dumps(
        evaluation.model_dump(mode="json"),
        sort_keys=True,
        separators=(
            ",",
            ":",
        ),
        ensure_ascii=False,
    ).encode()

    return hashlib.sha256(payload).hexdigest()


def validate_coverage_protocol() -> None:
    evaluation = build_seed_evaluation()

    if len(evaluation.cases) != 24:
        raise RuntimeError("Expected 24 frozen evaluation cases.")

    cases = {case.query_id: case for case in evaluation.cases}

    declaration_ids = tuple(declaration.query_id for declaration in DECLARATIONS)

    if declaration_ids != TARGET_QUERY_IDS:
        raise RuntimeError("Coverage declarations do not match frozen target order.")

    if set(EXPECTED_TOOL_SETS) != set(TARGET_QUERY_IDS):
        raise RuntimeError("Expected-tool map does not match target cases.")

    for query_id in TARGET_QUERY_IDS:
        if query_id not in cases:
            raise RuntimeError(f"Missing frozen benchmark case: {query_id}.")

        observed = normalize_required_tools(cases[query_id])

        expected = EXPECTED_TOOL_SETS[query_id]

        if observed != expected:
            raise RuntimeError(
                "Benchmark tool-set mismatch "
                f"for {query_id}: "
                f"expected={expected!r}, "
                f"observed={observed!r}."
            )

    q0024 = cases["Q-0024"]

    if q0024.answerable:
        raise RuntimeError("Q-0024 must remain unanswerable.")

    if q0024.expected_answer.answer_type != "abstain":
        raise RuntimeError("Q-0024 must remain an abstention benchmark case.")

    unsupported = [
        declaration.query_id
        for declaration in DECLARATIONS
        if declaration.primitive_coverage == "unsupported_metric_by_design"
    ]

    if unsupported != ["Q-0024"]:
        raise RuntimeError("Only Q-0024 may be protocol-declared unsupported.")


def protocol_report() -> dict[
    str,
    object,
]:
    validate_coverage_protocol()

    evaluation = build_seed_evaluation()

    cases = {case.query_id: case for case in evaluation.cases}

    declaration_map = {declaration.query_id: declaration for declaration in DECLARATIONS}

    reports: list[
        dict[
            str,
            object,
        ]
    ] = []

    for query_id in TARGET_QUERY_IDS:
        case = cases[query_id]

        declaration = declaration_map[query_id]

        reports.append(
            {
                "query_id": query_id,
                "question": (case.question),
                "query_type": (case.query_type),
                "split": (case.split),
                "answerable": (case.answerable),
                "required_tools": list(normalize_required_tools(case)),
                "coverage": asdict(declaration),
            }
        )

    return {
        "protocol_version": (EXECUTION_COVERAGE_VERSION),
        "dataset_version": (evaluation.dataset_version),
        "evaluation_version": (evaluation.evaluation_version),
        "evaluation_payload_sha256": (evaluation_payload_sha256()),
        "target_case_count": len(TARGET_QUERY_IDS),
        "cases": reports,
    }


def deterministic_execution_coverage_bytes(
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


def write_execution_coverage_report(
    report: dict[
        str,
        object,
    ],
    output: Path,
) -> None:
    if output.exists():
        raise FileExistsError("Execution coverage output already exists.")

    output.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    output.write_bytes(deterministic_execution_coverage_bytes(report))
