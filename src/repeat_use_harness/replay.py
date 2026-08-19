"""Deterministic episode and trajectory replay."""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping, Sequence

from .constants import *
from .core import HarnessValidationError, canonical_digest, validate_assignment, validate_consent, validate_epoch, validate_event, _parse_timestamp, _elapsed_seconds

def _episode_from_events(events: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    if not events:
        raise HarnessValidationError("episode event log is empty")
    ordered = sorted(events, key=lambda item: item["sequence"])
    first = ordered[0]
    human_fields = {name: None for name in HUMAN_ONLY_FIELDS}
    burden = {name: 0.0 for name in BURDEN_DIMENSIONS}
    corrections: list[dict[str, Any]] = []
    contamination_flags: list[str] = []
    agency_events: list[str] = []
    start_timestamp: str | None = None
    end_timestamp: str | None = None
    lens_timestamp: str | None = None
    reentry_timestamp: str | None = None
    action_outcome: dict[str, Any] = {
        "mechanical_status": "UNOBSERVED",
        "human_confirmed": False,
    }

    for event in ordered:
        validate_event(event)
        event_type = event["event_type"]
        payload = event["payload"]
        if event_type == "EPISODE_STARTED":
            start_timestamp = event["timestamp"]
        elif event_type == "EPISODE_ENDED":
            end_timestamp = event["timestamp"]
            action_outcome = {
                "mechanical_status": payload.get("mechanical_status", "ENDED"),
                "human_confirmed": payload.get("human_confirmed") is True,
            }
        elif event_type == "FIRST_USEFUL_LENS_MARKED":
            lens_timestamp = event["timestamp"]
        elif event_type == "EXACT_REENTRY_IDENTIFIED":
            reentry_timestamp = event["timestamp"]
        elif event_type == "BURDEN_RECORDED":
            for name in BURDEN_DIMENSIONS:
                if name in payload:
                    value = payload[name]
                    if not isinstance(value, (int, float)) or value < 0:
                        raise HarnessValidationError(
                            f"burden dimension {name} must be non-negative"
                        )
                    burden[name] += float(value)
        elif event_type == "HUMAN_JUDGMENT_RECORDED":
            for name, value in payload["fields"].items():
                human_fields[name] = deepcopy(value)
            if payload.get("correction"):
                corrections.append(deepcopy(payload["correction"]))
        elif event_type == "CONTAMINATION_RECORDED":
            contamination_flags.append(str(payload.get("kind", "UNSPECIFIED")))
        elif event_type == "HIDDEN_STATE_DEPENDENCE_RECORDED":
            contamination_flags.append("HIDDEN_STATE_DEPENDENCE")
        elif event_type == "MEASUREMENT_REACTIVITY_RECORDED":
            contamination_flags.append("MEASUREMENT_REACTIVE")
        if event_type in AGENCY_EVENT_TYPES:
            agency_events.append(event_type)

    if start_timestamp is None:
        contamination_flags.append("MISSING_EPISODE_START")
    if end_timestamp is None:
        contamination_flags.append("MISSING_EPISODE_END")
    missing = sorted(name for name, value in human_fields.items() if value is None)
    episode = {
        "schema_version": EPISODE_SCHEMA_VERSION,
        "episode_id": first["episode_id"],
        "participant_id": first.get("participant_id", "participant:unbound"),
        "project_id": first.get("project_id", "project:unbound"),
        "inquiry_id": first.get("inquiry_id", "inquiry:unbound"),
        "condition_id": first["condition_id"],
        "product_phase_id": first.get("product_phase_id"),
        "preregistration_ref": first.get("preregistration_ref"),
        "start_timestamp": start_timestamp,
        "end_timestamp": end_timestamp,
        "time_to_first_useful_lens": _elapsed_seconds(start_timestamp, lens_timestamp),
        "time_to_exact_reentry": _elapsed_seconds(start_timestamp, reentry_timestamp),
        "capture_review_burden": burden,
        "human_usefulness_judgment": human_fields["human_usefulness_judgment"],
        "human_next_action_change_judgment": human_fields[
            "human_next_action_change_judgment"
        ],
        "history_reuse_judgment": human_fields["history_reuse_judgment"],
        "voluntary_reuse_or_bypass": human_fields["voluntary_reuse_or_bypass"],
        "corrections": corrections,
        "action_outcome": action_outcome,
        "human_only_fields": human_fields,
        "agency_events": agency_events,
        "missingness": missing,
        "contamination_flags": sorted(set(contamination_flags)),
        "claim_ceiling": CLAIM_CEILING,
        "evidence_rung": "R0_MECHANICAL",
        "source_event_digest": canonical_digest(ordered),
    }
    episode["episode_digest"] = canonical_digest(episode)
    return episode


def _all_positive_gates(review: Mapping[str, Any] | None) -> bool:
    if not review or review.get("accepted_current") is not True:
        return False
    gates = review.get("positive_terminal_gates")
    expected = [f"G.ID.{index:02d}" for index in range(1, 11)]
    return isinstance(gates, Mapping) and all(gates.get(gate) is True for gate in expected)


def _causal_terminal(
    episodes: Sequence[Mapping[str, Any]],
    *,
    consent: Mapping[str, Any],
    thresholds: Mapping[str, Any],
    review: Mapping[str, Any] | None,
) -> tuple[str, list[str]]:
    reasons: list[str] = []
    event_types = {event for episode in episodes for event in episode["agency_events"]}
    contaminations = {
        item for episode in episodes for item in episode["contamination_flags"]
    }
    scopes = consent["scopes"]
    if "CONSENT_WITHDRAWN" in event_types or not scopes["local_operational_capture"]:
        return "HARM_OR_TRUST_BREACH", ["consent/control guardrail failed"]

    required_human = (
        "human_usefulness_judgment",
        "human_next_action_change_judgment",
        "history_reuse_judgment",
        "voluntary_reuse_or_bypass",
    )
    human_missing = any(episode.get(field) is None for episode in episodes for field in required_human)
    minimum_episodes = int(thresholds.get("minimum_real_episodes", 5))
    minimum_projects = int(thresholds.get("minimum_real_projects", 2))
    projects = {episode["project_id"] for episode in episodes}
    evidence_rung = str(thresholds.get("evidence_rung", "R0_MECHANICAL"))

    if human_missing or len(episodes) < minimum_episodes or len(projects) < minimum_projects:
        reasons.extend(
            [
                "required prospective human observations are missing",
                f"episodes={len(episodes)} minimum={minimum_episodes}",
                f"projects={len(projects)} minimum={minimum_projects}",
            ]
        )
        return "RIGHT_CENSORED", reasons
    if contaminations.intersection(
        {"CARRYOVER", "HISTORY_LEAKAGE", "VERSION_DRIFT", "TASK_MISMATCH"}
    ):
        return "NON_IDENTIFIABLE", sorted(contaminations)
    if "MEASUREMENT_REACTIVE" in contaminations:
        return "MEASUREMENT_REACTIVE", ["instrumentation changed behavior or burden"]
    burden_ceiling = float(thresholds.get("capture_review_minutes_ceiling", 30.0))
    burden = sum(
        float(episode["capture_review_burden"].get("capture_minutes", 0.0))
        + float(
            episode["capture_review_burden"].get(
                "review_and_correction_minutes", 0.0
            )
        )
        for episode in episodes
    )
    if burden > burden_ceiling:
        return "CAPTURE_COST_TOO_HIGH", [
            f"capture/review burden {burden} exceeds ceiling {burden_ceiling}"
        ]
    if evidence_rung not in EVIDENCE_RUNG_ORDER:
        return "NO_SAFE_PRODUCT_STEERING", ["unknown evidence rung"]

    voluntary = any(
        episode.get("voluntary_reuse_or_bypass") == "VOLUNTARY_REUSE"
        or "VOLUNTARY_REUSE" in episode["agency_events"]
        for episode in episodes
    )
    explicit_useful = all(
        episode.get("human_usefulness_judgment") in {True, "USEFUL", "POSITIVE"}
        for episode in episodes
    )
    explicit_history = all(
        episode.get("history_reuse_judgment")
        in {True, "MATERIALLY_HELPED", "POSITIVE"}
        for episode in episodes
    )
    if (
        EVIDENCE_RUNG_ORDER[evidence_rung] >= EVIDENCE_RUNG_ORDER["R3_REPEAT_TRAJECTORY"]
        and voluntary
        and explicit_useful
        and explicit_history
        and _all_positive_gates(review)
    ):
        return "REPEAT_USE_VALUE_SUPPORTED_BOUNDED", [
            "all positive gates passed at R3-or-higher evidence rung"
        ]
    return "NO_SAFE_PRODUCT_STEERING", [
        "complete observations do not satisfy all noncompensatory positive gates"
    ]


def replay(
    events: Sequence[Mapping[str, Any]],
    *,
    epoch: Mapping[str, Any],
    assignment: Mapping[str, Any],
    consent: Mapping[str, Any],
    thresholds: Mapping[str, Any] | None = None,
    independent_review: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Replay one or more episode logs into bounded trajectory dispositions."""
    validate_epoch(epoch)
    validate_assignment(assignment)
    validate_consent(consent)
    if not events:
        raise HarnessValidationError("replay requires at least one event")
    grouped: dict[str, list[Mapping[str, Any]]] = {}
    seen_ids: set[str] = set()
    for event in events:
        validate_event(event)
        if event["event_id"] in seen_ids:
            raise HarnessValidationError("duplicate event_id in replay")
        seen_ids.add(event["event_id"])
        if dict(event["feature_flag_snapshot"]) != dict(epoch["feature_flags"]):
            raise HarnessValidationError("feature flag snapshot drift")
        if event.get("product_phase_id") != epoch["product_phase_id"]:
            raise HarnessValidationError("product phase drift")
        if event["condition_id"] != assignment["condition_id"]:
            raise HarnessValidationError("event/assignment condition mismatch")
        grouped.setdefault(event["episode_id"], []).append(event)
    episodes = [_episode_from_events(grouped[key]) for key in sorted(grouped)]
    threshold_policy = {
        "minimum_real_episodes": 5,
        "minimum_real_projects": 2,
        "capture_review_minutes_ceiling": 30.0,
        "evidence_rung": "R0_MECHANICAL",
    }
    if thresholds:
        threshold_policy.update(dict(thresholds))

    causal_terminal, reasons = _causal_terminal(
        episodes,
        consent=consent,
        thresholds=threshold_policy,
        review=independent_review,
    )
    contaminations = {
        item for episode in episodes for item in episode["contamination_flags"]
    }
    event_types = {event for episode in episodes for event in episode["agency_events"]}

    if not consent["scopes"]["local_operational_capture"]:
        instrumentation_terminal = "CONSENT_SCOPE_ABSENT"
    elif "ACCESSIBILITY_BLOCKED" in event_types:
        instrumentation_terminal = "ACCESSIBILITY_BLOCKED"
    elif "HIDDEN_STATE_DEPENDENCE" in contaminations:
        instrumentation_terminal = "HIDDEN_STATE_DEPENDENCE"
    elif "MEASUREMENT_REACTIVE" in contaminations:
        instrumentation_terminal = "MEASUREMENT_REACTIVE"
    elif contaminations.intersection(
        {"CARRYOVER", "HISTORY_LEAKAGE", "VERSION_DRIFT", "TASK_MISMATCH"}
    ):
        instrumentation_terminal = "NON_IDENTIFIABLE"
    elif causal_terminal == "RIGHT_CENSORED":
        instrumentation_terminal = "RIGHT_CENSORED"
    else:
        instrumentation_terminal = "INSTRUMENTATION_READY"

    if any(
        item in contaminations
        for item in ("MISSING_EPISODE_START", "MISSING_EPISODE_END", "PROTOCOL_VIOLATION")
    ):
        trajectory_disposition = "PROTOCOL_VIOLATION"
    elif causal_terminal == "NON_IDENTIFIABLE":
        trajectory_disposition = "NON_IDENTIFIABLE"
    elif causal_terminal == "CAPTURE_COST_TOO_HIGH":
        trajectory_disposition = "CAPTURE_COST_TOO_HIGH"
    elif causal_terminal == "RIGHT_CENSORED":
        trajectory_disposition = "RIGHT_CENSORED"
    elif causal_terminal == "NEGATIVE_NET_VALUE":
        trajectory_disposition = "NEGATIVE_NET_VALUE"
    elif causal_terminal == "REPEAT_USE_VALUE_SUPPORTED_BOUNDED":
        trajectory_disposition = "REPEAT_USE_SUPPORTED"
    elif not any("VOLUNTARY_REUSE" in episode["agency_events"] for episode in episodes):
        trajectory_disposition = "NO_VOLUNTARY_REUSE"
    else:
        trajectory_disposition = "ACCUMULATION_NOT_SUPPORTED"

    trajectory = {
        "schema_version": TRAJECTORY_SCHEMA_VERSION,
        "trajectory_id": events[0]["trajectory_id"],
        "participant_id": episodes[0]["participant_id"],
        "episode_ids": [episode["episode_id"] for episode in episodes],
        "project_ids": sorted({episode["project_id"] for episode in episodes}),
        "assignment_schedule_ref": assignment["assignment_id"],
        "product_phase_ids": sorted(
            {episode["product_phase_id"] for episode in episodes if episode["product_phase_id"]}
        ),
        "carryover_assessment": {
            "firewall": assignment["carryover_firewall"],
            "contamination_flags": sorted(contaminations),
            "identifiable": trajectory_disposition not in {"NON_IDENTIFIABLE", "PROTOCOL_VIOLATION"},
        },
        "trajectory_disposition": trajectory_disposition,
        "instrumentation_terminal": instrumentation_terminal,
        "causal_terminal": causal_terminal,
        "terminal_reasons": reasons,
        "evidence_scope": {
            "rung": threshold_policy["evidence_rung"],
            "human_value_supported": causal_terminal
            == "REPEAT_USE_VALUE_SUPPORTED_BOUNDED",
            "mechanical_replay_supported": True,
            "claim_ceiling": CLAIM_CEILING,
        },
        "exact_reentry": (
            "Collect prospectively consented human judgments, matched comparator "
            "episodes, delayed reentry, and independent outcome review; then rerun "
            "the same frozen epoch and policy digest."
        ),
    }
    trajectory["trajectory_digest"] = canonical_digest(trajectory)
    result = {
        "schema_version": HARNESS_SCHEMA_VERSION,
        "program_id": PROGRAM_ID,
        "branch_id": BRANCH_ID,
        "epoch_ref": epoch["epoch_id"],
        "assignment_ref": assignment["assignment_id"],
        "consent_ref": consent["receipt_id"],
        "event_count": len(events),
        "episodes": episodes,
        "trajectory": trajectory,
        "terminal_priority": list(CAUSAL_TERMINAL_PRIORITY),
        "positive_terminal_guard": {
            "default_enabled": False,
            "required_evidence_rung": "R3_REPEAT_TRAJECTORY",
            "required_gate_ids": [f"G.ID.{index:02d}" for index in range(1, 11)],
            "independent_review_required": True,
        },
        "claim_ceiling": CLAIM_CEILING,
    }
    result["replay_digest"] = canonical_digest(result)
    return result
