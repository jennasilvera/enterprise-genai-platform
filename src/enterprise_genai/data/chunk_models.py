from typing import Self

from pydantic import BaseModel, Field, model_validator


class RetrievalChunk(BaseModel):
    chunk_id: str
    document_id: str
    evidence_id: str
    chunk_ordinal: int = Field(ge=0)
    strategy_version: str = Field(min_length=1)
    text: str = Field(min_length=1)
    text_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    character_count: int = Field(gt=0)
    word_count: int = Field(gt=0)
    source_fact_ids: list[str] = Field(min_length=1)


class ChunkCorpus(BaseModel):
    dataset_version: str
    strategy_version: str = Field(min_length=1)
    chunks: list[RetrievalChunk]

    @model_validator(mode="after")
    def validate_chunk_identity(self) -> Self:
        chunk_ids = [chunk.chunk_id for chunk in self.chunks]

        if len(chunk_ids) != len(set(chunk_ids)):
            raise ValueError("Duplicate chunk_id detected.")

        positions = [
            (
                chunk.evidence_id,
                chunk.strategy_version,
                chunk.chunk_ordinal,
            )
            for chunk in self.chunks
        ]

        if len(positions) != len(set(positions)):
            raise ValueError("Duplicate evidence/strategy/chunk ordinal detected.")

        for chunk in self.chunks:
            if chunk.strategy_version != self.strategy_version:
                raise ValueError("Chunk strategy_version does not match corpus strategy_version.")

            if len(chunk.source_fact_ids) != len(set(chunk.source_fact_ids)):
                raise ValueError(f"Duplicate source fact in {chunk.chunk_id}.")

        return self
