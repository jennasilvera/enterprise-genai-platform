import hashlib

import numpy as np

from enterprise_genai.data.core_corpus import (
    build_core_corpus,
)
from enterprise_genai.data.evaluation_seed import (
    build_seed_evaluation,
)
from enterprise_genai.evaluation.dense_benchmark import (
    build_development_retrieval_evaluation,
    run_dense_benchmark,
)
from enterprise_genai.retrieval.chunking import (
    build_evidence_chunks,
)


class HashEncoder:
    embedding_dimension = 16

    @property
    def metadata(self):
        return {
            "model_id": "hash-test",
            "embedding_dimension": 16,
        }

    def _encode(
        self,
        texts,
    ):
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
        texts,
    ):
        return self._encode(texts)

    def encode_queries(
        self,
        texts,
    ):
        return self._encode(texts)


def test_dense_development_scope_has_ten_cases() -> None:
    evaluation = build_development_retrieval_evaluation(build_seed_evaluation())

    assert len(evaluation.cases) == 10


def test_dense_development_scope_excludes_test_cases() -> None:
    evaluation = build_development_retrieval_evaluation(build_seed_evaluation())

    assert all(case.split == "development" for case in evaluation.cases)


def test_dense_benchmark_records_ranker_metadata() -> None:
    documents = build_core_corpus()

    chunks = build_evidence_chunks(documents)

    evaluation = build_development_retrieval_evaluation(build_seed_evaluation())

    report = run_dense_benchmark(
        evaluation,
        chunks,
        encoder=HashEncoder(),
    )

    assert report["benchmark_version"] == ("northstar-dense-baseline-v1")

    assert report["summary"]["retrieval_eligible"]["cases"] == 10

    assert report["corpus"]["chunks"] == 80

    assert report["encoder"]["model_id"] == "hash-test"

    assert {case["split"] for case in report["cases"]} == {"development"}


def test_dense_development_scope_has_expected_case_ids() -> None:
    evaluation = build_development_retrieval_evaluation(build_seed_evaluation())

    assert {case.query_id for case in evaluation.cases} == {
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
