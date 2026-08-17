from pathlib import Path
import tempfile
import unittest

from project_semantics import ValidationError, init_project, load_json, record_contribution, record_episode
from project_semantics.contribution import (
    create_capability_projection,
    record_assertion_transition,
    record_attestation,
    record_capability_assertion,
    record_contribution_relation,
    record_evidence_scope,
    validate_attestation,
    validate_capability_assertion,
    validate_evidence_scope,
)

FIXTURE = (
    Path(__file__).resolve().parents[1]
    / "fixtures"
    / "contribution_hardening"
    / "bundle.json"
)


class ContributionHardeningTests(unittest.TestCase):
    def _project(self, root: Path):
        bundle = load_json(FIXTURE)
        init_project(root, project_id="p:test", title="Contribution hardening")
        record_episode(root, bundle["episode_a"])
        record_episode(root, bundle["episode_b"])
        record_contribution(root, bundle["contribution_a"])
        record_contribution(root, bundle["contribution_b"])
        record_contribution_relation(root, bundle["correction_relation"])
        record_evidence_scope(root, bundle["evidence_scope"])
        record_attestation(root, bundle["attestation"])
        return bundle

    def test_supported_capability_requires_all_gates(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            bundle = self._project(root)
            result = record_capability_assertion(root, bundle["capability_assertion"])
            self.assertEqual(result["capability_assertions"][0]["state"], "supported_bounded")
            projection = create_capability_projection(root, actor_ref="actor:human")
            self.assertEqual(len(projection["assertions"]), 1)

    def test_output_cannot_become_mastery(self):
        value = load_json(FIXTURE)["capability_assertion"]
        value["claim_level"] = "mastery"
        with self.assertRaises(ValidationError):
            validate_capability_assertion(value)

    def test_activity_volume_cannot_replace_recurrence_transfer(self):
        value = load_json(FIXTURE)["capability_assertion"]
        value["recurrence_count"] = 100
        value["transfer_contexts"] = []
        value["activity_refs"] = [f"activity:{i}" for i in range(100)]
        with self.assertRaises(ValidationError):
            validate_capability_assertion(value)

    def test_attestation_requires_identity_scope_and_nonclaims(self):
        value = load_json(FIXTURE)["attestation"]
        value["attestor_ref"] = ""
        with self.assertRaises(ValidationError):
            validate_attestation(value)

    def test_independent_assessment_requires_structured_scope(self):
        value = load_json(FIXTURE)["evidence_scope"]
        value["covered_actions"] = []
        with self.assertRaises(ValidationError):
            validate_evidence_scope(value)

    def test_revocation_requires_bound_transition(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            bundle = self._project(root)
            record_capability_assertion(root, bundle["capability_assertion"])
            transition = dict(bundle["revocation_transition"])
            transition["assertion_ref"] = "assertion:missing"
            with self.assertRaises(ValidationError):
                record_assertion_transition(root, transition)

    def test_valid_revocation_changes_assertion_state(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            bundle = self._project(root)
            record_capability_assertion(root, bundle["capability_assertion"])
            project = record_assertion_transition(root, bundle["revocation_transition"])
            self.assertEqual(project["capability_assertions"][0]["state"], "revoked")
            self.assertEqual(len(project["assertion_transitions"]), 1)


if __name__ == "__main__":
    unittest.main()
