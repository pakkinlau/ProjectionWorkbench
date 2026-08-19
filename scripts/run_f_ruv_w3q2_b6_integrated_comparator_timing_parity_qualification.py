#!/usr/bin/env python3
"""Independent W3Q2.B6 qualification of comparator/timing parity on a frozen target.

This script is qualification-only.  It does not repair or mutate target code, does
not execute a prospective human trajectory, and cannot open Wave 4 by itself.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

from repeat_use_harness.comparator_parity import (
    CLAIM_CEILING as TARGET_CLAIM_CEILING,
    ComparatorParityError,
    adapt_event,
    canonical_comparator_id,
    canonical_history_condition,
    canonicalize_consent,
    canonicalize_features,
    digest as target_digest,
    make_event,
    parity_receipt,
    repair_artifact,
    summarize,
    synthetic_corpus,
    validate_events,
    validate_generic_baseline,
)

PROGRAM_ID = "GVA06.F.repeat-use-value-discovery.v2"
WAVE_ID = "F.RUV.W3Q2"
BRANCH_ID = "F.RUV.W3Q2.B6"
ARTIFACT_ID = "IntegratedComparatorTimingParityQualification.v1"
SCHEMA_VERSION = "gva06.f.ruv.integrated-comparator-timing-parity-qualification.v1"
ROUTE_LAUNCH_DIGEST = "a4848d67212416935e25d8f4fc09b3aeee1b62b4c761c5cfd7055eb0e4b26baa"
ROUTE_PIN_COMMIT = "a644409f293609ec2e6f0cb230ba0799d455ec1d"
CURRENT_STEWARDSTACK_COMMIT = "5713f1fffdea8e56dd6f0242a4c247c7b4ae7659"
CURRENT_STEWARDSTACK_TREE = "1b30eec0f7967f8ad24fab6a55bfaea2ddaec719"
TARGET_IDENTITY = "sha256:54ad0ee3651b391ff965fb5bc89954e66e061d4e6ff1e8504d090a6b427e5779"
TARGET_PATCH_SHA256 = "54ad0ee3651b391ff965fb5bc89954e66e061d4e6ff1e8504d090a6b427e5779"
TARGET_BASE_COMMIT = "e289a2ff01ee31f2f32e85247a2956a835e3c175"
ASSEMBLY_SOURCE_HEAD = "d41a17d2558ab8957b055e28f383350a4e06c007"
W3R_B6_HEAD = "a8d2d7499ff48c884b992dca5e0373d2142bb95d"
EXPECTED_ASSEMBLY_ARTIFACT_DIGEST = "f48e690ea1896973bbedf44ce3e7ec621766e1204fffa38aa87c1a6ba911f5ff"
EXPECTED_REPAIR_ARTIFACT_DIGEST = "deeabb981c2fbed82bd6ff0e1eadb48487729b7b30aa18dedf406b92174d3385"
EXPECTED_CORPUS_DIGEST = "6ba010e1c42b2efc576671eadf968fad5791881f82495fe10f191130336f564b"
EXPECTED_PARITY_RECEIPT_DIGEST = "1ebb98a4c6e4d9a2ee051c2e8eae549a1a0402170ddfd73c6e46d86dd5c718d1"
PASS_TERMINAL = "INTEGRATED_COMPARATOR_TIMING_PARITY_QUALIFIED_AT_CONTROLLED_FIXTURE_CEILING"
TARGET_MISMATCH_TERMINAL = "RIGHT_CENSORED_TARGET_IDENTITY_MISMATCH"
REPAIR_TERMINAL = "SELECTIVE_REPAIR_REQUIRED"
CLAIM_CEILING = (
    "Independent content-addressed target reconstruction and integrated comparator/timing "
    "parity qualification at a controlled mechanical/fixture ceiling only; no prospective "
    "human comparison, repeat-use value, retention, accumulated-history benefit, product "
    "direction, Wave-4 opening, release, merge, cutover, market, network, or owner admission."
)


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def digest(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected JSON object: {path}")
    return value


def _sha_label(label: str) -> str:
    return hashlib.sha256(label.encode("utf-8")).hexdigest()


def _iso_utc(value: str) -> datetime:
    parsed = datetime.fromisoformat(value[:-1] + "+00:00" if value.endswith("Z") else value)
    if parsed.tzinfo is None:
        raise ValueError("timestamp is not timezone-aware")
    return parsed.astimezone(timezone.utc)


def _expect_comparator_error(fn: Callable[[], Any]) -> tuple[bool, str]:
    try:
        fn()
    except ComparatorParityError as exc:
        return True, str(exc)
    except Exception as exc:  # pragma: no cover - classified explicitly in result
        return False, f"unexpected {type(exc).__name__}: {exc}"
    return False, "expected ComparatorParityError but call returned"


def _rebuild_events(
    envelope: Mapping[str, Any],
    events: Sequence[Mapping[str, Any]],
    overrides: Mapping[int, Mapping[str, Any]],
) -> list[dict[str, Any]]:
    rebuilt: list[dict[str, Any]] = []
    previous: str | None = None
    for index, original in enumerate(events):
        change = dict(overrides.get(index, {}))
        event = make_event(
            envelope,
            sequence=int(change.get("sequence", original["sequence"])),
            event_type=str(change.get("event_type", original["event_type"])),
            monotonic_ns=int(change.get("monotonic_ns", original["monotonic_ns"])),
            timestamp_utc=str(change.get("timestamp_utc", original["timestamp_utc"])),
            payload=deepcopy(change.get("payload", original["payload"])),
            previous_event_hash=change.get("previous_event_hash", previous),
        )
        previous = event["event_hash"]
        rebuilt.append(event)
    return rebuilt


def _valid_generic_declaration(envelope: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "task_f_semantics_available": False,
        "task_f_history_available": False,
        "hidden_chat_state_available": False,
        "treatment_only_assistance_available": False,
        "source_snapshot_digest": envelope["source_snapshot_digest"],
        "task_prompt_digest": envelope["task_prompt_digest"],
        "evaluator_policy_digest": envelope["evaluator_policy_digest"],
        "public_information_digest": envelope["public_information_digest"],
        "measurement_dose_digest": envelope["measurement_dose_digest"],
        "assistance_policy_digest": envelope["assistance_policy_digest"],
        "active_time_budget_seconds": envelope["active_time_budget_seconds"],
        "familiarization_seconds": envelope["familiarization_seconds"],
    }


def _record(
    checks: dict[str, dict[str, Any]],
    check_id: str,
    passed: bool,
    observed: Any,
    expected: Any,
    note: str,
) -> None:
    checks[check_id] = {
        "pass": bool(passed),
        "observed": observed,
        "expected": expected,
        "note": note,
    }


def qualify(*, root: Path, assembly_dir: Path) -> dict[str, Any]:
    root = root.resolve()
    assembly_dir = assembly_dir.resolve()
    checks: dict[str, dict[str, Any]] = {}

    target_patch = assembly_dir / "IntegratedW3RRepairAssembly.patch"
    assembly_path = assembly_dir / "IntegratedW3RRepairAssembly.v1.json"
    repair_path = assembly_dir / "ComparatorTimingParityRepair.v1.json"
    corpus_path = assembly_dir / "SyntheticTimingParityCorpus.v2.json"

    required_paths = [target_patch, assembly_path, repair_path, corpus_path]
    missing = [str(path) for path in required_paths if not path.is_file()]
    _record(
        checks,
        "Q01_ASSEMBLY_OUTPUTS_PRESENT",
        not missing,
        missing,
        [],
        "The qualifier consumes only the exact reconstruction outputs, not a prior-wave archive body.",
    )

    observed_patch_sha = file_sha256(target_patch) if target_patch.is_file() else None
    _record(
        checks,
        "Q02_TARGET_PATCH_IDENTITY",
        observed_patch_sha == TARGET_PATCH_SHA256,
        observed_patch_sha,
        TARGET_PATCH_SHA256,
        "All W3Q2 branches must bind the same content-addressed target.",
    )

    assembly = load_json(assembly_path) if assembly_path.is_file() else {}
    repair_from_run = load_json(repair_path) if repair_path.is_file() else {}
    corpus_from_run = load_json(corpus_path) if corpus_path.is_file() else {}

    _record(
        checks,
        "Q03_ASSEMBLY_TERMINAL",
        assembly.get("terminal_disposition")
        == "INTEGRATED_W3R_REPAIR_ASSEMBLY_PASS_AT_CONTROLLED_LOCAL_CEILING",
        assembly.get("terminal_disposition"),
        "INTEGRATED_W3R_REPAIR_ASSEMBLY_PASS_AT_CONTROLLED_LOCAL_CEILING",
        "The integrated target must pass its own construction checks before B6 can qualify it.",
    )
    _record(
        checks,
        "Q04_ASSEMBLY_ARTIFACT_DIGEST",
        assembly.get("artifact_digest") == EXPECTED_ASSEMBLY_ARTIFACT_DIGEST,
        assembly.get("artifact_digest"),
        EXPECTED_ASSEMBLY_ARTIFACT_DIGEST,
        "B6 does not accept a semantically similar but differently assembled target.",
    )
    assembly_checks = assembly.get("checks", {}) if isinstance(assembly.get("checks"), dict) else {}
    _record(
        checks,
        "Q05_ASSEMBLY_COMPONENT_CHECKS",
        bool(assembly_checks) and all(value is True for value in assembly_checks.values()),
        assembly_checks,
        "all true",
        "Terminal admission, custody, clean room, noninterference, comparator, replay, and attack closure are noncompensatory.",
    )

    repair_direct_a = repair_artifact()
    repair_direct_b = repair_artifact()
    corpus_direct_a = synthetic_corpus()
    corpus_direct_b = synthetic_corpus()

    _record(
        checks,
        "Q06_REPAIR_REPLAY_DETERMINISTIC",
        repair_direct_a == repair_direct_b,
        repair_direct_a.get("artifact_digest"),
        repair_direct_b.get("artifact_digest"),
        "Independent replay of the repair artifact must be byte-semantically deterministic.",
    )
    _record(
        checks,
        "Q07_CORPUS_REPLAY_DETERMINISTIC",
        corpus_direct_a == corpus_direct_b,
        corpus_direct_a.get("corpus_digest"),
        corpus_direct_b.get("corpus_digest"),
        "The six-arm corpus and its receipts must not depend on ambient state.",
    )
    _record(
        checks,
        "Q08_REPAIR_ARTIFACT_EXACT",
        repair_direct_a.get("artifact_digest") == EXPECTED_REPAIR_ARTIFACT_DIGEST
        and repair_from_run.get("artifact_digest") == EXPECTED_REPAIR_ARTIFACT_DIGEST,
        {
            "direct": repair_direct_a.get("artifact_digest"),
            "assembly_output": repair_from_run.get("artifact_digest"),
        },
        EXPECTED_REPAIR_ARTIFACT_DIGEST,
        "The exact B6 repair witness must survive integration unchanged.",
    )
    _record(
        checks,
        "Q09_CORPUS_AND_RECEIPT_EXACT",
        corpus_direct_a.get("corpus_digest") == EXPECTED_CORPUS_DIGEST
        and corpus_from_run.get("corpus_digest") == EXPECTED_CORPUS_DIGEST
        and corpus_direct_a.get("baseline_timing_parity_receipt", {}).get("receipt_digest")
        == EXPECTED_PARITY_RECEIPT_DIGEST,
        {
            "direct_corpus": corpus_direct_a.get("corpus_digest"),
            "assembly_corpus": corpus_from_run.get("corpus_digest"),
            "receipt": corpus_direct_a.get("baseline_timing_parity_receipt", {}).get("receipt_digest"),
        },
        {
            "corpus": EXPECTED_CORPUS_DIGEST,
            "receipt": EXPECTED_PARITY_RECEIPT_DIGEST,
        },
        "Corpus and receipt identity are pinned, not merely their terminal strings.",
    )

    receipt = corpus_direct_a["baseline_timing_parity_receipt"]
    gates = receipt["gate_results"]
    _record(
        checks,
        "Q10_P01_TO_P12_NONCOMPENSATORY_PASS",
        len(gates) == 12 and all(gates.values()) and receipt["noncompensatory_pass"] is True,
        gates,
        "P01-P12 all true",
        "Visibility, exposure, timing, dose, budget, familiarization, order, burden, history, and arm integrity all pass.",
    )
    condition_ids = receipt["condition_ids"]
    _record(
        checks,
        "Q11_SIX_CANONICAL_ARMS_UNIQUE",
        len(condition_ids) == 6 and len(set(condition_ids)) == 6,
        condition_ids,
        "six unique canonical arms",
        "Comparator-arm collapse would invalidate causal interpretation.",
    )

    alias_expectations = {
        "M.manual": "C0_MANUAL_ORDINARY_WORKFLOW",
        "G.generic": "C1_GENERIC_PROJECT_MEMORY",
        "R.reset": "C3_F2_EMPTY_HISTORY",
        "A.accumulated.1": "C4_F2_ACCUMULATED_VALID_HISTORY",
        "C5_NEGATIVE_HISTORY_CONTROL": "C5_F2_HISTORY_NEGATIVE_CONTROL_FAMILY",
    }
    alias_observed = {key: canonical_comparator_id(key) for key in alias_expectations}
    _record(
        checks,
        "Q12_COMPARATOR_ALIAS_CANONICALIZATION",
        alias_observed == alias_expectations,
        alias_observed,
        alias_expectations,
        "Known legacy aliases map to one canonical identity without flattening unknown values.",
    )

    history_expectations = {
        "ACCUMULATED_VALID": "VALID_ACCUMULATED",
        "VALID_HISTORY": "VALID_ACCUMULATED",
        "NO_TASK_F_STATE": "NO_F2_STATE",
        "RESET": "RESET",
        "SHUFFLED": "SHUFFLED",
    }
    history_observed = {key: canonical_history_condition(key) for key in history_expectations}
    _record(
        checks,
        "Q13_HISTORY_ALIAS_CANONICALIZATION",
        history_observed == history_expectations,
        history_observed,
        history_expectations,
        "History identity is explicit and domain-specific negative controls remain distinct.",
    )

    ok, note = _expect_comparator_error(lambda: canonical_comparator_id("UNKNOWN_ARM"))
    _record(checks, "Q14_UNKNOWN_COMPARATOR_FAILS_CLOSED", ok, note, "ComparatorParityError", "Unknown arms are never coerced into a known control.")
    ok, note = _expect_comparator_error(lambda: canonical_history_condition("EMPTY_OR_RESET"))
    _record(checks, "Q15_AMBIGUOUS_HISTORY_FAILS_CLOSED", ok, note, "ComparatorParityError", "Empty and reset remain distinct unless the protocol names one.")

    first_case = corpus_direct_a["cases"][0]
    first_envelope = first_case["envelope"]
    first_events = first_case["events"]

    conflicting_features = deepcopy(first_envelope["feature_flag_snapshot"])
    conflicting_features["history_enabled"] = not conflicting_features["product.history_enabled"]
    ok, note = _expect_comparator_error(lambda: canonicalize_features(conflicting_features))
    _record(checks, "Q16_FEATURE_ALIAS_CONFLICT_FAILS_CLOSED", ok, note, "ComparatorParityError", "Legacy and canonical feature names may coexist only when semantically identical.")

    ok, note = _expect_comparator_error(
        lambda: canonicalize_consent(["local_operational_capture"])
    )
    _record(checks, "Q17_CONSENT_SHAPE_FAILS_CLOSED", ok, note, "ComparatorParityError", "Array-shaped consent cannot imply enabled scopes without an explicit mapping.")

    sequence_bad = _rebuild_events(first_envelope, first_events, {1: {"sequence": 3}})
    ok, note = _expect_comparator_error(lambda: validate_events(sequence_bad))
    _record(checks, "Q18_SEQUENCE_GAP_REJECTED", ok, note, "ComparatorParityError", "Event sequence must be contiguous.")

    monotonic_bad = _rebuild_events(
        first_envelope,
        first_events,
        {1: {"monotonic_ns": first_events[0]["monotonic_ns"]}},
    )
    ok, note = _expect_comparator_error(lambda: validate_events(monotonic_bad))
    _record(checks, "Q19_MONOTONIC_ROLLBACK_REJECTED", ok, note, "ComparatorParityError", "Active-time measurement uses a strictly increasing monotonic clock.")

    earlier = (_iso_utc(first_events[0]["timestamp_utc"]).timestamp() - 1.0)
    earlier_text = datetime.fromtimestamp(earlier, tz=timezone.utc).isoformat().replace("+00:00", "Z")
    utc_bad = _rebuild_events(first_envelope, first_events, {1: {"timestamp_utc": earlier_text}})
    ok, note = _expect_comparator_error(lambda: validate_events(utc_bad))
    _record(checks, "Q20_UTC_ROLLBACK_REJECTED", ok, note, "ComparatorParityError", "UTC audit time may tie but cannot move backwards.")

    chain_bad = _rebuild_events(first_envelope, first_events, {1: {"previous_event_hash": "0" * 64}})
    ok, note = _expect_comparator_error(lambda: validate_events(chain_bad))
    _record(checks, "Q21_HASH_CHAIN_TAMPER_REJECTED", ok, note, "ComparatorParityError", "Every event binds the prior event hash.")

    id_bad = deepcopy(first_events)
    id_bad[1] = deepcopy(id_bad[1])
    id_bad[1]["event_id"] = "event:" + "0" * 24
    ok, note = _expect_comparator_error(lambda: validate_events(id_bad))
    _record(checks, "Q22_EVENT_ID_TAMPER_REJECTED", ok, note, "ComparatorParityError", "Event identity is derived from immutable content.")

    content_bad = deepcopy(first_events)
    content_bad[1] = deepcopy(content_bad[1])
    content_bad[1]["payload"] = {"tampered": True}
    ok, note = _expect_comparator_error(lambda: validate_events(content_bad))
    _record(checks, "Q23_EVENT_CONTENT_TAMPER_REJECTED", ok, note, "ComparatorParityError", "Payload mutation invalidates the content hash.")

    first_summary = summarize(first_envelope, first_events)
    _record(
        checks,
        "Q24_PAUSE_AND_ACTIVE_TIME_ACCOUNTING",
        first_summary["pause_seconds"] == 1.0 and first_summary["active_seconds"] == 5.0,
        {
            "pause_seconds": first_summary["pause_seconds"],
            "active_seconds": first_summary["active_seconds"],
        },
        {"pause_seconds": 1.0, "active_seconds": 5.0},
        "Paused time is excluded from active time rather than hidden in elapsed wall time.",
    )

    low_budget_envelope = deepcopy(first_envelope)
    low_budget_envelope["active_time_budget_seconds"] = 1
    low_budget_events = _rebuild_events(low_budget_envelope, first_events, {})
    ok, note = _expect_comparator_error(lambda: validate_events(low_budget_events))
    _record(checks, "Q25_ACTIVE_TIME_BUDGET_FAILS_CLOSED", ok, note, "ComparatorParityError", "A longer run cannot borrow budget from another arm.")

    generic_case = corpus_direct_a["cases"][1]
    generic_envelope = generic_case["envelope"]
    generic_valid = _valid_generic_declaration(generic_envelope)
    generic_valid_ok = True
    generic_valid_note = "PASS"
    try:
        validate_generic_baseline(generic_envelope, generic_valid)
    except Exception as exc:  # pragma: no cover - recorded
        generic_valid_ok = False
        generic_valid_note = f"{type(exc).__name__}: {exc}"
    _record(checks, "Q26_GENERIC_BASELINE_VALID_CONTRACT", generic_valid_ok, generic_valid_note, "PASS", "The generic comparator remains Task-F-blind while matching public conditions.")

    generic_bad = deepcopy(generic_valid)
    generic_bad["task_f_history_available"] = True
    ok, note = _expect_comparator_error(lambda: validate_generic_baseline(generic_envelope, generic_bad))
    _record(checks, "Q27_GENERIC_BASELINE_CONTAMINATION_REJECTED", ok, note, "ComparatorParityError", "Generic memory cannot gain treatment-only history.")

    mutated_summaries = [deepcopy(case["summary"]) for case in corpus_direct_a["cases"]]
    mutated_summaries[1]["assistance_policy_digest"] = _sha_label("unequal-assistance")
    negative_receipt = parity_receipt(mutated_summaries)
    _record(
        checks,
        "Q28_NONCOMPENSATORY_PARITY_FAILURE",
        negative_receipt["noncompensatory_pass"] is False
        and negative_receipt["gate_results"]["P02_INFORMATION_VISIBILITY"] is False
        and negative_receipt["terminal"] == "REPAIR_REQUIRED_BEFORE_PROSPECTIVE_COMPARATOR_PARITY",
        {
            "terminal": negative_receipt["terminal"],
            "P02": negative_receipt["gate_results"]["P02_INFORMATION_VISIBILITY"],
        },
        {
            "terminal": "REPAIR_REQUIRED_BEFORE_PROSPECTIVE_COMPARATOR_PARITY",
            "P02": False,
        },
        "One failed parity coordinate cannot be compensated by the other eleven.",
    )

    adapter_results: dict[str, Any] = {}
    adapter_ok = True
    adapter_note = "PASS"
    try:
        source_event = first_events[0]
        source_record = {
            "condition_id": source_event["condition_id"],
            "history_condition": source_event["history_condition"],
            "sequence": source_event["sequence"],
            "event_type": source_event["event_type"],
            "timestamp_utc": source_event["timestamp_utc"],
            "monotonic_ns": source_event["monotonic_ns"],
            "payload": source_event["payload"],
        }
        for contract in ("B1_HARNESS", "B4_MANUAL", "B6_LOW_BURDEN", "B7_SYNTHETIC"):
            adapted = adapt_event(
                contract,
                source_record,
                first_envelope,
                monotonic_ns=source_event["monotonic_ns"],
                previous_event_hash=None,
            )
            adapter_results[contract] = {
                "condition_id": adapted["condition_id"],
                "event_id": adapted["event_id"],
                "adapter_source_contract": adapted["payload"]["adapter_source_contract"],
            }
            if adapted["condition_id"] != first_envelope["condition_id"]:
                adapter_ok = False
    except Exception as exc:  # pragma: no cover - recorded
        adapter_ok = False
        adapter_note = f"{type(exc).__name__}: {exc}"
    _record(checks, "Q29_B1_B4_B6_B7_ADAPTER_CLOSURE", adapter_ok, adapter_results or adapter_note, "four content-bound adapters", "Adapters normalize timing and identity but never invent a missing witness.")

    target_surface_paths = [
        "src/repeat_use_harness/comparator_parity.py",
        "scripts/run_f_ruv_w3r_b6_comparator_timing_parity_repair.py",
        "tests/test_f_ruv_w3r_b6_comparator_timing_parity_repair.py",
        "receipts/f_ruv_w3r_b6_execution_receipt.md",
    ]
    surface_hashes = {
        path: file_sha256(root / path) if (root / path).is_file() else None
        for path in target_surface_paths
    }
    _record(
        checks,
        "Q30_EXACT_B6_SURFACES_PRESENT",
        all(value is not None for value in surface_hashes.values()),
        surface_hashes,
        "all four exact surfaces present",
        "The integrated target must contain module, runner, tests, and receipt.",
    )

    _record(
        checks,
        "Q31_TARGET_CLAIM_CEILING_NONPROMOTING",
        "no prospective human comparison" in TARGET_CLAIM_CEILING
        and repair_direct_a.get("wave4_open") is False
        and repair_direct_a.get("w3q_requalification_required") is True,
        {
            "target_claim_ceiling": TARGET_CLAIM_CEILING,
            "repair_wave4_open": repair_direct_a.get("wave4_open"),
            "requalification_required": repair_direct_a.get("w3q_requalification_required"),
        },
        "nonpromoting mechanical repair boundary",
        "A successful fixture repair cannot become human-value evidence.",
    )

    all_pass = all(item["pass"] for item in checks.values())
    target_identity_pass = checks["Q02_TARGET_PATCH_IDENTITY"]["pass"]
    terminal = (
        PASS_TERMINAL
        if all_pass
        else TARGET_MISMATCH_TERMINAL
        if not target_identity_pass
        else REPAIR_TERMINAL
    )
    failed_checks = [check_id for check_id, item in checks.items() if not item["pass"]]
    exact_reentry = (
        "Return this BranchReturn to F.RUV.W3Q2.RollingSynthesis; await B1-B8, then run "
        "web.synthesize -> web.steer. This branch alone cannot open Wave 4."
        if all_pass
        else (
            "Reconstruct the frozen target from base e289a2ff plus patch sha256:54ad0ee3, "
            f"repair only the failed qualification coordinates {failed_checks}, and rerun F.RUV.W3Q2.B6."
        )
    )

    result: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "artifact_id": ARTIFACT_ID,
        "artifact_state": "EXECUTED_VALIDATED_BRANCH_RETURN" if all_pass else "EXECUTED_REPAIR_OR_REENTRY_REQUIRED",
        "program_id": PROGRAM_ID,
        "wave_id": WAVE_ID,
        "branch_id": BRANCH_ID,
        "route_binding": {
            "canonical_entrypoint": "web.intake",
            "canonical_prompt": "web.branch",
            "canonical_local_route": "web.reentry -> local.task -> core.intake -> core.work -> local.worker/core.action -> local.cross-home -> web.branch",
            "route_pin_commit": ROUTE_PIN_COMMIT,
            "current_stewardstack_commit": CURRENT_STEWARDSTACK_COMMIT,
            "current_stewardstack_tree": CURRENT_STEWARDSTACK_TREE,
            "route_launch_digest": ROUTE_LAUNCH_DIGEST,
        },
        "target_binding": {
            "target_identity": TARGET_IDENTITY,
            "target_patch_sha256": TARGET_PATCH_SHA256,
            "observed_patch_sha256": observed_patch_sha,
            "base_commit": TARGET_BASE_COMMIT,
            "assembly_source_head": ASSEMBLY_SOURCE_HEAD,
            "w3r_b6_head": W3R_B6_HEAD,
            "prior_wave_payload_bytes_embedded": 0,
        },
        "qualification_checks": checks,
        "summary": {
            "total": len(checks),
            "passed": sum(1 for item in checks.values() if item["pass"]),
            "failed": len(failed_checks),
            "failed_check_ids": failed_checks,
        },
        "terminal_disposition": terminal,
        "w3q2_coordinate_passed": all_pass,
        "independent_w3q2_complete": False,
        "human_value_supported": False,
        "prospective_human_trajectory_authorized": False,
        "product_direction_authorized": False,
        "wave4_open": False,
        "no_learning_consequence": {
            "policy_or_model_updated": False,
            "reason": "This branch independently qualifies measurement machinery on controlled fixtures only.",
        },
        "exact_reentry": exact_reentry,
        "claim_ceiling": CLAIM_CEILING,
    }
    result["content_digest"] = digest(result)
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--assembly-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = qualify(root=args.root, assembly_dir=args.assembly_dir)
    text = json.dumps(result, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding="utf-8")
    else:
        print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
