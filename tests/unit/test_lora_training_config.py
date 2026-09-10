from enterprise_genai.routing.lora_training_config import (
    BATCH_SIZE,
    CHECKPOINT_SELECTION_ORDER,
    DEVELOPMENT_CASES,
    EPOCHS,
    EXPECTED_TRAINABLE_PARAMETERS,
    FROZEN_LORA_TRAINING_CONFIG_SHA256,
    ID2LABEL,
    LABEL2ID,
    LORA_ALPHA,
    LORA_DROPOUT,
    LORA_R,
    LORA_TARGET_MODULES,
    ROUTE_ORDER,
    SEED_SELECTION_ORDER,
    STEPS_PER_EPOCH,
    TOTAL_STEPS_PER_SEED,
    TRAIN_CASES,
    TRAINING_SEEDS,
    lora_training_config_sha256,
)


def test_frozen_lora_training_config_fingerprint() -> None:
    assert (
        lora_training_config_sha256()
        == FROZEN_LORA_TRAINING_CONFIG_SHA256
        == "bd2f9f65decf4e5d6b8d2b7dc9908c778f081cc20b2ade3ce78e502ab50c39cf"
    )


def test_route_label_mapping_is_bijective() -> None:
    assert len(ROUTE_ORDER) == 7

    assert len(LABEL2ID) == 7

    assert len(ID2LABEL) == 7

    for route, label_id in LABEL2ID.items():
        assert ID2LABEL[label_id] == route


def test_training_budget_is_consistent() -> None:
    assert TRAIN_CASES % BATCH_SIZE == 0

    assert STEPS_PER_EPOCH == TRAIN_CASES // BATCH_SIZE == 7

    assert TOTAL_STEPS_PER_SEED == EPOCHS * STEPS_PER_EPOCH == 140

    assert DEVELOPMENT_CASES == 28


def test_lora_and_selection_contract() -> None:
    assert TRAINING_SEEDS == (
        1729,
        2718,
        31415,
    )

    assert LORA_R == 8

    assert LORA_ALPHA == 16

    assert LORA_DROPOUT == 0.05

    assert LORA_TARGET_MODULES == (
        "query_proj",
        "value_proj",
    )

    assert EXPECTED_TRAINABLE_PARAMETERS == 150151

    assert CHECKPOINT_SELECTION_ORDER[-1] == "earlier_epoch"

    assert SEED_SELECTION_ORDER[-1] == "earlier_seed_in_frozen_seed_order"
