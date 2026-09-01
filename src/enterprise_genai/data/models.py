from datetime import date
from typing import Literal, Self

from pydantic import BaseModel, Field, model_validator


class DatasetMetadata(BaseModel):
    dataset_version: str
    schema_version: str
    random_seed: int


class Firm(BaseModel):
    firm_id: str
    name: str


class Fund(BaseModel):
    fund_id: str
    firm_id: str
    name: str
    vintage_year: int
    committed_capital_usd: int = Field(gt=0)


class Company(BaseModel):
    company_id: str
    fund_id: str
    name: str
    industry: str
    headquarters_country: str
    investment_date: date
    ownership_pct: float = Field(ge=0, le=100)


class Customer(BaseModel):
    customer_id: str
    name: str
    industry: str
    country: str


class Supplier(BaseModel):
    supplier_id: str
    name: str
    category: str
    country: str


class CompanyCustomer(BaseModel):
    relationship_id: str
    company_id: str
    customer_id: str
    revenue_share_pct: float = Field(ge=0, le=100)
    relationship_start_date: date
    relationship_status: Literal["active", "at_risk", "ended"]


class CompanySupplier(BaseModel):
    relationship_id: str
    company_id: str
    supplier_id: str
    spend_share_pct: float = Field(ge=0, le=100)
    criticality: Literal["low", "medium", "high", "critical"]
    single_source: bool
    relationship_status: Literal["active", "at_risk", "ended"]


class FinancialMetric(BaseModel):
    company_id: str
    period: str = Field(pattern=r"^\d{4}Q[1-4]$")
    revenue_usd: int = Field(ge=0)
    ebitda_usd: int
    gross_margin_pct: float = Field(ge=0, le=100)
    net_retention_pct: float | None = Field(default=None, ge=0, le=300)
    customer_count: int | None = Field(default=None, ge=0)
    employee_count: int | None = Field(default=None, ge=0)


class OperationalMetric(BaseModel):
    metric_id: str
    company_id: str
    period: str = Field(pattern=r"^\d{4}Q[1-4]$")
    metric_name: str
    metric_value: float
    unit: str


class GeographicExposure(BaseModel):
    exposure_id: str
    company_id: str
    country: str
    exposure_type: Literal[
        "revenue",
        "supplier",
        "employee",
        "manufacturing",
        "project",
    ]
    exposure_pct: float = Field(ge=0, le=100)


class Risk(BaseModel):
    risk_id: str
    company_id: str
    risk_category: str
    title: str
    severity: Literal["low", "medium", "high", "critical"]
    status: Literal["open", "monitoring", "mitigated", "closed"]
    identified_date: date
    description: str


class Transaction(BaseModel):
    transaction_id: str
    company_id: str
    transaction_type: str
    announcement_date: date
    close_date: date | None = None
    value_usd: int | None = Field(default=None, gt=0)
    counterparty: str


class EnterpriseUniverse(BaseModel):
    metadata: DatasetMetadata
    firms: list[Firm]
    funds: list[Fund]
    companies: list[Company]
    customers: list[Customer]
    suppliers: list[Supplier]
    company_customers: list[CompanyCustomer]
    company_suppliers: list[CompanySupplier]
    financial_metrics: list[FinancialMetric]
    operational_metrics: list[OperationalMetric]
    geographic_exposures: list[GeographicExposure]
    risks: list[Risk]
    transactions: list[Transaction]

    @staticmethod
    def _assert_unique(values: list[str], label: str) -> None:
        if len(values) != len(set(values)):
            raise ValueError(f"Duplicate {label} detected.")

    @model_validator(mode="after")
    def validate_universe(self) -> Self:
        self._assert_unique(
            [firm.firm_id for firm in self.firms],
            "firm_id",
        )
        self._assert_unique(
            [fund.fund_id for fund in self.funds],
            "fund_id",
        )
        self._assert_unique(
            [company.company_id for company in self.companies],
            "company_id",
        )
        self._assert_unique(
            [customer.customer_id for customer in self.customers],
            "customer_id",
        )
        self._assert_unique(
            [supplier.supplier_id for supplier in self.suppliers],
            "supplier_id",
        )
        self._assert_unique(
            [relationship.relationship_id for relationship in self.company_customers],
            "company-customer relationship_id",
        )
        self._assert_unique(
            [relationship.relationship_id for relationship in self.company_suppliers],
            "company-supplier relationship_id",
        )
        self._assert_unique(
            [f"{metric.company_id}:{metric.period}" for metric in self.financial_metrics],
            "financial company-period",
        )
        self._assert_unique(
            [metric.metric_id for metric in self.operational_metrics],
            "operational metric_id",
        )
        self._assert_unique(
            [
                f"{metric.company_id}:{metric.period}:{metric.metric_name}"
                for metric in self.operational_metrics
            ],
            "operational company-period-metric",
        )
        self._assert_unique(
            [exposure.exposure_id for exposure in self.geographic_exposures],
            "exposure_id",
        )
        self._assert_unique(
            [risk.risk_id for risk in self.risks],
            "risk_id",
        )
        self._assert_unique(
            [transaction.transaction_id for transaction in self.transactions],
            "transaction_id",
        )

        firm_ids = {firm.firm_id for firm in self.firms}
        fund_ids = {fund.fund_id for fund in self.funds}
        company_ids = {company.company_id for company in self.companies}
        customer_ids = {customer.customer_id for customer in self.customers}
        supplier_ids = {supplier.supplier_id for supplier in self.suppliers}

        for fund in self.funds:
            if fund.firm_id not in firm_ids:
                raise ValueError(f"Fund {fund.fund_id} references unknown firm {fund.firm_id}.")

        for company in self.companies:
            if company.fund_id not in fund_ids:
                raise ValueError(
                    f"Company {company.company_id} references unknown fund {company.fund_id}."
                )

        for relationship in self.company_customers:
            if relationship.company_id not in company_ids:
                raise ValueError(f"{relationship.relationship_id} references unknown company.")
            if relationship.customer_id not in customer_ids:
                raise ValueError(f"{relationship.relationship_id} references unknown customer.")

        for relationship in self.company_suppliers:
            if relationship.company_id not in company_ids:
                raise ValueError(f"{relationship.relationship_id} references unknown company.")
            if relationship.supplier_id not in supplier_ids:
                raise ValueError(f"{relationship.relationship_id} references unknown supplier.")

        for metric in self.financial_metrics:
            if metric.company_id not in company_ids:
                raise ValueError(
                    f"Financial metric references unknown company {metric.company_id}."
                )

        for metric in self.operational_metrics:
            if metric.company_id not in company_ids:
                raise ValueError(
                    f"{metric.metric_id} references unknown company {metric.company_id}."
                )

        for exposure in self.geographic_exposures:
            if exposure.company_id not in company_ids:
                raise ValueError(f"{exposure.exposure_id} references unknown company.")

        for risk in self.risks:
            if risk.company_id not in company_ids:
                raise ValueError(f"{risk.risk_id} references unknown company.")

        for transaction in self.transactions:
            if transaction.company_id not in company_ids:
                raise ValueError(f"{transaction.transaction_id} references unknown company.")

        return self
