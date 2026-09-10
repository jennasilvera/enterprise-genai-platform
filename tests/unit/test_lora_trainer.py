from pathlib import Path

import pytest

from enterprise_genai.data.routing_seed import (
    build_routing_seed,
)
from enterprise_genai.routing.lora_trainer import (
    assert_output_dir_empty,
    epoch_permutation,
    normalize_question,
    partition_routing_cases,
)


def test_epoch_permutation_is_repeatable() -> None:
    first = epoch_permutation(
        112,
        seed=1729,
        epoch=1,
    )

    second = epoch_permutation(
        112,
        seed=1729,
        epoch=1,
    )

    assert first == second


def test_epoch_permutation_covers_every_case_once() -> None:
    permutation = epoch_permutation(
        112,
        seed=1729,
        epoch=1,
    )

    assert sorted(permutation) == list(range(112))


def test_epoch_permutation_changes_between_epochs() -> None:
    assert epoch_permutation(
        112,
        seed=1729,
        epoch=1,
    ) != epoch_permutation(
        112,
        seed=1729,
        epoch=2,
    )


def test_frozen_routing_partition() -> None:
    train, development = partition_routing_cases(build_routing_seed())

    assert len(train) == 112

    assert len(development) == 28

    assert not (
        {case.template_family for case in train} & {case.template_family for case in development}
    )


def test_output_directory_guard(
    tmp_path: Path,
) -> None:
    empty = tmp_path / "empty"

    empty.mkdir()

    assert_output_dir_empty(empty)

    (empty / "unexpected.txt").write_text("x")

    with pytest.raises(
        FileExistsError,
        match="absent or empty",
    ):
        assert_output_dir_empty(empty)


def test_question_normalization() -> None:
    assert normalize_question("  alpha \n beta   gamma ") == "alpha beta gamma"
