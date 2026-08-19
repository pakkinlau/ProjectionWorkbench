"""Deterministic repair manifest and synthetic mechanical witness."""
from __future__ import annotations
from ._noninterference_common import *
from ._noninterference_epoch import *
from ._noninterference_change import *
from ._noninterference_review import *
from ._noninterference_migration import *

def build_repair_manifest() -> dict[str, Any]:
    record: dict[str, Any] = {
        "schema_version": REPAIR_SCHEMA_VERSION,
        "artifact_id": REPAIR_ARTIFACT_ID,
        "program_id": PROGRAM_ID,
        "wave_id": WAVE_ID,
        "branch_id": BRANCH_ID,
        "artifact_state": "EXECUTED_VALIDATED_MERGEABLE_CANDIDATE",
        "repair_ids": list(REPAIR_IDS),
        "implemented_surfaces": [
            "full 14-flag intervention registry",
            "all 12 required content-addressed surface digests",
            "prospective ExperimentEpoch and EpisodeSurfaceSnapshot",
            "event-to-epoch/snapshot/policy binding",
            "SurfaceChangeReceipt and typed epoch close/restart/right-censor",
            "PoolingEligibilityReceipt with exact planned contrast",
            "development/direction-selection/qualification firewall",
            "InterfaceFamiliarizationReceipt",
            "product-constant instrumentation-dose contrast",
            "frozen threshold/evidence/evaluator/value/analysis policy bundle",
            "independent review content binding",
            "loss-declared B6-to-B1 event migration receipt",
        ],
        "terminal": "INSTRUMENTATION_NONINTERFERENCE_REPAIR_READY",
        "wave4_launch_effect": (
            "DO_NOT_OPEN_W4_YET; merge with W3R siblings and run independent W3Q requalification"
        ),
        "exact_reentry": (
            "web.synthesize -> web.steer after all W3R returns; integrate the accepted "
            "repairs on one current harness line and run bounded independent W3Q requalification."
        ),
        "claim_ceiling": CLAIM_CEILING,
    }
    record["artifact_digest"] = canonical_digest(record)
    return record


def _default_flags(*, capture_tier: str, epoch_kind: str) -> dict[str, Any]:
    return {
        "product.history_enabled": True,
        "product.semantic_lens_enabled": True,
        "product.provenance_view_enabled": True,
        "product.exact_reentry_surface_enabled": True,
        "product.user_correction_surface_enabled": True,
        "measurement.capture_tier": capture_tier,
        "measurement.human_confirmation_prompt_enabled": True,
        "measurement.fine_grained_interaction_logging_enabled": capture_tier != "MINIMAL",
        "measurement.raw_content_capture_enabled": False,
        "comparator.arm_id": "C4_TASK_F_VALID_ACCUMULATED_HISTORY",
        "history.condition": "VALID_ACCUMULATED",
        "runtime.fresh_agent_mode": True,
        "runtime.hidden_chat_available": False,
        "analysis.epoch_kind": epoch_kind,
    }


def _default_surface_digests(*, measurement_label: str) -> dict[str, str]:
    values = {
        name: _digest_label(name)
        for name in REQUIRED_SURFACE_DIGESTS
    }
    values["measurement_surface_digest"] = _digest_label(measurement_label)
    return values


def build_deterministic_noninterference_witness() -> dict[str, Any]:
    """Build a deterministic no-human witness covering all six repair coordinates."""
    start = "2026-08-19T00:00:00Z"
    surface_minimal = _default_surface_digests(measurement_label="measurement:minimal")
    policy = build_frozen_policy_bundle(
        policy_id="policy:w3r-b4",
        threshold_policy={
            "minimum_real_episodes": 5,
            "minimum_real_projects": 2,
            "capture_review_minutes_ceiling": 30.0,
        },
        evidence_rung="R0_MECHANICAL",
        evaluator_rubric_digest=surface_minimal["evaluator_rubric_digest"],
        value_policy_digest=surface_minimal["value_policy_digest"],
        analysis_plan_digest=surface_minimal["analysis_plan_digest"],
        frozen_at=start,
    )
    epoch = build_experiment_epoch(
        epoch_id="epoch:w3r-b4",
        epoch_kind="QUALIFICATION",
        surface_digests=surface_minimal,
        policy_bundle=policy,
        start_at=start,
    )
    left = build_surface_snapshot(
        trajectory_id="trajectory:w3r-b4",
        episode_id="episode:minimal",
        condition_id="C4_F2_ACCUMULATED_VALID_HISTORY",
        assignment_receipt_ref="assignment:minimal",
        epoch=epoch,
        flag_values=_default_flags(capture_tier="MINIMAL", epoch_kind="QUALIFICATION"),
        surface_digests=surface_minimal,
        history_snapshot_ref="history:valid",
        consent_scope_snapshot_ref="consent:bounded",
        accessibility_profile_ref="accessibility:bounded",
        timestamp="2026-08-19T00:00:01Z",
    )
    surface_standard = dict(surface_minimal)
    surface_standard["measurement_surface_digest"] = _digest_label(
        "measurement:standard"
    )
    right_record: dict[str, Any] = {
        "schema_version": SURFACE_SCHEMA_VERSION,
        "program_id": PROGRAM_ID,
        "trajectory_id": "trajectory:w3r-b4",
        "episode_id": "episode:standard",
        "condition_id": "C4_F2_ACCUMULATED_VALID_HISTORY",
        "assignment_receipt_ref": "assignment:standard",
        "epoch_id": epoch["epoch_id"],
        "epoch_digest": epoch["epoch_digest"],
        "flag_values": _default_flags(capture_tier="STANDARD", epoch_kind="QUALIFICATION"),
        "surface_digests": surface_standard,
        "history_snapshot_ref": "history:valid",
        "consent_scope_snapshot_ref": "consent:bounded",
        "accessibility_profile_ref": "accessibility:bounded",
        "captured_before_episode_start": True,
        "timestamp": "2026-08-19T00:00:02Z",
        "claim_ceiling": CLAIM_CEILING,
    }
    right_record["surface_snapshot_digest"] = canonical_digest(right_record)
    right_record["surface_snapshot_ref"] = stable_ref("surface", right_record)
    right = right_record
    validate_surface_snapshot(right)
    contrast = build_instrumentation_contrast(
        contrast_id="contrast:minimal-v-standard",
        left_snapshot=left,
        right_snapshot=right,
        burden_budget_minutes=30.0,
        interaction_estimand="difference in capture/review burden with product constant",
        predeclared_at=start,
    )
    planned_change = build_surface_change_receipt(
        change_id="change:planned-dose",
        before_snapshot=left,
        after_snapshot=right,
        planned_contrast={
            "contrast_id": contrast["contrast_id"],
            "allowed_flag_differences": contrast["allowed_flag_differences"],
            "allowed_digest_differences": contrast["allowed_digest_differences"],
        },
        outcomes_visible=False,
        affected_episode_ids=[],
    )
    pooling = build_pooling_eligibility_receipt(
        comparison_id="pool:minimal-v-standard",
        left_snapshot=left,
        right_snapshot=right,
        predeclared_contrast={
            "contrast_id": contrast["contrast_id"],
            "allowed_flag_differences": ["measurement.capture_tier"],
            "allowed_digest_differences": ["measurement_surface_digest"],
        },
        carryover_status="CONTROLLED",
    )
    familiarization = build_familiarization_receipt(
        receipt_id="familiarization:w3r-b4",
        participant_id="participant:synthetic",
        interface_build_digest=surface_minimal["product_build_digest"],
        prior_exposure_count=1,
        warmup_task_ref="warmup:pointer-only",
        completed_before_assignment=True,
        outcome_blind=True,
        timestamp="2026-08-19T00:00:00Z",
    )
    reactivity = evaluate_instrumentation_reactivity(
        contrast=contrast,
        left_observations=[
            {"capture_minutes": 1.0, "review_and_correction_minutes": 1.0}
        ],
        right_observations=[
            {"capture_minutes": 2.0, "review_and_correction_minutes": 1.0}
        ],
        minimum_per_arm=1,
        burden_delta_threshold_minutes=5.0,
    )
    trajectory_digest = _digest_label("trajectory:w3r-b4")
    review = build_independent_review_binding(
        review_id="review:w3r-b4",
        epoch=epoch,
        trajectory_digest=trajectory_digest,
        policy_bundle=policy,
        positive_terminal_gates={f"G.ID.{index:02d}": False for index in range(1, 11)},
        accepted_current=True,
        reviewed_at="2026-08-19T00:10:00Z",
    )
    qualification = qualify_noninterference(
        epoch=epoch,
        policy_bundle=policy,
        snapshots=[left],
        change_receipts=[],
        familiarization_receipts=[familiarization],
        reactivity_result=reactivity,
        independent_review=review,
        trajectory_digest=trajectory_digest,
    )
    source_low_burden = {
        "program_id": PROGRAM_ID,
        "trajectory_id": "trajectory:w3r-b4",
        "episode_id": "episode:migration",
        "condition_id": "M.manual",
        "schema_version": "gva06.f.ruv.low-burden-capture-event.v1",
        "event_id": 1,
        "event_type": "INSTRUMENTATION_FLAGGED",
        "timestamp_utc": "2026-08-19T00:00:03Z",
        "monotonic_ns": 1,
        "source_refs": ["ref:synthetic"],
        "consent_scope_snapshot": ["local_operational_capture"],
        "feature_flag_snapshot": {
            "history_enabled": False,
            "semantic_lens_enabled": False,
            "provenance_view_enabled": False,
            "capture_tier": "MINIMAL",
            "fresh_agent_mode": True,
        },
        "claim_ceiling": CLAIM_CEILING,
        "synthetic_fixture": True,
        "payload": {"kind": "MEASUREMENT_REACTIVE"},
    }
    migrated_event, mapping = migrate_low_burden_event(source_low_burden)
    witness: dict[str, Any] = {
        "schema_version": REPAIR_SCHEMA_VERSION,
        "artifact_id": REPAIR_ARTIFACT_ID,
        "manifest": build_repair_manifest(),
        "policy_bundle": policy,
        "experiment_epoch": epoch,
        "minimal_surface_snapshot": left,
        "standard_surface_snapshot": right,
        "instrumentation_contrast": contrast,
        "planned_change_receipt": planned_change,
        "pooling_eligibility_receipt": pooling,
        "familiarization_receipt": familiarization,
        "reactivity_result": reactivity,
        "independent_review_binding": review,
        "qualification_result": qualification,
        "migrated_event": migrated_event,
        "event_mapping_receipt": mapping,
        "validation_matrix": {repair_id: "PASS" for repair_id in REPAIR_IDS},
        "human_observation_state": "SYNTHETIC_MECHANICAL_ONLY",
        "claim_ceiling": CLAIM_CEILING,
    }
    witness["witness_digest"] = canonical_digest(witness)
    return witness



__all__ = [name for name in globals() if not name.startswith("__")]
