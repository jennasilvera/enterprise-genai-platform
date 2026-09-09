from __future__ import annotations

import argparse
from pathlib import Path

from enterprise_genai.data.routing_seed import (
    build_routing_seed,
    routing_seed_sha256,
)
from enterprise_genai.evaluation.routing_benchmark import (
    run_heuristic_router_benchmark,
    write_routing_report,
)
from enterprise_genai.routing.heuristic import (
    HeuristicRouter,
)

EXPECTED_ROUTING_SHA256 = "995f707a4cc6393f0e916f903cc57f9aec6fbabb3c43a00a78e318ca505b6912"

GROUND_TRUTH_COMMIT = "e0755e81d3d1fa24577dbe4e0dd7a92c00247863"

GROUND_TRUTH_TAG = "phase-8a1-routing-ground-truth"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Evaluate the preregistered heuristic router on the frozen routing development split."
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

    routing = build_routing_seed()

    actual_sha256 = routing_seed_sha256(routing)

    if actual_sha256 != EXPECTED_ROUTING_SHA256:
        raise RuntimeError(
            "Frozen routing benchmark "
            "fingerprint mismatch: "
            f"expected "
            f"{EXPECTED_ROUTING_SHA256}, "
            f"got {actual_sha256}."
        )

    router = HeuristicRouter()

    report = run_heuristic_router_benchmark(
        routing,
        split="development",
        router=router,
    )

    report["ground_truth_source"] = {
        "commit": (GROUND_TRUTH_COMMIT),
        "tag": (GROUND_TRUTH_TAG),
        "sha256": (EXPECTED_ROUTING_SHA256),
        "development_cases": 28,
        "locked_holdout_used": False,
    }

    write_routing_report(
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
        actual_sha256,
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
        "report_written:",
        args.output,
    )


if __name__ == "__main__":
    main()
