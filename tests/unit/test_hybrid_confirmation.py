import hashlib

import numpy as np
import pytest

from enterprise_genai.data.core_corpus import build_core_corpus
from enterprise_genai.data.evaluation_seed import build_seed_evaluation
from enterprise_genai.evaluation.hybrid_confirmation import (
    EXPECTED_TEST_QUERY_IDS,
    TEST_SPLIT_STATUS,
    run_hybrid_test_confirmation,
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


class HashEncoder:
    embedding_dimension = 16

    @property
    def metadata(self):
        return {
            "model_id": "hash-test",
            "embedding_dimension": 16,
            "representation_version": (DENSE_DOCUMENT_TITLE_TEXT_VERSION),
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


def _inputs():
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

    return (
        build_seed_evaluation(),
        lexical,
        dense,
    )


def test_confirmation_uses_exact_test_query_ids() -> None:
    evaluation, lexical, dense = _inputs()

    report = run_hybrid_test_confirmation(
        evaluation,
        lexical,
        dense,
        encoder=HashEncoder(),
    )

    assert (
        tuple(case["query_id"] for case in report["hybrid_benchmark"]["cases"])
        == EXPECTED_TEST_QUERY_IDS
    )


def test_confirmation_records_nonpristine_scope() -> None:
    evaluation, lexical, dense = _inputs()

    report = run_hybrid_test_confirmation(
        evaluation,
        lexical,
        dense,
        encoder=HashEncoder(),
    )

    assert report["scope"] == "test-confirmation"

    assert report["test_split_status"] == TEST_SPLIT_STATUS

    assert report["selection_status"] == "frozen-before-test-confirmation"

    assert report["frozen_selected_retriever"] == "hybrid:rrf-k60-v1"


def test_confirmation_compares_same_four_cases() -> None:
    evaluation, lexical, dense = _inputs()

    report = run_hybrid_test_confirmation(
        evaluation,
        lexical,
        dense,
        encoder=HashEncoder(),
    )

    dense_report = report["dense_reference_benchmark"]

    hybrid_report = report["hybrid_benchmark"]

    assert dense_report["summary"]["retrieval_eligible"]["cases"] == 4

    assert hybrid_report["summary"]["retrieval_eligible"]["cases"] == 4

    assert all(case["split"] == "test" for case in dense_report["cases"])

    assert all(case["split"] == "test" for case in hybrid_report["cases"])


def test_confirmation_rejects_wrong_dense_representation() -> None:
    evaluation, lexical, dense = _inputs()

    class WrongEncoder(HashEncoder):
        @property
        def metadata(self):
            return {"representation_version": ("e5-evidence-text-v1")}

    with pytest.raises(
        ValueError,
        match="representation",
    ):
        run_hybrid_test_confirmation(
            evaluation,
            lexical,
            dense,
            encoder=WrongEncoder(),
        )
