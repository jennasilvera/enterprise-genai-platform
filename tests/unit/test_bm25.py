import hashlib

from enterprise_genai.data.chunk_models import (
    RetrievalChunk,
)
from enterprise_genai.retrieval.bm25 import (
    BM25Index,
)


def _chunk(
    chunk_id: str,
    evidence_id: str,
    text: str,
) -> RetrievalChunk:
    return RetrievalChunk(
        chunk_id=chunk_id,
        document_id=(f"DOC-{evidence_id}"),
        evidence_id=evidence_id,
        chunk_ordinal=0,
        strategy_version=("evidence-block-v1"),
        text=text,
        text_sha256=hashlib.sha256(text.encode("utf-8")).hexdigest(),
        character_count=len(text),
        word_count=len(text.split()),
        source_fact_ids=[f"FACT-{evidence_id}"],
    )


def test_exact_identifier_ranks_matching_chunk_first() -> None:
    index = BM25Index(
        [
            _chunk(
                "CHK-B",
                "EVID-B",
                "General reliability review.",
            ),
            _chunk(
                "CHK-A",
                "EVID-A",
                ("The ORBIS-IDX-7 defect caused a service incident."),
            ),
        ]
    )

    results = index.search("What defect affected ORBIS-IDX-7?")

    assert results[0].evidence_id == ("EVID-A")
    assert "orbis-idx-7" in (results[0].matched_terms)


def test_zero_overlap_returns_no_results() -> None:
    index = BM25Index(
        [
            _chunk(
                "CHK-A",
                "EVID-A",
                "Titanium supplier exposure.",
            )
        ]
    )

    assert index.search("completely unrelated vocabulary") == []


def test_equal_scores_use_chunk_id_tie_break() -> None:
    index = BM25Index(
        [
            _chunk(
                "CHK-B",
                "EVID-B",
                "supplier risk",
            ),
            _chunk(
                "CHK-A",
                "EVID-A",
                "supplier risk",
            ),
        ]
    )

    results = index.search("supplier")

    assert [result.chunk_id for result in results] == [
        "CHK-A",
        "CHK-B",
    ]


def test_search_is_deterministic() -> None:
    index = BM25Index(
        [
            _chunk(
                "CHK-A",
                "EVID-A",
                "permitting delay",
            ),
            _chunk(
                "CHK-B",
                "EVID-B",
                "customer renewal",
            ),
        ]
    )

    first = index.search("permitting delay")
    second = index.search("permitting delay")

    assert first == second
