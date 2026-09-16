# Phase 13 — Human-in-the-Loop Review Workflow Protocol

## 1. Status

PRE-IMPLEMENTATION / PREREGISTERED / UNMEASURED

This protocol is frozen before implementation of the dedicated human-review
workflow.

Phase 13 does not treat automated abstention, deterministic rejection,
instruction-integrity blocking, generation-fidelity rejection, or other
machine-only policy decisions as Human-in-the-Loop behavior.

A Phase 13 case counts as HITL only when an externally supplied human review
decision changes the subsequent workflow outcome.

---

## 2. Purpose

Add a bounded, auditable, resumable human-review workflow to the Northstar
grounded-answering system without changing the behavior of the existing
ordinary `/answer` path.

The reviewed workflow must stop after deterministic grounded synthesis and
before:

1. generation-authority construction;
2. local language-model invocation;
3. generation-fidelity evaluation;
4. answer presentation.

A human decision must then determine whether downstream answer generation may
continue.

---

## 3. Architectural boundary

The intended reviewed-answer flow is:

question
→ bounded specification
→ execution
→ evidence normalization
→ deterministic sufficiency
→ instruction-integrity policy
→ deterministic grounded synthesis
→ human-review boundary
→ human decision
→ approved downstream generation OR rejected terminal outcome

The review boundary is intentionally downstream of instruction integrity.

Human approval MUST NOT:

- override an insufficient evidence assessment;
- override an unsupported bounded request;
- override an instruction-integrity block;
- expand the execution plan;
- add tools;
- add evidence;
- add citations;
- add provenance;
- modify the deterministic grounded answer under review.

Requests that fail before grounded synthesis continue to use their existing
typed behavior and MUST NOT be converted into approvable human-review items.

---

## 4. Scope

Phase 13 introduces an explicit reviewed-answer workflow.

It does NOT introduce an automatic classifier for deciding which requests are
high-risk or require review.

Automatic risk-based escalation is outside Phase 13 and may be addressed by a
later dedicated policy phase.

The existing ordinary `/answer` path remains behaviorally unchanged.

---

## 5. Human-review contract

The implementation must provide a frozen typed review contract containing at
least the following concepts.

### 5.1 Review status

Allowed lifecycle states:

- `awaiting_review`
- `approved`
- `rejected`

`approved` and `rejected` are terminal review-decision states.

A terminal decision may not be changed to a different decision.

### 5.2 Review disposition

Allowed human dispositions:

- `approve`
- `reject`

No implicit default disposition is permitted.

### 5.3 HumanReviewRequest

A review request must have a stable review identifier and must bind exactly to:

- the original answer request;
- the deterministic grounded answer under review;
- selected supporting evidence record IDs;
- citation IDs;
- canonical source-fact provenance;
- the synthesis/policy versions needed to interpret the prepared answer;
- current review status.

The persisted review representation MUST NOT rely on mutable process-local
object identity.

### 5.4 HumanReviewDecision

A decision must include:

- review ID;
- explicit `approve` or `reject` disposition;
- non-empty reviewer identity asserted by the caller;
- deterministic decision metadata required by the frozen contract.

Reviewer identity in Phase 13 is caller-asserted metadata.

Phase 13 does NOT establish user authentication, authorization, identity
verification, RBAC, or enterprise IAM.

Those capabilities must not be claimed from this phase.

---

## 6. Review packet

The human reviewer must receive a bounded review packet derived from the
deterministic grounded answer.

The packet may include:

- deterministic answer type;
- deterministic answer value;
- citation IDs;
- source-fact provenance;
- selected supporting record IDs;
- bounded source summaries where explicitly permitted by the final contract.

The packet MUST NOT include:

- raw model generation, because generation has not yet occurred;
- hidden prompts;
- unrestricted execution state;
- credentials or secrets;
- an expanded tool plan;
- arbitrary unselected retrieval context.

Phase 12 instruction-integrity decisions remain upstream and authoritative.

---

## 7. Persistence requirements

Review state must survive beyond one Python object lifetime.

The implementation must persist review records using the repository's existing
PostgreSQL / SQLAlchemy / Alembic infrastructure.

At minimum, persistence must support:

- create awaiting-review record;
- fetch by stable review ID;
- submit one terminal human decision;
- reload terminal decision;
- reject conflicting second decisions;
- preserve the exact prepared-review authority required for deterministic
  continuation.

The database schema must be introduced through a new Alembic migration.

Tests may use a bounded test database fixture or repository abstraction, but the
verified integration path must exercise persisted database state.

---

## 8. Decision semantics

### 8.1 Approval

An approved review must resume from the exact frozen prepared authority that was
reviewed.

Approval may authorize:

- construction of generation authority;
- generation-provider invocation;
- fidelity validation;
- safe presentation.

Approval MUST NOT rerun or mutate:

- specification;
- retrieval;
- SQL;
- graph execution;
- evidence selection;
- sufficiency;
- instruction-integrity evaluation;
- deterministic grounded synthesis.

The final answer must remain bounded by the exact deterministic authority that
the reviewer approved.

### 8.2 Rejection

A rejected review must terminate through a typed human-rejected application
result.

Rejection must guarantee:

- no generation authority is created after rejection;
- generation provider is not invoked after rejection;
- no raw model output exists for the rejected continuation;
- the deterministic candidate is not presented as an approved answer.

The rejected result may expose bounded citations/provenance required by the
frozen contract, but it must clearly represent a human-rejected workflow rather
than an evidence-insufficiency abstention.

---

## 9. Pause / resume requirement

The workflow must contain a genuine external intervention boundary.

A single synchronous method that internally chooses `approve` or `reject`
without returning control to an external caller does NOT satisfy this
requirement.

The workflow must:

1. create/persist an `awaiting_review` item;
2. return control to the caller;
3. accept the human decision in a separate operation;
4. reload the persisted review;
5. resume or terminate according to that decision.

LangGraph interrupt/resume primitives should be used where they provide the
workflow boundary cleanly.

Persistent correctness must not depend solely on an in-memory LangGraph
checkpointer.

The PostgreSQL review record is the durable source of review lifecycle truth.

---

## 10. Idempotency and conflict behavior

Decision submission must be deterministic.

Required behavior:

- first valid decision transitions `awaiting_review` to the matching terminal
  state;
- exact replay of the same terminal disposition may return the existing
  terminal decision idempotently;
- a conflicting second disposition must fail with a typed conflict;
- decision submission for an unknown review ID must fail with a typed
  not-found result;
- continuation for an `awaiting_review` item without a decision must not invoke
  generation;
- terminal review records must not silently return to `awaiting_review`.

The final contract must define exact exception/result types before confirmation.

---

## 11. Concurrency boundary

The implementation must prevent two conflicting terminal decisions from both
being accepted.

A database transaction, optimistic version check, row lock, conditional update,
or another explicit deterministic mechanism must enforce the invariant.

Phase 13 does not claim distributed consensus.

---

## 12. Application/API surface

The intended bounded application surface contains separate operations for:

1. start reviewed answer;
2. inspect review;
3. submit human decision;
4. obtain/resume terminal answer behavior.

The final HTTP paths and schemas must be frozen before Phase 13 confirmation.

Existing `/answer` semantics must remain unchanged.

HTTP authorization is outside Phase 13 unless separately implemented and
verified.

---

## 13. Observability and privacy

Human-review observability must remain bounded.

Permitted operational fields may include:

- trace ID;
- review ID;
- review status;
- decision disposition;
- stage name;
- bounded timing;
- violation/error code;
- counts.

Logs must not newly emit:

- complete question text;
- complete evidence text;
- hidden prompt text;
- raw model output;
- reviewer free-form rationale, if such a field is later allowed.

The final contract must explicitly document every logged review field.

---

## 14. Confirmation case families

Phase 13 confirmation must contain locked cases covering the following
families.

### A. Non-reviewed regression controls

At least three existing answer cases must continue through the ordinary
unreviewed `/answer` path with frozen behavior.

Purpose:

- prove the new workflow does not silently force review on existing requests;
- preserve existing answer/abstention semantics.

### B. Awaiting-review creation

At least three supported, sufficient, integrity-allowed cases must:

- reach deterministic grounded synthesis;
- create one persisted review record;
- return `awaiting_review`;
- invoke no generation before a human decision.

### C. Human approval

At least three awaiting-review cases must receive `approve`.

Required observations:

- persisted decision becomes `approved`;
- exact reviewed grounded authority is reused;
- generation is invoked only after approval;
- final presentation remains bounded by existing fidelity behavior;
- citation/provenance continuity is preserved.

### D. Human rejection

At least three awaiting-review cases must receive `reject`.

Required observations:

- persisted decision becomes `rejected`;
- generation remains uninvoked;
- no approved answer presentation occurs;
- terminal result is typed as human rejection;
- citation/provenance behavior matches the frozen Phase 13 contract.

### E. Pre-review failure preservation

Cases must include:

- insufficient evidence;
- unsupported bounded request;
- instruction-integrity blocked request.

These cases must retain their pre-existing typed outcomes and MUST NOT create an
approvable review request.

### F. Decision idempotency / conflict

Cases must include:

- exact duplicate approval replay;
- exact duplicate rejection replay;
- approve followed by reject;
- reject followed by approve;
- unknown review ID.

Expected behavior must be frozen before confirmation.

### G. Persistence / restart

At least one case must:

1. create an awaiting-review record;
2. destroy the originating application/service object;
3. construct a fresh application/service object;
4. reload the persisted review;
5. submit the human decision;
6. complete the expected approved or rejected path.

This verifies durable review lifecycle behavior rather than process-local state.

---

## 15. Locked confirmation metrics

Before confirmation, Phase 13 must freeze exact denominators for:

### Review Creation Accuracy

Expected reviewed cases that enter exactly one awaiting-review state.

Promotion threshold:

`100%`

### Pre-Decision Generation Suppression

Awaiting-review cases with zero generation invocation before a human decision.

Promotion threshold:

`100%`

### Approval Continuation Accuracy

Approved cases that resume through the approved continuation with exact reviewed
authority identity/provenance.

Promotion threshold:

`100%`

### Rejection Enforcement Rate

Rejected cases that terminate without generation or approved presentation.

Promotion threshold:

`100%`

### Pre-Review Failure Preservation

Pre-review failure cases retaining their existing typed failure behavior without
creating an approvable review.

Promotion threshold:

`100%`

### Citation Integrity

Locked cases whose observed citation behavior exactly matches the frozen
contract.

Promotion threshold:

`100%`

### Provenance Integrity

Locked cases whose observed provenance behavior exactly matches the frozen
contract.

Promotion threshold:

`100%`

### Decision Conflict Enforcement

Conflicting second decisions rejected according to the frozen contract.

Promotion threshold:

`100%`

### Restart Resume Accuracy

Locked restart/persistence cases completing from persisted review state using a
fresh service/runtime instance.

Promotion threshold:

`100%`

No threshold may be changed after the first confirmation measurement.

---

## 16. Reproducibility requirements

Before Phase 13 confirmation:

- the review contract must have an explicit version;
- the persistence schema revision must be frozen;
- the case manifest must be frozen;
- the measuring instrument must be frozen;
- canonical JSON serialization must be deterministic;
- protocol, case-manifest, contract, and runner hashes must be recorded;
- the confirmation result path must not yet exist.

The first confirmation artifact must be preserved whether promotion succeeds or
fails.

---

## 17. Capability-promotion rule

`Human-in-the-Loop Workflows` may move from `NOT STARTED` to `VERIFIED` only if
all of the following are demonstrated by frozen evidence:

1. a real external human decision boundary exists;
2. awaiting-review state is persisted;
3. the workflow returns control while awaiting review;
4. approval and rejection materially produce different downstream behavior;
5. rejection prevents generation;
6. approval is required before generation in the reviewed path;
7. review state survives reconstruction of the application/service object;
8. conflicting terminal decisions cannot both succeed;
9. citation/provenance invariants remain bounded;
10. the ordinary unreviewed answer path remains behaviorally intact.

Automated abstention does not satisfy this rule.

---

## 18. Claim boundary

If verified, Phase 13 may support a narrow claim such as:

> Built a persisted human-review workflow for grounded enterprise-AI answers
> with explicit awaiting-review state, separate approve/reject operations,
> deterministic continuation, conflict-safe terminal decisions, and
> citation/provenance continuity.

Phase 13 must NOT by itself be represented as proof of:

- enterprise authentication;
- reviewer identity verification;
- RBAC;
- authorization;
- multi-party approval;
- legal/compliance approval;
- production workflow durability;
- distributed workflow consensus;
- general Responsible AI governance;
- automatic risk classification;
- comprehensive model safety.

The broader `Responsible AI Guardrails` capability remains separate.

---

## 19. Planned phase decomposition

### Phase 13A

Freeze this preregistered HITL protocol and exact claim boundary.

### Phase 13B

Implement and freeze typed human-review contracts and PostgreSQL persistence.

### Phase 13C

Implement the reviewed-answer preparation boundary and external pause/resume
workflow.

### Phase 13D

Implement bounded HTTP/application review operations and observability.

### Phase 13E0

Freeze the confirmation case manifest and measuring instrument.

### Phase 13E1

Execute the first frozen confirmation and preserve the result.

### Phase 13F

Record final repository evidence without moving historical feature/result tags.
