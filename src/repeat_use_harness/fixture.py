"""Terminal manifest and deterministic mechanical fixture."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from .constants import *
from .core import HarnessValidationError, append_event_file, canonical_digest, read_jsonl, stable_id, write_json
from .replay import replay

def build_harness_manifest() -> dict[str, Any]:
    manifest = {
        "schema_version": HARNESS_SCHEMA_VERSION,
        "artifact_id": "RepeatUseValueDiscoveryHarness.v1",
        "program_id": PROGRAM_ID,
        "wave_id": WAVE_ID,
        "branch_id": BRANCH_ID,
        "status": "IMPLEMENTED_VALIDATED_AT_MECHANICAL_CEILING",
        "terminal_disposition": "HARNESS_READY_FOR_SYNTHETIC_AND_FUTURE_PROSPECTIVE_USE",
        "artifact_state": "EXECUTED_VALIDATED_MERGEABLE_CANDIDATE",
        "source_horizon": {
            "stewardstack_commit": STEWARDSTACK_COMMIT,
            "canonical_route_launch_digest": ROUTE_LAUNCH_DIGEST,
            "projectionworkbench_base_commit": PROJECTIONWORKBENCH_BASE,
            "wave1_terminal_pointers": list(SOURCE_TERMINALS),
            "prior_wave_bytes_embedded": False,
        },
        "implemented_objects": [
            "RepeatUseExperimentEpoch.v1",
            "EpisodeAssignment.v1",
            "ConsentReceipt.v1",
            "RepeatUseEvent.v1",
            "UserValueEpisode.v1",
            "UserValueTrajectory.v1",
            "AppendOnlyEventReceipt.v1",
            "RepeatUseEventExportReceipt.v1",
            "RepeatUseDeletionReceipt.v1",
            "ReplayResult.v1",
        ],
        "required_control_surfaces": list(REQUIRED_CONTROL_SURFACES),
        "event_required_metadata": list(EVENT_REQUIRED_METADATA),
        "human_only_fields": list(HUMAN_ONLY_FIELDS),
        "burden_dimensions": list(BURDEN_DIMENSIONS),
        "comparator_arms": list(COMPARATOR_ARMS),
        "mandatory_comparator_arms": list(MANDATORY_COMPARATOR_ARMS),
        "parity_rules": list(PARITY_RULES),
        "agency_event_types": list(AGENCY_EVENT_TYPES),
        "instrumentation_terminals": list(INSTRUMENTATION_TERMINALS),
        "trajectory_terminals": list(TRAJECTORY_TERMINALS),
        "causal_terminal_priority": list(CAUSAL_TERMINAL_PRIORITY),
        "positive_terminal_guard": {
            "mechanical_or_synthetic_fixture_can_pass": False,
            "minimum_evidence_rung": "R3_REPEAT_TRAJECTORY",
            "all_identifiability_gates_required": True,
            "explicit_human_judgment_required": True,
            "independent_review_required": True,
        },
        "privacy_and_custody": {
            "local_first": True,
            "append_only_events": True,
            "raw_content_capture_default": False,
            "pointer_first_source_refs": True,
            "separate_consent_scopes": list(CONSENT_SCOPES),
            "explicit_export_receipt": True,
            "explicit_deletion_receipt": True,
        },
        "determinism": {
            "canonical_json": "UTF-8, sorted keys, compact separators",
            "content_hash": "sha256",
            "replay_order": "episode_id then event sequence",
            "same_input_same_digest": True,
        },
        "cli": {
            "fixture": "python -m repeat_use_harness fixture --output <dir>",
            "replay": "python -m repeat_use_harness replay --epoch <json> --assignment <json> --consent <json> --events <jsonl> --output <json>",
            "manifest": "python -m repeat_use_harness manifest --output <json>",
        },
        "lawful_default_fixture_terminal": "RIGHT_CENSORED",
        "nonclaims": [
            "No real human repeat-use trajectory was observed.",
            "No retention, accumulated-history benefit, or product direction is established.",
            "No interpersonal, hosted, network, willingness-to-pay, or market claim is established.",
            "No release, merge, cutover, or owner admission is established.",
        ],
        "exact_reentry": "After independent Wave-2 synthesis, bind a prospective human protocol through the declared owner/evaluator route; do not infer human value from this harness.",
        "claim_ceiling": CLAIM_CEILING,
    }
    manifest["artifact_digest"] = canonical_digest(manifest)
    return manifest


def make_fixture() -> dict[str, Any]:
    feature_flags = {
        "history_enabled": False,
        "semantic_lens_enabled": True,
        "provenance_view_enabled": True,
        "capture_tier": "MINIMAL",
        "fresh_agent_mode": True,
    }
    epoch = {
        "object_type": "RepeatUseExperimentEpoch.v1",
        "epoch_id": "epoch:F.RUV.W2.B1.fixture.v1",
        "program_id": PROGRAM_ID,
        "product_phase_id": "projectionworkbench:19cab543",
        "policy_digest": ROUTE_LAUNCH_DIGEST,
        "instrumentation_tier": "MINIMAL",
        "feature_flags": feature_flags,
        "started_at": "2026-08-19T08:00:00Z",
        "source_snapshot_refs": [
            f"git:pakkinlau/ProjectionWorkbench@{PROJECTIONWORKBENCH_BASE}",
            f"git:pakkinlau/StewardStack@{STEWARDSTACK_COMMIT}",
        ],
        "claim_ceiling": CLAIM_CEILING,
    }
    assignment = {
        "object_type": "EpisodeAssignment.v1",
        "assignment_id": "assignment:F.RUV.W2.B1.fixture.C3",
        "eligible_inquiry_stratum": "synthetic_mechanical_replay_only",
        "condition_id": "C3_F2_EMPTY_HISTORY",
        "assignment_method": "deterministic_fixture",
        "assignment_seed_or_rule": "fixture-v1",
        "assigned_before_start": True,
        "outcome_blind": True,
        "carryover_firewall": "fresh-agent empty-history fixture",
        "version_phase": "projectionworkbench:19cab543",
    }
    scopes = {
        "local_operational_capture": True,
        "human_judgment_capture": False,
        "artifact_export": False,
        "share_or_merge_with_another_party": False,
        "research_reuse_or_training": False,
        "future_recontact": False,
    }
    consent = {
        "object_type": "ConsentReceipt.v1",
        "receipt_id": "consent:F.RUV.W2.B1.fixture.local-only",
        "participant_id": "participant:synthetic-fixture",
        "issued_at": "2026-08-19T07:59:00Z",
        "scopes": scopes,
        "claim_ceiling": CLAIM_CEILING,
    }

    def event(
        sequence: int, event_type: str, timestamp: str, payload: Mapping[str, Any]
    ) -> dict[str, Any]:
        base = {
            "program_id": PROGRAM_ID,
            "trajectory_id": "trajectory:F.RUV.W2.B1.fixture",
            "episode_id": "episode:F.RUV.W2.B1.fixture.001",
            "participant_id": "participant:synthetic-fixture",
            "project_id": "project:synthetic-fixture",
            "inquiry_id": "inquiry:deterministic-replay",
            "condition_id": assignment["condition_id"],
            "product_phase_id": epoch["product_phase_id"],
            "preregistration_ref": "prereg:mechanical-fixture-only",
            "schema_version": EVENT_SCHEMA_VERSION,
            "event_type": event_type,
            "sequence": sequence,
            "timestamp": timestamp,
            "source_refs": epoch["source_snapshot_refs"],
            "consent_scope_snapshot": scopes,
            "feature_flag_snapshot": feature_flags,
            "payload": dict(payload),
            "claim_ceiling": CLAIM_CEILING,
        }
        base["event_id"] = stable_id("ruv-event", base)
        return base

    events = [
        event(1, "EPISODE_STARTED", "2026-08-19T08:00:00Z", {"mode": "fixture"}),
        event(
            2,
            "SOURCE_POINTER_OPENED",
            "2026-08-19T08:00:10Z",
            {"pointer_count": 2, "raw_content_captured": False},
        ),
        event(
            3,
            "FIRST_USEFUL_LENS_MARKED",
            "2026-08-19T08:00:25Z",
            {"mechanical_marker_only": True},
        ),
        event(
            4,
            "EXACT_REENTRY_IDENTIFIED",
            "2026-08-19T08:00:40Z",
            {"mechanical_marker_only": True, "source_supported": True},
        ),
        event(
            5,
            "BURDEN_RECORDED",
            "2026-08-19T08:00:45Z",
            {
                "capture_minutes": 0.5,
                "review_and_correction_minutes": 0.0,
                "cognitive_load": 0.0,
                "switching_friction": 0.0,
                "privacy_concern": 0.0,
                "trust_or_control_loss": 0.0,
                "lock_in_dependence": 0.0,
                "error_recovery_cost": 0.0,
            },
        ),
        event(
            6,
            "EPISODE_ENDED",
            "2026-08-19T08:01:00Z",
            {"mechanical_status": "REPLAY_COMPLETE", "human_confirmed": False},
        ),
    ]
    return {"epoch": epoch, "assignment": assignment, "consent": consent, "events": events}


def materialize_fixture(output: str | Path) -> dict[str, Any]:
    destination = Path(output)
    if destination.exists() and any(destination.iterdir()):
        raise HarnessValidationError("fixture output must be empty")
    destination.mkdir(parents=True, exist_ok=True)
    fixture = make_fixture()
    write_json(destination / "epoch.json", fixture["epoch"])
    write_json(destination / "assignment.json", fixture["assignment"])
    write_json(destination / "consent.json", fixture["consent"])
    event_path = destination / "events.jsonl"
    for event in fixture["events"]:
        append_event_file(
            event_path,
            event,
            epoch=fixture["epoch"],
            consent=fixture["consent"],
        )
    events = read_jsonl(event_path)
    replay_result = replay(
        events,
        epoch=fixture["epoch"],
        assignment=fixture["assignment"],
        consent=fixture["consent"],
    )
    manifest = build_harness_manifest()
    write_json(destination / "replay.json", replay_result)
    write_json(destination / "RepeatUseValueDiscoveryHarness.v1.json", manifest)
    summary = {
        "fixture_id": "F.RUV.W2.B1.mechanical-fixture.v1",
        "event_count": len(events),
        "replay_digest": replay_result["replay_digest"],
        "terminal": replay_result["trajectory"]["causal_terminal"],
        "expected_terminal": "RIGHT_CENSORED",
        "passed": replay_result["trajectory"]["causal_terminal"] == "RIGHT_CENSORED",
        "human_value_supported": False,
        "claim_ceiling": CLAIM_CEILING,
    }
    summary["fixture_digest"] = canonical_digest(summary)
    write_json(destination / "fixture_receipt.json", summary)
    return summary
