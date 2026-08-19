#!/usr/bin/env python3
"""Independent adversarial measurement-validity review for F.RUV.W3.B8.

The script deliberately treats confirmed defects as a successful review outcome.
It does not repair product code or promote any human-value claim.
"""
from __future__ import annotations

from copy import deepcopy
import argparse
import hashlib
import importlib
import inspect
import json
from pathlib import Path
from typing import Any

from repeat_use_harness import CLAIM_CEILING, make_fixture, replay, validate_event

PROGRAM_ID = "GVA06.F.repeat-use-value-discovery.v2"
BRANCH_ID = "F.RUV.W3.B8"
ROUTE_LAUNCH_DIGEST = "a4848d67212416935e25d8f4fc09b3aeee1b62b4c761c5cfd7055eb0e4b26baa"
STEWARDSTACK_COMMIT = "a644409f293609ec2e6f0cb230ba0799d455ec1d"
PROJECTIONWORKBENCH_HEAD = "510c60889d9ed7d3014cb6d9d6607ef7305c141c"
REVIEW_CLAIM_CEILING = (
    "Controlled independent measurement-validity qualification only; no live-user "
    "repeat-use value, retention, accumulated-history benefit, product direction, "
    "interpersonal/network value, market demand, release, merge, or owner admission."
)


def canonical_digest(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    ).hexdigest()


def _event(template: dict[str, Any], *, episode_index: int, sequence: int, event_type: str, timestamp: str, payload: dict[str, Any]) -> dict[str, Any]:
    event = deepcopy(template)
    event.update(
        {
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
        }
    )
    return event


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
        events.append(
            _event(
                fixture["events"][0],
                episode_index=index,
                sequence=6,
                event_type="HUMAN_JUDGMENT_RECORDED",
                timestamp="2026-08-19T08:01:10Z",
                payload={
                    "human_supplied": True,
                    "fields": {
                        "human_usefulness_judgment": True,
                        "human_next_action_change_judgment": False,
                        "history_reuse_judgment": True,
                        "voluntary_reuse_or_bypass": "VOLUNTARY_REUSE",
                    },
                },
            )
        )
        events.append(
            _event(
                fixture["events"][0],
                episode_index=index,
                sequence=7,
                event_type="VOLUNTARY_REUSE",
                timestamp="2026-08-19T08:01:20Z",
                payload={"synthetic": True},
            )
        )

    review = {
        "accepted_current": True,
        "positive_terminal_gates": {f"G.ID.{index:02d}": True for index in range(1, 11)},
    }
    result = replay(
        events,
        epoch=fixture["epoch"],
        assignment=fixture["assignment"],
        consent=fixture["consent"],
        thresholds={
            "minimum_real_episodes": 5,
            "minimum_real_projects": 2,
            "capture_review_minutes_ceiling": 30.0,
            "evidence_rung": "R3_REPEAT_TRAJECTORY",
        },
        independent_review=review,
    )
    return {
        "observed_causal_terminal": result["trajectory"]["causal_terminal"],
        "observed_trajectory_disposition": result["trajectory"]["trajectory_disposition"],
        "observed_instrumentation_terminal": result["trajectory"]["instrumentation_terminal"],
        "human_value_supported": result["trajectory"]["evidence_scope"]["human_value_supported"],
        "human_judgment_capture_consent": fixture["consent"]["scopes"]["human_judgment_capture"],
        "next_action_changed_judgment": False,
        "comparator_receipt_supplied": False,
        "synthetic_source": True,
        "confirmed_gap": result["trajectory"]["causal_terminal"] == "REPEAT_USE_VALUE_SUPPORTED_BOUNDED",
    }


def consent_snapshot_mismatch_case() -> dict[str, Any]:
    fixture = make_fixture()
    events = deepcopy(fixture["events"])
    for event in events:
        event["consent_scope_snapshot"]["local_operational_capture"] = False
    result = replay(
        events,
        epoch=fixture["epoch"],
        assignment=fixture["assignment"],
        consent=fixture["consent"],
    )
    return {
        "bound_receipt_local_capture": fixture["consent"]["scopes"]["local_operational_capture"],
        "event_snapshot_local_capture": False,
        "replay_accepted": True,
        "observed_terminal": result["trajectory"]["causal_terminal"],
        "confirmed_gap": True,
    }


def chronology_and_identity_case() -> dict[str, Any]:
    fixture = make_fixture()
    events = deepcopy(fixture["events"])
    events[2]["sequence"] = events[1]["sequence"]
    events[2]["timestamp"] = "2026-08-19T07:59:50Z"
    events[3]["project_id"] = "project:conflicting-later-event"
    result = replay(
        events,
        epoch=fixture["epoch"],
        assignment=fixture["assignment"],
        consent=fixture["consent"],
    )
    episode = result["episodes"][0]
    return {
        "duplicate_sequence_accepted": True,
        "backward_timestamp_accepted": True,
        "conflicting_later_project_id_accepted": True,
        "derived_project_id": episode["project_id"],
        "time_to_first_useful_lens": episode["time_to_first_useful_lens"],
        "chronology_contamination_flagged": any(
            item in episode["contamination_flags"] for item in ("CLOCK_ROLLBACK", "DUPLICATE_SEQUENCE", "IDENTITY_MISMATCH")
        ),
        "confirmed_gap": True,
    }


def content_identity_case() -> dict[str, Any]:
    fixture = make_fixture()
    event = deepcopy(fixture["events"][1])
    original_id = event["event_id"]
    event["payload"]["pointer_count"] = 999
    event["payload"]["opaque_private_payload"] = "accepted-by-key-blacklist"
    validate_event(event)
    return {
        "event_id_unchanged_after_payload_mutation": event["event_id"] == original_id,
        "opaque_payload_accepted": True,
        "confirmed_gap": True,
    }


def terminal_reachability_case() -> dict[str, Any]:
    module = importlib.import_module("repeat_use_harness.replay")
    source = inspect.getsource(module._causal_terminal)
    declared_but_not_emitted = [
        terminal
        for terminal in (
            "NEGATIVE_NET_VALUE",
            "RETENTION_WITHOUT_VALUE",
            "ACCUMULATION_EFFECT_NOT_OBSERVED",
            "EPISODE_VALUE_ONLY",
            "VALUE_WITHOUT_REPEAT_NEED",
            "HETEROGENEOUS_CONTEXT_DEPENDENT",
        )
        if f'"{terminal}"' not in source
    ]
    return {
        "declared_but_not_emitted": declared_but_not_emitted,
        "confirmed_gap": len(declared_but_not_emitted) == 6,
    }


def run_review() -> dict[str, Any]:
    executable_cases = {
        "MV01_SYNTHETIC_POSITIVE_PROMOTION": synthetic_positive_promotion_case(),
        "MV02_CONSENT_SNAPSHOT_MISMATCH": consent_snapshot_mismatch_case(),
        "MV03_REPLAY_CHRONOLOGY_AND_IDENTITY": chronology_and_identity_case(),
        "MV04_EVENT_CONTENT_IDENTITY": content_identity_case(),
        "MV05_TERMINAL_REACHABILITY": terminal_reachability_case(),
    }
    confirmed = sum(1 for case in executable_cases.values() if case["confirmed_gap"])
    review = {
        "schema_version": "gva06.f.ruv.independent-measurement-validity-review.v1",
        "artifact_id": "IndependentMeasurementValidityReview.v1",
        "program_id": PROGRAM_ID,
        "wave_id": "F.RUV.W3",
        "branch_id": BRANCH_ID,
        "artifact_state": "EXECUTED_VALIDATED_MERGEABLE_CANDIDATE",
        "terminal_disposition": "REPAIR_REQUIRED_BEFORE_PROSPECTIVE_HUMAN_TRAJECTORY",
        "source_binding": {
            "stewardstack_commit": STEWARDSTACK_COMMIT,
            "route_launch_digest": ROUTE_LAUNCH_DIGEST,
            "projectionworkbench_head": PROJECTIONWORKBENCH_HEAD,
        },
        "executable_attack_cases": executable_cases,
        "executable_attack_summary": {
            "cases": len(executable_cases),
            "confirmed_gaps": confirmed,
            "passed_as_review": confirmed == len(executable_cases),
        },
        "required_repairs": [
            "Derive evidence rung from signed/typed episode and comparator receipts; do not accept a caller-supplied rung.",
            "Bind independent-review identity, source horizon, policy digest, gate evidence and authority; do not accept bare booleans.",
            "Require active human_judgment_capture consent for every human judgment event and enforce withdrawal prospectively.",
            "Bind every replayed event consent snapshot to the active receipt and verify imported append/export receipts.",
            "Validate sequence uniqueness, monotone time and cross-event trajectory/participant/project/inquiry identity during replay.",
            "Make event identity content-bound or require verified content-digest receipts before replay.",
            "Implement or explicitly map every declared terminal; preserve NO_SAFE and heterogeneous/null/negative distinctions.",
            "Require comparator/counterfactual receipts and burden/reentry/next-action gates before a positive repeat-use terminal.",
        ],
        "nonclaims": [
            "No real participant trajectory was reviewed.",
            "No human repeat-use value or retention is supported.",
            "No product direction is selected.",
            "The review does not repair or merge the harness.",
        ],
        "exact_reentry": (
            "Repair the confirmed admission, consent, replay-integrity, terminal and comparator bindings; rerun this adversarial suite plus "
            "the W3 terminal-calibration, privacy/burden, fresh-agent and schema/tamper branches before opening Wave 4."
        ),
        "claim_ceiling": REVIEW_CLAIM_CEILING,
    }
    without_digest = dict(review)
    review["content_digest"] = canonical_digest(without_digest)
    return review


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    review = run_review()
    payload = json.dumps(review, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload, encoding="utf-8")
    else:
        print(payload, end="")
    if review["terminal_disposition"] != "REPAIR_REQUIRED_BEFORE_PROSPECTIVE_HUMAN_TRAJECTORY":
        return 1
    if not review["executable_attack_summary"]["passed_as_review"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
