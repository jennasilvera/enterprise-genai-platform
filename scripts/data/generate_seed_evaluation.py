from pathlib import Path

from enterprise_genai.data.core_corpus import build_core_corpus
from enterprise_genai.data.evaluation_seed import build_seed_evaluation
from enterprise_genai.data.evaluation_validation import (
    validate_evaluation_ground_truth,
    validate_evaluation_references,
)
from enterprise_genai.data.universe import build_universe

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
OUTPUT_PATH = REPOSITORY_ROOT / "data" / "evaluation" / "northstar_v1_seed_evaluation.json"


def main() -> None:
    universe = build_universe()
    corpus = build_core_corpus()
    evaluation = build_seed_evaluation()

    validate_evaluation_references(
        evaluation,
        corpus,
    )
    validate_evaluation_ground_truth(
        evaluation,
        universe,
    )

    OUTPUT_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    serialized = evaluation.model_dump_json(indent=2) + "\n"

    OUTPUT_PATH.write_text(
        serialized,
        encoding="utf-8",
    )

    development_count = sum(case.split == "development" for case in evaluation.cases)

    test_count = sum(case.split == "test" for case in evaluation.cases)

    print(f"dataset_version: {evaluation.dataset_version}")
    print(f"evaluation_version: {evaluation.evaluation_version}")
    print(f"cases: {len(evaluation.cases)}")
    print(f"development_cases: {development_count}")
    print(f"test_cases: {test_count}")
    print("document_reference_validation: OK")
    print("answer_ground_truth_validation: OK")
    print(f"wrote: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
