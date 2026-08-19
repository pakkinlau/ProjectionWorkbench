#!/usr/bin/env python3
"""Execute the F.RUV.W3R.B7 local repair witness."""
from __future__ import annotations

import argparse
from copy import deepcopy
import json
from pathlib import Path
import tempfile
from typing import Any, Callable

from repeat_use_harness import (
    CLAIM_CEILING,
    EVENT_SCHEMA_VERSION,
    EVENT_SCHEMA_VERSION_MINOR1,
    HarnessValidationError,
    ReplayIntegrityError,
    SchemaVersionError,
    SourceCurrentnessError,
    StateInvalidatedError,
    StrictJSONError,
    StrictJSONLimits,
    build_cross_version_replay_operand,
    canonical_digest,
    delete_export,
    expected_event_id,
    export_event_log,
    make_fixture,
    make_tombstone,
    map_terminal,
    migrate_record,
    replay,
    rollback_migration,
    schema_envelope_receipt,
    strict_loads,
    validate_assignment,
    validate_consent,
    validate_epoch,
    validate_event,
    verify_event_log,
)

PROGRAM_ID = "GVA06.F.repeat-use-value-discovery.v2"
BRANCH_ID = "F.RUV.W3R.B7"
STEWARDSTACK_COMMIT = "a644409f293609ec2e6f0cb230ba0799d455ec1d"
ROUTE_LAUNCH_DIGEST = "a4848d67212416935e25d8f4fc09b3aeee1b62b4c761c5cfd7055eb0e4b26baa"
BASE_COMMIT = "510c60889d9ed7d3014cb6d9d6607ef7305c141c"
CLAIM = (
    "Local schema/currentness/migration/tamper/replay repair and deterministic R6 "
    "operand preparation only. No independent Wave-3 qualification, human repeat-use "
    "value, retention, product direction, release, merge, cutover, or owner admission."
)


def _passes(call: Callable[[], Any]) -> tuple[bool, str]:
    try:
        call()
        return True, "PASS"
    except Exception as exc:
        return False, f"{type(exc).__name__}: {exc}"


def _rejects(call: Callable[[], Any], expected: type[BaseException] = HarnessValidationError) -> tuple[bool, str]:
    try:
        call()
    except expected as exc:
        return True, f"REJECTED:{type(exc).__name__}"
    except Exception as exc:
        return False, f"WRONG_EXCEPTION:{type(exc).__name__}:{exc}"
    return False, "FAIL_OPEN"


def _human_event(fixture: dict[str, Any]) -> dict[str, Any]:
    event = deepcopy(fixture["events"][-1])
    event["sequence"] = 7
    event["event_type"] = "HUMAN_JUDGMENT_RECORDED"
    event["timestamp"] = "2026-08-19T08:01:10Z"
    event["payload"] = {"human_supplied": True,"fields": {"human_usefulness_judgment": True}}
    event["event_id"] = expected_event_id(event)
    return event


def run() -> dict[str, Any]:
    fixture = make_fixture()
    cases: dict[str, dict[str, Any]] = {}

    def record(case_id: str, result: tuple[bool, str], repair: str) -> None:
        cases[case_id] = {"passed": result[0], "observation": result[1], "repair": repair}

    record("SMT-A03", _passes(lambda: schema_envelope_receipt(fixture["epoch"], "epoch")), "R1")
    record("SMT-A04", _passes(lambda: schema_envelope_receipt(fixture["assignment"], "assignment")), "R1")
    record("SMT-A05", _passes(lambda: schema_envelope_receipt(fixture["consent"], "consent")), "R1")

    drift_epoch = deepcopy(fixture["epoch"]); drift_epoch["policy_digest"] = "drift"
    record("SMT-A06", _rejects(lambda: validate_epoch(drift_epoch), SourceCurrentnessError), "R4")
    source_events = deepcopy(fixture["events"]); source_events[0]["source_refs"] = ["git:drift"]
    record("SMT-A07", _rejects(lambda: replay(source_events, epoch=fixture["epoch"], assignment=fixture["assignment"], consent=fixture["consent"]), SourceCurrentnessError), "R4")
    phase_assignment = deepcopy(fixture["assignment"]); phase_assignment["version_phase"] = "phase:drift"
    record("SMT-A08", _rejects(lambda: replay(fixture["events"], epoch=fixture["epoch"], assignment=phase_assignment, consent=fixture["consent"]), SourceCurrentnessError), "R4")

    record("SMT-B02", _rejects(lambda: strict_loads('{"x":NaN}'), StrictJSONError), "R1")
    record("SMT-B03", _rejects(lambda: strict_loads('{"x":1,"x":2}'), StrictJSONError), "R1")
    deeply_nested = "[" * 6 + "0" + "]" * 6
    record("SMT-B04", _rejects(lambda: strict_loads(deeply_nested, limits=StrictJSONLimits(max_depth=3)), StrictJSONError), "R1")
    additive_epoch = deepcopy(fixture["epoch"]); additive_epoch["new_additive_field"] = {"kept": True}
    env_receipt = schema_envelope_receipt(additive_epoch, "epoch")
    record("SMT-B06", (env_receipt["unknown_fields_policy"] == "PRESERVE_WITH_RECEIPT" and "new_additive_field" in env_receipt["unknown_fields"], env_receipt["unknown_fields_policy"]), "R1")

    mutated = deepcopy(fixture["events"][1]); mutated["payload"]["pointer_count"] = 999
    record("SMT-C03", _rejects(lambda: validate_event(mutated), ReplayIntegrityError), "R3")
    duplicate_seq = deepcopy(fixture["events"]); duplicate_seq[2]["sequence"] = 2
    record("SMT-C05", _rejects(lambda: replay(duplicate_seq, epoch=fixture["epoch"], assignment=fixture["assignment"], consent=fixture["consent"]), ReplayIntegrityError), "R3")
    gap_seq = deepcopy(fixture["events"]); gap_seq[-1]["sequence"] = 7
    record("SMT-C06", _rejects(lambda: replay(gap_seq, epoch=fixture["epoch"], assignment=fixture["assignment"], consent=fixture["consent"]), ReplayIntegrityError), "R3")
    time_back = deepcopy(fixture["events"]); time_back[2]["timestamp"] = "2026-08-19T07:59:00Z"
    record("SMT-C08", _rejects(lambda: replay(time_back, epoch=fixture["epoch"], assignment=fixture["assignment"], consent=fixture["consent"]), ReplayIntegrityError), "R3")
    mixed_trajectory = deepcopy(fixture["events"]); mixed_trajectory[-1]["trajectory_id"] = "trajectory:other"
    record("SMT-C10", _rejects(lambda: replay(mixed_trajectory, epoch=fixture["epoch"], assignment=fixture["assignment"], consent=fixture["consent"]), ReplayIntegrityError), "R3")
    mixed_subject = deepcopy(fixture["events"]); mixed_subject[-1]["participant_id"] = "participant:other"
    record("SMT-C11", _rejects(lambda: replay(mixed_subject, epoch=fixture["epoch"], assignment=fixture["assignment"], consent=fixture["consent"]), ReplayIntegrityError), "R3")
    integrity = verify_event_log(fixture["events"], epoch=fixture["epoch"], assignment=fixture["assignment"], consent=fixture["consent"])
    record("SMT-C12", (integrity["receipt"]["chain_root"] != "GENESIS" and len(integrity["receipt"]["chain_nodes"]) == len(fixture["events"]), integrity["receipt"]["chain_root"]), "R3")

    event_claim = deepcopy(fixture["events"]); event_claim[0]["claim_ceiling"] = "wider"
    record("SMT-D01", _rejects(lambda: replay(event_claim, epoch=fixture["epoch"], assignment=fixture["assignment"], consent=fixture["consent"]), SourceCurrentnessError), "R4")
    epoch_claim = deepcopy(fixture["epoch"]); epoch_claim["claim_ceiling"] = "wider"
    record("SMT-D02", _rejects(lambda: validate_epoch(epoch_claim), SourceCurrentnessError), "R4")
    consent_claim = deepcopy(fixture["consent"]); consent_claim["claim_ceiling"] = "wider"
    record("SMT-D03", _rejects(lambda: validate_consent(consent_claim), SourceCurrentnessError), "R4")
    human_events = deepcopy(fixture["events"]) + [_human_event(fixture)]
    record("SMT-D06", _rejects(lambda: replay(human_events, epoch=fixture["epoch"], assignment=fixture["assignment"], consent=fixture["consent"]), SourceCurrentnessError), "R4")
    snapshot = deepcopy(fixture["events"]); snapshot[0]["consent_scope_snapshot"]["artifact_export"] = True
    record("SMT-D07", _rejects(lambda: replay(snapshot, epoch=fixture["epoch"], assignment=fixture["assignment"], consent=fixture["consent"]), SourceCurrentnessError), "R4")

    minor = deepcopy(fixture["events"][0]); minor["schema_version"] = EVENT_SCHEMA_VERSION_MINOR1; minor["new_field"] = "preserved"; minor["event_id"] = "legacy:minor"
    migrated, migration = migrate_record(minor, kind="event", target_schema_version=EVENT_SCHEMA_VERSION)
    record("SMT-E01", (migration["receipt_kind"] == "MigrationReceipt.v1" and bool(migration["adapter_id"]), migration["adapter_id"]), "R2")
    record("SMT-E03", (migration["source_schema"] == EVENT_SCHEMA_VERSION_MINOR1 and migrated["schema_version"] == EVENT_SCHEMA_VERSION, migration["target_schema"]), "R2")
    record("SMT-E04", ("information_loss" in migration and "claim_impact" in migration, str(migration["information_loss"])), "R2")
    rolled_back = rollback_migration(minor, migration)
    record("SMT-E05", (migration["source_unchanged"] is True and canonical_digest(rolled_back) == canonical_digest(minor), migration["source_digest"]), "R2")
    record("SMT-E06", (migration["identity_map"].get("legacy:minor") == migrated["event_id"], json.dumps(migration["identity_map"], sort_keys=True)), "R2")
    terminal, terminal_receipt = map_terminal("RIGHT_CENSORED")
    record("SMT-E07", (terminal == "RIGHT_CENSORED" and terminal_receipt["equivalence"] == "IDENTITY_EXACT", terminal_receipt["receipt_id"]), "R2")
    major = deepcopy(fixture["events"][0]); major["schema_version"] = "gva06.f.ruv.repeat-use-event.v2"
    record("SMT-E08", _rejects(lambda: schema_envelope_receipt(major, "event"), SchemaVersionError), "R2")

    consent_tombstone = make_tombstone(target_kind="all-derived-state", target_id="consent-revoked", reason="withdrawn", effective_at="2026-08-19T08:01:01Z", source_receipt_ref=fixture["consent"]["receipt_id"])
    record("SMT-F04", _rejects(lambda: replay(fixture["events"], epoch=fixture["epoch"], assignment=fixture["assignment"], consent=fixture["consent"], tombstones=[consent_tombstone]), StateInvalidatedError), "R5")
    with tempfile.TemporaryDirectory() as tmp:
        consent = deepcopy(fixture["consent"]); consent["scopes"]["artifact_export"] = True
        destination = Path(tmp) / "events.jsonl"
        export_event_log(fixture["events"], destination, consent=consent, epoch=fixture["epoch"], assignment=fixture["assignment"])
        deletion = delete_export(destination, consent=consent, explicit_confirmation=True, effective_at="2026-08-19T08:02:00Z")
        record("SMT-F05", _rejects(lambda: replay(fixture["events"], epoch=fixture["epoch"], assignment=fixture["assignment"], consent=fixture["consent"], tombstones=[deletion["tombstone"]]), StateInvalidatedError), "R5")

    repairs = {
        "R1_STRICT_SCHEMA_ENVELOPE_AND_PARSER": all(cases[key]["passed"] for key in ("SMT-A03","SMT-A04","SMT-A05","SMT-B02","SMT-B03","SMT-B04","SMT-B06")),
        "R2_VERSION_REGISTRY_AND_MIGRATION_RECEIPT": all(cases[key]["passed"] for key in ("SMT-E01","SMT-E03","SMT-E04","SMT-E05","SMT-E06","SMT-E07","SMT-E08")),
        "R3_EVENT_IDENTITY_CHAIN_AND_REPLAY_INTEGRITY": all(cases[key]["passed"] for key in ("SMT-C03","SMT-C05","SMT-C06","SMT-C08","SMT-C10","SMT-C11","SMT-C12")),
        "R4_CURRENTNESS_CONSENT_AND_CLAIM_BINDING": all(cases[key]["passed"] for key in ("SMT-A06","SMT-A07","SMT-A08","SMT-D01","SMT-D02","SMT-D03","SMT-D06","SMT-D07")),
        "R5_TOMBSTONE_REVOCATION_DELETE_INTEGRATION": all(cases[key]["passed"] for key in ("SMT-F04","SMT-F05")),
    }
    operand = build_cross_version_replay_operand()
    all_passed = all(case["passed"] for case in cases.values()) and all(repairs.values()) and operand["unknown_major_rejected"]
    result = {
        "schema_version": "gva06.f.ruv.schema-currentness-replay-repair-result.v1",
        "artifact_id": "SchemaCurrentnessReplayRepair.v1",
        "program_id": PROGRAM_ID,"wave_id": "F.RUV.W3R","branch_id": BRANCH_ID,
        "artifact_state": "EXECUTED_VALIDATED_MERGEABLE_CANDIDATE_AT_LOCAL_REPAIR_CEILING",
        "terminal_disposition": "SCHEMA_CURRENTNESS_REPLAY_REPAIR_PASS" if all_passed else "REPAIR_INCOMPLETE",
        "source_binding": {"stewardstack_commit": STEWARDSTACK_COMMIT,"route_launch_digest": ROUTE_LAUNCH_DIGEST,"projectionworkbench_base": BASE_COMMIT},
        "case_summary": {"total": len(cases),"passed": sum(1 for c in cases.values() if c["passed"]),"failed": sum(1 for c in cases.values() if not c["passed"])},
        "case_results": cases,"repair_packages": repairs,"r6_cross_version_operand": operand,
        "independent_requalification_complete": False,"wave4_open": False,
        "exact_reentry": "Merge the accepted W3R repairs onto one current harness line, then run a fresh-agent W3Q cross-version requalification using the R6 operand before any Wave-4 human trajectory.",
        "claim_ceiling": CLAIM,
    }
    result["content_digest"] = canonical_digest(result)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(); parser.add_argument("--output", type=Path); args = parser.parse_args()
    result = run(); payload = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True); args.output.write_text(payload, encoding="utf-8")
    else: print(payload, end="")
    return 0 if result["terminal_disposition"] == "SCHEMA_CURRENTNESS_REPLAY_REPAIR_PASS" else 1


if __name__ == "__main__": raise SystemExit(main())
