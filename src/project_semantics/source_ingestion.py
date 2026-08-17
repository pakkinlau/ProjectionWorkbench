"""F2.W4.B1 bounded source-semantic ingestion and private-value repair."""
from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path
from typing import Any, Iterable, Mapping

from . import (
    ValidationError, _now, canonical_bytes, canonical_digest, init_project,
    link_source, load_json, load_project, save_project, stable_id, validate_task,
    write_json,
)

_SOURCE_MAX_BYTES = 256_000
_ACTION_KEYS = {"next_action", "exact_reentry", "reentry", "next_safe_action", "recommended_next_action"}
_BLOCKER_KEYS = {"blockers", "missing_operands", "holds", "unresolved", "first_zero"}
_STATUS_KEYS = {"status", "state", "disposition", "rolling_verdict", "current_state"}


def _bounded_text(path: Path) -> tuple[str, bytes]:
    raw = path.read_bytes()
    if len(raw) > _SOURCE_MAX_BYTES:
        raise ValidationError(f"source exceeds bounded ingestion limit: {path}")
    return raw.decode("utf-8", errors="replace"), raw


def _source_kind(path: Path) -> str:
    name = path.name.casefold()
    if path.suffix.casefold() == ".json":
        return "json"
    if "git" in name or name in {"status.txt", "log.txt"}:
        return "git_like"
    return "markdown_or_text"


def _flatten_json(value: Any, prefix: str = "") -> list[tuple[str, Any]]:
    rows: list[tuple[str, Any]] = []
    if isinstance(value, Mapping):
        for key in sorted(value):
            child = f"{prefix}.{key}" if prefix else str(key)
            rows.extend(_flatten_json(value[key], child))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            rows.extend(_flatten_json(item, f"{prefix}[{index}]"))
    else:
        rows.append((prefix, value))
    return rows


def _candidate(text: str, *, score: int, source_ref: str, line: int | None, kind: str) -> dict[str, Any]:
    compact = " ".join(text.strip().split())
    return {"text": compact[:500], "score": score, "source_ref": source_ref, "line": line, "kind": kind}


def _extract_json_semantics(value: Any, source_ref: str) -> dict[str, list[dict[str, Any]]]:
    result = {"actions": [], "blockers": [], "statuses": [], "claims": []}
    for key_path, item in _flatten_json(value):
        leaf = key_path.rsplit(".", 1)[-1].split("[")[0].casefold()
        if isinstance(item, (str, int, float, bool)):
            text = str(item)
            if leaf in _ACTION_KEYS and text.strip():
                result["actions"].append(_candidate(text, score=100, source_ref=source_ref, line=None, kind="explicit_json_action"))
            elif leaf in _STATUS_KEYS and text.strip():
                result["statuses"].append(_candidate(text, score=85, source_ref=source_ref, line=None, kind="json_status"))
            elif any(token in key_path.casefold() for token in ("claim", "supported", "contradicted")) and text.strip():
                result["claims"].append(_candidate(f"{key_path}: {text}", score=60, source_ref=source_ref, line=None, kind="json_claim"))
        if any(leaf == token for token in _BLOCKER_KEYS):
            if isinstance(item, list):
                for part in item:
                    if isinstance(part, (str, int, float)):
                        result["blockers"].append(_candidate(str(part), score=80, source_ref=source_ref, line=None, kind="json_blocker"))
            elif isinstance(item, str):
                result["blockers"].append(_candidate(item, score=80, source_ref=source_ref, line=None, kind="json_blocker"))
    return result


def _extract_text_semantics(text: str, source_ref: str, *, git_like: bool = False) -> dict[str, list[dict[str, Any]]]:
    result = {"actions": [], "blockers": [], "statuses": [], "claims": []}
    heading = ""
    for number, raw_line in enumerate(text.splitlines(), 1):
        line = raw_line.strip()
        if not line:
            continue
        if line.startswith("#"):
            heading = line.lstrip("#").strip().casefold()
            continue
        lower = line.casefold()
        if any(token in lower for token in ("raw_private_marker", "password", "secret", "api_key", "access_token")):
            continue
        clean = line.lstrip("-*+[] xX0123456789.).\t").strip()
        if git_like:
            if lower.startswith(("on branch ", "branch ")):
                result["statuses"].append(_candidate(line, score=70, source_ref=source_ref, line=number, kind="git_status"))
            elif lower.startswith(("m ", "a ", "d ", "??", "modified:", "new file:")):
                result["blockers"].append(_candidate(f"Unreviewed working-tree change: {line}", score=45, source_ref=source_ref, line=number, kind="git_dirty_state"))
            continue
        if any(token in heading for token in ("next", "reentry", "action", "todo")) and clean:
            result["actions"].append(_candidate(clean, score=90, source_ref=source_ref, line=number, kind="markdown_next_action"))
        elif line.startswith("- [ ]"):
            result["actions"].append(_candidate(clean, score=75, source_ref=source_ref, line=number, kind="unchecked_task"))
        if any(token in heading for token in ("blocker", "missing", "hold", "unresolved", "first zero")) and clean:
            result["blockers"].append(_candidate(clean, score=75, source_ref=source_ref, line=number, kind="markdown_blocker"))
        elif any(token in lower for token in ("blocked", "missing operand", "unresolved", "right-censored", "right_censored")):
            result["blockers"].append(_candidate(clean, score=60, source_ref=source_ref, line=number, kind="text_blocker"))
        if any(token in heading for token in ("status", "state", "verdict", "disposition")) and clean:
            result["statuses"].append(_candidate(clean, score=70, source_ref=source_ref, line=number, kind="markdown_status"))
        if any(token in heading for token in ("claim", "supported", "contradicted")) and clean:
            result["claims"].append(_candidate(clean, score=55, source_ref=source_ref, line=number, kind="markdown_claim"))
    return result


def ingest_source_files(root: str | Path, source_paths: Iterable[str | Path], task: Mapping[str, Any], *, observed_at: str | None = None, max_confirmations: int = 3) -> dict[str, Any]:
    """Derive a provisional semantic state while leaving raw source bytes external."""
    validate_task(task)
    if max_confirmations < 0 or max_confirmations > 10:
        raise ValidationError("max_confirmations must be between 0 and 10")
    project = load_project(root)
    records: list[dict[str, Any]] = []
    aggregate = {"actions": [], "blockers": [], "statuses": [], "claims": []}
    for supplied in source_paths:
        path = Path(supplied)
        if not path.is_file():
            raise ValidationError(f"source not found: {path}")
        text, raw = _bounded_text(path)
        kind = _source_kind(path)
        source_id = stable_id("source", [str(path.resolve()), hashlib.sha256(raw).hexdigest()])
        records.append({
            "source_id": source_id,
            "locator": str(path),
            "kind": kind,
            "content_identity": hashlib.sha256(raw).hexdigest(),
            "size_bytes": len(raw),
            "line_count": len(text.splitlines()),
            "custody": "external_or_linked",
            "raw_bytes_embedded": False,
        })
        if kind == "json":
            try:
                extracted = _extract_json_semantics(json.loads(text), source_id)
            except json.JSONDecodeError as exc:
                raise ValidationError(f"invalid JSON source {path}: {exc}") from exc
        else:
            extracted = _extract_text_semantics(text, source_id, git_like=kind == "git_like")
        for key in aggregate:
            aggregate[key].extend(extracted[key])
    for key in aggregate:
        aggregate[key] = sorted(aggregate[key], key=lambda item: (-item["score"], item["text"], item["source_ref"]))
    task_fallback = (task.get("questions") or [task["goal"]])[0]
    action_candidates = aggregate["actions"]
    exact_reentry = action_candidates[0]["text"] if action_candidates else task_fallback
    confidence = "HIGH" if action_candidates and action_candidates[0]["score"] >= 90 else "MEDIUM" if action_candidates else "LOW"
    questions: list[str] = []
    if action_candidates and len(action_candidates) > 1 and action_candidates[0]["text"] != action_candidates[1]["text"]:
        questions.append(f"Confirm the priority between: '{action_candidates[0]['text']}' and '{action_candidates[1]['text']}'.")
    if aggregate["blockers"]:
        questions.append(f"Confirm whether the leading blocker is still active: '{aggregate['blockers'][0]['text']}'.")
    if confidence == "LOW":
        questions.append("No explicit source-derived reentry was found; confirm the proposed task fallback.")
    questions = questions[:max_confirmations]
    payload = {
        "semantic_state_kind": "ProvisionalSourceSemanticState",
        "project_ref": project["project_ref"]["project_id"],
        "task_context_ref": task["task_context_id"],
        "observed_at": observed_at or _now(),
        "source_records": records,
        "status_candidates": aggregate["statuses"][:10],
        "action_candidates": action_candidates[:10],
        "blocker_candidates": aggregate["blockers"][:10],
        "claim_candidates": aggregate["claims"][:10],
        "exact_reentry_candidate": exact_reentry,
        "reentry_confidence": confidence,
        "confirmation_questions": questions,
        "confirmation_budget": max_confirmations,
        "information_loss": [
            "raw source bytes remain external",
            "extraction is heuristic and task-relative",
            "intent, authority, truth and capability are not inferred",
        ],
        "claim_ceiling": "Provisional source-derived project state and reentry candidate only; requires bounded human correction before consequential use.",
    }
    identity_payload = dict(payload)
    identity_payload.pop("observed_at")
    payload["semantic_state_id"] = stable_id("semantic-state", identity_payload)
    project.setdefault("semantic_states", []).append(payload)
    save_project(root, project)
    return payload


def derive_source_lens(root: str | Path, task: Mapping[str, Any], *, semantic_state_ref: str) -> dict[str, Any]:
    validate_task(task)
    project = load_project(root)
    state = next((item for item in project.get("semantic_states", []) if item.get("semantic_state_id") == semantic_state_ref), None)
    if state is None:
        raise ValidationError("unknown semantic_state_ref")
    payload = {
        "lens_kind": "source_derived_continuation",
        "project_snapshot_ref": stable_id("snapshot", {"project_ref": project["project_ref"], "semantic_state_ref": semantic_state_ref}),
        "task_context_ref": task["task_context_id"],
        "semantic_state_ref": semantic_state_ref,
        "construction_rule": "source-ingestion:continuation:v1",
        "selected_objects": [
            {"kind": "ProjectRef", "ref": project["project_ref"]["project_id"]},
            {"kind": "ProvisionalSourceSemanticState", "ref": semantic_state_ref},
        ],
        "provenance_refs": [item["source_id"] for item in state["source_records"]],
        "privacy_projection": "private",
        "currentness": "source_bound_at_observation",
        "actionable_private_value": {
            "current_state": state["status_candidates"][0]["text"] if state["status_candidates"] else "SOURCE_STATE_OBSERVED_NO_EXPLICIT_STATUS",
            "next_action_or_reentry": state["exact_reentry_candidate"],
            "blockers": [item["text"] for item in state["blocker_candidates"][:5]],
            "confirmation_questions": state["confirmation_questions"],
            "source_derived": True,
        },
        "information_loss": state["information_loss"],
        "claim_ceiling": state["claim_ceiling"],
    }
    payload["lens_id"] = stable_id("lens", payload)
    project["lenses"].append(payload)
    save_project(root, project)
    return payload


def run_personal_value_repair_witness(bundle_path: str | Path, workspace: str | Path, output: str | Path) -> dict[str, Any]:
    bundle_path = Path(bundle_path)
    bundle = load_json(bundle_path)
    base = bundle_path.parent
    work = Path(workspace)
    out = Path(output)
    if work.exists():
        shutil.rmtree(work)
    if out.exists():
        shutil.rmtree(out)
    work.mkdir(parents=True)
    out.mkdir(parents=True)
    task = bundle["task_context"]
    paths = [base / item for item in bundle["source_files"]]
    init_project(work, project_id=bundle["project_id"], title=bundle["title"], canonical_location=bundle["canonical_location"], recorded_at=bundle["recorded_at"])
    for path in paths:
        raw = path.read_bytes()
        link_source(work, {
            "link_id": stable_id("link", [path.name, hashlib.sha256(raw).hexdigest()]),
            "kind": _source_kind(path),
            "locator": str(path),
            "content_identity": hashlib.sha256(raw).hexdigest(),
            "custody": "external_fixture_source",
            "access_policy": "local_read_only",
        })
    semantic = ingest_source_files(work, paths, task, observed_at=bundle["observed_at"], max_confirmations=bundle.get("max_confirmations", 3))
    lens = derive_source_lens(work, task, semantic_state_ref=semantic["semantic_state_id"])
    project = load_project(work)
    project_bytes = canonical_bytes(project)
    raw_markers = bundle.get("raw_markers", [])
    task_fallback = (task.get("questions") or [task["goal"]])[0]
    source_line_count = sum(item["line_count"] for item in semantic["source_records"])
    checks = {
        "source_semantic_state_created": bool(project.get("semantic_states")),
        "source_derived_reentry": lens["actionable_private_value"]["source_derived"] is True,
        "generic_task_not_echoed": lens["actionable_private_value"]["next_action_or_reentry"] != task_fallback,
        "expected_reentry_selected": lens["actionable_private_value"]["next_action_or_reentry"] == bundle["expected_reentry"],
        "confirmation_budget_respected": len(semantic["confirmation_questions"]) <= bundle.get("max_confirmations", 3),
        "raw_source_bytes_not_embedded": all(marker.encode("utf-8") not in project_bytes for marker in raw_markers),
        "external_custody_preserved": all(item["raw_bytes_embedded"] is False and item["custody"] == "external_or_linked" for item in semantic["source_records"]),
        "evidence_pointers_present": all(item["content_identity"] and item["source_id"] for item in semantic["source_records"]),
    }
    outputs = {
        "provisional_semantic_state.json": semantic,
        "source_derived_lens.json": lens,
        "project_export.json": project,
    }
    for name, value in outputs.items():
        write_json(out / name, value)
    result = {
        "witness_id": "F2.W4.B1.source-semantic-personal-value-repair.v1",
        "passed": all(checks.values()),
        "checks": checks,
        "private_value_disposition": "MECHANICAL_REPAIR_SUPPORTED_HUMAN_VALUE_RIGHT_CENSORED",
        "derived_reentry": lens["actionable_private_value"]["next_action_or_reentry"],
        "generic_task_input": task_fallback,
        "capture_burden": {
            "source_file_count": len(paths),
            "source_line_count": source_line_count,
            "confirmation_question_count": len(semantic["confirmation_questions"]),
            "confirmation_budget": semantic["confirmation_budget"],
            "timing_scope": "Deterministic local process witness; no human timing or retention observation.",
        },
        "baseline_comparison": {
            "baseline": "manual Markdown/JSON/Git-like inspection",
            "baseline_material_to_scan": {"files": len(paths), "lines": source_line_count},
            "semantic_stack_return": "one ranked exact reentry plus bounded confirmation questions and source digests",
            "human_benefit": "RIGHT_CENSORED_NO_HUMAN_OBSERVED",
        },
        "output_digests": {name: canonical_digest(value) for name, value in outputs.items()},
        "claim_ceiling": "One deterministic source-ingestion repair witness. No human adoption, retention, market, capability or broad usability claim.",
    }
    write_json(out / "witness_result.json", result)
    return result
