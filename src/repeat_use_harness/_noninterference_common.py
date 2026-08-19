"""Instrumentation noninterference controls for repeat-use value discovery.

This module implements the bounded repair requested by
``F.RUV.W3R.B4 — InstrumentationNoninterferenceRepair``.  It is deliberately
stdlib-only and fail-closed.  It adds a strict qualification envelope around
the existing repeat-use harness without asserting human value.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from statistics import mean
from typing import Any, Iterable, Mapping, Sequence

PROGRAM_ID = "GVA06.F.repeat-use-value-discovery.v2"
WAVE_ID = "F.RUV.W3R"
BRANCH_ID = "F.RUV.W3R.B4"
REPAIR_ARTIFACT_ID = "InstrumentationNoninterferenceRepair.v1"
REPAIR_SCHEMA_VERSION = "gva06.f.ruv.instrumentation-noninterference-repair.v1"
EPOCH_SCHEMA_VERSION = "gva06.f.ruv.experiment-epoch.v1"
SURFACE_SCHEMA_VERSION = "gva06.f.ruv.episode-surface-snapshot.v1"
POLICY_SCHEMA_VERSION = "gva06.f.ruv.frozen-qualification-policy.v1"
CHANGE_SCHEMA_VERSION = "gva06.f.ruv.surface-change-receipt.v1"
POOLING_SCHEMA_VERSION = "gva06.f.ruv.pooling-eligibility-receipt.v1"
FAMILIARIZATION_SCHEMA_VERSION = "gva06.f.ruv.interface-familiarization-receipt.v1"
REACTIVITY_SCHEMA_VERSION = "gva06.f.ruv.instrumentation-reactivity-contrast.v1"
REVIEW_SCHEMA_VERSION = "gva06.f.ruv.independent-review-binding.v1"
MAPPING_SCHEMA_VERSION = "gva06.f.ruv.event-schema-mapping-receipt.v1"

CLAIM_CEILING = (
    "Instrumentation/product noninterference repair and controlled mechanical "
    "qualification only; no human repeat-use value, retention, accumulated-"
    "history benefit, product direction, interpersonal/network value, market "
    "demand, release, merge, cutover, or owner admission claim."
)

EPOCH_KINDS = ("DEVELOPMENT", "DIRECTION_SELECTION", "QUALIFICATION")
EPOCH_STATES = (
    "DRAFT",
    "FROZEN_PRE_OUTCOME",
    "ACTIVE",
    "CLOSED",
    "QUALIFIED_OR_RIGHT_CENSORED",
)
INSTRUMENTATION_DOSES = ("MINIMAL", "STANDARD", "DIAGNOSTIC")

REQUIRED_SURFACE_DIGESTS = (
    "source_snapshot_digest",
    "product_build_digest",
    "product_surface_digest",
    "measurement_surface_digest",
    "comparator_protocol_digest",
    "history_policy_digest",
    "runtime_context_digest",
    "evaluator_rubric_digest",
    "value_policy_digest",
    "analysis_plan_digest",
    "consent_scope_snapshot_digest",
    "accessibility_profile_digest",
)

FLAG_ALLOWED_VALUES: dict[str, tuple[Any, ...]] = {
    "product.history_enabled": (False, True),
    "product.semantic_lens_enabled": (False, True),
    "product.provenance_view_enabled": (False, True),
    "product.exact_reentry_surface_enabled": (False, True),
    "product.user_correction_surface_enabled": (False, True),
    "measurement.capture_tier": INSTRUMENTATION_DOSES,
    "measurement.human_confirmation_prompt_enabled": (False, True),
    "measurement.fine_grained_interaction_logging_enabled": (False, True),
    "measurement.raw_content_capture_enabled": (False, True),
    "comparator.arm_id": (
        "C0_MANUAL_ORDINARY_WORKFLOW",
        "C1_GENERIC_PROJECT_MEMORY",
        "C2_POINTER_ONLY_REENTRY",
        "C3_TASK_F_EMPTY_OR_RESET_HISTORY",
        "C4_TASK_F_VALID_ACCUMULATED_HISTORY",
        "C5_NEGATIVE_HISTORY_CONTROL",
    ),
    "history.condition": (
        "VALID_ACCUMULATED",
        "EMPTY",
        "RESET",
        "SHUFFLED",
        "IRRELEVANT",
        "STALE",
        "CONTAMINATED",
        "NO_F2_STATE",
    ),
    "runtime.fresh_agent_mode": (False, True),
    "runtime.hidden_chat_available": (False, True),
    "analysis.epoch_kind": EPOCH_KINDS,
}

PLANE_BY_FLAG: dict[str, str] = {
    **{name: "P_PRODUCT" for name in FLAG_ALLOWED_VALUES if name.startswith("product.")},
    **{name: "P_MEASUREMENT" for name in FLAG_ALLOWED_VALUES if name.startswith("measurement.")},
    "comparator.arm_id": "P_COMPARATOR",
    "history.condition": "P_HISTORY",
    "runtime.fresh_agent_mode": "P_RUNTIME_CONTEXT",
    "runtime.hidden_chat_available": "P_RUNTIME_CONTEXT",
    "analysis.epoch_kind": "P_EVALUATION_POLICY",
}

PLANE_BY_DIGEST: dict[str, str] = {
    "source_snapshot_digest": "P_RUNTIME_CONTEXT",
    "product_build_digest": "P_PRODUCT",
    "product_surface_digest": "P_PRODUCT",
    "measurement_surface_digest": "P_MEASUREMENT",
    "comparator_protocol_digest": "P_COMPARATOR",
    "history_policy_digest": "P_HISTORY",
    "runtime_context_digest": "P_RUNTIME_CONTEXT",
    "evaluator_rubric_digest": "P_EVALUATION_POLICY",
    "value_policy_digest": "P_EVALUATION_POLICY",
    "analysis_plan_digest": "P_EVALUATION_POLICY",
    "consent_scope_snapshot_digest": "P_RUNTIME_CONTEXT",
    "accessibility_profile_digest": "P_RUNTIME_CONTEXT",
}

BOUND_EVENT_FIELDS = (
    "epoch_id",
    "epoch_digest",
    "surface_snapshot_ref",
    "surface_snapshot_digest",
    "assignment_receipt_ref",
    "policy_bundle_digest",
    "surface_flag_snapshot",
)

CONSENT_SCOPES = (
    "local_operational_capture",
    "human_judgment_capture",
    "artifact_export",
    "share_or_merge_with_another_party",
    "research_reuse_or_training",
    "future_recontact",
)

LOW_BURDEN_CONDITION_MAP = {
    "M.manual": "C0_MANUAL_ORDINARY_WORKFLOW",
    "A.accumulated": "C4_F2_ACCUMULATED_VALID_HISTORY",
    "R.reset": "C3_F2_EMPTY_HISTORY",
    "G.generic-comparator": "C1_GENERIC_PROJECT_MEMORY",
}

LOW_BURDEN_EVENT_MAP = {
    "EPISODE_STARTED": "EPISODE_STARTED",
    "SOURCE_REF_OPENED": "SOURCE_POINTER_OPENED",
    "FIRST_USEFUL_ORIENTATION_CONFIRMED": "FIRST_USEFUL_LENS_MARKED",
    "HUMAN_FIELD_CONFIRMED": "HUMAN_JUDGMENT_RECORDED",
    "EXACT_REENTRY_CONFIRMED": "EXACT_REENTRY_IDENTIFIED",
    "CORRECTION_RECORDED": "HUMAN_JUDGMENT_RECORDED",
    "BURDEN_RECORDED": "BURDEN_RECORDED",
    "BYPASS": "BYPASS",
    "ABANDONMENT": "ABANDONMENT",
    "ACCESSIBILITY_BLOCKED": "ACCESSIBILITY_BLOCKED",
    "INSTRUMENTATION_FLAGGED": "MEASUREMENT_REACTIVITY_RECORDED",
    "EPISODE_CLOSED": "EPISODE_ENDED",
}

REPAIR_IDS = (
    "R1_FULL_EPOCH_AND_SURFACE_BINDING",
    "R2_FULL_FLAG_REGISTRY_AND_RUNTIME_CONTEXT",
    "R3_CHANGE_POOLING_AND_QUALIFICATION_FIREWALL",
    "R4_NOVELTY_AND_REACTIVITY_PROTOCOL",
    "R5_POLICY_AND_REVIEW_CONTENT_BINDING",
    "R6_EVENT_SCHEMA_INTEGRATION",
)


class NoninterferenceValidationError(ValueError):
    """Fail-closed error for the bounded noninterference contract."""


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")


def canonical_digest(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def stable_ref(prefix: str, value: Any) -> str:
    return f"{prefix}:{canonical_digest(value)[:24]}"


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace(
        "+00:00", "Z"
    )


def _require_fields(record: Mapping[str, Any], fields: Iterable[str], kind: str) -> None:
    missing = [field for field in fields if field not in record]
    if missing:
        raise NoninterferenceValidationError(
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
        raise NoninterferenceValidationError(
            f"{kind} requires non-empty text: {', '.join(invalid)}"
        )


def _parse_timestamp(value: str) -> datetime:
    if not isinstance(value, str) or not value:
        raise NoninterferenceValidationError("timestamp must be non-empty text")
    normalized = value[:-1] + "+00:00" if value.endswith("Z") else value
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise NoninterferenceValidationError(f"invalid ISO timestamp: {value}") from exc
    if parsed.tzinfo is None:
        raise NoninterferenceValidationError("timestamp must include timezone")
    return parsed.astimezone(timezone.utc)


def _normalize_digest(value: str) -> str:
    if not isinstance(value, str):
        raise NoninterferenceValidationError("digest must be text")
    raw = value[7:] if value.startswith("sha256:") else value
    if len(raw) != 64 or any(char not in "0123456789abcdef" for char in raw):
        raise NoninterferenceValidationError(f"invalid sha256 digest: {value}")
    return raw


def _digest_label(label: str) -> str:
    return hashlib.sha256(label.encode("utf-8")).hexdigest()


def _copy_without_digest(record: Mapping[str, Any], digest_field: str) -> dict[str, Any]:
    return {key: deepcopy(value) for key, value in record.items() if key != digest_field}


def validate_flag_values(flag_values: Mapping[str, Any]) -> None:
    if not isinstance(flag_values, Mapping):
        raise NoninterferenceValidationError("flag_values must be an object")
    required = set(FLAG_ALLOWED_VALUES)
    missing = sorted(required - set(flag_values))
    unknown = sorted(set(flag_values) - required)
    if missing:
        raise NoninterferenceValidationError(
            "full intervention flag registry is required; missing: " + ", ".join(missing)
        )
    if unknown:
        raise NoninterferenceValidationError(
            "unknown intervention flags: " + ", ".join(unknown)
        )
    for name, allowed in FLAG_ALLOWED_VALUES.items():
        value = flag_values[name]
        if value not in allowed:
            raise NoninterferenceValidationError(
                f"unsupported value for {name}: {value!r}"
            )


def validate_surface_digests(surface_digests: Mapping[str, str]) -> None:
    if not isinstance(surface_digests, Mapping):
        raise NoninterferenceValidationError("surface_digests must be an object")
    missing = sorted(set(REQUIRED_SURFACE_DIGESTS) - set(surface_digests))
    unknown = sorted(set(surface_digests) - set(REQUIRED_SURFACE_DIGESTS))
    if missing:
        raise NoninterferenceValidationError(
            "all required surface digests are mandatory; missing: " + ", ".join(missing)
        )
    if unknown:
        raise NoninterferenceValidationError(
            "unknown surface digests: " + ", ".join(unknown)
        )
    for value in surface_digests.values():
        _normalize_digest(value)



__all__ = [name for name in globals() if not name.startswith("__")]
