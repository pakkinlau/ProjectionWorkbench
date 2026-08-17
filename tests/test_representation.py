from __future__ import annotations

import json
import unittest

from project_semantics.fixtures import build_fixture, fixture_json
from project_semantics.representation import (
    GlobalizationDisposition,
    InformationLossReport,
    LensMapping,
    MappingKind,
    attempt_glue,
)


class ProjectLensKernelTests(unittest.TestCase):
    def test_two_useful_incompatible_lenses_coexist(self) -> None:
        fixture = build_fixture()
        continuation = fixture["lenses"]["continuation"]
        contribution = fixture["lenses"]["contribution"]
        self.assertNotEqual(continuation["lens_id"], contribution["lens_id"])
        self.assertEqual(
            fixture["gluing"]["shared_core"]["disposition"],
            GlobalizationDisposition.SHARED_CORE_WITH_LOCAL_REFINEMENTS,
        )

    def test_failed_gluing_is_not_fabricated(self) -> None:
        fixture = build_fixture()
        failed = fixture["gluing"]["invalid_commit_author_claim"]
        self.assertEqual(failed["disposition"], GlobalizationDisposition.NO_SAFE_GLOBALIZATION)
        kinds = set(failed["obstruction"]["kinds"])
        self.assertIn("SEMANTIC_MISMATCH", kinds)
        self.assertIn("EVIDENCE_SCOPE_MISMATCH", kinds)
        self.assertIn("ATTRIBUTION_COLLAPSE", kinds)

    def test_missing_vocabulary_returns_grammar_insufficient(self) -> None:
        fixture = build_fixture()
        lens = fixture["lenses"]["continuation"]
        from project_semantics.representation import ProjectLens
        source = ProjectLens(**lens)
        mapping = LensMapping(
            mapping_id="mapping:missing-vocabulary",
            kind=MappingKind.TRANSLATION,
            source_lens_or_chart=source.lens_id,
            target_lens_or_chart=source.lens_id,
            correspondences={},
            preconditions=(),
            preserved_invariants=(),
            added_assumptions=(),
            information_loss=InformationLossReport(),
            provenance_continuity=True,
            attribution_continuity=True,
            privacy_compatibility=True,
            version_compatibility=True,
            claim_ceiling="none",
            vocabulary_available=False,
        )
        result = attempt_glue(source, source, mapping)
        self.assertEqual(result.disposition, GlobalizationDisposition.GRAMMAR_INSUFFICIENT)

    def test_fixture_is_deterministic(self) -> None:
        first = fixture_json()
        second = fixture_json()
        self.assertEqual(first, second)
        parsed = json.loads(first)
        self.assertTrue(parsed["fixture_digest"].startswith("sha256:"))

    def test_information_loss_is_separate_from_obstruction(self) -> None:
        fixture = build_fixture()
        shared = fixture["gluing"]["shared_core"]
        self.assertIsNone(shared["obstruction"])
        self.assertIsInstance(shared["information_loss"], dict)


if __name__ == "__main__":
    unittest.main()
