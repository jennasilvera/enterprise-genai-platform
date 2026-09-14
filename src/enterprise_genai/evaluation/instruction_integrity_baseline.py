from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from enterprise_genai.answering.evidence import (
    evidence_bundle_from_snapshot,
    unsupported_request_bundle,
)
from enterprise_genai.answering.outcomes import (
    GroundedAnswer,
)
from enterprise_genai.answering.sufficiency import (
    evaluate_sufficiency,
)
from enterprise_genai.answering.synthesis import (
    SynthesisInstruction,
    synthesize_answer,
)
from enterprise_genai.application.answering import (
    AnswerRequest,
)
from enterprise_genai.application.northstar_specification import (
    NorthstarBoundedSpecificationProvider,
)
from enterprise_genai.application.specification import (
    ExecutableAnswerSpecification,
    UnsupportedAnswerSpecification,
)
from enterprise_genai.execution.contracts import (
    RetrievalHit,
    RetrievalPayload,
    RetrievalQuery,
    ToolExecutionResult,
)
from enterprise_genai.generation.contracts import (
    GenerationAuthority,
    GroundedGenerationRequest,
    generation_request_from_outcome,
)
from enterprise_genai.generation.guarded import (
    render_deterministic_authority,
)
from enterprise_genai.orchestration.langgraph_runtime import (
    BoundedLangGraphRuntime,
)

PHASE12B_BASELINE_VERSION = "northstar-instruction-integrity-phase12b-unguarded-baseline-v2"

PHASE12B_AUTHORITY_EXPOSURE_METRIC_VERSION = "raw-string-leaf-exact-span-v2"

PHASE12B_MANIFEST_VERSION = "northstar-instruction-integrity-phase12b-case-manifest-v1"

PHASE12B_MANIFEST_CANONICAL_SHA256 = (
    "20a5fcfe0a7ab41cabe36d3503dabf9828ffa65753c8c747cdfd3974afe224b8"
)

PHASE12B_MANIFEST_FILE_SHA256 = "af91e9ede94085d8b9d1f713506520b1e882a6da64a7bcdb59a4c8352576f924"

DEFAULT_MANIFEST_PATH = Path(
    "artifacts/evaluation/phase12b/instruction_integrity_case_manifest.json"
)

DEFAULT_RESULT_PATH = Path("artifacts/evaluation/phase12b/instruction_integrity_baseline.json")


def _canonical_bytes(value: object) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


def deterministic_report_bytes(
    report: dict[str, object],
) -> bytes:
    return _canonical_bytes(report)


def report_sha256(
    report: dict[str, object],
) -> str:
    return hashlib.sha256(deterministic_report_bytes(report)).hexdigest()


def _file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_frozen_manifest(
    path: Path = DEFAULT_MANIFEST_PATH,
) -> dict[str, Any]:
    if _file_sha256(path) != PHASE12B_MANIFEST_FILE_SHA256:
        raise ValueError("Phase 12B baseline requires the exact frozen manifest bytes.")

    manifest: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))

    if manifest.get("manifest_version") != PHASE12B_MANIFEST_VERSION:
        raise ValueError("Phase 12B manifest version does not match the frozen contract.")

    stored_sha = manifest.get("canonical_sha256")

    canonical_payload = {key: value for key, value in manifest.items() if key != "canonical_sha256"}

    observed_sha = hashlib.sha256(_canonical_bytes(canonical_payload)).hexdigest()

    if stored_sha != PHASE12B_MANIFEST_CANONICAL_SHA256:
        raise ValueError("Phase 12B manifest stored SHA does not match the frozen contract.")

    if observed_sha != PHASE12B_MANIFEST_CANONICAL_SHA256:
        raise ValueError("Phase 12B manifest canonical payload drifted.")

    return manifest


class InjectedRetrievalExecutor:
    """Evaluation-only retrieval seam for one frozen adversarial case."""

    def __init__(
        self,
        *,
        question: str,
        hits: tuple[RetrievalHit, ...],
    ) -> None:
        self._question = question
        self._hits = hits
        self.observed_queries: list[RetrievalQuery] = []

    def execute(
        self,
        query: RetrievalQuery,
    ) -> ToolExecutionResult:
        if query.question != self._question:
            raise ValueError("Injected retrieval executor received a different question.")

        self.observed_queries.append(query)

        return ToolExecutionResult(
            tool="retrieval",
            status="ok",
            payload=RetrievalPayload(
                hits=self._hits,
            ),
            duration_ms=0.0,
        )


def _string_leaves(
    value: object,
) -> tuple[str, ...]:
    """Return raw string leaves without serialization transforms."""

    if isinstance(value, str):
        return (value,)

    if isinstance(value, dict):
        return tuple(leaf for child in value.values() for leaf in _string_leaves(child))

    if isinstance(
        value,
        (
            list,
            tuple,
        ),
    ):
        return tuple(leaf for child in value for leaf in _string_leaves(child))

    return ()


def _contains_any(
    *,
    value: object,
    spans: tuple[str, ...],
) -> bool:
    """Match exact registered spans against raw string leaves."""

    if not spans:
        return False

    leaves = _string_leaves(value)

    return any(span in leaf for span in spans for leaf in leaves)


def _selected_source_fact_ids(
    request: GroundedGenerationRequest,
) -> tuple[str, ...]:
    return tuple(
        sorted({fact_id for evidence in request.evidence for fact_id in evidence.source_fact_ids})
    )


def _authority_fields(
    authority: GenerationAuthority,
) -> dict[str, object]:
    dumped = authority.model_dump(mode="json")

    return {
        "authority_outcome": authority.outcome,
        "authority_answer_type": (authority.answer_type if authority.outcome == "answer" else None),
        "authority_value": dumped.get("value"),
        "authority_reason": dumped.get("reason"),
        "authority_missing_information": list(authority.missing_information),
        "authority_supporting_record_ids": list(authority.supporting_record_ids),
        "authority_source_fact_ids": list(authority.source_fact_ids),
    }


def _rate(
    *,
    numerator: int,
    denominator: int,
) -> dict[str, object]:
    return {
        "numerator": numerator,
        "denominator": denominator,
        "rate": (numerator / denominator if denominator else None),
    }


def _run_case(
    case: dict[str, Any],
) -> dict[str, object]:
    question = str(case["question"])

    request = AnswerRequest(question=question)

    provider = NorthstarBoundedSpecificationProvider()

    specification = provider.prepare(request)

    expected_kind = case["expected_specification_kind"]

    expected_route = case["expected_route_label"]

    expected_tools = tuple(case["expected_planned_tools"])

    expected_plan = case["expected_plan"]

    retrieved_evidence_ids: tuple[str, ...] = ()

    if isinstance(
        specification,
        UnsupportedAnswerSpecification,
    ):
        actual_kind = "unsupported"
        actual_route = None
        actual_tools: tuple[str, ...] = ()
        actual_plan = None

        bundle = unsupported_request_bundle(
            question=question,
            detail=specification.detail,
        )

        requirements = ()
        synthesis = None

    elif isinstance(
        specification,
        ExecutableAnswerSpecification,
    ):
        actual_kind = "executable"

        execution_plan = specification.orchestration_plan.execution_plan

        actual_route = execution_plan.route_label

        actual_tools = tuple(execution_plan.required_tools())

        actual_plan = execution_plan.model_dump(mode="json")

        hits = tuple(RetrievalHit.model_validate(raw) for raw in case["retrieval_hits"])

        retriever = InjectedRetrievalExecutor(
            question=question,
            hits=hits,
        )

        runtime = BoundedLangGraphRuntime(
            retrieval_executor=retriever,
        )

        snapshot = runtime.execute(specification.orchestration_plan)

        if len(retriever.observed_queries) != 1:
            raise RuntimeError("Expected exactly one retrieval execution.")

        bundle = evidence_bundle_from_snapshot(snapshot)

        requirements = specification.requirements

        synthesis = specification.synthesis

        retrieved_evidence_ids = tuple(hit.evidence_id for hit in hits)

    else:
        raise TypeError("Unsupported specification type.")

    plan_integrity_pass = (
        actual_kind == expected_kind
        and actual_route == expected_route
        and actual_tools == expected_tools
        and actual_plan == expected_plan
    )

    assessment = evaluate_sufficiency(
        bundle=bundle,
        requirements=requirements,
    )

    if assessment.status == "sufficient":
        if synthesis is None:
            raise RuntimeError("Sufficient evidence requires synthesis metadata.")

        outcome = synthesize_answer(
            assessment=assessment,
            instruction=SynthesisInstruction(
                mode=synthesis.mode,
                answer_type=synthesis.answer_type,
                answer_record_ids=(assessment.supporting_record_ids),
            ),
        )
    else:
        outcome = synthesize_answer(assessment=assessment)

    generation_request = generation_request_from_outcome(
        question=question,
        outcome=outcome,
    )

    authority = generation_request.authority

    presentation_text = render_deterministic_authority(authority)

    spans = tuple(case["disallowed_payload_spans"])

    authority_exposed = _contains_any(
        value=authority.model_dump(mode="json"),
        spans=spans,
    )

    presentation_exposed = _contains_any(
        value=presentation_text,
        spans=spans,
    )

    citation_integrity_pass = (
        generation_request.allowed_citation_ids
        == authority.supporting_record_ids
        == assessment.supporting_record_ids
    )

    expected_source_facts = _selected_source_fact_ids(generation_request)

    provenance_integrity_pass = authority.source_fact_ids == expected_source_facts

    requires_safe_failure = bool(case["requires_safe_failure"])

    # Phase 12B records existing abstention behavior only.
    # The formal typed safe-failure disposition is defined
    # and frozen later by the Phase 12C policy contract.
    baseline_abstention_observed = authority.outcome == "abstain"

    outcome_kind = "answer" if isinstance(outcome, GroundedAnswer) else "abstain"

    return {
        "case_id": case["case_id"],
        "family": case["family"],
        "scenario": case["scenario"],
        "case_kind": case["case_kind"],
        "question": question,
        "manifest_expectation": {
            "specification_kind": expected_kind,
            "route_label": expected_route,
            "planned_tools": list(expected_tools),
            "requires_safe_failure": (requires_safe_failure),
            "authority_exposure_permitted": bool(case["authority_exposure_permitted"]),
            "presentation_exposure_permitted": bool(case["presentation_exposure_permitted"]),
            "disallowed_payload_spans": list(spans),
        },
        "execution": {
            "specification_kind": actual_kind,
            "route_label": actual_route,
            "planned_tools": list(actual_tools),
            "plan_integrity_pass": (plan_integrity_pass),
            "retrieved_evidence_ids": list(retrieved_evidence_ids),
        },
        "evidence": {
            "bundle_status": bundle.status,
            "record_ids": [record.record_id for record in bundle.records],
            "sufficiency_status": (assessment.status),
            "sufficiency_reason": (assessment.reason),
            "supporting_record_ids": list(assessment.supporting_record_ids),
            "missing_information": list(assessment.missing_information),
        },
        "outcome": {
            "kind": outcome_kind,
            **_authority_fields(authority),
        },
        "generation_contract": {
            "allowed_citation_ids": list(generation_request.allowed_citation_ids),
            "selected_evidence_ids": [
                evidence.record_id for evidence in generation_request.evidence
            ],
            "citation_integrity_pass": (citation_integrity_pass),
            "provenance_integrity_pass": (provenance_integrity_pass),
        },
        "presentation": {
            "mode": "deterministic_authority_renderer",
            "text": presentation_text,
        },
        "metrics": {
            "authority_payload_exposed": (authority_exposed),
            "presentation_payload_exposed": (presentation_exposed),
            "baseline_abstention_observed": (baseline_abstention_observed),
        },
    }


def run_phase12b_baseline(
    *,
    manifest_path: Path = DEFAULT_MANIFEST_PATH,
) -> dict[str, object]:
    manifest = load_frozen_manifest(manifest_path)

    observations = [_run_case(case) for case in manifest["cases"]]

    total = len(observations)

    plan_passed = sum(
        bool(observation["execution"]["plan_integrity_pass"]) for observation in observations
    )

    authority_population = [
        observation
        for observation in observations
        if not observation["manifest_expectation"]["authority_exposure_permitted"]
    ]

    authority_exposed = sum(
        bool(observation["metrics"]["authority_payload_exposed"])
        for observation in authority_population
    )

    presentation_population = [
        observation
        for observation in observations
        if not observation["manifest_expectation"]["presentation_exposure_permitted"]
    ]

    presentation_exposed = sum(
        bool(observation["metrics"]["presentation_payload_exposed"])
        for observation in presentation_population
    )

    citation_passed = sum(
        bool(observation["generation_contract"]["citation_integrity_pass"])
        for observation in observations
    )

    provenance_passed = sum(
        bool(observation["generation_contract"]["provenance_integrity_pass"])
        for observation in observations
    )

    safe_failure_designated_population = [
        observation
        for observation in observations
        if observation["manifest_expectation"]["requires_safe_failure"]
    ]

    baseline_abstentions = sum(
        bool(observation["metrics"]["baseline_abstention_observed"])
        for observation in (safe_failure_designated_population)
    )

    clean_reference = [
        {
            "case_id": observation["case_id"],
            "authority": observation["outcome"],
            "presentation": observation["presentation"],
            "allowed_citation_ids": observation["generation_contract"]["allowed_citation_ids"],
        }
        for observation in observations
        if observation["case_kind"] == "clean_control"
    ]

    return {
        "baseline_version": (PHASE12B_BASELINE_VERSION),
        "baseline_type": ("current_unguarded_deterministic_authority_path"),
        "authority_exposure_metric_version": (PHASE12B_AUTHORITY_EXPOSURE_METRIC_VERSION),
        "model_generation_invoked": False,
        "network_required": False,
        "timing_fields_included": False,
        "manifest": {
            "version": (PHASE12B_MANIFEST_VERSION),
            "canonical_sha256": (PHASE12B_MANIFEST_CANONICAL_SHA256),
            "file_sha256": (PHASE12B_MANIFEST_FILE_SHA256),
            "case_count": manifest["case_count"],
        },
        "metrics": {
            "plan_integrity": _rate(
                numerator=plan_passed,
                denominator=total,
            ),
            "authority_instruction_exposure": _rate(
                numerator=authority_exposed,
                denominator=len(authority_population),
            ),
            "presentation_instruction_exposure": _rate(
                numerator=(presentation_exposed),
                denominator=len(presentation_population),
            ),
            "citation_integrity": _rate(
                numerator=citation_passed,
                denominator=total,
            ),
            "provenance_integrity": _rate(
                numerator=provenance_passed,
                denominator=total,
            ),
            "safe_failure": {
                "status": ("not_scored_pre_phase12c_policy"),
                "designated_cases": len(safe_failure_designated_population),
                "baseline_abstentions": (baseline_abstentions),
                "rate": None,
            },
            "clean_answer_retention": {
                "status": ("baseline_reference_only"),
                "rate": None,
            },
        },
        "clean_reference": clean_reference,
        "cases": observations,
    }


def write_phase12b_baseline(
    *,
    result_path: Path = DEFAULT_RESULT_PATH,
    manifest_path: Path = DEFAULT_MANIFEST_PATH,
) -> tuple[dict[str, object], str]:
    if result_path.exists():
        raise FileExistsError("Refusing to overwrite an existing Phase 12B baseline artifact.")

    report = run_phase12b_baseline(manifest_path=manifest_path)

    digest = report_sha256(report)

    artifact = {
        **report,
        "report_canonical_sha256": digest,
    }

    result_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    result_path.write_text(
        json.dumps(
            artifact,
            indent=2,
            sort_keys=True,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )

    return artifact, digest


def main() -> None:
    artifact, digest = write_phase12b_baseline()

    print(f"BASELINE_CASE_COUNT={artifact['manifest']['case_count']}")

    print(f"BASELINE_CANONICAL_SHA256={digest}")

    print(f"BASELINE_RESULT_PATH={DEFAULT_RESULT_PATH}")


if __name__ == "__main__":
    main()
