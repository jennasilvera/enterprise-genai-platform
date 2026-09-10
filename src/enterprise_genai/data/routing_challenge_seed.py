from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass

from enterprise_genai.data.routing_models import (
    RouteLabel,
    RoutingCase,
    RoutingSet,
    ToolFamily,
    canonical_route_label,
)

ROUTING_CHALLENGE_VERSION = "northstar-routing-challenge-v1"

CHALLENGE_SPLIT = "locked_holdout"


@dataclass(frozen=True)
class ChallengeAnchor:
    company_id: str
    company: str


@dataclass(frozen=True)
class ChallengeFamily:
    family_id: str
    required_tools: tuple[ToolFamily, ...]
    template: str
    rationale: str


ANCHORS: tuple[ChallengeAnchor, ...] = (
    ChallengeAnchor(
        company_id="PC-003",
        company="BluePeak Logistics",
    ),
    ChallengeAnchor(
        company_id="PC-004",
        company="HelioGrid Energy",
    ),
    ChallengeAnchor(
        company_id="PC-006",
        company="Orbis Cybersecurity",
    ),
    ChallengeAnchor(
        company_id="PC-007",
        company="Cedar Financial Technologies",
    ),
)


FAMILIES: tuple[ChallengeFamily, ...] = (
    ChallengeFamily(
        family_id=("challenge-retrieval-synonym-01"),
        required_tools=("retrieval",),
        template=(
            "What does the record say is driving the most material business concern at {company}?"
        ),
        rationale=(
            "Requires qualitative evidence "
            "without structured computation "
            "or relationship traversal."
        ),
    ),
    ChallengeFamily(
        family_id=("challenge-retrieval-reframe-01"),
        required_tools=("retrieval",),
        template=("What rationale is given for the principal risk affecting {company}?"),
        rationale=("Requires qualitative explanation from portfolio evidence."),
    ),
    ChallengeFamily(
        family_id=("challenge-retrieval-implicit-01"),
        required_tools=("retrieval",),
        template=("How is the underlying cause of {company}'s main operating concern described?"),
        rationale=("Requires qualitative evidence rather than structured arithmetic."),
    ),
    ChallengeFamily(
        family_id=("challenge-sql-synonym-01"),
        required_tools=("sql",),
        template=(
            "Of every dollar of sales at {company} in 2026Q2, what share remained as EBITDA?"
        ),
        rationale=("Requires deterministic structured financial arithmetic."),
    ),
    ChallengeFamily(
        family_id=("challenge-sql-comparison-01"),
        required_tools=("sql",),
        template=(
            "Was {company}'s customer count higher in 2026Q2 than in 2025Q2, and by how many?"
        ),
        rationale=("Requires deterministic structured period comparison."),
    ),
    ChallengeFamily(
        family_id=("challenge-sql-reframe-01"),
        required_tools=("sql",),
        template=("How large was the change in {company}'s revenue between 2025Q2 and 2026Q2?"),
        rationale=("Requires deterministic structured period arithmetic."),
    ),
    ChallengeFamily(
        family_id=("challenge-graph-synonym-01"),
        required_tools=("graph",),
        template=("Who does {company} sell to and purchase from?"),
        rationale=("Requires traversal across direct commercial entity relationships."),
    ),
    ChallengeFamily(
        family_id=("challenge-graph-reframe-01"),
        required_tools=("graph",),
        template=("Name the buyers and vendors directly connected to {company}."),
        rationale=("Requires customer and supplier relationship traversal."),
    ),
    ChallengeFamily(
        family_id=("challenge-graph-implicit-01"),
        required_tools=("graph",),
        template=("Which outside organizations have direct commercial ties to {company}?"),
        rationale=("Requires relationship traversal without quantitative computation."),
    ),
    ChallengeFamily(
        family_id=("challenge-retrieval-sql-synonym-01"),
        required_tools=(
            "retrieval",
            "sql",
        ),
        template=(
            "How much did {company}'s sales "
            "change from 2025Q2 to 2026Q2, "
            "and what rationale is given for "
            "its principal risk?"
        ),
        rationale=("Requires structured period comparison plus qualitative risk evidence."),
    ),
    ChallengeFamily(
        family_id=("challenge-retrieval-sql-reframe-01"),
        required_tools=(
            "retrieval",
            "sql",
        ),
        template=(
            "What share of {company}'s 2026Q2 "
            "sales became EBITDA, and what does "
            "the record say is driving its main "
            "business concern?"
        ),
        rationale=("Requires financial arithmetic plus qualitative evidence."),
    ),
    ChallengeFamily(
        family_id=("challenge-retrieval-sql-implicit-01"),
        required_tools=(
            "retrieval",
            "sql",
        ),
        template=(
            "How did {company}'s net retention "
            "move between 2025Q2 and 2026Q2, "
            "and how is the cause of its main "
            "operating concern described?"
        ),
        rationale=("Requires structured metric comparison plus qualitative risk evidence."),
    ),
    ChallengeFamily(
        family_id=("challenge-retrieval-graph-synonym-01"),
        required_tools=(
            "retrieval",
            "graph",
        ),
        template=(
            "Who does {company} buy from, and "
            "what does the record say about its "
            "principal business risk?"
        ),
        rationale=("Requires supplier relationship traversal plus qualitative evidence."),
    ),
    ChallengeFamily(
        family_id=("challenge-retrieval-graph-reframe-01"),
        required_tools=(
            "retrieval",
            "graph",
        ),
        template=(
            "Identify the buyers of {company}'s "
            "products or services, then state "
            "the rationale given for its main "
            "operating concern."
        ),
        rationale=("Requires customer relationship traversal plus qualitative evidence."),
    ),
    ChallengeFamily(
        family_id=("challenge-retrieval-graph-implicit-01"),
        required_tools=(
            "retrieval",
            "graph",
        ),
        template=(
            "Which vendors are directly tied "
            "to {company}, and how is its most "
            "material risk described?"
        ),
        rationale=("Requires supplier relationship traversal plus qualitative evidence."),
    ),
    ChallengeFamily(
        family_id=("challenge-sql-graph-synonym-01"),
        required_tools=(
            "sql",
            "graph",
        ),
        template=("Who does {company} sell to, and what share of its 2026Q2 sales was EBITDA?"),
        rationale=("Requires customer relationship traversal plus financial arithmetic."),
    ),
    ChallengeFamily(
        family_id=("challenge-sql-graph-reframe-01"),
        required_tools=(
            "sql",
            "graph",
        ),
        template=(
            "List {company}'s vendors and "
            "determine whether its 2026Q2 net "
            "retention was under 100 percent."
        ),
        rationale=("Requires supplier relationships plus structured threshold logic."),
    ),
    ChallengeFamily(
        family_id=("challenge-sql-graph-implicit-01"),
        required_tools=(
            "sql",
            "graph",
        ),
        template=(
            "Which organizations buy from "
            "{company}, and how much did its "
            "revenue change from 2025Q2 to "
            "2026Q2?"
        ),
        rationale=("Requires customer relationships plus structured period arithmetic."),
    ),
    ChallengeFamily(
        family_id=("challenge-all-tools-synonym-01"),
        required_tools=(
            "retrieval",
            "sql",
            "graph",
        ),
        template=(
            "Who does {company} purchase from, "
            "what share of 2026Q2 sales became "
            "EBITDA, and what rationale is "
            "recorded for its principal risk?"
        ),
        rationale=("Requires supplier traversal, financial arithmetic, and qualitative evidence."),
    ),
    ChallengeFamily(
        family_id=("challenge-all-tools-reframe-01"),
        required_tools=(
            "retrieval",
            "sql",
            "graph",
        ),
        template=(
            "Identify the businesses that buy "
            "from {company}, compare its 2025Q2 "
            "and 2026Q2 revenue, and summarize "
            "the cause given for its main "
            "business concern."
        ),
        rationale=("Requires customer traversal, structured comparison, and qualitative evidence."),
    ),
    ChallengeFamily(
        family_id=("challenge-all-tools-implicit-01"),
        required_tools=(
            "retrieval",
            "sql",
            "graph",
        ),
        template=(
            "Name {company}'s vendors, state "
            "its 2026Q2 net retention, and "
            "explain what the record says is "
            "driving its most material risk."
        ),
        rationale=(
            "Requires supplier traversal, structured metric retrieval, and qualitative evidence."
        ),
    ),
)


def _routing_id(
    family_id: str,
    company_id: str,
) -> str:
    digest = hashlib.sha256((f"{family_id}|{company_id}").encode()).hexdigest()[:16].upper()

    return f"RCH-{digest}"


def build_routing_challenge() -> RoutingSet:
    cases: list[RoutingCase] = []

    for family in FAMILIES:
        route_label: RouteLabel = canonical_route_label(family.required_tools)

        for anchor in ANCHORS:
            cases.append(
                RoutingCase(
                    routing_id=_routing_id(
                        family.family_id,
                        anchor.company_id,
                    ),
                    question=(family.template.format(company=(anchor.company))),
                    split=(CHALLENGE_SPLIT),
                    template_family=(family.family_id),
                    difficulty="hard",
                    required_tools=list(family.required_tools),
                    route_label=(route_label),
                    rationale=(family.rationale),
                    source_entity_ids=[anchor.company_id],
                )
            )

    return RoutingSet(
        dataset_version=("northstar-v1"),
        routing_version=(ROUTING_CHALLENGE_VERSION),
        cases=cases,
    )


def routing_challenge_sha256(
    routing: RoutingSet,
) -> str:
    payload = json.dumps(
        routing.model_dump(mode="json"),
        sort_keys=True,
        separators=(
            ",",
            ":",
        ),
        ensure_ascii=False,
    ).encode()

    return hashlib.sha256(payload).hexdigest()
