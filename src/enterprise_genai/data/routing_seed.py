from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass

from enterprise_genai.data.routing_models import (
    RouteLabel,
    RoutingCase,
    RoutingDifficulty,
    RoutingSet,
    RoutingSplit,
    ToolFamily,
    canonical_route_label,
)
from enterprise_genai.data.universe import (
    build_universe,
)

ROUTING_VERSION = "northstar-routing-v1"

ANCHOR_COMPANY_IDS = (
    "PC-001",
    "PC-002",
    "PC-005",
    "PC-008",
)


@dataclass(frozen=True)
class FamilySpec:
    family_id: str
    split: RoutingSplit
    required_tools: tuple[
        ToolFamily,
        ...,
    ]
    difficulty: RoutingDifficulty
    template: str


def _route_specs(
    prefix: str,
    tools: tuple[
        ToolFamily,
        ...,
    ],
    *,
    difficulty: RoutingDifficulty,
    train: tuple[
        str,
        str,
        str,
        str,
    ],
    development: str,
    locked_holdout: str,
) -> list[FamilySpec]:
    specs = [
        FamilySpec(
            family_id=(f"{prefix}-train-{index:02d}"),
            split="train",
            required_tools=tools,
            difficulty=difficulty,
            template=template,
        )
        for index, template in enumerate(
            train,
            start=1,
        )
    ]

    specs.append(
        FamilySpec(
            family_id=(f"{prefix}-development-01"),
            split="development",
            required_tools=tools,
            difficulty=difficulty,
            template=development,
        )
    )

    specs.append(
        FamilySpec(
            family_id=(f"{prefix}-locked-01"),
            split="locked_holdout",
            required_tools=tools,
            difficulty=difficulty,
            template=locked_holdout,
        )
    )

    return specs


def _family_specs() -> list[FamilySpec]:
    specs: list[FamilySpec] = []

    specs.extend(
        _route_specs(
            "retrieval",
            ("retrieval",),
            difficulty="easy",
            train=(
                ("What explanation did management give for {risk_title} at {company}?"),
                ("Why has management highlighted {risk_title} as a concern at {company}?"),
                ("What circumstances are described behind {risk_title} at {company}?"),
                ("How does management characterize the impact of {risk_title} on {company}?"),
            ),
            development=(
                "What is management's explanation for why {risk_title} matters at {company}?"
            ),
            locked_holdout=("Why is management concerned about {risk_title} at {company}?"),
        )
    )

    specs.extend(
        _route_specs(
            "sql",
            ("sql",),
            difficulty="easy",
            train=(
                ("What was {company}'s revenue in {period}?"),
                ("What percentage of {company}'s {period} revenue was EBITDA?"),
                ("How many customers did {company} have in {period}?"),
                ("Did {company}'s net retention fall below {nrr_threshold} percent in {period}?"),
            ),
            development=(
                "By what percentage did "
                "{company}'s revenue change from "
                "{comparison_period} to {period}?"
            ),
            locked_holdout=("What was {company}'s EBITDA margin in {period}?"),
        )
    )

    specs.extend(
        _route_specs(
            "graph",
            ("graph",),
            difficulty="medium",
            train=(
                (
                    "Which portfolio company "
                    "serves {customer}, and which "
                    "suppliers does that company "
                    "rely on?"
                ),
                (
                    "Which portfolio company buys "
                    "from {supplier}, and which "
                    "customers does it serve?"
                ),
                ("Which customers and suppliers share {company} as their portfolio-company link?"),
                (
                    "Starting with {customer}, "
                    "which suppliers can be reached "
                    "through the same portfolio "
                    "company?"
                ),
            ),
            development=("Who supplies the portfolio company that serves {customer}?"),
            locked_holdout=(
                "Which customers are served by "
                "the same portfolio company that "
                "buys from {supplier}?"
            ),
        )
    )

    specs.extend(
        _route_specs(
            "retrieval-sql",
            (
                "retrieval",
                "sql",
            ),
            difficulty="medium",
            train=(
                (
                    "How much revenue did "
                    "{company} generate in "
                    "{period}, and why has "
                    "management highlighted "
                    "{risk_title}?"
                ),
                (
                    "What percentage of "
                    "{company}'s {period} revenue "
                    "was EBITDA, and what "
                    "explanation did management "
                    "give for {risk_title}?"
                ),
                (
                    "How much did {company}'s "
                    "revenue change from "
                    "{comparison_period} to "
                    "{period}, and why is "
                    "management concerned about "
                    "{risk_title}?"
                ),
                (
                    "What was {company}'s net "
                    "retention in {period}, and "
                    "how does management describe "
                    "the impact of {risk_title}?"
                ),
            ),
            development=(
                "How many customers did {company} "
                "have in {period}, and what "
                "explanation did management give "
                "for {risk_title}?"
            ),
            locked_holdout=(
                "How did {company}'s revenue "
                "change from {comparison_period} "
                "to {period}, and why does "
                "management say {risk_title} "
                "matters?"
            ),
        )
    )

    specs.extend(
        _route_specs(
            "retrieval-graph",
            (
                "retrieval",
                "graph",
            ),
            difficulty="hard",
            train=(
                (
                    "Which portfolio company buys "
                    "from {supplier}, and why has "
                    "management highlighted "
                    "{risk_title} there?"
                ),
                (
                    "Which portfolio company "
                    "serves {customer}, and what "
                    "explanation did management "
                    "give for {risk_title} at that "
                    "company?"
                ),
                (
                    "Which customers does "
                    "{company} serve, and why is "
                    "management concerned about "
                    "{risk_title}?"
                ),
                (
                    "Which suppliers does "
                    "{company} rely on, and how "
                    "does management characterize "
                    "{risk_title}?"
                ),
            ),
            development=(
                "Who supplies {company}, and what "
                "explanation has management given "
                "for {risk_title}?"
            ),
            locked_holdout=(
                "Which portfolio company buys "
                "from {supplier}, and why is "
                "management worried about "
                "{risk_title} there?"
            ),
        )
    )

    specs.extend(
        _route_specs(
            "sql-graph",
            (
                "sql",
                "graph",
            ),
            difficulty="hard",
            train=(
                (
                    "If {company}'s ownership "
                    "stake is above "
                    "{ownership_threshold} percent, "
                    "which suppliers serve it?"
                ),
                (
                    "Did {company}'s revenue "
                    "exceed {revenue_threshold} "
                    "million USD in {period}; if "
                    "so, which suppliers serve it?"
                ),
                (
                    "Which customers of {company} "
                    "account for more than "
                    "{share_threshold} percent of "
                    "revenue?"
                ),
                (
                    "Which portfolio company buys "
                    "from {supplier}, and what was "
                    "that company's revenue in "
                    "{period}?"
                ),
            ),
            development=(
                "Which portfolio company serves "
                "{customer}, what was its EBITDA "
                "in {period}, and who supplies it?"
            ),
            locked_holdout=(
                "Which portfolio company buys "
                "from {supplier}, and was its "
                "{period} net retention below "
                "{nrr_threshold} percent?"
            ),
        )
    )

    specs.extend(
        _route_specs(
            "retrieval-sql-graph",
            (
                "retrieval",
                "sql",
                "graph",
            ),
            difficulty="hard",
            train=(
                (
                    "Which portfolio company buys "
                    "from {supplier}, what was its "
                    "revenue in {period}, and why "
                    "has management highlighted "
                    "{risk_title} there?"
                ),
                (
                    "Which portfolio company "
                    "serves {customer}, what "
                    "percentage of its {period} "
                    "revenue was EBITDA, and what "
                    "explanation did management "
                    "give for {risk_title}?"
                ),
                (
                    "Which suppliers serve "
                    "{company}, what was its net "
                    "retention in {period}, and "
                    "why is management concerned "
                    "about {risk_title}?"
                ),
                (
                    "Which customers and suppliers "
                    "share {company}, how much "
                    "revenue did it generate in "
                    "{period}, and why has "
                    "management highlighted "
                    "{risk_title}?"
                ),
            ),
            development=(
                "Who are {company}'s customers "
                "and suppliers, how did its "
                "revenue change from "
                "{comparison_period} to {period}, "
                "and what explanation did "
                "management give for {risk_title}?"
            ),
            locked_holdout=(
                "Which portfolio company buys "
                "from {supplier}, what was its "
                "EBITDA margin in {period}, and "
                "why is management worried about "
                "{risk_title} there?"
            ),
        )
    )

    return specs


ROUTE_RATIONALES: dict[
    RouteLabel,
    str,
] = {
    "retrieval": ("Requires qualitative evidence from unstructured portfolio documents."),
    "sql": (
        "Requires deterministic filtering, "
        "comparison, aggregation, or arithmetic "
        "over structured fields."
    ),
    "graph": ("Requires relationship traversal across connected enterprise entities."),
    "retrieval+sql": (
        "Requires both structured quantitative computation and unstructured narrative evidence."
    ),
    "retrieval+graph": ("Requires relationship traversal plus unstructured narrative evidence."),
    "sql+graph": ("Requires structured computation plus relationship traversal."),
    "retrieval+sql+graph": (
        "Requires narrative evidence, structured computation, and relationship traversal."
    ),
}


def _contexts() -> list[dict[str, object]]:
    universe = build_universe()

    companies = {company.company_id: company for company in universe.companies}

    customers = {customer.customer_id: customer for customer in universe.customers}

    suppliers = {supplier.supplier_id: supplier for supplier in universe.suppliers}

    thresholds = {
        "PC-001": (
            60,
            100,
            50,
            15,
        ),
        "PC-002": (
            70,
            105,
            70,
            20,
        ),
        "PC-005": (
            65,
            98,
            60,
            25,
        ),
        "PC-008": (
            66,
            110,
            80,
            10,
        ),
    }

    contexts = []

    for company_id in ANCHOR_COMPANY_IDS:
        company = companies[company_id]

        company_customers = sorted(
            (
                relationship
                for relationship in universe.company_customers
                if relationship.company_id == company_id
            ),
            key=lambda relationship: relationship.relationship_id,
        )

        company_suppliers = sorted(
            (
                relationship
                for relationship in universe.company_suppliers
                if relationship.company_id == company_id
            ),
            key=lambda relationship: relationship.relationship_id,
        )

        company_risks = sorted(
            (risk for risk in universe.risks if risk.company_id == company_id),
            key=lambda risk: risk.risk_id,
        )

        if not (company_customers and company_suppliers and company_risks):
            raise ValueError(
                "Routing benchmark anchors "
                "require customer, supplier, "
                f"and risk data: {company_id}."
            )

        customer_relationship = company_customers[0]

        supplier_relationship = company_suppliers[0]

        risk = company_risks[0]

        customer = customers[customer_relationship.customer_id]

        supplier = suppliers[supplier_relationship.supplier_id]

        (
            ownership_threshold,
            nrr_threshold,
            revenue_threshold,
            share_threshold,
        ) = thresholds[company_id]

        contexts.append(
            {
                "company": company.name,
                "company_id": (company.company_id),
                "customer": customer.name,
                "customer_id": (customer.customer_id),
                "supplier": supplier.name,
                "supplier_id": (supplier.supplier_id),
                "risk_title": risk.title,
                "risk_id": risk.risk_id,
                "period": "2026Q2",
                "comparison_period": ("2025Q2"),
                "ownership_threshold": (ownership_threshold),
                "nrr_threshold": (nrr_threshold),
                "revenue_threshold": (revenue_threshold),
                "share_threshold": (share_threshold),
            }
        )

    return contexts


def _routing_id(
    family_id: str,
    company_id: str,
) -> str:
    digest = hashlib.sha256((f"{family_id}|{company_id}").encode()).hexdigest()[:16].upper()

    return f"RTE-{digest}"


def build_routing_seed() -> RoutingSet:
    cases: list[RoutingCase] = []

    contexts = _contexts()

    for family in _family_specs():
        required_tools = list(family.required_tools)

        route_label = canonical_route_label(required_tools)

        for context in contexts:
            question = family.template.format(**context)

            source_entity_ids = [
                str(context["company_id"]),
                str(context["customer_id"]),
                str(context["supplier_id"]),
                str(context["risk_id"]),
            ]

            cases.append(
                RoutingCase(
                    routing_id=_routing_id(
                        family.family_id,
                        str(context["company_id"]),
                    ),
                    question=question,
                    split=family.split,
                    template_family=(family.family_id),
                    difficulty=(family.difficulty),
                    required_tools=(required_tools),
                    route_label=(route_label),
                    rationale=(ROUTE_RATIONALES[route_label]),
                    source_entity_ids=(source_entity_ids),
                )
            )

    return RoutingSet(
        dataset_version="northstar-v1",
        routing_version=(ROUTING_VERSION),
        cases=cases,
    )


def routing_seed_sha256(
    routing: RoutingSet,
) -> str:
    payload = json.dumps(
        routing.model_dump(mode="json"),
        sort_keys=True,
        separators=(
            ",",
            ":",
        ),
    ).encode("utf-8")

    return hashlib.sha256(payload).hexdigest()
