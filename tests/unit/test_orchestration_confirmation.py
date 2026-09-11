from __future__ import annotations

from pathlib import Path

import pytest

from enterprise_genai.evaluation.orchestration_confirmation import (
    deterministic_orchestration_confirmation_bytes,
    orchestration_confirmation_sha256,
    write_orchestration_confirmation,
)


def _report() -> dict[str, object]:
    return {
        "confirmation_version": "test-v1",
        "summary": {
            "completed_cases": 3,
            "target_cases": 3,
        },
        "cases": [
            {
                "query_id": "Q-0020",
                "terminal_status": "completed",
            },
            {
                "query_id": "Q-0021",
                "terminal_status": "completed",
            },
            {
                "query_id": "Q-0022",
                "terminal_status": "completed",
            },
        ],
    }


def test_confirmation_serialization_is_deterministic() -> None:
    first = deterministic_orchestration_confirmation_bytes(_report())

    second = deterministic_orchestration_confirmation_bytes(_report())

    assert first == second

    assert first.endswith(b"\n")

    assert orchestration_confirmation_sha256(_report()) == orchestration_confirmation_sha256(
        _report()
    )


def test_confirmation_writer_refuses_overwrite(
    tmp_path: Path,
) -> None:
    output = tmp_path / "confirmation.json"

    write_orchestration_confirmation(
        _report(),
        output,
    )

    assert output.read_bytes() == deterministic_orchestration_confirmation_bytes(_report())

    with pytest.raises(
        FileExistsError,
        match=("output already exists"),
    ):
        write_orchestration_confirmation(
            _report(),
            output,
        )
