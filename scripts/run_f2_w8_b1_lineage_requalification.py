#!/usr/bin/env python3
"""Independent F2.W8.B1 requalification of the exact PR17 integrated head."""
from __future__ import annotations

import argparse
import importlib.util
import json
import subprocess
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
EXPECTED = ROOT / "fixtures" / "integrated_head_requalification" / "expected_lineage.json"


def _git(*args: str, check: bool = True) -> str:
    proc = subprocess.run(
        ["git", *args], cwd=ROOT, text=True, capture_output=True, check=False
    )
    if check and proc.returncode:
        raise RuntimeError(proc.stderr.strip() or proc.stdout.strip())
    return proc.stdout.strip()


def _load_run(path: Path, name: str) -> Callable[[], dict[str, Any]]:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    run = getattr(module, "run", None)
    if not callable(run):
        raise RuntimeError(f"{path} has no callable run()")
    return run


def _allowed_delta(candidate: str) -> tuple[bool, list[str]]:
    changed = [
        line for line in _git("diff", "--name-only", f"{candidate}..HEAD").splitlines()
        if line.strip()
    ]
    allowed = (
        ".github/workflows/f2-w8-b1-",
        "docs/f2_w8_b1_",
        "fixtures/integrated_head_requalification/",
        "receipts/f2_w8_b1_",
        "scripts/run_f2_w8_b1_",
        "tests/test_f2_w8_b1_",
    )
    return all(path.startswith(allowed) for path in changed), changed


def run() -> dict[str, Any]:
    expected = json.loads(EXPECTED.read_text(encoding="utf-8"))
    candidate = expected["candidate"]["commit"]

    ancestor = subprocess.run(
        ["git", "merge-base", "--is-ancestor", candidate, "HEAD"],
        cwd=ROOT,
        check=False,
    ).returncode == 0

    actual_blobs: dict[str, str | None] = {}
    for path in expected["candidate_blob_identities"]:
        try:
            actual_blobs[path] = _git("rev-parse", f"{candidate}:{path}")
        except RuntimeError:
            actual_blobs[path] = None
    blob_matches = {
        path: actual_blobs[path] == blob
        for path, blob in expected["candidate_blob_identities"].items()
    }

    delta_ok, changed_paths = _allowed_delta(candidate)

    contribution = _load_run(
        ROOT / "scripts" / "run_f2_w6_b1_requalification.py", "f2w6b1"
    )()
    privacy = _load_run(
        ROOT / "scripts" / "run_f2_w6_b2_privacy_requalification.py", "f2w6b2"
    )()
    integrated = _load_run(
        ROOT / "scripts" / "run_f2_w7_b1_integrated_assembly.py", "f2w7b1"
    )()

    from project_semantics import source_ingestion
    from project_semantics.event_spine import run_shadow_migration_witness

    event_bundle = json.loads(
        (ROOT / "fixtures" / "event_spine_shadow" / "bundle.json").read_text(
            encoding="utf-8"
        )
    )
    event = run_shadow_migration_witness(event_bundle)

    source_symbols = (
        "ingest_source_files",
        "refresh_source_records",
        "derive_source_lens",
        "run_personal_value_repair_witness",
    )
    required_modules = {
        "core": ROOT / "src" / "project_semantics" / "__init__.py",
        "contribution_evidence_capability": ROOT / "src" / "project_semantics" / "contribution.py",
        "privacy_portability_repair": ROOT / "src" / "project_semantics" / "privacy_v2.py",
        "source_ingestion": ROOT / "src" / "project_semantics" / "source_ingestion.py",
        "event_provenance_shadow": ROOT / "src" / "project_semantics" / "event_spine.py",
    }
    owner_files_unique = all(path.is_file() for path in required_modules.values()) and len(
        {path.resolve() for path in required_modules.values()}
    ) == len(required_modules)

    lineage_expected = expected["predecessor_identities"]
    lineage_observed = integrated.get("lineage", {})
    lineage_checks = {
        "integrated_wave5_base": lineage_observed.get("integrated_wave5_base")
        == lineage_expected["integrated_wave5_base"],
        "contribution_repair": lineage_observed.get("contribution_repair")
        == lineage_expected["contribution_repair"],
        "privacy_repair": lineage_observed.get("privacy_repair")
        == lineage_expected["privacy_repair"],
        "event_spine_shadow": lineage_observed.get("event_spine_shadow")
        == lineage_expected["event_spine_shadow"],
        "source_ingestion_materialized": all(
            hasattr(source_ingestion, symbol) for symbol in source_symbols
        ),
    }

    claim_ceiling = str(integrated.get("claim_ceiling", ""))
    claim_ceiling_continuity = all(
        phrase in claim_ceiling
        for phrase in (
            "no owner merge",
            "event-spine cutover",
            "production security",
            "human value",
            "release",
        )
    )

    checks = {
        "exact_candidate_is_ancestor": ancestor,
        "candidate_blob_lineage_exact": all(blob_matches.values()),
        "qualification_delta_only": delta_ok,
        "one_owner_per_public_object": owner_files_unique
        and integrated.get("canonical_owners") == expected["canonical_owners"],
        "predecessor_lineage_exact": all(lineage_checks.values()),
        "contribution_requalification": contribution.get("terminal") == "PASS"
        and contribution.get("policy_matches") == 12
        and contribution.get("false_accepts") == 0
        and contribution.get("false_rejects") == 0,
        "privacy_requalification": privacy.get("terminal")
        == "QUALIFIED_AT_CONTROLLED_LOCAL_CEILING"
        and privacy.get("test_count") == 20
        and privacy.get("pass_count") == 20
        and privacy.get("finding_count") == 0,
        "source_ingestion_generalization_present": all(
            hasattr(source_ingestion, symbol) for symbol in source_symbols
        ),
        "event_shadow_parity": event.get("terminal")
        == "SHADOW_MIGRATION_PARITY_SUPPORTED"
        and event.get("checks", {}).get("parity") is True,
        "compatibility_model_retained": integrated.get("canonical_history_rewritten")
        is False,
        "event_spine_cutover_disabled": integrated.get(
            "event_spine_cutover_authorized"
        )
        is False
        and event.get("migration", {}).get("canonical_cutover_authorized") is False,
        "claim_ceiling_continuity": claim_ceiling_continuity,
    }

    failed = [name for name, passed in checks.items() if not passed]
    if not ancestor or not all(blob_matches.values()):
        terminal = "SOURCE_CURRENTNESS_DRIFT"
    elif not all(lineage_checks.values()):
        terminal = "LINEAGE_GAP"
    elif not claim_ceiling_continuity:
        terminal = "CLAIM_CEILING_DRIFT"
    elif failed:
        terminal = "REPAIR_REQUIRED"
    else:
        terminal = "CURRENT_HEAD_QUALIFIED_FOR_HUMAN_VALUE_PILOT"

    return {
        "schema_version": "gva06.f2.integrated-head-lineage-currentness-requalification.v1",
        "programme_id": "GVA06.F2.open-work-semantics-mvp.v1",
        "branch_id": "F2.W8.B1",
        "terminal_object": "IntegratedHeadLineageCurrentnessRequalification.v1",
        "candidate": expected["candidate"],
        "observed_qualification_head": _git("rev-parse", "HEAD"),
        "checks": checks,
        "failed_checks": failed,
        "blob_matches": blob_matches,
        "actual_candidate_blobs": actual_blobs,
        "lineage_checks": lineage_checks,
        "changed_paths_after_candidate": changed_paths,
        "terminal": terminal,
        "passed": not failed,
        "human_value_pilot_gate": "OPEN" if not failed else "CLOSED",
        "event_spine_cutover_authorized": False,
        "canonical_history_rewritten": False,
        "claim_ceiling": "Independent exact-head lineage/currentness and clean-room fixture qualification only; no owner merge, release, production security, human-observed value, event-spine cutover, or Wave-8 completion.",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    payload = run()
    text = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding="utf-8")
    else:
        print(text, end="")
    return 0 if payload["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
