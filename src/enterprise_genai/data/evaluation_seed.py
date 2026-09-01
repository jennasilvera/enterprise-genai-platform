from enterprise_genai.data.evaluation_models import (
    EvaluationCase,
    EvaluationSet,
    ExpectedAnswer,
    RelevanceJudgment,
)


def _judgment(
    document_id: str,
    evidence_id: str,
    grade: int,
    rationale: str,
) -> RelevanceJudgment:
    return RelevanceJudgment(
        document_id=document_id,
        evidence_id=evidence_id,
        relevance_grade=grade,
        rationale=rationale,
    )


def build_seed_evaluation() -> EvaluationSet:
    """Build the hand-authored 24-case Northstar evaluation seed."""

    return EvaluationSet(
        dataset_version="northstar-v1",
        evaluation_version="northstar-eval-v1-seed",
        cases=[
            EvaluationCase(
                query_id="Q-0001",
                question="What defect affected ORBIS-IDX-7?",
                query_type="lexical",
                split="development",
                difficulty="easy",
                answerable=True,
                expected_answer=ExpectedAnswer(
                    answer_type="text",
                    value=(
                        "An authentication defect caused intermittent "
                        "identity-validation failures for a subset of "
                        "enterprise tenants."
                    ),
                ),
                answer_source_fact_ids=["RISK-006"],
                required_tools=["lexical_retrieval"],
                relevance_judgments=[
                    _judgment(
                        "DOC-CORE-PC006-RISK-2026Q2",
                        "EVID-CORE-PC006-RISK-PRIMARY",
                        3,
                        "Explicitly names ORBIS-IDX-7 and the defect.",
                    ),
                    _judgment(
                        "DOC-CORE-PC006-QMR-2026Q2",
                        "EVID-CORE-PC006-QMR-SIGNAL",
                        1,
                        "Describes the reliability issue without the identifier.",
                    ),
                ],
            ),
            EvaluationCase(
                query_id="Q-0002",
                question=("Which critical titanium supplier is Alder's only qualified source?"),
                query_type="lexical",
                split="development",
                difficulty="easy",
                answerable=True,
                expected_answer=ExpectedAnswer(
                    answer_type="entity",
                    value="TitaniumWorks GmbH",
                ),
                answer_source_fact_ids=[
                    "CS-003",
                    "SUP-005",
                    "RISK-002",
                ],
                required_tools=["lexical_retrieval"],
                relevance_judgments=[
                    _judgment(
                        "DOC-CORE-PC002-RISK-2026Q2",
                        "EVID-CORE-PC002-RISK-PRIMARY",
                        3,
                        "Explicitly identifies TitaniumWorks GmbH.",
                    )
                ],
            ),
            EvaluationCase(
                query_id="Q-0003",
                question=(
                    "Which portfolio company relies on Helix Motion "
                    "GmbH as its only qualified source?"
                ),
                query_type="lexical",
                split="test",
                difficulty="easy",
                answerable=True,
                expected_answer=ExpectedAnswer(
                    answer_type="entity",
                    value="NovaBio Instruments",
                ),
                answer_source_fact_ids=[
                    "RISK-008",
                    "CS-011",
                    "SUP-011",
                ],
                required_tools=["lexical_retrieval"],
                relevance_judgments=[
                    _judgment(
                        "DOC-CORE-PC008-RISK-2026Q2",
                        "EVID-CORE-PC008-RISK-PRIMARY",
                        3,
                        "Explicitly identifies Helix Motion GmbH.",
                    )
                ],
            ),
            EvaluationCase(
                query_id="Q-0004",
                question=(
                    "Which portfolio company is still growing even "
                    "though newer customers are failing to settle into "
                    "normal renewal behavior?"
                ),
                query_type="semantic",
                split="development",
                difficulty="medium",
                answerable=True,
                expected_answer=ExpectedAnswer(
                    answer_type="entity",
                    value="Vantage Retail Analytics",
                ),
                answer_source_fact_ids=[
                    "RISK-005",
                    "FIN-PC-005-2025Q2",
                    "FIN-PC-005-2026Q2",
                ],
                required_tools=["dense_retrieval"],
                relevance_judgments=[
                    _judgment(
                        "DOC-CORE-PC005-QMR-2026Q2",
                        "EVID-CORE-PC005-QMR-SIGNAL",
                        3,
                        "Direct semantic description of weakening cohorts.",
                    ),
                    _judgment(
                        "DOC-CORE-PC005-BOARD-2026Q2",
                        "EVID-CORE-PC005-BOARD-PRIORITY",
                        2,
                        "Supports the cohort-quality deterioration.",
                    ),
                ],
            ),
            EvaluationCase(
                query_id="Q-0005",
                question=(
                    "Which company has projects progressing more "
                    "slowly because local approvals are taking longer?"
                ),
                query_type="semantic",
                split="test",
                difficulty="medium",
                answerable=True,
                expected_answer=ExpectedAnswer(
                    answer_type="entity",
                    value="HelioGrid Energy",
                ),
                answer_source_fact_ids=["RISK-004"],
                required_tools=["dense_retrieval"],
                relevance_judgments=[
                    _judgment(
                        "DOC-CORE-PC004-QMR-2026Q2",
                        "EVID-CORE-PC004-QMR-SIGNAL",
                        3,
                        "Paraphrases the permitting-delay problem.",
                    ),
                    _judgment(
                        "DOC-CORE-PC004-RISK-2026Q2",
                        "EVID-CORE-PC004-RISK-PRIMARY",
                        2,
                        "States the permitting risk explicitly.",
                    ),
                ],
            ),
            EvaluationCase(
                query_id="Q-0006",
                question=(
                    "Which portfolio company is seeing freight "
                    "momentum weaken in Canadian corridors?"
                ),
                query_type="semantic",
                split="development",
                difficulty="medium",
                answerable=True,
                expected_answer=ExpectedAnswer(
                    answer_type="entity",
                    value="BluePeak Logistics",
                ),
                answer_source_fact_ids=[
                    "RISK-003",
                    "GEO-003",
                    "OP-PC-003-2026Q2-FREIGHT",
                ],
                required_tools=["dense_retrieval"],
                relevance_judgments=[
                    _judgment(
                        "DOC-CORE-PC003-BOARD-2026Q2",
                        "EVID-CORE-PC003-BOARD-PRIORITY",
                        3,
                        "Directly describes weaker Canadian freight momentum.",
                    ),
                    _judgment(
                        "DOC-CORE-PC003-QMR-2026Q2",
                        "EVID-CORE-PC003-QMR-SIGNAL",
                        2,
                        "Describes customers reducing shipment expectations.",
                    ),
                ],
            ),
            EvaluationCase(
                query_id="Q-0007",
                question=(
                    "What happened to ORBIS-IDX-7, and how did "
                    "service reliability change afterward?"
                ),
                query_type="hybrid",
                split="test",
                difficulty="medium",
                answerable=True,
                expected_answer=ExpectedAnswer(
                    answer_type="text",
                    value=(
                        "ORBIS-IDX-7 experienced an authentication defect "
                        "that caused intermittent identity-validation "
                        "failures; reliability deteriorated in 2026 Q1 "
                        "and recovered during 2026 Q2."
                    ),
                ),
                answer_source_fact_ids=[
                    "RISK-006",
                    "OP-PC-006-2026Q1-UPTIME",
                    "OP-PC-006-2026Q2-UPTIME",
                ],
                required_tools=["hybrid_retrieval"],
                relevance_judgments=[
                    _judgment(
                        "DOC-CORE-PC006-RISK-2026Q2",
                        "EVID-CORE-PC006-RISK-PRIMARY",
                        3,
                        "Canonical identifier-specific incident evidence.",
                    ),
                    _judgment(
                        "DOC-CORE-PC006-QMR-2026Q2",
                        "EVID-CORE-PC006-QMR-SIGNAL",
                        3,
                        "Canonical evidence of deterioration and recovery.",
                    ),
                ],
            ),
            EvaluationCase(
                query_id="Q-0008",
                question=(
                    "What operational risk is associated with "
                    "TitaniumWorks GmbH, and how has Alder's "
                    "production yield changed?"
                ),
                query_type="hybrid",
                split="development",
                difficulty="hard",
                answerable=True,
                expected_answer=ExpectedAnswer(
                    answer_type="text",
                    value=(
                        "Alder has a critical single-source dependency on "
                        "TitaniumWorks GmbH, while production yield declined "
                        "from 96.8 percent in 2025 Q2 to 94.2 percent in "
                        "2026 Q2."
                    ),
                ),
                answer_source_fact_ids=[
                    "RISK-002",
                    "CS-003",
                    "SUP-005",
                    "OP-PC-002-2025Q2-YIELD",
                    "OP-PC-002-2026Q2-YIELD",
                ],
                required_tools=["hybrid_retrieval"],
                relevance_judgments=[
                    _judgment(
                        "DOC-CORE-PC002-RISK-2026Q2",
                        "EVID-CORE-PC002-RISK-PRIMARY",
                        3,
                        "Canonical supplier-risk evidence.",
                    ),
                    _judgment(
                        "DOC-CORE-PC002-QMR-2026Q2",
                        "EVID-CORE-PC002-QMR-OPERATING",
                        3,
                        "Canonical production-yield trend evidence.",
                    ),
                ],
            ),
            EvaluationCase(
                query_id="Q-0009",
                question=(
                    "What is the risk around Crown Street Retail, "
                    "and what broader customer-quality problem is "
                    "Vantage experiencing?"
                ),
                query_type="hybrid",
                split="development",
                difficulty="hard",
                answerable=True,
                expected_answer=ExpectedAnswer(
                    answer_type="text",
                    value=(
                        "Crown Street Retail represents 27 percent of "
                        "Vantage revenue and is at risk, while newer "
                        "customer cohorts are failing to settle into "
                        "normal renewal behavior."
                    ),
                ),
                answer_source_fact_ids=[
                    "CC-008",
                    "RISK-005",
                ],
                required_tools=["hybrid_retrieval"],
                relevance_judgments=[
                    _judgment(
                        "DOC-CORE-PC005-RISK-2026Q2",
                        "EVID-CORE-PC005-RISK-CONTEXT",
                        3,
                        "Canonical Crown Street relationship evidence.",
                    ),
                    _judgment(
                        "DOC-CORE-PC005-QMR-2026Q2",
                        "EVID-CORE-PC005-QMR-SIGNAL",
                        3,
                        "Canonical semantic cohort-quality evidence.",
                    ),
                ],
            ),
            EvaluationCase(
                query_id="Q-0010",
                question=(
                    "Which portfolio company had the highest "
                    "year-over-year revenue growth in 2026 Q2?"
                ),
                query_type="sql",
                split="development",
                difficulty="medium",
                answerable=True,
                expected_answer=ExpectedAnswer(
                    answer_type="entity",
                    value="HelioGrid Energy",
                ),
                answer_source_fact_ids=[
                    "FIN-PC-004-2025Q2",
                    "FIN-PC-004-2026Q2",
                ],
                required_tools=["sql"],
                relevance_judgments=[],
            ),
            EvaluationCase(
                query_id="Q-0011",
                question=("What was total portfolio revenue in 2026 Q2?"),
                query_type="sql",
                split="test",
                difficulty="medium",
                answerable=True,
                expected_answer=ExpectedAnswer(
                    answer_type="number",
                    value=735_000_000,
                    unit="USD",
                    tolerance=0,
                ),
                answer_source_fact_ids=[
                    "FIN-PC-001-2026Q2",
                    "FIN-PC-002-2026Q2",
                    "FIN-PC-003-2026Q2",
                    "FIN-PC-004-2026Q2",
                    "FIN-PC-005-2026Q2",
                    "FIN-PC-006-2026Q2",
                    "FIN-PC-007-2026Q2",
                    "FIN-PC-008-2026Q2",
                ],
                required_tools=["sql"],
                relevance_judgments=[],
            ),
            EvaluationCase(
                query_id="Q-0012",
                question=("Which company had net retention below 100 percent in 2026 Q2?"),
                query_type="sql",
                split="development",
                difficulty="easy",
                answerable=True,
                expected_answer=ExpectedAnswer(
                    answer_type="entity",
                    value="Vantage Retail Analytics",
                ),
                answer_source_fact_ids=[
                    "FIN-PC-005-2026Q2",
                ],
                required_tools=["sql"],
                relevance_judgments=[],
            ),
            EvaluationCase(
                query_id="Q-0013",
                question=("Which company had the highest EBITDA margin in 2026 Q2?"),
                query_type="sql",
                split="development",
                difficulty="medium",
                answerable=True,
                expected_answer=ExpectedAnswer(
                    answer_type="entity",
                    value="Orbis Cybersecurity",
                ),
                answer_source_fact_ids=[
                    "FIN-PC-001-2026Q2",
                    "FIN-PC-002-2026Q2",
                    "FIN-PC-003-2026Q2",
                    "FIN-PC-004-2026Q2",
                    "FIN-PC-005-2026Q2",
                    "FIN-PC-006-2026Q2",
                    "FIN-PC-007-2026Q2",
                    "FIN-PC-008-2026Q2",
                ],
                required_tools=["sql"],
                relevance_judgments=[],
            ),
            EvaluationCase(
                query_id="Q-0014",
                question=(
                    "Which portfolio companies depend on critical suppliers located in Germany?"
                ),
                query_type="graph",
                split="test",
                difficulty="medium",
                answerable=True,
                expected_answer=ExpectedAnswer(
                    answer_type="entities",
                    value=[
                        "Alder Manufacturing",
                        "NovaBio Instruments",
                    ],
                ),
                answer_source_fact_ids=[
                    "CS-003",
                    "SUP-005",
                    "GEO-002",
                    "RISK-002",
                    "CS-011",
                    "SUP-011",
                    "GEO-008",
                    "RISK-008",
                ],
                required_tools=["graph"],
                relevance_judgments=[],
            ),
            EvaluationCase(
                query_id="Q-0015",
                question=("Which portfolio company serves a customer based in Germany?"),
                query_type="graph",
                split="development",
                difficulty="easy",
                answerable=True,
                expected_answer=ExpectedAnswer(
                    answer_type="entity",
                    value="Orbis Cybersecurity",
                ),
                answer_source_fact_ids=[
                    "CC-010",
                    "CUST-010",
                    "PC-006",
                ],
                required_tools=["graph"],
                relevance_judgments=[],
            ),
            EvaluationCase(
                query_id="Q-0016",
                question=(
                    "Which company has both a critical German "
                    "supplier and a supplier located in Switzerland?"
                ),
                query_type="graph",
                split="development",
                difficulty="hard",
                answerable=True,
                expected_answer=ExpectedAnswer(
                    answer_type="entity",
                    value="NovaBio Instruments",
                ),
                answer_source_fact_ids=[
                    "CS-011",
                    "SUP-011",
                    "CS-012",
                    "SUP-012",
                    "GEO-008",
                    "GEO-009",
                ],
                required_tools=["graph"],
                relevance_judgments=[],
            ),
            EvaluationCase(
                query_id="Q-0017",
                question=("Summarize HelioGrid's Q2 revenue growth and principal operating risk."),
                query_type="multi_source",
                split="development",
                difficulty="medium",
                answerable=True,
                expected_answer=ExpectedAnswer(
                    answer_type="text",
                    value=(
                        "Revenue increased from $68 million in 2025 Q2 "
                        "to $92 million in 2026 Q2, while permitting "
                        "delays are slowing western distributed-storage "
                        "projects."
                    ),
                ),
                answer_source_fact_ids=[
                    "FIN-PC-004-2025Q2",
                    "FIN-PC-004-2026Q2",
                    "RISK-004",
                ],
                required_tools=["hybrid_retrieval"],
                relevance_judgments=[
                    _judgment(
                        "DOC-CORE-PC004-QMR-2026Q2",
                        "EVID-CORE-PC004-QMR-FINANCIAL",
                        3,
                        "Canonical revenue-growth evidence.",
                    ),
                    _judgment(
                        "DOC-CORE-PC004-RISK-2026Q2",
                        "EVID-CORE-PC004-RISK-PRIMARY",
                        3,
                        "Canonical permitting-risk evidence.",
                    ),
                ],
            ),
            EvaluationCase(
                query_id="Q-0018",
                question=(
                    "What customer concentration risk does Cedar "
                    "face, and what were its 2026 Q2 revenue and "
                    "net retention?"
                ),
                query_type="multi_source",
                split="test",
                difficulty="medium",
                answerable=True,
                expected_answer=ExpectedAnswer(
                    answer_type="text",
                    value=(
                        "Harbor Regional Bank represents 26 percent of "
                        "Cedar revenue; Cedar generated $84 million of "
                        "revenue in 2026 Q2 with net retention of "
                        "106 percent."
                    ),
                ),
                answer_source_fact_ids=[
                    "RISK-007",
                    "CC-011",
                    "FIN-PC-007-2026Q2",
                ],
                required_tools=["hybrid_retrieval"],
                relevance_judgments=[
                    _judgment(
                        "DOC-CORE-PC007-RISK-2026Q2",
                        "EVID-CORE-PC007-RISK-PRIMARY",
                        3,
                        "Canonical customer-concentration evidence.",
                    ),
                    _judgment(
                        "DOC-CORE-PC007-QMR-2026Q2",
                        "EVID-CORE-PC007-QMR-FINANCIAL",
                        3,
                        "Canonical Q2 financial evidence.",
                    ),
                ],
            ),
            EvaluationCase(
                query_id="Q-0019",
                question=(
                    "What critical supplier risk does NovaBio face, "
                    "and how have instrument shipments changed?"
                ),
                query_type="multi_source",
                split="development",
                difficulty="medium",
                answerable=True,
                expected_answer=ExpectedAnswer(
                    answer_type="text",
                    value=(
                        "NovaBio depends on Helix Motion GmbH as its "
                        "only qualified source for a critical precision "
                        "motion assembly, while instrument shipments "
                        "increased from 950 units in 2025 Q2 to "
                        "1,175 units in 2026 Q2."
                    ),
                ),
                answer_source_fact_ids=[
                    "RISK-008",
                    "CS-011",
                    "SUP-011",
                    "OP-PC-008-2025Q2-SHIPMENTS",
                    "OP-PC-008-2026Q2-SHIPMENTS",
                ],
                required_tools=["hybrid_retrieval"],
                relevance_judgments=[
                    _judgment(
                        "DOC-CORE-PC008-RISK-2026Q2",
                        "EVID-CORE-PC008-RISK-PRIMARY",
                        3,
                        "Canonical supplier-risk evidence.",
                    ),
                    _judgment(
                        "DOC-CORE-PC008-QMR-2026Q2",
                        "EVID-CORE-PC008-QMR-OPERATING",
                        3,
                        "Canonical shipment-trend evidence.",
                    ),
                ],
            ),
            EvaluationCase(
                query_id="Q-0020",
                question=(
                    "Which company had net retention below 100 percent "
                    "in 2026 Q2 and also has document evidence that "
                    "newer customer cohorts are failing to normalize?"
                ),
                query_type="mixed_tool",
                split="development",
                difficulty="hard",
                answerable=True,
                expected_answer=ExpectedAnswer(
                    answer_type="entity",
                    value="Vantage Retail Analytics",
                ),
                answer_source_fact_ids=[
                    "FIN-PC-005-2026Q2",
                    "RISK-005",
                ],
                required_tools=[
                    "sql",
                    "hybrid_retrieval",
                ],
                relevance_judgments=[
                    _judgment(
                        "DOC-CORE-PC005-QMR-2026Q2",
                        "EVID-CORE-PC005-QMR-SIGNAL",
                        3,
                        "Canonical semantic cohort-quality evidence.",
                    )
                ],
            ),
            EvaluationCase(
                query_id="Q-0021",
                question=(
                    "Which company had the highest year-over-year "
                    "revenue growth in 2026 Q2 and also has a "
                    "documented permitting problem?"
                ),
                query_type="mixed_tool",
                split="development",
                difficulty="hard",
                answerable=True,
                expected_answer=ExpectedAnswer(
                    answer_type="entity",
                    value="HelioGrid Energy",
                ),
                answer_source_fact_ids=[
                    "FIN-PC-004-2025Q2",
                    "FIN-PC-004-2026Q2",
                    "RISK-004",
                ],
                required_tools=[
                    "sql",
                    "hybrid_retrieval",
                ],
                relevance_judgments=[
                    _judgment(
                        "DOC-CORE-PC004-RISK-2026Q2",
                        "EVID-CORE-PC004-RISK-PRIMARY",
                        3,
                        "Canonical permitting-risk evidence.",
                    )
                ],
            ),
            EvaluationCase(
                query_id="Q-0022",
                question=(
                    "Among companies with critical suppliers in "
                    "Germany, which had lower revenue in 2026 Q2?"
                ),
                query_type="mixed_tool",
                split="test",
                difficulty="hard",
                answerable=True,
                expected_answer=ExpectedAnswer(
                    answer_type="entity",
                    value="NovaBio Instruments",
                ),
                answer_source_fact_ids=[
                    "CS-003",
                    "SUP-005",
                    "CS-011",
                    "SUP-011",
                    "FIN-PC-002-2026Q2",
                    "FIN-PC-008-2026Q2",
                ],
                required_tools=[
                    "graph",
                    "sql",
                ],
                relevance_judgments=[],
            ),
            EvaluationCase(
                query_id="Q-0023",
                question=(
                    "What is Northstar's expected 2030 exit valuation for Meridian Health Systems?"
                ),
                query_type="insufficient_evidence",
                split="test",
                difficulty="medium",
                answerable=False,
                expected_answer=ExpectedAnswer(
                    answer_type="abstain",
                    value=None,
                ),
                answer_source_fact_ids=[],
                required_tools=["hybrid_retrieval"],
                relevance_judgments=[],
            ),
            EvaluationCase(
                query_id="Q-0024",
                question=("What was Alder Manufacturing's exact customer churn rate in 2026 Q2?"),
                query_type="insufficient_evidence",
                split="development",
                difficulty="medium",
                answerable=False,
                expected_answer=ExpectedAnswer(
                    answer_type="abstain",
                    value=None,
                ),
                answer_source_fact_ids=[],
                required_tools=["sql"],
                relevance_judgments=[],
            ),
        ],
    )
