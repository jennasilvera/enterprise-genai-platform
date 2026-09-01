import hashlib

import pytest
from pydantic import ValidationError

from enterprise_genai.data.models import Company
from enterprise_genai.data.universe import build_universe


def test_universe_has_expected_core_entities() -> None:
    universe = build_universe()

    assert universe.metadata.dataset_version == "northstar-v1"
    assert len(universe.firms) == 1
    assert len(universe.funds) == 1
    assert len(universe.companies) == 8
    assert len(universe.customers) == 14
    assert len(universe.suppliers) == 14


def test_company_ids_are_unique() -> None:
    universe = build_universe()

    company_ids = [company.company_id for company in universe.companies]

    assert len(company_ids) == len(set(company_ids))


def test_known_german_critical_supplier_relationships() -> None:
    universe = build_universe()

    suppliers_by_id = {supplier.supplier_id: supplier for supplier in universe.suppliers}

    affected_company_ids = {
        relationship.company_id
        for relationship in universe.company_suppliers
        if relationship.criticality == "critical"
        and suppliers_by_id[relationship.supplier_id].country == "Germany"
    }

    assert affected_company_ids == {"PC-002", "PC-008"}


def test_orbis_incident_identifier_is_canonical_truth() -> None:
    universe = build_universe()

    orbis_risks = [risk for risk in universe.risks if risk.company_id == "PC-006"]

    assert any("ORBIS-IDX-7" in risk.description for risk in orbis_risks)


def test_invalid_ownership_percentage_is_rejected() -> None:
    with pytest.raises(ValidationError):
        Company(
            company_id="PC-999",
            fund_id="FUND-001",
            name="Invalid Company",
            industry="test",
            headquarters_country="United States",
            investment_date="2026-01-01",
            ownership_pct=101.0,
        )


def test_universe_serialization_is_deterministic() -> None:
    first = build_universe().model_dump_json(indent=2)
    second = build_universe().model_dump_json(indent=2)

    first_hash = hashlib.sha256(first.encode()).hexdigest()
    second_hash = hashlib.sha256(second.encode()).hexdigest()

    assert first_hash == second_hash
