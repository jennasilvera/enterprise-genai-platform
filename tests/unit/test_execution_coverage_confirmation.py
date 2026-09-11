import hashlib

from enterprise_genai.evaluation.execution_coverage_confirmation import (
    EXECUTION_COVERAGE_CONFIRMATION_VERSION,
    FROZEN_PROTOCOL_REPORT_SHA256,
    assert_frozen_protocol,
    deterministic_confirmation_bytes,
    protocol_report_sha256,
)


def test_confirmation_uses_frozen_protocol() -> None:
    assert_frozen_protocol()

    assert protocol_report_sha256() == FROZEN_PROTOCOL_REPORT_SHA256


def test_confirmation_version_is_frozen() -> None:
    assert EXECUTION_COVERAGE_CONFIRMATION_VERSION == (
        "northstar-execution-coverage-confirmation-v1"
    )


def test_confirmation_serialization_is_deterministic() -> None:
    report = {
        "b": 2,
        "a": {
            "value": 1,
        },
    }

    first = deterministic_confirmation_bytes(report)

    second = deterministic_confirmation_bytes(report)

    assert first == second

    assert first.endswith(b"\n")

    assert hashlib.sha256(first).hexdigest() == hashlib.sha256(second).hexdigest()
