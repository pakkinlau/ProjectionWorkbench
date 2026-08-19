"""Surface change, pooling, familiarization, and reactivity controls."""
from __future__ import annotations
from statistics import mean
from ._noninterference_common import *
from ._noninterference_epoch import *

def _surface_differences(
    left: Mapping[str, Any], right: Mapping[str, Any]
) -> tuple[list[str], list[str], list[str]]:
    validate_surface_snapshot(left)
    validate_surface_snapshot(right)
    changed_flags = sorted(
        name
        for name in FLAG_ALLOWED_VALUES
        if left["flag_values"][name] != right["flag_values"][name]
    )
    changed_digests = sorted(
        name
        for name in REQUIRED_SURFACE_DIGESTS
        if _normalize_digest(left["surface_digests"][name])
        != _normalize_digest(right["surface_digests"][name])
    )
    changed_planes = sorted(
        {
            *(PLANE_BY_FLAG[name] for name in changed_flags),
            *(PLANE_BY_DIGEST[name] for name in changed_digests),
        }
    )
    return changed_flags, changed_digests, changed_planes


def build_surface_change_receipt(
    *,
    change_id: str,
    before_snapshot: Mapping[str, Any],
    after_snapshot: Mapping[str, Any],
    planned_contrast: Mapping[str, Any] | None,
    outcomes_visible: bool,
    affected_episode_ids: Sequence[str],
) -> dict[str, Any]:
    changed_flags, changed_digests, changed_planes = _surface_differences(
        before_snapshot, after_snapshot
    )
    allowed_flags = set((planned_contrast or {}).get("allowed_flag_differences", []))
    allowed_digests = set((planned_contrast or {}).get("allowed_digest_differences", []))
    unplanned_flags = sorted(set(changed_flags) - allowed_flags)
    unplanned_digests = sorted(set(changed_digests) - allowed_digests)
    has_change = bool(changed_flags or changed_digests)
    exact_planned = has_change and not unplanned_flags and not unplanned_digests
    materiality = (
        "NO_CHANGE"
        if not has_change
        else "EXACT_PREDECLARED_CONTRAST"
        if exact_planned
        else "UNPLANNED_MATERIAL_CHANGE"
    )
    new_epoch_required = bool(unplanned_flags or unplanned_digests)
    active_episode_disposition = (
        "RIGHT_CENSORED"
        if new_epoch_required and outcomes_visible
        else "RESTART_REQUIRED"
        if new_epoch_required
        else "UNCHANGED"
    )
    route_effect = (
        "OPEN_NEW_EPOCH_AND_REQUALIFY"
        if new_epoch_required
        else "RETAIN_PREDECLARED_CONTRAST"
        if exact_planned
        else "NO_ROUTE_CHANGE"
    )
    record: dict[str, Any] = {
        "schema_version": CHANGE_SCHEMA_VERSION,
        "change_id": change_id,
        "before_snapshot_ref": before_snapshot["surface_snapshot_ref"],
        "after_snapshot_ref": after_snapshot["surface_snapshot_ref"],
        "changed_flags": changed_flags,
        "changed_digests": changed_digests,
        "changed_planes": changed_planes,
        "unplanned_flags": unplanned_flags,
        "unplanned_digests": unplanned_digests,
        "materiality": materiality,
        "outcomes_visible": bool(outcomes_visible),
        "planned_contrast": deepcopy(dict(planned_contrast or {})),
        "affected_episode_ids": list(affected_episode_ids),
        "new_epoch_required": new_epoch_required,
        "active_episode_disposition": active_episode_disposition,
        "pooling_consequence": (
            "NON_IDENTIFIABLE_WITHOUT_NEW_EPOCH"
            if new_epoch_required
            else "POOL_ONLY_AS_PREDECLARED_CONTRAST"
            if exact_planned
            else "UNCHANGED"
        ),
        "route_effect": route_effect,
        "claim_ceiling": CLAIM_CEILING,
    }
    record["change_digest"] = canonical_digest(record)
    return record


def close_epoch_for_change(
    epoch: Mapping[str, Any],
    change_receipt: Mapping[str, Any],
    *,
    closed_at: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    validate_experiment_epoch(epoch)
    _parse_timestamp(closed_at)
    if change_receipt.get("new_epoch_required") is not True:
        raise NoninterferenceValidationError("change does not require an epoch boundary")
    closed = deepcopy(dict(epoch))
    closed["state"] = "CLOSED"
    closed["closed_at_or_null"] = closed_at
    closed["close_reason_or_null"] = change_receipt["materiality"]
    closed["epoch_digest"] = canonical_digest(
        _copy_without_digest(closed, "epoch_digest")
    )
    receipt: dict[str, Any] = {
        "schema_version": "gva06.f.ruv.epoch-boundary-receipt.v1",
        "prior_epoch_id": epoch["epoch_id"],
        "prior_epoch_digest": epoch["epoch_digest"],
        "closed_epoch_digest": closed["epoch_digest"],
        "change_digest": change_receipt["change_digest"],
        "active_episode_disposition": change_receipt["active_episode_disposition"],
        "next_epoch_required": True,
        "reentry": (
            "Freeze a new epoch and new surface snapshots before any additional "
            "assigned episode; do not pool active or prior outcomes silently."
        ),
        "claim_ceiling": CLAIM_CEILING,
    }
    receipt["boundary_digest"] = canonical_digest(receipt)
    return closed, receipt


def build_pooling_eligibility_receipt(
    *,
    comparison_id: str,
    left_snapshot: Mapping[str, Any],
    right_snapshot: Mapping[str, Any],
    predeclared_contrast: Mapping[str, Any],
    carryover_status: str,
) -> dict[str, Any]:
    changed_flags, changed_digests, changed_planes = _surface_differences(
        left_snapshot, right_snapshot
    )
    allowed_flags = set(predeclared_contrast.get("allowed_flag_differences", []))
    allowed_digests = set(predeclared_contrast.get("allowed_digest_differences", []))
    exact = set(changed_flags).issubset(allowed_flags) and set(changed_digests).issubset(
        allowed_digests
    )
    controlled = carryover_status == "CONTROLLED"
    disposition = "POOL_ALLOWED" if exact and controlled else "NON_IDENTIFIABLE"
    record: dict[str, Any] = {
        "schema_version": POOLING_SCHEMA_VERSION,
        "comparison_id": comparison_id,
        "left_snapshot_ref": left_snapshot["surface_snapshot_ref"],
        "right_snapshot_ref": right_snapshot["surface_snapshot_ref"],
        "predeclared_contrast": deepcopy(dict(predeclared_contrast)),
        "equal_required_planes": [
            plane
            for plane in sorted(set(PLANE_BY_FLAG.values()) | set(PLANE_BY_DIGEST.values()))
            if plane not in changed_planes
        ],
        "observed_differences": {
            "flags": changed_flags,
            "digests": changed_digests,
            "planes": changed_planes,
        },
        "carryover_status": carryover_status,
        "pooling_disposition": disposition,
        "reason": (
            "Only the prospectively declared contrast differs and carryover is controlled."
            if disposition == "POOL_ALLOWED"
            else "An undeclared surface difference or uncontrolled carryover prevents pooling."
        ),
        "claim_ceiling": CLAIM_CEILING,
    }
    record["pooling_digest"] = canonical_digest(record)
    return record


def build_familiarization_receipt(
    *,
    receipt_id: str,
    participant_id: str,
    interface_build_digest: str,
    prior_exposure_count: int,
    warmup_task_ref: str,
    completed_before_assignment: bool,
    outcome_blind: bool,
    timestamp: str,
) -> dict[str, Any]:
    if prior_exposure_count < 0:
        raise NoninterferenceValidationError("prior exposure count cannot be negative")
    if completed_before_assignment is not True or outcome_blind is not True:
        raise NoninterferenceValidationError(
            "familiarization must be prospective and outcome blind"
        )
    _normalize_digest(interface_build_digest)
    _parse_timestamp(timestamp)
    record: dict[str, Any] = {
        "schema_version": FAMILIARIZATION_SCHEMA_VERSION,
        "receipt_id": receipt_id,
        "participant_id": participant_id,
        "interface_build_digest": _normalize_digest(interface_build_digest),
        "prior_exposure_count": prior_exposure_count,
        "warmup_task_ref": warmup_task_ref,
        "completed_before_assignment": True,
        "outcome_blind": True,
        "timestamp": timestamp,
        "claim_ceiling": CLAIM_CEILING,
    }
    record["familiarization_digest"] = canonical_digest(record)
    return record


def validate_familiarization_receipt(receipt: Mapping[str, Any]) -> None:
    _require_text(
        receipt,
        (
            "schema_version",
            "receipt_id",
            "participant_id",
            "interface_build_digest",
            "warmup_task_ref",
            "timestamp",
            "claim_ceiling",
            "familiarization_digest",
        ),
        "InterfaceFamiliarizationReceipt.v1",
    )
    if receipt["schema_version"] != FAMILIARIZATION_SCHEMA_VERSION:
        raise NoninterferenceValidationError("familiarization schema mismatch")
    if receipt.get("completed_before_assignment") is not True:
        raise NoninterferenceValidationError("familiarization was not pre-assignment")
    if receipt.get("outcome_blind") is not True:
        raise NoninterferenceValidationError("familiarization was not outcome blind")
    if not isinstance(receipt.get("prior_exposure_count"), int) or receipt[
        "prior_exposure_count"
    ] < 0:
        raise NoninterferenceValidationError("invalid prior exposure count")
    _normalize_digest(str(receipt["interface_build_digest"]))
    _parse_timestamp(str(receipt["timestamp"]))
    expected = canonical_digest(
        _copy_without_digest(receipt, "familiarization_digest")
    )
    if expected != receipt["familiarization_digest"]:
        raise NoninterferenceValidationError("familiarization digest mismatch")


def build_instrumentation_contrast(
    *,
    contrast_id: str,
    left_snapshot: Mapping[str, Any],
    right_snapshot: Mapping[str, Any],
    burden_budget_minutes: float,
    interaction_estimand: str,
    predeclared_at: str,
) -> dict[str, Any]:
    validate_surface_snapshot(left_snapshot)
    validate_surface_snapshot(right_snapshot)
    if burden_budget_minutes < 0:
        raise NoninterferenceValidationError("burden budget cannot be negative")
    _parse_timestamp(predeclared_at)
    left_dose = left_snapshot["flag_values"]["measurement.capture_tier"]
    right_dose = right_snapshot["flag_values"]["measurement.capture_tier"]
    if left_dose == right_dose:
        raise NoninterferenceValidationError("instrumentation doses must differ")
    changed_flags, changed_digests, changed_planes = _surface_differences(
        left_snapshot, right_snapshot
    )
    allowed_flags = {
        name for name in changed_flags if PLANE_BY_FLAG[name] == "P_MEASUREMENT"
    }
    allowed_digests = {
        name for name in changed_digests if PLANE_BY_DIGEST[name] == "P_MEASUREMENT"
    }
    if "measurement.capture_tier" not in allowed_flags:
        raise NoninterferenceValidationError(
            "instrumentation contrast must change measurement.capture_tier"
        )
    product_constant = "P_PRODUCT" not in changed_planes
    context_constant = all(plane == "P_MEASUREMENT" for plane in changed_planes)
    record: dict[str, Any] = {
        "schema_version": REACTIVITY_SCHEMA_VERSION,
        "contrast_id": contrast_id,
        "left_snapshot_ref": left_snapshot["surface_snapshot_ref"],
        "right_snapshot_ref": right_snapshot["surface_snapshot_ref"],
        "left_dose": left_dose,
        "right_dose": right_dose,
        "allowed_flag_differences": sorted(allowed_flags),
        "allowed_digest_differences": sorted(allowed_digests),
        "product_constant": product_constant,
        "all_nonmeasurement_planes_constant": context_constant,
        "burden_budget_minutes": float(burden_budget_minutes),
        "interaction_estimand": interaction_estimand,
        "predeclared_at": predeclared_at,
        "outcome_blind": True,
        "claim_ceiling": CLAIM_CEILING,
    }
    record["contrast_digest"] = canonical_digest(record)
    return record


def validate_instrumentation_contrast(contrast: Mapping[str, Any]) -> None:
    _require_text(
        contrast,
        (
            "schema_version",
            "contrast_id",
            "left_snapshot_ref",
            "right_snapshot_ref",
            "left_dose",
            "right_dose",
            "interaction_estimand",
            "predeclared_at",
            "claim_ceiling",
            "contrast_digest",
        ),
        "InstrumentationReactivityContrast.v1",
    )
    if contrast["schema_version"] != REACTIVITY_SCHEMA_VERSION:
        raise NoninterferenceValidationError("reactivity contrast schema mismatch")
    if contrast["left_dose"] not in INSTRUMENTATION_DOSES:
        raise NoninterferenceValidationError("invalid left instrumentation dose")
    if contrast["right_dose"] not in INSTRUMENTATION_DOSES:
        raise NoninterferenceValidationError("invalid right instrumentation dose")
    if contrast["left_dose"] == contrast["right_dose"]:
        raise NoninterferenceValidationError("reactivity contrast doses are equal")
    if contrast.get("outcome_blind") is not True:
        raise NoninterferenceValidationError("reactivity contrast is not outcome blind")
    _parse_timestamp(str(contrast["predeclared_at"]))
    expected = canonical_digest(_copy_without_digest(contrast, "contrast_digest"))
    if expected != contrast["contrast_digest"]:
        raise NoninterferenceValidationError("reactivity contrast digest mismatch")


def evaluate_instrumentation_reactivity(
    *,
    contrast: Mapping[str, Any],
    left_observations: Sequence[Mapping[str, Any]],
    right_observations: Sequence[Mapping[str, Any]],
    minimum_per_arm: int = 1,
    burden_delta_threshold_minutes: float = 5.0,
) -> dict[str, Any]:
    validate_instrumentation_contrast(contrast)
    if contrast.get("product_constant") is not True or contrast.get(
        "all_nonmeasurement_planes_constant"
    ) is not True:
        terminal = "NON_IDENTIFIABLE"
        reasons = ["nonmeasurement plane changed inside the reactivity contrast"]
    elif len(left_observations) < minimum_per_arm or len(right_observations) < minimum_per_arm:
        terminal = "RIGHT_CENSORED"
        reasons = ["insufficient prospectively observed episodes per instrumentation arm"]
    else:
        def burden(row: Mapping[str, Any]) -> float:
            return float(row.get("capture_minutes", 0.0)) + float(
                row.get("review_and_correction_minutes", 0.0)
            )

        left_burden = mean(burden(row) for row in left_observations)
        right_burden = mean(burden(row) for row in right_observations)
        delta = right_burden - left_burden
        explicit_reactivity = any(
            row.get("measurement_reactive_confirmed_by_human") is True
            or row.get("reactivity_event") == "MEASUREMENT_REACTIVE"
            for row in [*left_observations, *right_observations]
        )
        if explicit_reactivity or abs(delta) > burden_delta_threshold_minutes:
            terminal = "MEASUREMENT_REACTIVE"
            reasons = [
                "explicit human/reactivity event or burden delta exceeded the frozen threshold"
            ]
        else:
            terminal = "NO_REACTIVITY_OBSERVED_AT_BOUND"
            reasons = ["no bounded reactivity signal under the predeclared matched contrast"]
    record: dict[str, Any] = {
        "schema_version": "gva06.f.ruv.instrumentation-reactivity-result.v1",
        "contrast_digest": contrast["contrast_digest"],
        "left_episode_count": len(left_observations),
        "right_episode_count": len(right_observations),
        "minimum_per_arm": minimum_per_arm,
        "burden_delta_threshold_minutes": burden_delta_threshold_minutes,
        "terminal": terminal,
        "reasons": reasons,
        "human_value_supported": False,
        "claim_ceiling": CLAIM_CEILING,
    }
    record["result_digest"] = canonical_digest(record)
    return record



__all__ = [name for name in globals() if not name.startswith("__")]
