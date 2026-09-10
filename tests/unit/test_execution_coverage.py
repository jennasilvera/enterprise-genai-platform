import hashlib

from enterprise_genai.evaluation.execution_coverage import (
    DECLARATIONS,
    EXPECTED_TOOL_SETS,
    TARGET_QUERY_IDS,
    deterministic_execution_coverage_bytes,
    protocol_report,
    validate_coverage_protocol,
)


def test_execution_coverage_protocol_validates() -> None:
    validate_coverage_protocol()


def test_execution_coverage_targets_expected_cases() -> None:
    assert TARGET_QUERY_IDS == (
        "Q-0010",
        "Q-0011",
        "Q-0012",
        "Q-0013",
        "Q-0014",
        "Q-0015",
        "Q-0016",
        "Q-0020",
        "Q-0021",
        "Q-0022",
        "Q-0024",
    )

    assert len(DECLARATIONS) == 11

    assert len(EXPECTED_TOOL_SETS) == 11


def test_mixed_tool_cases_have_expected_protocol_status() -> None:
    declarations = {item.query_id: item for item in DECLARATIONS}

    assert declarations["Q-0020"].composition_coverage == "pending_explicit_verification"

    assert declarations["Q-0021"].composition_coverage == "pending_explicit_verification"

    assert declarations["Q-0022"].composition_coverage == "verified_explicit"


def test_q0024_distinguishes_guardrail_from_abstention() -> None:
    declarations = {item.query_id: item for item in DECLARATIONS}

    q0024 = declarations["Q-0024"]

    assert q0024.primitive_coverage == "unsupported_metric_by_design"

    assert q0024.abstention == "not_implemented"


def test_protocol_report_is_byte_deterministic() -> None:
    first = deterministic_execution_coverage_bytes(protocol_report())

    second = deterministic_execution_coverage_bytes(protocol_report())

    assert first == second

    assert first.endswith(b"\n")

    assert hashlib.sha256(first).hexdigest() == hashlib.sha256(second).hexdigest()
