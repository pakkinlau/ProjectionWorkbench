from pathlib import Path
import tempfile
from project_semantics import run_witness
ROOT=Path(__file__).resolve().parents[1]
with tempfile.TemporaryDirectory(prefix="pws-replay-") as tmp:
    result=run_witness(ROOT/"fixtures"/"first_witness"/"bundle.json",Path(tmp)/"project",Path(tmp)/"out")
    if not result["passed"]: raise SystemExit(1)
    print(result["witness_id"]); print(result["project_export_digest"])
