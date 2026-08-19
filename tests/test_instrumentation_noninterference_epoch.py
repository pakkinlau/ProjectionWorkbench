from __future__ import annotations

from copy import deepcopy

from _noninterference_test_support import (
    InstrumentationNoninterferenceTestBase,
    ni,
)


class InstrumentationNoninterferenceRepairTests(InstrumentationNoninterferenceTestBase):
    def test_policy_bundle_is_content_bound(self) -> None:
        ni.validate_frozen_policy_bundle(self.policy)
        tampered = deepcopy(self.policy)
        tampered["threshold_policy"]["minimum_real_episodes"] = 1
        with self.assertRaises(ni.NoninterferenceValidationError):
            ni.validate_frozen_policy_bundle(tampered)

    def test_policy_must_freeze_before_outcomes(self) -> None:
        with self.assertRaises(ni.NoninterferenceValidationError):
            ni.build_frozen_policy_bundle(
                policy_id="policy:bad",
                threshold_policy={"x": 1},
                evidence_rung="R0_MECHANICAL",
                evaluator_rubric_digest=self.digests["evaluator_rubric_digest"],
                value_policy_digest=self.digests["value_policy_digest"],
                analysis_plan_digest=self.digests["analysis_plan_digest"],
                frozen_at=self.start,
                frozen_before_outcomes=False,
            )

    def test_epoch_binds_all_surface_digests(self) -> None:
        ni.validate_experiment_epoch(self.epoch, policy_bundle=self.policy)
        for name in ni.REQUIRED_SURFACE_DIGESTS:
            self.assertIn(name, self.epoch)

    def test_epoch_rejects_policy_mismatch(self) -> None:
        bad_policy = deepcopy(self.policy)
        bad_policy["policy_id"] = "policy:tampered"
        bad_policy["policy_bundle_digest"] = ni.canonical_digest(
            {k: v for k, v in bad_policy.items() if k != "policy_bundle_digest"}
        )
        with self.assertRaises(ni.NoninterferenceValidationError):
            ni.validate_experiment_epoch(self.epoch, policy_bundle=bad_policy)

    def test_full_flag_registry_is_required(self) -> None:
        bad = dict(self.flags)
        bad.pop("product.user_correction_surface_enabled")
        with self.assertRaises(ni.NoninterferenceValidationError):
            ni.validate_flag_values(bad)

    def test_unknown_flag_is_rejected(self) -> None:
        bad = dict(self.flags)
        bad["product.unknown"] = True
        with self.assertRaises(ni.NoninterferenceValidationError):
            ni.validate_flag_values(bad)

    def test_snapshot_is_prospective_and_epoch_bound(self) -> None:
        ni.validate_surface_snapshot(self.snapshot, epoch=self.epoch)
        self.assertTrue(self.snapshot["captured_before_episode_start"])

    def test_snapshot_rejects_epoch_kind_drift(self) -> None:
        bad_flags = dict(self.flags)
        bad_flags["analysis.epoch_kind"] = "DEVELOPMENT"
        with self.assertRaises(ni.NoninterferenceValidationError):
            ni.build_surface_snapshot(
                trajectory_id="trajectory:test",
                episode_id="episode:bad",
                condition_id="C4_F2_ACCUMULATED_VALID_HISTORY",
                assignment_receipt_ref="assignment:bad",
                epoch=self.epoch,
                flag_values=bad_flags,
                surface_digests=self.digests,
                history_snapshot_ref="history:test",
                consent_scope_snapshot_ref="consent:test",
                accessibility_profile_ref="accessibility:test",
                timestamp="2026-08-19T00:00:01Z",
            )

    def test_event_binding_is_content_bound(self) -> None:
        event = {
            "trajectory_id": "trajectory:test",
            "episode_id": "episode:test",
            "condition_id": "C4_F2_ACCUMULATED_VALID_HISTORY",
            "event_type": "EPISODE_STARTED",
        }
        bound = ni.bind_event_to_surface(
            event,
            epoch=self.epoch,
            snapshot=self.snapshot,
            policy_bundle=self.policy,
        )
        ni.validate_bound_event(
            bound,
            epoch=self.epoch,
            snapshot=self.snapshot,
            policy_bundle=self.policy,
        )
        tampered = deepcopy(bound)
        tampered["surface_flag_snapshot"]["product.history_enabled"] = False
        with self.assertRaises(ni.NoninterferenceValidationError):
            ni.validate_bound_event(
                tampered,
                epoch=self.epoch,
                snapshot=self.snapshot,
                policy_bundle=self.policy,
            )

