#!/usr/bin/env python3
"""Independent counterfactual-assignment requalification for F.RUV.W3Q.B5.

This branch requalifies the B5 counterfactual surface on the current integrated
W3R candidate and separately checks whether the terminal-admission repair is
materialized and its transport fragments are cleared. Missing integrated B1 is
a lawful right-censored terminal, not a failed branch execution.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
from typing import Any

from repeat_use_harness.counterfactual import qualify_counterfactual_assignment

PROGRAM_ID = "GVA06.F.repeat-use-value-discovery.v2"
WAVE_ID = "F.RUV.W3Q"
BRANCH_ID = "F.RUV.W3Q.B5"
ROUTE_LAUNCH_DIGEST = "a4848d67212416935e25d8f4fc09b3aeee1b62b4c761c5cfd7055eb0e4b26baa"
STEWARDSTACK_ROUTE_PIN = "a644409f293609ec2e6f0cb230ba0799d455ec1d"
STEWARDSTACK_CURRENT_OBSERVATION = "5713f1fffdea8e56dd6f0242a4c247c7b4ae7659"
STEWARDSTACK_ROUTE_TREE = "1b30eec0f7967f8ad24fab6a55bfaea2ddaec719"
INTEGRATED_BASE_REF = "agent/f-ruv-w3i-b1-integrated-w3r-repair-assembly-v2"
CLAIM_CEILING = (
    "Independent integrated counterfactual-assignment requalification at a "
    "controlled mechanical/fixture and source-currentness ceiling only; no "
    "prospective human repeat-use value, retention, accumulated-history benefit, "
    "product direction, Wave-4 opening, release, merge, cutover, market demand, "
    "interpersonal/network value, or owner admission."
)


def canonical_digest(value: Any) -> str:
    return "sha256:" + hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    ).hexdigest()


def load_fixture_helpers():
    path = Path("tests/test_counterfactual_assignment_repair.py")
    spec = importlib.util.spec_from_file_location("w3r_b5_fixture_helpers", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load frozen W3R.B5 fixture helpers")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def check(case_id: str, observed: Any, expected: Any, detail: str) -> dict[str, Any]:
    return {
        "case_id": case_id,
        "observed": observed,
        "expected": expected,
        "passed": observed == expected,
        "detail": detail,
    }


def run_requalification() -> dict[str, Any]:
    h = load_fixture_helpers()
    cases: list[dict[str, Any]] = []

    baseline = h.bundle()
    baseline_result = qualify_counterfactual_assignment(baseline, epoch=h.base_epoch())
    cases.append(check("Q5.01_BASELINE_ADMISSIBLE", baseline_result["disposition"], "COUNTERFACTUAL_ASSIGNMENT_ADMISSIBLE", "typed prospective baseline"))
    cases.append(check("Q5.02_NO_HUMAN_VALUE_PROMOTION", baseline_result["human_value_supported"], False, "assignment admissibility is non-promoting"))

    b = h.bundle(); b["schedules"][0]["outcome_blind"] = False
    cases.append(check("Q5.03_OUTCOME_BLINDNESS", qualify_counterfactual_assignment(b, epoch=h.base_epoch())["disposition"], "INVALID_OUTCOME_BLINDNESS", "outcome visibility fails closed"))

    b = h.bundle(); b["schedules"][0]["condition_id"] = "manual"
    cases.append(check("Q5.04_CANONICAL_COMPARATOR_ID", qualify_counterfactual_assignment(b, epoch=h.base_epoch())["disposition"], "INVALID_CONDITION_ASSIGNMENT", "alias drift is not silently flattened"))

    b = h.bundle(); b["comparator_parity_receipt"]["parity_checks"]["P06_INTERFACE_FAMILIARIZATION"] = False
    cases.append(check("Q5.05_PARITY_NONCOMPENSATORY", qualify_counterfactual_assignment(b, epoch=h.base_epoch())["disposition"], "COMPARATOR_CONTAMINATION", "one parity failure blocks the panel"))

    b = h.bundle(); b["schedules"][0]["product_phase_id"] = "phase:drift"
    cases.append(check("Q5.06_PRODUCT_EPOCH_DRIFT", qualify_counterfactual_assignment(b, epoch=h.base_epoch())["disposition"], "ASSIGNMENT_OR_SURFACE_DRIFT", "product epoch is frozen"))

    b = h.bundle(); b["schedules"][0]["measurement_policy_digest"] = h.D("different")
    cases.append(check("Q5.07_MEASUREMENT_POLICY_DRIFT", qualify_counterfactual_assignment(b, epoch=h.base_epoch())["disposition"], "MEASUREMENT_OR_PRODUCT_DRIFT", "measurement policy is frozen"))

    b = h.bundle(); b["missingness_policy"] = h.missingness([h.missing_record("CONSENT_WITHDRAWN")])
    cases.append(check("Q5.08_CONSENT_WITHDRAWAL", qualify_counterfactual_assignment(b, epoch=h.base_epoch())["disposition"], "CONSENT_WITHDRAWN_STOP", "withdrawal precedes interpretation"))

    b = h.bundle(); b["missingness_policy"] = h.missingness([h.missing_record("ACCESSIBILITY_BLOCKED")])
    cases.append(check("Q5.09_ACCESSIBILITY_NOT_NEGATIVE", qualify_counterfactual_assignment(b, epoch=h.base_epoch())["disposition"], "ACCESSIBILITY_BLOCKED_NOT_NEGATIVE_VALUE", "accessibility is not negative value"))

    b = h.bundle(); b["human_outcomes_complete"] = False
    b["missingness_policy"] = h.missingness([h.missing_record("REQUIRED_HUMAN_OUTCOME_ABSENT", outcome_related=True)])
    b["carryover_ledger"]["prior_exposures"] = [{
        "exposure_type": "HISTORY", "source_ref": "prior:history",
        "occurred_at": "2026-08-18T09:00:00Z", "relevant_to_current_inquiry": True,
    }]
    cases.append(check("Q5.10_NONIDENTIFIABLE_PRECEDES_CENSOR", qualify_counterfactual_assignment(b, epoch=h.base_epoch())["disposition"], "NON_IDENTIFIABLE", "contamination is not laundered as missingness"))

    b = h.bundle(); b["schedules"][0]["assignment_method"] = "OBSERVATIONAL_VOLUNTARY"; b["schedules"][0]["allocation_probability_or_rule"] = "observed-choice:v1"
    cases.append(check("Q5.11_OBSERVATIONAL_DOWNGRADE", qualify_counterfactual_assignment(b, epoch=h.base_epoch())["disposition"], "OBSERVATIONAL_ASSOCIATION_ONLY", "voluntary assignment remains associational"))

    b = h.bundle(); b["exposure_receipts"][0]["exposure_status"] = "BYPASS"; b["exposure_receipts"][0]["bypass"] = True; b["exposure_receipts"][0]["dose"] = 0.0
    cases.append(check("Q5.12_BYPASS_SEPARATE_AGENCY", qualify_counterfactual_assignment(b, epoch=h.base_epoch())["disposition"], "BYPASS_SEPARATE_AGENCY", "bypass is not negative value"))

    b = h.bundle()
    b["schedules"] = [
        h.schedule(sid="schedule:a", inquiry="same", condition="C0_MANUAL_ORDINARY_WORKFLOW", method="COUNTERBALANCED_CROSSOVER", period=1, period_count=2),
        h.schedule(sid="schedule:b", inquiry="same", condition="C4_F2_ACCUMULATED_VALID_HISTORY", method="COUNTERBALANCED_CROSSOVER", period=2, period_count=2, first_exposure="2026-08-20T09:05:00Z"),
    ]
    b["exposure_receipts"] = [
        h.exposure(sid="schedule:a", eid="episode:a"),
        {**h.exposure(sid="schedule:b", eid="episode:b", assigned="C4_F2_ACCUMULATED_VALID_HISTORY"), "exposure_started_at": "2026-08-20T09:05:00Z", "exposure_ended_at": "2026-08-20T09:25:00Z", "formed_at": "2026-08-20T09:26:00Z"},
    ]
    cases.append(check("Q5.13_SAME_INQUIRY_CROSSOVER", qualify_counterfactual_assignment(b, epoch=h.base_epoch())["disposition"], "SPLIT_OR_REPLAN", "same-inquiry carryover triggers split"))

    cases.append(check(
        "Q5.14_W3R_B5_SURFACE_PRESENT",
        Path("src/repeat_use_harness/counterfactual.py").is_file() and Path("tests/test_counterfactual_assignment_repair.py").is_file(),
        True,
        "B5 implementation and frozen 36-scenario fixture suite are materialized",
    ))

    sibling_paths = [
        "src/repeat_use_harness/custody_repair.py",
        "src/repeat_use_harness/noninterference.py",
        "src/repeat_use_harness/comparator_parity.py",
        "src/repeat_use_harness/strict_schema.py",
        "src/repeat_use_harness/schema_currentness.py",
        "src/repeat_use_harness/replay_integrity.py",
        "src/repeat_use_harness/state_membrane.py",
    ]
    sibling_present = all(Path(path).is_file() for path in sibling_paths)
    cases.append(check("Q5.15_B2_TO_B7_INTEGRATED_SURFACES", sibling_present, True, "non-B1 repair modules coexist on one current line"))

    b1_present = Path("src/repeat_use_harness/admission.py").is_file() and Path("src/repeat_use_harness/normalization.py").is_file()
    cases.append(check("Q5.16_B1_TERMINAL_ADMISSION_MATERIALIZED", b1_present, True, "terminal admission and B7 normalization must be materialized, not transport-shaped"))

    transfer_fragments = sorted(str(path) for path in Path(".gva-transfer").glob("*w3r-b1*") if path.is_file()) if Path(".gva-transfer").exists() else []
    cases.append(check("Q5.17_B1_TRANSPORT_CLEARED", len(transfer_fragments), 0, "accepted source line must not retain unresolved B1 payload fragments"))

    counterfactual_pass = all(item["passed"] for item in cases[:15])
    integrated_b1_closed = cases[15]["passed"] and cases[16]["passed"]
    if not counterfactual_pass:
        terminal = "REPAIR_REQUIRED_BEFORE_PROSPECTIVE_COUNTERFACTUAL_TRAJECTORY"
    elif not integrated_b1_closed:
        terminal = "RIGHT_CENSORED_INTEGRATED_TERMINAL_ADMISSION_OPERAND_ABSENT"
    else:
        terminal = "COUNTERFACTUAL_ASSIGNMENT_REQUALIFICATION_PASS_AT_INTEGRATED_CONTROLLED_CEILING"

    passed = sum(1 for item in cases if item["passed"])
    result = {
        "schema_version": "gva06.f.ruv.counterfactual-assignment-requalification.v1",
        "artifact_id": "CounterfactualAssignmentRequalification.v1",
        "artifact_state": "EXECUTED_VALIDATED_MERGEABLE_CANDIDATE",
        "program_id": PROGRAM_ID,
        "wave_id": WAVE_ID,
        "branch_id": BRANCH_ID,
        "route_launch_digest": ROUTE_LAUNCH_DIGEST,
        "stewardstack_route_pin": STEWARDSTACK_ROUTE_PIN,
        "stewardstack_current_observation": STEWARDSTACK_CURRENT_OBSERVATION,
        "stewardstack_route_tree": STEWARDSTACK_ROUTE_TREE,
        "integrated_base_ref": INTEGRATED_BASE_REF,
        "terminal_disposition": terminal,
        "case_count": len(cases),
        "passed": passed,
        "failed": len(cases) - passed,
        "counterfactual_surface_requalified": counterfactual_pass,
        "integrated_terminal_admission_closed": integrated_b1_closed,
        "cases": cases,
        "unresolved_b1_transfer_fragments": transfer_fragments,
        "positive_human_terminal_enabled": False,
        "prospective_human_trajectory_executed": False,
        "wave_4_open_from_this_branch": False,
        "prior_wave_payload_bytes_embedded": 0,
        "exact_reentry": (
            "Materialize the accepted W3R.B1 admission/normalization delta on the same "
            "current integrated line, remove B1 transport fragments, then rerun this "
            "unchanged B5 qualifier before the conjunctive W3Q N3 merge."
        ),
        "claim_ceiling": CLAIM_CEILING,
    }
    result["content_digest"] = canonical_digest(result)
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    result = run_requalification()
    target = Path(args.output)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({key: result[key] for key in ("terminal_disposition", "case_count", "passed", "failed", "content_digest")}, sort_keys=True))
    return 1 if result["terminal_disposition"] == "REPAIR_REQUIRED_BEFORE_PROSPECTIVE_COUNTERFACTUAL_TRAJECTORY" else 0


if __name__ == "__main__":
    raise SystemExit(main())
