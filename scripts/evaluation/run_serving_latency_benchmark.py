from __future__ import annotations

from enterprise_genai.evaluation.serving_latency_benchmark import (
    run_benchmark,
)


def main() -> None:
    path = run_benchmark()

    print(
        "latency_result_path:",
        path,
    )


if __name__ == "__main__":
    main()
