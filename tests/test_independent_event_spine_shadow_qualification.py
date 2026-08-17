from copy import deepcopy
import json
from pathlib import Path
import unittest

from project_semantics.event_spine import (
    EventSpineError, append_event, derive_views, digest, make_event,
    migrate_v0_project_to_shadow, reduce_v0_compatibility_state,
    run_shadow_migration_witness, validate_event, validate_ledger,
)

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "event_spine_shadow" / "independent_qualification_bundle.json"


def accepted(fn):
    try:
        return True, repr(fn())[:240]
    except Exception as exc:
        return False, f"{type(exc).__name__}: {exc}"


def event(stream="project:p", kind="project.registered", payload=None, sequence=0,
          previous=None, happened="2026-08-17T00:00:00Z", recorded="2026-08-17T00:00:00Z"):
    return make_event(
        stream_id=stream, sequence=sequence, event_type=kind,
        payload=payload if payload is not None else {"project_ref": {"project_id": "p"}},
        happened_at=happened, recorded_at=recorded,
        actor_ref="actor:independent-redteam", previous_event_id=previous,
    )


def qualify(bundle):
    migration = migrate_v0_project_to_shadow(
        bundle["v0_project"], source_horizon_refs=bundle["source_horizon_refs"],
        migration_recorded_at=bundle["migration_recorded_at"], policy=bundle["policy"],
    )
    events = migration["events"]
    cases = []

    def add(case_id, family, expected_accept, fn, severity="control"):
        actual_accept, detail = accepted(fn)
        cases.append({
            "case_id": case_id, "family": family,
            "expected_accept": expected_accept, "actual_accept": actual_accept,
            "policy_match": expected_accept == actual_accept,
            "severity": severity if expected_accept != actual_accept else "none",
            "detail": detail,
        })

    add("ES01", "baseline_parity", True, lambda: run_shadow_migration_witness(bundle))

    def tamper():
        item = deepcopy(events[0]); item["payload"]["project_ref"]["project_id"] = "tampered"; validate_event(item)
    add("ES02", "event_chain_tamper", False, tamper)
    add("ES03", "reordered_replay", False, lambda: validate_ledger([events[1], events[0], *events[2:]]))
    add("ES04", "duplicate_event", False, lambda: validate_ledger([events[0], events[0]]))

    def schema_drift():
        item = deepcopy(events[0]); item["schema_version"] = "project-semantics.event-envelope.v0"; validate_event(item)
    add("ES05", "cross_version_schema", False, schema_drift)
    add("ES06", "reducer_determinism", True,
        lambda: digest(reduce_v0_compatibility_state(events)) == digest(reduce_v0_compatibility_state(deepcopy(events))))
    add("ES07", "prefix_rollback", True, lambda: reduce_v0_compatibility_state(events[:2]))
    add("ES08", "suffix_without_checkpoint", False, lambda: validate_ledger(events[1:]))

    def cross_stream():
        first = event(stream="project:a")
        second = event(stream="project:b", kind="projection.used", payload={"projection_ref": "projection:1"}, sequence=1, previous=first["event_id"])
        return validate_ledger([first, second])
    add("ES09", "cross_stream_injection", False, cross_stream, "high")
    add("ES10", "event_payload_schema", False, lambda: validate_ledger([event(payload={})]), "high")

    def resurrection():
        ledger = append_event(
            list(events), stream_id=events[0]["stream_id"], event_type="assertion.transitioned",
            payload={"transition": {
                "transition_id": "transition:invalid-resurrection",
                "assertion_ref": "contribution:1", "from_state": "unrelated_state",
                "to_state": "supported_bounded", "authority_actor_ref": "actor:unbound",
                "evidence_refs": [], "occurred_at": "2026-08-04T00:00:00Z",
                "reason": "red-team resurrection", "claim_delta": "re-promote revoked contribution"
            }}, happened_at="2026-08-04T00:00:00Z", recorded_at="2026-08-04T00:00:00Z",
            actor_ref="actor:unbound",
        )
        views = derive_views(ledger, source_horizon_refs=bundle["source_horizon_refs"], policy=bundle["policy"], expires_at=bundle["expires_at"])
        active = views["CurrentCapabilityProjection"]["payload"]["contributions"]
        if active:
            return {"resurrected": [x["contribution_id"] for x in active]}
        raise EventSpineError("invalid transition was rejected")
    add("ES11", "transition_authority_and_from_state", False, resurrection, "critical")

    add("ES12", "snapshot_expiry_enforcement", False,
        lambda: derive_views(events, source_horizon_refs=bundle["source_horizon_refs"], policy=bundle["policy"], expires_at="2020-01-01T00:00:00Z")["CurrentnessView"]["currentness"], "high")
    add("ES13", "source_horizon_continuity", False,
        lambda: derive_views(events, source_horizon_refs=["git:unrelated/repository@deadbeef"], policy=bundle["policy"], expires_at=bundle["expires_at"])["CurrentnessView"]["source_horizon_digest"], "high")

    def concurrent_forks():
        base = [event()]
        fork_a = append_event(base, stream_id="project:p", event_type="projection.used", payload={"projection_ref": "projection:a"}, happened_at="2026-08-17T00:01:00Z", recorded_at="2026-08-17T00:01:00Z", actor_ref="actor:a")
        fork_b = append_event(base, stream_id="project:p", event_type="projection.used", payload={"projection_ref": "projection:b"}, happened_at="2026-08-17T00:01:00Z", recorded_at="2026-08-17T00:01:00Z", actor_ref="actor:b")
        validate_ledger(fork_a); validate_ledger(fork_b)
        return {"fork_a": fork_a[-1]["event_id"], "fork_b": fork_b[-1]["event_id"], "shared_parent": base[-1]["event_id"]}
    add("ES14", "concurrent_writer_fork", False, concurrent_forks, "high")
    add("ES15", "recording_chronology", False,
        lambda: event(happened="2026-08-18T00:00:00Z", recorded="2026-08-17T00:00:00Z"), "medium")
    add("ES16", "unknown_event_type", False,
        lambda: make_event(stream_id="project:p", sequence=0, event_type="unknown", payload={}, happened_at="2026-08-17T00:00:00Z", recorded_at="2026-08-17T00:00:00Z", actor_ref="actor:test"))

    findings = [c for c in cases if not c["policy_match"]]
    return {
        "terminal": "PASS" if not findings else "KEEP_CURRENT_COMPATIBILITY_MODEL",
        "case_count": len(cases), "policy_matches": len(cases) - len(findings),
        "findings": len(findings),
        "critical_findings": sum(c["severity"] == "critical" for c in findings),
        "high_findings": sum(c["severity"] == "high" for c in findings),
        "first_zero": findings[0]["case_id"] if findings else None,
        "cases": cases,
    }


class IndependentEventSpineShadowQualificationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.result = qualify(json.loads(FIXTURE.read_text(encoding="utf-8")))
        cls.by_id = {c["case_id"]: c for c in cls.result["cases"]}

    def test_terminal(self): self.assertEqual(self.result["terminal"], "KEEP_CURRENT_COMPATIBILITY_MODEL")
    def test_case_count(self): self.assertEqual(self.result["case_count"], 16)
    def test_controls(self):
        for case_id in ("ES01", "ES02", "ES03", "ES04", "ES05", "ES06", "ES07", "ES08", "ES16"):
            self.assertTrue(self.by_id[case_id]["policy_match"], case_id)
    def test_cross_stream_gap(self): self.assertFalse(self.by_id["ES09"]["policy_match"])
    def test_payload_schema_gap(self): self.assertFalse(self.by_id["ES10"]["policy_match"])
    def test_transition_resurrection_critical(self):
        self.assertFalse(self.by_id["ES11"]["policy_match"]); self.assertEqual(self.by_id["ES11"]["severity"], "critical")
    def test_expiry_and_horizon_gaps(self):
        self.assertFalse(self.by_id["ES12"]["policy_match"]); self.assertFalse(self.by_id["ES13"]["policy_match"])
    def test_concurrency_gap(self): self.assertFalse(self.by_id["ES14"]["policy_match"])
    def test_chronology_gap(self): self.assertFalse(self.by_id["ES15"]["policy_match"])
    def test_counts(self):
        self.assertEqual((self.result["policy_matches"], self.result["findings"], self.result["critical_findings"], self.result["high_findings"], self.result["first_zero"]), (9, 7, 1, 5, "ES09"))


if __name__ == "__main__": unittest.main()
