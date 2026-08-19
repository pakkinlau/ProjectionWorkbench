#!/usr/bin/env bash
set -euo pipefail

repo_root="${1:-$(cd "$(dirname "$0")/.." && pwd)}"
output="${2:-/tmp/CleanRoomFreshAgentRepair.v1.json}"
requirements="$repo_root/fixtures/repeat_use/clean_room_build_requirements.txt"
pinned_result="$repo_root/fixtures/repeat_use/CleanRoomFreshAgentRepair.v1.json"
expected_fixture='87e733e018764d38cce55d00082dc614122b9c8a0fcd19bdc6bffa0f04a34d29'
expected_replay='33b58812596daac7d3f1e6d7fe1776d3bd28e65426c81ded596b6642bd7c5ab2'

test -f "$repo_root/pyproject.toml"
test -f "$requirements"
test -f "$pinned_result"
python - "$requirements" <<'PY'
from pathlib import Path
import sys
lines=[x.strip() for x in Path(sys.argv[1]).read_text().splitlines() if x.strip() and not x.lstrip().startswith('#')]
assert lines and all('==' in x for x in lines), lines
PY

work="$(mktemp -d -t f-ruv-w3r-b3-XXXXXX)"
trap 'rm -rf "$work"' EXIT
mkdir -p "$work/fresh-agent-cwd" "$work/home" "$work/cache"

unset PYTHONPATH PYTHONHOME VIRTUAL_ENV PYTHONSTARTUP PIP_REQUIRE_VIRTUALENV
export HOME="$work/home"
export XDG_CACHE_HOME="$work/cache"
export PIP_CACHE_DIR="$work/cache/pip"
export PIP_CONFIG_FILE=/dev/null
export PIP_DISABLE_PIP_VERSION_CHECK=1
export PIP_NO_CACHE_DIR=1
export PYTHONNOUSERSITE=1
export PYTHONDONTWRITEBYTECODE=1

python -m venv "$work/source-venv"
python -m venv "$work/build-venv"
python -m venv "$work/wheel-venv"
source_py="$work/source-venv/bin/python"
build_py="$work/build-venv/bin/python"
wheel_py="$work/wheel-venv/bin/python"
source_entry="$work/source-venv/bin/pws-ruv"
wheel_entry="$work/wheel-venv/bin/pws-ruv"

"$source_py" -m pip install --no-cache-dir -r "$requirements"
"$build_py" -m pip install --no-cache-dir -r "$requirements"

(
  cd "$work/fresh-agent-cwd"
  PIP_NO_INDEX=1 "$source_py" -m pip install \
    --no-cache-dir --no-deps --no-build-isolation "$repo_root"
)
test -x "$source_entry"
source_module="$(cd "$work/fresh-agent-cwd" && "$source_py" -c \
  'import pathlib,repeat_use_harness; print(pathlib.Path(repeat_use_harness.__file__).resolve())')"
case "$source_module" in "$repo_root"/*) echo "source install leaked repository path" >&2; exit 1;; esac

run_fixture () {
  local entry="$1" out="$2"
  (cd "$work/fresh-agent-cwd" && "$entry" fixture --output "$out")
  python - "$out" "$expected_fixture" "$expected_replay" <<'PY'
import json,sys
from pathlib import Path
root=Path(sys.argv[1])
fixture=json.loads((root/'fixture_receipt.json').read_text())
replay=json.loads((root/'replay.json').read_text())
assert fixture['fixture_digest']==sys.argv[2]
assert replay['replay_digest']==sys.argv[3]
assert replay['trajectory']['causal_terminal']=='RIGHT_CENSORED'
assert replay['trajectory']['evidence_scope']['human_value_supported'] is False
PY
}

run_fixture "$source_entry" "$work/source-a"
run_fixture "$source_entry" "$work/source-b"
diff -ru "$work/source-a" "$work/source-b"

mkdir "$work/wheelhouse"
(
  cd "$work/fresh-agent-cwd"
  PIP_NO_INDEX=1 "$build_py" -m pip wheel \
    --no-cache-dir --no-deps --no-build-isolation \
    --wheel-dir "$work/wheelhouse" "$repo_root"
)
mapfile -t wheels < <(find "$work/wheelhouse" -maxdepth 1 -type f -name '*.whl' -print | sort)
test "${#wheels[@]}" -eq 1
(
  cd "$work/fresh-agent-cwd"
  PIP_NO_INDEX=1 "$wheel_py" -m pip install --no-cache-dir --no-deps "${wheels[0]}"
)
test -x "$wheel_entry"
wheel_module="$(cd "$work/fresh-agent-cwd" && "$wheel_py" -c \
  'import pathlib,repeat_use_harness; print(pathlib.Path(repeat_use_harness.__file__).resolve())')"
case "$wheel_module" in "$repo_root"/*) echo "wheel install leaked repository path" >&2; exit 1;; esac

run_fixture "$wheel_entry" "$work/wheel-a"
run_fixture "$wheel_entry" "$work/wheel-b"
diff -ru "$work/wheel-a" "$work/wheel-b"
diff -ru "$work/source-a" "$work/wheel-a"

python - "$pinned_result" <<'PY'
import hashlib,json,sys
from pathlib import Path
path=Path(sys.argv[1]); value=json.loads(path.read_text())
digest=value.pop('artifact_digest')
encoded=json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()
assert hashlib.sha256(encoded).hexdigest()==digest
assert value['terminal_disposition']=='CLEAN_ROOM_FRESH_AGENT_REPAIR_PASS'
assert all(item['result']=='PASS' for item in value['checks'])
PY
mkdir -p "$(dirname "$output")"
cp "$pinned_result" "$output"
echo CLEAN_ROOM_FRESH_AGENT_REPAIR_PASS
python - "$output" <<'PY'
import json,sys
print(json.load(open(sys.argv[1]))['artifact_digest'])
PY
