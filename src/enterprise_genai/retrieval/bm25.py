import math
from collections import Counter
from dataclasses import dataclass

from enterprise_genai.data.chunk_models import (
    RetrievalChunk,
)
from enterprise_genai.retrieval.tokenization import (
    TOKENIZER_VERSION,
    tokenize,
)

BM25_VERSION = "bm25-v1"


@dataclass(frozen=True)
class BM25Config:
    k1: float = 1.5
    b: float = 0.75

    def __post_init__(self) -> None:
        if self.k1 <= 0:
            raise ValueError("BM25 k1 must be positive.")

        if not 0 <= self.b <= 1:
            raise ValueError("BM25 b must be between 0 and 1.")


@dataclass(frozen=True)
class BM25SearchResult:
    rank: int
    score: float
    chunk_id: str
    document_id: str
    evidence_id: str
    text: str
    source_fact_ids: tuple[str, ...]
    matched_terms: tuple[str, ...]


class BM25Index:
    """Small deterministic in-memory BM25 retrieval index."""

    def __init__(
        self,
        chunks: list[RetrievalChunk],
        *,
        config: BM25Config | None = None,
    ) -> None:
        if not chunks:
            raise ValueError("BM25 requires at least one chunk.")

        self.config = config or BM25Config()

        self.chunks = tuple(
            sorted(
                chunks,
                key=lambda chunk: chunk.chunk_id,
            )
        )

        self._tokens = tuple(tokenize(chunk.text) for chunk in self.chunks)

        self._term_frequencies = tuple(Counter(tokens) for tokens in self._tokens)

        self._document_lengths = tuple(len(tokens) for tokens in self._tokens)

        self.document_count = len(self.chunks)

        self.average_document_length = sum(self._document_lengths) / self.document_count

        document_frequency: Counter[str] = Counter()

        for tokens in self._tokens:
            document_frequency.update(set(tokens))

        self.document_frequency = dict(document_frequency)

    @property
    def tokenizer_version(self) -> str:
        return TOKENIZER_VERSION

    def idf(self, term: str) -> float:
        """Return positive Robertson-style BM25 IDF."""

        df = self.document_frequency.get(
            term,
            0,
        )

        if df == 0:
            return 0.0

        numerator = self.document_count - df + 0.5

        denominator = df + 0.5

        return math.log1p(numerator / denominator)

    def _score_document(
        self,
        query_tokens: tuple[str, ...],
        document_index: int,
    ) -> float:
        frequencies = self._term_frequencies[document_index]

        document_length = self._document_lengths[document_index]

        query_frequency = Counter(query_tokens)

        score = 0.0

        for term, query_count in query_frequency.items():
            term_frequency = frequencies.get(
                term,
                0,
            )

            if term_frequency == 0:
                continue

            idf = self.idf(term)

            length_normalization = (
                1 - self.config.b + self.config.b * document_length / self.average_document_length
            )

            denominator = term_frequency + self.config.k1 * length_normalization

            term_score = idf * term_frequency * (self.config.k1 + 1) / denominator

            score += term_score * query_count

        return score

    def search(
        self,
        query: str,
        *,
        top_k: int | None = None,
    ) -> list[BM25SearchResult]:
        if top_k is not None and top_k <= 0:
            raise ValueError("top_k must be positive.")

        query_tokens = tokenize(query)

        if not query_tokens:
            return []

        scored: list[
            tuple[
                float,
                RetrievalChunk,
                tuple[str, ...],
            ]
        ] = []

        for index, chunk in enumerate(self.chunks):
            score = self._score_document(
                query_tokens,
                index,
            )

            # Do not fill rankings with arbitrary
            # zero-overlap chunks.
            if score <= 0:
                continue

            frequencies = self._term_frequencies[index]

            matched_terms = tuple(
                dict.fromkeys(term for term in query_tokens if term in frequencies)
            )

            scored.append(
                (
                    score,
                    chunk,
                    matched_terms,
                )
            )

        scored.sort(
            key=lambda item: (
                -item[0],
                item[1].chunk_id,
            )
        )

        if top_k is not None:
            scored = scored[:top_k]

        return [
            BM25SearchResult(
                rank=rank,
                score=score,
                chunk_id=chunk.chunk_id,
                document_id=(chunk.document_id),
                evidence_id=(chunk.evidence_id),
                text=chunk.text,
                source_fact_ids=tuple(chunk.source_fact_ids),
                matched_terms=(matched_terms),
            )
            for rank, (
                score,
                chunk,
                matched_terms,
            ) in enumerate(
                scored,
                start=1,
            )
        ]
