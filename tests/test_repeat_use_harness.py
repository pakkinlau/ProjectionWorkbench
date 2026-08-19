from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest

from repeat_use_harness import (
    CLAIM_CEILING,
    EVENT_REQUIRED_METADATA,
    HUMAN_ONLY_FIELDS,
    REQUIRED_CONTROL_SURFACES,
    HarnessValidationError,
    append_event_file,
    build_harness_manifest,
    canonical_digest,
    delete_export,
    export_event_log,
    make_fixture,
    materialize_fixture,
    replay,
)


class RepeatUseHarnessTests(unittest.TestCase):
    def setUp(self) -> None:
        self.fixture = make_fixture()

    def _replay(self, **kwargs):
        return replay(
            self.fixture["events"],
            epoch=self.fixture["epoch"],
            assignment=self.fixture["assignment"],
            consent=self.fixture["consent"],
            **kwargs,
        )

    def test_manifest_closes_all_declared_control_surfaces(self) -> None:
        manifest = build_harness_manifest()
        self.assertEqual(
            set(manifest["required_control_surfaces"]), set(REQUIRED_CONTROL_SURFACES)
        )
        self.assertFalse(
            manifest["positive_terminal_guard"]["mechanical_or_synthetic_fixture_can_pass"]
        )
        self.assertFalse(manifest["source_horizon"]["prior_wave_bytes_embedded"])

    def test_fixture_is_deterministic_and_right_censored(self) -> None:
        first = self._replay()
        second = self._replay()
        self.assertEqual(first["replay_digest"], second["replay_digest"])
        self.assertEqual(first["trajectory"]["causal_terminal"], "RIGHT_CENSORED")
        self.assertFalse(first["trajectory"]["evidence_scope"]["human_value_supported"])

    def test_human_fields_are_never_imputed_from_mechanics(self) -> None:
        result = self._replay()
        episode = result["episodes"][0]
        for field in HUMAN_ONLY_FIELDS:
            self.assertIsNone(episode["human_only_fields"][field])
        self.assertIn("human_usefulness_judgment", episode["missingness"])
        self.assertEqual(episode["evidence_rung"], "R0_MECHANICAL")

    def test_events_carry_required_metadata_and_no_raw_content(self) -> None:
        forbidden = {
            "raw_content",
            "raw_source_bytes",
            "source_bytes",
            "message_body",
            "document_body",
            "private_raw_text",
        }

        def keys(value):
            if isinstance(value, dict):
                for key, child in value.items():
                    yield key
                    yield from keys(child)
            elif isinstance(value, list):
                for child in value:
                    yield from keys(child)

        for event in self.fixture["events"]:
            self.assertTrue(set(EVENT_REQUIRED_METADATA).issubset(event))
            self.assertTrue(forbidden.isdisjoint(set(keys(event))))

    def test_append_only_log_rejects_duplicate_and_flag_drift(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "events.jsonl"
            first = self.fixture["events"][0]
            append_event_file(
                path,
                first,
                epoch=self.fixture["epoch"],
                consent=self.fixture["consent"],
            )
            with self.assertRaises(HarnessValidationError):
                append_event_file(
                    path,
                    first,
                    epoch=self.fixture["epoch"],
                    consent=self.fixture["consent"],
                )
            drift = deepcopy(self.fixture["events"][1])
            drift["feature_flag_snapshot"]["history_enabled"] = True
            with self.assertRaises(HarnessValidationError):
                append_event_file(
                    path,
                    drift,
                    epoch=self.fixture["epoch"],
                    consent=self.fixture["consent"],
                )

    def test_raw_content_is_rejected(self) -> None:
        bad = deepcopy(self.fixture["events"][1])
        bad["payload"]["raw_content"] = "forbidden"
        bad["event_id"] = "event:raw-content-negative"
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(HarnessValidationError):
                append_event_file(
                    Path(tmp) / "events.jsonl",
                    bad,
                    epoch=self.fixture["epoch"],
                    consent=self.fixture["consent"],
                )

    def test_positive_terminal_remains_locked_at_r0(self) -> None:
        review = {
            "accepted_current": True,
            "positive_terminal_gates": {
                f"G.ID.{index:02d}": True for index in range(1, 11)
            },
        }
        result = self._replay(
            thresholds={
                "minimum_real_episodes": 1,
                "minimum_real_projects": 1,
                "evidence_rung": "R0_MECHANICAL",
            },
            independent_review=review,
        )
        self.assertNotEqual(
            result["trajectory"]["causal_terminal"],
            "REPEAT_USE_VALUE_SUPPORTED_BOUNDED",
        )

    def test_consent_scope_absence_fails_closed(self) -> None:
        consent = deepcopy(self.fixture["consent"])
        consent["scopes"]["local_operational_capture"] = False
        result = replay(
            self.fixture["events"],
            epoch=self.fixture["epoch"],
            assignment=self.fixture["assignment"],
            consent=consent,
        )
        self.assertEqual(result["trajectory"]["causal_terminal"], "HARM_OR_TRUST_BREACH")
        self.assertEqual(
            result["trajectory"]["instrumentation_terminal"], "CONSENT_SCOPE_ABSENT"
        )

    def test_accessibility_blocked_is_not_negative_value(self) -> None:
        events = deepcopy(self.fixture["events"])
        event = deepcopy(events[-1])
        event["event_type"] = "ACCESSIBILITY_BLOCKED"
        event["sequence"] = 7
        event["timestamp"] = "2026-08-19T08:01:01Z"
        event["payload"] = {"barrier": "fixture-only"}
        event["event_id"] = "event:accessibility-blocked"
        events.append(event)
        result = replay(
            events,
            epoch=self.fixture["epoch"],
            assignment=self.fixture["assignment"],
            consent=self.fixture["consent"],
        )
        self.assertEqual(
            result["trajectory"]["instrumentation_terminal"], "ACCESSIBILITY_BLOCKED"
        )
        self.assertNotEqual(result["trajectory"]["causal_terminal"], "NEGATIVE_NET_VALUE")

    def test_export_and_delete_require_explicit_receipts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            destination = Path(tmp) / "export.jsonl"
            with self.assertRaises(HarnessValidationError):
                export_event_log(
                    self.fixture["events"],
                    destination,
                    consent=self.fixture["consent"],
                )
            consent = deepcopy(self.fixture["consent"])
            consent["scopes"]["artifact_export"] = True
            receipt = export_event_log(
                self.fixture["events"], destination, consent=consent
            )
            self.assertFalse(receipt["raw_content_included"])
            deletion = delete_export(
                destination, consent=consent, explicit_confirmation=True
            )
            self.assertTrue(deletion["deleted"])
            self.assertFalse(destination.exists())

    def test_materialized_fixture_is_reproducible(self) -> None:
        with tempfile.TemporaryDirectory() as first_tmp, tempfile.TemporaryDirectory() as second_tmp:
            first = materialize_fixture(first_tmp)
            second = materialize_fixture(second_tmp)
            self.assertTrue(first["passed"])
            self.assertEqual(first["fixture_digest"], second["fixture_digest"])
            self.assertEqual(first["claim_ceiling"], CLAIM_CEILING)

    def test_manifest_digest_is_content_bound(self) -> None:
        manifest = build_harness_manifest()
        digest = manifest.pop("artifact_digest")
        self.assertEqual(digest, canonical_digest(manifest))


if __name__ == "__main__":
    unittest.main()
