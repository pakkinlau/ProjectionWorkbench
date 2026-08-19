#!/usr/bin/env python3
"""Materialize the deterministic F.RUV.W3R.B4 repair witness."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from repeat_use_harness.noninterference import (
    build_deterministic_noninterference_witness,
)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output",
        default="fixtures/repeat_use_noninterference/InstrumentationNoninterferenceRepair.v1.json",
    )
    args = parser.parse_args()
    target = Path(args.output)
    target.parent.mkdir(parents=True, exist_ok=True)
    witness = build_deterministic_noninterference_witness()
    target.write_text(
        json.dumps(witness, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(f"artifact={witness['artifact_id']}")
    print(f"terminal={witness['manifest']['terminal']}")
    print(f"qualification={witness['qualification_result']['terminal']}")
    print(f"witness_digest={witness['witness_digest']}")


if __name__ == "__main__":
    main()
