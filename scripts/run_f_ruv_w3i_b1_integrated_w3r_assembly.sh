#!/usr/bin/env bash
set -euo pipefail

ROOT="$(git rev-parse --show-toplevel)"
cd "$ROOT"
OUT="${1:-/tmp/f-ruv-w3i-b1}"
mkdir -p "$OUT"

BASE=e289a2ff01ee31f2f32e85247a2956a835e3c175
BASE_W2=510c60889d9ed7d3014cb6d9d6607ef7305c141c
B2=3434f231f448643e98c75393734f0f1f5e117d54
B3=f626a674a8b10cf3c97b662bb9ab9ef70453ec7d
B4=aaccbe75756f6e5ed4a884ce66146d6e1475b2ed
B5=a97cd81cb861a152e19ea7aa26b3f2f33501c45f
B6=a8d2d7499ff48c884b992dca5e0373d2142bb95d
B7=85dbf8dd8e133e92612a0f6cbb8f4892f78e0c03
B1_PATCH_PARTS=integration/w3r/b1_patch_parts/part-*
B1_PATCH_B64="$OUT/TerminalAdmissionIntegrityRepair.patch.gz.b64"
B1_PATCH="$OUT/TerminalAdmissionIntegrityRepair.patch"

for ref in "$BASE" "$BASE_W2" "$B2" "$B3" "$B4" "$B5" "$B6" "$B7"; do
  git fetch --no-tags --depth=1 origin "$ref"
done

git merge-base --is-ancestor "$BASE" HEAD
cat $B1_PATCH_PARTS > "$B1_PATCH_B64"
base64 -d "$B1_PATCH_B64" | gzip -dc > "$B1_PATCH"
sha256sum "$B1_PATCH" | tee "$OUT/B1_PATCH_SHA256.txt"
# The uploaded B1 return was produced from a route-equivalent predecessor blob set,
# so bind it by its content-addressed index and use Git's three-way application.
git apply --3way "$B1_PATCH"

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

__all__ = [name for name in globals() if not name.startswith("_")]
__version__ = "1.2.0"
PY

python -m compileall -q src tests scripts
PYTHONPATH=src python -m unittest discover -s tests -v 2>&1 | tee "$OUT/full_unit_suite.txt"

PYTHONPATH=src python scripts/run_f_ruv_w3r_b1_terminal_admission_integrity_repair.py --output "$OUT/TerminalAdmissionIntegrityRepair.v1.json"
python scripts/run_f_ruv_w3r_b2_custody_privacy_burden_requalification.py --output "$OUT/CustodyPrivacyBurdenRepairRequalification.v1.json"
PYTHONPATH=src python scripts/run_f_ruv_w3r_b4_noninterference_repair.py --output "$OUT/InstrumentationNoninterferenceRepair.v1.json"
PYTHONPATH=src python scripts/run_f_ruv_w3r_b6_comparator_timing_parity_repair.py --output "$OUT/ComparatorTimingParityRepair.v1.json" --corpus-output "$OUT/SyntheticTimingParityCorpus.v2.json"
PYTHONPATH=src python scripts/run_f_ruv_w3r_b7_schema_currentness_replay_repair.py --output "$OUT/SchemaCurrentnessReplayRepair.v1.json"
PYTHONPATH=src python scripts/run_f_ruv_w3_b8_independent_measurement_validity_review.py --output "$OUT/IndependentMeasurementValidityReview.after-W3I.v1.json"

bash scripts/run_f_ruv_w3r_b3_clean_room_fresh_agent_repair.sh "$ROOT" "$OUT/CleanRoomFreshAgentRepair.v1.json" 2>&1 | tee "$OUT/clean_room_stdout.txt"

# Build the integration delta without embedding generated environments or build products.
git diff --binary "$BASE" -- \
  . ':(exclude)dist' ':(exclude)build' ':(exclude)*.egg-info' \
  ':(exclude)integration/w3r/b1_patch_parts' \
  ':(exclude)integration/w3r/TerminalAdmissionIntegrityRepair.patch.gz.b64' \
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
  'base':'e289a2ff01ee31f2f32e85247a2956a835e3c175',
  'B2':'3434f231f448643e98c75393734f0f1f5e117d54','B3':'f626a674a8b10cf3c97b662bb9ab9ef70453ec7d',
  'B4':'aaccbe75756f6e5ed4a884ce66146d6e1475b2ed','B5':'a97cd81cb861a152e19ea7aa26b3f2f33501c45f',
  'B6':'a8d2d7499ff48c884b992dca5e0373d2142bb95d','B7':'85dbf8dd8e133e92612a0f6cbb8f4892f78e0c03'},
 'combined_patch_sha256':hashlib.sha256((out/'IntegratedW3RRepairAssembly.patch').read_bytes()).hexdigest(),
 'claim_ceiling':'Controlled integration and mechanical qualification preparation only; no human repeat-use value, Wave-4 launch, release, merge, cutover, or owner admission.',
 'first_zero':'INDEPENDENT_W3Q_REQUALIFICATION_NOT_YET_RUN',
 'exact_reentry':'Use this assembly artifact as the immutable W3Q source operand; run independent eight-axis requalification before any prospective human trajectory.'}
encoded=json.dumps(report,sort_keys=True,separators=(',',':')).encode(); report['artifact_digest']=hashlib.sha256(encoded).hexdigest()
(out/'IntegratedW3RRepairAssembly.v1.json').write_text(json.dumps(report,indent=2,sort_keys=True)+'\n')
if not all(checks.values()): raise SystemExit(json.dumps(checks,sort_keys=True))
PY

find "$OUT" -type f -printf '%P\n' | sort > "$OUT/ARTIFACT_INDEX.txt"
(cd "$OUT" && sha256sum * > SHA256SUMS)
echo INTEGRATED_W3R_REPAIR_ASSEMBLY_PASS_AT_CONTROLLED_LOCAL_CEILING
