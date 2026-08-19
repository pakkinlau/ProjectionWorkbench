"""Loss-declared migration from the low-burden B6 event vocabulary."""
from __future__ import annotations
from copy import deepcopy
from ._noninterference_common import *

def migrate_low_burden_event(
    source_event: Mapping[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    _require_fields(
        source_event,
        (
            "program_id",
            "trajectory_id",
            "episode_id",
            "condition_id",
            "event_id",
            "event_type",
            "timestamp_utc",
            "monotonic_ns",
            "source_refs",
            "consent_scope_snapshot",
            "feature_flag_snapshot",
            "claim_ceiling",
        ),
        "LowBurdenCaptureEvent.v1",
    )
    if source_event["program_id"] != PROGRAM_ID:
        raise NoninterferenceValidationError("low-burden event program mismatch")
    condition = LOW_BURDEN_CONDITION_MAP.get(str(source_event["condition_id"]))
    if condition is None:
        raise NoninterferenceValidationError("low-burden condition has no safe mapping")
    target_event_type = LOW_BURDEN_EVENT_MAP.get(str(source_event["event_type"]))
    if target_event_type is None:
        raise NoninterferenceValidationError("low-burden event type has no safe mapping")
    _parse_timestamp(str(source_event["timestamp_utc"]))
    payload = deepcopy(dict(source_event.get("payload", {})))
    losses: list[str] = []
    if source_event["event_type"] == "HUMAN_FIELD_CONFIRMED":
        payload = {
            "human_supplied": True,
            "fields": deepcopy(payload.get("fields", payload)),
        }
    elif source_event["event_type"] == "CORRECTION_RECORDED":
        payload = {
            "human_supplied": True,
            "fields": {
                "contribution_proposal_correction_by_human": True,
                "correction_reason": payload.get("reason"),
            },
            "correction": deepcopy(payload),
        }
    elif source_event["event_type"] == "INSTRUMENTATION_FLAGGED":
        payload = {"kind": payload.get("kind", "MEASUREMENT_REACTIVE")}
    elif source_event["event_type"] == "EPISODE_CLOSED":
        payload = {
            "mechanical_status": payload.get("mechanical_status", "ENDED"),
            "human_confirmed": payload.get("human_confirmed") is True,
        }
    consent_value = source_event["consent_scope_snapshot"]
    if isinstance(consent_value, Mapping):
        consent_snapshot = {
            name: bool(consent_value.get(name, False)) for name in CONSENT_SCOPES
        }
    elif isinstance(consent_value, Sequence) and not isinstance(
        consent_value, (str, bytes)
    ):
        granted = set(str(item) for item in consent_value)
        consent_snapshot = {name: name in granted for name in CONSENT_SCOPES}
        losses.append("consent scope order discarded")
    else:
        raise NoninterferenceValidationError("unsupported consent snapshot shape")
    flags = dict(source_event["feature_flag_snapshot"])
    canonical_flags = {
        "history_enabled": bool(flags.get("history_enabled", False)),
        "semantic_lens_enabled": bool(flags.get("semantic_lens_enabled", False)),
        "provenance_view_enabled": bool(flags.get("provenance_view_enabled", False)),
        "capture_tier": flags.get("capture_tier", "MINIMAL"),
        "fresh_agent_mode": bool(flags.get("fresh_agent_mode", True)),
    }
    source_digest = canonical_digest(dict(source_event))
    target: dict[str, Any] = {
        "event_id": stable_ref("event", source_event),
        "sequence": int(source_event["event_id"]),
        "program_id": PROGRAM_ID,
        "trajectory_id": source_event["trajectory_id"],
        "episode_id": source_event["episode_id"],
        "condition_id": condition,
        "schema_version": "gva06.f.ruv.repeat-use-event.v1",
        "event_type": target_event_type,
        "timestamp": source_event["timestamp_utc"],
        "source_refs": list(source_event["source_refs"]),
        "consent_scope_snapshot": consent_snapshot,
        "feature_flag_snapshot": canonical_flags,
        "claim_ceiling": source_event["claim_ceiling"],
        "payload": payload,
        "low_burden_monotonic_ns": source_event["monotonic_ns"],
        "source_low_burden_event_digest": source_digest,
    }
    target_digest = canonical_digest(target)
    receipt: dict[str, Any] = {
        "schema_version": MAPPING_SCHEMA_VERSION,
        "mapping_id": stable_ref("mapping", {"source": source_digest, "target": target_digest}),
        "source_schema": "gva06.f.ruv.low-burden-capture-event.v1",
        "target_schema": "gva06.f.ruv.repeat-use-event.v1",
        "source_event_digest": source_digest,
        "target_event_digest": target_digest,
        "condition_mapping": {
            str(source_event["condition_id"]): condition,
        },
        "event_type_mapping": {
            str(source_event["event_type"]): target_event_type,
        },
        "declared_losses": losses,
        "safe_for_replay": True,
        "claim_ceiling": CLAIM_CEILING,
    }
    receipt["mapping_digest"] = canonical_digest(receipt)
    return target, receipt



__all__ = [name for name in globals() if not name.startswith("__")]
