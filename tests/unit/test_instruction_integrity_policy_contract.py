from __future__ import annotations

import hashlib
import json

from enterprise_genai.evaluation.instruction_integrity_policy_contract import (
    EXPECTED_SOURCE_SHA256,
    PHASE12C_POLICY_CONTRACT_VERSION,
    build_policy_contract,
    canonical_contract_bytes,
    contract_sha256,
    deterministic_contract_bytes,
)


def test_policy_contract_is_deterministic() -> None:
    first = build_policy_contract()
    second = build_policy_contract()

    assert first == second

    assert deterministic_contract_bytes(first) == deterministic_contract_bytes(second)


def test_policy_contract_canonical_digest() -> None:
    contract = build_policy_contract()

    observed = hashlib.sha256(canonical_contract_bytes(contract)).hexdigest()

    assert contract["canonical_sha256"] == observed

    assert contract_sha256(contract) == observed


def test_policy_contract_records_exact_v1_boundary() -> None:
    contract = build_policy_contract()

    assert contract["contract_version"] == PHASE12C_POLICY_CONTRACT_VERSION

    assert contract["policy_version"] == ("northstar-selected-retrieval-instruction-integrity-v1")

    scope = contract["scope"]

    assert scope == {
        "required_assessment_status": ("sufficient"),
        "record_selection": ("assessment.supporting_record_ids"),
        "inspected_record_tool": ("retrieval"),
        "inspected_record_kind": ("retrieval_hit"),
        "unselected_retrieval_records": ("not_inspected"),
        "structured_sql_graph_records": ("outside_this_policy"),
    }


def test_policy_contract_records_safe_failure() -> None:
    contract = build_policy_contract()

    safe = contract["safe_failure"]

    assert safe["service_status"] == ("abstained")

    assert safe["reason"] == ("instruction_integrity_blocked")

    assert safe["presentation_source"] == ("deterministic")

    assert safe["generation_fidelity"] == ("not_applicable")

    assert safe["synthesis_invoked"] is False

    assert safe["generation_authority_created"] is False

    assert safe["generation_invoked"] is False

    assert safe["retrieval_text_exposed_in_policy_result"] is False

    assert safe["retrieval_text_exposed_in_presentation"] is False


def test_policy_contract_records_complete_typed_taxonomy() -> None:
    contract = build_policy_contract()

    assert contract["violation_codes"] == [
        "abstention_override",
        "answer_redirection",
        "answer_value_manipulation",
        "authority_priority_override",
        "citation_manipulation",
        "provenance_manipulation",
    ]

    rules = contract["rules"]

    assert len(rules) == 16

    assert all(
        set(rule)
        == {
            "violation_code",
            "pattern",
        }
        for rule in rules
    )


def test_policy_contract_records_reviewed_source_hashes() -> None:
    contract = build_policy_contract()

    assert contract["reviewed_source_sha256"] == EXPECTED_SOURCE_SHA256


def test_serialized_contract_roundtrip_is_stable() -> None:
    contract = build_policy_contract()

    rendered = deterministic_contract_bytes(contract)

    roundtrip = json.loads(rendered.decode("utf-8"))

    assert roundtrip == contract


def test_claim_boundary_remains_narrow() -> None:
    contract = build_policy_contract()

    boundary = contract["claim_boundary"]

    assert boundary["complete_prompt_injection_detector"] is False

    assert boundary["universal_jailbreak_prevention"] is False

    assert boundary["comprehensive_responsible_ai_guardrail"] is False
