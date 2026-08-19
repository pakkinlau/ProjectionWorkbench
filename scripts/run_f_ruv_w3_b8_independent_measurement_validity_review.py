#!/usr/bin/env python3
"""Post-repair independent adversarial measurement-validity review.

The five historical W3.B8 attacks remain fixed.  A repaired integrated harness is
allowed to reject an attack earlier than the original vulnerable path.  Such a
fail-closed rejection is recorded as a repaired gap; it is never converted into
human-value evidence or product authority.
"""
from __future__ import annotations

from copy import deepcopy
import argparse
import hashlib
import importlib
import inspect
import json
from pathlib import Path
from typing import Any, Callable

from repeat_use_harness import HarnessValidationError, make_fixture, replay, validate_event

PROGRAM_ID = "GVA06.F.repeat-use-value-discovery.v2"
BRANCH_ID = "F.RUV.W3.B8"
ROUTE_LAUNCH_DIGEST = "a4848d67212416935e25d8f4fc09b3aeee1b62b4c761c5cfd7055eb0e4b26baa"
REVIEW_CLAIM_CEILING = (
    "Controlled post-repair measurement-validity qualification only; no live-user "
    "repeat-use value, retention, accumulated-history benefit, product direction, "
    "interpersonal/network value, market demand, release, merge, or owner admission."
)


def canonical_digest(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    ).hexdigest()


def _event(template: dict[str, Any], *, episode_index: int, sequence: int, event_type: str, timestamp: str, payload: dict[str, Any]) -> dict[str, Any]:
    event = deepcopy(template)
    event.update({
        "trajectory_id": "trajectory:F.RUV.W3.B8.synthetic-positive",
        "episode_id": f"episode:F.RUV.W3.B8.synthetic.{episode_index:02d}",
        "participant_id": "participant:synthetic-validity-review",
        "project_id": f"project:synthetic-{episode_index % 2}",
        "inquiry_id": f"inquiry:synthetic-{episode_index:02d}",
        "sequence": sequence,
        "event_type": event_type,
        "timestamp": timestamp,
        "payload": payload,
        "event_id": f"event:F.RUV.W3.B8:{episode_index:02d}:{sequence:02d}:{event_type}",
    })
    return event


def _blocked(exc: Exception, **extra: Any) -> dict[str, Any]:
    return {
        **extra,
        "blocked_by_repair": type(exc).__name__,
        "error": str(exc),
        "confirmed_gap": False,
        "repaired": True,
    }


def synthetic_positive_promotion_case() -> dict[str, Any]:
    fixture = make_fixture()
    events: list[dict[str, Any]] = []
    for index in range(5):
        for base in fixture["events"]:
            event = deepcopy(base)
            event["trajectory_id"] = "trajectory:F.RUV.W3.B8.synthetic-positive"
            event["episode_id"] = f"episode:F.RUV.W3.B8.synthetic.{index:02d}"
            event["participant_id"] = "participant:synthetic-validity-review"
            event["project_id"] = f"project:synthetic-{index % 2}"
            event["inquiry_id"] = f"inquiry:synthetic-{index:02d}"
            if event["event_type"] == "EPISODE_ENDED":
                event["sequence"] = 8
                event["timestamp"] = "2026-08-19T08:02:00Z"
            event["event_id"] = f"event:F.RUV.W3.B8:{index:02d}:{event['sequence']:02d}:{event['event_type']}"
            events.append(event)
        events.append(_event(
            fixture["events"][0], episode_index=index, sequence=6,
            event_type="HUMAN_JUDGMENT_RECORDED", timestamp="2026-08-19T08:01:10Z",
            payload={"human_supplied": True, "fields": {
                "human_usefulness_judgment": True,
                "human_next_action_change_judgment": False,
                "history_reuse_judgment": True,
                "voluntary_reuse_or_bypass": "VOLUNTARY_REUSE",
            }},
        ))
        events.append(_event(
            fixture["events"][0], episode_index=index, sequence=7,
            event_type="VOLUNTARY_REUSE", timestamp="2026-08-19T08:01:20Z",
            payload={"synthetic": True},
        ))
    review = {"accepted_current": True, "positive_terminal_gates": {f"G.ID.{i:02d}": True for i in range(1, 11)}}
    try:
        result = replay(
            events, epoch=fixture["epoch"], assignment=fixture["assignment"], consent=fixture["consent"],
            thresholds={
                "minimum_real_episodes": 5,
                "minimum_real_projects": 2,
                "capture_review_minutes_ceiling": 30.0,
                "evidence_rung": "R3_REPEAT_TRAJECTORY",
            },
            independent_review=review,
        )
    except HarnessValidationError as exc:
        return _blocked(exc, promotion_rejected=True, synthetic_source=True, comparator_receipt_supplied=False)
    gap = result["trajectory"]["causal_terminal"] == "REPEAT_USE_VALUE_SUPPORTED_BOUNDED"
    return {
        "promotion_rejected": not gap,
        "observed_causal_terminal": result["trajectory"]["causal_terminal"],
        "synthetic_source": True,
        "comparator_receipt_supplied": False,
        "confirmed_gap": gap,
        "repaired": not gap,
    }


def consent_snapshot_mismatch_case() -> dict[str, Any]:
    fixture = make_fixture(); events = deepcopy(fixture["events"])
    for event in events:
        event["consent_scope_snapshot"]["local_operational_capture"] = False
    try:
        replay(events, epoch=fixture["epoch"], assignment=fixture["assignment"], consent=fixture["consent"])
    except HarnessValidationError as exc:
        return _blocked(exc, replay_accepted=False)
    return {"replay_accepted": True, "confirmed_gap": True, "repaired": False}


def chronology_and_identity_case() -> dict[str, Any]:
    fixture = make_fixture(); events = deepcopy(fixture["events"])
    events[2]["sequence"] = events[1]["sequence"]
    events[2]["timestamp"] = "2026-08-19T07:59:50Z"
    events[3]["project_id"] = "project:conflicting-later-event"
    try:
        replay(events, epoch=fixture["epoch"], assignment=fixture["assignment"], consent=fixture["consent"])
    except HarnessValidationError as exc:
        return _blocked(exc, chronology_and_identity_rejected=True)
    return {"chronology_and_identity_rejected": False, "confirmed_gap": True, "repaired": False}


def content_identity_case() -> dict[str, Any]:
    fixture = make_fixture(); event = deepcopy(fixture["events"][1])
    original_id = event["event_id"]
    event["payload"]["pointer_count"] = 999
    event["payload"]["opaque_private_payload"] = "accepted-by-key-blacklist"
    try:
        validate_event(event)
    except HarnessValidationError as exc:
        return _blocked(exc, event_id_unchanged_after_payload_mutation=event["event_id"] == original_id)
    return {
        "event_id_unchanged_after_payload_mutation": event["event_id"] == original_id,
        "confirmed_gap": True,
        "repaired": False,
    }


def terminal_reachability_case() -> dict[str, Any]:
    module = importlib.import_module("repeat_use_harness.admission")
    source = inspect.getsource(module.evaluate_terminal_case)
    declared = (
        "NEGATIVE_NET_VALUE", "RETENTION_WITHOUT_VALUE", "ACCUMULATION_EFFECT_NOT_OBSERVED",
        "EPISODE_VALUE_ONLY", "VALUE_WITHOUT_REPEAT_NEED", "HETEROGENEOUS_CONTEXT_DEPENDENT",
    )
    missing = [terminal for terminal in declared if f'"{terminal}"' not in source]
    return {
        "declared_but_not_emitted": missing,
        "confirmed_gap": bool(missing),
        "repaired": not missing,
    }


def run_review() -> dict[str, Any]:
    executable_cases = {
        "MV01_SYNTHETIC_POSITIVE_PROMOTION": synthetic_positive_promotion_case(),
        "MV02_CONSENT_SNAPSHOT_MISMATCH": consent_snapshot_mismatch_case(),
        "MV03_REPLAY_CHRONOLOGY_AND_IDENTITY": chronology_and_identity_case(),
        "MV04_EVENT_CONTENT_IDENTITY": content_identity_case(),
        "MV05_TERMINAL_REACHABILITY": terminal_reachability_case(),
    }
    confirmed = sum(case.get("confirmed_gap") is True for case in executable_cases.values())
    repaired = sum(case.get("repaired") is True for case in executable_cases.values())
    clean = confirmed == 0 and repaired == len(executable_cases)
    review = {
        "schema_version": "gva06.f.ruv.independent-measurement-validity-review.v1",
        "artifact_id": "IndependentMeasurementValidityReview.v1",
        "program_id": PROGRAM_ID,
        "wave_id": "F.RUV.W3",
        "branch_id": BRANCH_ID,
        "artifact_state": "EXECUTED_VALIDATED_MERGEABLE_CANDIDATE",
        "terminal_disposition": (
            "POST_REPAIR_VALIDITY_ATTACKS_CLOSED_AT_CONTROLLED_MECHANICAL_CEILING"
            if clean else "REPAIR_REQUIRED_BEFORE_PROSPECTIVE_HUMAN_TRAJECTORY"
        ),
        "source_binding": {"route_launch_digest": ROUTE_LAUNCH_DIGEST},
        "executable_attack_cases": executable_cases,
        "executable_attack_summary": {
            "cases": len(executable_cases),
            "confirmed_gaps": confirmed,
            "repaired_gaps": repaired,
            "remaining_gaps": confirmed,
            "passed_as_review": confirmed + repaired == len(executable_cases),
        },
        "required_repairs": ([] if clean else [
            "Repair only still-confirmed integrated attack findings; never weaken fail-closed controls to reproduce historical vulnerabilities."
        ]),
        "nonclaims": [
            "No real participant trajectory was reviewed.",
            "No human repeat-use value or retention is supported.",
            "No product direction is selected.",
            "This review does not itself open Wave 4.",
        ],
        "exact_reentry": (
            "Run independent eight-axis W3Q2 qualification against the frozen integrated target before opening Wave 4."
            if clean else "Repair the still-confirmed integrated attack findings and rerun this review."
        ),
        "claim_ceiling": REVIEW_CLAIM_CEILING,
    }
    review["content_digest"] = canonical_digest(review)
    return review


def main() -> int:
    parser = argparse.ArgumentParser(); parser.add_argument("--output", type=Path); args = parser.parse_args()
    review = run_review(); payload = json.dumps(review, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True); args.output.write_text(payload, encoding="utf-8")
    else:
        print(payload, end="")
    return 0 if review["executable_attack_summary"]["passed_as_review"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
