#!/usr/bin/env python3
from pathlib import Path
import json, sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from project_semantics.source_ingestion import run_personal_value_repair_witness

if len(sys.argv) != 3:
    raise SystemExit("usage: run_personal_value_repair_witness.py WORKSPACE OUTPUT")
result = run_personal_value_repair_witness(
    ROOT / "fixtures" / "personal_value_repair" / "bundle.json",
    sys.argv[1],
    sys.argv[2],
)
print(json.dumps(result, indent=2, sort_keys=True))
raise SystemExit(0 if result["passed"] else 1)
