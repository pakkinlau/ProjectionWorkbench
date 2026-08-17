from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from project_semantics.privacy import (
    PrivacyValidationError,
    create_projection,
    export_bundle,
    import_bundle,
    make_external_reference,
    transition_projection,
    validate_external_reference,
    validate_json_limits,
    verify_bundle,
)


class ProjectionPrivacyPortabilityTests(unittest.TestCase):
    def setUp(self) -> None:
        self.project = {
            "schema_version": "project-semantics.kernel.v0",
            "project_ref": {
                "project_id": "demo",
                "title": "Demo",
                "owner_or_custodian": "private-owner",
                "private_note": "never disclose",
            },
            "source_links": [
                {
                    "link_id": "source-1",
                    "kind": "git",
                    "locator": "external://repo",
                    "content_identity": "sha256:abc",
                    "credentials": "secret-token",
                }
            ],
            "episodes": [
                {
                    "episode_id": "episode-1",
                    "outcome_state": "DONE",
                    "activities": [{"kind": "review", "private_reason": "sealed"}],
                }
            ],
            "contributions": [{"contribution_id": "c1", "scope": "public", "secret": "hidden"}],
        }
        self.policy = {
            "policy_id": "public-minimal-v1",
            "audience": "public",
            "allowlist": {
                "project_ref": {"project_id": True, "title": True},
                "source_links": {"*": {"link_id": True, "kind": True, "content_identity": True}},
                "episodes": {"*": {"episode_id": True, "outcome_state": True}},
            },
            "redactions": {},
            "subject_approval_requirement": "REQUIRED",
            "currentness_policy": "EXPLICIT_REFRESH",
            "expires_at": "2026-09-01T00:00:00Z",
        }

    def test_recursive_allowlist_blocks_nested_private_fields(self) -> None:
        projection = create_projection(self.project, self.policy, created_at="2026-08-17T00:00:00Z")
        text = json.dumps(projection, sort_keys=True)
        self.assertNotIn("private-owner", text)
        self.assertNotIn("never disclose", text)
        self.assertNotIn("secret-token", text)
        self.assertNotIn("sealed", text)
        self.assertNotIn("hidden", text)
        self.assertEqual(projection["visible"]["project_ref"], {"project_id": "demo", "title": "Demo"})
        self.assertFalse(projection["canonical_history_mutated"])

    def test_composite_true_allow_is_rejected(self) -> None:
        policy = dict(self.policy)
        policy["allowlist"] = {"project_ref": True}
        with self.assertRaises(PrivacyValidationError):
            create_projection(self.project, policy)

    def test_external_reference_modes_are_explicit(self) -> None:
        immutable = make_external_reference(locator="external://artifact", sha256="a" * 64)
        mutable = make_external_reference(
            locator="https://example.invalid/current",
            observed_at="2026-08-17T00:00:00Z",
            revision_token="etag:1",
            refresh_policy="RECHECK_BEFORE_USE",
        )
        validate_external_reference(immutable)
        validate_external_reference(mutable)
        broken = dict(mutable)
        broken["mutable_currentness"] = None
        with self.assertRaises(PrivacyValidationError):
            validate_external_reference(broken)

    def test_projection_revocation_and_tombstone_do_not_mutate_source(self) -> None:
        projection = create_projection(self.project, self.policy, created_at="2026-08-17T00:00:00Z")
        original = json.loads(json.dumps(projection))
        revoked = transition_projection(
            projection,
            action="REVOKE",
            actor="owner",
            reason="withdrawn",
            at="2026-08-18T00:00:00Z",
        )
        tombstone = transition_projection(
            revoked,
            action="TOMBSTONE",
            actor="owner",
            reason="remove public payload",
            at="2026-08-19T00:00:00Z",
        )
        self.assertEqual(projection, original)
        self.assertEqual(revoked["lifecycle"]["state"], "REVOKED")
        self.assertEqual(tombstone["lifecycle"]["state"], "TOMBSTONED")
        self.assertEqual(tombstone["visible"], {})
        self.assertFalse(tombstone["canonical_history_mutated"])

    def test_export_import_clean_room_round_trip(self) -> None:
        projection = create_projection(self.project, self.policy, created_at="2026-08-17T00:00:00Z")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest = export_bundle(
                project=self.project,
                projections=[projection],
                destination=root / "export",
                created_at="2026-08-17T00:00:00Z",
            )
            verification = verify_bundle(root / "export")
            receipt = import_bundle(root / "export", root / "imported")
            self.assertEqual(manifest["bundle_digest"], verification["bundle_digest"])
            self.assertEqual(receipt["source_bundle_digest"], receipt["imported_bundle_digest"])
            self.assertTrue(receipt["clean_room"])

    def test_tampered_bundle_fails_closed(self) -> None:
        projection = create_projection(self.project, self.policy, created_at="2026-08-17T00:00:00Z")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            export_bundle(project=self.project, projections=[projection], destination=root / "export")
            project_file = root / "export" / "payload" / "project.json"
            project_file.write_text("{}\n", encoding="utf-8")
            with self.assertRaises(PrivacyValidationError):
                verify_bundle(root / "export")

    def test_malicious_depth_is_rejected(self) -> None:
        nested = value = {}
        for _ in range(20):
            value["next"] = {}
            value = value["next"]
        with self.assertRaises(PrivacyValidationError):
            validate_json_limits(nested, max_depth=8)


if __name__ == "__main__":
    unittest.main()
