from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import get_args

from enterprise_genai.answering.instruction_integrity import (
    _RULES,
    INSTRUCTION_INTEGRITY_BLOCK_DETAIL,
    INSTRUCTION_INTEGRITY_BLOCK_REASON,
    INSTRUCTION_INTEGRITY_BLOCK_TEXT,
    INSTRUCTION_INTEGRITY_POLICY_VERSION,
    InstructionIntegrityViolationCode,
)

PHASE12C_POLICY_CONTRACT_VERSION = "northstar-instruction-integrity-phase12c-policy-contract-v1"

PHASE12C_PARENT_COMMIT = "1fdf6b661d343356a2bc1901eb8caef9cd036673"

PHASE12A_PROTOCOL_TAG = "phase-12a-instruction-integrity-protocol"

PHASE12A_PROTOCOL_COMMIT = "f18d48703ee89e0d193b3621c08746d04a106d4b"

PHASE12A_PROTOCOL_SHA256 = "0a52c1daf1f439ed6977a834305f5bff9a2256d25b0153118d1bd90f4a8516f2"

PHASE12B_MANIFEST_TAG = "phase-12b0-instruction-integrity-case-manifest"

PHASE12B_MANIFEST_COMMIT = "a1f3d8703899e0b414e45fb830e1c59196b5af7e"

PHASE12B_MANIFEST_CANONICAL_SHA256 = (
    "20a5fcfe0a7ab41cabe36d3503dabf9828ffa65753c8c747cdfd3974afe224b8"
)

PHASE12B_MANIFEST_FILE_SHA256 = "af91e9ede94085d8b9d1f713506520b1e882a6da64a7bcdb59a4c8352576f924"

PHASE12B_BASELINE_TAG = "phase-12b4-instruction-integrity-baseline-v2"

PHASE12B_BASELINE_COMMIT = "af379f07af2678206672c0a6894acbc0615b66a3"

PHASE12B_BASELINE_CANONICAL_SHA256 = (
    "47a095e3c264398b7e3ed3beca1697cd9e2cb5f738ff2d955cc0ab7e80923f78"
)

PHASE12B_BASELINE_FILE_SHA256 = "a2149e2bb1b7ae248e4bc4c76dd06c323be6e12cce1d3d2278b7ce9a84e95955"

EXPECTED_SOURCE_SHA256 = {
    ("src/enterprise_genai/answering/instruction_integrity.py"): (
        "647170957b86b6ddc89fbcb2396b66931f7c30032a075f9187ff79d267dacbd1"
    ),
    ("src/enterprise_genai/application/service.py"): (
        "37dd9b68f91e493db5cc349311aa08da2ad9f6de42d38299b45b455c846cb6cc"
    ),
    ("tests/unit/test_instruction_integrity_policy.py"): (
        "57f4cf95b6cf659fc1191171b928676f60600566b908b63def527fd2887ca01f"
    ),
    ("tests/unit/test_application_service.py"): (
        "84caf940ffd8dff27e762767b6eb7fa1689c92630019eefda0a7f90487bea393"
    ),
}


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _file_sha256(
    path: Path,
) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical_contract_bytes(
    contract: dict[str, object],
) -> bytes:
    payload = dict(contract)

    payload.pop(
        "canonical_sha256",
        None,
    )

    return json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


def contract_sha256(
    contract: dict[str, object],
) -> str:
    return hashlib.sha256(canonical_contract_bytes(contract)).hexdigest()


def _verified_source_hashes() -> dict[str, str]:
    root = _repo_root()

    observed: dict[str, str] = {}

    for relative, expected in sorted(EXPECTED_SOURCE_SHA256.items()):
        digest = _file_sha256(root / relative)

        if digest != expected:
            raise RuntimeError(
                "Phase 12C reviewed source drifted: "
                f"{relative}: "
                f"expected {expected}, "
                f"observed {digest}"
            )

        observed[relative] = digest

    return observed


def build_policy_contract() -> dict[str, object]:
    source_hashes = _verified_source_hashes()

    violation_codes = tuple(sorted(get_args(InstructionIntegrityViolationCode)))

    rules = tuple(
        {
            "violation_code": code,
            "pattern": pattern.pattern,
        }
        for code, pattern in _RULES
    )

    payload: dict[str, object] = {
        "contract_version": (PHASE12C_POLICY_CONTRACT_VERSION),
        "phase12c_parent_commit": (PHASE12C_PARENT_COMMIT),
        "policy_version": (INSTRUCTION_INTEGRITY_POLICY_VERSION),
        "scope": {
            "required_assessment_status": ("sufficient"),
            "record_selection": ("assessment.supporting_record_ids"),
            "inspected_record_tool": ("retrieval"),
            "inspected_record_kind": ("retrieval_hit"),
            "unselected_retrieval_records": ("not_inspected"),
            "structured_sql_graph_records": ("outside_this_policy"),
        },
        "normalization": {
            "casefold": True,
            "collapse_whitespace": True,
            "semantic_model": False,
            "probabilistic_classifier": False,
        },
        "decision_contract": {
            "dispositions": [
                "allow",
                "block",
            ],
            "policy_result_contains_source_text": (False),
            "blocked_record_ids_must_be_subset_of_inspected": (True),
            "deterministic_sorted_ids": True,
            "deterministic_sorted_violation_codes": (True),
        },
        "violation_codes": list(violation_codes),
        "rules": list(rules),
        "safe_failure": {
            "trigger": ("decision.disposition == block"),
            "service_status": ("abstained"),
            "reason": (INSTRUCTION_INTEGRITY_BLOCK_REASON),
            "detail": (INSTRUCTION_INTEGRITY_BLOCK_DETAIL),
            "presentation_text": (INSTRUCTION_INTEGRITY_BLOCK_TEXT),
            "presentation_source": ("deterministic"),
            "generation_fidelity": ("not_applicable"),
            "synthesis_invoked": False,
            "generation_authority_created": (False),
            "generation_invoked": False,
            "citation_ids": ("selected supporting record IDs"),
            "provenance_fact_ids": ("canonical source-fact union of selected support"),
            "retrieval_text_exposed_in_policy_result": (False),
            "retrieval_text_exposed_in_presentation": (False),
        },
        "claim_boundary": {
            "complete_prompt_injection_detector": (False),
            "universal_jailbreak_prevention": (False),
            "comprehensive_responsible_ai_guardrail": (False),
            "intended_claim": (
                "typed deterministic instruction-integrity "
                "boundary for selected natural-language "
                "retrieval evidence before deterministic "
                "answer authority"
            ),
        },
        "phase12a_protocol": {
            "tag": PHASE12A_PROTOCOL_TAG,
            "commit": (PHASE12A_PROTOCOL_COMMIT),
            "sha256": (PHASE12A_PROTOCOL_SHA256),
        },
        "phase12b_manifest": {
            "tag": PHASE12B_MANIFEST_TAG,
            "commit": (PHASE12B_MANIFEST_COMMIT),
            "canonical_sha256": (PHASE12B_MANIFEST_CANONICAL_SHA256),
            "file_sha256": (PHASE12B_MANIFEST_FILE_SHA256),
        },
        "phase12b_baseline": {
            "tag": PHASE12B_BASELINE_TAG,
            "commit": (PHASE12B_BASELINE_COMMIT),
            "canonical_sha256": (PHASE12B_BASELINE_CANONICAL_SHA256),
            "file_sha256": (PHASE12B_BASELINE_FILE_SHA256),
        },
        "reviewed_source_sha256": (source_hashes),
    }

    digest = contract_sha256(payload)

    return {
        **payload,
        "canonical_sha256": digest,
    }


def deterministic_contract_bytes(
    contract: dict[str, object],
) -> bytes:
    return (
        json.dumps(
            contract,
            indent=2,
            sort_keys=True,
            ensure_ascii=False,
        )
        + "\n"
    ).encode("utf-8")


def write_policy_contract(
    *,
    output_path: Path,
) -> tuple[
    dict[str, object],
    str,
]:
    if output_path.exists():
        raise FileExistsError("Refusing to overwrite existing Phase 12C policy contract.")

    contract = build_policy_contract()

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    output_path.write_bytes(deterministic_contract_bytes(contract))

    return (
        contract,
        contract["canonical_sha256"],
    )


def main() -> None:
    output = (
        _repo_root() / "artifacts/evaluation/phase12c/instruction_integrity_policy_contract.json"
    )

    contract, digest = write_policy_contract(output_path=output)

    print(f"PHASE12C_POLICY_VERSION={contract['policy_version']}")

    print(f"PHASE12C_POLICY_RULE_COUNT={len(contract['rules'])}")

    print(f"PHASE12C_POLICY_CONTRACT_CANONICAL_SHA256={digest}")

    print(f"PHASE12C_POLICY_CONTRACT_PATH={output.relative_to(_repo_root())}")


if __name__ == "__main__":
    main()
