from __future__ import annotations

from copy import deepcopy
import importlib
import unittest

ni = importlib.import_module("repeat_use_harness.noninterference")


class InstrumentationNoninterferenceTestBase(unittest.TestCase):
    def setUp(self) -> None:
        self.start = "2026-08-19T00:00:00Z"
        self.digests = ni._default_surface_digests(measurement_label="measurement:minimal")
        self.policy = ni.build_frozen_policy_bundle(
            policy_id="policy:test",
            threshold_policy={
                "minimum_real_episodes": 5,
                "minimum_real_projects": 2,
                "capture_review_minutes_ceiling": 30.0,
            },
            evidence_rung="R0_MECHANICAL",
            evaluator_rubric_digest=self.digests["evaluator_rubric_digest"],
            value_policy_digest=self.digests["value_policy_digest"],
            analysis_plan_digest=self.digests["analysis_plan_digest"],
            frozen_at=self.start,
        )
        self.epoch = ni.build_experiment_epoch(
            epoch_id="epoch:test",
            epoch_kind="QUALIFICATION",
            surface_digests=self.digests,
            policy_bundle=self.policy,
            start_at=self.start,
        )
        self.flags = ni._default_flags(
            capture_tier="MINIMAL", epoch_kind="QUALIFICATION"
        )
        self.snapshot = ni.build_surface_snapshot(
            trajectory_id="trajectory:test",
            episode_id="episode:test",
            condition_id="C4_F2_ACCUMULATED_VALID_HISTORY",
            assignment_receipt_ref="assignment:test",
            epoch=self.epoch,
            flag_values=self.flags,
            surface_digests=self.digests,
            history_snapshot_ref="history:test",
            consent_scope_snapshot_ref="consent:test",
            accessibility_profile_ref="accessibility:test",
            timestamp="2026-08-19T00:00:01Z",
        )

    def _variant_snapshot(
        self,
        *,
        capture_tier: str = "MINIMAL",
        product_surface_label: str = "product_surface_digest",
        measurement_label: str = "measurement:minimal",
    ) -> dict:
        flags = ni._default_flags(
            capture_tier=capture_tier, epoch_kind="QUALIFICATION"
        )
        digests = dict(self.digests)
        digests["product_surface_digest"] = ni._digest_label(product_surface_label)
        digests["measurement_surface_digest"] = ni._digest_label(measurement_label)
        record = {
            "schema_version": ni.SURFACE_SCHEMA_VERSION,
            "program_id": ni.PROGRAM_ID,
            "trajectory_id": "trajectory:test",
            "episode_id": f"episode:{capture_tier.lower()}",
            "condition_id": "C4_F2_ACCUMULATED_VALID_HISTORY",
            "assignment_receipt_ref": f"assignment:{capture_tier.lower()}",
            "epoch_id": self.epoch["epoch_id"],
            "epoch_digest": self.epoch["epoch_digest"],
            "flag_values": flags,
            "surface_digests": digests,
            "history_snapshot_ref": "history:test",
            "consent_scope_snapshot_ref": "consent:test",
            "accessibility_profile_ref": "accessibility:test",
            "captured_before_episode_start": True,
            "timestamp": "2026-08-19T00:00:02Z",
            "claim_ceiling": ni.CLAIM_CEILING,
        }
        record["surface_snapshot_digest"] = ni.canonical_digest(record)
        record["surface_snapshot_ref"] = ni.stable_ref("surface", record)
        ni.validate_surface_snapshot(record)
        return record

