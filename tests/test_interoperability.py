from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest

from project_semantics.interoperability import (
    InteroperabilityError,
    export_bundle,
    import_bundle,
    migrate_v0_to_v1,
    revalidate_exchange,
)

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "schema_migration" / "v0_exchange_bundle.json"

class InteroperabilityTests(unittest.TestCase):
    def source(self):
        return json.loads(FIXTURE.read_text(encoding="utf-8"))

    def test_lossless_migration_and_revalidation(self):
        _, receipt = migrate_v0_to_v1(self.source())
        self.assertEqual(receipt["disposition"], "MIGRATED_LOSSLESSLY")
        self.assertEqual(receipt["revalidation"]["disposition"], "INTEROPERABLE")
        self.assertFalse(receipt["canonical_source_mutated"])

    def test_round_trip_is_deterministic(self):
        migrated, _ = migrate_v0_to_v1(self.source())
        with tempfile.TemporaryDirectory() as tmp:
            m1 = export_bundle(migrated, Path(tmp) / "a")
            m2 = export_bundle(migrated, Path(tmp) / "b")
            self.assertEqual(m1, m2)
            imported, receipt = import_bundle(Path(tmp) / "a")
            self.assertEqual(imported, migrated)
            self.assertEqual(receipt["integrity"], "PASS")

    def test_bad_connector_version_fails_closed(self):
        migrated, _ = migrate_v0_to_v1(self.source())
        connector = next(x["payload"] for x in migrated["records"] if x["kind"] == "ConnectorManifest")
        connector["accepted_target_versions"] = ["9.9.9"]
        result = revalidate_exchange(migrated)
        self.assertEqual(result["disposition"], "INCOMPATIBLE")

    def test_attestation_requires_bound_scope(self):
        migrated, _ = migrate_v0_to_v1(self.source())
        attestation = next(x["payload"] for x in migrated["records"] if x["kind"] == "Attestation")
        attestation["evidence_scope_refs"] = ["scope:missing"]
        self.assertEqual(revalidate_exchange(migrated)["disposition"], "INCOMPATIBLE")

    def test_promoted_without_evidence_downgrades_with_loss(self):
        source = self.source()
        c = next(x["payload"] for x in source["records"] if x["kind"] == "ContributionRecord")
        c["assertion_state"] = "human_confirmed"; c["evidence_refs"] = []
        migrated, receipt = migrate_v0_to_v1(source)
        migrated_c = next(x["payload"] for x in migrated["records"] if x["kind"] == "ContributionRecord")
        self.assertEqual(migrated_c["assertion_state"], "unresolved")
        self.assertEqual(receipt["disposition"], "MIGRATED_WITH_DECLARED_LOSS")

    def test_tampered_export_is_rejected(self):
        migrated, _ = migrate_v0_to_v1(self.source())
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); export_bundle(migrated, root)
            p = root / "exchange_bundle.json"; p.write_text(p.read_text() + " ")
            with self.assertRaises(InteroperabilityError): import_bundle(root)

    def test_unsupported_kind_rejected(self):
        source = self.source(); source["records"].append({"kind":"UnknownThing","payload":{"receipt_id":"x"}})
        with self.assertRaises(InteroperabilityError): migrate_v0_to_v1(source)

    def test_source_not_mutated(self):
        source = self.source(); before = deepcopy(source); migrate_v0_to_v1(source)
        self.assertEqual(source, before)

if __name__ == "__main__": unittest.main()
