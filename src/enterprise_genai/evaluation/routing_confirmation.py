from __future__ import annotations

import json
from pathlib import Path
from typing import cast

from enterprise_genai.data.routing_challenge_seed import (
    build_routing_challenge,
    routing_challenge_sha256,
)
from enterprise_genai.data.routing_models import (
    RouteLabel,
    RoutingCase,
    RoutingSet,
)
from enterprise_genai.data.routing_seed import (
    build_routing_seed,
    routing_seed_sha256,
)
from enterprise_genai.evaluation.lora_routing_benchmark import (
    adapter_manifest,
    evaluate_route_predictions,
    sha256_file,
)
from enterprise_genai.evaluation.routing_confirmation_config import (
    CHALLENGE_CASES,
    CHALLENGE_ROUTING_SHA256,
    DEVELOPMENT_RESULT_COMMIT,
    EVALUATION_ORDER,
    EXPERIMENT_VERSION,
    FROZEN_ROUTING_CONFIRMATION_CONFIG_SHA256,
    LORA_TRAINING_CONFIG_SHA256,
    NLI_CONFIG_SHA256,
    ORIGINAL_HOLDOUT_CASES,
    ORIGINAL_ROUTING_SHA256,
    ROUTER_ORDER,
    SELECTED_ADAPTER_CONFIG_SHA256,
    SELECTED_ADAPTER_MODEL_SHA256,
    SELECTED_ADAPTER_RELATIVE_PATH,
    SELECTED_EPOCH,
    SELECTED_SEED,
    TRAINING_REPORT_RELATIVE_PATH,
    TRAINING_REPORT_SHA256,
    routing_confirmation_config_payload,
    routing_confirmation_config_sha256,
)
from enterprise_genai.routing.heuristic import (
    HeuristicRouter,
)
from enterprise_genai.routing.lora_trainer import (
    build_tokenizer,
    configure_runtime,
    evaluate_model,
    load_adapter_for_inference,
)
from enterprise_genai.routing.lora_training_config import (
    FROZEN_LORA_TRAINING_CONFIG_SHA256,
    lora_training_config_sha256,
)
from enterprise_genai.routing.nli_router import (
    FROZEN_ROUTER_CONFIG_SHA256,
    PretrainedNliRouter,
    nli_router_config_sha256,
)


def _locked_cases(
    routing: RoutingSet,
    *,
    expected_cases: int,
) -> list[RoutingCase]:
    cases = [case for case in routing.cases if case.split == "locked_holdout"]

    if len(cases) != expected_cases:
        raise RuntimeError(f"Unexpected locked evaluation case count: {len(cases)}.")

    return cases


def _verify_selected_lora_artifacts(
    repository_root: Path,
) -> Path:
    report_path = repository_root / TRAINING_REPORT_RELATIVE_PATH

    adapter_dir = repository_root / SELECTED_ADAPTER_RELATIVE_PATH

    if sha256_file(report_path) != TRAINING_REPORT_SHA256:
        raise RuntimeError("Frozen LoRA development report fingerprint mismatch.")

    config_path = adapter_dir / "adapter_config.json"

    model_path = adapter_dir / "adapter_model.safetensors"

    if sha256_file(config_path) != SELECTED_ADAPTER_CONFIG_SHA256:
        raise RuntimeError("Selected adapter configuration fingerprint mismatch.")

    if sha256_file(model_path) != SELECTED_ADAPTER_MODEL_SHA256:
        raise RuntimeError("Selected adapter weights fingerprint mismatch.")

    manifest = adapter_manifest(adapter_dir)

    observed = {
        item["name"]: item["sha256"]
        for item in cast(
            list[dict[str, object]],
            manifest["files"],
        )
    }

    if observed != {
        "adapter_config.json": (SELECTED_ADAPTER_CONFIG_SHA256),
        "adapter_model.safetensors": (SELECTED_ADAPTER_MODEL_SHA256),
    }:
        raise RuntimeError("Selected adapter manifest does not match frozen hashes.")

    report = json.loads(report_path.read_text())

    if report["selected_seed"] != SELECTED_SEED:
        raise RuntimeError("Frozen selected seed mismatch.")

    if report["selected_epoch"] != SELECTED_EPOCH:
        raise RuntimeError("Frozen selected epoch mismatch.")

    if report["training_config_sha256"] != LORA_TRAINING_CONFIG_SHA256:
        raise RuntimeError("Frozen LoRA training configuration mismatch.")

    return adapter_dir


def _evaluate_heuristic(
    cases: list[RoutingCase],
    router: HeuristicRouter,
) -> dict[str, object]:
    labels: list[RouteLabel] = []

    extras: list[dict[str, object]] = []

    for case in cases:
        prediction = router.predict(case.question)

        labels.append(prediction.route_label)

        extras.append(
            {
                "matched_rules": list(prediction.matched_rules),
                "fallback_used": (prediction.fallback_used),
            }
        )

    result = evaluate_route_predictions(
        cases,
        labels,
    )

    case_reports = cast(
        list[dict[str, object]],
        result["cases"],
    )

    for case_report, extra in zip(
        case_reports,
        extras,
        strict=True,
    ):
        case_report.update(extra)

    return {
        "router_metadata": router.metadata(),
        "metrics": result["metrics"],
        "cases": case_reports,
    }


def _evaluate_nli(
    cases: list[RoutingCase],
    router: PretrainedNliRouter,
) -> dict[str, object]:
    labels: list[RouteLabel] = []

    extras: list[dict[str, object]] = []

    for case in cases:
        prediction = router.predict(case.question)

        labels.append(prediction.route_label)

        extras.append(
            {
                "route_scores": [
                    {
                        "route_label": (score.route_label),
                        "hypothesis": (score.hypothesis),
                        "entailment_probability": (score.entailment_probability),
                    }
                    for score in prediction.route_scores
                ],
            }
        )

    result = evaluate_route_predictions(
        cases,
        labels,
    )

    case_reports = cast(
        list[dict[str, object]],
        result["cases"],
    )

    for case_report, extra in zip(
        case_reports,
        extras,
        strict=True,
    ):
        case_report.update(extra)

    return {
        "router_metadata": router.metadata(),
        "metrics": result["metrics"],
        "cases": case_reports,
    }


def _evaluate_lora(
    cases: list[RoutingCase],
    *,
    model,
    tokenizer,
    adapter_dir: Path,
) -> dict[str, object]:
    result = evaluate_model(
        model,
        tokenizer,
        cases,
    )

    return {
        "router_metadata": {
            "router_version": ("lora-router-training-v1"),
            "development_result_commit": (DEVELOPMENT_RESULT_COMMIT),
            "selected_seed": SELECTED_SEED,
            "selected_epoch": SELECTED_EPOCH,
            "training_config_sha256": (LORA_TRAINING_CONFIG_SHA256),
            "adapter_manifest": (adapter_manifest(adapter_dir)),
        },
        "metrics": result["metrics"],
        "cases": result["cases"],
    }


def deterministic_confirmation_report_bytes(
    report: dict[str, object],
) -> bytes:
    payload = json.dumps(
        report,
        indent=2,
        sort_keys=True,
        ensure_ascii=False,
    )

    return (payload + "\n").encode()


def run_routing_confirmation(
    *,
    repository_root: Path,
    output: Path,
) -> dict[str, object]:
    if output.exists():
        raise FileExistsError("Confirmation output already exists.")

    protocol_sha = routing_confirmation_config_sha256()

    if protocol_sha != FROZEN_ROUTING_CONFIRMATION_CONFIG_SHA256:
        raise RuntimeError("Frozen confirmation protocol fingerprint mismatch.")

    if (
        nli_router_config_sha256() != NLI_CONFIG_SHA256
        or NLI_CONFIG_SHA256 != FROZEN_ROUTER_CONFIG_SHA256
    ):
        raise RuntimeError("Frozen NLI configuration mismatch.")

    if (
        lora_training_config_sha256() != LORA_TRAINING_CONFIG_SHA256
        or LORA_TRAINING_CONFIG_SHA256 != FROZEN_LORA_TRAINING_CONFIG_SHA256
    ):
        raise RuntimeError("Frozen LoRA configuration mismatch.")

    adapter_dir = _verify_selected_lora_artifacts(repository_root)

    original = build_routing_seed()

    if routing_seed_sha256(original) != ORIGINAL_ROUTING_SHA256:
        raise RuntimeError("Original routing benchmark fingerprint mismatch.")

    challenge = build_routing_challenge()

    if routing_challenge_sha256(challenge) != CHALLENGE_ROUTING_SHA256:
        raise RuntimeError("Routing challenge fingerprint mismatch.")

    original_cases = _locked_cases(
        original,
        expected_cases=(ORIGINAL_HOLDOUT_CASES),
    )

    challenge_cases = _locked_cases(
        challenge,
        expected_cases=(CHALLENGE_CASES),
    )

    original_ids = {case.routing_id for case in original_cases}

    challenge_ids = {case.routing_id for case in challenge_cases}

    if original_ids & challenge_ids:
        raise RuntimeError("Original holdout and challenge case identifiers overlap.")

    configure_runtime()

    heuristic = HeuristicRouter()
    nli = PretrainedNliRouter()

    tokenizer = build_tokenizer()

    lora = load_adapter_for_inference(adapter_dir)

    datasets = {
        "original_locked_holdout": (original_cases),
        "routing_challenge": (challenge_cases),
    }

    results: dict[
        str,
        object,
    ] = {}

    for dataset_name in EVALUATION_ORDER:
        cases = datasets[dataset_name]

        router_results: dict[
            str,
            object,
        ] = {}

        for router_name in ROUTER_ORDER:
            if router_name == "heuristic":
                router_results[router_name] = _evaluate_heuristic(
                    cases,
                    heuristic,
                )

            elif router_name == "pretrained_nli":
                router_results[router_name] = _evaluate_nli(
                    cases,
                    nli,
                )

            elif router_name == "lora":
                router_results[router_name] = _evaluate_lora(
                    cases,
                    model=lora,
                    tokenizer=tokenizer,
                    adapter_dir=(adapter_dir),
                )

            else:
                raise RuntimeError(f"Unknown frozen router {router_name!r}.")

        routing_version = (
            original.routing_version
            if dataset_name == "original_locked_holdout"
            else challenge.routing_version
        )

        routing_sha = (
            ORIGINAL_ROUTING_SHA256
            if dataset_name == "original_locked_holdout"
            else CHALLENGE_ROUTING_SHA256
        )

        results[dataset_name] = {
            "routing_version": (routing_version),
            "routing_sha256": (routing_sha),
            "cases": len(cases),
            "routers": (router_results),
        }

    report = {
        "experiment_version": (EXPERIMENT_VERSION),
        "confirmation_config_sha256": (protocol_sha),
        "protocol": (routing_confirmation_config_payload()),
        "results": results,
    }

    output.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    output.write_bytes(deterministic_confirmation_report_bytes(report))

    return report
