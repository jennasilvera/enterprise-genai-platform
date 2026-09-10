from collections.abc import Iterator
from datetime import date
from decimal import Decimal

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
    GraphPayload,
    PortfolioGraphPredicate,
    PortfolioGraphQuery,
)
from enterprise_genai.execution.relational_graph import (
    RelationalGraphExecutor,
    build_portfolio_predicate_statement,
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
        scalar_batches: list[list[object]],
        scalar_error: (SQLAlchemyError | None) = None,
    ) -> None:
        self.objects = objects
        self.scalar_batches = list(scalar_batches)
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
        industry="Test",
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
    company_id: str,
    supplier_id: str,
    *,
    criticality: str = "high",
    single_source: bool = False,
    relationship_status: str = "active",
) -> CompanySupplierRow:
    return CompanySupplierRow(
        dataset_version=VERSION,
        relationship_id=(relationship_id),
        company_id=company_id,
        supplier_id=supplier_id,
        spend_share_pct=Decimal("20.000"),
        criticality=criticality,
        single_source=single_source,
        relationship_status=(relationship_status),
    )


def _customer_edge(
    relationship_id: str,
    company_id: str,
    customer_id: str,
) -> CompanyCustomerRow:
    return CompanyCustomerRow(
        dataset_version=VERSION,
        relationship_id=(relationship_id),
        company_id=company_id,
        customer_id=customer_id,
        revenue_share_pct=Decimal("19.000"),
        relationship_start_date=date(
            2021,
            2,
            17,
        ),
        relationship_status="active",
    )


def _executor(
    session: _FakeSession,
) -> RelationalGraphExecutor:
    return RelationalGraphExecutor(
        session,  # type: ignore[arg-type]
        clock=_Clock(),
    )


def _object_map(
    *,
    companies: tuple[
        CompanyRow,
        ...,
    ] = (),
    suppliers: tuple[
        SupplierRow,
        ...,
    ] = (),
    customers: tuple[
        CustomerRow,
        ...,
    ] = (),
    edges: tuple[
        CompanyCustomerRow | CompanySupplierRow,
        ...,
    ] = (),
) -> dict[
    tuple[type[object], object],
    object,
]:
    objects: dict[
        tuple[type[object], object],
        object,
    ] = {}

    for company in companies:
        objects[
            (
                CompanyRow,
                (
                    VERSION,
                    company.company_id,
                ),
            )
        ] = company

        objects[
            (
                CanonicalFactRow,
                (
                    VERSION,
                    company.company_id,
                ),
            )
        ] = _fact(
            company.company_id,
            "company",
        )

    for supplier in suppliers:
        objects[
            (
                SupplierRow,
                (
                    VERSION,
                    supplier.supplier_id,
                ),
            )
        ] = supplier

        objects[
            (
                CanonicalFactRow,
                (
                    VERSION,
                    supplier.supplier_id,
                ),
            )
        ] = _fact(
            supplier.supplier_id,
            "supplier",
        )

    for customer in customers:
        objects[
            (
                CustomerRow,
                (
                    VERSION,
                    customer.customer_id,
                ),
            )
        ] = customer

        objects[
            (
                CanonicalFactRow,
                (
                    VERSION,
                    customer.customer_id,
                ),
            )
        ] = _fact(
            customer.customer_id,
            "customer",
        )

    for edge in edges:
        fact_type = (
            "company_customer"
            if isinstance(
                edge,
                CompanyCustomerRow,
            )
            else "company_supplier"
        )

        objects[
            (
                CanonicalFactRow,
                (
                    VERSION,
                    edge.relationship_id,
                ),
            )
        ] = _fact(
            edge.relationship_id,
            fact_type,
        )

    return objects


def test_critical_german_supplier_discovers_two_companies() -> None:
    alder = _company(
        "PC-002",
        "Alder Manufacturing",
    )
    nova = _company(
        "PC-008",
        "NovaBio Instruments",
    )

    titanium = _supplier(
        "SUP-005",
        "TitaniumWorks GmbH",
        "Germany",
    )
    helix = _supplier(
        "SUP-011",
        "Helix Motion GmbH",
        "Germany",
    )

    cs003 = _supplier_edge(
        "CS-003",
        "PC-002",
        "SUP-005",
        criticality="critical",
        single_source=True,
        relationship_status="at_risk",
    )
    cs011 = _supplier_edge(
        "CS-011",
        "PC-008",
        "SUP-011",
        criticality="critical",
        single_source=True,
        relationship_status="at_risk",
    )

    result = _executor(
        _FakeSession(
            objects=_object_map(
                companies=(
                    alder,
                    nova,
                ),
                suppliers=(
                    titanium,
                    helix,
                ),
                edges=(
                    cs003,
                    cs011,
                ),
            ),
            scalar_batches=[
                [
                    alder,
                    nova,
                ],
                [
                    cs003,
                    cs011,
                ],
            ],
        )
    ).execute(
        PortfolioGraphQuery(
            predicates=(
                PortfolioGraphPredicate(
                    relationship_type=("company_supplier"),
                    target_country="Germany",
                    criticality="critical",
                ),
            )
        )
    )

    assert result.status == "ok"

    assert isinstance(
        result.payload,
        GraphPayload,
    )

    assert result.payload.matched_company_ids == (
        "PC-002",
        "PC-008",
    )

    assert [edge.relationship_id for edge in result.payload.edges] == [
        "CS-003",
        "CS-011",
    ]

    assert {node.entity_id for node in result.payload.nodes if node.entity_type == "supplier"} == {
        "SUP-005",
        "SUP-011",
    }


def test_distinct_supplier_predicates_use_existential_intersection() -> None:
    alder = _company(
        "PC-002",
        "Alder Manufacturing",
    )
    nova = _company(
        "PC-008",
        "NovaBio Instruments",
    )

    helix = _supplier(
        "SUP-011",
        "Helix Motion GmbH",
        "Germany",
    )
    alpine = _supplier(
        "SUP-012",
        "Alpine Optics AG",
        "Switzerland",
    )

    cs003 = _supplier_edge(
        "CS-003",
        "PC-002",
        "SUP-005",
        criticality="critical",
    )
    cs011 = _supplier_edge(
        "CS-011",
        "PC-008",
        "SUP-011",
        criticality="critical",
    )
    cs012 = _supplier_edge(
        "CS-012",
        "PC-008",
        "SUP-012",
    )

    result = _executor(
        _FakeSession(
            objects=_object_map(
                companies=(nova,),
                suppliers=(
                    helix,
                    alpine,
                ),
                edges=(
                    cs011,
                    cs012,
                ),
            ),
            scalar_batches=[
                [
                    alder,
                    nova,
                ],
                [
                    cs003,
                    cs011,
                ],
                [
                    cs012,
                ],
            ],
        )
    ).execute(
        PortfolioGraphQuery(
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
    )

    assert result.status == "ok"

    assert isinstance(
        result.payload,
        GraphPayload,
    )

    assert result.payload.matched_company_ids == ("PC-008",)

    assert [edge.relationship_id for edge in result.payload.edges] == [
        "CS-011",
        "CS-012",
    ]


def test_german_customer_discovers_orbis() -> None:
    orbis = _company(
        "PC-006",
        "Orbis Cybersecurity",
    )
    rheinwerk = _customer(
        "CUST-010",
        "Rheinwerk AG",
        "Germany",
    )
    cc010 = _customer_edge(
        "CC-010",
        "PC-006",
        "CUST-010",
    )

    result = _executor(
        _FakeSession(
            objects=_object_map(
                companies=(orbis,),
                customers=(rheinwerk,),
                edges=(cc010,),
            ),
            scalar_batches=[
                [
                    orbis,
                ],
                [
                    cc010,
                ],
            ],
        )
    ).execute(
        PortfolioGraphQuery(
            predicates=(
                PortfolioGraphPredicate(
                    relationship_type=("company_customer"),
                    target_country="Germany",
                ),
            )
        )
    )

    assert result.status == "ok"

    assert isinstance(
        result.payload,
        GraphPayload,
    )

    assert result.payload.matched_company_ids == ("PC-006",)

    assert [edge.relationship_id for edge in result.payload.edges] == [
        "CC-010",
    ]


def test_no_portfolio_match_returns_typed_empty() -> None:
    alder = _company(
        "PC-002",
        "Alder Manufacturing",
    )

    result = _executor(
        _FakeSession(
            objects={},
            scalar_batches=[
                [
                    alder,
                ],
                [],
            ],
        )
    ).execute(
        PortfolioGraphQuery(
            predicates=(
                PortfolioGraphPredicate(
                    relationship_type=("company_supplier"),
                    target_country="Brazil",
                ),
            )
        )
    )

    assert result.status == "empty"

    assert isinstance(
        result.payload,
        GraphPayload,
    )

    assert result.payload.empty_reason == "no_matches"

    assert result.payload.matched_company_ids == ()

    assert result.payload.nodes == ()
    assert result.payload.edges == ()


def test_unknown_candidate_company_is_integrity_error() -> None:
    result = _executor(
        _FakeSession(
            objects={},
            scalar_batches=[
                [],
            ],
        )
    ).execute(
        PortfolioGraphQuery(
            candidate_company_ids=("PC-999",),
            predicates=(
                PortfolioGraphPredicate(
                    relationship_type=("company_supplier"),
                    target_country="Germany",
                ),
            ),
        )
    )

    assert result.status == "error"

    assert result.error is not None

    assert "unknown company IDs" in result.error


def test_candidate_scope_is_preserved() -> None:
    nova = _company(
        "PC-008",
        "NovaBio Instruments",
    )
    helix = _supplier(
        "SUP-011",
        "Helix Motion GmbH",
        "Germany",
    )
    cs011 = _supplier_edge(
        "CS-011",
        "PC-008",
        "SUP-011",
        criticality="critical",
    )

    result = _executor(
        _FakeSession(
            objects=_object_map(
                companies=(nova,),
                suppliers=(helix,),
                edges=(cs011,),
            ),
            scalar_batches=[
                [
                    nova,
                ],
                [
                    cs011,
                ],
            ],
        )
    ).execute(
        PortfolioGraphQuery(
            candidate_company_ids=("PC-008",),
            predicates=(
                PortfolioGraphPredicate(
                    relationship_type=("company_supplier"),
                    target_country="Germany",
                    criticality="critical",
                ),
            ),
        )
    )

    assert result.status == "ok"

    assert isinstance(
        result.payload,
        GraphPayload,
    )

    assert result.payload.matched_company_ids == ("PC-008",)


def test_portfolio_predicate_sql_uses_bound_parameters() -> None:
    injected_country = "Germany' OR 1=1 --"
    injected_company = "PC-002' OR 1=1 --"

    predicate = PortfolioGraphPredicate(
        relationship_type=("company_supplier"),
        target_country=(injected_country),
        criticality="critical",
    )

    statement = build_portfolio_predicate_statement(
        dataset_version=VERSION,
        predicate=predicate,
        company_ids=(injected_company,),
    )

    compiled = statement.compile(
        dialect=(postgresql.dialect()),
        compile_kwargs={
            "literal_binds": False,
        },
    )

    sql = str(compiled)

    assert injected_country not in sql
    assert injected_company not in sql

    params = repr(compiled.params)

    assert injected_country in params
    assert injected_company in params
