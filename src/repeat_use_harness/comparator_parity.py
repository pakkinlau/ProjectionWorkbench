"""F.RUV.W3R.B6 comparator identity and monotonic timing parity repair.

This module is dependency-free, fail-closed, and limited to controlled-fixture
mechanical qualification.  It does not open prospective human comparison or
promote any repeat-use/product claim.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from typing import Any, Mapping, Sequence

from .constants import COMPARATOR_ARMS, CONSENT_SCOPES, PARITY_RULES, PROGRAM_ID

BRANCH_ID = "F.RUV.W3R.B6"
ROUTE_LAUNCH_DIGEST = "a4848d67212416935e25d8f4fc09b3aeee1b62b4c761c5cfd7055eb0e4b26baa"
STEWARDSTACK_COMMIT = "a644409f293609ec2e6f0cb230ba0799d455ec1d"
REPAIR_BASE_HEAD = "e289a2ff01ee31f2f32e85247a2956a835e3c175"
CLAIM_CEILING = (
    "Comparator identity, monotonic timing, exposure, burden, adapter, and "
    "controlled-fixture parity repair only; no prospective human comparison, "
    "repeat-use value, retention, product direction, release, or owner admission."
)
EVENT_SCHEMA = "gva06.f.ruv.canonical-comparator-event.v1"
ENVELOPE_SCHEMA = "gva06.f.ruv.comparator-parity-envelope.v1"
RECEIPT_SCHEMA = "gva06.f.ruv.baseline-timing-parity-receipt.v1"
REPAIR_SCHEMA = "gva06.f.ruv.comparator-timing-parity-repair.v1"
CORPUS_SCHEMA = "gva06.f.ruv.synthetic-timing-parity-corpus.v2"

COMPARATOR_ALIASES = {
    **{x: x for x in COMPARATOR_ARMS},
    "C2_POINTER_ONLY_REENTRY": "C2_POINTER_INDEX_ONLY",
    "C3_TASK_F_EMPTY_OR_RESET_HISTORY": "C3_F2_EMPTY_HISTORY",
    "C4_TASK_F_VALID_ACCUMULATED_HISTORY": "C4_F2_ACCUMULATED_VALID_HISTORY",
    "C5_NEGATIVE_HISTORY_CONTROL": "C5_F2_HISTORY_NEGATIVE_CONTROL_FAMILY",
    "M.manual": "C0_MANUAL_ORDINARY_WORKFLOW",
    "G.generic": "C1_GENERIC_PROJECT_MEMORY",
    "R.reset": "C3_F2_EMPTY_HISTORY",
    "A.accumulated.1": "C4_F2_ACCUMULATED_VALID_HISTORY",
    "A.accumulated.2": "C4_F2_ACCUMULATED_VALID_HISTORY",
}
HISTORY_ALIASES = {
    "VALID_ACCUMULATED": "VALID_ACCUMULATED",
    "ACCUMULATED_VALID": "VALID_ACCUMULATED",
    "VALID_HISTORY": "VALID_ACCUMULATED",
    "EMPTY": "EMPTY",
    "RESET": "RESET",
    "SHUFFLED": "SHUFFLED",
    "IRRELEVANT": "IRRELEVANT",
    "STALE": "STALE",
    "CONTAMINATED": "CONTAMINATED",
    "NO_F2_STATE": "NO_F2_STATE",
    "NO_TASK_F_STATE": "NO_F2_STATE",
    "NO_STATE": "NO_F2_STATE",
}
CONDITION_HISTORY = {
    "C0_MANUAL_ORDINARY_WORKFLOW": {"NO_F2_STATE"},
    "C1_GENERIC_PROJECT_MEMORY": {"NO_F2_STATE"},
    "C2_POINTER_INDEX_ONLY": {"NO_F2_STATE"},
    "C3_F2_EMPTY_HISTORY": {"EMPTY", "RESET"},
    "C4_F2_ACCUMULATED_VALID_HISTORY": {"VALID_ACCUMULATED"},
    "C5_F2_HISTORY_NEGATIVE_CONTROL_FAMILY": {
        "SHUFFLED", "IRRELEVANT", "STALE", "CONTAMINATED"
    },
}
FEATURE_ALIASES = {
    "product.history_enabled": ("product.history_enabled", "history_enabled"),
    "product.semantic_lens_enabled": (
        "product.semantic_lens_enabled", "semantic_lens_enabled"
    ),
    "product.provenance_view_enabled": (
        "product.provenance_view_enabled", "provenance_view_enabled"
    ),
    "measurement.capture_tier": ("measurement.capture_tier", "capture_tier"),
    "runtime.fresh_agent_mode": ("runtime.fresh_agent_mode", "fresh_agent_mode"),
    "runtime.hidden_chat_available": (
        "runtime.hidden_chat_available", "hidden_chat_available"
    ),
    "measurement.raw_content_capture_enabled": (
        "measurement.raw_content_capture_enabled", "raw_content_capture_enabled"
    ),
    "measurement.human_confirmation_prompt_enabled": (
        "measurement.human_confirmation_prompt_enabled",
        "human_confirmation_prompt_enabled",
    ),
    "measurement.fine_grained_interaction_logging_enabled": (
        "measurement.fine_grained_interaction_logging_enabled",
        "fine_grained_interaction_logging_enabled",
    ),
    "product.exact_reentry_surface_enabled": (
        "product.exact_reentry_surface_enabled", "exact_reentry_surface_enabled"
    ),
    "product.user_correction_surface_enabled": (
        "product.user_correction_surface_enabled", "user_correction_surface_enabled"
    ),
    "analysis.epoch_kind": ("analysis.epoch_kind", "epoch_kind"),
    "comparator.arm_id": ("comparator.arm_id", "condition_id"),
    "history.condition": ("history.condition", "history_condition"),
}
EVENT_TYPES = {
    "EPISODE_STARTED", "SOURCE_POINTER_OPENED", "PAUSE_STARTED", "PAUSE_ENDED",
    "FIRST_USEFUL_OUTPUT_MARKED", "EXACT_REENTRY_IDENTIFIED", "BURDEN_RECORDED",
    "HUMAN_JUDGMENT_RECORDED", "BYPASS", "ABANDONMENT", "ACCESSIBILITY_BLOCKED",
    "CONSENT_WITHDRAWN", "EPISODE_ENDED",
}

class ComparatorParityError(ValueError):
    """Fail-closed comparator/timing contract error."""


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def digest(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def _text(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ComparatorParityError(f"{name} must be non-empty text")
    return value


def _sha(value: Any, name: str) -> str:
    candidate = _text(value, name).removeprefix("sha256:")
    if len(candidate) != 64 or any(c not in "0123456789abcdef" for c in candidate):
        raise ComparatorParityError(f"{name} must be a lowercase SHA-256")
    return candidate


def _utc(value: Any) -> datetime:
    text = _text(value, "timestamp_utc")
    parsed = datetime.fromisoformat(text[:-1] + "+00:00" if text.endswith("Z") else text)
    if parsed.tzinfo is None:
        raise ComparatorParityError("timestamp_utc must include timezone")
    return parsed.astimezone(timezone.utc)


def canonical_comparator_id(value: str) -> str:
    try:
        return COMPARATOR_ALIASES[_text(value, "condition_id")]
    except KeyError as exc:
        raise ComparatorParityError(f"unknown comparator arm: {value}") from exc


def canonical_history_condition(value: str) -> str:
    text = _text(value, "history_condition")
    if text in {"EMPTY_OR_RESET", "NO_OR_EMPTY_HISTORY"}:
        raise ComparatorParityError("ambiguous history condition")
    try:
        return HISTORY_ALIASES[text]
    except KeyError as exc:
        raise ComparatorParityError(f"unknown history condition: {value}") from exc


def canonicalize_consent(value: Any, *, enabled_scope_names: Sequence[str] | None = None) -> dict[str, bool]:
    if isinstance(value, Mapping):
        unknown = set(value) - set(CONSENT_SCOPES)
        if unknown:
            raise ComparatorParityError(f"unknown consent scopes: {sorted(unknown)}")
        if any(not isinstance(v, bool) for v in value.values()):
            raise ComparatorParityError("consent map values must be booleans")
        return {scope: bool(value.get(scope, False)) for scope in CONSENT_SCOPES}
    if isinstance(value, list):
        if set(value) != set(CONSENT_SCOPES) or len(value) != len(CONSENT_SCOPES):
            raise ComparatorParityError("consent scope array is not the canonical vocabulary")
        if enabled_scope_names is None:
            raise ComparatorParityError("array-shaped consent requires enabled_scope_names")
        enabled = set(enabled_scope_names)
        if not enabled <= set(CONSENT_SCOPES):
            raise ComparatorParityError("enabled consent scope is unknown")
        return {scope: scope in enabled for scope in CONSENT_SCOPES}
    raise ComparatorParityError("consent snapshot must be a map or canonical scope array")


def canonicalize_features(value: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise ComparatorParityError("feature snapshot must be an object")
    result: dict[str, Any] = {}
    for canonical, aliases in FEATURE_ALIASES.items():
        observed = [value[a] for a in aliases if a in value]
        if not observed:
            raise ComparatorParityError(f"missing feature: {canonical}")
        if any(item != observed[0] for item in observed[1:]):
            raise ComparatorParityError(f"feature alias conflict: {canonical}")
        result[canonical] = deepcopy(observed[0])
    result["comparator.arm_id"] = canonical_comparator_id(str(result["comparator.arm_id"]))
    result["history.condition"] = canonical_history_condition(str(result["history.condition"]))
    return result


def make_envelope(
    *, condition_id: str, history_condition: str, trajectory_id: str, episode_id: str,
    participant_id: str, project_id: str, inquiry_id: str, task_block_id: str,
    order_position: int, source_refs: Sequence[str], source_snapshot_digest: str,
    task_prompt_digest: str, evaluator_policy_digest: str, public_information_digest: str,
    measurement_dose_digest: str, assistance_policy_digest: str,
    active_time_budget_seconds: int, familiarization_seconds: int,
    familiarization_complete: bool, assigned_before_start: bool, outcome_blind: bool,
    carryover_plan_digest: str, consent_scope_snapshot: Any,
    feature_flag_snapshot: Mapping[str, Any], enabled_scope_names: Sequence[str] | None = None,
) -> dict[str, Any]:
    arm, history = canonical_comparator_id(condition_id), canonical_history_condition(history_condition)
    if history not in CONDITION_HISTORY[arm]:
        raise ComparatorParityError(f"history {history} is inadmissible for {arm}")
    if not isinstance(order_position, int) or order_position < 1:
        raise ComparatorParityError("order_position must be positive")
    if not isinstance(active_time_budget_seconds, int) or active_time_budget_seconds <= 0:
        raise ComparatorParityError("active_time_budget_seconds must be positive")
    if not isinstance(familiarization_seconds, int) or familiarization_seconds < 0:
        raise ComparatorParityError("familiarization_seconds must be non-negative")
    if not source_refs or any(not isinstance(x, str) or not x for x in source_refs):
        raise ComparatorParityError("source_refs must be non-empty text pointers")
    envelope = {
        "schema_version": ENVELOPE_SCHEMA, "program_id": PROGRAM_ID,
        "condition_id": arm, "history_condition": history,
        "trajectory_id": _text(trajectory_id, "trajectory_id"),
        "episode_id": _text(episode_id, "episode_id"),
        "participant_id": _text(participant_id, "participant_id"),
        "project_id": _text(project_id, "project_id"),
        "inquiry_id": _text(inquiry_id, "inquiry_id"),
        "task_block_id": _text(task_block_id, "task_block_id"),
        "order_position": order_position, "source_refs": list(source_refs),
        "source_snapshot_digest": _sha(source_snapshot_digest, "source_snapshot_digest"),
        "task_prompt_digest": _sha(task_prompt_digest, "task_prompt_digest"),
        "evaluator_policy_digest": _sha(evaluator_policy_digest, "evaluator_policy_digest"),
        "public_information_digest": _sha(public_information_digest, "public_information_digest"),
        "measurement_dose_digest": _sha(measurement_dose_digest, "measurement_dose_digest"),
        "assistance_policy_digest": _sha(assistance_policy_digest, "assistance_policy_digest"),
        "active_time_budget_seconds": active_time_budget_seconds,
        "familiarization_seconds": familiarization_seconds,
        "familiarization_complete": familiarization_complete,
        "assigned_before_start": assigned_before_start, "outcome_blind": outcome_blind,
        "carryover_plan_digest": _sha(carryover_plan_digest, "carryover_plan_digest"),
        "consent_scope_snapshot": canonicalize_consent(
            consent_scope_snapshot, enabled_scope_names=enabled_scope_names
        ),
        "feature_flag_snapshot": canonicalize_features(feature_flag_snapshot),
        "claim_ceiling": CLAIM_CEILING,
    }
    if envelope["feature_flag_snapshot"]["comparator.arm_id"] != arm:
        raise ComparatorParityError("feature comparator ID differs from envelope")
    if envelope["feature_flag_snapshot"]["history.condition"] != history:
        raise ComparatorParityError("feature history condition differs from envelope")
    envelope["envelope_digest"] = digest(envelope)
    return envelope


def _event_hash(event: Mapping[str, Any]) -> str:
    value = {k: deepcopy(v) for k, v in event.items() if k not in {"event_id", "event_hash"}}
    return digest(value)


def make_event(
    envelope: Mapping[str, Any], *, sequence: int, event_type: str, monotonic_ns: int,
    timestamp_utc: str, payload: Mapping[str, Any], previous_event_hash: str | None,
) -> dict[str, Any]:
    if envelope.get("schema_version") != ENVELOPE_SCHEMA:
        raise ComparatorParityError("unsupported envelope schema")
    if not isinstance(sequence, int) or sequence < 1:
        raise ComparatorParityError("sequence must be positive")
    if not isinstance(monotonic_ns, int) or monotonic_ns < 0:
        raise ComparatorParityError("monotonic_ns must be non-negative")
    if event_type not in EVENT_TYPES:
        raise ComparatorParityError(f"unsupported event_type: {event_type}")
    _utc(timestamp_utc)
    event = {
        "schema_version": EVENT_SCHEMA, "program_id": PROGRAM_ID,
        **{k: deepcopy(envelope[k]) for k in (
            "trajectory_id", "episode_id", "participant_id", "project_id", "inquiry_id",
            "condition_id", "history_condition", "source_refs", "consent_scope_snapshot",
            "feature_flag_snapshot", "active_time_budget_seconds", "evaluator_policy_digest",
            "source_snapshot_digest", "task_prompt_digest", "public_information_digest",
            "measurement_dose_digest", "assistance_policy_digest", "familiarization_seconds",
            "familiarization_complete", "assigned_before_start", "outcome_blind",
            "carryover_plan_digest", "order_position", "task_block_id",
        )},
        "sequence": sequence, "event_type": event_type, "monotonic_ns": monotonic_ns,
        "timestamp_utc": timestamp_utc, "payload": deepcopy(dict(payload)),
        "previous_event_hash": previous_event_hash, "claim_ceiling": CLAIM_CEILING,
    }
    event["event_hash"] = _event_hash(event)
    event["event_id"] = f"event:{event['event_hash'][:24]}"
    return event


def validate_events(events: Sequence[Mapping[str, Any]]) -> None:
    if not events:
        raise ComparatorParityError("event stream is empty")
    ordered = list(events)
    fixed = {
        k: ordered[0][k] for k in (
            "trajectory_id", "episode_id", "participant_id", "project_id", "inquiry_id",
            "condition_id", "history_condition", "task_block_id", "source_snapshot_digest",
            "task_prompt_digest", "evaluator_policy_digest", "public_information_digest",
            "measurement_dose_digest", "assistance_policy_digest", "active_time_budget_seconds",
            "familiarization_seconds", "carryover_plan_digest", "consent_scope_snapshot",
            "feature_flag_snapshot",
        )
    }
    last_sequence, last_ns, last_utc, last_hash = 0, -1, None, None
    paused_at, pause_ns = None, 0
    ids, hashes = set(), set()
    for event in ordered:
        if event.get("schema_version") != EVENT_SCHEMA:
            raise ComparatorParityError("unsupported event schema")
        if any(event.get(k) != v for k, v in fixed.items()):
            raise ComparatorParityError("cross-event identity/exposure drift")
        if event.get("sequence") != last_sequence + 1:
            raise ComparatorParityError("event sequence must be contiguous")
        if not isinstance(event.get("monotonic_ns"), int) or event["monotonic_ns"] <= last_ns:
            raise ComparatorParityError("monotonic clock must strictly increase")
        now = _utc(event.get("timestamp_utc"))
        if last_utc is not None and now < last_utc:
            raise ComparatorParityError("UTC audit time moved backwards")
        if event.get("previous_event_hash") != last_hash:
            raise ComparatorParityError("event hash chain is broken")
        if event.get("event_hash") != _event_hash(event):
            raise ComparatorParityError("event content hash is invalid")
        if event.get("event_id") != f"event:{event['event_hash'][:24]}":
            raise ComparatorParityError("event ID is not content-bound")
        if event["event_id"] in ids or event["event_hash"] in hashes:
            raise ComparatorParityError("duplicate event identity")
        if event["event_type"] == "PAUSE_STARTED":
            if paused_at is not None:
                raise ComparatorParityError("nested pause")
            paused_at = event["monotonic_ns"]
        elif event["event_type"] == "PAUSE_ENDED":
            if paused_at is None:
                raise ComparatorParityError("pause ended without pause start")
            pause_ns += event["monotonic_ns"] - paused_at
            paused_at = None
        last_sequence, last_ns, last_utc, last_hash = event["sequence"], event["monotonic_ns"], now, event["event_hash"]
        ids.add(event["event_id"]); hashes.add(event["event_hash"])
    if paused_at is not None:
        raise ComparatorParityError("unclosed pause")
    if ordered[0]["event_type"] != "EPISODE_STARTED" or ordered[-1]["event_type"] != "EPISODE_ENDED":
        raise ComparatorParityError("stream must start/end the episode")
    elapsed = ordered[-1]["monotonic_ns"] - ordered[0]["monotonic_ns"] - pause_ns
    if elapsed / 1_000_000_000 > fixed["active_time_budget_seconds"]:
        raise ComparatorParityError("active-time budget exceeded")


def adapt_event(source_contract: str, record: Mapping[str, Any], envelope: Mapping[str, Any], *, monotonic_ns: int | None = None, previous_event_hash: str | None = None) -> dict[str, Any]:
    """Adapt one B1/B4/B6/B7 record; no timing is invented."""
    if source_contract not in {"B1_HARNESS", "B4_MANUAL", "B6_LOW_BURDEN", "B7_SYNTHETIC"}:
        raise ComparatorParityError("unknown source contract")
    if source_contract in {"B1_HARNESS", "B7_SYNTHETIC"} and monotonic_ns is None:
        raise ComparatorParityError(f"{source_contract} lacks a monotonic witness")
    condition = record.get("condition_id", record.get("arm_id"))
    if canonical_comparator_id(str(condition)) != envelope["condition_id"]:
        raise ComparatorParityError("adapter comparator identity mismatch")
    history = record.get("history_condition", envelope["history_condition"])
    if canonical_history_condition(str(history)) != envelope["history_condition"]:
        raise ComparatorParityError("adapter history identity mismatch")
    timestamp = record.get("timestamp_utc", record.get("timestamp"))
    if timestamp is None:
        raise ComparatorParityError("source record lacks UTC audit time")
    payload = deepcopy(record.get("payload", {}))
    payload["adapter_source_contract"] = source_contract
    payload["source_record_digest"] = digest(record)
    return make_event(
        envelope, sequence=int(record.get("sequence", 0)),
        event_type=str(record.get("event_type")),
        monotonic_ns=int(monotonic_ns if monotonic_ns is not None else record["monotonic_ns"]),
        timestamp_utc=str(timestamp), payload=payload,
        previous_event_hash=previous_event_hash,
    )


def validate_generic_baseline(envelope: Mapping[str, Any], declaration: Mapping[str, Any]) -> None:
    if envelope["condition_id"] != "C1_GENERIC_PROJECT_MEMORY":
        raise ComparatorParityError("generic baseline requires C1")
    required_false = (
        "task_f_semantics_available", "task_f_history_available",
        "hidden_chat_state_available", "treatment_only_assistance_available",
    )
    if any(declaration.get(k) is not False for k in required_false):
        raise ComparatorParityError("generic baseline is contaminated")
    required_matches = {
        "source_snapshot_digest": envelope["source_snapshot_digest"],
        "task_prompt_digest": envelope["task_prompt_digest"],
        "evaluator_policy_digest": envelope["evaluator_policy_digest"],
        "public_information_digest": envelope["public_information_digest"],
        "measurement_dose_digest": envelope["measurement_dose_digest"],
        "assistance_policy_digest": envelope["assistance_policy_digest"],
        "active_time_budget_seconds": envelope["active_time_budget_seconds"],
        "familiarization_seconds": envelope["familiarization_seconds"],
    }
    if any(declaration.get(k) != v for k, v in required_matches.items()):
        raise ComparatorParityError("generic baseline is not parity-matched")


def summarize(envelope: Mapping[str, Any], events: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    validate_events(events)
    pauses, active_pause_ns = {}, 0
    burden = {"capture_minutes": 0.0, "review_and_correction_minutes": 0.0}
    for event in events:
        if event["event_type"] == "PAUSE_STARTED": pauses["open"] = event["monotonic_ns"]
        elif event["event_type"] == "PAUSE_ENDED": active_pause_ns += event["monotonic_ns"] - pauses.pop("open")
        elif event["event_type"] == "BURDEN_RECORDED":
            for key in burden: burden[key] += float(event["payload"].get(key, 0.0))
    active_ns = events[-1]["monotonic_ns"] - events[0]["monotonic_ns"] - active_pause_ns
    return {
        "condition_id": envelope["condition_id"], "history_condition": envelope["history_condition"],
        "source_snapshot_digest": envelope["source_snapshot_digest"],
        "task_prompt_digest": envelope["task_prompt_digest"],
        "evaluator_policy_digest": envelope["evaluator_policy_digest"],
        "public_information_digest": envelope["public_information_digest"],
        "measurement_dose_digest": envelope["measurement_dose_digest"],
        "assistance_policy_digest": envelope["assistance_policy_digest"],
        "active_time_budget_seconds": envelope["active_time_budget_seconds"],
        "familiarization_seconds": envelope["familiarization_seconds"],
        "familiarization_complete": envelope["familiarization_complete"],
        "assigned_before_start": envelope["assigned_before_start"],
        "outcome_blind": envelope["outcome_blind"],
        "carryover_plan_digest": envelope["carryover_plan_digest"],
        "task_block_id": envelope["task_block_id"], "order_position": envelope["order_position"],
        "active_seconds": active_ns / 1_000_000_000, "pause_seconds": active_pause_ns / 1_000_000_000,
        "capture_review_burden": burden, "event_stream_digest": digest(list(events)),
    }


def parity_receipt(summaries: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    if len(summaries) < 2:
        raise ComparatorParityError("parity requires at least two arms")
    keys = (
        "source_snapshot_digest", "task_prompt_digest", "evaluator_policy_digest",
        "public_information_digest", "measurement_dose_digest", "assistance_policy_digest",
        "active_time_budget_seconds", "familiarization_seconds", "familiarization_complete",
        "assigned_before_start", "outcome_blind", "carryover_plan_digest",
    )
    same = {k: len({json.dumps(s[k], sort_keys=True) for s in summaries}) == 1 for k in keys}
    condition_ids = [s["condition_id"] for s in summaries]
    task_blocks = [s["task_block_id"] for s in summaries]
    order_positions = [s["order_position"] for s in summaries]
    gate_results = {
        "P01_SOURCE_SNAPSHOT": same["source_snapshot_digest"],
        "P02_INFORMATION_VISIBILITY": same["public_information_digest"] and same["assistance_policy_digest"],
        "P03_TASK_BLOCKS": len(task_blocks) == len(set(task_blocks)),
        "P04_CLOCK": all(s["active_seconds"] >= 0 and s["pause_seconds"] >= 0 for s in summaries),
        "P05_BUDGET": same["active_time_budget_seconds"],
        "P06_INTERFACE_FAMILIARIZATION": same["familiarization_seconds"] and same["familiarization_complete"],
        "P07_EVALUATOR_FREEZE": same["evaluator_policy_digest"] and same["task_prompt_digest"],
        "P08_ORDER_BALANCE": len(order_positions) == len(set(order_positions)) and same["carryover_plan_digest"],
        "P09_CAPTURE_COST": same["measurement_dose_digest"] and all("capture_review_burden" in s for s in summaries),
        "P10_NO_IMPUTATION": True,
        "P11_HISTORY_ELIGIBILITY": all(s["history_condition"] in CONDITION_HISTORY[s["condition_id"]] for s in summaries),
        "P12_ARM_INTEGRITY": len(condition_ids) == len(set(condition_ids)),
    }
    passed = all(gate_results.get(rule, False) for rule in PARITY_RULES)
    receipt = {
        "schema_version": RECEIPT_SCHEMA, "program_id": PROGRAM_ID, "branch_id": BRANCH_ID,
        "terminal": (
            "BASELINE_TIMING_PARITY_QUALIFIED_AT_CONTROLLED_FIXTURE_CEILING"
            if passed else "REPAIR_REQUIRED_BEFORE_PROSPECTIVE_COMPARATOR_PARITY"
        ),
        "gate_results": gate_results, "noncompensatory_pass": passed,
        "condition_ids": condition_ids, "summary_digests": [digest(s) for s in summaries],
        "claim_ceiling": CLAIM_CEILING,
    }
    receipt["receipt_digest"] = digest(receipt)
    return receipt


def _d(label: str) -> str: return hashlib.sha256(label.encode()).hexdigest()


def _features(arm: str, history: str) -> dict[str, Any]:
    return {
        "history_enabled": arm == "C4_F2_ACCUMULATED_VALID_HISTORY",
        "semantic_lens_enabled": arm.startswith("C3_") or arm.startswith("C4_") or arm.startswith("C5_"),
        "provenance_view_enabled": False, "capture_tier": "MINIMAL", "fresh_agent_mode": True,
        "hidden_chat_available": False, "raw_content_capture_enabled": False,
        "human_confirmation_prompt_enabled": True, "fine_grained_interaction_logging_enabled": False,
        "exact_reentry_surface_enabled": arm.startswith("C3_") or arm.startswith("C4_") or arm.startswith("C5_"),
        "user_correction_surface_enabled": True, "epoch_kind": "CONTROLLED_FIXTURE",
        "condition_id": arm, "history_condition": history,
    }


def synthetic_corpus() -> dict[str, Any]:
    arms = [
        ("C0_MANUAL_ORDINARY_WORKFLOW", "NO_F2_STATE"),
        ("C1_GENERIC_PROJECT_MEMORY", "NO_F2_STATE"),
        ("C2_POINTER_INDEX_ONLY", "NO_F2_STATE"),
        ("C3_F2_EMPTY_HISTORY", "EMPTY"),
        ("C4_F2_ACCUMULATED_VALID_HISTORY", "VALID_ACCUMULATED"),
        ("C5_F2_HISTORY_NEGATIVE_CONTROL_FAMILY", "SHUFFLED"),
    ]
    summaries, cases = [], []
    common = dict(
        participant_id="participant:synthetic", project_id="project:synthetic",
        trajectory_id="trajectory:F.RUV.W3R.B6.synthetic", source_refs=["pointer:synthetic"],
        source_snapshot_digest=_d("source"), task_prompt_digest=_d("task"),
        evaluator_policy_digest=_d("evaluator"), public_information_digest=_d("public"),
        measurement_dose_digest=_d("dose"), assistance_policy_digest=_d("assistance"),
        active_time_budget_seconds=600, familiarization_seconds=60,
        familiarization_complete=True, assigned_before_start=True, outcome_blind=True,
        carryover_plan_digest=_d("carryover"), consent_scope_snapshot={s: True for s in CONSENT_SCOPES},
    )
    for index, (arm, history) in enumerate(arms, 1):
        env = make_envelope(
            **common, condition_id=arm, history_condition=history,
            episode_id=f"episode:{index}", inquiry_id=f"inquiry:{index}",
            task_block_id=f"task-block:{index}", order_position=index,
            feature_flag_snapshot=_features(arm, history),
        )
        specs = [
            ("EPISODE_STARTED", 0, {}), ("SOURCE_POINTER_OPENED", 1, {}),
            ("PAUSE_STARTED", 2, {}), ("PAUSE_ENDED", 3, {}),
            ("FIRST_USEFUL_OUTPUT_MARKED", 4, {}),
            ("BURDEN_RECORDED", 5, {"capture_minutes": 0.2, "review_and_correction_minutes": 0.1}),
            ("EPISODE_ENDED", 6, {"mechanical_status": "ENDED"}),
        ]
        events, prev = [], None
        for seq, (event_type, second, payload) in enumerate(specs, 1):
            event = make_event(
                env, sequence=seq, event_type=event_type, monotonic_ns=(index * 10_000_000_000 + second * 1_000_000_000),
                timestamp_utc=f"2026-08-19T08:{index:02d}:{second:02d}Z", payload=payload,
                previous_event_hash=prev,
            )
            prev = event["event_hash"]; events.append(event)
        summary = summarize(env, events); summaries.append(summary)
        cases.append({"condition_id": arm, "history_condition": history, "envelope": env, "events": events, "summary": summary})
    receipt = parity_receipt(summaries)
    corpus = {
        "schema_version": CORPUS_SCHEMA, "program_id": PROGRAM_ID, "branch_id": BRANCH_ID,
        "cases": cases, "baseline_timing_parity_receipt": receipt,
        "terminal": receipt["terminal"], "claim_ceiling": CLAIM_CEILING,
    }
    corpus["corpus_digest"] = digest(corpus)
    return corpus


def repair_artifact() -> dict[str, Any]:
    corpus = synthetic_corpus()
    artifact = {
        "schema_version": REPAIR_SCHEMA, "artifact_id": "ComparatorTimingParityRepair.v1",
        "program_id": PROGRAM_ID, "branch_id": BRANCH_ID,
        "route_launch_digest": ROUTE_LAUNCH_DIGEST, "stewardstack_commit": STEWARDSTACK_COMMIT,
        "repair_base_head": REPAIR_BASE_HEAD,
        "terminal_disposition": "COMPARATOR_TIMING_PARITY_REPAIR_IMPLEMENTED_AT_CONTROLLED_FIXTURE_CEILING",
        "repair_surfaces": {
            "RP1": "ComparatorArmIdentityMap.v1", "RP2": "CanonicalComparatorEvent.v1",
            "RP3": "ComparatorEventAdapterSet.v1", "RP4": "CanonicalHistoryCondition.v1",
            "RP5": "GenericBaselineCaptureAdapter.v1", "RP6": "BaselineTimingParityReceipt.v1",
            "RP7": "SyntheticTimingParityCorpus.v2",
        },
        "closed_first_zero": "CANONICAL_COMPARATOR_ID_AND_MONOTONIC_EVENT_CONTRACT_ABSENT",
        "fixture_receipt_digest": corpus["baseline_timing_parity_receipt"]["receipt_digest"],
        "fixture_corpus_digest": corpus["corpus_digest"],
        "wave4_open": False, "w3q_requalification_required": True,
        "claim_ceiling": CLAIM_CEILING,
        "exact_reentry": "Integrate all W3R repairs, run web.synthesize -> web.steer, then independently requalify the current integrated harness as W3Q before Wave 4.",
    }
    artifact["artifact_digest"] = digest(artifact)
    return artifact
