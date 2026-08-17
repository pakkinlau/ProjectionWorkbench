from __future__ import annotations

import argparse
from pathlib import Path

from .fixtures import fixture_json


def main() -> int:
    parser = argparse.ArgumentParser(prog="project-semantics")
    sub = parser.add_subparsers(dest="command", required=True)
    witness = sub.add_parser("witness", help="emit the deterministic ProjectLens fixture")
    witness.add_argument("--output", type=Path)
    args = parser.parse_args()

    if args.command == "witness":
        text = fixture_json()
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(text, encoding="utf-8")
        else:
            print(text, end="")
        return 0
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
