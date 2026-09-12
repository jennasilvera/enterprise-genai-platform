from __future__ import annotations

import argparse
import subprocess
import sys
from importlib.metadata import version
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

PROTO_ROOT = ROOT / "proto"

PROTO_PATH = PROTO_ROOT / "enterprise_genai" / "rpc" / "retrieval" / "v1" / "retrieval.proto"

DEFAULT_OUTPUT_ROOT = ROOT / "src"

GENERATED_RELATIVE_PATHS = (
    Path("enterprise_genai/rpc/retrieval/v1/retrieval_pb2.py"),
    Path("enterprise_genai/rpc/retrieval/v1/retrieval_pb2_grpc.py"),
)

RUFF_HEADER = "# ruff: noqa\n# fmt: off\n"

EXPECTED_GRPCIO_TOOLS_VERSION = "1.81.1"


def validate_generator_version() -> None:
    observed = version("grpcio-tools")

    if observed != EXPECTED_GRPCIO_TOOLS_VERSION:
        raise RuntimeError(
            "grpcio-tools version mismatch: "
            f"expected {EXPECTED_GRPCIO_TOOLS_VERSION}, "
            f"observed {observed}"
        )


def generate(
    output_root: Path,
) -> tuple[Path, ...]:
    validate_generator_version()

    output_root.mkdir(
        parents=True,
        exist_ok=True,
    )

    subprocess.run(
        [
            sys.executable,
            "-m",
            "grpc_tools.protoc",
            f"-I{PROTO_ROOT}",
            f"--python_out={output_root}",
            f"--grpc_python_out={output_root}",
            str(PROTO_PATH),
        ],
        check=True,
    )

    generated = tuple(output_root / relative for relative in GENERATED_RELATIVE_PATHS)

    for path in generated:
        if not path.is_file():
            raise RuntimeError(f"Expected generated file was not created: {path}")

        text = path.read_text(
            encoding="utf-8",
        )

        if not text.startswith(RUFF_HEADER):
            path.write_text(
                RUFF_HEADER + text,
                encoding="utf-8",
            )

    return generated


def main() -> None:
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--output-root",
        type=Path,
        default=DEFAULT_OUTPUT_ROOT,
    )

    args = parser.parse_args()

    for path in generate(args.output_root):
        print(path)


if __name__ == "__main__":
    main()
