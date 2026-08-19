#!/usr/bin/env bash
set -uo pipefail

OUT="$RUNNER_TEMP/gva06-f-ruv-w3q2-b5"
TMP="$RUNNER_TEMP/gva06-f-ruv-w3q2-b5-work"
TARGET="$TMP/target"
ZIP="$TMP/assembly.zip"
ASSEMBLY="$TMP/assembly"
PATCH="$ASSEMBLY/IntegratedW3RRepairAssembly.patch"
BASE="e289a2ff01ee31f2f32e85247a2956a835e3c175"
TARGET_ID="sha256:54ad0ee3651b391ff965fb5bc89954e66e061d4e6ff1e8504d090a6b427e5779"
ARTIFACT_ID="9379960992"
EXPECTED_ZIP="606e400a116d3cd07cd7bcd196973aa8ff954be11d0997ec9e4f5e8cdf81be7f"
EXPECTED_PATCH="54ad0ee3651b391ff965fb5bc89954e66e061d4e6ff1e8504d090a6b427e5779"
mkdir -p "$OUT" "$ASSEMBLY"
exec > >(tee "$OUT/qualification-execution.log") 2>&1

curl --fail --location --retry 3 \
  -H "Authorization: Bearer $GITHUB_TOKEN" \
  -H "Accept: application/vnd.github+json" \
  -H "X-GitHub-Api-Version: 2022-11-28" \
  "https://api.github.com/repos/$GITHUB_REPOSITORY/actions/artifacts/$ARTIFACT_ID/zip" \
  -o "$ZIP"
ZIP_SHA="$(sha256sum "$ZIP" | awk '{print $1}')"
unzip -q "$ZIP" -d "$ASSEMBLY"
PATCH_SHA="$(sha256sum "$PATCH" | awk '{print $1}')"
printf '%s\n' "$ZIP_SHA" > "$OUT/assembly-evidence-zip-sha256.txt"
printf '%s\n' "$PATCH_SHA" > "$OUT/integrated-patch-sha256.txt"

RECON=PASS
[[ "$ZIP_SHA" == "$EXPECTED_ZIP" && "$PATCH_SHA" == "$EXPECTED_PATCH" ]] || RECON=FAIL
if [[ "$RECON" == PASS ]]; then git worktree add --detach "$TARGET" "$BASE" || RECON=FAIL; fi
if [[ "$RECON" == PASS ]]; then
  git -C "$TARGET" apply --check "$PATCH" && git -C "$TARGET" apply --index "$PATCH" || RECON=FAIL
fi
if [[ "$RECON" == PASS ]]; then
  # The frozen assembly artifact carries the B1 add-only payload separately from
  # the combined integration patch. Reconstruct only declared ADD_B1 paths;
  # overlap-owned harness/replay/review surfaces remain those in the patch.
  python - "$ASSEMBLY" "$TARGET" <<'PY'
import json, shutil, sys
from pathlib import Path
assembly=Path(sys.argv[1]); target=Path(sys.argv[2])
actions=json.loads((assembly/'B1_SEMANTIC_PORT_ACTIONS.json').read_text())
conflicts=json.loads((assembly/'B1_SEMANTIC_PORT_CONFLICTS.json').read_text())
assert conflicts == [], conflicts
added=[]
for row in actions:
    path=row['path']
    if row['action'] != 'ADD_B1':
        continue
    source=assembly/'b1_payload'/path
    destination=target/path
    if not source.is_file():
        raise SystemExit(f'missing B1 add-only payload: {path}')
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source,destination)
    added.append(path)
assert added, 'no ADD_B1 payload paths reconstructed'
(target/'.w3q2-b5-b1-add-paths.json').write_text(json.dumps(added,indent=2)+'\n')
PY
  mapfile -t B1_ADD_PATHS < <(python - "$TARGET/.w3q2-b5-b1-add-paths.json" <<'PY'
import json,sys
for path in json.load(open(sys.argv[1])):
    print(path)
PY
)
  git -C "$TARGET" add -- "${B1_ADD_PATHS[@]}"
  rm -f "$TARGET/.w3q2-b5-b1-add-paths.json"
fi
if [[ "$RECON" == PASS ]]; then
  git -C "$TARGET" status --porcelain=v1 > "$OUT/target-status.before.txt"
  sha256sum "$OUT/target-status.before.txt" | awk '{print $1}' > "$OUT/target-status.before.sha256"
  git -C "$TARGET" write-tree > "$OUT/reconstructed-target-tree-sha1.txt"
else
  : > "$OUT/target-status.before.txt"; : > "$OUT/target-status.before.sha256"; : > "$OUT/reconstructed-target-tree-sha1.txt"
fi

FULL=FAIL; B5=FAIL; OLD=NOT_RUN
if [[ "$RECON" == PASS ]]; then
  set +e
  (cd "$TARGET" && PYTHONPATH=src PYTHONNOUSERSITE=1 PYTHONDONTWRITEBYTECODE=1 python -m unittest discover -s tests -v) > "$OUT/full-suite.log" 2>&1
  [[ $? == 0 ]] && FULL=PASS
  (cd "$TARGET" && PYTHONPATH=src PYTHONNOUSERSITE=1 PYTHONDONTWRITEBYTECODE=1 python -m unittest discover -s tests -p 'test_counterfactual_assignment_repair.py' -v) > "$OUT/b5-suite.log" 2>&1
  [[ $? == 0 ]] && B5=PASS
  set -e
  curl --fail --location --retry 3 \
    "https://raw.githubusercontent.com/pakkinlau/ProjectionWorkbench/8923df109668bf69e9dc6966069689f7dff44139/scripts/run_f_ruv_w3q_b5_counterfactual_assignment_requalification.py" \
    -o "$TMP/pr44-b5-qualifier.py"
  (cd "$TARGET" && PYTHONPATH=src PYTHONNOUSERSITE=1 PYTHONDONTWRITEBYTECODE=1 python "$TMP/pr44-b5-qualifier.py" --output "$OUT/CounterfactualAssignmentRequalification.v1.json") > "$OUT/independent-b5.log" 2>&1 && OLD=PASS || OLD=FAIL
  git -C "$TARGET" status --porcelain=v1 > "$OUT/target-status.after.txt"
  sha256sum "$OUT/target-status.after.txt" | awk '{print $1}' > "$OUT/target-status.after.sha256"
else
  printf 'target reconstruction failed\n' > "$OUT/full-suite.log"
  printf 'target reconstruction failed\n' > "$OUT/b5-suite.log"
  printf 'target reconstruction failed\n' > "$OUT/independent-b5.log"
  : > "$OUT/target-status.after.txt"; : > "$OUT/target-status.after.sha256"
fi

export OUT TARGET RECON FULL B5 OLD ZIP_SHA PATCH_SHA TARGET_ID BASE
export GITHUB_RUN_ID GITHUB_SHA GITHUB_REF_NAME GITHUB_REPOSITORY
python scripts/build_f_ruv_w3q2_b5_terminal.py
python scripts/build_f_ruv_w3q2_b5_returns.py

git worktree remove --force "$TARGET" 2>/dev/null || true
git worktree prune || true
rm -rf "$TMP"
