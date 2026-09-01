from datetime import date

from enterprise_genai.data.document_models import (
    DocumentCorpus,
    EnterpriseDocument,
    EvidenceBlock,
)


def build_pilot_corpus() -> DocumentCorpus:
    """Build the deterministic eight-document Northstar pilot corpus."""

    return DocumentCorpus(
        dataset_version="northstar-v1",
        documents=[
            EnterpriseDocument(
                document_id="DOC-PC001-RISK-001",
                company_id="PC-001",
                document_type="risk_review",
                title="Meridian Health Systems Q2 2026 Risk Review",
                document_date=date(2026, 6, 30),
                confidentiality="confidential",
                version=1,
                evidence=[
                    EvidenceBlock(
                        evidence_id="EVID-PC001-CUSTOMER-001",
                        heading="Major account concentration",
                        text=(
                            "St. Anne Health Network represents 31 percent of "
                            "Meridian revenue. The size of this relationship "
                            "continues to create material exposure to a single "
                            "health-system customer."
                        ),
                        source_fact_ids=[
                            "RISK-001",
                            "CC-001",
                        ],
                    ),
                    EvidenceBlock(
                        evidence_id="EVID-PC001-PERFORMANCE-001",
                        heading="Current operating performance",
                        text=(
                            "Meridian generated $98 million of revenue in "
                            "2026 Q2 while net retention stood at 111 percent."
                        ),
                        source_fact_ids=[
                            "FIN-PC-001-2026Q2",
                        ],
                    ),
                ],
            ),
            EnterpriseDocument(
                document_id="DOC-PC002-SUPPLIER-001",
                company_id="PC-002",
                document_type="supplier_review",
                title="Alder Manufacturing Critical Supplier Review",
                document_date=date(2026, 6, 24),
                confidentiality="restricted",
                version=1,
                evidence=[
                    EvidenceBlock(
                        evidence_id="EVID-PC002-SUPPLIER-001",
                        heading="Titanium sourcing dependency",
                        text=(
                            "TitaniumWorks GmbH remains Alder's only qualified "
                            "source for a critical aerospace titanium input. "
                            "The supplier is located in Germany and a second "
                            "source has not yet completed qualification."
                        ),
                        source_fact_ids=[
                            "CS-003",
                            "SUP-005",
                            "RISK-002",
                            "GEO-002",
                        ],
                    ),
                    EvidenceBlock(
                        evidence_id="EVID-PC002-YIELD-001",
                        heading="Manufacturing yield",
                        text=(
                            "Production yield declined to 94.2 percent in "
                            "2026 Q2, extending the deterioration observed "
                            "during the prior quarters."
                        ),
                        source_fact_ids=[
                            "OP-PC-002-2026Q2-YIELD",
                        ],
                    ),
                ],
            ),
            EnterpriseDocument(
                document_id="DOC-PC003-BOARD-2026Q2",
                company_id="PC-003",
                document_type="board_update",
                title="BluePeak Logistics Q2 2026 Board Update",
                document_date=date(2026, 7, 14),
                confidentiality="confidential",
                version=1,
                evidence=[
                    EvidenceBlock(
                        evidence_id="EVID-PC003-DEMAND-001",
                        heading="Canadian corridor demand",
                        text=(
                            "Several large accounts have trimmed shipment "
                            "expectations as activity softened across selected "
                            "Canadian freight corridors. Management is watching "
                            "the change in customer planning assumptions."
                        ),
                        source_fact_ids=[
                            "RISK-003",
                            "GEO-003",
                        ],
                    ),
                    EvidenceBlock(
                        evidence_id="EVID-PC003-VOLUME-001",
                        heading="Freight activity",
                        text=(
                            "Platform freight volume measured 12.7 million "
                            "shipments in 2026 Q2 compared with 13.3 million "
                            "shipments in 2025 Q2."
                        ),
                        source_fact_ids=[
                            "OP-PC-003-2025Q2-FREIGHT",
                            "OP-PC-003-2026Q2-FREIGHT",
                        ],
                    ),
                ],
            ),
            EnterpriseDocument(
                document_id="DOC-PC004-BOARD-2026Q2",
                company_id="PC-004",
                document_type="board_update",
                title="HelioGrid Energy Q2 2026 Board Update",
                document_date=date(2026, 7, 9),
                confidentiality="confidential",
                version=1,
                evidence=[
                    EvidenceBlock(
                        evidence_id="EVID-PC004-PERMIT-001",
                        heading="Development schedule",
                        text=(
                            "Several western distributed-storage projects are "
                            "running behind their original schedules because "
                            "local approvals are taking longer than planned."
                        ),
                        source_fact_ids=[
                            "RISK-004",
                        ],
                    ),
                    EvidenceBlock(
                        evidence_id="EVID-PC004-GROWTH-001",
                        heading="Scale expansion",
                        text=(
                            "Quarterly revenue increased from $68 million in "
                            "2025 Q2 to $92 million in 2026 Q2. Installed "
                            "capacity reached 770 megawatts by quarter end."
                        ),
                        source_fact_ids=[
                            "FIN-PC-004-2025Q2",
                            "FIN-PC-004-2026Q2",
                            "OP-PC-004-2026Q2-CAPACITY",
                        ],
                    ),
                ],
            ),
            EnterpriseDocument(
                document_id="DOC-PC005-CUSTOMER-001",
                company_id="PC-005",
                document_type="customer_review",
                title="Vantage Retail Analytics Customer Health Review",
                document_date=date(2026, 7, 2),
                confidentiality="confidential",
                version=1,
                evidence=[
                    EvidenceBlock(
                        evidence_id="EVID-PC005-COHORT-001",
                        heading="Recent customer cohorts",
                        text=(
                            "New-logo activity remains healthy, but several "
                            "recently signed accounts have failed to settle into "
                            "normal renewal behavior. Revenue continued to rise "
                            "even as the quality of newer customer cohorts "
                            "weakened."
                        ),
                        source_fact_ids=[
                            "RISK-005",
                            "FIN-PC-005-2025Q2",
                            "FIN-PC-005-2026Q2",
                        ],
                    ),
                    EvidenceBlock(
                        evidence_id="EVID-PC005-CROWN-001",
                        heading="Crown Street relationship",
                        text=(
                            "Crown Street Retail contributes 27 percent of "
                            "company revenue and is currently classified as an "
                            "at-risk relationship."
                        ),
                        source_fact_ids=[
                            "CC-008",
                        ],
                    ),
                ],
            ),
            EnterpriseDocument(
                document_id="DOC-PC006-INCIDENT-001",
                company_id="PC-006",
                document_type="incident_report",
                title="Orbis Cybersecurity ORBIS-IDX-7 Incident Report",
                document_date=date(2026, 3, 5),
                confidentiality="restricted",
                version=1,
                evidence=[
                    EvidenceBlock(
                        evidence_id="EVID-PC006-INCIDENT-001",
                        heading="ORBIS-IDX-7 authentication failure",
                        text=(
                            "The ORBIS-IDX-7 service experienced an "
                            "authentication defect that caused intermittent "
                            "identity-validation failures for a subset of "
                            "enterprise tenants."
                        ),
                        source_fact_ids=[
                            "RISK-006",
                        ],
                    ),
                    EvidenceBlock(
                        evidence_id="EVID-PC006-RECOVERY-001",
                        heading="Service recovery",
                        text=(
                            "Platform uptime fell to 99.72 percent in 2026 Q1 "
                            "and recovered to 99.97 percent in 2026 Q2 after "
                            "remediation."
                        ),
                        source_fact_ids=[
                            "OP-PC-006-2026Q1-UPTIME",
                            "OP-PC-006-2026Q2-UPTIME",
                        ],
                    ),
                ],
            ),
            EnterpriseDocument(
                document_id="DOC-PC007-RISK-001",
                company_id="PC-007",
                document_type="risk_review",
                title="Cedar Financial Technologies Q2 2026 Risk Review",
                document_date=date(2026, 6, 28),
                confidentiality="confidential",
                version=1,
                evidence=[
                    EvidenceBlock(
                        evidence_id="EVID-PC007-CUSTOMER-001",
                        heading="Harbor Regional Bank exposure",
                        text=(
                            "Harbor Regional Bank represents 26 percent of "
                            "Cedar revenue, leaving the company materially "
                            "exposed to a single regional-bank customer."
                        ),
                        source_fact_ids=[
                            "RISK-007",
                            "CC-011",
                        ],
                    ),
                    EvidenceBlock(
                        evidence_id="EVID-PC007-PERFORMANCE-001",
                        heading="Quarterly performance",
                        text=(
                            "Cedar generated $84 million of revenue in "
                            "2026 Q2 with net retention of 106 percent."
                        ),
                        source_fact_ids=[
                            "FIN-PC-007-2026Q2",
                        ],
                    ),
                ],
            ),
            EnterpriseDocument(
                document_id="DOC-PC008-SUPPLIER-001",
                company_id="PC-008",
                document_type="supplier_review",
                title="NovaBio Instruments Critical Supplier Review",
                document_date=date(2026, 6, 21),
                confidentiality="restricted",
                version=1,
                evidence=[
                    EvidenceBlock(
                        evidence_id="EVID-PC008-SUPPLIER-001",
                        heading="Precision motion dependency",
                        text=(
                            "NovaBio remains dependent on Helix Motion GmbH "
                            "for a precision motion assembly used in its "
                            "automation platform. The German supplier is the "
                            "only currently qualified source for the assembly."
                        ),
                        source_fact_ids=[
                            "RISK-008",
                            "CS-011",
                            "SUP-011",
                            "GEO-008",
                        ],
                    ),
                    EvidenceBlock(
                        evidence_id="EVID-PC008-SHIPMENTS-001",
                        heading="Instrument shipments",
                        text=("Instrument shipments reached 1,175 units during 2026 Q2."),
                        source_fact_ids=[
                            "OP-PC-008-2026Q2-SHIPMENTS",
                        ],
                    ),
                ],
            ),
        ],
    )
