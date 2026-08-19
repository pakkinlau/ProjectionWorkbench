"""CLI for deterministic repeat-use harness mechanics."""
from __future__ import annotations

import argparse
from pathlib import Path
from typing import Sequence

from .harness import (
    build_harness_manifest,
    load_json,
    materialize_fixture,
    read_jsonl,
    replay,
    write_json,
)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="pws-ruv")
    sub = parser.add_subparsers(dest="command", required=True)

    fixture = sub.add_parser("fixture", help="materialize deterministic R0 fixture")
    fixture.add_argument("--output", required=True)

    manifest = sub.add_parser("manifest", help="write harness manifest")
    manifest.add_argument("--output", required=True)

    run = sub.add_parser("replay", help="replay an append-only event log")
    run.add_argument("--epoch", required=True)
    run.add_argument("--assignment", required=True)
    run.add_argument("--consent", required=True)
    run.add_argument("--events", required=True)
    run.add_argument("--thresholds")
    run.add_argument("--review")
    run.add_argument("--output", required=True)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.command == "fixture":
        result = materialize_fixture(Path(args.output))
        print(result["fixture_digest"])
        return 0 if result["passed"] else 1
    if args.command == "manifest":
        value = build_harness_manifest()
        write_json(args.output, value)
        print(value["artifact_digest"])
        return 0
    if args.command == "replay":
        thresholds = load_json(args.thresholds) if args.thresholds else None
        review = load_json(args.review) if args.review else None
        value = replay(
            read_jsonl(args.events),
            epoch=load_json(args.epoch),
            assignment=load_json(args.assignment),
            consent=load_json(args.consent),
            thresholds=thresholds,
            independent_review=review,
        )
        write_json(args.output, value)
        print(value["replay_digest"])
        return 0
    raise AssertionError("unreachable")


if __name__ == "__main__":
    raise SystemExit(main())
