from datetime import date
from decimal import Decimal

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Date,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from enterprise_genai.db.base import Base

PERCENT = Numeric(6, 3)
MONEY = BigInteger


class DatasetVersionRow(Base):
    __tablename__ = "dataset_versions"

    dataset_version: Mapped[str] = mapped_column(
        String(64),
        primary_key=True,
    )
    schema_version: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )
    random_seed: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )


class CanonicalFactRow(Base):
    __tablename__ = "canonical_facts"
    __table_args__ = (
        CheckConstraint(
            "char_length(fact_type) > 0",
            name="ck_canonical_facts_fact_type",
        ),
    )

    dataset_version: Mapped[str] = mapped_column(
        ForeignKey("dataset_versions.dataset_version"),
        primary_key=True,
    )
    fact_id: Mapped[str] = mapped_column(
        String(128),
        primary_key=True,
    )
    fact_type: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )


class FirmRow(Base):
    __tablename__ = "firms"

    dataset_version: Mapped[str] = mapped_column(
        ForeignKey("dataset_versions.dataset_version"),
        primary_key=True,
    )
    firm_id: Mapped[str] = mapped_column(
        String(64),
        primary_key=True,
    )
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )


class FundRow(Base):
    __tablename__ = "funds"
    __table_args__ = (
        ForeignKeyConstraint(
            ["dataset_version", "firm_id"],
            ["firms.dataset_version", "firms.firm_id"],
            name="fk_funds_firm",
        ),
        CheckConstraint(
            "committed_capital_usd > 0",
            name="ck_funds_committed_capital_usd",
        ),
    )

    dataset_version: Mapped[str] = mapped_column(
        String(64),
        primary_key=True,
    )
    fund_id: Mapped[str] = mapped_column(
        String(64),
        primary_key=True,
    )
    firm_id: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    vintage_year: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    committed_capital_usd: Mapped[int] = mapped_column(
        MONEY,
        nullable=False,
    )


class CompanyRow(Base):
    __tablename__ = "companies"
    __table_args__ = (
        ForeignKeyConstraint(
            ["dataset_version", "fund_id"],
            ["funds.dataset_version", "funds.fund_id"],
            name="fk_companies_fund",
        ),
        CheckConstraint(
            "ownership_pct >= 0 AND ownership_pct <= 100",
            name="ck_companies_ownership_pct",
        ),
    )

    dataset_version: Mapped[str] = mapped_column(
        String(64),
        primary_key=True,
    )
    company_id: Mapped[str] = mapped_column(
        String(64),
        primary_key=True,
    )
    fund_id: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    industry: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    headquarters_country: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
    )
    investment_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
    )
    ownership_pct: Mapped[Decimal] = mapped_column(
        PERCENT,
        nullable=False,
    )


class CustomerRow(Base):
    __tablename__ = "customers"

    dataset_version: Mapped[str] = mapped_column(
        ForeignKey("dataset_versions.dataset_version"),
        primary_key=True,
    )
    customer_id: Mapped[str] = mapped_column(
        String(64),
        primary_key=True,
    )
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    industry: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    country: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
    )


class SupplierRow(Base):
    __tablename__ = "suppliers"

    dataset_version: Mapped[str] = mapped_column(
        ForeignKey("dataset_versions.dataset_version"),
        primary_key=True,
    )
    supplier_id: Mapped[str] = mapped_column(
        String(64),
        primary_key=True,
    )
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    category: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    country: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
    )


class CompanyCustomerRow(Base):
    __tablename__ = "company_customers"
    __table_args__ = (
        ForeignKeyConstraint(
            ["dataset_version", "company_id"],
            [
                "companies.dataset_version",
                "companies.company_id",
            ],
            name="fk_company_customers_company",
        ),
        ForeignKeyConstraint(
            ["dataset_version", "customer_id"],
            [
                "customers.dataset_version",
                "customers.customer_id",
            ],
            name="fk_company_customers_customer",
        ),
        CheckConstraint(
            "revenue_share_pct >= 0 AND revenue_share_pct <= 100",
            name="ck_company_customers_revenue_share_pct",
        ),
        CheckConstraint(
            "relationship_status IN ('active', 'at_risk', 'ended')",
            name="ck_company_customers_relationship_status",
        ),
    )

    dataset_version: Mapped[str] = mapped_column(
        String(64),
        primary_key=True,
    )
    relationship_id: Mapped[str] = mapped_column(
        String(64),
        primary_key=True,
    )
    company_id: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )
    customer_id: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )
    revenue_share_pct: Mapped[Decimal] = mapped_column(
        PERCENT,
        nullable=False,
    )
    relationship_start_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
    )
    relationship_status: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
    )


class CompanySupplierRow(Base):
    __tablename__ = "company_suppliers"
    __table_args__ = (
        ForeignKeyConstraint(
            ["dataset_version", "company_id"],
            [
                "companies.dataset_version",
                "companies.company_id",
            ],
            name="fk_company_suppliers_company",
        ),
        ForeignKeyConstraint(
            ["dataset_version", "supplier_id"],
            [
                "suppliers.dataset_version",
                "suppliers.supplier_id",
            ],
            name="fk_company_suppliers_supplier",
        ),
        CheckConstraint(
            "spend_share_pct >= 0 AND spend_share_pct <= 100",
            name="ck_company_suppliers_spend_share_pct",
        ),
        CheckConstraint(
            "criticality IN ('low', 'medium', 'high', 'critical')",
            name="ck_company_suppliers_criticality",
        ),
        CheckConstraint(
            "relationship_status IN ('active', 'at_risk', 'ended')",
            name="ck_company_suppliers_relationship_status",
        ),
    )

    dataset_version: Mapped[str] = mapped_column(
        String(64),
        primary_key=True,
    )
    relationship_id: Mapped[str] = mapped_column(
        String(64),
        primary_key=True,
    )
    company_id: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )
    supplier_id: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )
    spend_share_pct: Mapped[Decimal] = mapped_column(
        PERCENT,
        nullable=False,
    )
    criticality: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
    )
    single_source: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
    )
    relationship_status: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
    )


class FinancialMetricRow(Base):
    __tablename__ = "financial_metrics"
    __table_args__ = (
        ForeignKeyConstraint(
            ["dataset_version", "company_id"],
            [
                "companies.dataset_version",
                "companies.company_id",
            ],
            name="fk_financial_metrics_company",
        ),
        CheckConstraint(
            "period ~ '^[0-9]{4}Q[1-4]$'",
            name="ck_financial_metrics_period",
        ),
        CheckConstraint(
            "revenue_usd >= 0",
            name="ck_financial_metrics_revenue_usd",
        ),
        CheckConstraint(
            "gross_margin_pct >= 0 AND gross_margin_pct <= 100",
            name="ck_financial_metrics_gross_margin_pct",
        ),
        CheckConstraint(
            "net_retention_pct IS NULL OR (net_retention_pct >= 0 AND net_retention_pct <= 300)",
            name="ck_financial_metrics_net_retention_pct",
        ),
        CheckConstraint(
            "customer_count IS NULL OR customer_count >= 0",
            name="ck_financial_metrics_customer_count",
        ),
        CheckConstraint(
            "employee_count IS NULL OR employee_count >= 0",
            name="ck_financial_metrics_employee_count",
        ),
        Index(
            "ix_financial_metrics_period",
            "dataset_version",
            "period",
        ),
    )

    dataset_version: Mapped[str] = mapped_column(
        String(64),
        primary_key=True,
    )
    company_id: Mapped[str] = mapped_column(
        String(64),
        primary_key=True,
    )
    period: Mapped[str] = mapped_column(
        String(6),
        primary_key=True,
    )
    revenue_usd: Mapped[int] = mapped_column(
        MONEY,
        nullable=False,
    )
    ebitda_usd: Mapped[int] = mapped_column(
        MONEY,
        nullable=False,
    )
    gross_margin_pct: Mapped[Decimal] = mapped_column(
        PERCENT,
        nullable=False,
    )
    net_retention_pct: Mapped[Decimal | None] = mapped_column(
        PERCENT,
    )
    customer_count: Mapped[int | None] = mapped_column(
        Integer,
    )
    employee_count: Mapped[int | None] = mapped_column(
        Integer,
    )


class OperationalMetricRow(Base):
    __tablename__ = "operational_metrics"
    __table_args__ = (
        ForeignKeyConstraint(
            ["dataset_version", "company_id"],
            [
                "companies.dataset_version",
                "companies.company_id",
            ],
            name="fk_operational_metrics_company",
        ),
        UniqueConstraint(
            "dataset_version",
            "company_id",
            "period",
            "metric_name",
            name="uq_operational_metrics_company_period_metric",
        ),
        CheckConstraint(
            "period ~ '^[0-9]{4}Q[1-4]$'",
            name="ck_operational_metrics_period",
        ),
        Index(
            "ix_operational_metrics_period",
            "dataset_version",
            "period",
        ),
    )

    dataset_version: Mapped[str] = mapped_column(
        String(64),
        primary_key=True,
    )
    metric_id: Mapped[str] = mapped_column(
        String(128),
        primary_key=True,
    )
    company_id: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )
    period: Mapped[str] = mapped_column(
        String(6),
        nullable=False,
    )
    metric_name: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
    )
    metric_value: Mapped[Decimal] = mapped_column(
        Numeric(20, 6),
        nullable=False,
    )
    unit: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )


class GeographicExposureRow(Base):
    __tablename__ = "geographic_exposures"
    __table_args__ = (
        ForeignKeyConstraint(
            ["dataset_version", "company_id"],
            [
                "companies.dataset_version",
                "companies.company_id",
            ],
            name="fk_geographic_exposures_company",
        ),
        CheckConstraint(
            "exposure_type IN ('revenue', 'supplier', 'employee', 'manufacturing', 'project')",
            name="ck_geographic_exposures_type",
        ),
        CheckConstraint(
            "exposure_pct >= 0 AND exposure_pct <= 100",
            name="ck_geographic_exposures_pct",
        ),
    )

    dataset_version: Mapped[str] = mapped_column(
        String(64),
        primary_key=True,
    )
    exposure_id: Mapped[str] = mapped_column(
        String(64),
        primary_key=True,
    )
    company_id: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )
    country: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
    )
    exposure_type: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
    )
    exposure_pct: Mapped[Decimal] = mapped_column(
        PERCENT,
        nullable=False,
    )


class RiskRow(Base):
    __tablename__ = "risks"
    __table_args__ = (
        ForeignKeyConstraint(
            ["dataset_version", "company_id"],
            [
                "companies.dataset_version",
                "companies.company_id",
            ],
            name="fk_risks_company",
        ),
        CheckConstraint(
            "severity IN ('low', 'medium', 'high', 'critical')",
            name="ck_risks_severity",
        ),
        CheckConstraint(
            "status IN ('open', 'monitoring', 'mitigated', 'closed')",
            name="ck_risks_status",
        ),
    )

    dataset_version: Mapped[str] = mapped_column(
        String(64),
        primary_key=True,
    )
    risk_id: Mapped[str] = mapped_column(
        String(64),
        primary_key=True,
    )
    company_id: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )
    risk_category: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
    )
    title: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    severity: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
    )
    identified_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
    )
    description: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )


class TransactionRow(Base):
    __tablename__ = "transactions"
    __table_args__ = (
        ForeignKeyConstraint(
            ["dataset_version", "company_id"],
            [
                "companies.dataset_version",
                "companies.company_id",
            ],
            name="fk_transactions_company",
        ),
        CheckConstraint(
            "value_usd IS NULL OR value_usd > 0",
            name="ck_transactions_value_usd",
        ),
    )

    dataset_version: Mapped[str] = mapped_column(
        String(64),
        primary_key=True,
    )
    transaction_id: Mapped[str] = mapped_column(
        String(64),
        primary_key=True,
    )
    company_id: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )
    transaction_type: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
    )
    announcement_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
    )
    close_date: Mapped[date | None] = mapped_column(
        Date,
    )
    value_usd: Mapped[int | None] = mapped_column(
        MONEY,
    )
    counterparty: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )


class DocumentRow(Base):
    __tablename__ = "documents"
    __table_args__ = (
        ForeignKeyConstraint(
            ["dataset_version", "company_id"],
            [
                "companies.dataset_version",
                "companies.company_id",
            ],
            name="fk_documents_company",
        ),
        CheckConstraint(
            "document_type IN "
            "('investment_committee_memo', "
            "'quarterly_management_report', "
            "'board_update', 'risk_review', "
            "'incident_report', 'supplier_review', "
            "'customer_review', 'strategy_memo')",
            name="ck_documents_type",
        ),
        CheckConstraint(
            "confidentiality IN ('internal', 'confidential', 'restricted')",
            name="ck_documents_confidentiality",
        ),
        CheckConstraint(
            "version >= 1",
            name="ck_documents_version",
        ),
        Index(
            "ix_documents_company_date",
            "dataset_version",
            "company_id",
            "document_date",
        ),
    )

    dataset_version: Mapped[str] = mapped_column(
        String(64),
        primary_key=True,
    )
    document_id: Mapped[str] = mapped_column(
        String(128),
        primary_key=True,
    )
    company_id: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )
    document_type: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )
    title: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    document_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
    )
    confidentiality: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
    )
    version: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )


class EvidenceBlockRow(Base):
    __tablename__ = "evidence_blocks"
    __table_args__ = (
        ForeignKeyConstraint(
            ["dataset_version", "document_id"],
            [
                "documents.dataset_version",
                "documents.document_id",
            ],
            name="fk_evidence_blocks_document",
        ),
        UniqueConstraint(
            "dataset_version",
            "document_id",
            "evidence_ordinal",
            name="uq_evidence_blocks_document_ordinal",
        ),
        CheckConstraint(
            "evidence_ordinal >= 0",
            name="ck_evidence_blocks_ordinal",
        ),
        CheckConstraint(
            "char_length(text) > 0",
            name="ck_evidence_blocks_text",
        ),
    )

    dataset_version: Mapped[str] = mapped_column(
        String(64),
        primary_key=True,
    )
    evidence_id: Mapped[str] = mapped_column(
        String(128),
        primary_key=True,
    )
    document_id: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
    )
    evidence_ordinal: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    heading: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    text: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )


class EvidenceSourceFactRow(Base):
    __tablename__ = "evidence_source_facts"
    __table_args__ = (
        ForeignKeyConstraint(
            ["dataset_version", "evidence_id"],
            [
                "evidence_blocks.dataset_version",
                "evidence_blocks.evidence_id",
            ],
            name="fk_evidence_source_facts_evidence",
        ),
        ForeignKeyConstraint(
            ["dataset_version", "source_fact_id"],
            [
                "canonical_facts.dataset_version",
                "canonical_facts.fact_id",
            ],
            name="fk_evidence_source_facts_fact",
        ),
        UniqueConstraint(
            "dataset_version",
            "evidence_id",
            "source_ordinal",
            name="uq_evidence_source_facts_ordinal",
        ),
        CheckConstraint(
            "source_ordinal >= 0",
            name="ck_evidence_source_facts_ordinal",
        ),
    )

    dataset_version: Mapped[str] = mapped_column(
        String(64),
        primary_key=True,
    )
    evidence_id: Mapped[str] = mapped_column(
        String(128),
        primary_key=True,
    )
    source_fact_id: Mapped[str] = mapped_column(
        String(128),
        primary_key=True,
    )
    source_ordinal: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
