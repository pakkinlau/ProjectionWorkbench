from __future__ import annotations

from copy import deepcopy
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from repeat_use_harness import (
    EVENT_SCHEMA_VERSION,
    EVENT_SCHEMA_VERSION_MINOR1,
    ReplayIntegrityError,
    SchemaVersionError,
    SourceCurrentnessError,
    StateInvalidatedError,
    StrictJSONError,
    build_cross_version_replay_operand,
    canonical_digest,
    expected_event_id,
    make_fixture,
    make_tombstone,
    migrate_record,
    replay,
    schema_envelope_receipt,
    strict_loads,
    validate_event,
    verify_event_log,
)


class SchemaCurrentnessReplayRepairTests(unittest.TestCase):
    def setUp(self) -> None: self.fixture = make_fixture()

    def test_legacy_envelopes_are_explicit_and_unknown_fields_are_receipted(self) -> None:
        epoch = deepcopy(self.fixture["epoch"]); epoch["additive"] = True
        receipt = schema_envelope_receipt(epoch, "epoch")
        self.assertTrue(receipt["legacy_schema_inferred"]); self.assertEqual(receipt["unknown_fields_policy"], "PRESERVE_WITH_RECEIPT"); self.assertIn("additive", receipt["unknown_fields"])

    def test_strict_json_rejects_duplicate_and_nonfinite(self) -> None:
        with self.assertRaises(StrictJSONError): strict_loads('{"a":1,"a":2}')
        with self.assertRaises(StrictJSONError): strict_loads('{"a":NaN}')

    def test_content_mutation_invalidates_direct_event_identity(self) -> None:
        event = deepcopy(self.fixture["events"][1]); event["payload"]["pointer_count"] = 999
        with self.assertRaises(ReplayIntegrityError): validate_event(event)

    def test_replay_normalizes_legacy_aliases_with_migration_receipts(self) -> None:
        events = deepcopy(self.fixture["events"]); events[-1]["event_id"] = "legacy:arbitrary-alias"
        result = replay(events,epoch=self.fixture["epoch"],assignment=self.fixture["assignment"],consent=self.fixture["consent"])
        receipts = result["schema_currentness_repair"]["integrity_receipt"]["migration_receipts"]
        self.assertTrue(any("legacy:arbitrary-alias" in receipt["identity_map"] for receipt in receipts))

    def test_duplicate_sequence_timestamp_and_identity_drift_fail_closed(self) -> None:
        duplicate = deepcopy(self.fixture["events"]); duplicate[2]["sequence"] = 2
        with self.assertRaises(ReplayIntegrityError): replay(duplicate, epoch=self.fixture["epoch"], assignment=self.fixture["assignment"], consent=self.fixture["consent"])
        backward = deepcopy(self.fixture["events"]); backward[2]["timestamp"] = "2026-08-19T07:00:00Z"
        with self.assertRaises(ReplayIntegrityError): replay(backward, epoch=self.fixture["epoch"], assignment=self.fixture["assignment"], consent=self.fixture["consent"])
        mixed = deepcopy(self.fixture["events"]); mixed[-1]["participant_id"] = "participant:other"
        with self.assertRaises(ReplayIntegrityError): replay(mixed, epoch=self.fixture["epoch"], assignment=self.fixture["assignment"], consent=self.fixture["consent"])

    def test_route_source_phase_consent_and_claim_bindings_fail_closed(self) -> None:
        epoch = deepcopy(self.fixture["epoch"]); epoch["policy_digest"] = "drift"
        with self.assertRaises(SourceCurrentnessError): replay(self.fixture["events"], epoch=epoch, assignment=self.fixture["assignment"], consent=self.fixture["consent"])
        events = deepcopy(self.fixture["events"]); events[0]["source_refs"] = ["git:drift"]
        with self.assertRaises(SourceCurrentnessError): replay(events, epoch=self.fixture["epoch"], assignment=self.fixture["assignment"], consent=self.fixture["consent"])
        events = deepcopy(self.fixture["events"]); events[0]["consent_scope_snapshot"]["artifact_export"] = True
        with self.assertRaises(SourceCurrentnessError): replay(events, epoch=self.fixture["epoch"], assignment=self.fixture["assignment"], consent=self.fixture["consent"])

    def test_human_judgment_requires_bound_consent_scope(self) -> None:
        event = deepcopy(self.fixture["events"][-1]); event.update({"sequence": 7, "event_type": "HUMAN_JUDGMENT_RECORDED", "timestamp": "2026-08-19T08:01:10Z"})
        event["payload"] = {"human_supplied": True, "fields": {"human_usefulness_judgment": True}}; event["event_id"] = expected_event_id(event)
        with self.assertRaises(SourceCurrentnessError): replay(self.fixture["events"] + [event], epoch=self.fixture["epoch"], assignment=self.fixture["assignment"], consent=self.fixture["consent"])

    def test_additive_minor_migration_is_receipted_and_unknown_major_rejected(self) -> None:
        source = deepcopy(self.fixture["events"][0]); source["schema_version"] = EVENT_SCHEMA_VERSION_MINOR1; source["new_field"] = {"preserved": True}; source["event_id"] = "legacy:minor"
        target, receipt = migrate_record(source, kind="event", target_schema_version=EVENT_SCHEMA_VERSION)
        self.assertTrue(receipt["source_unchanged"]); self.assertEqual(receipt["identity_map"]["legacy:minor"], target["event_id"])
        major = deepcopy(source); major["schema_version"] = "gva06.f.ruv.repeat-use-event.v2"
        with self.assertRaises(SchemaVersionError): schema_envelope_receipt(major, "event")

    def test_integrity_receipt_is_deterministic_and_content_bound(self) -> None:
        first = verify_event_log(self.fixture["events"], epoch=self.fixture["epoch"], assignment=self.fixture["assignment"], consent=self.fixture["consent"])
        second = verify_event_log(self.fixture["events"], epoch=self.fixture["epoch"], assignment=self.fixture["assignment"], consent=self.fixture["consent"])
        self.assertEqual(first["receipt"]["chain_root"], second["receipt"]["chain_root"]); self.assertEqual(len(first["receipt"]["chain_nodes"]), len(self.fixture["events"]))

    def test_tombstone_invalidates_replay_without_resurrection(self) -> None:
        tombstone = make_tombstone(target_kind="all-derived-state",target_id="all",reason="test deletion",effective_at="2026-08-19T08:02:00Z",source_receipt_ref="receipt:test")
        with self.assertRaises(StateInvalidatedError): replay(self.fixture["events"],epoch=self.fixture["epoch"],assignment=self.fixture["assignment"],consent=self.fixture["consent"],tombstones=[tombstone])

    def test_r6_operand_is_content_bound_but_not_independent_qualification(self) -> None:
        operand = build_cross_version_replay_operand(); self.assertTrue(operand["unknown_major_rejected"]); self.assertTrue(operand["source_unchanged"]); self.assertTrue(operand["independent_requalification_required"])
        digest = operand.pop("operand_digest"); self.assertEqual(digest, canonical_digest(operand))

    def test_branch_witness_closes_all_31_repair_cases(self) -> None:
        root = Path(__file__).resolve().parents[1]; script = root / "scripts" / "run_f_ruv_w3r_b7_schema_currentness_replay_repair.py"
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "result.json"; env = dict(os.environ); env["PYTHONPATH"] = str(root / "src")
            completed = subprocess.run([sys.executable, str(script), "--output", str(output)],cwd=root,env=env,text=True,capture_output=True,check=False)
            self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr); result = json.loads(output.read_text(encoding="utf-8"))
        self.assertEqual(result["terminal_disposition"], "SCHEMA_CURRENTNESS_REPLAY_REPAIR_PASS"); self.assertEqual(result["case_summary"], {"failed": 0, "passed": 31, "total": 31})
        self.assertTrue(all(result["repair_packages"].values())); self.assertFalse(result["independent_requalification_complete"]); self.assertFalse(result["wave4_open"])


if __name__ == "__main__": unittest.main()
