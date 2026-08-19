#!/usr/bin/env python3
"""Deterministic fresh-agent R6 replay probe for F.RUV.W3Q2Q.B1."""
from __future__ import annotations

from copy import deepcopy
import argparse
import json
import os
from pathlib import Path
import tempfile
from typing import Any

import repeat_use_harness
from repeat_use_harness.fixture import make_fixture
from repeat_use_harness.strict_schema import (
    EVENT_SCHEMA_VERSION,
    EVENT_SCHEMA_VERSION_MINOR1,
    SchemaVersionError,
    StateInvalidatedError,
    canonical_digest,
    expected_event_id,
    migrate_record,
    read_jsonl,
    rollback_migration,
    schema_envelope_receipt,
    validate_event,
)
from repeat_use_harness.replay_integrity import make_tombstone, replay
from repeat_use_harness.state_membrane import delete_export, export_event_log


def _write(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")


def run_probe() -> dict[str, Any]:
    fixture = make_fixture()
    cases: dict[str, dict[str, Any]] = {}

    exact = replay(
        fixture["events"],
        epoch=fixture["epoch"],
        assignment=fixture["assignment"],
        consent=fixture["consent"],
    )
    cases["EXACT_V1_REPLAY"] = {
        "passed": exact["trajectory"]["causal_terminal"] == "RIGHT_CENSORED",
        "terminal": exact["trajectory"]["causal_terminal"],
        "replay_digest": exact["replay_digest"],
    }

    source = deepcopy(fixture["events"][0])
    source["schema_version"] = EVENT_SCHEMA_VERSION_MINOR1
    source["additive_metadata"] = {"fresh_agent": True, "semantics": "preserved"}
    source["event_id"] = "legacy:fresh-agent-minor"
    migrated, migration = migrate_record(source, kind="event", target_schema_version=EVENT_SCHEMA_VERSION)
    validate_event(migrated)
    cases["ADDITIVE_MINOR_MIGRATION"] = {
        "passed": (
            migration["source_unchanged"] is True
            and migration["unknown_fields_policy"] == "PRESERVE_WITH_RECEIPT"
            and "additive_metadata" in migration["unknown_fields"]
            and migration["identity_map"].get("legacy:fresh-agent-minor") == migrated["event_id"]
        ),
        "source_digest": migration["source_digest"],
        "target_digest": migration["target_digest"],
        "receipt_id": migration["receipt_id"],
    }

    major = deepcopy(source)
    major["schema_version"] = "gva06.f.ruv.repeat-use-event.v2"
    major_rejected = False
    try:
        schema_envelope_receipt(major, "event")
    except SchemaVersionError:
        major_rejected = True
    cases["UNKNOWN_MAJOR_REJECT"] = {"passed": major_rejected}

    export_fixture = make_fixture()
    export_consent = deepcopy(export_fixture["consent"])
    export_consent["scopes"]["artifact_export"] = True
    export_events = deepcopy(export_fixture["events"])
    for event in export_events:
        event["consent_scope_snapshot"] = deepcopy(export_consent["scopes"])
        event["event_id"] = expected_event_id(event)
    export_events[0]["schema_version"] = EVENT_SCHEMA_VERSION_MINOR1
    export_events[0]["additive_metadata"] = {"export_import": "preserve"}
    export_events[0]["event_id"] = "legacy:export-import"
    with tempfile.TemporaryDirectory() as tmp:
        export_path = Path(tmp) / "events.jsonl"
        export_receipt = export_event_log(
            export_events,
            export_path,
            consent=export_consent,
            epoch=export_fixture["epoch"],
            assignment=export_fixture["assignment"],
        )
        imported = read_jsonl(export_path)
        imported_result = replay(
            imported,
            epoch=export_fixture["epoch"],
            assignment=export_fixture["assignment"],
            consent=export_consent,
        )
        deletion = delete_export(
            export_path,
            consent=export_consent,
            explicit_confirmation=True,
            effective_at="2026-08-20T00:02:00Z",
        )
        resurrection_rejected = False
        try:
            replay(
                imported,
                epoch=export_fixture["epoch"],
                assignment=export_fixture["assignment"],
                consent=export_consent,
                tombstones=[deletion["tombstone"]],
            )
        except StateInvalidatedError:
            resurrection_rejected = True
    cases["MIGRATED_EXPORT_IMPORT"] = {
        "passed": (
            export_receipt["purpose_bound"] is True
            and len(imported) == len(export_events)
            and imported_result["trajectory"]["causal_terminal"] == "RIGHT_CENSORED"
            and resurrection_rejected
        ),
        "event_count": len(imported),
        "terminal": imported_result["trajectory"]["causal_terminal"],
        "event_log_digest": export_receipt["event_log_digest"],
        "resurrection_rejected": resurrection_rejected,
    }

    rolled = rollback_migration(source, migration)
    cases["ROLLBACK_REPLAY"] = {
        "passed": canonical_digest(rolled) == canonical_digest(source),
        "source_digest": canonical_digest(source),
        "rollback_digest": canonical_digest(rolled),
    }

    tombstone = make_tombstone(
        target_kind="trajectory",
        target_id=fixture["events"][0]["trajectory_id"],
        reason="fresh-agent no-resurrection probe",
        effective_at="2026-08-20T00:02:00Z",
        source_receipt_ref="receipt:f-ruv-w3q2q-b1-r6",
    )
    tombstone_rejected = False
    invalidation_disposition = None
    try:
        replay(
            fixture["events"],
            epoch=fixture["epoch"],
            assignment=fixture["assignment"],
            consent=fixture["consent"],
            tombstones=[tombstone],
        )
    except StateInvalidatedError as exc:
        tombstone_rejected = True
        invalidation_disposition = exc.receipt.get("disposition")
    cases["TOMBSTONE_NO_RESURRECTION"] = {
        "passed": tombstone_rejected and invalidation_disposition == "STATE_INVALIDATED_NO_RESURRECTION",
        "disposition": invalidation_disposition,
    }

    forbidden = os.environ.get("FORBIDDEN_CHECKOUT")
    module_path = Path(repeat_use_harness.__file__).resolve()
    outside_checkout = True
    if forbidden:
        try:
            module_path.relative_to(Path(forbidden).resolve())
            outside_checkout = False
        except ValueError:
            outside_checkout = True

    result = {
        "schema_version": "gva06.f.ruv.w3q2q.b1.fresh-agent-r6-probe.v1",
        "artifact_id": "CorrectedTargetFreshAgentCrossVersionReplayProbe.v1",
        "branch_id": "F.RUV.W3Q2Q.B1",
        "cases": cases,
        "case_count": len(cases),
        "passed": sum(1 for case in cases.values() if case["passed"]),
        "failed": sum(1 for case in cases.values() if not case["passed"]),
        "module_outside_checkout": outside_checkout,
        "human_value_supported": False,
        "wave_4_open": False,
        "claim_ceiling": (
            "Fresh-agent R6 schema/currentness/replay qualification only; no human repeat-use value, "
            "Wave-4 opening, release, merge, cutover, or owner admission."
        ),
    }
    result["semantic_digest"] = canonical_digest(result)
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = run_probe()
    _write(args.output, result)
    return 0 if result["failed"] == 0 and result["module_outside_checkout"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
