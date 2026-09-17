from __future__ import annotations

import gc
import hashlib
import json
from pathlib import Path
from typing import Any

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import (
    delete,
    select,
)
from sqlalchemy import (
    inspect as sqlalchemy_inspect,
)
from sqlalchemy.orm import sessionmaker

from enterprise_genai.api.answer import (
    router as answer_router,
)
from enterprise_genai.api.reviewed_answer import (
    router as reviewed_answer_router,
)
from enterprise_genai.application.answering import (
    AnswerRequest,
)
from enterprise_genai.application.northstar_specification import (
    NorthstarBoundedSpecificationProvider,
)
from enterprise_genai.application.reviewed_answering import (
    ReviewedAnsweringService,
)
from enterprise_genai.application.service import (
    GroundedAnsweringService,
)
from enterprise_genai.application.specification import (
    ExecutableAnswerSpecification,
)
from enterprise_genai.db.models import (
    HumanReviewRow,
)
from enterprise_genai.db.session import engine
from enterprise_genai.execution.contracts import (
    DatabaseRowReference,
    RetrievalHit,
    RetrievalPayload,
    StructuredEntity,
    StructuredPayload,
    ToolExecutionResult,
)
from enterprise_genai.generation.contracts import (
    GenerationProviderMetadata,
    GroundedGenerationRequest,
    RawGeneration,
)
from enterprise_genai.human_review.repository import (
    HumanReviewNotFoundError,
    HumanReviewRepository,
)
from enterprise_genai.orchestration.contracts import (
    BoundedOrchestrationPlan,
    OrchestrationStateSnapshot,
)

PHASE13E_CONFIRMATION_VERSION = "northstar-human-review-phase13e-confirmation-v1"

DEFAULT_CASE_MANIFEST_PATH = Path("artifacts/evaluation/phase13e0/human_review_case_manifest.json")

DEFAULT_FREEZE_MANIFEST_PATH = Path(
    "artifacts/evaluation/phase13e0/human_review_confirmation_freeze.json"
)

DEFAULT_RESULT_PATH = Path("artifacts/evaluation/phase13e1/human_review_confirmation.json")

RUNNER_PATH = Path("src/enterprise_genai/evaluation/human_review_confirmation.py")


def _canonical_bytes(
    value: object,
) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


def deterministic_report_bytes(
    report: dict[str, object],
) -> bytes:
    return (
        json.dumps(
            report,
            indent=2,
            sort_keys=True,
            ensure_ascii=False,
        )
        + "\n"
    ).encode("utf-8")


def report_sha256(
    report: dict[str, object],
) -> str:
    return hashlib.sha256(_canonical_bytes(report)).hexdigest()


def _file_sha256(
    path: Path,
) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load_json(
    path: Path,
) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _verify_embedded_digest(
    *,
    payload: dict[str, Any],
    digest_field: str,
) -> str:
    body = dict(payload)

    stored = str(body.pop(digest_field))

    observed = hashlib.sha256(_canonical_bytes(body)).hexdigest()

    if stored != observed:
        raise RuntimeError(f"{digest_field} canonical drift: stored {stored}, observed {observed}")

    return stored


def load_frozen_inputs(
    *,
    case_manifest_path: Path = (DEFAULT_CASE_MANIFEST_PATH),
    freeze_manifest_path: Path = (DEFAULT_FREEZE_MANIFEST_PATH),
) -> tuple[
    dict[str, Any],
    dict[str, Any],
]:
    cases = _load_json(case_manifest_path)

    case_digest = _verify_embedded_digest(
        payload=cases,
        digest_field=("canonical_sha256"),
    )

    freeze = _load_json(freeze_manifest_path)

    _verify_embedded_digest(
        payload=freeze,
        digest_field=("canonical_sha256"),
    )

    frozen_case = freeze["case_manifest"]

    if frozen_case["canonical_sha256"] != case_digest:
        raise RuntimeError("Frozen Phase 13E0 case manifest canonical digest drifted.")

    if frozen_case["file_sha256"] != _file_sha256(case_manifest_path):
        raise RuntimeError("Frozen Phase 13E0 case manifest bytes drifted.")

    for raw_path, expected in freeze["files"].items():
        path = Path(raw_path)

        observed = _file_sha256(path)

        if observed != expected:
            raise RuntimeError(f"Frozen Phase 13E0 file drifted: {raw_path}")

    for name, spec in cases["locked_metrics"].items():
        case_ids = spec["case_ids"]

        if len(case_ids) != spec["denominator"]:
            raise RuntimeError(f"Frozen metric denominator drifted: {name}")

        if spec["threshold"] != 1.0:
            raise RuntimeError("Phase 13 promotion thresholds are frozen at 100%.")

    if len(cases["ordinary_controls"]) != 3:
        raise RuntimeError("Phase 13 requires exactly three frozen ordinary controls.")

    if len(cases["reviewed_cases"]) != 6:
        raise RuntimeError("Phase 13 requires exactly six frozen reviewed cases.")

    if len(cases["pre_review_failures"]) != 3:
        raise RuntimeError("Phase 13 requires exactly three frozen pre-review failures.")

    if len(cases["decision_cases"]) != 5:
        raise RuntimeError("Phase 13 requires exactly five frozen decision cases.")

    return (
        cases,
        freeze,
    )


def _metadata() -> GenerationProviderMetadata:
    return GenerationProviderMetadata(
        provider_id=("phase13e-confirmation-provider"),
        model_id=("deterministic-confirmation-model"),
        model_revision="v1",
        device="cpu",
        dtype="float32",
    )


class TrackingGenerationProvider:
    def __init__(
        self,
        text: str,
    ) -> None:
        self.text = text
        self.calls = 0

        self.requests: list[GroundedGenerationRequest] = []

    @property
    def last_request(
        self,
    ) -> GroundedGenerationRequest | None:
        if not self.requests:
            return None

        return self.requests[-1]

    def generate(
        self,
        request: GroundedGenerationRequest,
    ) -> RawGeneration:
        self.calls += 1

        self.requests.append(request)

        return RawGeneration(
            text=self.text,
            metadata=_metadata(),
        )


class FixedRuntime:
    def __init__(
        self,
        snapshot: OrchestrationStateSnapshot,
    ) -> None:
        self.snapshot = snapshot
        self.calls = 0

    def execute(
        self,
        plan: BoundedOrchestrationPlan,
    ) -> OrchestrationStateSnapshot:
        self.calls += 1

        if plan != self.snapshot.plan:
            raise RuntimeError("confirmation runtime plan drift")

        return self.snapshot


class ForbiddenRuntime:
    def execute(
        self,
        plan: BoundedOrchestrationPlan,
    ) -> OrchestrationStateSnapshot:
        del plan

        raise AssertionError("upstream execution must not run")


class ForbiddenSpecificationProvider:
    def prepare(
        self,
        request: AnswerRequest,
    ):
        del request

        raise AssertionError("specification must not rerun")


def _source_rows(
    fixture: dict[str, Any],
) -> tuple[
    DatabaseRowReference,
    ...,
]:
    return tuple(
        DatabaseRowReference(
            table=str(row["table"]),
            primary_key=dict(row["primary_key"]),
            canonical_fact_ids=tuple(row["canonical_fact_ids"]),
        )
        for row in fixture["source_rows"]
    )


def _snapshot_for_case(
    case: dict[str, Any],
) -> OrchestrationStateSnapshot:
    provider = NorthstarBoundedSpecificationProvider()

    specification = provider.prepare(AnswerRequest(question=str(case["question"])))

    if not isinstance(
        specification,
        ExecutableAnswerSpecification,
    ):
        raise RuntimeError("snapshot fixture requires an executable specification")

    plan = specification.orchestration_plan

    fixture = case["fixture"]

    kind = str(fixture["kind"])

    if kind == "retrieval":
        raw_hit = fixture["hit"]

        payload = RetrievalPayload(
            hits=(
                RetrievalHit(
                    rank=int(raw_hit["rank"]),
                    chunk_id=str(raw_hit["chunk_id"]),
                    evidence_id=str(raw_hit["evidence_id"]),
                    document_id=str(raw_hit["document_id"]),
                    text=str(raw_hit["text"]),
                    source_fact_ids=tuple(raw_hit["source_fact_ids"]),
                    rrf_score=float(raw_hit["rrf_score"]),
                ),
            )
        )

        result = ToolExecutionResult(
            tool="retrieval",
            status="ok",
            payload=payload,
            duration_ms=0.0,
        )

    elif kind == "retrieval_empty":
        result = ToolExecutionResult(
            tool="retrieval",
            status="empty",
            payload=RetrievalPayload(hits=()),
            duration_ms=0.0,
        )

    elif kind == "sql_value":
        result = ToolExecutionResult(
            tool="sql",
            status="ok",
            payload=StructuredPayload(
                operation=str(fixture["operation"]),
                value=fixture["value"],
                unit=fixture["unit"],
                source_rows=(_source_rows(fixture)),
            ),
            duration_ms=0.0,
        )

    elif kind == "sql_entity":
        raw_entity = fixture["entity"]

        entity = StructuredEntity(
            company_id=str(raw_entity["company_id"]),
            name=str(raw_entity["name"]),
            score=raw_entity["score"],
            canonical_fact_ids=tuple(raw_entity["canonical_fact_ids"]),
        )

        result = ToolExecutionResult(
            tool="sql",
            status="ok",
            payload=StructuredPayload(
                operation=str(fixture["operation"]),
                value=None,
                entities=(entity,),
                unit=fixture["unit"],
                source_rows=(_source_rows(fixture)),
            ),
            duration_ms=0.0,
        )

    else:
        raise RuntimeError(f"unsupported confirmation fixture kind: {kind}")

    return OrchestrationStateSnapshot(
        plan=plan,
        results=(result,),
        status="completed",
    )


def _runtime_for_case(
    case: dict[str, Any],
):
    kind = str(case["fixture"]["kind"])

    if kind == "unsupported":
        return ForbiddenRuntime()

    return FixedRuntime(_snapshot_for_case(case))


def _minimal_app(
    *,
    ordinary_service=None,
    reviewed_service=None,
) -> FastAPI:
    app = FastAPI(title=("phase13e-human-review-confirmation"))

    app.include_router(answer_router)

    app.include_router(reviewed_answer_router)

    if ordinary_service is not None:
        app.state.answering_service = ordinary_service

    if reviewed_service is not None:
        app.state.reviewed_answering_service = reviewed_service

    return app


def _response_body(
    response,
) -> dict[str, Any]:
    try:
        value = response.json()
    except Exception:
        return {
            "_raw": response.text,
        }

    if isinstance(
        value,
        dict,
    ):
        return value

    return {
        "_json": value,
    }


def _prepared_matches(
    body: dict[str, Any],
    expected: dict[str, Any],
) -> bool:
    return (
        body.get("answer_type") == expected["answer_type"]
        and body.get("answer_value") == expected["answer_value"]
        and body.get("unit") == expected["unit"]
        and body.get("supporting_record_ids") == expected["supporting_record_ids"]
        and body.get("citation_ids") == expected["citation_ids"]
        and body.get("source_fact_ids") == expected["source_fact_ids"]
    )


def _answered_matches(
    body: dict[str, Any],
    expected: dict[str, Any],
) -> bool:
    payload = body.get("payload")

    if not isinstance(
        payload,
        dict,
    ):
        return False

    return (
        body.get("status") == "answered"
        and payload.get("answer_type") == expected["answer_type"]
        and payload.get("value") == expected["answer_value"]
        and payload.get("unit") == expected["unit"]
        and body.get("citation_ids") == expected["citation_ids"]
        and body.get("provenance_fact_ids") == expected["source_fact_ids"]
    )


def _get_review(
    session_factory,
    review_id: str,
):
    with session_factory() as session:
        try:
            return HumanReviewRepository(session).get(review_id)

        except HumanReviewNotFoundError:
            return None


def _review_count(
    session_factory,
    review_id: str,
) -> int:
    with session_factory() as session:
        rows = session.execute(
            select(HumanReviewRow.review_id).where(HumanReviewRow.review_id == review_id)
        ).all()

    return len(rows)


def _all_review_ids(
    manifest: dict[str, Any],
) -> tuple[str, ...]:
    ids = [str(case["review_id"]) for case in manifest["reviewed_cases"]]

    ids.extend(str(case["review_id"]) for case in manifest["pre_review_failures"])

    for case in manifest["decision_cases"]:
        review_id = case.get("review_id")

        if review_id is not None:
            ids.append(str(review_id))

    return tuple(sorted(set(ids)))


def _cleanup_review_rows(
    session_factory,
    manifest: dict[str, Any],
) -> None:
    review_ids = _all_review_ids(manifest)

    with session_factory() as session:
        session.execute(delete(HumanReviewRow).where(HumanReviewRow.review_id.in_(review_ids)))

        session.commit()


def _ordinary_service(
    case: dict[str, Any],
):
    provider = TrackingGenerationProvider(
        str(
            case.get(
                "generation_text",
                "UNUSED",
            )
        )
    )

    service = GroundedAnsweringService(
        specification_provider=(NorthstarBoundedSpecificationProvider()),
        runtime=_runtime_for_case(case),
        generation_provider=provider,
    )

    return (
        service,
        provider,
    )


def _reviewed_service(
    *,
    case: dict[str, Any],
    session_factory,
    resume_only: bool = False,
):
    provider = TrackingGenerationProvider(
        str(
            case.get(
                "generation_text",
                "UNUSED",
            )
        )
    )

    if resume_only:
        specification_provider = ForbiddenSpecificationProvider()

        runtime = ForbiddenRuntime()

    else:
        specification_provider = NorthstarBoundedSpecificationProvider()

        runtime = _runtime_for_case(case)

    service = ReviewedAnsweringService(
        specification_provider=(specification_provider),
        runtime=runtime,
        generation_provider=provider,
        session_factory=session_factory,
    )

    return (
        service,
        provider,
    )


def _run_ordinary_case(
    case: dict[str, Any],
) -> dict[str, object]:
    service, provider = _ordinary_service(case)

    app = _minimal_app(ordinary_service=service)

    with TestClient(
        app,
        raise_server_exceptions=False,
    ) as client:
        response = client.post(
            "/answer",
            json={
                "question": (case["question"]),
            },
        )

    body = _response_body(response)

    expected = case["expected"]

    common = (
        response.status_code == 200
        and body.get("status") == expected["status"]
        and body.get("presentation_source") == expected["presentation_source"]
        and body.get("generation_fidelity") == expected["generation_fidelity"]
        and body.get("citation_ids") == expected["citation_ids"]
        and body.get("provenance_fact_ids") == expected["source_fact_ids"]
        and provider.calls == expected["generation_calls"]
    )

    if expected["status"] == "answered":
        payload = body.get("payload")

        behavior_pass = (
            common
            and isinstance(
                payload,
                dict,
            )
            and payload.get("answer_type") == expected["answer_type"]
            and payload.get("value") == expected["answer_value"]
            and payload.get("unit") == expected["unit"]
        )

    else:
        behavior_pass = common and body.get("reason") == expected["reason"]

    return {
        "case_id": case["case_id"],
        "http_status": (response.status_code),
        "service_status": (body.get("status")),
        "generation_calls": (provider.calls),
        "behavior_pass": bool(behavior_pass),
    }


def _decision_cases_for(
    manifest: dict[str, Any],
    review_case_id: str,
) -> list[dict[str, Any]]:
    return [
        case for case in manifest["decision_cases"] if case.get("review_case_id") == review_case_id
    ]


def _run_decision_probes(
    *,
    client: TestClient,
    manifest: dict[str, Any],
    review_case: dict[str, Any],
    initial_body: dict[str, Any],
) -> list[dict[str, object]]:
    results: list[dict[str, object]] = []

    for probe in _decision_cases_for(
        manifest,
        str(review_case["case_id"]),
    ):
        kind = str(probe["kind"])

        initial = str(review_case["disposition"])

        if kind.startswith("duplicate_"):
            disposition = initial
        else:
            disposition = "reject" if initial == "approve" else "approve"

        response = client.post(
            f"/reviewed-answers/{review_case['review_id']}/decision",
            json={
                "disposition": disposition,
                "reviewer_identity": (review_case["reviewer_identity"]),
            },
        )

        body = _response_body(response)

        expected_status = int(probe["expected_http_status"])

        if kind.startswith("duplicate_"):
            passed = response.status_code == expected_status and body == initial_body
        else:
            passed = response.status_code == expected_status and body.get("detail") == (
                "human review decision conflict"
            )

        results.append(
            {
                "case_id": (probe["case_id"]),
                "kind": kind,
                "http_status": (response.status_code),
                "pass": bool(passed),
            }
        )

    return results


def _run_reviewed_case(
    *,
    case: dict[str, Any],
    manifest: dict[str, Any],
    session_factory,
) -> tuple[
    dict[str, object],
    list[dict[str, object]],
]:
    service1, provider1 = _reviewed_service(
        case=case,
        session_factory=(session_factory),
    )

    app1 = _minimal_app(reviewed_service=service1)

    with TestClient(
        app1,
        raise_server_exceptions=False,
    ) as client:
        started = client.post(
            "/reviewed-answers",
            json={
                "question": (case["question"]),
                "review_id": (case["review_id"]),
            },
        )

        inspected = client.get(f"/reviewed-answers/{case['review_id']}")

        waiting = client.post(f"/reviewed-answers/{case['review_id']}/resume")

    started_body = _response_body(started)

    inspected_body = _response_body(inspected)

    waiting_body = _response_body(waiting)

    expected = case["expected_prepared"]

    awaiting = _get_review(
        session_factory,
        str(case["review_id"]),
    )

    creation_pass = (
        started.status_code == 202
        and started_body.get("status") == "awaiting_review"
        and inspected.status_code == 200
        and inspected_body.get("status") == "awaiting_review"
        and _prepared_matches(
            inspected_body,
            expected,
        )
        and awaiting is not None
        and awaiting.status == "awaiting_review"
        and _review_count(
            session_factory,
            str(case["review_id"]),
        )
        == 1
    )

    predecision_pass = (
        provider1.calls == 0
        and waiting.status_code == 200
        and waiting_body.get("status") == "awaiting_review"
    )

    restart = bool(case["restart_before_decision"])

    if restart:
        del service1
        del app1

        gc.collect()

        service2, provider2 = _reviewed_service(
            case=case,
            session_factory=(session_factory),
            resume_only=True,
        )

        app2 = _minimal_app(reviewed_service=service2)

    else:
        service2 = service1
        provider2 = provider1
        app2 = app1

    with TestClient(
        app2,
        raise_server_exceptions=False,
    ) as client:
        reloaded = client.get(f"/reviewed-answers/{case['review_id']}")

        reloaded_body = _response_body(reloaded)

        decided = client.post(
            f"/reviewed-answers/{case['review_id']}/decision",
            json={
                "disposition": (case["disposition"]),
                "reviewer_identity": (case["reviewer_identity"]),
            },
        )

        decided_body = _response_body(decided)

        decision_observations = _run_decision_probes(
            client=client,
            manifest=manifest,
            review_case=case,
            initial_body=(decided_body),
        )

        calls_before_resume = provider1.calls + provider2.calls if restart else provider1.calls

        resumed = client.post(f"/reviewed-answers/{case['review_id']}/resume")

        resumed_body = _response_body(resumed)

    persisted = _get_review(
        session_factory,
        str(case["review_id"]),
    )

    if restart:
        total_calls = provider1.calls + provider2.calls

        active_provider = provider2
    else:
        total_calls = provider1.calls

        active_provider = provider1

    decision_status = "approved" if case["disposition"] == "approve" else "rejected"

    decision_pass = (
        decided.status_code == 200
        and decided_body.get("status") == decision_status
        and calls_before_resume == 0
    )

    reload_pass = reloaded.status_code == 200 and _prepared_matches(
        reloaded_body,
        expected,
    )

    approval_pass = False
    rejection_pass = False

    authority_pass = False

    if case["disposition"] == "approve":
        authority_request = active_provider.last_request

        authority_pass = (
            authority_request is not None
            and authority_request.authority.answer_type == expected["answer_type"]
            and authority_request.authority.value == expected["answer_value"]
            and authority_request.authority.unit == expected["unit"]
            and list(authority_request.authority.supporting_record_ids)
            == expected["supporting_record_ids"]
            and list(authority_request.authority.source_fact_ids) == expected["source_fact_ids"]
            and list(authority_request.allowed_citation_ids) == expected["citation_ids"]
        )

        approval_pass = (
            decision_pass
            and persisted is not None
            and persisted.status == "approved"
            and total_calls == 1
            and authority_pass
            and resumed.status_code == 200
            and _answered_matches(
                resumed_body,
                expected,
            )
        )

        citation_pass = (
            persisted is not None
            and list(persisted.citation_ids) == expected["citation_ids"]
            and resumed_body.get("citation_ids") == expected["citation_ids"]
        )

        provenance_pass = (
            persisted is not None
            and list(persisted.source_fact_ids) == expected["source_fact_ids"]
            and resumed_body.get("provenance_fact_ids") == expected["source_fact_ids"]
        )

    else:
        rejection_pass = (
            decision_pass
            and persisted is not None
            and persisted.status == "rejected"
            and total_calls == 0
            and resumed.status_code == 200
            and resumed_body.get("status") == "human_rejected"
            and "payload" not in resumed_body
        )

        citation_pass = (
            persisted is not None
            and list(persisted.citation_ids) == expected["citation_ids"]
            and "citation_ids" not in resumed_body
        )

        provenance_pass = (
            persisted is not None
            and list(persisted.source_fact_ids) == expected["source_fact_ids"]
            and "provenance_fact_ids" not in resumed_body
        )

    restart_pass = (
        reload_pass
        and decision_pass
        and (approval_pass if case["disposition"] == "approve" else rejection_pass)
    )

    observation = {
        "case_id": case["case_id"],
        "disposition": case["disposition"],
        "restart_case": restart,
        "start_http_status": (started.status_code),
        "decision_http_status": (decided.status_code),
        "resume_http_status": (resumed.status_code),
        "generation_calls": (total_calls),
        "checks": {
            "review_creation": bool(creation_pass),
            "pre_decision_generation_suppression": bool(predecision_pass),
            "approval_continuation": bool(approval_pass),
            "rejection_enforcement": bool(rejection_pass),
            "citation_integrity": bool(citation_pass),
            "provenance_integrity": bool(provenance_pass),
            "restart_resume": bool(restart_pass),
            "exact_persisted_authority_reused": bool(authority_pass),
        },
    }

    return (
        observation,
        decision_observations,
    )


def _run_pre_review_failure(
    *,
    case: dict[str, Any],
    session_factory,
) -> dict[str, object]:
    service, provider = _reviewed_service(
        case=case,
        session_factory=(session_factory),
    )

    app = _minimal_app(reviewed_service=service)

    with TestClient(
        app,
        raise_server_exceptions=False,
    ) as client:
        response = client.post(
            "/reviewed-answers",
            json={
                "question": (case["question"]),
                "review_id": (case["review_id"]),
            },
        )

    body = _response_body(response)

    expected = case["expected"]

    preserved = (
        response.status_code == expected["http_status"]
        and body.get("status") == expected["status"]
        and body.get("reason") == expected["reason"]
        and body.get("presentation_source") == expected["presentation_source"]
        and body.get("generation_fidelity") == expected["generation_fidelity"]
        and body.get("citation_ids") == expected["citation_ids"]
        and body.get("provenance_fact_ids") == expected["source_fact_ids"]
        and provider.calls == 0
        and _review_count(
            session_factory,
            str(case["review_id"]),
        )
        == 0
    )

    return {
        "case_id": case["case_id"],
        "http_status": (response.status_code),
        "service_status": (body.get("status")),
        "reason": body.get("reason"),
        "generation_calls": (provider.calls),
        "checks": {
            "pre_review_failure_preservation": bool(preserved),
        },
    }


def _run_unknown_decision(
    *,
    manifest: dict[str, Any],
    session_factory,
) -> dict[str, object]:
    probe = next(case for case in manifest["decision_cases"] if case["kind"] == "unknown_review_id")

    seed = manifest["reviewed_cases"][0]

    service, _provider = _reviewed_service(
        case=seed,
        session_factory=(session_factory),
        resume_only=True,
    )

    app = _minimal_app(reviewed_service=service)

    with TestClient(
        app,
        raise_server_exceptions=False,
    ) as client:
        response = client.post(
            f"/reviewed-answers/{probe['review_id']}/decision",
            json={
                "disposition": ("approve"),
                "reviewer_identity": ("phase13e1-caller-reviewer"),
            },
        )

    body = _response_body(response)

    return {
        "case_id": probe["case_id"],
        "kind": probe["kind"],
        "http_status": (response.status_code),
        "pass": bool(
            response.status_code == probe["expected_http_status"]
            and body.get("detail") == "human review not found"
        ),
    }


def _score(
    *,
    metric_spec: dict[str, Any],
    observations: dict[
        str,
        dict[str, Any],
    ],
    check: str,
) -> dict[str, object]:
    case_ids = list(metric_spec["case_ids"])

    values = [bool(observations[case_id]["checks"][check]) for case_id in case_ids]

    passed = sum(values)

    total = len(values)

    if total != metric_spec["denominator"]:
        raise RuntimeError("measurement denominator does not match frozen manifest")

    rate = passed / total if total else 0.0

    threshold = float(metric_spec["threshold"])

    return {
        "passed": passed,
        "total": total,
        "rate": rate,
        "threshold": threshold,
        "promotion_met": (rate >= threshold),
        "case_ids": case_ids,
    }


def run_phase13e1_confirmation(
    *,
    case_manifest_path: Path = (DEFAULT_CASE_MANIFEST_PATH),
    freeze_manifest_path: Path = (DEFAULT_FREEZE_MANIFEST_PATH),
) -> dict[str, object]:
    manifest, freeze = load_frozen_inputs(
        case_manifest_path=(case_manifest_path),
        freeze_manifest_path=(freeze_manifest_path),
    )

    inspector = sqlalchemy_inspect(engine)

    if not inspector.has_table("human_review_requests"):
        raise RuntimeError(
            "Phase 13E1 requires the frozen human-review PostgreSQL schema to be upgraded."
        )

    session_factory = sessionmaker(
        bind=engine,
        expire_on_commit=False,
    )

    _cleanup_review_rows(
        session_factory,
        manifest,
    )

    ordinary_observations: list[dict[str, object]] = []

    reviewed_observations: list[dict[str, object]] = []

    failure_observations: list[dict[str, object]] = []

    decision_observations: list[dict[str, object]] = []

    try:
        for case in manifest["ordinary_controls"]:
            ordinary_observations.append(_run_ordinary_case(case))

        for case in manifest["reviewed_cases"]:
            (
                observation,
                probes,
            ) = _run_reviewed_case(
                case=case,
                manifest=manifest,
                session_factory=(session_factory),
            )

            reviewed_observations.append(observation)

            decision_observations.extend(probes)

        for case in manifest["pre_review_failures"]:
            failure_observations.append(
                _run_pre_review_failure(
                    case=case,
                    session_factory=(session_factory),
                )
            )

        decision_observations.append(
            _run_unknown_decision(
                manifest=manifest,
                session_factory=(session_factory),
            )
        )

        reviewed_by_id = {
            str(observation["case_id"]): observation for observation in reviewed_observations
        }

        failure_by_id = {
            str(observation["case_id"]): observation for observation in failure_observations
        }

        decision_by_id = {
            str(observation["case_id"]): observation for observation in decision_observations
        }

        specs = manifest["locked_metrics"]

        metrics = {
            "review_creation_accuracy": _score(
                metric_spec=specs["review_creation_accuracy"],
                observations=(reviewed_by_id),
                check="review_creation",
            ),
            "pre_decision_generation_suppression": _score(
                metric_spec=specs["pre_decision_generation_suppression"],
                observations=(reviewed_by_id),
                check=("pre_decision_generation_suppression"),
            ),
            "approval_continuation_accuracy": _score(
                metric_spec=specs["approval_continuation_accuracy"],
                observations=(reviewed_by_id),
                check=("approval_continuation"),
            ),
            "rejection_enforcement_rate": _score(
                metric_spec=specs["rejection_enforcement_rate"],
                observations=(reviewed_by_id),
                check=("rejection_enforcement"),
            ),
            "pre_review_failure_preservation": _score(
                metric_spec=specs["pre_review_failure_preservation"],
                observations=(failure_by_id),
                check=("pre_review_failure_preservation"),
            ),
            "citation_integrity": _score(
                metric_spec=specs["citation_integrity"],
                observations=(reviewed_by_id),
                check=("citation_integrity"),
            ),
            "provenance_integrity": _score(
                metric_spec=specs["provenance_integrity"],
                observations=(reviewed_by_id),
                check=("provenance_integrity"),
            ),
            "decision_conflict_enforcement": _score(
                metric_spec=specs["decision_conflict_enforcement"],
                observations=(
                    {
                        case_id: {"checks": {"decision_conflict": (observation["pass"])}}
                        for (
                            case_id,
                            observation,
                        ) in decision_by_id.items()
                    }
                ),
                check=("decision_conflict"),
            ),
            "restart_resume_accuracy": _score(
                metric_spec=specs["restart_resume_accuracy"],
                observations=(reviewed_by_id),
                check=("restart_resume"),
            ),
        }

        ordinary_pass = all(
            bool(observation["behavior_pass"]) for observation in ordinary_observations
        )

        decision_controls_pass = all(
            bool(observation["pass"]) for observation in decision_observations
        )

        locked_metrics_pass = all(bool(metric["promotion_met"]) for metric in metrics.values())

        promotion = {
            "locked_metrics_pass": (locked_metrics_pass),
            "ordinary_regression_controls_pass": (ordinary_pass),
            "decision_behavior_controls_pass": (decision_controls_pass),
            "eligible": bool(locked_metrics_pass and ordinary_pass and decision_controls_pass),
        }

        return {
            "confirmation_version": (PHASE13E_CONFIRMATION_VERSION),
            "measurement_status": ("measured"),
            "environment": {
                "database": (engine.dialect.name),
                "database_required": True,
                "http_boundary_exercised": True,
                "network_required": False,
                "real_language_model_required": False,
                "generation_provider": ("deterministic_confirmation_provider"),
                "timing_fields_included": False,
            },
            "anchors": {
                "freeze_manifest": {
                    "canonical_sha256": (freeze["canonical_sha256"]),
                },
                "case_manifest": (freeze["case_manifest"]),
                "phase13a": (freeze["phase13a"]),
                "phase13b": (freeze["phase13b"]),
                "phase13c": (freeze["phase13c"]),
                "phase13d": (freeze["phase13d"]),
            },
            "metrics": metrics,
            "promotion": promotion,
            "ordinary_controls": (ordinary_observations),
            "reviewed_cases": (reviewed_observations),
            "pre_review_failures": (failure_observations),
            "decision_cases": (decision_observations),
        }

    finally:
        _cleanup_review_rows(
            session_factory,
            manifest,
        )


def write_phase13e1_confirmation(
    *,
    result_path: Path = (DEFAULT_RESULT_PATH),
    case_manifest_path: Path = (DEFAULT_CASE_MANIFEST_PATH),
    freeze_manifest_path: Path = (DEFAULT_FREEZE_MANIFEST_PATH),
) -> tuple[
    dict[str, object],
    str,
]:
    if result_path.exists():
        raise FileExistsError("Refusing to overwrite an existing Phase 13E1 confirmation artifact.")

    report = run_phase13e1_confirmation(
        case_manifest_path=(case_manifest_path),
        freeze_manifest_path=(freeze_manifest_path),
    )

    digest = report_sha256(report)

    artifact = {
        **report,
        "report_canonical_sha256": (digest),
    }

    result_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    result_path.write_bytes(deterministic_report_bytes(artifact))

    return (
        artifact,
        digest,
    )


def main() -> None:
    artifact, digest = write_phase13e1_confirmation()

    print(f"PHASE13E1_REVIEWED_CASE_COUNT={len(artifact['reviewed_cases'])}")

    print(f"PHASE13E1_CANONICAL_SHA256={digest}")

    print(f"PHASE13E1_PROMOTION_ELIGIBLE={artifact['promotion']['eligible']}")

    print(f"PHASE13E1_RESULT_PATH={DEFAULT_RESULT_PATH}")


if __name__ == "__main__":
    main()
