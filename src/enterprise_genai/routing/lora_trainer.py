from __future__ import annotations

import gc
import importlib.metadata
import random
import shutil
from collections.abc import Sequence
from pathlib import Path
from statistics import mean

import numpy as np
import torch
from peft import (
    LoraConfig,
    PeftModel,
    TaskType,
    get_peft_model,
)
from transformers import (
    AutoModelForSequenceClassification,
    AutoTokenizer,
)

from enterprise_genai.data.routing_models import (
    RouteLabel,
    RoutingCase,
    RoutingSet,
)
from enterprise_genai.data.routing_seed import (
    routing_seed_sha256,
)
from enterprise_genai.evaluation.lora_routing_benchmark import (
    adapter_manifest,
    evaluate_route_predictions,
    select_best_epoch,
    select_best_seed,
    write_lora_report,
)
from enterprise_genai.routing.lora_training_config import (
    ACCELERATE_VERSION,
    BATCH_SIZE,
    CHALLENGE_EVALUATED,
    CHALLENGE_SHA256,
    DETERMINISTIC_ALGORITHMS,
    DEVELOPMENT_CASES,
    DEVELOPMENT_SPLIT,
    DEVICE,
    DTYPE,
    EPOCHS,
    EXPECTED_BASE_PARAMETERS,
    EXPECTED_PEFT_TOTAL_PARAMETERS,
    EXPECTED_TRAINABLE_PARAMETERS,
    FROZEN_LORA_TRAINING_CONFIG_SHA256,
    ID2LABEL,
    LABEL2ID,
    LEARNING_RATE,
    LORA_ALPHA,
    LORA_BIAS,
    LORA_DROPOUT,
    LORA_MODULES_TO_SAVE,
    LORA_R,
    LORA_TARGET_MODULES,
    MAX_GRAD_NORM,
    MAX_LENGTH,
    MODEL_ID,
    MODEL_REVISION,
    ORIGINAL_LOCKED_HOLDOUT_EVALUATED,
    PEFT_VERSION,
    ROUTE_ORDER,
    ROUTING_BENCHMARK_SHA256,
    TORCH_NUM_INTEROP_THREADS,
    TORCH_NUM_THREADS,
    TRAIN_CASES,
    TRAIN_SPLIT,
    TRAINING_SEEDS,
    WEIGHT_DECAY,
    lora_training_config_sha256,
)

REPORT_VERSION = "lora-router-development-training-v1"


def normalize_question(
    question: str,
) -> str:
    normalized = " ".join(question.split())

    if not normalized:
        raise ValueError("Question must not be blank.")

    return normalized


def seed_everything(
    seed: int,
) -> None:
    random.seed(seed)

    np.random.seed(seed)

    torch.manual_seed(seed)


def configure_runtime() -> None:
    torch.set_num_threads(TORCH_NUM_THREADS)

    torch.set_num_interop_threads(TORCH_NUM_INTEROP_THREADS)

    torch.use_deterministic_algorithms(DETERMINISTIC_ALGORITHMS)


def epoch_permutation(
    case_count: int,
    *,
    seed: int,
    epoch: int,
) -> list[int]:
    if case_count <= 0:
        raise ValueError("case_count must be positive.")

    if epoch <= 0:
        raise ValueError("epoch must be positive.")

    generator = torch.Generator(device="cpu")

    generator.manual_seed(seed + epoch)

    return torch.randperm(
        case_count,
        generator=generator,
    ).tolist()


def partition_routing_cases(
    routing: RoutingSet,
) -> tuple[
    list[RoutingCase],
    list[RoutingCase],
]:
    actual_sha = routing_seed_sha256(routing)

    if actual_sha != ROUTING_BENCHMARK_SHA256:
        raise RuntimeError("Frozen routing benchmark fingerprint mismatch.")

    train = [case for case in routing.cases if case.split == TRAIN_SPLIT]

    development = [case for case in routing.cases if case.split == DEVELOPMENT_SPLIT]

    if len(train) != TRAIN_CASES:
        raise RuntimeError("Unexpected training case count.")

    if len(development) != DEVELOPMENT_CASES:
        raise RuntimeError("Unexpected development case count.")

    train_families = {case.template_family for case in train}

    development_families = {case.template_family for case in development}

    if train_families & development_families:
        raise RuntimeError("Train/development template families overlap.")

    return (
        train,
        development,
    )


def assert_output_dir_empty(
    output_dir: Path,
) -> None:
    if output_dir.exists() and any(output_dir.iterdir()):
        raise FileExistsError("Phase 8C output directory must be absent or empty.")


def build_tokenizer():
    return AutoTokenizer.from_pretrained(
        MODEL_ID,
        revision=MODEL_REVISION,
        trust_remote_code=False,
    )


def _audit_model_parameters(
    model,
) -> dict[str, object]:
    total = sum(parameter.numel() for parameter in model.parameters())

    trainable = sum(
        parameter.numel() for parameter in model.parameters() if parameter.requires_grad
    )

    parameter_devices = sorted({str(parameter.device) for parameter in model.parameters()})

    parameter_dtypes = sorted({str(parameter.dtype) for parameter in model.parameters()})

    if parameter_devices != [DEVICE]:
        raise RuntimeError(f"Unexpected model parameter devices: {parameter_devices!r}.")

    if parameter_dtypes != [f"torch.{DTYPE}"]:
        raise RuntimeError(f"Unexpected model parameter dtypes: {parameter_dtypes!r}.")

    if total != EXPECTED_PEFT_TOTAL_PARAMETERS:
        raise RuntimeError(f"Unexpected PEFT total parameter count: {total}.")

    if trainable != EXPECTED_TRAINABLE_PARAMETERS:
        raise RuntimeError(f"Unexpected trainable parameter count: {trainable}.")

    trainable_names = [
        name for name, parameter in model.named_parameters() if parameter.requires_grad
    ]

    unexpected = [
        name
        for name in trainable_names
        if ("lora_A" not in name and "lora_B" not in name and "classifier" not in name)
    ]

    if unexpected:
        raise RuntimeError(f"Unexpected trainable parameters: {unexpected!r}.")

    lora_a = [name for name in trainable_names if "lora_A" in name]

    lora_b = [name for name in trainable_names if "lora_B" in name]

    classifier = [name for name in trainable_names if "classifier" in name]

    pooler = [name for name in trainable_names if "pooler" in name]

    if len(lora_a) != 24:
        raise RuntimeError("Expected 24 LoRA-A parameter tensors.")

    if len(lora_b) != 24:
        raise RuntimeError("Expected 24 LoRA-B parameter tensors.")

    if len(classifier) != 2:
        raise RuntimeError("Expected exactly two trainable classifier tensors.")

    if pooler:
        raise RuntimeError("Pooler must remain frozen.")

    return {
        "total_parameters": (total),
        "trainable_parameters": (trainable),
        "trainable_percent": (100.0 * trainable / total),
        "lora_A_tensors": (len(lora_a)),
        "lora_B_tensors": (len(lora_b)),
        "classifier_tensors": (len(classifier)),
        "parameter_devices": (parameter_devices),
        "parameter_dtypes": (parameter_dtypes),
        "unexpected_trainable": (unexpected),
        "pooler_trainable": (pooler),
    }


def build_lora_model(
    seed: int,
):
    seed_everything(seed)

    base = AutoModelForSequenceClassification.from_pretrained(
        MODEL_ID,
        revision=MODEL_REVISION,
        num_labels=7,
        id2label=ID2LABEL,
        label2id=LABEL2ID,
        ignore_mismatched_sizes=True,
        trust_remote_code=False,
        use_safetensors=True,
    )

    base_parameters = sum(parameter.numel() for parameter in base.parameters())

    if base_parameters != EXPECTED_BASE_PARAMETERS:
        raise RuntimeError(f"Unexpected seven-class base parameter count: {base_parameters}.")

    config = LoraConfig(
        task_type=(TaskType.SEQ_CLS),
        inference_mode=False,
        r=LORA_R,
        lora_alpha=(LORA_ALPHA),
        lora_dropout=(LORA_DROPOUT),
        target_modules=list(LORA_TARGET_MODULES),
        bias=LORA_BIAS,
        modules_to_save=list(LORA_MODULES_TO_SAVE),
    )

    model = get_peft_model(
        base,
        config,
    )

    model.to(DEVICE)

    audit = _audit_model_parameters(model)

    return (
        model,
        audit,
    )


def evaluate_model(
    model,
    tokenizer,
    cases: Sequence[RoutingCase],
) -> dict[str, object]:
    model.eval()

    predicted: list[RouteLabel] = []

    probabilities: list[
        dict[
            RouteLabel,
            float,
        ]
    ] = []

    with torch.no_grad():
        for start in range(
            0,
            len(cases),
            BATCH_SIZE,
        ):
            batch_cases = cases[start : start + BATCH_SIZE]

            questions = [normalize_question(case.question) for case in batch_cases]

            encoded = tokenizer(
                questions,
                padding=True,
                truncation=True,
                max_length=MAX_LENGTH,
                return_tensors="pt",
            )

            logits = model(**encoded).logits

            probs = torch.softmax(
                logits,
                dim=-1,
            )

            indices = probs.argmax(dim=-1).tolist()

            for row_index, label_id in enumerate(indices):
                route = ID2LABEL[int(label_id)]

                predicted.append(route)

                probabilities.append(
                    {
                        candidate: float(
                            probs[
                                row_index,
                                LABEL2ID[candidate],
                            ].item()
                        )
                        for candidate in ROUTE_ORDER
                    }
                )

    return evaluate_route_predictions(
        cases,
        predicted,
        probability_rows=(probabilities),
    )


def _save_adapter(
    model,
    adapter_dir: Path,
) -> None:
    shutil.rmtree(
        adapter_dir,
        ignore_errors=True,
    )

    adapter_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    model.save_pretrained(
        adapter_dir,
        safe_serialization=True,
    )

    readme = adapter_dir / "README.md"

    if readme.exists():
        readme.unlink()

    adapter_manifest(adapter_dir)


def train_one_seed(
    *,
    seed: int,
    train_cases: Sequence[RoutingCase],
    development_cases: Sequence[RoutingCase],
    tokenizer,
    output_dir: Path,
) -> dict[str, object]:
    if seed not in TRAINING_SEEDS:
        raise ValueError("Training seed is not in frozen seed set.")

    model, parameter_audit = build_lora_model(seed)

    trainable_parameters = [
        parameter for parameter in model.parameters() if parameter.requires_grad
    ]

    optimizer = torch.optim.AdamW(
        trainable_parameters,
        lr=LEARNING_RATE,
        weight_decay=(WEIGHT_DECAY),
    )

    epoch_records: list[dict[str, object]] = []

    development_by_epoch: dict[
        int,
        dict[str, object],
    ] = {}

    adapter_dir = output_dir / f"seed-{seed}" / "best_adapter"

    for epoch in range(
        1,
        EPOCHS + 1,
    ):
        model.train()

        permutation = epoch_permutation(
            len(train_cases),
            seed=seed,
            epoch=epoch,
        )

        batch_losses: list[float] = []

        for start in range(
            0,
            len(permutation),
            BATCH_SIZE,
        ):
            indices = permutation[start : start + BATCH_SIZE]

            batch_cases = [train_cases[index] for index in indices]

            questions = [normalize_question(case.question) for case in batch_cases]

            labels = torch.tensor(
                [LABEL2ID[case.route_label] for case in batch_cases],
                dtype=torch.long,
            )

            encoded = tokenizer(
                questions,
                padding=True,
                truncation=True,
                max_length=MAX_LENGTH,
                return_tensors="pt",
            )

            optimizer.zero_grad(set_to_none=True)

            output = model(
                **encoded,
                labels=labels,
            )

            loss = output.loss

            if loss is None or not torch.isfinite(loss):
                raise RuntimeError("Training produced non-finite loss.")

            loss.backward()

            frozen_with_grad = [
                name
                for name, parameter in model.named_parameters()
                if (not parameter.requires_grad and parameter.grad is not None)
            ]

            if frozen_with_grad:
                raise RuntimeError("Frozen parameters received gradients.")

            torch.nn.utils.clip_grad_norm_(
                trainable_parameters,
                max_norm=(MAX_GRAD_NORM),
            )

            optimizer.step()

            batch_losses.append(float(loss.detach()))

        development = evaluate_model(
            model,
            tokenizer,
            development_cases,
        )

        development_by_epoch[epoch] = development

        record = {
            "epoch": (epoch),
            "mean_train_loss": (mean(batch_losses)),
            "metrics": (development["metrics"]),
        }

        epoch_records.append(record)

        best_so_far = select_best_epoch(epoch_records)

        if best_so_far["epoch"] == epoch:
            _save_adapter(
                model,
                adapter_dir,
            )

    best = select_best_epoch(epoch_records)

    best_epoch = int(best["epoch"])

    best_development = development_by_epoch[best_epoch]

    manifest = adapter_manifest(adapter_dir)

    report = {
        "seed": seed,
        "parameter_audit": (parameter_audit),
        "epochs": (epoch_records),
        "best_epoch": (best["epoch"]),
        "best_development": (best_development),
        "best_metrics": (best["metrics"]),
        "best_adapter_path": (f"seed-{seed}/best_adapter"),
        "best_adapter_manifest": (manifest),
    }

    del model

    gc.collect()

    return report


def load_adapter_for_inference(
    adapter_dir: Path,
):
    seed_everything(0)

    base = AutoModelForSequenceClassification.from_pretrained(
        MODEL_ID,
        revision=MODEL_REVISION,
        num_labels=7,
        id2label=ID2LABEL,
        label2id=LABEL2ID,
        ignore_mismatched_sizes=True,
        trust_remote_code=False,
        use_safetensors=True,
    )

    model = PeftModel.from_pretrained(
        base,
        adapter_dir,
        is_trainable=False,
    )

    model.to(DEVICE)

    model.eval()

    return model


def runtime_versions() -> dict[
    str,
    str,
]:
    return {
        package: (importlib.metadata.version(package))
        for package in (
            "torch",
            "transformers",
            "numpy",
            "peft",
            "accelerate",
        )
    }


def train_lora_experiment(
    routing: RoutingSet,
    *,
    output_dir: Path,
) -> dict[str, object]:
    actual_config_sha = lora_training_config_sha256()

    if actual_config_sha != FROZEN_LORA_TRAINING_CONFIG_SHA256:
        raise RuntimeError("Frozen LoRA training configuration mismatch.")

    versions = runtime_versions()

    if versions["peft"] != PEFT_VERSION:
        raise RuntimeError("Unexpected PEFT version.")

    if versions["accelerate"] != ACCELERATE_VERSION:
        raise RuntimeError("Unexpected Accelerate version.")

    assert_output_dir_empty(output_dir)

    output_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    train_cases, development_cases = partition_routing_cases(routing)

    tokenizer = build_tokenizer()

    seed_reports: list[dict[str, object]] = []

    for seed in TRAINING_SEEDS:
        seed_reports.append(
            train_one_seed(
                seed=seed,
                train_cases=(train_cases),
                development_cases=(development_cases),
                tokenizer=tokenizer,
                output_dir=(output_dir),
            )
        )

    selected = select_best_seed(seed_reports)

    selected_seed = int(selected["seed"])

    selected_adapter = output_dir / str(selected["best_adapter_path"])

    reloaded = load_adapter_for_inference(selected_adapter)

    final_development = evaluate_model(
        reloaded,
        tokenizer,
        development_cases,
    )

    if final_development != selected["best_development"]:
        raise RuntimeError(
            "Reloaded selected adapter does not exactly reproduce the selected development output."
        )

    report = {
        "report_version": (REPORT_VERSION),
        "training_config_sha256": (actual_config_sha),
        "runtime": {
            "device": (DEVICE),
            "dtype": (DTYPE),
            "versions": (versions),
            "torch_num_threads": (torch.get_num_threads()),
            "torch_num_interop_threads": (torch.get_num_interop_threads()),
            "deterministic_algorithms": (torch.are_deterministic_algorithms_enabled()),
        },
        "benchmark": {
            "routing_version": (routing.routing_version),
            "routing_sha256": (routing_seed_sha256(routing)),
            "train_cases": (len(train_cases)),
            "development_cases": (len(development_cases)),
            "original_locked_holdout_evaluated": (ORIGINAL_LOCKED_HOLDOUT_EVALUATED),
        },
        "challenge_guard": {
            "challenge_sha256": (CHALLENGE_SHA256),
            "challenge_evaluated": (CHALLENGE_EVALUATED),
        },
        "seed_reports": (seed_reports),
        "selected_seed": (selected_seed),
        "selected_epoch": (selected["best_epoch"]),
        "selected_adapter_path": (selected["best_adapter_path"]),
        "selected_adapter_manifest": (selected["best_adapter_manifest"]),
        "selected_development_metrics": (final_development["metrics"]),
        "selected_development_cases": (final_development["cases"]),
    }

    report_path = output_dir / "training-report.json"

    write_lora_report(
        report,
        report_path,
    )

    return report
