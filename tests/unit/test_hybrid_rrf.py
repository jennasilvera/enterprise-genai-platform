import hashlib

import numpy as np
import pytest

from enterprise_genai.data.core_corpus import (
    build_core_corpus,
)
from enterprise_genai.data.evaluation_seed import (
    build_seed_evaluation,
)
from enterprise_genai.evaluation.dense_benchmark import (
    build_development_retrieval_evaluation,
)
from enterprise_genai.evaluation.hybrid_rrf import (
    run_hybrid_rrf_benchmark,
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

    evaluation = build_development_retrieval_evaluation(build_seed_evaluation())

    return (
        evaluation,
        lexical,
        dense,
    )


def test_hybrid_rrf_uses_exact_development_cases() -> None:
    evaluation, lexical, dense = _inputs()

    report = run_hybrid_rrf_benchmark(
        evaluation,
        lexical,
        dense,
        encoder=HashEncoder(),
    )

    assert {case["query_id"] for case in report["cases"]} == {
        "Q-0001",
        "Q-0002",
        "Q-0004",
        "Q-0006",
        "Q-0008",
        "Q-0009",
        "Q-0017",
        "Q-0019",
        "Q-0020",
        "Q-0021",
    }

    assert all(case["split"] == "development" for case in report["cases"])


def test_hybrid_rrf_records_frozen_configuration() -> None:
    evaluation, lexical, dense = _inputs()

    report = run_hybrid_rrf_benchmark(
        evaluation,
        lexical,
        dense,
        encoder=HashEncoder(),
    )

    assert report["fusion"]["version"] == "rrf-k60-v1"

    assert report["fusion"]["k"] == 60

    assert report["lexical"]["representation_version"] == "document-title-text-v1"

    assert report["dense"]["representation_version"] == DENSE_DOCUMENT_TITLE_TEXT_VERSION

    assert report["summary"]["retrieval_eligible"]["cases"] == 10

    assert all(case["retrieved_fused"] == 80 for case in report["cases"])


def test_hybrid_rrf_rejects_wrong_dense_representation() -> None:
    evaluation, lexical, dense = _inputs()

    class WrongEncoder(HashEncoder):
        @property
        def metadata(self):
            return {"representation_version": ("e5-evidence-text-v1")}

    with pytest.raises(
        ValueError,
        match=("requires frozen dense document-title"),
    ):
        run_hybrid_rrf_benchmark(
            evaluation,
            lexical,
            dense,
            encoder=WrongEncoder(),
        )
