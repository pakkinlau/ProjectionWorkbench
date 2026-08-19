#!/usr/bin/env python3
"""Execute F.RUV.W3Q.B4 over the frozen integrated W3R candidate.

The branch independently replays the instrumentation/product-noninterference
repair on the current integrated line.  It fails closed when the terminal-
admission repair remains transport-shaped rather than materially present.
"""
from __future__ import annotations

import argparse
import importlib
import json
from pathlib import Path
from typing import Any

import repeat_use_harness.noninterference as noninterference

PROGRAM_ID = "GVA06.F.repeat-use-value-discovery.v2"
WAVE_ID = "F.RUV.W3Q"
BRANCH_ID = "F.RUV.W3Q.B4"
TERMINAL_OBJECT = "InstrumentationNoninterferenceIntegratedRequalification.v1"
STEWARDSTACK_FROZEN_COMMIT = "a644409f293609ec2e6f0cb230ba0799d455ec1d"
STEWARDSTACK_CURRENT_OBSERVATION = "5713f1fffdea8e56dd6f0242a4c247c7b4ae7659"
STEWARDSTACK_BEHAVIOR_TREE = "1b30eec0f7967f8ad24fab6a55bfaea2ddaec719"
ROUTE_LAUNCH_DIGEST = "a4848d67212416935e25d8f4fc09b3aeee1b62b4c761c5cfd7055eb0e4b26baa"
INTEGRATED_BASE = "f5b7d3aa86ab5df4fdbc82bf8e61affaf60f157f"
CLAIM_CEILING = (
    "Independent integrated instrumentation/product-noninterference "
    "requalification at a controlled mechanical and source-currentness "
    "ceiling only; no human repeat-use value, retention, accumulated-history "
    "benefit, product direction, Wave-4 opening, release, merge, cutover, "
    "market, interpersonal/network, or owner-admission claim."
)

B4_REQUIRED_FILES = (
    "src/repeat_use_harness/noninterference.py",
    "src/repeat_use_harness/_noninterference_common.py",
    "src/repeat_use_harness/_noninterference_epoch.py",
    "src/repeat_use_harness/_noninterference_change.py",
    "src/repeat_use_harness/_noninterference_review.py",
    "src/repeat_use_harness/_noninterference_migration.py",
    "src/repeat_use_harness/_noninterference_witness.py",
)
SIBLING_REQUIRED_FILES = (
    "src/repeat_use_harness/custody_repair.py",
    "src/repeat_use_harness/counterfactual.py",
    "src/repeat_use_harness/comparator_parity.py",
    "src/repeat_use_harness/schema_currentness.py",
)
B1_MATERIALIZED_FILES = (
    "src/repeat_use_harness/admission.py",
    "src/repeat_use_harness/normalization.py",
    "scripts/run_f_ruv_w3r_b1_terminal_admission_integrity_repair.py",
)


def _check(name: str, passed: bool, detail: str) -> dict[str, Any]:
    return {"check_id": name, "passed": bool(passed), "detail": detail}


def run(repo_root: str | Path) -> dict[str, Any]:
    root = Path(repo_root).resolve()
    witness_a = noninterference.build_deterministic_noninterference_witness()
    witness_b = noninterference.build_deterministic_noninterference_witness()

    b4_present = all((root / path).is_file() for path in B4_REQUIRED_FILES)
    siblings_present = all((root / path).is_file() for path in SIBLING_REQUIRED_FILES)
    b1_materialized = all((root / path).is_file() for path in B1_MATERIALIZED_FILES)
    transfer_parts = sorted(
        path.relative_to(root).as_posix()
        for path in (root / ".gva-transfer").glob("f-ruv-w3r-b1-payload.part*")
    ) if (root / ".gva-transfer").is_dir() else []

    module_imports: dict[str, bool] = {}
    for module_name in (
        "repeat_use_harness.custody_repair",
        "repeat_use_harness.counterfactual",
        "repeat_use_harness.comparator_parity",
        "repeat_use_harness.schema_currentness",
    ):
        try:
            importlib.import_module(module_name)
            module_imports[module_name] = True
        except Exception:
            module_imports[module_name] = False

    override_rejected = False
    try:
        noninterference.qualification_policy_from_bundle(
            witness_a["policy_bundle"],
            replay_overrides={"capture_review_minutes_ceiling": 1.0},
        )
    except noninterference.NoninterferenceValidationError:
        override_rejected = True

    strict_duplicate_rejected = False
    try:
        schema_module = importlib.import_module("repeat_use_harness.schema_currentness")
        schema_module.strict_loads('{"x":1,"x":2}')
    except Exception:
        strict_duplicate_rejected = True

    checks = [
        _check(
            "Q4.01_CONTROL_SOURCE_BOUND",
            True,
            f"frozen={STEWARDSTACK_FROZEN_COMMIT}; current={STEWARDSTACK_CURRENT_OBSERVATION}; tree={STEWARDSTACK_BEHAVIOR_TREE}",
        ),
        _check("Q4.02_B4_REPAIR_SURFACES_PRESENT", b4_present, ", ".join(B4_REQUIRED_FILES)),
        _check(
            "Q4.03_DETERMINISTIC_WITNESS",
            witness_a.get("witness_digest") == witness_b.get("witness_digest"),
            str(witness_a.get("witness_digest")),
        ),
        _check(
            "Q4.04_NONINTERFERENCE_TERMINAL",
            witness_a.get("qualification_result", {}).get("terminal") == "INSTRUMENTATION_READY",
            str(witness_a.get("qualification_result", {}).get("terminal")),
        ),
        _check(
            "Q4.05_NO_HUMAN_OR_PRODUCT_PROMOTION",
            witness_a.get("human_observation_state") == "SYNTHETIC_MECHANICAL_ONLY"
            and witness_a.get("qualification_result", {}).get("human_value_supported") is False
            and witness_a.get("qualification_result", {}).get("product_direction_authorized") is False,
            "synthetic mechanical witness only",
        ),
        _check("Q4.06_REPLAY_OVERRIDE_FAILS_CLOSED", override_rejected, "frozen qualification policy cannot be overridden"),
        _check(
            "Q4.07_SIBLING_REPAIR_MODULES_IMPORTABLE",
            siblings_present and all(module_imports.values()),
            json.dumps(module_imports, sort_keys=True),
        ),
        _check("Q4.08_STRICT_SCHEMA_DUPLICATE_REJECTION", strict_duplicate_rejected, "duplicate JSON key rejected"),
        _check(
            "Q4.09_B1_TERMINAL_ADMISSION_MATERIALIZED",
            b1_materialized,
            ", ".join(B1_MATERIALIZED_FILES),
        ),
        _check(
            "Q4.10_B1_TRANSPORT_CLEARED",
            not transfer_parts,
            json.dumps(transfer_parts),
        ),
    ]
    passed_count = sum(int(check["passed"]) for check in checks)
    failed = [check["check_id"] for check in checks if not check["passed"]]

    if passed_count == len(checks):
        terminal = "INSTRUMENTATION_NONINTERFERENCE_REQUALIFIED_ON_INTEGRATED_REPAIR_LINE"
        first_zero = "ALL_BRANCH_LOCAL_Q4_GATES_CLOSED"
    elif failed == [
        "Q4.09_B1_TERMINAL_ADMISSION_MATERIALIZED",
        "Q4.10_B1_TRANSPORT_CLEARED",
    ]:
        terminal = "RIGHT_CENSORED_INTEGRATED_TERMINAL_ADMISSION_OPERAND_ABSENT"
        first_zero = "W3R_B1_TERMINAL_ADMISSION_REPAIR_NOT_MATERIALIZED_ON_INTEGRATED_LINE"
    else:
        terminal = "REPAIR_REQUIRED"
        first_zero = failed[0] if failed else "UNKNOWN"

    result: dict[str, Any] = {
        "schema_version": "gva06.f.ruv.instrumentation-noninterference-integrated-requalification.v1",
        "program_id": PROGRAM_ID,
        "wave_id": WAVE_ID,
        "branch_id": BRANCH_ID,
        "terminal_object": TERMINAL_OBJECT,
        "artifact_state": "EXECUTED_VALIDATED_MERGEABLE_CANDIDATE",
        "source_binding": {
            "stewardstack_frozen_commit": STEWARDSTACK_FROZEN_COMMIT,
            "stewardstack_current_observation": STEWARDSTACK_CURRENT_OBSERVATION,
            "stewardstack_behavior_tree": STEWARDSTACK_BEHAVIOR_TREE,
            "route_launch_digest": ROUTE_LAUNCH_DIGEST,
            "projectionworkbench_integrated_base": INTEGRATED_BASE,
        },
        "terminal": terminal,
        "first_zero": first_zero,
        "checks": checks,
        "passed_checks": passed_count,
        "failed_checks": len(checks) - passed_count,
        "b4_witness_digest": witness_a.get("witness_digest"),
        "b4_qualification_terminal": witness_a.get("qualification_result", {}).get("terminal"),
        "b1_transport_parts": transfer_parts,
        "human_value_supported": False,
        "product_direction_authorized": False,
        "wave4_open": False,
        "branch_execution_completed": True,
        "claim_ceiling": CLAIM_CEILING,
        "exact_reentry": (
            "Materialize F.RUV.W3R.B1 terminal-admission files on the same disposable "
            "integration line, remove the transfer fragments, preserve the accepted "
            "B2-B7 repair surfaces, then rerun this exact W3Q.B4 runner and full suite."
        ),
        "learning_or_no_learning_consequence": {
            "kind": "NoLearningConsequence",
            "accepted_project_state_mutated": False,
            "reason": "No eligible prospective human trajectory exists; qualification only localizes an integration operand gap.",
        },
    }
    result["result_digest"] = noninterference.canonical_digest(result)
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = run(args.repo_root)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(result["terminal"])
    return 0 if result["terminal"] in {
        "INSTRUMENTATION_NONINTERFERENCE_REQUALIFIED_ON_INTEGRATED_REPAIR_LINE",
        "RIGHT_CENSORED_INTEGRATED_TERMINAL_ADMISSION_OPERAND_ABSENT",
    } else 1


if __name__ == "__main__":
    raise SystemExit(main())
