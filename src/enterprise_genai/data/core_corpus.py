from dataclasses import dataclass
from datetime import date

from enterprise_genai.data.document_models import (
    DocumentCorpus,
    EnterpriseDocument,
    EvidenceBlock,
)
from enterprise_genai.data.models import (
    EnterpriseUniverse,
    FinancialMetric,
    OperationalMetric,
)
from enterprise_genai.data.universe import build_universe

CURRENT_PERIOD = "2026Q2"
PRIOR_PERIOD = "2025Q2"


@dataclass(frozen=True)
class CompanyCorpusProfile:
    company_id: str
    ic_date: date

    thesis_text: str
    thesis_sources: tuple[str, ...]

    diligence_text: str
    diligence_sources: tuple[str, ...]

    semantic_signal_text: str
    semantic_signal_sources: tuple[str, ...]

    board_priority_text: str
    board_priority_sources: tuple[str, ...]

    risk_primary_text: str
    risk_primary_sources: tuple[str, ...]

    risk_context_text: str
    risk_context_sources: tuple[str, ...]


PROFILES = (
    CompanyCorpusProfile(
        company_id="PC-001",
        ic_date=date(2023, 2, 1),
        thesis_text=(
            "Meridian provides hospital workflow and clinical-operations software "
            "to health systems. The underwriting thesis centers on durable demand "
            "for software that coordinates complex hospital operations."
        ),
        thesis_sources=("PC-001", "FUND-001"),
        diligence_text=(
            "Commercial diligence identified St. Anne Health Network and Atlantic "
            "University Hospitals as established customer relationships, with "
            "St. Anne representing the larger account."
        ),
        diligence_sources=("CC-001", "CC-002", "CUST-001", "CUST-002"),
        semantic_signal_text=(
            "Revenue continues to expand, but reliance on one health-system account "
            "remains a material commercial exposure."
        ),
        semantic_signal_sources=("RISK-001", "FIN-PC-001-2026Q2"),
        board_priority_text=(
            "The company's strongest operating trend is continued growth, while "
            "single-account exposure remains its clearest commercial vulnerability."
        ),
        board_priority_sources=("RISK-001", "FIN-PC-001-2026Q2"),
        risk_primary_text=(
            "St. Anne Health Network represents 31 percent of Meridian revenue, "
            "creating material customer concentration exposure."
        ),
        risk_primary_sources=("RISK-001", "CC-001"),
        risk_context_text=(
            "Atlantic University Hospitals represents an additional 14 percent "
            "of revenue, making the two named health-system relationships important "
            "to the company's commercial profile."
        ),
        risk_context_sources=("CC-002",),
    ),
    CompanyCorpusProfile(
        company_id="PC-002",
        ic_date=date(2022, 10, 20),
        thesis_text=(
            "Alder manufactures precision industrial components with meaningful "
            "exposure to aerospace demand. The investment thesis depends on durable "
            "customer relationships and specialized production capability."
        ),
        thesis_sources=("PC-002", "FUND-001"),
        diligence_text=(
            "Skyward Aerospace and Kestrel Industrial Group were established "
            "customers during underwriting, giving Alder exposure to both aerospace "
            "and broader industrial end markets."
        ),
        diligence_sources=("CC-003", "CC-004", "CUST-003", "CUST-004"),
        semantic_signal_text=(
            "Manufacturing performance has weakened while a key aerospace material "
            "still lacks a qualified alternative source."
        ),
        semantic_signal_sources=(
            "RISK-002",
            "OP-PC-002-2026Q2-YIELD",
        ),
        board_priority_text=(
            "Two operating concerns are moving in the wrong direction at the same "
            "time: factory yield has deteriorated and a critical input remains "
            "dependent on one supplier."
        ),
        board_priority_sources=(
            "RISK-002",
            "OP-PC-002-2025Q2-YIELD",
            "OP-PC-002-2026Q2-YIELD",
        ),
        risk_primary_text=(
            "TitaniumWorks GmbH is Alder's only qualified source for a critical "
            "aerospace titanium input. The German supplier accounts for 28 percent "
            "of supplier exposure represented by the relationship."
        ),
        risk_primary_sources=("RISK-002", "CS-003", "SUP-005", "GEO-002"),
        risk_context_text=(
            "Alder also sources semiconductor components from SecureChip "
            "Technologies, but that relationship is classified as medium "
            "criticality rather than critical."
        ),
        risk_context_sources=("CS-014", "SUP-002"),
    ),
    CompanyCorpusProfile(
        company_id="PC-003",
        ic_date=date(2023, 5, 1),
        thesis_text=(
            "BluePeak provides freight-management and routing software for logistics "
            "customers. The thesis combines workflow software adoption with growing "
            "complexity in cross-border freight operations."
        ),
        thesis_sources=("PC-003", "FUND-001"),
        diligence_text=(
            "MapleMart Canada and TransContinental Freight were established Canadian "
            "customer relationships before Northstar's investment."
        ),
        diligence_sources=("CC-005", "CC-006", "CUST-005", "CUST-006"),
        semantic_signal_text=(
            "Several customers have reduced shipment expectations as activity "
            "softened across selected Canadian freight corridors."
        ),
        semantic_signal_sources=("RISK-003", "GEO-003"),
        board_priority_text=(
            "The main operating concern is a loss of freight momentum in Canada "
            "rather than a broad contraction in the customer base."
        ),
        board_priority_sources=(
            "RISK-003",
            "GEO-003",
            "OP-PC-003-2026Q2-FREIGHT",
        ),
        risk_primary_text=(
            "Customer shipment forecasts have weakened in selected Canadian "
            "corridors, creating demand sensitivity for BluePeak."
        ),
        risk_primary_sources=("RISK-003", "GEO-003"),
        risk_context_text=(
            "Canada represents 36 percent of BluePeak revenue exposure, while "
            "MapleMart Canada and TransContinental Freight are two named customer "
            "relationships in that market."
        ),
        risk_context_sources=("GEO-003", "CC-005", "CC-006"),
    ),
    CompanyCorpusProfile(
        company_id="PC-004",
        ic_date=date(2022, 8, 29),
        thesis_text=(
            "HelioGrid develops distributed solar and battery infrastructure. "
            "The underwriting thesis is based on continued deployment of distributed "
            "energy assets and expansion of installed capacity."
        ),
        thesis_sources=("PC-004", "FUND-001"),
        diligence_text=(
            "Northbridge Utilities was an established customer relationship before "
            "Northstar's investment and provided evidence of demand from utility "
            "counterparties."
        ),
        diligence_sources=("CC-007", "CUST-007"),
        semantic_signal_text=(
            "Growth remains strong, but several western storage projects are "
            "progressing more slowly because local approvals are taking longer "
            "than planned."
        ),
        semantic_signal_sources=(
            "RISK-004",
            "FIN-PC-004-2026Q2",
        ),
        board_priority_text=(
            "Rapid scale expansion and permitting friction are occurring "
            "simultaneously: installed capacity is rising while some projects "
            "remain behind their original schedules."
        ),
        board_priority_sources=(
            "RISK-004",
            "OP-PC-004-2026Q2-CAPACITY",
        ),
        risk_primary_text=(
            "Permitting delays are affecting the schedule of several distributed "
            "storage projects in western states."
        ),
        risk_primary_sources=("RISK-004",),
        risk_context_text=(
            "HelioGrid depends on Pacific Battery Cells for battery cells and "
            "SolarCore Modules for solar modules, creating additional supply-chain "
            "exposures around its deployment program."
        ),
        risk_context_sources=("CS-005", "SUP-004", "CS-006", "SUP-007"),
    ),
    CompanyCorpusProfile(
        company_id="PC-005",
        ic_date=date(2023, 7, 20),
        thesis_text=(
            "Vantage provides demand-forecasting and merchandising analytics for "
            "large retailers. The investment thesis is based on increasing adoption "
            "of data-driven merchandising workflows."
        ),
        thesis_sources=("PC-005", "FUND-001"),
        diligence_text=(
            "Crown Street Retail and Hartwell Department Stores were established "
            "customers before Northstar's investment and represented meaningful "
            "enterprise-retail relationships."
        ),
        diligence_sources=("CC-008", "CC-009", "CUST-008", "CUST-009"),
        semantic_signal_text=(
            "New-logo activity remains healthy, but newer customer cohorts are "
            "taking longer to settle into normal renewal behavior."
        ),
        semantic_signal_sources=(
            "RISK-005",
            "FIN-PC-005-2025Q2",
            "FIN-PC-005-2026Q2",
        ),
        board_priority_text=(
            "Top-line expansion remains strong even though the quality of newer "
            "customer cohorts has weakened."
        ),
        board_priority_sources=(
            "RISK-005",
            "FIN-PC-005-2025Q2",
            "FIN-PC-005-2026Q2",
        ),
        risk_primary_text=(
            "Vantage's net retention declined from 112 percent in 2025 Q2 to "
            "97 percent in 2026 Q2 despite continued revenue growth."
        ),
        risk_primary_sources=(
            "RISK-005",
            "FIN-PC-005-2025Q2",
            "FIN-PC-005-2026Q2",
        ),
        risk_context_text=(
            "Crown Street Retail represents 27 percent of company revenue and is "
            "currently classified as an at-risk customer relationship."
        ),
        risk_context_sources=("CC-008",),
    ),
    CompanyCorpusProfile(
        company_id="PC-006",
        ic_date=date(2022, 11, 30),
        thesis_text=(
            "Orbis provides enterprise identity and threat-detection software. "
            "The investment thesis is based on durable cybersecurity demand and "
            "expansion of recurring enterprise deployments."
        ),
        thesis_sources=("PC-006", "FUND-001"),
        diligence_text=(
            "Rheinwerk AG was an established enterprise customer before Northstar's "
            "investment, providing direct exposure to the German market."
        ),
        diligence_sources=("CC-010", "CUST-010", "GEO-006"),
        semantic_signal_text=(
            "Authentication reliability deteriorated during the first quarter "
            "before service performance recovered during Q2."
        ),
        semantic_signal_sources=(
            "RISK-006",
            "OP-PC-006-2026Q1-UPTIME",
            "OP-PC-006-2026Q2-UPTIME",
        ),
        board_priority_text=(
            "The authentication reliability problem has been remediated, and "
            "service availability recovered materially in the following quarter."
        ),
        board_priority_sources=(
            "RISK-006",
            "OP-PC-006-2026Q1-UPTIME",
            "OP-PC-006-2026Q2-UPTIME",
        ),
        risk_primary_text=(
            "The ORBIS-IDX-7 service experienced an authentication defect that "
            "caused intermittent identity-validation failures for a subset of "
            "enterprise tenants."
        ),
        risk_primary_sources=("RISK-006",),
        risk_context_text=(
            "Germany represents 28 percent of Orbis revenue exposure, and Rheinwerk "
            "AG is a named German customer. This is a commercial exposure rather "
            "than a critical-supplier dependency."
        ),
        risk_context_sources=("GEO-006", "CC-010", "CUST-010"),
    ),
    CompanyCorpusProfile(
        company_id="PC-007",
        ic_date=date(2023, 3, 10),
        thesis_text=(
            "Cedar provides compliance and workflow infrastructure to regional "
            "banks. The underwriting thesis is based on persistent regulatory "
            "complexity and modernization of bank operating workflows."
        ),
        thesis_sources=("PC-007", "FUND-001"),
        diligence_text=(
            "Harbor Regional Bank and Pioneer Community Bank were established "
            "customers before Northstar's investment."
        ),
        diligence_sources=("CC-011", "CC-012", "CUST-011", "CUST-012"),
        semantic_signal_text=(
            "The business continues to grow, but a single regional-bank account "
            "still represents a substantial share of revenue."
        ),
        semantic_signal_sources=("RISK-007", "FIN-PC-007-2026Q2"),
        board_priority_text=(
            "Customer concentration remains the principal commercial risk even "
            "as transaction activity and quarterly revenue continue to increase."
        ),
        board_priority_sources=(
            "RISK-007",
            "FIN-PC-007-2026Q2",
            "OP-PC-007-2026Q2-VOLUME",
        ),
        risk_primary_text=(
            "Harbor Regional Bank represents 26 percent of Cedar revenue, leaving "
            "the company materially exposed to one regional-bank relationship."
        ),
        risk_primary_sources=("RISK-007", "CC-011"),
        risk_context_text=(
            "Pioneer Community Bank represents another 13 percent of revenue, "
            "although the Harbor relationship is the larger concentration."
        ),
        risk_context_sources=("CC-012", "CC-011"),
    ),
    CompanyCorpusProfile(
        company_id="PC-008",
        ic_date=date(2022, 10, 10),
        thesis_text=(
            "NovaBio develops laboratory automation and diagnostic instrumentation. "
            "The investment thesis combines automation demand with recurring needs "
            "for high-precision life-sciences equipment."
        ),
        thesis_sources=("PC-008", "FUND-001"),
        diligence_text=(
            "Alpine Diagnostics and Genomicore Laboratories were established "
            "life-sciences customers before Northstar's investment."
        ),
        diligence_sources=("CC-013", "CC-014", "CUST-013", "CUST-014"),
        semantic_signal_text=(
            "Shipment growth remains healthy, but a precision-motion assembly still "
            "depends on a single qualified source."
        ),
        semantic_signal_sources=(
            "RISK-008",
            "OP-PC-008-2026Q2-SHIPMENTS",
        ),
        board_priority_text=(
            "Commercial activity continues to expand while an unresolved "
            "single-source dependency remains embedded in the automation platform."
        ),
        board_priority_sources=(
            "RISK-008",
            "OP-PC-008-2026Q2-SHIPMENTS",
        ),
        risk_primary_text=(
            "Helix Motion GmbH is the only currently qualified supplier for a "
            "precision motion assembly used in NovaBio's automation platform. "
            "The supplier is located in Germany."
        ),
        risk_primary_sources=("RISK-008", "CS-011", "SUP-011", "GEO-008"),
        risk_context_text=(
            "NovaBio also sources laboratory optics from Alpine Optics AG in "
            "Switzerland, but that relationship is classified as high criticality "
            "rather than single-source critical."
        ),
        risk_context_sources=("CS-012", "SUP-012", "GEO-009"),
    ),
)


def _company_name(
    universe: EnterpriseUniverse,
    company_id: str,
) -> str:
    return next(company.name for company in universe.companies if company.company_id == company_id)


def _financial_metric(
    universe: EnterpriseUniverse,
    company_id: str,
    period: str,
) -> FinancialMetric:
    return next(
        metric
        for metric in universe.financial_metrics
        if metric.company_id == company_id and metric.period == period
    )


def _operational_metric(
    universe: EnterpriseUniverse,
    company_id: str,
    period: str,
) -> OperationalMetric:
    return next(
        metric
        for metric in universe.operational_metrics
        if metric.company_id == company_id and metric.period == period
    )


def _financial_text(
    universe: EnterpriseUniverse,
    company_id: str,
) -> str:
    prior = _financial_metric(
        universe,
        company_id,
        PRIOR_PERIOD,
    )
    current = _financial_metric(
        universe,
        company_id,
        CURRENT_PERIOD,
    )

    text = (
        f"Revenue increased from ${prior.revenue_usd / 1_000_000:.0f} million "
        f"in {PRIOR_PERIOD} to ${current.revenue_usd / 1_000_000:.0f} million "
        f"in {CURRENT_PERIOD}. EBITDA in the current quarter was "
        f"${current.ebitda_usd / 1_000_000:.0f} million."
    )

    if current.net_retention_pct is not None:
        text += f" Net retention in {CURRENT_PERIOD} was {current.net_retention_pct:.0f} percent."

    return text


def _operational_text(
    universe: EnterpriseUniverse,
    company_id: str,
) -> str:
    prior = _operational_metric(
        universe,
        company_id,
        PRIOR_PERIOD,
    )
    current = _operational_metric(
        universe,
        company_id,
        CURRENT_PERIOD,
    )

    metric_label = current.metric_name.replace("_", " ")

    return (
        f"The operating indicator '{metric_label}' moved from "
        f"{prior.metric_value:g} {prior.unit} in {PRIOR_PERIOD} to "
        f"{current.metric_value:g} {current.unit} in {CURRENT_PERIOD}."
    )


def _board_scorecard_text(
    universe: EnterpriseUniverse,
    company_id: str,
) -> str:
    current_financial = _financial_metric(
        universe,
        company_id,
        CURRENT_PERIOD,
    )
    current_operational = _operational_metric(
        universe,
        company_id,
        CURRENT_PERIOD,
    )

    metric_label = current_operational.metric_name.replace("_", " ")

    return (
        f"The Q2 scorecard records ${current_financial.revenue_usd / 1_000_000:.0f} "
        f"million of revenue and {current_operational.metric_value:g} "
        f"{current_operational.unit} for {metric_label}."
    )


def _risk_indicator_text(
    universe: EnterpriseUniverse,
    company_id: str,
) -> str:
    prior = _operational_metric(
        universe,
        company_id,
        PRIOR_PERIOD,
    )
    current = _operational_metric(
        universe,
        company_id,
        CURRENT_PERIOD,
    )

    metric_label = current.metric_name.replace("_", " ")

    return (
        f"For monitoring context, {metric_label} was "
        f"{prior.metric_value:g} {prior.unit} in {PRIOR_PERIOD} and "
        f"{current.metric_value:g} {current.unit} in {CURRENT_PERIOD}."
    )


def _core_documents_for_company(
    universe: EnterpriseUniverse,
    profile: CompanyCorpusProfile,
) -> list[EnterpriseDocument]:
    company_id = profile.company_id
    company_token = company_id.replace("-", "")
    company_name = _company_name(universe, company_id)

    prior_fin_id = f"FIN-{company_id}-{PRIOR_PERIOD}"
    current_fin_id = f"FIN-{company_id}-{CURRENT_PERIOD}"

    prior_operational = _operational_metric(
        universe,
        company_id,
        PRIOR_PERIOD,
    )
    current_operational = _operational_metric(
        universe,
        company_id,
        CURRENT_PERIOD,
    )

    return [
        EnterpriseDocument(
            document_id=f"DOC-CORE-{company_token}-IC-001",
            company_id=company_id,
            document_type="investment_committee_memo",
            title=f"{company_name} Investment Committee Memorandum",
            document_date=profile.ic_date,
            confidentiality="restricted",
            version=1,
            evidence=[
                EvidenceBlock(
                    evidence_id=f"EVID-CORE-{company_token}-IC-THESIS",
                    heading="Investment thesis",
                    text=profile.thesis_text,
                    source_fact_ids=list(profile.thesis_sources),
                ),
                EvidenceBlock(
                    evidence_id=f"EVID-CORE-{company_token}-IC-DILIGENCE",
                    heading="Commercial diligence",
                    text=profile.diligence_text,
                    source_fact_ids=list(profile.diligence_sources),
                ),
            ],
        ),
        EnterpriseDocument(
            document_id=f"DOC-CORE-{company_token}-QMR-2026Q2",
            company_id=company_id,
            document_type="quarterly_management_report",
            title=f"{company_name} Q2 2026 Management Report",
            document_date=date(2026, 7, 10),
            confidentiality="confidential",
            version=1,
            evidence=[
                EvidenceBlock(
                    evidence_id=f"EVID-CORE-{company_token}-QMR-FINANCIAL",
                    heading="Financial performance",
                    text=_financial_text(
                        universe,
                        company_id,
                    ),
                    source_fact_ids=[
                        prior_fin_id,
                        current_fin_id,
                    ],
                ),
                EvidenceBlock(
                    evidence_id=f"EVID-CORE-{company_token}-QMR-OPERATING",
                    heading="Operating indicator",
                    text=_operational_text(
                        universe,
                        company_id,
                    ),
                    source_fact_ids=[
                        prior_operational.metric_id,
                        current_operational.metric_id,
                    ],
                ),
                EvidenceBlock(
                    evidence_id=f"EVID-CORE-{company_token}-QMR-SIGNAL",
                    heading="Management signal",
                    text=profile.semantic_signal_text,
                    source_fact_ids=list(profile.semantic_signal_sources),
                ),
            ],
        ),
        EnterpriseDocument(
            document_id=f"DOC-CORE-{company_token}-BOARD-2026Q2",
            company_id=company_id,
            document_type="board_update",
            title=f"{company_name} Q2 2026 Board Update",
            document_date=date(2026, 7, 20),
            confidentiality="confidential",
            version=1,
            evidence=[
                EvidenceBlock(
                    evidence_id=f"EVID-CORE-{company_token}-BOARD-PRIORITY",
                    heading="Primary board issue",
                    text=profile.board_priority_text,
                    source_fact_ids=list(profile.board_priority_sources),
                ),
                EvidenceBlock(
                    evidence_id=f"EVID-CORE-{company_token}-BOARD-SCORECARD",
                    heading="Quarter-end scorecard",
                    text=_board_scorecard_text(
                        universe,
                        company_id,
                    ),
                    source_fact_ids=[
                        current_fin_id,
                        current_operational.metric_id,
                    ],
                ),
            ],
        ),
        EnterpriseDocument(
            document_id=f"DOC-CORE-{company_token}-RISK-2026Q2",
            company_id=company_id,
            document_type="risk_review",
            title=f"{company_name} Q2 2026 Risk Review",
            document_date=date(2026, 7, 31),
            confidentiality="restricted",
            version=1,
            evidence=[
                EvidenceBlock(
                    evidence_id=f"EVID-CORE-{company_token}-RISK-PRIMARY",
                    heading="Primary risk",
                    text=profile.risk_primary_text,
                    source_fact_ids=list(profile.risk_primary_sources),
                ),
                EvidenceBlock(
                    evidence_id=f"EVID-CORE-{company_token}-RISK-CONTEXT",
                    heading="Risk context",
                    text=profile.risk_context_text,
                    source_fact_ids=list(profile.risk_context_sources),
                ),
                EvidenceBlock(
                    evidence_id=f"EVID-CORE-{company_token}-RISK-INDICATOR",
                    heading="Operating indicator",
                    text=_risk_indicator_text(
                        universe,
                        company_id,
                    ),
                    source_fact_ids=[
                        prior_operational.metric_id,
                        current_operational.metric_id,
                    ],
                ),
            ],
        ),
    ]


def build_core_corpus() -> DocumentCorpus:
    """Build the deterministic 32-document Northstar core corpus."""

    universe = build_universe()

    documents = [
        document
        for profile in PROFILES
        for document in _core_documents_for_company(
            universe,
            profile,
        )
    ]

    return DocumentCorpus(
        dataset_version="northstar-v1",
        documents=documents,
    )
