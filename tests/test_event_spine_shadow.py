from copy import deepcopy
import json
from pathlib import Path
import unittest

from project_semantics.event_spine import (
    EventSpineError,
    DERIVED_VIEW_KINDS,
    append_event,
    digest,
    make_event,
    migrate_v0_project_to_shadow,
    run_shadow_migration_witness,
    validate_event,
    validate_ledger,
)

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "event_spine_shadow" / "bundle.json"


class EventSpineShadowTests(unittest.TestCase):
    def setUp(self):
        self.bundle = json.loads(FIXTURE.read_text(encoding="utf-8"))

    def test_stable_event_identity(self):
        args = dict(
            stream_id="project:p",
            sequence=0,
            event_type="project.registered",
            payload={"project_ref": {"project_id": "p"}},
            happened_at="2026-08-17T00:00:00Z",
            recorded_at="2026-08-17T00:00:00Z",
            actor_ref="actor:test",
        )
        self.assertEqual(make_event(**args), make_event(**args))

    def test_append_only_chain(self):
        first = append_event(
            [], stream_id="project:p", event_type="project.registered",
            payload={"project_ref": {"project_id": "p"}},
            happened_at="2026-08-17T00:00:00Z", recorded_at="2026-08-17T00:00:00Z",
            actor_ref="actor:test",
        )
        second = append_event(
            first, stream_id="project:p", event_type="projection.used",
            payload={"projection_ref": "projection:1"},
            happened_at="2026-08-17T00:01:00Z", recorded_at="2026-08-17T00:01:00Z",
            actor_ref="actor:test",
        )
        self.assertTrue(validate_ledger(second))
        self.assertEqual(second[1]["previous_event_id"], second[0]["event_id"])

    def test_tampered_payload_fails(self):
        event = make_event(
            stream_id="project:p", sequence=0, event_type="project.registered",
            payload={"project_ref": {"project_id": "p"}},
            happened_at="2026-08-17T00:00:00Z", recorded_at="2026-08-17T00:00:00Z",
            actor_ref="actor:test",
        )
        event["payload"]["project_ref"]["project_id"] = "tampered"
        with self.assertRaises(EventSpineError):
            validate_event(event)

    def test_migration_does_not_mutate_v0(self):
        before = deepcopy(self.bundle["v0_project"])
        migrate_v0_project_to_shadow(
            self.bundle["v0_project"],
            source_horizon_refs=self.bundle["source_horizon_refs"],
            migration_recorded_at=self.bundle["migration_recorded_at"],
            policy=self.bundle["policy"],
        )
        self.assertEqual(before, self.bundle["v0_project"])

    def test_v0_parity_is_supported(self):
        result = run_shadow_migration_witness(self.bundle)
        self.assertEqual(result["terminal"], "SHADOW_MIGRATION_PARITY_SUPPORTED")
        self.assertTrue(result["checks"]["parity"])
        self.assertTrue(all(result["migration"]["parity"]["fields"].values()))

    def test_all_materialized_views_bind_reproduction_state(self):
        result = run_shadow_migration_witness(self.bundle)
        self.assertEqual(set(result["views"]), DERIVED_VIEW_KINDS)
        for view in result["views"].values():
            self.assertFalse(view["canonical"])
            self.assertEqual(view["event_horizon_digest"], result["migration"]["event_horizon_digest"])
            self.assertEqual(view["source_horizon_digest"], result["migration"]["source_horizon_digest"])
            self.assertEqual(view["reproduction_receipt"]["output_digest"], digest(view["payload"]))

    def test_revoked_contribution_is_not_projected_as_current(self):
        result = run_shadow_migration_witness(self.bundle)
        current = result["views"]["CurrentCapabilityProjection"]["payload"]
        self.assertEqual(current["contributions"], [])
        currentness = result["views"]["CurrentnessView"]["payload"]
        self.assertEqual(currentness["assertion_states"]["contribution:1"], "revoked")

    def test_no_cutover_authority(self):
        result = run_shadow_migration_witness(self.bundle)
        self.assertFalse(result["migration"]["canonical_cutover_authorized"])
        self.assertEqual(result["migration"]["mode"], "shadow_compatible_no_cutover")

    def test_unknown_event_type_fails_closed(self):
        with self.assertRaises(EventSpineError):
            make_event(
                stream_id="project:p", sequence=0, event_type="unknown",
                payload={}, happened_at="2026-08-17T00:00:00Z",
                recorded_at="2026-08-17T00:00:00Z", actor_ref="actor:test",
            )


if __name__ == "__main__":
    unittest.main()
