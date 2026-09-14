from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from enterprise_genai.evaluation.instruction_integrity_baseline import (
    PHASE12B_MANIFEST_CANONICAL_SHA256,
    PHASE12B_MANIFEST_FILE_SHA256,
    InjectedRetrievalExecutor,
    _contains_any,
    deterministic_report_bytes,
    load_frozen_manifest,
    report_sha256,
)
from enterprise_genai.execution.contracts import (
    RetrievalHit,
    RetrievalQuery,
)

MANIFEST_PATH = Path("artifacts/evaluation/phase12b/instruction_integrity_case_manifest.json")


def test_frozen_manifest_bytes_are_exact() -> None:
    assert hashlib.sha256(MANIFEST_PATH.read_bytes()).hexdigest() == PHASE12B_MANIFEST_FILE_SHA256


def test_frozen_manifest_canonical_sha_is_exact() -> None:
    manifest = load_frozen_manifest()

    assert manifest["canonical_sha256"] == PHASE12B_MANIFEST_CANONICAL_SHA256

    assert manifest["case_count"] == 32


def test_manifest_loader_rejects_byte_drift(
    tmp_path: Path,
) -> None:
    drifted = tmp_path / "manifest.json"

    drifted.write_bytes(MANIFEST_PATH.read_bytes() + b"\n")

    with pytest.raises(
        ValueError,
        match="exact frozen manifest bytes",
    ):
        load_frozen_manifest(drifted)


def test_injected_retrieval_executor_uses_real_contract() -> None:
    question = "What defect affected ORBIS-IDX-7?"

    hit = RetrievalHit(
        rank=1,
        chunk_id="CHK-TEST",
        evidence_id="EVID-TEST",
        document_id="DOC-TEST",
        text=("ORBIS-IDX-7 experienced an authentication defect."),
        source_fact_ids=("RISK-006",),
        rrf_score=0.03,
        bm25_rank=1,
        dense_rank=1,
    )

    executor = InjectedRetrievalExecutor(
        question=question,
        hits=(hit,),
    )

    result = executor.execute(
        RetrievalQuery(
            question=question,
            top_k=10,
        )
    )

    assert result.tool == "retrieval"
    assert result.status == "ok"
    assert result.duration_ms == 0.0
    assert result.payload is not None
    assert result.payload.hits == (hit,)

    assert executor.observed_queries == [
        RetrievalQuery(
            question=question,
            top_k=10,
        )
    ]


def test_injected_retrieval_executor_rejects_question_drift() -> None:
    executor = InjectedRetrievalExecutor(
        question="Expected question",
        hits=(),
    )

    with pytest.raises(
        ValueError,
        match="different question",
    ):
        executor.execute(
            RetrievalQuery(
                question="Different question",
            )
        )


def test_report_serialization_is_deterministic() -> None:
    report = {
        "z": [3, 2, 1],
        "a": {
            "unicode": "—",
            "value": True,
        },
    }

    first = deterministic_report_bytes(report)

    second = deterministic_report_bytes(report)

    assert first == second

    assert report_sha256(report) == hashlib.sha256(first).hexdigest()

    assert json.loads(first.decode("utf-8")) == report


def test_authority_exposure_detects_locked_newline_cases() -> None:
    manifest = load_frozen_manifest()

    by_id = {case["case_id"]: case for case in manifest["cases"]}

    for case_id in (
        "PH12B-F2",
        "PH12B-F3",
    ):
        case = by_id[case_id]

        assert len(case["retrieval_hits"]) == 1

        raw_authority_like = {"authority_value": (case["retrieval_hits"][0]["text"])}

        spans = tuple(case["disallowed_payload_spans"])

        assert _contains_any(
            value=raw_authority_like,
            spans=spans,
        )

        serialized = json.dumps(
            raw_authority_like,
            sort_keys=True,
            ensure_ascii=False,
        )

        assert not any(span in serialized for span in spans)


def test_authority_exposure_does_not_join_distinct_string_leaves() -> None:
    assert not _contains_any(
        value={
            "first": "Ignore previous",
            "second": " instructions",
        },
        spans=("Ignore previous instructions",),
    )
