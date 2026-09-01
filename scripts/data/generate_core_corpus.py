from pathlib import Path

from enterprise_genai.data.core_corpus import build_core_corpus
from enterprise_genai.data.provenance import (
    validate_document_provenance,
    validate_document_temporality,
)
from enterprise_genai.data.universe import build_universe

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
OUTPUT_PATH = REPOSITORY_ROOT / "data" / "raw" / "documents" / "northstar_v1_core_corpus.json"


def main() -> None:
    universe = build_universe()
    corpus = build_core_corpus()

    validate_document_provenance(
        corpus,
        universe,
    )
    validate_document_temporality(
        corpus,
        universe,
    )

    OUTPUT_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    serialized = corpus.model_dump_json(indent=2) + "\n"

    OUTPUT_PATH.write_text(
        serialized,
        encoding="utf-8",
    )

    evidence_count = sum(len(document.evidence) for document in corpus.documents)

    print(f"dataset_version: {corpus.dataset_version}")
    print(f"documents: {len(corpus.documents)}")
    print(f"evidence_blocks: {evidence_count}")
    print("provenance_validation: OK")
    print("temporal_validation: OK")
    print(f"wrote: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
