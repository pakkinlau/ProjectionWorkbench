#!/usr/bin/env python3
"""Execute the bounded F2.W9.B1 human-observed private-value pilot.

The branch may complete with RIGHT_CENSORED. Mechanical success is not promoted
into human value when a timed manual baseline or post-lens human confirmation is
absent.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
import tempfile
import time
from typing import Any, Mapping

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from project_semantics.source_ingestion import run_personal_value_repair_witness

MECHANICAL_BUNDLE = ROOT / "fixtures" / "personal_value_repair" / "bundle.json"


def _terminal(payload: Mapping[str, Any]) -> str:
    observation = payload["observation"]
    policy = payload["acceptance_policy"]
    if policy.get("require_manual_baseline", True) and not observation.get("manual_baseline_recorded"):
        return "RIGHT_CENSORED"
    if policy.get("require_human_usefulness_confirmation", True) and observation.get("usefulness_confirmed_by_human") is None:
        return "RIGHT_CENSORED"
    burden = observation.get("capture_review_minutes")
    if burden is not None and float(burden) > float(policy.get("maximum_capture_review_minutes", 10)):
        return "CAPTURE_COST_TOO_HIGH"
    if observation.get("representation_useful_confirmed_by_human") is False:
        return "REPRESENTATION_NOT_USEFUL"
    if observation.get("usefulness_confirmed_by_human") is False:
        return "PRIVATE_VALUE_WEAK"
    if policy.get("require_reentry_comparison", True) and observation.get("reentry_better_than_baseline_confirmed_by_human") is not True:
        return "REENTRY_NOT_BETTER_THAN_BASELINE"
    return "PRIVATE_VALUE_SUPPORTED"


def evaluate_pilot(payload: Mapping[str, Any], mechanical: Mapping[str, Any], elapsed_ms: float) -> dict[str, Any]:
    terminal = _terminal(payload)
    current_route = payload["current_route"]
    observation = payload["observation"]
    exact_reentry = {
        "current_wave": current_route["wave"],
        "current_branch": current_route["branch"],
        "next_action": "Complete a real timed baseline and post-lens human confirmation before opening interpersonal value claims.",
        "later_route_if_supported": "web.synthesize -> web.steer -> IndependentInterpersonalRealProjectExchange",
        "later_route_if_weak": "pivot or repair the personal loop; do not open hosted/network work",
    }
    measures = {
        "system_processing_ms": round(elapsed_ms, 3),
        "time_to_first_useful_lens_human_minutes": None,
        "time_to_exact_reentry_human_minutes": None,
        "manual_baseline_minutes": observation.get("manual_baseline_minutes"),
        "capture_review_minutes": observation.get("capture_review_minutes"),
        "manual_confirmation_fields_required": 7,
        "project_history_mechanically_reused": bool(mechanical.get("passed")),
        "human_confirmed_history_reuse": observation.get("prior_history_reuse_confirmed_by_human"),
        "human_confirmed_voluntary_reopen": observation.get("human_voluntarily_reopened_programme"),
        "human_confirmed_next_action_change": observation.get("next_action_changed_confirmed_by_human"),
        "human_confirmed_future_reuse": observation.get("would_reopen_or_reuse_confirmed_by_human"),
    }
    return {
        "schema_version": "gva06.f2.human-observed-private-value-pilot.v1",
        "programme_id": payload["programme_id"],
        "branch_id": payload["branch_id"],
        "terminal_object": "HumanObservedPrivateValuePilot.v1",
        "terminal": terminal,
        "branch_execution_completed": True,
        "mechanical_candidate_check": {
            "passed": bool(mechanical.get("passed")),
            "source_semantic_reentry": mechanical.get("terminal"),
            "candidate_commit": current_route["candidate_commit"],
            "hosted_dependency_required": False,
        },
        "real_project": payload["project"],
        "declared_inquiry": payload["declared_inquiry"],
        "task_relative_lens": {
            "view": "private_reentry_and_product_value",
            "current_state": "Wave 8 complete; PR19 is the current compatibility candidate; the human private-value gate is open.",
            "selected_action": "Execute F2.W9.B1 and measure actual human benefit against a manual baseline.",
            "observed_value": "A real project and human-declared task are bound; the system can return exact reentry and pointer-first lineage.",
            "unresolved": [
                "no contemporaneous timed manual baseline",
                "no post-lens human usefulness confirmation",
                "no human-confirmed next-action change",
                "no human-confirmed voluntary future reuse after seeing the lens",
            ],
            "claim_ceiling": "mechanical reentry support and partial human-observation binding only",
        },
        "measures": measures,
        "observation": observation,
        "exact_reentry": exact_reentry,
        "lawful_outcomes": [
            "PRIVATE_VALUE_SUPPORTED",
            "PRIVATE_VALUE_WEAK",
            "CAPTURE_COST_TOO_HIGH",
            "REENTRY_NOT_BETTER_THAN_BASELINE",
            "REPRESENTATION_NOT_USEFUL",
            "RIGHT_CENSORED",
        ],
        "passed": terminal in {
            "PRIVATE_VALUE_SUPPORTED",
            "PRIVATE_VALUE_WEAK",
            "CAPTURE_COST_TOO_HIGH",
            "REENTRY_NOT_BETTER_THAN_BASELINE",
            "REPRESENTATION_NOT_USEFUL",
            "RIGHT_CENSORED",
        },
        "claim_ceiling": "One bounded human-use pilot execution. RIGHT_CENSORED is not evidence of private value, retention, interpersonal value, hosted necessity, or market demand.",
    }


def run(input_path: str | Path, output_path: str | Path) -> dict[str, Any]:
    payload = json.loads(Path(input_path).read_text(encoding="utf-8"))
    start = time.perf_counter()
    with tempfile.TemporaryDirectory(prefix="f2-w9-b1-") as workspace:
        mechanical_output = Path(workspace) / "mechanical.json"
        mechanical = run_personal_value_repair_witness(
            MECHANICAL_BUNDLE,
            Path(workspace) / "project",
            mechanical_output,
        )
    elapsed_ms = (time.perf_counter() - start) * 1000
    result = evaluate_pilot(payload, mechanical, elapsed_ms)
    destination = Path(output_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=ROOT / "fixtures" / "human_private_value_pilot" / "pilot.json")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = run(args.input, args.output)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
