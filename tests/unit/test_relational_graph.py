from collections.abc import Iterator
from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy.dialects import postgresql
from sqlalchemy.exc import SQLAlchemyError

from enterprise_genai.db.models import (
    CanonicalFactRow,
    CompanyCustomerRow,
    CompanyRow,
    CompanySupplierRow,
    CustomerRow,
    SupplierRow,
)
from enterprise_genai.execution.contracts import (
    GraphPath,
    GraphPayload,
    GraphQuery,
)
from enterprise_genai.execution.relational_graph import (
    RelationalGraphExecutor,
    build_relationship_statement,
)

VERSION = "northstar-v1"


class _FakeSession:
    def __init__(
        self,
        *,
        objects: dict[
            tuple[type[object], object],
            object,
        ],
        scalar_batches: list[list[object]] | None = None,
        scalar_error: (SQLAlchemyError | None) = None,
    ) -> None:
        self.objects = objects
        self.scalar_batches = list(scalar_batches or [])
        self.scalar_error = scalar_error

    def get(
        self,
        model: type[object],
        identity: object,
    ) -> object | None:
        return self.objects.get(
            (
                model,
                identity,
            )
        )

    def scalars(
        self,
        statement: object,
    ) -> Iterator[object]:
        del statement

        if self.scalar_error is not None:
            raise self.scalar_error

        if not self.scalar_batches:
            return iter(())

        return iter(self.scalar_batches.pop(0))


class _Clock:
    def __init__(
        self,
    ) -> None:
        self.values = iter(
            (
                1.0,
                1.002,
            )
        )

    def __call__(
        self,
    ) -> float:
        return next(self.values)


def _fact(
    fact_id: str,
    fact_type: str,
) -> CanonicalFactRow:
    return CanonicalFactRow(
        dataset_version=VERSION,
        fact_id=fact_id,
        fact_type=fact_type,
    )


def _company(
    company_id: str,
    name: str,
) -> CompanyRow:
    return CompanyRow(
        dataset_version=VERSION,
        company_id=company_id,
        fund_id="FUND-001",
        name=name,
        industry="Industrial Technology",
        headquarters_country=("United States"),
        investment_date=date(
            2020,
            1,
            1,
        ),
        ownership_pct=Decimal("70.000"),
    )


def _supplier(
    supplier_id: str,
    name: str,
    country: str,
) -> SupplierRow:
    return SupplierRow(
        dataset_version=VERSION,
        supplier_id=supplier_id,
        name=name,
        category="components",
        country=country,
    )


def _customer(
    customer_id: str,
    name: str,
    country: str,
) -> CustomerRow:
    return CustomerRow(
        dataset_version=VERSION,
        customer_id=customer_id,
        name=name,
        industry="Banking",
        country=country,
    )


def _supplier_edge(
    relationship_id: str,
    supplier_id: str,
    *,
    criticality: str = "high",
    single_source: bool = False,
) -> CompanySupplierRow:
    return CompanySupplierRow(
        dataset_version=VERSION,
        relationship_id=(relationship_id),
        company_id="PC-002",
        supplier_id=supplier_id,
        spend_share_pct=Decimal("20.000"),
        criticality=criticality,
        single_source=(single_source),
        relationship_status=("active"),
    )


def _executor(
    session: _FakeSession,
) -> RelationalGraphExecutor:
    return RelationalGraphExecutor(
        session,  # type: ignore[arg-type]
        clock=_Clock(),
    )


def test_company_to_suppliers_returns_attributes_and_provenance() -> None:
    company = _company(
        "PC-002",
        "Alder Manufacturing",
    )

    supplier_a = _supplier(
        "SUP-003",
        "Forge Systems",
        "United States",
    )

    supplier_b = _supplier(
        "SUP-005",
        "TitaniumWorks GmbH",
        "Germany",
    )

    edge_a = _supplier_edge(
        "CS-002",
        "SUP-003",
    )

    edge_b = _supplier_edge(
        "CS-003",
        "SUP-005",
        criticality="critical",
        single_source=True,
    )

    objects = {
        (
            CompanyRow,
            (
                VERSION,
                "PC-002",
            ),
        ): company,
        (
            SupplierRow,
            (
                VERSION,
                "SUP-003",
            ),
        ): supplier_a,
        (
            SupplierRow,
            (
                VERSION,
                "SUP-005",
            ),
        ): supplier_b,
        (
            CanonicalFactRow,
            (
                VERSION,
                "PC-002",
            ),
        ): _fact(
            "PC-002",
            "company",
        ),
        (
            CanonicalFactRow,
            (
                VERSION,
                "SUP-003",
            ),
        ): _fact(
            "SUP-003",
            "supplier",
        ),
        (
            CanonicalFactRow,
            (
                VERSION,
                "SUP-005",
            ),
        ): _fact(
            "SUP-005",
            "supplier",
        ),
        (
            CanonicalFactRow,
            (
                VERSION,
                "CS-002",
            ),
        ): _fact(
            "CS-002",
            "company_supplier",
        ),
        (
            CanonicalFactRow,
            (
                VERSION,
                "CS-003",
            ),
        ): _fact(
            "CS-003",
            "company_supplier",
        ),
    }

    result = _executor(
        _FakeSession(
            objects=objects,
            scalar_batches=[
                [
                    edge_a,
                    edge_b,
                ]
            ],
        )
    ).execute(
        GraphQuery(
            start_entity_type=("company"),
            start_entity_id="PC-002",
            paths=(
                GraphPath(
                    hops=("company_suppliers",),
                ),
            ),
        )
    )

    assert result.status == "ok"
    assert result.duration_ms == (pytest.approx(2.0))

    assert isinstance(
        result.payload,
        GraphPayload,
    )

    nodes = {node.entity_id: node for node in result.payload.nodes}

    assert nodes["SUP-005"].attributes["country"] == "Germany"

    assert nodes["SUP-005"].canonical_fact_ids == ("SUP-005",)

    edges = {edge.relationship_id: edge for edge in result.payload.edges}

    critical = edges["CS-003"]

    assert critical.attributes["criticality"] == "critical"

    assert critical.attributes["single_source"] is True

    assert critical.canonical_fact_ids == ("CS-003",)


def test_inverse_customer_to_company_preserves_canonical_edge_orientation() -> None:
    customer = _customer(
        "CUST-010",
        "Deutsche Retail Bank",
        "Germany",
    )

    company = _company(
        "PC-006",
        "Orbis Cybersecurity",
    )

    edge = CompanyCustomerRow(
        dataset_version=VERSION,
        relationship_id="CC-010",
        company_id="PC-006",
        customer_id="CUST-010",
        revenue_share_pct=Decimal("19.000"),
        relationship_start_date=date(
            2021,
            2,
            17,
        ),
        relationship_status="active",
    )

    objects = {
        (
            CustomerRow,
            (
                VERSION,
                "CUST-010",
            ),
        ): customer,
        (
            CompanyRow,
            (
                VERSION,
                "PC-006",
            ),
        ): company,
        (
            CanonicalFactRow,
            (
                VERSION,
                "CUST-010",
            ),
        ): _fact(
            "CUST-010",
            "customer",
        ),
        (
            CanonicalFactRow,
            (
                VERSION,
                "PC-006",
            ),
        ): _fact(
            "PC-006",
            "company",
        ),
        (
            CanonicalFactRow,
            (
                VERSION,
                "CC-010",
            ),
        ): _fact(
            "CC-010",
            "company_customer",
        ),
    }

    result = _executor(
        _FakeSession(
            objects=objects,
            scalar_batches=[
                [edge],
            ],
        )
    ).execute(
        GraphQuery(
            start_entity_type=("customer"),
            start_entity_id=("CUST-010"),
            paths=(
                GraphPath(
                    hops=("customer_company",),
                ),
            ),
        )
    )

    assert result.status == "ok"

    assert isinstance(
        result.payload,
        GraphPayload,
    )

    returned = result.payload.edges[0]

    assert returned.relationship_id == "CC-010"

    assert returned.source_type == ("company")
    assert returned.source_id == ("PC-006")

    assert returned.target_type == ("customer")
    assert returned.target_id == ("CUST-010")


def test_two_hop_customer_company_supplier_traversal() -> None:
    customer = _customer(
        "CUST-003",
        "Industrial Buyer",
        "France",
    )

    company = _company(
        "PC-002",
        "Alder Manufacturing",
    )

    supplier = _supplier(
        "SUP-005",
        "TitaniumWorks GmbH",
        "Germany",
    )

    customer_edge = CompanyCustomerRow(
        dataset_version=VERSION,
        relationship_id="CC-003",
        company_id="PC-002",
        customer_id="CUST-003",
        revenue_share_pct=(Decimal("24.000")),
        relationship_start_date=(
            date(
                2019,
                3,
                11,
            )
        ),
        relationship_status=("active"),
    )

    supplier_edge = _supplier_edge(
        "CS-003",
        "SUP-005",
        criticality="critical",
        single_source=True,
    )

    objects = {
        (
            CustomerRow,
            (
                VERSION,
                "CUST-003",
            ),
        ): customer,
        (
            CompanyRow,
            (
                VERSION,
                "PC-002",
            ),
        ): company,
        (
            SupplierRow,
            (
                VERSION,
                "SUP-005",
            ),
        ): supplier,
    }

    for fact_id, fact_type in (
        (
            "CUST-003",
            "customer",
        ),
        (
            "PC-002",
            "company",
        ),
        (
            "SUP-005",
            "supplier",
        ),
        (
            "CC-003",
            "company_customer",
        ),
        (
            "CS-003",
            "company_supplier",
        ),
    ):
        objects[
            (
                CanonicalFactRow,
                (
                    VERSION,
                    fact_id,
                ),
            )
        ] = _fact(
            fact_id,
            fact_type,
        )

    result = _executor(
        _FakeSession(
            objects=objects,
            scalar_batches=[
                [customer_edge],
                [supplier_edge],
            ],
        )
    ).execute(
        GraphQuery(
            start_entity_type=("customer"),
            start_entity_id=("CUST-003"),
            paths=(
                GraphPath(
                    hops=(
                        "customer_company",
                        "company_suppliers",
                    ),
                ),
            ),
        )
    )

    assert result.status == "ok"

    assert isinstance(
        result.payload,
        GraphPayload,
    )

    assert [node.entity_id for node in (result.payload.nodes)] == [
        "PC-002",
        "CUST-003",
        "SUP-005",
    ]

    assert [edge.relationship_id for edge in (result.payload.edges)] == [
        "CC-003",
        "CS-003",
    ]


def test_missing_start_entity_and_existing_isolated_entity_are_distinct() -> None:
    missing = _executor(
        _FakeSession(
            objects={},
        )
    ).execute(
        GraphQuery(
            start_entity_type=("company"),
            start_entity_id="PC-999",
            paths=(
                GraphPath(
                    hops=("company_suppliers",),
                ),
            ),
        )
    )

    assert missing.status == ("empty")

    assert isinstance(
        missing.payload,
        GraphPayload,
    )

    assert missing.payload.empty_reason == "start_entity_not_found"

    company = _company(
        "PC-002",
        "Alder Manufacturing",
    )

    isolated_objects = {
        (
            CompanyRow,
            (
                VERSION,
                "PC-002",
            ),
        ): company,
        (
            CanonicalFactRow,
            (
                VERSION,
                "PC-002",
            ),
        ): _fact(
            "PC-002",
            "company",
        ),
    }

    isolated = _executor(
        _FakeSession(
            objects=isolated_objects,
            scalar_batches=[
                [],
            ],
        )
    ).execute(
        GraphQuery(
            start_entity_type=("company"),
            start_entity_id="PC-002",
            paths=(
                GraphPath(
                    hops=("company_suppliers",),
                ),
            ),
        )
    )

    assert isolated.status == ("empty")

    assert isinstance(
        isolated.payload,
        GraphPayload,
    )

    assert isolated.payload.empty_reason == "no_relationships"

    assert [node.entity_id for node in (isolated.payload.nodes)] == ["PC-002"]


def test_missing_relationship_fact_is_integrity_error() -> None:
    company = _company(
        "PC-002",
        "Alder Manufacturing",
    )

    supplier = _supplier(
        "SUP-005",
        "TitaniumWorks GmbH",
        "Germany",
    )

    edge = _supplier_edge(
        "CS-003",
        "SUP-005",
    )

    objects = {
        (
            CompanyRow,
            (
                VERSION,
                "PC-002",
            ),
        ): company,
        (
            SupplierRow,
            (
                VERSION,
                "SUP-005",
            ),
        ): supplier,
        (
            CanonicalFactRow,
            (
                VERSION,
                "PC-002",
            ),
        ): _fact(
            "PC-002",
            "company",
        ),
        (
            CanonicalFactRow,
            (
                VERSION,
                "SUP-005",
            ),
        ): _fact(
            "SUP-005",
            "supplier",
        ),
    }

    result = _executor(
        _FakeSession(
            objects=objects,
            scalar_batches=[
                [edge],
            ],
        )
    ).execute(
        GraphQuery(
            start_entity_type=("company"),
            start_entity_id="PC-002",
            paths=(
                GraphPath(
                    hops=("company_suppliers",),
                ),
            ),
        )
    )

    assert result.status == ("error")
    assert result.payload is None
    assert result.error is not None

    assert "canonical fact registry" in result.error


def test_database_failure_returns_graph_error_result() -> None:
    company = _company(
        "PC-002",
        "Alder Manufacturing",
    )

    objects = {
        (
            CompanyRow,
            (
                VERSION,
                "PC-002",
            ),
        ): company,
        (
            CanonicalFactRow,
            (
                VERSION,
                "PC-002",
            ),
        ): _fact(
            "PC-002",
            "company",
        ),
    }

    result = _executor(
        _FakeSession(
            objects=objects,
            scalar_error=(SQLAlchemyError("simulated")),
        )
    ).execute(
        GraphQuery(
            start_entity_type=("company"),
            start_entity_id="PC-002",
            paths=(
                GraphPath(
                    hops=("company_suppliers",),
                ),
            ),
        )
    )

    assert result.status == ("error")
    assert result.payload is None
    assert result.error is not None

    assert "SQLAlchemyError" in result.error


def test_relationship_statement_uses_bound_frontier_values() -> None:
    injected = "PC-002') OR TRUE --"

    statement = build_relationship_statement(
        dataset_version=VERSION,
        relation=("company_suppliers"),
        frontier_ids=(injected,),
    )

    compiled = statement.compile(
        dialect=postgresql.dialect(),
        compile_kwargs={
            "literal_binds": False,
        },
    )

    sql = str(compiled)

    assert injected not in sql

    flattened_values = repr(compiled.params)

    assert injected in (flattened_values)
