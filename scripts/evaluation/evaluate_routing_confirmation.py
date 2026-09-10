from __future__ import annotations

import argparse
from pathlib import Path

from enterprise_genai.evaluation.routing_confirmation import (
    run_routing_confirmation,
)
from enterprise_genai.evaluation.routing_confirmation_config import (
    FROZEN_ROUTING_CONFIRMATION_CONFIG_SHA256,
    routing_confirmation_config_sha256,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=("Run the preregistered locked routing confirmation evaluation.")
    )

    parser.add_argument(
        "--output",
        type=Path,
        required=True,
    )

    return parser.parse_args()


def main() -> None:
    args = parse_args()

    actual = routing_confirmation_config_sha256()

    if actual != FROZEN_ROUTING_CONFIRMATION_CONFIG_SHA256:
        raise RuntimeError("Frozen routing-confirmation configuration mismatch.")

    report = run_routing_confirmation(
        repository_root=Path("."),
        output=args.output,
    )

    print(
        "confirmation_config_sha256:",
        actual,
    )

    for dataset_name in (
        "original_locked_holdout",
        "routing_challenge",
    ):
        print(f"\n=== {dataset_name} ===")

        dataset = report["results"][dataset_name]

        for router_name in (
            "heuristic",
            "pretrained_nli",
            "lora",
        ):
            metrics = dataset["routers"][router_name]["metrics"]

            print(
                router_name,
                "exact",
                metrics["exact_route_set_accuracy"],
                "macro_f1",
                metrics["macro_f1"],
                "omission",
                metrics["required_tool_omission_rate"],
                "addition",
                metrics["unnecessary_tool_addition_rate"],
            )

    print(
        "\nreport_written:",
        args.output,
    )


if __name__ == "__main__":
    main()
