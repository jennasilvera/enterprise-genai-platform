from __future__ import annotations

import hashlib
import json
from pathlib import Path

from enterprise_genai.evaluation.serving_latency_protocol import (
    latency_protocol_payload,
)

OUTPUT = Path("artifacts/evaluation/phase11c4a/latency-protocol.json")


def main() -> None:
    payload = latency_protocol_payload()

    serialized = (
        json.dumps(
            payload,
            indent=2,
            sort_keys=True,
        )
        + "\n"
    )

    OUTPUT.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    OUTPUT.write_text(
        serialized,
        encoding="utf-8",
    )

    digest = hashlib.sha256(serialized.encode("utf-8")).hexdigest()

    print(
        "protocol_path:",
        OUTPUT,
    )

    print(
        "protocol_sha256:",
        digest,
    )


if __name__ == "__main__":
    main()
