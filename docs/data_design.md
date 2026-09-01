# Northstar Capital Synthetic Enterprise Dataset

## 1. Purpose

This dataset provides a controlled enterprise information environment for
developing and evaluating the Enterprise GenAI Retrieval, Agent & Evaluation
Platform.

The dataset is synthetic. It is designed so that the correct underlying facts,
relationships, documents, and expected answers are known in advance.

The goal is not merely to provide text for a RAG demo. The goal is to create
ground truth against which retrieval, reasoning, generation, and agent behavior
can be measured.

## 2. Business Context

Northstar Capital is a fictional investment firm managing a diversified
private-equity portfolio.

The platform will support investment professionals conducting:

- portfolio monitoring
- investment committee research
- operating-performance analysis
- risk identification
- competitive research
- supplier and customer concentration analysis
- cross-portfolio exposure analysis
- transaction review
- investment thesis validation

Users may need information from both structured and unstructured sources.

Some questions should be answerable from documents alone.

Some should require SQL.

Some should require graph traversal.

Some should require multiple sources or multiple tools.

Some should deliberately have insufficient evidence.

## 3. Design Principles

The dataset must satisfy the following constraints.

### 3.1 Deterministic

Generation must use a fixed random seed.

Running the generator against the same version of the source definitions should
produce equivalent canonical data.

### 3.2 Internally consistent

Facts repeated across documents and structured data should agree unless a
deliberate contradiction is part of an evaluation case.

### 3.3 Traceable

Every important synthetic fact should have a stable identifier.

Documents should also have stable identifiers so evaluation records can point
to exact supporting evidence.

### 3.4 Retrieval-diverse

The corpus must contain questions where different retrieval strategies have
different strengths.

### 3.5 Evaluation-first

Evaluation cases must be defined from known ground truth rather than generated
after observing model behavior.

### 3.6 No fabricated performance claims

The dataset itself contains no claims about retrieval or model performance.

Metrics will only be reported after running experiments.

---

# 4. Enterprise Universe

## 4.1 Investment Firm

Firm:

- `FIRM-001` — Northstar Capital

Initial fund:

- `FUND-001` — Northstar Growth Fund IV

The initial implementation uses one fund so that retrieval complexity comes
from portfolio-company relationships and enterprise documents rather than from
unnecessary fund-count scale.

Future dataset versions may add additional funds.

## 4.2 Portfolio Companies

The first version contains eight portfolio companies.

### PC-001 — Meridian Health Systems

Industry:

- healthcare technology

Primary geography:

- United States

Business:

- hospital workflow and clinical operations software

Important evaluation characteristics:

- major customer concentration
- recurring-revenue growth
- regulatory exposure
- semantically described operational risks

### PC-002 — Alder Manufacturing

Industry:

- industrial manufacturing

Primary geography:

- United States

Business:

- precision components for aerospace and industrial customers

Important evaluation characteristics:

- supplier concentration
- raw-material exposure
- exact component identifiers
- aerospace customer relationships

### PC-003 — BluePeak Logistics

Industry:

- logistics and transportation technology

Primary geography:

- United States and Canada

Business:

- freight-management and routing software

Important evaluation characteristics:

- cross-border exposure
- fuel-related customer sensitivity
- geographic relationships
- operational efficiency metrics

### PC-004 — HelioGrid Energy

Industry:

- renewable energy infrastructure

Primary geography:

- United States

Business:

- distributed solar and battery infrastructure

Important evaluation characteristics:

- project finance exposure
- permitting risks
- geographic concentration
- supplier dependencies

### PC-005 — Vantage Retail Analytics

Industry:

- retail technology

Primary geography:

- United States and United Kingdom

Business:

- demand forecasting and merchandising analytics

Important evaluation characteristics:

- semantic product descriptions
- large-enterprise customer relationships
- international exposure
- retention metrics

### PC-006 — Orbis Cybersecurity

Industry:

- cybersecurity

Primary geography:

- United States and Germany

Business:

- enterprise identity and threat-detection software

Important evaluation characteristics:

- technical terminology
- product codenames
- security incidents
- recurring-revenue metrics

### PC-007 — Cedar Financial Technologies

Industry:

- financial technology

Primary geography:

- United States

Business:

- compliance and workflow infrastructure for regional banks

Important evaluation characteristics:

- regulatory risk
- banking customer concentration
- transaction-volume metrics
- structured plus document reasoning

### PC-008 — NovaBio Instruments

Industry:

- life-sciences instrumentation

Primary geography:

- United States and Switzerland

Business:

- laboratory automation and diagnostic instrumentation

Important evaluation characteristics:

- supplier dependencies
- exact instrument identifiers
- life-sciences demand cycles
- product and geographic relationships

---

# 5. Structured Data Model

The canonical structured dataset should eventually map into PostgreSQL.

## 5.1 firms

Fields:

- `firm_id`
- `name`

## 5.2 funds

Fields:

- `fund_id`
- `firm_id`
- `name`
- `vintage_year`
- `committed_capital_usd`

## 5.3 companies

Fields:

- `company_id`
- `fund_id`
- `name`
- `industry`
- `headquarters_country`
- `investment_date`
- `ownership_pct`

## 5.4 financial_metrics

Quarterly observations.

Fields:

- `company_id`
- `period`
- `revenue_usd`
- `ebitda_usd`
- `gross_margin_pct`
- `net_retention_pct`
- `customer_count`
- `employee_count`

Not every field is economically meaningful for every company.

The generator should use nullable values where appropriate rather than forcing
irrelevant metrics into every business.

## 5.5 operational_metrics

Fields depend on company type.

Canonical fields:

- `metric_id`
- `company_id`
- `period`
- `metric_name`
- `metric_value`
- `unit`

This supports company-specific metrics without creating a separate table for
every industry.

Examples:

- software uptime
- implementation backlog
- shipments
- production yield
- freight volume
- installed megawatts
- transaction volume

## 5.6 customers

Fields:

- `customer_id`
- `name`
- `industry`
- `country`

## 5.7 company_customers

Fields:

- `company_id`
- `customer_id`
- `revenue_share_pct`
- `relationship_start_date`
- `relationship_status`

This table is deliberately important for concentration-risk questions.

## 5.8 suppliers

Fields:

- `supplier_id`
- `name`
- `category`
- `country`

## 5.9 company_suppliers

Fields:

- `company_id`
- `supplier_id`
- `spend_share_pct`
- `criticality`
- `single_source`
- `relationship_status`

This supports supplier-risk and graph reasoning.

## 5.10 geographic_exposures

Fields:

- `company_id`
- `country`
- `exposure_type`
- `exposure_pct`

Possible exposure types:

- revenue
- supplier
- employee
- manufacturing
- project

## 5.11 risks

Fields:

- `risk_id`
- `company_id`
- `risk_category`
- `title`
- `severity`
- `status`
- `identified_date`
- `description`

## 5.12 transactions

Fields:

- `transaction_id`
- `company_id`
- `transaction_type`
- `announcement_date`
- `close_date`
- `value_usd`
- `counterparty`

## 5.13 documents

Fields:

- `document_id`
- `company_id`
- `document_type`
- `title`
- `document_date`
- `source_path`
- `confidentiality`
- `version`

---

# 6. Document Corpus

The first corpus should contain approximately 32 to 40 documents.

Each company should initially have four core documents:

1. investment committee memo
2. quarterly management report
3. board update
4. risk or operating review

Additional documents may be added where they create useful retrieval cases.

Potential additional types:

- industry research
- competitive assessment
- call transcript
- strategy memorandum
- transaction memo
- incident report
- supplier review
- customer renewal memo

## 6.1 Document IDs

Use stable identifiers.

Example:

```text
DOC-PC001-IC-001
DOC-PC001-QMR-2026Q1
DOC-PC001-BOARD-2026Q2
DOC-PC001-RISK-001
```

Do not use filenames as the primary identity.

## 6.2 Evidence IDs

Important factual passages should have stable evidence identifiers.

Example:

```text
EVID-PC001-CUSTOMER-CONCENTRATION-001
```

The evaluation dataset should be able to point to one or more evidence IDs.

---

# 7. Ground-Truth Relationship Model

The synthetic world should explicitly encode important relationships before
documents are generated.

Examples:

```text
company -> owned_by -> fund
company -> serves -> customer
company -> depends_on -> supplier
company -> exposed_to -> geography
company -> has_risk -> risk
company -> acquired -> company
customer -> operates_in -> industry
supplier -> located_in -> geography
```

This relationship layer will later allow graph retrieval to be evaluated against
known paths.

Example path:

```text
Alder Manufacturing
    -> depends_on
TitaniumWorks GmbH
    -> located_in
Germany
```

A query asking which portfolio companies depend on German critical suppliers
should therefore have an objectively known answer.

---

# 8. Intentional Retrieval Cases

The corpus must not be neutral with respect to retrieval difficulty.

It should intentionally contain the following categories.

## 8.1 Lexical / BM25-favored cases

Questions involving:

- exact product codes
- uncommon company names
- contract identifiers
- acronyms
- technical terminology
- exact phrases

Example:

```text
Which company reported an incident involving ORBIS-IDX-7?
```

An exact lexical match should be highly valuable.

## 8.2 Dense-retrieval-favored cases

Questions where the query and evidence express the same idea using substantially
different wording.

Example query:

```text
Which company is having trouble converting new customers into stable recurring
accounts?
```

Possible evidence wording:

```text
New-logo bookings remained strong, but early-cohort retention weakened and
several recently signed accounts failed to progress into normalized renewal
patterns.
```

The evaluation case should not depend on exact term overlap.

## 8.3 Hybrid-favored cases

Questions combining semantic intent with an exact identifier.

Example:

```text
What operational issue affected the HG-BESS-42 deployment program?
```

The identifier favors lexical retrieval while the surrounding question requires
semantic interpretation.

## 8.4 SQL-favored cases

Questions involving:

- exact numerical filtering
- aggregation
- ranking
- time-series comparisons
- thresholds

Example:

```text
Which portfolio company had the largest year-over-year revenue increase in
2026 Q2?
```

Documents may contain related discussion, but the canonical answer should come
from structured data.

## 8.5 Graph-favored cases

Questions involving multi-hop relationships.

Example:

```text
Which portfolio companies depend on a critical supplier located in Germany?
```

## 8.6 Mixed-tool cases

Questions where no single retrieval mechanism is sufficient.

Example:

```text
Which company has both deteriorating customer retention and a board-identified
customer concentration risk?
```

This may require:

1. structured metric retrieval
2. document retrieval
3. evidence synthesis

## 8.7 Insufficient-evidence cases

Some questions must intentionally have no supported answer.

The correct system behavior should be abstention rather than fabrication.

Example:

```text
What is Northstar's expected exit valuation for Meridian in 2030?
```

if no source contains such a forecast.

---

# 9. Evaluation Dataset

The evaluation set should initially target approximately 100 questions.

Suggested composition:

| Category | Approximate Count |
| --- | ---: |
| lexical / identifier | 15 |
| semantic | 15 |
| hybrid | 15 |
| SQL / quantitative | 15 |
| graph / relationship | 10 |
| multi-source | 15 |
| mixed-tool | 10 |
| insufficient evidence | 5 |

Counts are initial design targets, not immutable requirements.

## 9.1 Evaluation Record

Each question should eventually use a structured representation similar to:

```json
{
  "query_id": "Q-0001",
  "question": "Which company reported an incident involving ORBIS-IDX-7?",
  "query_type": "lexical",
  "answerable": true,
  "expected_answer": "Orbis Cybersecurity",
  "relevant_document_ids": [
    "DOC-PC006-RISK-001"
  ],
  "relevant_evidence_ids": [
    "EVID-PC006-INCIDENT-001"
  ],
  "required_tools": [
    "lexical_retrieval"
  ],
  "difficulty": "easy"
}
```

For numerical questions, expected answers should include canonical units.

For multi-answer questions, answers should use a deterministic ordering when
order itself is not meaningful.

---

# 10. Evaluation Splits

The dataset should have:

```text
development
test
```

splits initially.

The development split may be inspected while tuning retrieval.

The test split should remain untouched during ordinary retriever tuning.

A future training split may be introduced for the LoRA routing experiment.

## 10.1 Leakage Prevention

Do not tune retrieval parameters directly against the test set.

Do not train routing or classification models on test questions.

Do not manually rewrite test queries after inspecting model failures unless the
dataset version is explicitly incremented.

---

# 11. Metrics Supported by the Dataset

Once retrieval systems exist, this dataset should support:

## Retrieval

- Precision@k
- Recall@k
- MRR
- NDCG@k

## Generation

- answer correctness
- citation correctness
- citation completeness
- groundedness
- abstention correctness

## Agent behavior

- tool-selection accuracy
- tool-sequence accuracy
- task completion
- unnecessary tool calls
- invalid tool calls

## System behavior

- latency
- throughput
- error rate
- recovery behavior

No metric is considered evidence until its corresponding experiment has
actually been run.

---

# 12. Dataset Versioning

The initial dataset version will be:

```text
northstar-v1
```

All generated artifacts should include or be traceable to the dataset version.

If ground truth changes materially, increment the dataset version rather than
silently overwriting the evaluation assumptions.

---

# 13. Phase 2 Completion Criteria

Phase 2 is complete only when:

1. the canonical enterprise universe exists in machine-readable form;
2. structured data is validated;
3. synthetic documents have stable IDs;
4. important claims map to stable evidence IDs;
5. ground-truth relationships are machine-readable;
6. an initial development/test evaluation set exists;
7. validation tests detect broken references and inconsistent IDs;
8. generation is deterministic;
9. dataset construction is documented;
10. the resulting artifacts are committed reproducibly.

Embeddings and retrieval implementations begin only after these criteria are
satisfied.
