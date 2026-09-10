from __future__ import annotations

import argparse
from pathlib import Path

from enterprise_genai.data.routing_seed import (
    build_routing_seed,
)
from enterprise_genai.routing.lora_trainer import (
    configure_runtime,
    train_lora_experiment,
)
from enterprise_genai.routing.lora_training_config import (
    FROZEN_LORA_TRAINING_CONFIG_SHA256,
    lora_training_config_sha256,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=("Run the preregistered three-seed PEFT/LoRA routing training experiment.")
    )

    parser.add_argument(
        "--output-dir",
        type=Path,
        required=True,
    )

    return parser.parse_args()


def main() -> None:
    args = parse_args()

    actual_config_sha = lora_training_config_sha256()

    if actual_config_sha != FROZEN_LORA_TRAINING_CONFIG_SHA256:
        raise RuntimeError("Frozen Phase 8C training configuration mismatch.")

    configure_runtime()

    routing = build_routing_seed()

    report = train_lora_experiment(
        routing,
        output_dir=(args.output_dir),
    )

    metrics = report["selected_development_metrics"]

    print(
        "training_config_sha256:",
        actual_config_sha,
    )

    print(
        "selected_seed:",
        report["selected_seed"],
    )

    print(
        "selected_epoch:",
        report["selected_epoch"],
    )

    print(
        "exact_route_set_accuracy:",
        metrics["exact_route_set_accuracy"],
    )

    print(
        "macro_f1:",
        metrics["macro_f1"],
    )

    print(
        "required_tool_omission_rate:",
        metrics["required_tool_omission_rate"],
    )

    print(
        "unnecessary_tool_addition_rate:",
        metrics["unnecessary_tool_addition_rate"],
    )

    print(
        "challenge_evaluated:",
        False,
    )

    print(
        "report_written:",
        args.output_dir / "training-report.json",
    )


if __name__ == "__main__":
    main()
