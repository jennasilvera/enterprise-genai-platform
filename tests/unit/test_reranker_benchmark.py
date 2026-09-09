import copy
import hashlib

import numpy as np
import pytest

from enterprise_genai.data.core_corpus import (
    build_core_corpus,
)
from enterprise_genai.data.evaluation_seed import (
    build_seed_evaluation,
)
from enterprise_genai.evaluation.reranker_benchmark import (
    EXPECTED_DEVELOPMENT_QUERY_IDS,
    run_reranker_development_benchmark,
    verify_phase6a_regeneration,
)
from enterprise_genai.retrieval.chunking import (
    build_evidence_chunks,
)
from enterprise_genai.retrieval.dense_representation import (
    DENSE_DOCUMENT_TITLE_TEXT_VERSION,
    build_dense_index_corpus,
)
from enterprise_genai.retrieval.lexical_representation import (
    build_lexical_index_corpus,
)
from enterprise_genai.retrieval.reranker import (
    CANDIDATE_K,
    RERANKER_REPRESENTATION_VERSION,
    RERANKER_VERSION,
)


class HashEncoder:
    embedding_dimension = 16

    @property
    def metadata(
        self,
    ) -> dict[str, object]:
        return {
            "dense_version": ("hash-dense"),
            "representation_version": (DENSE_DOCUMENT_TITLE_TEXT_VERSION),
            "model_id": "hash-test",
            "embedding_dimension": 16,
        }

    def _encode(
        self,
        texts: list[str],
    ) -> np.ndarray:
        if not texts:
            return np.empty(
                (0, 16),
                dtype=np.float32,
            )

        vectors = []

        for text in texts:
            digest = hashlib.sha256(text.encode("utf-8")).digest()

            vector = np.frombuffer(
                digest[:16],
                dtype=np.uint8,
            ).astype(np.float32)

            vector += 1.0

            vector /= np.linalg.norm(vector)

            vectors.append(vector)

        return np.stack(vectors)

    def encode_passages(
        self,
        texts: list[str],
    ) -> np.ndarray:
        return self._encode(texts)

    def encode_queries(
        self,
        texts: list[str],
    ) -> np.ndarray:
        return self._encode(texts)


class FakeReranker:
    @property
    def metadata(
        self,
    ) -> dict[str, object]:
        return {
            "reranker_version": (RERANKER_VERSION),
            "representation_version": (RERANKER_REPRESENTATION_VERSION),
            "candidate_k": (CANDIDATE_K),
            "model_id": "fake",
        }

    def score(
        self,
        query: str,
        passages: list[str],
    ) -> np.ndarray:
        return np.arange(
            len(passages),
            0,
            -1,
            dtype=np.float32,
        )


def _benchmark():
    documents = build_core_corpus()

    chunks = build_evidence_chunks(documents)

    lexical = build_lexical_index_corpus(
        chunks,
        documents,
        {},
        representation_version=("document-title-text-v1"),
    )

    dense = build_dense_index_corpus(
        chunks,
        documents,
        representation_version=(DENSE_DOCUMENT_TITLE_TEXT_VERSION),
    )

    return run_reranker_development_benchmark(
        build_seed_evaluation(),
        lexical,
        dense,
        encoder=HashEncoder(),
        reranker=FakeReranker(),
    )


def test_benchmark_uses_exact_development_cases() -> None:
    report = _benchmark()

    assert tuple(report["evaluation"]["query_ids"]) == EXPECTED_DEVELOPMENT_QUERY_IDS

    assert report["evaluation"]["retrieval_eligible_cases"] == 10


def test_benchmark_preserves_candidate_set_and_tail() -> None:
    report = _benchmark()

    for case in report["reranked_benchmark"]["cases"]:
        assert case["candidate_set_preserved"] is True

        assert case["tail_order_preserved"] is True

        assert case["retrieved_reranked"] == 80


def test_reference_verifier_accepts_matching_baseline() -> None:
    report = _benchmark()

    frozen = {
        "selected_retriever": ("hybrid:rrf-k60-v1"),
        "hybrid_benchmark": (copy.deepcopy(report["baseline_benchmark"])),
    }

    verification = verify_phase6a_regeneration(
        frozen,
        report,
    )

    assert verification["verified"] is True


def test_reference_verifier_rejects_changed_top10() -> None:
    report = _benchmark()

    frozen = {
        "selected_retriever": ("hybrid:rrf-k60-v1"),
        "hybrid_benchmark": (copy.deepcopy(report["baseline_benchmark"])),
    }

    frozen["hybrid_benchmark"]["cases"][0]["top_results"][0]["chunk_id"] = "CHK-TAMPERED"

    with pytest.raises(
        ValueError,
        match="top-10 identity",
    ):
        verify_phase6a_regeneration(
            frozen,
            report,
        )
