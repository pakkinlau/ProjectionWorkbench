#!/usr/bin/env bash
set -euo pipefail

ROOT="$(git rev-parse --show-toplevel)"
cd "$ROOT"
OUT="${1:-/tmp/f-ruv-w3i-b1}"
mkdir -p "$OUT"

BASE=e289a2ff01ee31f2f32e85247a2956a835e3c175
BASE_W2=510c60889d9ed7d3014cb6d9d6607ef7305c141c
B1=bb409dba352825b95eb2176097d43fa13150514e
B2=3434f231f448643e98c75393734f0f1f5e117d54
B3=f626a674a8b10cf3c97b662bb9ab9ef70453ec7d
B4=aaccbe75756f6e5ed4a884ce66146d6e1475b2ed
B5=a97cd81cb861a152e19ea7aa26b3f2f33501c45f
B6=a8d2d7499ff48c884b992dca5e0373d2142bb95d
B7=85dbf8dd8e133e92612a0f6cbb8f4892f78e0c03
B1_PAYLOAD_DIR="$OUT/b1_payload"
B1_PAYLOAD_B64="$OUT/b1_payload.tar.gz.b64"
B1_PAYLOAD_TGZ="$OUT/b1_payload.tar.gz"

for ref in "$BASE" "$BASE_W2" "$B1" "$B2" "$B3" "$B4" "$B5" "$B6" "$B7"; do
  git fetch --no-tags --depth=1 origin "$ref"
done

git merge-base --is-ancestor "$BASE" HEAD
rm -rf "$B1_PAYLOAD_DIR"
mkdir -p "$B1_PAYLOAD_DIR"
mapfile -t B1_PARTS < <(git ls-tree -r --name-only "$B1" -- .gva-transfer | grep '^.gva-transfer/f-ruv-w3r-b1-payload.part' | sort)
test "${#B1_PARTS[@]}" -gt 0
: > "$B1_PAYLOAD_B64"
for path in "${B1_PARTS[@]}"; do
  git show "$B1:$path" >> "$B1_PAYLOAD_B64"
done
base64 -d "$B1_PAYLOAD_B64" > "$B1_PAYLOAD_TGZ"
echo '9fa65396ff8aa47f348cf1b10f12da2be752dd9d9afa87c029f6b0b86303ac6c  '"$B1_PAYLOAD_TGZ" | sha256sum -c -
tar -xzf "$B1_PAYLOAD_TGZ" -C "$B1_PAYLOAD_DIR"
find "$B1_PAYLOAD_DIR" -type f -printf '%P\n' | sort > "$OUT/B1_PAYLOAD_FILE_INDEX.txt"

python - "$B1_PAYLOAD_DIR" "$OUT" "$BASE" <<'PY'
from pathlib import Path
import json, subprocess, sys, tempfile

payload=Path(sys.argv[1]).resolve()
out=Path(sys.argv[2]).resolve()
base=sys.argv[3]
root=Path.cwd().resolve()
skip={'.github/workflows/apply-f-ruv-w3r-b1-payload.yml'}
actions=[]
conflicts=[]

def base_bytes(rel:str):
    p=subprocess.run(['git','show',f'{base}:{rel}'],stdout=subprocess.PIPE,stderr=subprocess.DEVNULL)
    return p.stdout if p.returncode==0 else None

def merge_text(ours:bytes, ancestor:bytes, theirs:bytes, rel:str):
    with tempfile.TemporaryDirectory() as td:
        td=Path(td)
        op=td/'ours'; bp=td/'base'; tp=td/'theirs'
        op.write_bytes(ours); bp.write_bytes(ancestor); tp.write_bytes(theirs)
        p=subprocess.run(['git','merge-file','-p',str(op),str(bp),str(tp)],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        if p.returncode==0:
            return p.stdout
        conflicts.append({'path':rel,'reason':'three_way_conflict','stderr':p.stderr.decode('utf-8','replace')})
        return None

for src in sorted(p for p in payload.rglob('*') if p.is_file()):
    rel=src.relative_to(payload).as_posix()
    if rel in skip or rel.startswith('.gva-transfer/'):
        continue
    dst=root/rel
    incoming=src.read_bytes()
    if not dst.exists():
        dst.parent.mkdir(parents=True,exist_ok=True)
        dst.write_bytes(incoming)
        actions.append({'path':rel,'action':'ADD_B1'})
        continue
    current=dst.read_bytes()
    if current==incoming:
        actions.append({'path':rel,'action':'IDENTICAL'})
        continue
    ancestor=base_bytes(rel)
    if ancestor is None:
        conflicts.append({'path':rel,'reason':'existing_file_without_base_ancestor'})
        continue
    if current==ancestor:
        dst.write_bytes(incoming)
        actions.append({'path':rel,'action':'TAKE_B1_OVER_BASE'})
        continue
    if incoming==ancestor:
        actions.append({'path':rel,'action':'KEEP_CURRENT'})
        continue
    try:
        current.decode('utf-8'); ancestor.decode('utf-8'); incoming.decode('utf-8')
    except UnicodeDecodeError:
        conflicts.append({'path':rel,'reason':'binary_overlap'})
        continue
    merged=merge_text(current,ancestor,incoming,rel)
    if merged is not None:
        dst.write_bytes(merged)
        actions.append({'path':rel,'action':'THREE_WAY_TEXT_MERGE'})

(out/'B1_SEMANTIC_PORT_ACTIONS.json').write_text(json.dumps(actions,indent=2,sort_keys=True)+'\n')
(out/'B1_SEMANTIC_PORT_CONFLICTS.json').write_text(json.dumps(conflicts,indent=2,sort_keys=True)+'\n')
if conflicts:
    raise SystemExit(json.dumps(conflicts,sort_keys=True))
PY

apply_delta() {
  local name="$1" base="$2" head="$3"; shift 3
  local patch="$OUT/${name}.patch"
  git diff --binary "$base" "$head" -- "$@" > "$patch"
  test -s "$patch"
  git apply --3way "$patch"
}

apply_delta B3 "$BASE" "$B3" \
  .github/workflows/f-ruv-w3r-b3-clean-room-fresh-agent-repair.yml \
  docs/f_ruv_w3r_b3_clean_room_fresh_agent_repair.md \
  fixtures/repeat_use/CleanRoomFreshAgentRepair.v1.json \
  fixtures/repeat_use/clean_room_build_requirements.txt \
  receipts/f_ruv_w3r_b3_execution_receipt.md \
  scripts/run_f_ruv_w3r_b3_clean_room_fresh_agent_repair.sh

apply_delta B2 "$BASE" "$B2" \
  .github/workflows/f-ruv-w3r-b2-custody-privacy-burden-repair.yml \
  docs/f_ruv_w3r_b2_custody_privacy_burden_repair.md \
  fixtures/repeat_use/CustodyPrivacyBurdenRepair.v1.json \
  receipts/f_ruv_w3r_b2_execution_receipt.md \
  scripts/run_f_ruv_w3r_b2_custody_privacy_burden_requalification.py \
  src/repeat_use_harness/custody_repair.py \
  tests/test_f_ruv_w3r_b2_custody_privacy_burden_repair.py

apply_delta B5 "$BASE_W2" "$B5" \
  .github/workflows/f-ruv-w3r-b5-counterfactual-assignment-repair.yml \
  docs/f_ruv_w3r_b5_counterfactual_assignment_repair.md \
  fixtures/repeat_use/CounterfactualAssignmentRepair.v1.json \
  fixtures/repeat_use/counterfactual_assignment_repair_scenarios.json \
  receipts/f_ruv_w3r_b5_execution_receipt.md \
  src/repeat_use_harness/counterfactual.py \
  tests/test_counterfactual_assignment_repair.py

apply_delta B6 "$BASE" "$B6" \
  .github/workflows/f-ruv-w3r-b6-comparator-timing-parity-repair.yml \
  docs/f_ruv_w3r_b6_comparator_timing_parity_repair.md \
  receipts/f_ruv_w3r_b6_execution_receipt.md \
  scripts/run_f_ruv_w3r_b6_comparator_timing_parity_repair.py \
  src/repeat_use_harness/comparator_parity.py \
  tests/test_f_ruv_w3r_b6_comparator_timing_parity_repair.py

apply_delta B7 "$BASE_W2" "$B7" \
  .github/workflows/f-ruv-w3r-b7-schema-currentness-replay-repair.yml \
  docs/f_ruv_w3r_b7_schema_currentness_replay_repair.md \
  receipts/f_ruv_w3r_b7_execution_receipt.md \
  scripts/run_f_ruv_w3r_b7_schema_currentness_replay_repair.py \
  src/repeat_use_harness/replay_integrity.py \
  src/repeat_use_harness/schema_currentness.py \
  src/repeat_use_harness/state_membrane.py \
  src/repeat_use_harness/strict_schema.py \
  tests/test_f_ruv_w3r_b7_schema_currentness_replay_repair.py

apply_delta B4 "$BASE_W2" "$B4" \
  .github/workflows/f-ruv-w3r-b4-instrumentation-noninterference.yml \
  docs/f_ruv_w3r_b4_instrumentation_noninterference_repair.md \
  receipts/f_ruv_w3r_b4_execution_receipt.md \
  scripts/run_f_ruv_w3r_b4_noninterference_repair.py \
  src/repeat_use_harness/_noninterference_change.py \
  src/repeat_use_harness/_noninterference_common.py \
  src/repeat_use_harness/_noninterference_epoch.py \
  src/repeat_use_harness/_noninterference_migration.py \
  src/repeat_use_harness/_noninterference_review.py \
  src/repeat_use_harness/_noninterference_witness.py \
  src/repeat_use_harness/noninterference.py \
  tests/_noninterference_test_support.py \
  tests/test_instrumentation_noninterference_change.py \
  tests/test_instrumentation_noninterference_epoch.py \
  tests/test_instrumentation_noninterference_qualification.py

cat > src/repeat_use_harness/harness.py <<'PY'
"""Integrated compatibility re-export for the repeat-use harness."""
from .constants import *
from .core import *
from .admission import *
from .normalization import *
from .replay import *
from .storage import *
from .fixture import *
from .counterfactual import *
from .custody_repair import *
from .comparator_parity import *
from .noninterference import *
# Import last: the repair membrane intentionally overrides legacy public names.
from .schema_currentness import *
PY
cat > src/repeat_use_harness/__init__.py <<'PY'
"""Public surface for the integrated repeat-use value-discovery harness."""
from .harness import *

B2_CASE_SCHEMA = "gva06.f.ruv.oracle-case.v1"

__all__ = [name for name in globals() if not name.startswith("_")]
__version__ = "1.2.1"
PY

rm -rf .gva-transfer
rm -f .github/workflows/apply-f-ruv-w3r-b1-payload.yml

python -m compileall -q src tests scripts
PYTHONPATH=src python -m unittest discover -s tests -v 2>&1 | tee "$OUT/full_unit_suite.txt"

PYTHONPATH=src python scripts/run_f_ruv_w3r_b1_terminal_admission_integrity_repair.py --output "$OUT/TerminalAdmissionIntegrityRepair.v1.json"
python scripts/run_f_ruv_w3r_b2_custody_privacy_burden_requalification.py --output "$OUT/CustodyPrivacyBurdenRepairRequalification.v1.json"
PYTHONPATH=src python scripts/run_f_ruv_w3r_b4_noninterference_repair.py --output "$OUT/InstrumentationNoninterferenceRepair.v1.json"
PYTHONPATH=src python scripts/run_f_ruv_w3r_b6_comparator_timing_parity_repair.py --output "$OUT/ComparatorTimingParityRepair.v1.json" --corpus-output "$OUT/SyntheticTimingParityCorpus.v2.json"
PYTHONPATH=src python scripts/run_f_ruv_w3r_b7_schema_currentness_replay_repair.py --output "$OUT/SchemaCurrentnessReplayRepair.v1.json"
PYTHONPATH=src python scripts/run_f_ruv_w3_b8_independent_measurement_validity_review.py --output "$OUT/IndependentMeasurementValidityReview.after-W3I.v1.json"
bash scripts/run_f_ruv_w3r_b3_clean_room_fresh_agent_repair.sh "$ROOT" "$OUT/CleanRoomFreshAgentRepair.v1.json" 2>&1 | tee "$OUT/clean_room_stdout.txt"

git diff --binary "$BASE" -- \
  . ':(exclude)dist' ':(exclude)build' ':(exclude)*.egg-info' \
  ':(exclude)integration/w3r/b1_patch_parts' \
  > "$OUT/IntegratedW3RRepairAssembly.patch"
git diff --name-status "$BASE" > "$OUT/IntegratedW3RRepairAssembly.name-status.txt"
git diff --stat "$BASE" > "$OUT/IntegratedW3RRepairAssembly.stat.txt"

python - "$OUT" <<'PY'
from pathlib import Path
import hashlib,json,sys
out=Path(sys.argv[1])
def load(name): return json.loads((out/name).read_text())
review=load('IndependentMeasurementValidityReview.after-W3I.v1.json')
terminal=load('TerminalAdmissionIntegrityRepair.v1.json')
b2=load('CustodyPrivacyBurdenRepairRequalification.v1.json')
b4=load('InstrumentationNoninterferenceRepair.v1.json')
b6=load('ComparatorTimingParityRepair.v1.json')
b7=load('SchemaCurrentnessReplayRepair.v1.json')
clean=load('CleanRoomFreshAgentRepair.v1.json')
checks={
 'terminal_admission': terminal.get('terminal_disposition')=='TERMINAL_ADMISSION_INTEGRITY_REPAIRED_AT_CONTROLLED_FIXTURE_CEILING',
 'custody_privacy_burden': b2.get('summary')=={'total':22,'pass':20,'fail':0,'right_censored':2},
 'noninterference': b4['manifest']['terminal']=='INSTRUMENTATION_NONINTERFERENCE_REPAIR_READY',
 'comparator_timing': b6.get('terminal_disposition')=='COMPARATOR_TIMING_PARITY_REPAIR_IMPLEMENTED_AT_CONTROLLED_FIXTURE_CEILING',
 'schema_replay': b7.get('terminal_disposition')=='SCHEMA_CURRENTNESS_REPLAY_REPAIR_PASS',
 'clean_room': clean.get('terminal_disposition')=='CLEAN_ROOM_FRESH_AGENT_REPAIR_PASS',
 'original_measurement_attacks_closed': review.get('executable_attack_summary',{}).get('remaining_gaps')==0,
}
state='INTEGRATED_W3R_REPAIR_ASSEMBLY_PASS_AT_CONTROLLED_LOCAL_CEILING' if all(checks.values()) else 'INTEGRATION_REPAIR_REQUIRED'
report={
 'schema_version':'gva06.f.ruv.integrated-w3r-repair-assembly.v1',
 'artifact_id':'IntegratedW3RRepairAssembly.v1',
 'branch_id':'F.RUV.W3I.B1',
 'artifact_state':'EXECUTED_VALIDATED_MERGEABLE_CANDIDATE' if all(checks.values()) else 'EXECUTED_REPAIR_REQUIRED',
 'terminal_disposition':state,
 'checks':checks,
 'source_heads':{
  'base':'e289a2ff01ee31f2f32e85247a2956a835e3c175','B1':'bb409dba352825b95eb2176097d43fa13150514e',
  'B2':'3434f231f448643e98c75393734f0f1f5e117d54','B3':'f626a674a8b10cf3c97b662bb9ab9ef70453ec7d',
  'B4':'aaccbe75756f6e5ed4a884ce66146d6e1475b2ed','B5':'a97cd81cb861a152e19ea7aa26b3f2f33501c45f',
  'B6':'a8d2d7499ff48c884b992dca5e0373d2142bb95d','B7':'85dbf8dd8e133e92612a0f6cbb8f4892f78e0c03'},
 'combined_patch_sha256':hashlib.sha256((out/'IntegratedW3RRepairAssembly.patch').read_bytes()).hexdigest(),
 'claim_ceiling':'Controlled integration and mechanical qualification preparation only; no human repeat-use value, Wave-4 launch, release, merge, cutover, or owner admission.',
 'first_zero':'INDEPENDENT_W3Q2_REQUALIFICATION_NOT_YET_RUN',
 'exact_reentry':'Freeze the committed integrated target SHA and run independent eight-axis W3Q2 requalification before any prospective human trajectory.'}
encoded=json.dumps(report,sort_keys=True,separators=(',',':')).encode(); report['artifact_digest']=hashlib.sha256(encoded).hexdigest()
(out/'IntegratedW3RRepairAssembly.v1.json').write_text(json.dumps(report,indent=2,sort_keys=True)+'\n')
if not all(checks.values()): raise SystemExit(json.dumps(checks,sort_keys=True))
PY

find "$OUT" -maxdepth 1 -type f -printf '%f\n' | sort > "$OUT/ARTIFACT_INDEX.txt"
(cd "$OUT" && sha256sum * > SHA256SUMS)
echo INTEGRATED_W3R_REPAIR_ASSEMBLY_PASS_AT_CONTROLLED_LOCAL_CEILING
