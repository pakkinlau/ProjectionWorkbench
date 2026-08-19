#!/usr/bin/env bash
set -euo pipefail

ROOT="$(git rev-parse --show-toplevel)"
SOURCE_HEAD='d41a17d2558ab8957b055e28f383350a4e06c007'
BASE='e289a2ff01ee31f2f32e85247a2956a835e3c175'
PATCH_SHA='54ad0ee3651b391ff965fb5bc89954e66e061d4e6ff1e8504d090a6b427e5779'
TARGET_ID="sha256:${PATCH_SHA}"
EXPECTED_FIXTURE='de35f75b8fec029126c1566c9d9f8a18745b85d2d4805310262a6f719017321c'
EXPECTED_REPLAY='bbed587ac730812c4b66ed6428142c4fdf9d8b9a92a840c04b472e577bd09f3d'
OUT="${1:-/tmp/f-ruv-w3q2-b3-results}"
TMP="$(mktemp -d -t f-ruv-w3q2-b3-XXXXXX)"
trap 'git -C "$ROOT" worktree prune >/dev/null 2>&1 || true; rm -rf "$TMP"' EXIT
rm -rf "$OUT" && mkdir -p "$OUT"
LOG="$OUT/qualification-execution.log"
: > "$LOG"

logrun() {
  printf '$' >> "$LOG"; printf ' %q' "$@" >> "$LOG"; printf '\n' >> "$LOG"
  "$@" 2>&1 | tee -a "$LOG"
}

prepare_integrator() {
  local work="$1"
  python - "$work/scripts/run_f_ruv_w3i_b1_integrated_w3r_assembly.sh" <<'PY'
from pathlib import Path
import sys
path=Path(sys.argv[1]); text=path.read_text(encoding='utf-8')
replacements=[
("skip={'.github/workflows/apply-f-ruv-w3r-b1-payload.yml'}",
 "skip={'.github/workflows/apply-f-ruv-w3r-b1-payload.yml','scripts/run_f_ruv_w3_b8_independent_measurement_validity_review.py','tests/test_f_ruv_w3_b8_independent_measurement_validity_review.py'}"),
('bash scripts/run_f_ruv_w3r_b3_clean_room_fresh_agent_repair.sh "$ROOT" "$OUT/CleanRoomFreshAgentRepair.v1.json" 2>&1 | tee "$OUT/clean_room_stdout.txt"',
 'python scripts/run_f_ruv_w3i_integrated_clean_room.py "$ROOT" "$OUT/CleanRoomFreshAgentRepair.v1.json" 2>&1 | tee "$OUT/clean_room_stdout.txt"'),
("clean.get('terminal_disposition')=='CLEAN_ROOM_FRESH_AGENT_REPAIR_PASS'",
 "clean.get('terminal_disposition')=='INTEGRATED_CLEAN_ROOM_FRESH_AGENT_PASS'"),
('(cd "$OUT" && sha256sum * > SHA256SUMS)',
 '(cd "$OUT" && find . -maxdepth 1 -type f ! -name SHA256SUMS -print0 | sort -z | xargs -0 sha256sum > SHA256SUMS)'),
]
for old,new in replacements:
    if old not in text: raise SystemExit('integration patch anchor absent: '+old)
    text=text.replace(old,new,1)
path.write_text(text,encoding='utf-8')
PY
}

reconstruct() {
  local label="$1" work="$TMP/assembly-$label" evidence="$TMP/evidence-$label" target="$TMP/target-$label"
  logrun git -C "$ROOT" worktree add --detach "$work" "$SOURCE_HEAD"
  prepare_integrator "$work"
  (cd "$work" && bash scripts/run_f_ruv_w3i_b1_integrated_w3r_assembly.sh "$evidence") 2>&1 | tee -a "$LOG"
  echo "${PATCH_SHA}  $evidence/IntegratedW3RRepairAssembly.patch" | sha256sum -c - | tee -a "$LOG"

  logrun git -C "$ROOT" worktree add --detach "$target" "$BASE"
  logrun git -C "$target" apply --check "$evidence/IntegratedW3RRepairAssembly.patch"
  logrun git -C "$target" apply "$evidence/IntegratedW3RRepairAssembly.patch"
  logrun git -C "$target" add -A
  git -C "$target" write-tree > "$OUT/reconstruction-$label-tree.txt"
  git -C "$target" ls-files -s | LC_ALL=C sort > "$OUT/reconstruction-$label-index.txt"

  cp "$evidence/CleanRoomFreshAgentRepair.v1.json" "$OUT/reconstruction-$label-clean-room.json"
  cp "$evidence/IntegratedW3RRepairAssembly.v1.json" "$OUT/reconstruction-$label-assembly.json"
  python - "$evidence/full_unit_suite.txt" "$OUT/reconstruction-$label-unit-summary.json" <<'PY'
import json,re,sys
text=open(sys.argv[1],encoding='utf-8').read()
m=re.search(r'Ran\s+(\d+)\s+tests?\s+in',text)
ok=text.rstrip().endswith('OK')
out={'total':int(m.group(1)) if m else None,'ok':ok,'failed':0 if ok else None}
open(sys.argv[2],'w',encoding='utf-8').write(json.dumps(out,indent=2,sort_keys=True)+'\n')
if not ok: raise SystemExit('unit suite did not pass')
PY
}

reconstruct a
reconstruct b
cmp "$OUT/reconstruction-a-tree.txt" "$OUT/reconstruction-b-tree.txt"
cmp "$OUT/reconstruction-a-index.txt" "$OUT/reconstruction-b-index.txt"

python - "$OUT" "$TARGET_ID" "$PATCH_SHA" "$EXPECTED_FIXTURE" "$EXPECTED_REPLAY" <<'PY'
from pathlib import Path
import hashlib,json,sys
out=Path(sys.argv[1]); target_id,patch_sha,expected_fixture,expected_replay=sys.argv[2:]
def load(name): return json.loads((out/name).read_text())
def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def digest(value): return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()
a=load('reconstruction-a-clean-room.json'); b=load('reconstruction-b-clean-room.json')
aa=load('reconstruction-a-assembly.json'); ab=load('reconstruction-b-assembly.json')
ta=load('reconstruction-a-unit-summary.json'); tb=load('reconstruction-b-unit-summary.json')
required=['source_source_byte_parity','wheel_wheel_byte_parity','source_wheel_byte_parity','outside_checkout_source','outside_checkout_wheel','right_censored_mechanical_terminal']
checks={
 'same_git_tree':(out/'reconstruction-a-tree.txt').read_bytes()==(out/'reconstruction-b-tree.txt').read_bytes(),
 'same_tracked_index':(out/'reconstruction-a-index.txt').read_bytes()==(out/'reconstruction-b-index.txt').read_bytes(),
 'assembly_a_pass':aa.get('terminal_disposition')=='INTEGRATED_W3R_REPAIR_ASSEMBLY_PASS_AT_CONTROLLED_LOCAL_CEILING',
 'assembly_b_pass':ab.get('terminal_disposition')=='INTEGRATED_W3R_REPAIR_ASSEMBLY_PASS_AT_CONTROLLED_LOCAL_CEILING',
 'unit_suite_a_pass':ta.get('ok') is True and ta.get('failed')==0,
 'unit_suite_b_pass':tb.get('ok') is True and tb.get('failed')==0,
 'clean_room_a_pass':a.get('terminal_disposition')=='INTEGRATED_CLEAN_ROOM_FRESH_AGENT_PASS',
 'clean_room_b_pass':b.get('terminal_disposition')=='INTEGRATED_CLEAN_ROOM_FRESH_AGENT_PASS',
 'frozen_fixture_match':a.get('fixture_digest')==b.get('fixture_digest')==expected_fixture,
 'frozen_replay_match':a.get('replay_digest')==b.get('replay_digest')==expected_replay,
 'clean_room_checks_a':all(a.get('checks',{}).get(k) is True for k in required) and a.get('checks',{}).get('human_value_supported') is False,
 'clean_room_checks_b':all(b.get('checks',{}).get(k) is True for k in required) and b.get('checks',{}).get('human_value_supported') is False,
}
passed=all(checks.values())
report={
 'schema_version':'gva06.f.ruv.w3q2.integrated-clean-room-fresh-agent-qualification.v1',
 'artifact_id':'IntegratedCleanRoomFreshAgentQualification.v2',
 'artifact_state':'EXECUTED_VALIDATED_MERGEABLE_CANDIDATE' if passed else 'EXECUTED_REPAIR_REQUIRED',
 'program_id':'GVA06.F.repeat-use-value-discovery.v2','wave_id':'F.RUV.W3Q2','branch_id':'F.RUV.W3Q2.B3',
 'target_identity':target_id,'base_commit':'e289a2ff01ee31f2f32e85247a2956a835e3c175','integrated_patch_sha256':patch_sha,
 'integration_source_head':'d41a17d2558ab8957b055e28f383350a4e06c007',
 'stewardstack_commit':'5713f1fffdea8e56dd6f0242a4c247c7b4ae7659','stewardstack_route_semantic_tree':'1b30eec0f7967f8ad24fab6a55bfaea2ddaec719',
 'route_launch_digest':'a4848d67212416935e25d8f4fc09b3aeee1b62b4c761c5cfd7055eb0e4b26baa',
 'terminal_disposition':'INTEGRATED_CLEAN_ROOM_FRESH_AGENT_QUALIFICATION_PASS' if passed else 'SELECTIVE_REPAIR_REQUIRED',
 'branch_axis_pass':passed,'checks':checks,
 'target_tree_sha1':(out/'reconstruction-a-tree.txt').read_text().strip() if checks['same_git_tree'] else None,
 'tracked_index_sha256':sha(out/'reconstruction-a-index.txt') if checks['same_tracked_index'] else None,
 'reconstruction_a':{'assembly_digest':aa.get('artifact_digest'),'clean_room_digest':a.get('artifact_digest'),'unit_suite':ta,'wheel_sha256':a.get('wheel_sha256')},
 'reconstruction_b':{'assembly_digest':ab.get('artifact_digest'),'clean_room_digest':b.get('artifact_digest'),'unit_suite':tb,'wheel_sha256':b.get('wheel_sha256')},
 'mechanical_witness':{'fixture_digest':expected_fixture,'replay_digest':expected_replay,'causal_terminal':'RIGHT_CENSORED','human_value_supported':False},
 'evidence_scope':{'mechanical_rung':'R0_MECHANICAL','overall_w3q2_gate_satisfied':False,'wave4_open':False},
 'claim_ceiling':'Independent clean-room/fresh-agent qualification at the R0 mechanical ceiling only; no human repeat-use value, Wave-4 opening, product direction, release, merge, cutover, or owner admission.',
 'exact_reentry':'Return to F.RUV.W3Q2.RollingSynthesis; await B1-B2 and B4-B8, then run web.synthesize -> web.steer.' if passed else 'Route only failed B3 coordinates through web.steer -> web.reentry -> local.task and rerun affected W3Q2 qualifiers.',
}
report['artifact_digest']=digest(report)
(out/'IntegratedCleanRoomFreshAgentQualification.v2.json').write_text(json.dumps(report,indent=2,sort_keys=True)+'\n')
summary={'branch_id':report['branch_id'],'target_identity':target_id,'terminal_disposition':report['terminal_disposition'],'branch_axis_pass':passed,'target_tree_sha1':report['target_tree_sha1'],'fixture_digest':expected_fixture,'replay_digest':expected_replay,'tests_a':ta,'tests_b':tb,'wave4_open':False}
(out/'qualification-summary.json').write_text(json.dumps(summary,indent=2,sort_keys=True)+'\n')
if not passed: raise SystemExit(20)
PY

(
  cd "$OUT"
  find . -maxdepth 1 -type f ! -name SHA256SUMS -print0 | sort -z | xargs -0 sha256sum > SHA256SUMS
)
cat "$OUT/qualification-summary.json"
