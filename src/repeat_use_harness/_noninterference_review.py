"""Independent review, frozen-policy, and qualification controls."""
from __future__ import annotations
from ._noninterference_common import *
from ._noninterference_epoch import *
from ._noninterference_change import *

def build_independent_review_binding(
    *,
    review_id: str,
    epoch: Mapping[str, Any],
    trajectory_digest: str,
    policy_bundle: Mapping[str, Any],
    positive_terminal_gates: Mapping[str, bool],
    accepted_current: bool,
    reviewed_at: str,
) -> dict[str, Any]:
    validate_experiment_epoch(epoch, policy_bundle=policy_bundle)
    _normalize_digest(trajectory_digest)
    _parse_timestamp(reviewed_at)
    record: dict[str, Any] = {
        "schema_version": REVIEW_SCHEMA_VERSION,
        "review_id": review_id,
        "epoch_id": epoch["epoch_id"],
        "epoch_digest": epoch["epoch_digest"],
        "trajectory_digest": _normalize_digest(trajectory_digest),
        "policy_bundle_digest": policy_bundle["policy_bundle_digest"],
        "evaluator_rubric_digest": policy_bundle["evaluator_rubric_digest"],
        "value_policy_digest": policy_bundle["value_policy_digest"],
        "threshold_policy_digest": policy_bundle["threshold_policy_digest"],
        "analysis_plan_digest": policy_bundle["analysis_plan_digest"],
        "positive_terminal_gates": deepcopy(dict(positive_terminal_gates)),
        "accepted_current": bool(accepted_current),
        "reviewed_at": reviewed_at,
        "claim_ceiling": CLAIM_CEILING,
    }
    record["review_digest"] = canonical_digest(record)
    return record


def validate_independent_review_binding(
    review: Mapping[str, Any],
    *,
    epoch: Mapping[str, Any],
    trajectory_digest: str,
    policy_bundle: Mapping[str, Any],
) -> None:
    _require_text(
        review,
        (
            "schema_version",
            "review_id",
            "epoch_id",
            "epoch_digest",
            "trajectory_digest",
            "policy_bundle_digest",
            "evaluator_rubric_digest",
            "value_policy_digest",
            "threshold_policy_digest",
            "analysis_plan_digest",
            "reviewed_at",
            "claim_ceiling",
            "review_digest",
        ),
        "IndependentReviewBinding.v1",
    )
    if review["schema_version"] != REVIEW_SCHEMA_VERSION:
        raise NoninterferenceValidationError("review schema mismatch")
    validate_experiment_epoch(epoch, policy_bundle=policy_bundle)
    expected_pairs = {
        "epoch_id": epoch["epoch_id"],
        "epoch_digest": epoch["epoch_digest"],
        "trajectory_digest": _normalize_digest(trajectory_digest),
        "policy_bundle_digest": policy_bundle["policy_bundle_digest"],
        "evaluator_rubric_digest": policy_bundle["evaluator_rubric_digest"],
        "value_policy_digest": policy_bundle["value_policy_digest"],
        "threshold_policy_digest": policy_bundle["threshold_policy_digest"],
        "analysis_plan_digest": policy_bundle["analysis_plan_digest"],
    }
    for field, expected in expected_pairs.items():
        if review[field] != expected:
            raise NoninterferenceValidationError(f"review binding mismatch for {field}")
    _parse_timestamp(str(review["reviewed_at"]))
    expected = canonical_digest(_copy_without_digest(review, "review_digest"))
    if expected != review["review_digest"]:
        raise NoninterferenceValidationError("review digest mismatch")


def qualification_policy_from_bundle(
    policy_bundle: Mapping[str, Any],
    *,
    replay_overrides: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    validate_frozen_policy_bundle(policy_bundle)
    if replay_overrides:
        raise NoninterferenceValidationError(
            "qualification replay policy overrides are forbidden after freeze"
        )
    policy = deepcopy(dict(policy_bundle["threshold_policy"]))
    policy["evidence_rung"] = policy_bundle["evidence_rung"]
    policy["policy_bundle_digest"] = policy_bundle["policy_bundle_digest"]
    return policy


def qualify_noninterference(
    *,
    epoch: Mapping[str, Any],
    policy_bundle: Mapping[str, Any],
    snapshots: Sequence[Mapping[str, Any]],
    change_receipts: Sequence[Mapping[str, Any]],
    familiarization_receipts: Sequence[Mapping[str, Any]],
    reactivity_result: Mapping[str, Any] | None,
    independent_review: Mapping[str, Any] | None,
    trajectory_digest: str | None,
) -> dict[str, Any]:
    validate_experiment_epoch(epoch, policy_bundle=policy_bundle)
    for snapshot in snapshots:
        validate_surface_snapshot(snapshot, epoch=epoch)
    if not snapshots:
        terminal = "ASSIGNMENT_OR_SURFACE_SNAPSHOT_MISSING"
        reasons = ["no prospectively captured surface snapshot"]
    elif epoch["epoch_kind"] == "DEVELOPMENT" and independent_review is not None:
        terminal = "DEVELOPMENT_QUALIFICATION_CONTAMINATION"
        reasons = ["development epoch cannot qualify the version it changed"]
    elif any(receipt.get("new_epoch_required") is True for receipt in change_receipts):
        product_change = any(
            "P_PRODUCT" in receipt.get("changed_planes", [])
            for receipt in change_receipts
        )
        terminal = "PRODUCT_SURFACE_DRIFT" if product_change else "MEASUREMENT_SURFACE_DRIFT"
        reasons = ["unplanned material surface change requires a new epoch"]
    elif not familiarization_receipts:
        terminal = "RIGHT_CENSORED"
        reasons = ["interface novelty/familiarization state is unobserved"]
    elif reactivity_result is None:
        terminal = "RIGHT_CENSORED"
        reasons = ["dedicated instrumentation-dose contrast is unobserved"]
    elif reactivity_result.get("terminal") in {
        "NON_IDENTIFIABLE",
        "RIGHT_CENSORED",
        "MEASUREMENT_REACTIVE",
    }:
        terminal = str(reactivity_result["terminal"])
        reasons = list(reactivity_result.get("reasons", []))
    elif independent_review is None or trajectory_digest is None:
        terminal = "ANALYSIS_POLICY_DRIFT"
        reasons = ["qualification review is not content-bound"]
    else:
        for receipt in familiarization_receipts:
            validate_familiarization_receipt(receipt)
        validate_independent_review_binding(
            independent_review,
            epoch=epoch,
            trajectory_digest=trajectory_digest,
            policy_bundle=policy_bundle,
        )
        terminal = "INSTRUMENTATION_READY"
        reasons = [
            "full epoch/surface, novelty, reactivity, frozen-policy, and review bindings pass"
        ]
    result: dict[str, Any] = {
        "schema_version": "gva06.f.ruv.instrumentation-noninterference-qualification.v1",
        "epoch_id": epoch["epoch_id"],
        "epoch_digest": epoch["epoch_digest"],
        "policy_bundle_digest": policy_bundle["policy_bundle_digest"],
        "snapshot_count": len(snapshots),
        "change_receipt_count": len(change_receipts),
        "familiarization_receipt_count": len(familiarization_receipts),
        "terminal": terminal,
        "reasons": reasons,
        "human_value_supported": False,
        "product_direction_authorized": False,
        "claim_ceiling": CLAIM_CEILING,
    }
    result["qualification_digest"] = canonical_digest(result)
    return result



__all__ = [name for name in globals() if not name.startswith("__")]
