#!/usr/bin/env python3
"""Integrated clean-room/source-wheel parity qualification for W3I.

Unlike W3R.B3, this witness does not require the pre-integration fixture digest.
It derives the baseline from the first fresh source installation, then requires
byte-identical source/source, wheel/wheel, and source/wheel outputs while
preserving the mechanical RIGHT_CENSORED / no-human-value ceiling.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile


def run(cmd, *, cwd=None, env=None, capture=False):
    return subprocess.run(
        cmd, cwd=cwd, env=env, check=True,
        text=True, stdout=subprocess.PIPE if capture else None,
        stderr=subprocess.STDOUT if capture else None,
    )


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def fixture(entry: Path, cwd: Path, out: Path, env: dict[str, str]) -> dict:
    run([str(entry), "fixture", "--output", str(out)], cwd=cwd, env=env)
    receipt=json.loads((out/"fixture_receipt.json").read_text())
    replay=json.loads((out/"replay.json").read_text())
    assert replay["trajectory"]["causal_terminal"] == "RIGHT_CENSORED"
    assert replay["trajectory"]["evidence_scope"]["human_value_supported"] is False
    return {
        "fixture_digest": receipt["fixture_digest"],
        "replay_digest": replay["replay_digest"],
        "fixture_receipt_sha256": sha(out/"fixture_receipt.json"),
        "replay_sha256": sha(out/"replay.json"),
    }


def tree_digest(root: Path) -> str:
    h=hashlib.sha256()
    for p in sorted(x for x in root.rglob("*") if x.is_file()):
        h.update(p.relative_to(root).as_posix().encode()); h.update(b"\0"); h.update(p.read_bytes()); h.update(b"\0")
    return h.hexdigest()


def main() -> int:
    ap=argparse.ArgumentParser(); ap.add_argument("repo_root", type=Path); ap.add_argument("output", type=Path)
    ns=ap.parse_args(); repo=ns.repo_root.resolve(); output=ns.output.resolve()
    requirements=repo/"fixtures/repeat_use/clean_room_build_requirements.txt"
    lines=[x.strip() for x in requirements.read_text().splitlines() if x.strip() and not x.lstrip().startswith("#")]
    assert lines and all("==" in x for x in lines)
    with tempfile.TemporaryDirectory(prefix="f-ruv-w3i-clean-") as td:
        work=Path(td); cwd=work/"fresh-agent-cwd"; cwd.mkdir(); (work/"home").mkdir(); (work/"cache").mkdir()
        env=dict(os.environ)
        for key in ("PYTHONPATH","PYTHONHOME","VIRTUAL_ENV","PYTHONSTARTUP","PIP_REQUIRE_VIRTUALENV"):
            env.pop(key,None)
        env.update({
            "HOME":str(work/"home"), "XDG_CACHE_HOME":str(work/"cache"), "PIP_CACHE_DIR":str(work/"cache/pip"),
            "PIP_CONFIG_FILE":"/dev/null", "PIP_DISABLE_PIP_VERSION_CHECK":"1", "PIP_NO_CACHE_DIR":"1",
            "PYTHONNOUSERSITE":"1", "PYTHONDONTWRITEBYTECODE":"1",
        })
        for name in ("source","build","wheel"):
            run([sys.executable,"-m","venv",str(work/f"{name}-venv")], env=env)
        source_py=work/"source-venv/bin/python"; build_py=work/"build-venv/bin/python"; wheel_py=work/"wheel-venv/bin/python"
        source_entry=work/"source-venv/bin/pws-ruv"; wheel_entry=work/"wheel-venv/bin/pws-ruv"
        run([str(source_py),"-m","pip","install","--no-cache-dir","-r",str(requirements)],env=env)
        run([str(build_py),"-m","pip","install","--no-cache-dir","-r",str(requirements)],env=env)
        install_env=dict(env); install_env["PIP_NO_INDEX"]="1"
        run([str(source_py),"-m","pip","install","--no-cache-dir","--no-deps","--no-build-isolation",str(repo)],cwd=cwd,env=install_env)
        assert source_entry.exists()
        mod=run([str(source_py),"-c","import pathlib,repeat_use_harness; print(pathlib.Path(repeat_use_harness.__file__).resolve())"],cwd=cwd,env=env,capture=True).stdout.strip()
        assert not mod.startswith(str(repo)+os.sep)
        sa=fixture(source_entry,cwd,work/"source-a",env); sb=fixture(source_entry,cwd,work/"source-b",env)
        assert sa==sb and tree_digest(work/"source-a")==tree_digest(work/"source-b")
        wheelhouse=work/"wheelhouse"; wheelhouse.mkdir()
        run([str(build_py),"-m","pip","wheel","--no-cache-dir","--no-deps","--no-build-isolation","--wheel-dir",str(wheelhouse),str(repo)],cwd=cwd,env=install_env)
        wheels=sorted(wheelhouse.glob("*.whl")); assert len(wheels)==1
        run([str(wheel_py),"-m","pip","install","--no-cache-dir","--no-deps",str(wheels[0])],cwd=cwd,env=install_env)
        assert wheel_entry.exists()
        modw=run([str(wheel_py),"-c","import pathlib,repeat_use_harness; print(pathlib.Path(repeat_use_harness.__file__).resolve())"],cwd=cwd,env=env,capture=True).stdout.strip()
        assert not modw.startswith(str(repo)+os.sep)
        wa=fixture(wheel_entry,cwd,work/"wheel-a",env); wb=fixture(wheel_entry,cwd,work/"wheel-b",env)
        assert wa==wb==sa
        assert tree_digest(work/"wheel-a")==tree_digest(work/"wheel-b")==tree_digest(work/"source-a")
        report={
            "schema_version":"gva06.f.ruv.integrated-clean-room-fresh-agent.v1",
            "artifact_id":"IntegratedCleanRoomFreshAgentQualification.v1",
            "terminal_disposition":"INTEGRATED_CLEAN_ROOM_FRESH_AGENT_PASS",
            "fixture_digest":sa["fixture_digest"], "replay_digest":sa["replay_digest"],
            "source_module":mod, "wheel_module":modw, "wheel_sha256":sha(wheels[0]),
            "checks":{
                "source_source_byte_parity":True, "wheel_wheel_byte_parity":True, "source_wheel_byte_parity":True,
                "outside_checkout_source":True, "outside_checkout_wheel":True,
                "right_censored_mechanical_terminal":True, "human_value_supported":False,
            },
            "claim_ceiling":"Integrated clean-room installation and deterministic R0 mechanical replay only; no human repeat-use value, Wave-4 opening, release, merge, cutover, or owner admission.",
        }
        encoded=json.dumps(report,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode(); report["artifact_digest"]=hashlib.sha256(encoded).hexdigest()
        output.parent.mkdir(parents=True,exist_ok=True); output.write_text(json.dumps(report,indent=2,sort_keys=True)+"\n")
        print(report["terminal_disposition"]); print(report["artifact_digest"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
