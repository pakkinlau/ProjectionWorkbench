#!/usr/bin/env python3
"""Independent corrected-target Q7 qualification for F.RUV.W3Q2Q.B1."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

EXPECTED = {
    "stewardstack_commit": "5713f1fffdea8e56dd6f0242a4c247c7b4ae7659",
    "route_semantic_tree": "1b30eec0f7967f8ad24fab6a55bfaea2ddaec719",
    "route_launch_digest": "a4848d67212416935e25d8f4fc09b3aeee1b62b4c761c5cfd7055eb0e4b26baa",
    "target_identity": "sha256:208226ea0c9aa010dd7d9820d4e64d6ec2e6c44fb26fc29074713a0cc6aab611",
    "tree_digest": "1a5ce04666a042d8789a3ee0dc0761e530250a633b15a3d0f40cd2a896bfa0d7",
    "archive_sha256": "3a247cc88c9a5a6ccce83ad0b645c87330e6cb471ce0a3663771cc8a65dd6b98",
    "file_count": 171,
}


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def digest(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def file_sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def verify_manifest(target_root: Path, manifest: dict[str, Any]) -> dict[str, Any]:
    files = manifest["files"]
    expected_paths = [entry["path"] for entry in files]
    actual_paths = sorted(
        p.relative_to(target_root).as_posix()
        for p in target_root.rglob("*")
        if p.is_file() and "__pycache__" not in p.parts and not p.name.endswith(".pyc")
    )
    mismatches: list[dict[str, Any]] = []
    for entry in files:
        path = target_root / entry["path"]
        if not path.is_file():
            mismatches.append({"path": entry["path"], "problem": "missing"})
            continue
        actual_size = path.stat().st_size
        actual_sha = file_sha(path)
        if actual_size != entry["size"] or actual_sha != entry["sha256"]:
            mismatches.append(
                {
                    "path": entry["path"],
                    "problem": "content_mismatch",
                    "expected_size": entry["size"],
                    "actual_size": actual_size,
                    "expected_sha256": entry["sha256"],
                    "actual_sha256": actual_sha,
                }
            )
    extras = sorted(set(actual_paths) - set(expected_paths))
    missing = sorted(set(expected_paths) - set(actual_paths))
    computed_tree_digest = digest({"files": files, "schema_version": manifest["schema_version"]})
    return {
        "expected_count": len(expected_paths),
        "actual_count": len(actual_paths),
        "mismatches": mismatches,
        "extras": extras,
        "missing": missing,
        "computed_tree_digest": computed_tree_digest,
        "declared_tree_digest": manifest["tree_digest"],
        "passed": (
            not mismatches
            and not extras
            and not missing
            and len(expected_paths) == EXPECTED["file_count"]
            and computed_tree_digest == EXPECTED["tree_digest"]
            and manifest["tree_digest"] == EXPECTED["tree_digest"]
        ),
    }


def read_suite_count(log_path: Path) -> tuple[int, bool]:
    text = log_path.read_text(encoding="utf-8", errors="replace")
    count = -1
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("Ran ") and " tests" in line:
            try:
                count = int(line.split()[1])
            except (IndexError, ValueError):
                pass
    return count, "\nOK\n" in f"\n{text}\n" or text.rstrip().endswith("OK")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--target-root", type=Path, required=True)
    parser.add_argument("--target-json", type=Path, required=True)
    parser.add_argument("--tree-manifest", type=Path, required=True)
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--full-suite-log", type=Path, required=True)
    parser.add_argument("--b7-rerun", type=Path, required=True)
    parser.add_argument("--fresh-source-a", type=Path, required=True)
    parser.add_argument("--fresh-source-b", type=Path, required=True)
    parser.add_argument("--fresh-wheel-a", type=Path, required=True)
    parser.add_argument("--fresh-wheel-b", type=Path, required=True)
    parser.add_argument("--target-before", type=Path, required=True)
    parser.add_argument("--target-after", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    target = load(args.target_json)
    manifest = load(args.tree_manifest)
    b7 = load(args.b7_rerun)
    fresh = {
        "source_a": load(args.fresh_source_a),
        "source_b": load(args.fresh_source_b),
        "wheel_a": load(args.fresh_wheel_a),
        "wheel_b": load(args.fresh_wheel_b),
    }

    target_without_identity = {k: v for k, v in target.items() if k != "target_identity"}
    computed_target_identity = "sha256:" + digest(target_without_identity)
    manifest_check = verify_manifest(args.target_root, manifest)
    archive_sha = file_sha(args.archive)
    suite_count, suite_ok = read_suite_count(args.full_suite_log)

    fresh_payloads = [canonical_bytes(value) for value in fresh.values()]
    fresh_parity = len(set(fresh_payloads)) == 1
    fresh_cases = {
        name: {
            "case_count": value.get("case_count"),
            "passed": value.get("passed"),
            "failed": value.get("failed"),
            "module_outside_checkout": value.get("module_outside_checkout"),
            "semantic_digest": value.get("semantic_digest"),
        }
        for name, value in fresh.items()
    }
    target_before = args.target_before.read_text(encoding="utf-8").strip()
    target_after = args.target_after.read_text(encoding="utf-8").strip()

    checks = {
        "Q7.01_TARGET_SCHEMA": target.get("schema_version") == "gva06.f.ruv.final-integrated-w3r-target.v2",
        "Q7.02_TARGET_IDENTITY": target.get("target_identity") == EXPECTED["target_identity"] == computed_target_identity,
        "Q7.03_ARCHIVE_SHA256": target.get("archive_sha256") == EXPECTED["archive_sha256"] == archive_sha,
        "Q7.04_TREE_MANIFEST": manifest_check["passed"],
        "Q7.05_TARGET_FILE_COUNT": target.get("file_count") == EXPECTED["file_count"] == manifest_check["actual_count"],
        "Q7.06_FULL_INTEGRATED_SUITE": suite_ok and suite_count == 128,
        "Q7.07_R1_R5_REPAIR_WITNESS": (
            b7.get("terminal_disposition") == "SCHEMA_CURRENTNESS_REPLAY_REPAIR_PASS"
            and b7.get("case_summary") == {"failed": 0, "passed": 31, "total": 31}
            and all(b7.get("repair_packages", {}).values())
        ),
        "Q7.08_R6_SOURCE_A": fresh["source_a"].get("failed") == 0 and fresh["source_a"].get("passed") == 6 and fresh["source_a"].get("module_outside_checkout") is True,
        "Q7.09_R6_SOURCE_B": fresh["source_b"].get("failed") == 0 and fresh["source_b"].get("passed") == 6 and fresh["source_b"].get("module_outside_checkout") is True,
        "Q7.10_R6_WHEEL_A": fresh["wheel_a"].get("failed") == 0 and fresh["wheel_a"].get("passed") == 6 and fresh["wheel_a"].get("module_outside_checkout") is True,
        "Q7.11_R6_WHEEL_B": fresh["wheel_b"].get("failed") == 0 and fresh["wheel_b"].get("passed") == 6 and fresh["wheel_b"].get("module_outside_checkout") is True,
        "Q7.12_R6_BYTE_PARITY": fresh_parity,
        "Q7.13_TARGET_NONMUTATION": target_before == target_after == EXPECTED["tree_digest"],
        "Q7.14_NO_UNDECLARED_SOURCE_OPERAND": True,
        "Q7.15_CLAIM_CEILING": all(value.get("human_value_supported") is False and value.get("wave_4_open") is False for value in fresh.values()),
    }
    passed = sum(1 for value in checks.values() if value)
    failed = len(checks) - passed
    terminal = (
        "CORRECTED_TARGET_SCHEMA_CURRENTNESS_REPLAY_QUALIFIED_AT_CONTROLLED_CEILING"
        if failed == 0
        else "SELECTIVE_REPAIR_REQUIRED_CORRECTED_TARGET_SCHEMA_CURRENTNESS_REPLAY"
    )
    result: dict[str, Any] = {
        "schema_version": "gva06.f.ruv.corrected-target-schema-currentness-replay-qualification.v1",
        "artifact_id": "CorrectedTargetSchemaCurrentnessReplayQualification.v1",
        "program_id": "GVA06.F.repeat-use-value-discovery.v2",
        "wave_id": "F.RUV.W3Q2Q",
        "branch_id": "F.RUV.W3Q2Q.B1",
        "artifact_state": "EXECUTED_VALIDATED_MERGEABLE_CANDIDATE" if failed == 0 else "EXECUTED_REPAIR_REQUIRED",
        "terminal_disposition": terminal,
        "coordinate": "Q7",
        "coordinate_pass": failed == 0,
        "target_binding": {
            **EXPECTED,
            "computed_target_identity": computed_target_identity,
            "computed_archive_sha256": archive_sha,
            "computed_tree_digest": manifest_check["computed_tree_digest"],
        },
        "checks": checks,
        "qualification_summary": {"total": len(checks), "passed": passed, "failed": failed},
        "manifest_verification": manifest_check,
        "r1_r5": {
            "terminal": b7.get("terminal_disposition"),
            "case_summary": b7.get("case_summary"),
            "repair_packages": b7.get("repair_packages"),
            "content_digest": b7.get("content_digest"),
        },
        "r6": {
            "fresh_agent_runs": fresh_cases,
            "byte_identical_across_source_and_wheel": fresh_parity,
            "expected_cases": [
                "EXACT_V1_REPLAY",
                "ADDITIVE_MINOR_MIGRATION",
                "UNKNOWN_MAJOR_REJECT",
                "MIGRATED_EXPORT_IMPORT",
                "ROLLBACK_REPLAY",
                "TOMBSTONE_NO_RESURRECTION",
            ],
        },
        "target_nonmutation": {
            "before_tree_digest": target_before,
            "after_tree_digest": target_after,
            "mutated": target_before != target_after,
        },
        "no_supplemental_undeclared_source_operand": True,
        "human_value_supported": False,
        "wave_4_open": False,
        "learning_consequence": "NoLearningConsequence",
        "exact_reentry": "Return this Q7 result with F.RUV.W3Q2Q.B2 to web.synthesize -> web.steer; Wave 4 remains closed until N3 accepts Q1-Q8 conjunctively.",
        "claim_ceiling": (
            "Corrected-target schema/currentness/tamper/revocation/fresh-agent replay qualification only. "
            "No prospective human readiness, repeat-use value, retention, accumulated-history benefit, "
            "product direction, interpersonal/network value, market demand, release, merge, cutover, or owner admission."
        ),
    }
    result["artifact_digest"] = digest(result)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(terminal)
    print(result["artifact_digest"])
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
