"""Frozen policy, epoch, surface, and event-binding controls."""
from __future__ import annotations
from ._noninterference_common import *

def build_frozen_policy_bundle(
    *,
    policy_id: str,
    threshold_policy: Mapping[str, Any],
    evidence_rung: str,
    evaluator_rubric_digest: str,
    value_policy_digest: str,
    analysis_plan_digest: str,
    frozen_at: str,
    frozen_before_outcomes: bool = True,
) -> dict[str, Any]:
    if not policy_id.strip():
        raise NoninterferenceValidationError("policy_id must be non-empty")
    if not isinstance(threshold_policy, Mapping) or not threshold_policy:
        raise NoninterferenceValidationError("threshold_policy must be a non-empty object")
    if frozen_before_outcomes is not True:
        raise NoninterferenceValidationError("policy must be frozen before outcomes")
    _parse_timestamp(frozen_at)
    for digest in (
        evaluator_rubric_digest,
        value_policy_digest,
        analysis_plan_digest,
    ):
        _normalize_digest(digest)
    threshold_policy_digest = canonical_digest(dict(threshold_policy))
    record: dict[str, Any] = {
        "schema_version": POLICY_SCHEMA_VERSION,
        "policy_id": policy_id,
        "threshold_policy": deepcopy(dict(threshold_policy)),
        "threshold_policy_digest": threshold_policy_digest,
        "evidence_rung": evidence_rung,
        "evaluator_rubric_digest": _normalize_digest(evaluator_rubric_digest),
        "value_policy_digest": _normalize_digest(value_policy_digest),
        "analysis_plan_digest": _normalize_digest(analysis_plan_digest),
        "frozen_at": frozen_at,
        "frozen_before_outcomes": True,
        "claim_ceiling": CLAIM_CEILING,
    }
    record["policy_bundle_digest"] = canonical_digest(record)
    return record


def validate_frozen_policy_bundle(bundle: Mapping[str, Any]) -> None:
    _require_text(
        bundle,
        (
            "schema_version",
            "policy_id",
            "threshold_policy_digest",
            "evidence_rung",
            "evaluator_rubric_digest",
            "value_policy_digest",
            "analysis_plan_digest",
            "frozen_at",
            "claim_ceiling",
            "policy_bundle_digest",
        ),
        "FrozenQualificationPolicy.v1",
    )
    if bundle["schema_version"] != POLICY_SCHEMA_VERSION:
        raise NoninterferenceValidationError("policy schema_version mismatch")
    if bundle.get("frozen_before_outcomes") is not True:
        raise NoninterferenceValidationError("policy was not frozen before outcomes")
    _parse_timestamp(str(bundle["frozen_at"]))
    for field in (
        "threshold_policy_digest",
        "evaluator_rubric_digest",
        "value_policy_digest",
        "analysis_plan_digest",
        "policy_bundle_digest",
    ):
        _normalize_digest(str(bundle[field]))
    if canonical_digest(dict(bundle["threshold_policy"])) != bundle["threshold_policy_digest"]:
        raise NoninterferenceValidationError("threshold policy digest mismatch")
    expected = canonical_digest(_copy_without_digest(bundle, "policy_bundle_digest"))
    if expected != bundle["policy_bundle_digest"]:
        raise NoninterferenceValidationError("policy bundle digest mismatch")


def build_experiment_epoch(
    *,
    epoch_id: str,
    epoch_kind: str,
    surface_digests: Mapping[str, str],
    policy_bundle: Mapping[str, Any],
    start_at: str,
    opened_before_outcomes: bool = True,
    state: str = "FROZEN_PRE_OUTCOME",
) -> dict[str, Any]:
    if epoch_kind not in EPOCH_KINDS:
        raise NoninterferenceValidationError("unsupported epoch_kind")
    if state not in EPOCH_STATES:
        raise NoninterferenceValidationError("unsupported epoch state")
    if opened_before_outcomes is not True:
        raise NoninterferenceValidationError("epoch must open before outcomes")
    _parse_timestamp(start_at)
    validate_surface_digests(surface_digests)
    validate_frozen_policy_bundle(policy_bundle)
    if _normalize_digest(surface_digests["evaluator_rubric_digest"]) != policy_bundle["evaluator_rubric_digest"]:
        raise NoninterferenceValidationError("epoch evaluator rubric differs from policy bundle")
    if _normalize_digest(surface_digests["value_policy_digest"]) != policy_bundle["value_policy_digest"]:
        raise NoninterferenceValidationError("epoch value policy differs from policy bundle")
    if _normalize_digest(surface_digests["analysis_plan_digest"]) != policy_bundle["analysis_plan_digest"]:
        raise NoninterferenceValidationError("epoch analysis plan differs from policy bundle")
    record: dict[str, Any] = {
        "schema_version": EPOCH_SCHEMA_VERSION,
        "program_id": PROGRAM_ID,
        "epoch_id": epoch_id,
        "epoch_kind": epoch_kind,
        "state": state,
        "opened_before_outcomes": True,
        "start_at": start_at,
        "closed_at_or_null": None,
        "close_reason_or_null": None,
        "policy_bundle_digest": policy_bundle["policy_bundle_digest"],
        "threshold_policy_digest_or_null": policy_bundle["threshold_policy_digest"],
        "claim_ceiling": CLAIM_CEILING,
    }
    for name in REQUIRED_SURFACE_DIGESTS:
        record[name] = _normalize_digest(surface_digests[name])
    record["epoch_digest"] = canonical_digest(record)
    return record


def validate_experiment_epoch(
    epoch: Mapping[str, Any],
    *,
    policy_bundle: Mapping[str, Any] | None = None,
) -> None:
    _require_text(
        epoch,
        (
            "schema_version",
            "program_id",
            "epoch_id",
            "epoch_kind",
            "state",
            "start_at",
            "policy_bundle_digest",
            "claim_ceiling",
            "epoch_digest",
        ),
        "ExperimentEpoch.v1",
    )
    _require_fields(
        epoch,
        ("opened_before_outcomes", "closed_at_or_null", "close_reason_or_null"),
        "ExperimentEpoch.v1",
    )
    if epoch["schema_version"] != EPOCH_SCHEMA_VERSION:
        raise NoninterferenceValidationError("epoch schema_version mismatch")
    if epoch["program_id"] != PROGRAM_ID:
        raise NoninterferenceValidationError("epoch program_id mismatch")
    if epoch["epoch_kind"] not in EPOCH_KINDS:
        raise NoninterferenceValidationError("unsupported epoch_kind")
    if epoch["state"] not in EPOCH_STATES:
        raise NoninterferenceValidationError("unsupported epoch state")
    if epoch["opened_before_outcomes"] is not True:
        raise NoninterferenceValidationError("epoch was not opened before outcomes")
    _parse_timestamp(str(epoch["start_at"]))
    validate_surface_digests({name: str(epoch[name]) for name in REQUIRED_SURFACE_DIGESTS})
    _normalize_digest(str(epoch["policy_bundle_digest"]))
    expected = canonical_digest(_copy_without_digest(epoch, "epoch_digest"))
    if expected != epoch["epoch_digest"]:
        raise NoninterferenceValidationError("epoch digest mismatch")
    if policy_bundle is not None:
        validate_frozen_policy_bundle(policy_bundle)
        if epoch["policy_bundle_digest"] != policy_bundle["policy_bundle_digest"]:
            raise NoninterferenceValidationError("epoch/policy bundle digest mismatch")


def build_surface_snapshot(
    *,
    trajectory_id: str,
    episode_id: str,
    condition_id: str,
    assignment_receipt_ref: str,
    epoch: Mapping[str, Any],
    flag_values: Mapping[str, Any],
    surface_digests: Mapping[str, str],
    history_snapshot_ref: str,
    consent_scope_snapshot_ref: str,
    accessibility_profile_ref: str,
    timestamp: str,
    captured_before_episode_start: bool = True,
) -> dict[str, Any]:
    validate_experiment_epoch(epoch)
    validate_flag_values(flag_values)
    validate_surface_digests(surface_digests)
    if captured_before_episode_start is not True:
        raise NoninterferenceValidationError("surface snapshot must precede episode start")
    if flag_values["analysis.epoch_kind"] != epoch["epoch_kind"]:
        raise NoninterferenceValidationError("flag epoch kind differs from bound epoch")
    for name in REQUIRED_SURFACE_DIGESTS:
        if _normalize_digest(surface_digests[name]) != epoch[name]:
            raise NoninterferenceValidationError(
                f"surface digest {name} differs from bound epoch"
            )
    _parse_timestamp(timestamp)
    record: dict[str, Any] = {
        "schema_version": SURFACE_SCHEMA_VERSION,
        "program_id": PROGRAM_ID,
        "trajectory_id": trajectory_id,
        "episode_id": episode_id,
        "condition_id": condition_id,
        "assignment_receipt_ref": assignment_receipt_ref,
        "epoch_id": epoch["epoch_id"],
        "epoch_digest": epoch["epoch_digest"],
        "flag_values": deepcopy(dict(flag_values)),
        "surface_digests": {
            name: _normalize_digest(surface_digests[name])
            for name in REQUIRED_SURFACE_DIGESTS
        },
        "history_snapshot_ref": history_snapshot_ref,
        "consent_scope_snapshot_ref": consent_scope_snapshot_ref,
        "accessibility_profile_ref": accessibility_profile_ref,
        "captured_before_episode_start": True,
        "timestamp": timestamp,
        "claim_ceiling": CLAIM_CEILING,
    }
    record["surface_snapshot_digest"] = canonical_digest(record)
    record["surface_snapshot_ref"] = stable_ref("surface", record)
    return record


def validate_surface_snapshot(
    snapshot: Mapping[str, Any],
    *,
    epoch: Mapping[str, Any] | None = None,
) -> None:
    _require_text(
        snapshot,
        (
            "schema_version",
            "program_id",
            "trajectory_id",
            "episode_id",
            "condition_id",
            "assignment_receipt_ref",
            "epoch_id",
            "epoch_digest",
            "history_snapshot_ref",
            "consent_scope_snapshot_ref",
            "accessibility_profile_ref",
            "timestamp",
            "claim_ceiling",
            "surface_snapshot_digest",
            "surface_snapshot_ref",
        ),
        "EpisodeSurfaceSnapshot.v1",
    )
    _require_fields(
        snapshot,
        ("flag_values", "surface_digests", "captured_before_episode_start"),
        "EpisodeSurfaceSnapshot.v1",
    )
    if snapshot["schema_version"] != SURFACE_SCHEMA_VERSION:
        raise NoninterferenceValidationError("surface snapshot schema mismatch")
    if snapshot["program_id"] != PROGRAM_ID:
        raise NoninterferenceValidationError("surface snapshot program mismatch")
    if snapshot["captured_before_episode_start"] is not True:
        raise NoninterferenceValidationError("surface snapshot was not prospective")
    _parse_timestamp(str(snapshot["timestamp"]))
    validate_flag_values(snapshot["flag_values"])
    validate_surface_digests(snapshot["surface_digests"])
    expected = canonical_digest(
        {
            key: deepcopy(value)
            for key, value in snapshot.items()
            if key not in {"surface_snapshot_digest", "surface_snapshot_ref"}
        }
    )
    if expected != snapshot["surface_snapshot_digest"]:
        raise NoninterferenceValidationError("surface snapshot digest mismatch")
    if snapshot["surface_snapshot_ref"] != stable_ref(
        "surface",
        {
            **{
                key: deepcopy(value)
                for key, value in snapshot.items()
                if key not in {"surface_snapshot_digest", "surface_snapshot_ref"}
            },
            "surface_snapshot_digest": snapshot["surface_snapshot_digest"],
        },
    ):
        if not str(snapshot["surface_snapshot_ref"]).startswith("surface:"):
            raise NoninterferenceValidationError("surface snapshot ref mismatch")
    if epoch is not None:
        validate_experiment_epoch(epoch)
        if snapshot["epoch_id"] != epoch["epoch_id"]:
            raise NoninterferenceValidationError("snapshot epoch_id mismatch")
        if snapshot["epoch_digest"] != epoch["epoch_digest"]:
            raise NoninterferenceValidationError("snapshot epoch_digest mismatch")
        for name in REQUIRED_SURFACE_DIGESTS:
            if _normalize_digest(snapshot["surface_digests"][name]) != epoch[name]:
                raise NoninterferenceValidationError(
                    f"snapshot/epoch mismatch for {name}"
                )


def bind_event_to_surface(
    event: Mapping[str, Any],
    *,
    epoch: Mapping[str, Any],
    snapshot: Mapping[str, Any],
    policy_bundle: Mapping[str, Any],
) -> dict[str, Any]:
    validate_experiment_epoch(epoch, policy_bundle=policy_bundle)
    validate_surface_snapshot(snapshot, epoch=epoch)
    bound = deepcopy(dict(event))
    bound.update(
        {
            "epoch_id": epoch["epoch_id"],
            "epoch_digest": epoch["epoch_digest"],
            "surface_snapshot_ref": snapshot["surface_snapshot_ref"],
            "surface_snapshot_digest": snapshot["surface_snapshot_digest"],
            "assignment_receipt_ref": snapshot["assignment_receipt_ref"],
            "policy_bundle_digest": policy_bundle["policy_bundle_digest"],
            "surface_flag_snapshot": deepcopy(snapshot["flag_values"]),
        }
    )
    bound["event_binding_digest"] = canonical_digest(bound)
    return bound


def validate_bound_event(
    event: Mapping[str, Any],
    *,
    epoch: Mapping[str, Any],
    snapshot: Mapping[str, Any],
    policy_bundle: Mapping[str, Any],
) -> None:
    _require_fields(event, BOUND_EVENT_FIELDS, "BoundRepeatUseEvent.v1")
    _require_text(
        event,
        (
            "epoch_id",
            "epoch_digest",
            "surface_snapshot_ref",
            "surface_snapshot_digest",
            "assignment_receipt_ref",
            "policy_bundle_digest",
            "event_binding_digest",
        ),
        "BoundRepeatUseEvent.v1",
    )
    validate_experiment_epoch(epoch, policy_bundle=policy_bundle)
    validate_surface_snapshot(snapshot, epoch=epoch)
    expected_pairs = {
        "epoch_id": epoch["epoch_id"],
        "epoch_digest": epoch["epoch_digest"],
        "surface_snapshot_ref": snapshot["surface_snapshot_ref"],
        "surface_snapshot_digest": snapshot["surface_snapshot_digest"],
        "assignment_receipt_ref": snapshot["assignment_receipt_ref"],
        "policy_bundle_digest": policy_bundle["policy_bundle_digest"],
    }
    for field, expected in expected_pairs.items():
        if event[field] != expected:
            raise NoninterferenceValidationError(f"bound event mismatch for {field}")
    if dict(event["surface_flag_snapshot"]) != dict(snapshot["flag_values"]):
        raise NoninterferenceValidationError("bound event surface flags drifted")
    for field in ("trajectory_id", "episode_id", "condition_id"):
        if field in event and event[field] != snapshot[field]:
            raise NoninterferenceValidationError(
                f"bound event {field} differs from surface snapshot"
            )
    expected = canonical_digest(_copy_without_digest(event, "event_binding_digest"))
    if expected != event["event_binding_digest"]:
        raise NoninterferenceValidationError("bound event digest mismatch")



__all__ = [name for name in globals() if not name.startswith("__")]
