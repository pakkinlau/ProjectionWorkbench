from __future__ import annotations

from copy import deepcopy

from _noninterference_test_support import (
    InstrumentationNoninterferenceTestBase,
    ni,
)


class InstrumentationNoninterferenceRepairTests(InstrumentationNoninterferenceTestBase):
    def test_unplanned_product_change_opens_new_epoch(self) -> None:
        changed = self._variant_snapshot(product_surface_label="product:changed")
        receipt = ni.build_surface_change_receipt(
            change_id="change:product",
            before_snapshot=self.snapshot,
            after_snapshot=changed,
            planned_contrast=None,
            outcomes_visible=True,
            affected_episode_ids=["episode:test"],
        )
        self.assertTrue(receipt["new_epoch_required"])
        self.assertEqual(receipt["active_episode_disposition"], "RIGHT_CENSORED")
        closed, boundary = ni.close_epoch_for_change(
            self.epoch, receipt, closed_at="2026-08-19T00:05:00Z"
        )
        self.assertEqual(closed["state"], "CLOSED")
        self.assertTrue(boundary["next_epoch_required"])

    def test_planned_measurement_contrast_does_not_count_as_leakage(self) -> None:
        standard = self._variant_snapshot(
            capture_tier="STANDARD", measurement_label="measurement:standard"
        )
        contrast = ni.build_instrumentation_contrast(
            contrast_id="contrast:test",
            left_snapshot=self.snapshot,
            right_snapshot=standard,
            burden_budget_minutes=30.0,
            interaction_estimand="burden delta",
            predeclared_at=self.start,
        )
        planned = {
            "contrast_id": contrast["contrast_id"],
            "allowed_flag_differences": contrast["allowed_flag_differences"],
            "allowed_digest_differences": contrast["allowed_digest_differences"],
        }
        receipt = ni.build_surface_change_receipt(
            change_id="change:planned",
            before_snapshot=self.snapshot,
            after_snapshot=standard,
            planned_contrast=planned,
            outcomes_visible=False,
            affected_episode_ids=[],
        )
        self.assertFalse(receipt["new_epoch_required"])
        self.assertEqual(receipt["materiality"], "EXACT_PREDECLARED_CONTRAST")

    def test_pooling_requires_exact_contrast_and_controlled_carryover(self) -> None:
        standard = self._variant_snapshot(
            capture_tier="STANDARD", measurement_label="measurement:standard"
        )
        contrast = ni.build_instrumentation_contrast(
            contrast_id="contrast:test",
            left_snapshot=self.snapshot,
            right_snapshot=standard,
            burden_budget_minutes=30.0,
            interaction_estimand="burden delta",
            predeclared_at=self.start,
        )
        planned = {
            "contrast_id": contrast["contrast_id"],
            "allowed_flag_differences": contrast["allowed_flag_differences"],
            "allowed_digest_differences": contrast["allowed_digest_differences"],
        }
        allowed = ni.build_pooling_eligibility_receipt(
            comparison_id="pool:test",
            left_snapshot=self.snapshot,
            right_snapshot=standard,
            predeclared_contrast=planned,
            carryover_status="CONTROLLED",
        )
        self.assertEqual(allowed["pooling_disposition"], "POOL_ALLOWED")
        blocked = ni.build_pooling_eligibility_receipt(
            comparison_id="pool:blocked",
            left_snapshot=self.snapshot,
            right_snapshot=standard,
            predeclared_contrast=planned,
            carryover_status="UNCONTROLLED",
        )
        self.assertEqual(blocked["pooling_disposition"], "NON_IDENTIFIABLE")

    def test_familiarization_is_prospective_and_outcome_blind(self) -> None:
        receipt = ni.build_familiarization_receipt(
            receipt_id="fam:test",
            participant_id="participant:test",
            interface_build_digest=self.digests["product_build_digest"],
            prior_exposure_count=0,
            warmup_task_ref="warmup:test",
            completed_before_assignment=True,
            outcome_blind=True,
            timestamp=self.start,
        )
        ni.validate_familiarization_receipt(receipt)
        with self.assertRaises(ni.NoninterferenceValidationError):
            ni.build_familiarization_receipt(
                receipt_id="fam:bad",
                participant_id="participant:test",
                interface_build_digest=self.digests["product_build_digest"],
                prior_exposure_count=0,
                warmup_task_ref="warmup:test",
                completed_before_assignment=False,
                outcome_blind=True,
                timestamp=self.start,
            )

    def test_reactivity_contrast_requires_product_constant(self) -> None:
        standard = self._variant_snapshot(
            capture_tier="STANDARD", measurement_label="measurement:standard"
        )
        contrast = ni.build_instrumentation_contrast(
            contrast_id="contrast:test",
            left_snapshot=self.snapshot,
            right_snapshot=standard,
            burden_budget_minutes=30.0,
            interaction_estimand="burden delta",
            predeclared_at=self.start,
        )
        self.assertTrue(contrast["product_constant"])
        self.assertTrue(contrast["all_nonmeasurement_planes_constant"])

    def test_reactivity_result_is_right_censored_without_observations(self) -> None:
        standard = self._variant_snapshot(
            capture_tier="STANDARD", measurement_label="measurement:standard"
        )
        contrast = ni.build_instrumentation_contrast(
            contrast_id="contrast:test",
            left_snapshot=self.snapshot,
            right_snapshot=standard,
            burden_budget_minutes=30.0,
            interaction_estimand="burden delta",
            predeclared_at=self.start,
        )
        result = ni.evaluate_instrumentation_reactivity(
            contrast=contrast, left_observations=[], right_observations=[]
        )
        self.assertEqual(result["terminal"], "RIGHT_CENSORED")

    def test_reactivity_result_detects_burden_delta(self) -> None:
        standard = self._variant_snapshot(
            capture_tier="STANDARD", measurement_label="measurement:standard"
        )
        contrast = ni.build_instrumentation_contrast(
            contrast_id="contrast:test",
            left_snapshot=self.snapshot,
            right_snapshot=standard,
            burden_budget_minutes=30.0,
            interaction_estimand="burden delta",
            predeclared_at=self.start,
        )
        result = ni.evaluate_instrumentation_reactivity(
            contrast=contrast,
            left_observations=[{"capture_minutes": 1, "review_and_correction_minutes": 0}],
            right_observations=[{"capture_minutes": 10, "review_and_correction_minutes": 0}],
            burden_delta_threshold_minutes=5,
        )
        self.assertEqual(result["terminal"], "MEASUREMENT_REACTIVE")

    def test_reactivity_result_can_pass_at_bounded_mechanical_ceiling(self) -> None:
        standard = self._variant_snapshot(
            capture_tier="STANDARD", measurement_label="measurement:standard"
        )
        contrast = ni.build_instrumentation_contrast(
            contrast_id="contrast:test",
            left_snapshot=self.snapshot,
            right_snapshot=standard,
            burden_budget_minutes=30.0,
            interaction_estimand="burden delta",
            predeclared_at=self.start,
        )
        result = ni.evaluate_instrumentation_reactivity(
            contrast=contrast,
            left_observations=[{"capture_minutes": 1, "review_and_correction_minutes": 1}],
            right_observations=[{"capture_minutes": 2, "review_and_correction_minutes": 1}],
            burden_delta_threshold_minutes=5,
        )
        self.assertEqual(result["terminal"], "NO_REACTIVITY_OBSERVED_AT_BOUND")
        self.assertFalse(result["human_value_supported"])

