"""Validation and append-only capture mechanics."""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Any, Iterable, Mapping

from .constants import *

class HarnessValidationError(ValueError):
    """Fail-closed validation error for the bounded harness contract."""


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")


def canonical_digest(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def stable_id(prefix: str, value: Any) -> str:
    return f"{prefix}:{canonical_digest(value)[:24]}"


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace(
        "+00:00", "Z"
    )


def load_json(path: str | Path) -> Any:
    with Path(path).open("r", encoding="utf-8") as handle:
        return json.load(handle)


def write_json(path: str | Path, value: Any) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return target


def read_jsonl(path: str | Path) -> list[dict[str, Any]]:
    target = Path(path)
    if not target.exists():
        return []
    events: list[dict[str, Any]] = []
    for line_no, line in enumerate(target.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        value = json.loads(line)
        if not isinstance(value, dict):
            raise HarnessValidationError(f"JSONL line {line_no} must be an object")
        events.append(value)
    return events


def _require_fields(record: Mapping[str, Any], fields: Iterable[str], kind: str) -> None:
    missing = [field for field in fields if field not in record]
    if missing:
        raise HarnessValidationError(
            f"{kind} missing required fields: {', '.join(missing)}"
        )


def _require_text(record: Mapping[str, Any], fields: Iterable[str], kind: str) -> None:
    _require_fields(record, fields, kind)
    invalid = [
        field
        for field in fields
        if not isinstance(record[field], str) or not record[field].strip()
    ]
    if invalid:
        raise HarnessValidationError(
            f"{kind} requires non-empty text: {', '.join(invalid)}"
        )


def _parse_timestamp(value: str) -> datetime:
    if not isinstance(value, str) or not value:
        raise HarnessValidationError("timestamp must be non-empty text")
    try:
        normalized = value[:-1] + "+00:00" if value.endswith("Z") else value
        parsed = datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise HarnessValidationError(f"invalid ISO timestamp: {value}") from exc
    if parsed.tzinfo is None:
        raise HarnessValidationError("timestamp must include timezone")
    return parsed.astimezone(timezone.utc)


def _find_forbidden_raw_keys(value: Any, path: str = "payload") -> list[str]:
    found: list[str] = []
    if isinstance(value, Mapping):
        for key, child in value.items():
            child_path = f"{path}.{key}"
            if str(key) in FORBIDDEN_RAW_PAYLOAD_KEYS:
                found.append(child_path)
            found.extend(_find_forbidden_raw_keys(child, child_path))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            found.extend(_find_forbidden_raw_keys(child, f"{path}[{index}]"))
    return found


def validate_epoch(epoch: Mapping[str, Any]) -> None:
    _require_text(
        epoch,
        (
            "epoch_id",
            "program_id",
            "product_phase_id",
            "policy_digest",
            "instrumentation_tier",
            "started_at",
            "claim_ceiling",
        ),
        "RepeatUseExperimentEpoch.v1",
    )
    _require_fields(epoch, ("feature_flags", "source_snapshot_refs"), "epoch")
    if epoch["program_id"] != PROGRAM_ID:
        raise HarnessValidationError("epoch program_id mismatch")
    if epoch["instrumentation_tier"] not in {"MINIMAL", "STANDARD", "DIAGNOSTIC"}:
        raise HarnessValidationError("unsupported instrumentation tier")
    _parse_timestamp(str(epoch["started_at"]))
    flags = epoch["feature_flags"]
    if not isinstance(flags, Mapping):
        raise HarnessValidationError("feature_flags must be an object")
    _require_fields(flags, REQUIRED_FEATURE_FLAGS, "feature_flags")
    if flags["capture_tier"] != epoch["instrumentation_tier"]:
        raise HarnessValidationError("capture_tier must equal instrumentation_tier")
    if not isinstance(epoch["source_snapshot_refs"], list) or not epoch["source_snapshot_refs"]:
        raise HarnessValidationError("source_snapshot_refs must be a non-empty list")


def validate_assignment(assignment: Mapping[str, Any]) -> None:
    required = (
        "assignment_id",
        "eligible_inquiry_stratum",
        "condition_id",
        "assignment_method",
        "assignment_seed_or_rule",
        "assigned_before_start",
        "outcome_blind",
        "carryover_firewall",
        "version_phase",
    )
    _require_fields(assignment, required, "EpisodeAssignment.v1")
    _require_text(
        assignment,
        (
            "assignment_id",
            "eligible_inquiry_stratum",
            "condition_id",
            "assignment_method",
            "assignment_seed_or_rule",
            "version_phase",
        ),
        "EpisodeAssignment.v1",
    )
    if assignment["condition_id"] not in COMPARATOR_ARMS:
        raise HarnessValidationError("assignment condition_id is not declared")
    if assignment["assigned_before_start"] is not True:
        raise HarnessValidationError("assignment must be prospective")
    if assignment["outcome_blind"] is not True:
        raise HarnessValidationError("assignment must be outcome blind")
    if not assignment["carryover_firewall"]:
        raise HarnessValidationError("carryover_firewall is required")


def validate_consent(consent: Mapping[str, Any]) -> None:
    _require_text(
        consent,
        ("receipt_id", "participant_id", "issued_at", "claim_ceiling"),
        "ConsentReceipt.v1",
    )
    _require_fields(consent, ("scopes",), "ConsentReceipt.v1")
    _parse_timestamp(str(consent["issued_at"]))
    scopes = consent["scopes"]
    if not isinstance(scopes, Mapping):
        raise HarnessValidationError("consent scopes must be an object")
    _require_fields(scopes, CONSENT_SCOPES, "consent scopes")
    if any(not isinstance(scopes[key], bool) for key in CONSENT_SCOPES):
        raise HarnessValidationError("consent scopes must be booleans")


def validate_event(event: Mapping[str, Any]) -> None:
    _require_fields(
        event,
        ("event_id", "sequence", "payload", *EVENT_REQUIRED_METADATA),
        "RepeatUseEvent.v1",
    )
    _require_text(
        event,
        (
            "event_id",
            "program_id",
            "trajectory_id",
            "episode_id",
            "condition_id",
            "schema_version",
            "event_type",
            "timestamp",
            "claim_ceiling",
        ),
        "RepeatUseEvent.v1",
    )
    if event["program_id"] != PROGRAM_ID:
        raise HarnessValidationError("event program_id mismatch")
    if event["schema_version"] != EVENT_SCHEMA_VERSION:
        raise HarnessValidationError("event schema_version mismatch")
    if event["event_type"] not in EVENT_TYPES:
        raise HarnessValidationError(f"unsupported event_type: {event['event_type']}")
    if not isinstance(event["sequence"], int) or event["sequence"] < 1:
        raise HarnessValidationError("event sequence must be a positive integer")
    _parse_timestamp(str(event["timestamp"]))
    if not isinstance(event["source_refs"], list) or not event["source_refs"]:
        raise HarnessValidationError("event source_refs must be non-empty")
    if not isinstance(event["payload"], Mapping):
        raise HarnessValidationError("event payload must be an object")
    forbidden = _find_forbidden_raw_keys(event["payload"])
    if forbidden:
        raise HarnessValidationError(
            "raw content is forbidden by default: " + ", ".join(forbidden)
        )
    consent_snapshot = event["consent_scope_snapshot"]
    if not isinstance(consent_snapshot, Mapping):
        raise HarnessValidationError("consent_scope_snapshot must be an object")
    _require_fields(consent_snapshot, CONSENT_SCOPES, "event consent snapshot")
    flags = event["feature_flag_snapshot"]
    if not isinstance(flags, Mapping):
        raise HarnessValidationError("feature_flag_snapshot must be an object")
    _require_fields(flags, REQUIRED_FEATURE_FLAGS, "event feature flags")
    if event["event_type"] == "HUMAN_JUDGMENT_RECORDED":
        payload = event["payload"]
        if payload.get("human_supplied") is not True:
            raise HarnessValidationError("human judgment event must be human supplied")
        fields = payload.get("fields")
        if not isinstance(fields, Mapping) or not fields:
            raise HarnessValidationError("human judgment event requires fields")
        unknown = sorted(set(fields) - set(HUMAN_ONLY_FIELDS))
        if unknown:
            raise HarnessValidationError(
                "human judgment event contains unsupported fields: " + ", ".join(unknown)
            )


def append_event_file(
    path: str | Path,
    event: Mapping[str, Any],
    *,
    epoch: Mapping[str, Any],
    consent: Mapping[str, Any],
) -> dict[str, Any]:
    """Validate and append one immutable event to a JSONL log."""
    validate_epoch(epoch)
    validate_consent(consent)
    validate_event(event)
    if consent["scopes"]["local_operational_capture"] is not True:
        raise HarnessValidationError("local operational capture consent is absent")
    if event["condition_id"] not in COMPARATOR_ARMS:
        raise HarnessValidationError("event condition_id is not a declared comparator")
    if dict(event["feature_flag_snapshot"]) != dict(epoch["feature_flags"]):
        raise HarnessValidationError("feature flags drifted within the experiment epoch")
    if event.get("product_phase_id") != epoch["product_phase_id"]:
        raise HarnessValidationError("product phase drifted within the experiment epoch")
    if dict(event["consent_scope_snapshot"]) != dict(consent["scopes"]):
        raise HarnessValidationError("event consent snapshot differs from bound receipt")

    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    existing = read_jsonl(target)
    event_ids = {item["event_id"] for item in existing}
    if event["event_id"] in event_ids:
        raise HarnessValidationError("duplicate event_id")
    if existing:
        previous = existing[-1]
        if event["sequence"] <= previous["sequence"]:
            raise HarnessValidationError("event sequence must be append-only")
        if _parse_timestamp(event["timestamp"]) < _parse_timestamp(previous["timestamp"]):
            raise HarnessValidationError("event timestamp moved backwards")
        if event["episode_id"] != previous["episode_id"]:
            raise HarnessValidationError("one event log file may contain one episode only")
    canonical = json.dumps(event, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    with target.open("a", encoding="utf-8") as handle:
        handle.write(canonical + "\n")
    return {
        "receipt_kind": "AppendOnlyEventReceipt.v1",
        "event_id": event["event_id"],
        "sequence": event["sequence"],
        "event_digest": canonical_digest(event),
        "log_path": target.as_posix(),
        "claim_ceiling": CLAIM_CEILING,
    }


def _elapsed_seconds(start: str | None, end: str | None) -> int | None:
    if start is None or end is None:
        return None
    delta = _parse_timestamp(end) - _parse_timestamp(start)
    return max(0, int(delta.total_seconds()))
