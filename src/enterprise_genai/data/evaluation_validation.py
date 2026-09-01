from enterprise_genai.data.document_models import DocumentCorpus
from enterprise_genai.data.evaluation_models import EvaluationSet


def validate_evaluation_references(
    evaluation_set: EvaluationSet,
    corpus: DocumentCorpus,
) -> None:
    """Validate evaluation judgments against the document corpus."""

    if evaluation_set.dataset_version != corpus.dataset_version:
        raise ValueError("Evaluation and corpus dataset versions do not match.")

    documents_by_id = {document.document_id: document for document in corpus.documents}

    evidence_to_document = {
        block.evidence_id: document.document_id
        for document in corpus.documents
        for block in document.evidence
    }

    for case in evaluation_set.cases:
        for judgment in case.relevance_judgments:
            document = documents_by_id.get(judgment.document_id)

            if document is None:
                raise ValueError(
                    f"{case.query_id} references unknown document {judgment.document_id}."
                )

            evidence_document_id = evidence_to_document.get(judgment.evidence_id)

            if evidence_document_id is None:
                raise ValueError(
                    f"{case.query_id} references unknown evidence {judgment.evidence_id}."
                )

            if evidence_document_id != judgment.document_id:
                raise ValueError(
                    f"{case.query_id} maps evidence "
                    f"{judgment.evidence_id} to "
                    f"{judgment.document_id}, but the evidence belongs to "
                    f"{evidence_document_id}."
                )
