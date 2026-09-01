from datetime import date
from typing import Literal, Self

from pydantic import BaseModel, Field, model_validator

DocumentType = Literal[
    "investment_committee_memo",
    "quarterly_management_report",
    "board_update",
    "risk_review",
    "incident_report",
    "supplier_review",
    "customer_review",
    "strategy_memo",
]


class EvidenceBlock(BaseModel):
    evidence_id: str
    heading: str
    text: str = Field(min_length=1)
    source_fact_ids: list[str] = Field(min_length=1)


class EnterpriseDocument(BaseModel):
    document_id: str
    company_id: str
    document_type: DocumentType
    title: str
    document_date: date
    confidentiality: Literal["internal", "confidential", "restricted"]
    version: int = Field(ge=1)
    evidence: list[EvidenceBlock] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_unique_evidence_ids(self) -> Self:
        evidence_ids = [block.evidence_id for block in self.evidence]

        if len(evidence_ids) != len(set(evidence_ids)):
            raise ValueError(f"Duplicate evidence_id in document {self.document_id}.")

        return self


class DocumentCorpus(BaseModel):
    dataset_version: str
    documents: list[EnterpriseDocument]

    @model_validator(mode="after")
    def validate_corpus_ids(self) -> Self:
        document_ids = [document.document_id for document in self.documents]

        if len(document_ids) != len(set(document_ids)):
            raise ValueError("Duplicate document_id detected.")

        evidence_ids = [
            block.evidence_id for document in self.documents for block in document.evidence
        ]

        if len(evidence_ids) != len(set(evidence_ids)):
            raise ValueError("Duplicate evidence_id detected across corpus.")

        return self
