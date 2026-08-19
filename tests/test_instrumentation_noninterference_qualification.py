from __future__ import annotations

from copy import deepcopy

from _noninterference_test_support import (
    InstrumentationNoninterferenceTestBase,
    ni,
)


class InstrumentationNoninterferenceRepairTests(InstrumentationNoninterferenceTestBase):
    def test_manifest_covers_all_six_repairs(self) -> None:
        manifest = ni.build_repair_manifest()
        self.assertEqual(set(manifest["repair_ids"]), set(ni.REPAIR_IDS))
        self.assertEqual(
            manifest["terminal"], "INSTRUMENTATION_NONINTERFERENCE_REPAIR_READY"
        )

    def test_independent_review_binds_exact_policy_and_epoch(self) -> None:
        trajectory_digest = ni._digest_label("trajectory:test")
        review = ni.build_independent_review_binding(
            review_id="review:test",
            epoch=self.epoch,
            trajectory_digest=trajectory_digest,
            policy_bundle=self.policy,
            positive_terminal_gates={"G.ID.01": False},
            accepted_current=True,
            reviewed_at="2026-08-19T00:10:00Z",
        )
        ni.validate_independent_review_binding(
            review,
            epoch=self.epoch,
            trajectory_digest=trajectory_digest,
            policy_bundle=self.policy,
        )
        with self.assertRaises(ni.NoninterferenceValidationError):
            ni.validate_independent_review_binding(
                review,
                epoch=self.epoch,
                trajectory_digest=ni._digest_label("other"),
                policy_bundle=self.policy,
            )

    def test_replay_overrides_are_forbidden(self) -> None:
        with self.assertRaises(ni.NoninterferenceValidationError):
            ni.qualification_policy_from_bundle(
                self.policy, replay_overrides={"evidence_rung": "R5_GENERALIZATION"}
            )

    def test_development_epoch_cannot_be_qualification_evidence(self) -> None:
        dev_flags = ni._default_flags(capture_tier="MINIMAL", epoch_kind="DEVELOPMENT")
        dev_epoch = ni.build_experiment_epoch(
            epoch_id="epoch:development",
            epoch_kind="DEVELOPMENT",
            surface_digests=self.digests,
            policy_bundle=self.policy,
            start_at=self.start,
        )
        dev_snapshot = ni.build_surface_snapshot(
            trajectory_id="trajectory:dev",
            episode_id="episode:dev",
            condition_id="C4_F2_ACCUMULATED_VALID_HISTORY",
            assignment_receipt_ref="assignment:dev",
            epoch=dev_epoch,
            flag_values=dev_flags,
            surface_digests=self.digests,
            history_snapshot_ref="history:dev",
            consent_scope_snapshot_ref="consent:dev",
            accessibility_profile_ref="accessibility:dev",
            timestamp="2026-08-19T00:00:01Z",
        )
        result = ni.qualify_noninterference(
            epoch=dev_epoch,
            policy_bundle=self.policy,
            snapshots=[dev_snapshot],
            change_receipts=[],
            familiarization_receipts=[],
            reactivity_result=None,
            independent_review={"some": "review"},
            trajectory_digest=ni._digest_label("trajectory:dev"),
        )
        self.assertEqual(
            result["terminal"], "DEVELOPMENT_QUALIFICATION_CONTAMINATION"
        )

    def test_low_burden_event_migration_is_loss_declared(self) -> None:
        source = {
            "program_id": ni.PROGRAM_ID,
            "trajectory_id": "trajectory:test",
            "episode_id": "episode:migrate",
            "condition_id": "M.manual",
            "schema_version": "gva06.f.ruv.low-burden-capture-event.v1",
            "event_id": 1,
            "event_type": "INSTRUMENTATION_FLAGGED",
            "timestamp_utc": self.start,
            "monotonic_ns": 1,
            "source_refs": ["ref:test"],
            "consent_scope_snapshot": ["local_operational_capture"],
            "feature_flag_snapshot": {
                "history_enabled": False,
                "semantic_lens_enabled": False,
                "provenance_view_enabled": False,
                "capture_tier": "MINIMAL",
                "fresh_agent_mode": True,
            },
            "claim_ceiling": ni.CLAIM_CEILING,
            "synthetic_fixture": True,
            "payload": {"kind": "MEASUREMENT_REACTIVE"},
        }
        migrated, receipt = ni.migrate_low_burden_event(source)
        self.assertEqual(
            migrated["event_type"], "MEASUREMENT_REACTIVITY_RECORDED"
        )
        self.assertEqual(
            migrated["condition_id"], "C0_MANUAL_ORDINARY_WORKFLOW"
        )
        self.assertTrue(receipt["safe_for_replay"])
        self.assertIn("declared_losses", receipt)

    def test_unknown_low_burden_event_mapping_fails_closed(self) -> None:
        source = {
            "program_id": ni.PROGRAM_ID,
            "trajectory_id": "trajectory:test",
            "episode_id": "episode:migrate",
            "condition_id": "UNASSIGNED",
            "event_id": 1,
            "event_type": "UNKNOWN_EVENT",
            "timestamp_utc": self.start,
            "monotonic_ns": 1,
            "source_refs": ["ref:test"],
            "consent_scope_snapshot": [],
            "feature_flag_snapshot": {},
            "claim_ceiling": ni.CLAIM_CEILING,
        }
        with self.assertRaises(ni.NoninterferenceValidationError):
            ni.migrate_low_burden_event(source)

    def test_deterministic_witness_is_byte_stable(self) -> None:
        left = ni.build_deterministic_noninterference_witness()
        right = ni.build_deterministic_noninterference_witness()
        self.assertEqual(ni.canonical_bytes(left), ni.canonical_bytes(right))
        self.assertEqual(
            left["qualification_result"]["terminal"], "INSTRUMENTATION_READY"
        )
        self.assertEqual(
            set(left["validation_matrix"].values()), {"PASS"}
        )

