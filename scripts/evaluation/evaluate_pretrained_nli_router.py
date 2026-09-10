from __future__ import annotations

import argparse
from pathlib import Path

from enterprise_genai.data.routing_seed import (
    build_routing_seed,
    routing_seed_sha256,
)
from enterprise_genai.evaluation.nli_routing_benchmark import (
    run_pretrained_nli_router_benchmark,
    write_nli_routing_report,
)
from enterprise_genai.routing.nli_router import (
    FROZEN_ROUTER_CONFIG_SHA256,
    PretrainedNliRouter,
    nli_router_config_sha256,
)

EXPECTED_ROUTING_SHA256 = "995f707a4cc6393f0e916f903cc57f9aec6fbabb3c43a00a78e318ca505b6912"

GROUND_TRUTH_COMMIT = "e0755e81d3d1fa24577dbe4e0dd7a92c00247863"

GROUND_TRUTH_TAG = "phase-8a1-routing-ground-truth"

CHALLENGE_COMMIT = "bea37c093783bcbfb9f66e934f449e56fafa2e06"

CHALLENGE_SHA256 = "e1fc84e80e5cd27cc311da4392e3c9d46375777a27c81bdc5e35e37b5b131867"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Evaluate the frozen pretrained "
            "zero-shot NLI router on the "
            "Northstar development split."
        )
    )

    parser.add_argument(
        "--output",
        type=Path,
        required=True,
    )

    return parser.parse_args()


def main() -> None:
    args = parse_args()

    actual_config_sha256 = nli_router_config_sha256()

    if actual_config_sha256 != FROZEN_ROUTER_CONFIG_SHA256:
        raise RuntimeError("Frozen NLI router configuration mismatch.")

    routing = build_routing_seed()

    actual_routing_sha256 = routing_seed_sha256(routing)

    if actual_routing_sha256 != EXPECTED_ROUTING_SHA256:
        raise RuntimeError(
            "Frozen routing benchmark "
            "fingerprint mismatch: "
            f"expected "
            f"{EXPECTED_ROUTING_SHA256}, "
            f"got "
            f"{actual_routing_sha256}."
        )

    router = PretrainedNliRouter()

    report = run_pretrained_nli_router_benchmark(
        routing,
        split="development",
        router=router,
    )

    report["ground_truth_source"] = {
        "commit": (GROUND_TRUTH_COMMIT),
        "tag": (GROUND_TRUTH_TAG),
        "sha256": (EXPECTED_ROUTING_SHA256),
        "development_cases": 28,
        "original_locked_holdout_used": (False),
    }

    report["challenge_guard"] = {
        "challenge_commit": (CHALLENGE_COMMIT),
        "challenge_sha256": (CHALLENGE_SHA256),
        "challenge_evaluated": (False),
    }

    write_nli_routing_report(
        report,
        args.output,
    )

    metrics = report["metrics"]

    print(
        "experiment_version:",
        report["experiment_version"],
    )

    print(
        "scope:",
        report["scope"],
    )

    print(
        "routing_sha256:",
        actual_routing_sha256,
    )

    print(
        "router_config_sha256:",
        actual_config_sha256,
    )

    print(
        "cases:",
        metrics["cases"],
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
        "challenge_evaluated:",
        False,
    )

    print(
        "report_written:",
        args.output,
    )


if __name__ == "__main__":
    main()
