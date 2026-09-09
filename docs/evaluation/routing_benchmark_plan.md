# Routing Benchmark Ground-Truth Plan

## Status

GROUND-TRUTH CONSTRUCTION / PRE-BASELINE

No Phase 8 routing baseline has been measured when this plan is created.

## Purpose

Create a deterministic routing-only benchmark for selecting enterprise tool
families before implementing learned routing.

The benchmark is independent of the 24-case Northstar answer/retrieval
evaluation seed.

## Tool Ontology

Canonical tool families:

- retrieval
- sql
- graph

Canonical multi-tool routes:

- retrieval
- sql
- graph
- retrieval+sql
- retrieval+graph
- sql+graph
- retrieval+sql+graph

Legacy lexical_retrieval, dense_retrieval, and hybrid_retrieval annotations
normalize to retrieval.

The selected retrieval implementation remains the frozen hybrid RRF stack.

## Tool Semantics

Retrieval is required for qualitative evidence contained in unstructured
portfolio documents.

SQL is required for deterministic structured filtering, aggregation,
comparison, or arithmetic.

Graph is required for relationship traversal across connected enterprise
entities.

These labels describe the preferred execution contract, not theoretical
computability. A relational database could technically implement many graph
operations with joins, but relationship traversal is intentionally assigned
to the graph tool family.

## Abstention

Insufficient evidence is not a routing tool.

A route may need to execute retrieval, SQL, or graph operations before the
system can determine that evidence is insufficient.

Abstention will be evaluated downstream.

## Dataset

Dataset version:

northstar-v1

Routing benchmark version:

northstar-routing-v1

Total cases:

168

Route labels:

7

Cases per route label:

24

## Frozen Benchmark Fingerprint

Canonical deterministic SHA-256:

995f707a4cc6393f0e916f903cc57f9aec6fbabb3c43a00a78e318ca505b6912

The fingerprint is computed from the canonical JSON serialization of the full
RoutingSet.

The test suite asserts this exact fingerprint after the Phase 8A1
ground-truth freeze.

Any semantic benchmark change after this freeze requires a new routing
benchmark version rather than silently updating northstar-routing-v1.

## Splits

Train:

112 cases

Development:

28 cases

Locked holdout:

28 cases

Each route label contains:

- 16 train cases
- 4 development cases
- 4 locked-holdout cases

## Template-Family Leakage Control

Each route label has six linguistic template families:

- four train families
- one development family
- one locked-holdout family

Each family generates four deterministic entity-grounded cases.

A template family belongs to exactly one split.

The split is therefore family-based rather than random-example-based.

The locked holdout tests generalization to linguistic task formulations not
seen in training.

## Lexical Leakage Control

Route classes must not be distinguishable merely because benchmark questions
explicitly name implementation concepts.

Development and locked-holdout formulations avoid direct instructions such as:

- narrative evidence
- written materials
- structured performance
- relationship network
- relationship path
- traverse
- calculate

Natural task semantics remain intentionally visible.

Examples include:

- revenue, EBITDA, retention, and percentage-change requests for structured
  computation;
- customer and supplier relationships for entity traversal;
- requests for management explanations or qualitative concerns for document
  retrieval.

The goal is not lexical neutrality. The goal is to require intent-to-capability
mapping rather than recognition of synthetic tool-instruction phrases.

## Existing Evaluation Separation

None of the 24 existing Northstar evaluation questions is copied into the
routing benchmark.

The existing evaluation set is not training data for the routing benchmark.

Its existing required_tools annotations may later be used as an external
compatibility diagnostic after model selection.

## Entity Grounding

Benchmark questions are instantiated against deterministic Northstar
companies, customers, suppliers, and risks.

Entity IDs are retained as audit metadata.

Models must receive only the question text as classifier input unless a later
experiment explicitly preregisters another representation.

## Intended Metrics

Primary metrics for later routing experiments:

- exact route-set accuracy
- macro F1 over tool families

Critical omission metric:

- required-tool omission rate

Secondary metrics:

- per-tool precision
- per-tool recall
- per-tool F1
- Hamming loss
- over-routing rate
- under-routing rate

## Benchmark Freeze Rule

The routing benchmark must be implemented, tested, fingerprinted, committed,
and tagged before measuring the Phase 8A2 heuristic baseline.

No routing examples or labels may be changed in response to baseline
performance.

## Phase Sequence

Phase 8A1:

routing ontology and benchmark freeze

Phase 8A2:

preregistered deterministic heuristic baseline

Phase 8B:

frozen pretrained classifier baseline

Phase 8C:

PEFT / LoRA routing classifier

Phase 8D:

SQL, graph, and retrieval execution

Phase 8E:

bounded LangGraph orchestration and human-in-the-loop policy

## Claim Boundary

Phase 8A1 establishes benchmark construction only.

It does not establish classifier quality, routing performance, production
behavior, SQL execution correctness, graph execution correctness, agent
quality, or generation quality.
