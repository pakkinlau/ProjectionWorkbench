#!/usr/bin/env python3
"""Assemble and validate the bounded F2.W7.B1 integrated candidate."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from project_semantics import source_ingestion
from project_semantics.event_spine import run_shadow_migration_witness
from scripts.run_f2_w6_b1_requalification import run as run_contribution_requalification
from scripts.run_f2_w6_b2_privacy_requalification import run as run_privacy_requalification

ROOT = Path(__file__).resolve().parents[1]
EVENT_FIXTURE = ROOT / "fixtures" / "event_spine_shadow" / "bundle.json"


def run() -> dict[str, Any]:
    contribution = run_contribution_requalification()
    privacy = run_privacy_requalification()
    event_bundle = json.loads(EVENT_FIXTURE.read_text(encoding="utf-8"))
    event_spine = run_shadow_migration_witness(event_bundle)
    source_symbols = (
        "ingest_source_files", "refresh_source_records", "derive_source_lens",
        "run_personal_value_repair_witness",
    )
    checks = {
        "contribution_requalified": contribution.get("terminal") == "PASS" and contribution.get("policy_matches") == 12 and contribution.get("false_accepts") == 0 and contribution.get("false_rejects") == 0,
        "privacy_requalified": privacy.get("terminal") == "QUALIFIED_AT_CONTROLLED_LOCAL_CEILING" and privacy.get("test_count") == 20 and privacy.get("pass_count") == 20 and privacy.get("finding_count") == 0,
        "source_ingestion_repair_present": all(hasattr(source_ingestion, symbol) for symbol in source_symbols),
        "event_shadow_parity": event_spine.get("terminal") == "SHADOW_MIGRATION_PARITY_SUPPORTED" and event_spine.get("checks", {}).get("parity") is True,
        "event_cutover_disabled": event_spine.get("migration", {}).get("canonical_cutover_authorized") is False and event_spine.get("migration", {}).get("mode") == "shadow_compatible_no_cutover",
    }
    passed = all(checks.values())
    return {
        "schema_version": "gva06.f2.integrated-core-repair-shadow-spine-candidate.v1",
        "programme_id": "GVA06.F2.open-work-semantics-mvp.v1",
        "branch_id": "F2.W7.B1",
        "terminal_object": "IntegratedCoreRepairShadowSpineCandidate.v1",
        "terminal": "INTEGRATED_CORE_REPAIR_SHADOW_SPINE_CANDIDATE_READY" if passed else "REPAIR_REQUIRED",
        "passed": passed,
        "checks": checks,
        "canonical_owners": {
            "core": "project_semantics.__init__",
            "contribution_evidence_capability": "project_semantics.contribution",
            "privacy_portability_repair": "project_semantics.privacy_v2",
            "source_ingestion": "project_semantics.source_ingestion",
            "event_provenance_shadow": "project_semantics.event_spine",
        },
        "lineage": {
            "integrated_wave5_base": "35ff5610d6546cb65af4d475551aad0afac65219",
            "contribution_repair": "979917f80c796dbcd88ebbf56bf3952aac5cfbf1",
            "privacy_repair": "dfd12ba65cb521248c607c1bc865edb8c1bb47dc",
            "source_ingestion_repair": "wave6/F2.W6.B3 portable source patch",
            "event_spine_shadow": "ed8ca19aec46f76a859bd626da59f6499e556357",
        },
        "event_spine_cutover_authorized": False,
        "canonical_history_rewritten": False,
        "claim_ceiling": "Coherent local integration candidate and deterministic fixture replay only; no owner merge, event-spine cutover, production security, human value, release, or Wave-7 completion.",
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
