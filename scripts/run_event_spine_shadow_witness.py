#!/usr/bin/env python3
from __future__ import annotations
import argparse
import json
from pathlib import Path
from project_semantics.event_spine import run_shadow_migration_witness


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fixture", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    bundle = json.loads(Path(args.fixture).read_text(encoding="utf-8"))
    result = run_shadow_migration_witness(bundle)
    target = Path(args.output)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"terminal": result["terminal"], "checks": result["checks"]}, indent=2, sort_keys=True))
    return 0 if result["terminal"] == "SHADOW_MIGRATION_PARITY_SUPPORTED" else 2


if __name__ == "__main__":
    raise SystemExit(main())
