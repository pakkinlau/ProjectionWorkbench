"""Source-semantic ingestion with currentness, privacy, refresh, and deduplication.

F2.W6.B3 repairs the exact generalization failures identified by F2.W5.B5.
Raw source bytes remain externally authoritative; the module stores bounded,
source-derived semantic state and explicit refresh receipts.
"""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import re
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
_SENSITIVE_TOKENS = {
    "password", "passwd", "secret", "api_key", "apikey", "access_token",
    "auth_token", "credential", "credentials", "private_key", "raw_private",
}
_ARCHIVED_TOKENS = {"archive", "archived", "deprecated", "obsolete", "historical", "example", "examples", "legacy"}
_CURRENTNESS_RANK = {"CURRENT": 4, "UNKNOWN": 3, "STALE": 2, "SUPERSEDED": 1, "ARCHIVED": 0, "MISSING": -1, "CHANGED": -1}
_GIT_BRANCH_RE = re.compile(r"^##\s+(?P<branch>.+?)(?:\.\.\.(?P<upstream>[^\s]+))?(?:\s+\[(?P<tracking>[^\]]+)\])?$")
_GIT_TRACK_RE = re.compile(r"(?:(ahead)\s+(\d+))|(?:(behind)\s+(\d+))")


def _iso(value: str | None, fallback: str) -> str:
    if not value:
        return fallback
    try:
        datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValidationError(f"invalid ISO currentness timestamp: {value}") from exc
    return value


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


def _sensitive(text: str) -> bool:
    lowered = text.casefold()
    return any(token in lowered for token in _SENSITIVE_TOKENS)


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


def _validate_semantic_envelope(value: Any, prefix: str = "") -> None:
    """Fail closed on reserved semantic fields with unsupported shapes."""
    if isinstance(value, Mapping):
        for key, child in value.items():
            path = f"{prefix}.{key}" if prefix else str(key)
            leaf = str(key).casefold()
            if leaf in _ACTION_KEYS | _STATUS_KEYS and not isinstance(child, (str, int, float, bool)):
                raise ValidationError(f"unsupported semantic envelope at {path}: scalar required")
            if leaf in _BLOCKER_KEYS:
                if isinstance(child, list) and not all(isinstance(item, (str, int, float)) for item in child):
                    raise ValidationError(f"unsupported semantic envelope at {path}: scalar list required")
                if not isinstance(child, (str, int, float, list)):
                    raise ValidationError(f"unsupported semantic envelope at {path}: scalar or scalar list required")
            _validate_semantic_envelope(child, path)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _validate_semantic_envelope(child, f"{prefix}[{index}]")


def _candidate(
    text: str,
    *,
    score: int,
    source_ref: str,
    line: int | None,
    kind: str,
    source_currentness: str = "UNKNOWN",
    source_observed_at: str = "",
    context_state: str = "CURRENT",
    metadata: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    compact = " ".join(text.strip().split())
    eligible = source_currentness not in {"STALE", "SUPERSEDED", "ARCHIVED", "MISSING", "CHANGED"} and context_state != "ARCHIVED"
    return {
        "text": compact[:500],
        "score": score,
        "source_ref": source_ref,
        "line": line,
        "kind": kind,
        "source_currentness": source_currentness,
        "source_observed_at": source_observed_at,
        "context_state": context_state,
        "eligible_for_reentry": eligible,
        "metadata": dict(metadata or {}),
    }


def _extract_json_semantics(
    value: Any,
    source_ref: str,
    *,
    source_currentness: str,
    source_observed_at: str,
) -> dict[str, list[dict[str, Any]]]:
    _validate_semantic_envelope(value)
    result = {"actions": [], "blockers": [], "statuses": [], "claims": []}
    for key_path, item in _flatten_json(value):
        leaf = key_path.rsplit(".", 1)[-1].split("[")[0].casefold()
        if _sensitive(key_path) or (isinstance(item, str) and _sensitive(item)):
            continue
        if isinstance(item, (str, int, float, bool)):
            text = str(item)
            if leaf in _ACTION_KEYS and text.strip():
                result["actions"].append(_candidate(text, score=100, source_ref=source_ref, line=None, kind="explicit_json_action", source_currentness=source_currentness, source_observed_at=source_observed_at))
            elif leaf in _STATUS_KEYS and text.strip():
                result["statuses"].append(_candidate(text, score=85, source_ref=source_ref, line=None, kind="json_status", source_currentness=source_currentness, source_observed_at=source_observed_at))
            elif any(token in key_path.casefold() for token in ("claim", "supported", "contradicted")) and text.strip():
                result["claims"].append(_candidate(f"{key_path}: {text}", score=60, source_ref=source_ref, line=None, kind="json_claim", source_currentness=source_currentness, source_observed_at=source_observed_at))
        if leaf in _BLOCKER_KEYS:
            if isinstance(item, list):
                for part in item:
                    if isinstance(part, (str, int, float)) and not _sensitive(str(part)):
                        result["blockers"].append(_candidate(str(part), score=80, source_ref=source_ref, line=None, kind="json_blocker", source_currentness=source_currentness, source_observed_at=source_observed_at))
            elif isinstance(item, str) and not _sensitive(item):
                result["blockers"].append(_candidate(item, score=80, source_ref=source_ref, line=None, kind="json_blocker", source_currentness=source_currentness, source_observed_at=source_observed_at))
    return result


def _heading_archived(stack: list[tuple[int, str]]) -> bool:
    return any(any(token in text for token in _ARCHIVED_TOKENS) for _, text in stack)


def _extract_text_semantics(
    text: str,
    source_ref: str,
    *,
    git_like: bool = False,
    source_currentness: str,
    source_observed_at: str,
) -> dict[str, list[dict[str, Any]]]:
    result = {"actions": [], "blockers": [], "statuses": [], "claims": []}
    headings: list[tuple[int, str]] = []
    for number, raw_line in enumerate(text.splitlines(), 1):
        line = raw_line.strip()
        if not line:
            continue
        lower = line.casefold()
        if _sensitive(line):
            continue

        if git_like:
            match = _GIT_BRANCH_RE.match(line)
            if match:
                ahead = behind = 0
                tracking = match.group("tracking") or ""
                for item in _GIT_TRACK_RE.finditer(tracking):
                    if item.group(1) == "ahead":
                        ahead = int(item.group(2))
                    elif item.group(3) == "behind":
                        behind = int(item.group(4))
                metadata = {"branch": match.group("branch"), "upstream": match.group("upstream"), "ahead": ahead, "behind": behind}
                result["statuses"].append(_candidate(line, score=90, source_ref=source_ref, line=number, kind="git_porcelain_branch", source_currentness=source_currentness, source_observed_at=source_observed_at, metadata=metadata))
                continue
            if lower.startswith(("on branch ", "branch ")):
                result["statuses"].append(_candidate(line, score=75, source_ref=source_ref, line=number, kind="git_status", source_currentness=source_currentness, source_observed_at=source_observed_at))
                continue
            porcelain = raw_line[:2]
            if porcelain in {" M", "M ", "MM", "A ", " A", "D ", " D", "R ", " R", "??"} or lower.startswith(("modified:", "new file:", "deleted:")):
                result["blockers"].append(_candidate(f"Unreviewed working-tree change: {line}", score=55, source_ref=source_ref, line=number, kind="git_dirty_state", source_currentness=source_currentness, source_observed_at=source_observed_at, metadata={"porcelain": porcelain.strip() or porcelain}))
                continue
            continue

        if line.startswith("#"):
            level = len(line) - len(line.lstrip("#"))
            heading = line[level:].strip().casefold()
            headings = [(old_level, old_text) for old_level, old_text in headings if old_level < level]
            headings.append((level, heading))
            continue

        heading_text = " / ".join(item[1] for item in headings)
        context_state = "ARCHIVED" if _heading_archived(headings) else "CURRENT"
        clean = line.lstrip("-*+[] xX0123456789.).\t").strip()
        if any(token in heading_text for token in ("next", "reentry", "action", "todo")) and clean:
            result["actions"].append(_candidate(clean, score=90, source_ref=source_ref, line=number, kind="markdown_next_action", source_currentness=source_currentness, source_observed_at=source_observed_at, context_state=context_state, metadata={"heading_ancestry": [text for _, text in headings]}))
        elif line.startswith("- [ ]"):
            result["actions"].append(_candidate(clean, score=75, source_ref=source_ref, line=number, kind="unchecked_task", source_currentness=source_currentness, source_observed_at=source_observed_at, context_state=context_state, metadata={"heading_ancestry": [text for _, text in headings]}))
        if any(token in heading_text for token in ("blocker", "missing", "hold", "unresolved", "first zero")) and clean:
            result["blockers"].append(_candidate(clean, score=75, source_ref=source_ref, line=number, kind="markdown_blocker", source_currentness=source_currentness, source_observed_at=source_observed_at, context_state=context_state))
        elif any(token in lower for token in ("blocked", "missing operand", "unresolved", "right-censored", "right_censored")):
            result["blockers"].append(_candidate(clean, score=60, source_ref=source_ref, line=number, kind="text_blocker", source_currentness=source_currentness, source_observed_at=source_observed_at, context_state=context_state))
        if any(token in heading_text for token in ("status", "state", "verdict", "disposition")) and clean:
            result["statuses"].append(_candidate(clean, score=70, source_ref=source_ref, line=number, kind="markdown_status", source_currentness=source_currentness, source_observed_at=source_observed_at, context_state=context_state))
        if any(token in heading_text for token in ("claim", "supported", "contradicted")) and clean:
            result["claims"].append(_candidate(clean, score=55, source_ref=source_ref, line=number, kind="markdown_claim", source_currentness=source_currentness, source_observed_at=source_observed_at, context_state=context_state))
    return result


def _metadata_for(path: Path, metadata: Mapping[str, Mapping[str, Any]] | None, default_observed_at: str) -> dict[str, Any]:
    raw = dict((metadata or {}).get(str(path), (metadata or {}).get(path.name, {})))
    currentness = str(raw.get("currentness", "CURRENT")).upper()
    if currentness not in _CURRENTNESS_RANK:
        raise ValidationError(f"unsupported source currentness: {currentness}")
    observed_at = _iso(raw.get("observed_at"), default_observed_at)
    supersedes = list(raw.get("supersedes", []))
    return {"currentness": currentness, "observed_at": observed_at, "supersedes": supersedes}


def _observed_epoch(value: str) -> float:
    if not value:
        return 0.0
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp()
    except ValueError:
        return 0.0


def _candidate_sort_key(item: Mapping[str, Any]) -> tuple[Any, ...]:
    return (
        -int(bool(item.get("eligible_for_reentry"))),
        -_CURRENTNESS_RANK.get(str(item.get("source_currentness", "UNKNOWN")), 0),
        -int(item.get("score", 0)),
        -_observed_epoch(str(item.get("source_observed_at", ""))),
        str(item.get("text", "")),
        str(item.get("source_ref", "")),
    )


def ingest_source_files(
    root: str | Path,
    source_paths: Iterable[str | Path],
    task: Mapping[str, Any],
    *,
    observed_at: str | None = None,
    max_confirmations: int = 3,
    source_metadata: Mapping[str, Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    """Derive provisional semantic state while keeping raw bytes external."""
    validate_task(task)
    if max_confirmations < 0 or max_confirmations > 10:
        raise ValidationError("max_confirmations must be between 0 and 10")
    observed = observed_at or _now()
    project = load_project(root)
    records_by_content: dict[str, dict[str, Any]] = {}
    aggregate = {"actions": [], "blockers": [], "statuses": [], "claims": []}

    for supplied in source_paths:
        path = Path(supplied)
        if not path.is_file():
            raise ValidationError(f"source not found: {path}")
        text, raw = _bounded_text(path)
        kind = _source_kind(path)
        content_identity = hashlib.sha256(raw).hexdigest()
        source_id = stable_id("source", content_identity)
        meta = _metadata_for(path, source_metadata, observed)
        if content_identity in records_by_content:
            records_by_content[content_identity]["alias_locators"].append(str(path))
            records_by_content[content_identity]["alias_count"] += 1
            continue
        record = {
            "source_id": source_id,
            "locator": str(path),
            "locator_display": path.name,
            "alias_locators": [],
            "alias_count": 0,
            "kind": kind,
            "content_identity": content_identity,
            "size_bytes": len(raw),
            "line_count": len(text.splitlines()),
            "custody": "external_or_linked",
            "raw_bytes_embedded": False,
            "currentness": meta,
        }
        records_by_content[content_identity] = record
        if kind == "json":
            try:
                parsed = json.loads(text, parse_constant=lambda token: (_ for _ in ()).throw(ValidationError(f"non-finite JSON constant: {token}")))
            except json.JSONDecodeError as exc:
                raise ValidationError(f"invalid JSON source {path}: {exc}") from exc
            extracted = _extract_json_semantics(parsed, source_id, source_currentness=meta["currentness"], source_observed_at=meta["observed_at"])
        else:
            extracted = _extract_text_semantics(text, source_id, git_like=kind == "git_like", source_currentness=meta["currentness"], source_observed_at=meta["observed_at"])
        for key in aggregate:
            aggregate[key].extend(extracted[key])

    records = sorted(records_by_content.values(), key=lambda item: (item["content_identity"], item["locator"]))
    superseded_ids = {item for record in records for item in record["currentness"].get("supersedes", [])}
    superseded_source_refs: set[str] = set()
    for record in records:
        if record["source_id"] in superseded_ids or record["content_identity"] in superseded_ids:
            record["currentness"]["currentness"] = "SUPERSEDED"
            superseded_source_refs.add(record["source_id"])
    if superseded_source_refs:
        for candidates in aggregate.values():
            for candidate in candidates:
                if candidate["source_ref"] in superseded_source_refs:
                    candidate["source_currentness"] = "SUPERSEDED"
                    candidate["eligible_for_reentry"] = False
    for key in aggregate:
        aggregate[key] = sorted(aggregate[key], key=_candidate_sort_key)

    task_fallback = (task.get("questions") or [task["goal"]])[0]
    eligible_actions = [item for item in aggregate["actions"] if item["eligible_for_reentry"]]
    exact_reentry = eligible_actions[0]["text"] if eligible_actions else task_fallback
    confidence = "HIGH" if eligible_actions and eligible_actions[0]["score"] >= 90 else "MEDIUM" if eligible_actions else "LOW"
    questions: list[str] = []
    if len(eligible_actions) > 1 and eligible_actions[0]["text"] != eligible_actions[1]["text"]:
        questions.append(f"Confirm the priority between: '{eligible_actions[0]['text']}' and '{eligible_actions[1]['text']}'.")
    eligible_blockers = [item for item in aggregate["blockers"] if item["eligible_for_reentry"]]
    if eligible_blockers:
        questions.append(f"Confirm whether the leading blocker is still active: '{eligible_blockers[0]['text']}'.")
    if confidence == "LOW":
        questions.append("No current explicit source-derived reentry was found; confirm the proposed task fallback.")
    questions = questions[:max_confirmations]

    payload = {
        "semantic_state_kind": "ProvisionalSourceSemanticState",
        "project_ref": project["project_ref"]["project_id"],
        "task_context_ref": task["task_context_id"],
        "observed_at": observed,
        "source_records": records,
        "source_alias_count": sum(item["alias_count"] for item in records),
        "status_candidates": aggregate["statuses"][:10],
        "action_candidates": aggregate["actions"][:10],
        "blocker_candidates": aggregate["blockers"][:10],
        "claim_candidates": aggregate["claims"][:10],
        "exact_reentry_candidate": exact_reentry,
        "reentry_confidence": confidence,
        "confirmation_questions": questions,
        "confirmation_budget": max_confirmations,
        "currentness_disposition": "CURRENT",
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


def refresh_source_records(
    root: str | Path,
    *,
    semantic_state_ref: str,
    observed_at: str | None = None,
) -> dict[str, Any]:
    """Compare linked locators with the stored content identity and mark staleness."""
    project = load_project(root)
    state = next((item for item in project.get("semantic_states", []) if item.get("semantic_state_id") == semantic_state_ref), None)
    if state is None:
        raise ValidationError("unknown semantic_state_ref")
    results = []
    stale = False
    for record in state["source_records"]:
        locators = [record["locator"], *record.get("alias_locators", [])]
        available = []
        for locator in locators:
            path = Path(locator)
            if path.is_file():
                available.append((locator, hashlib.sha256(path.read_bytes()).hexdigest()))
        if not available:
            disposition = "SOURCE_MISSING"
            stale = True
        elif any(digest == record["content_identity"] for _, digest in available):
            disposition = "SOURCE_CURRENT"
        else:
            disposition = "SOURCE_CHANGED"
            stale = True
        results.append({"source_id": record["source_id"], "content_identity": record["content_identity"], "locators": locators, "available": available, "disposition": disposition})
    state["currentness_disposition"] = "STALE_REFRESH_REQUIRED" if stale else "CURRENT"
    receipt = {
        "receipt_kind": "SourceRefreshReceipt",
        "semantic_state_ref": semantic_state_ref,
        "observed_at": observed_at or _now(),
        "results": results,
        "disposition": state["currentness_disposition"],
        "claim_ceiling": "Source availability/currentness comparison only; does not establish semantic truth.",
    }
    receipt["receipt_id"] = stable_id("source-refresh", receipt)
    project.setdefault("source_refresh_receipts", []).append(receipt)
    save_project(root, project)
    return receipt


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
        "construction_rule": "source-ingestion:continuation:v2",
        "selected_objects": [
            {"kind": "ProjectRef", "ref": project["project_ref"]["project_id"]},
            {"kind": "ProvisionalSourceSemanticState", "ref": semantic_state_ref},
        ],
        "provenance_refs": [item["source_id"] for item in state["source_records"]],
        "privacy_projection": "private",
        "currentness": state.get("currentness_disposition", "CURRENT"),
        "actionable_private_value": {
            "current_state": state["status_candidates"][0]["text"] if state["status_candidates"] else "SOURCE_STATE_OBSERVED_NO_EXPLICIT_STATUS",
            "next_action_or_reentry": state["exact_reentry_candidate"],
            "blockers": [item["text"] for item in state["blocker_candidates"][:5] if item.get("eligible_for_reentry")],
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
    outputs = {"provisional_semantic_state.json": semantic, "source_derived_lens.json": lens, "project_export.json": project}
    for name, value in outputs.items():
        write_json(out / name, value)
    result = {
        "witness_id": "F2.W4.B1.source-semantic-personal-value-repair.v1",
        "checks": checks,
        "passed": all(checks.values()),
        "source_line_count": source_line_count,
        "capture_burden": {"source_count": len(paths), "manual_semantic_fields_entered": 0, "confirmation_question_count": len(semantic["confirmation_questions"]), "confirmation_budget": bundle.get("max_confirmations", 3)},
        "generic_task_input": task_fallback,
        "derived_reentry": lens["actionable_private_value"]["next_action_or_reentry"],
        "output_digests": {name: canonical_digest(value) for name, value in outputs.items()},
        "claim_ceiling": "Mechanical source-to-semantic and exact-reentry witness only; no human timing, retention, usefulness, intent, capability or product-demand claim.",
    }
    write_json(out / "witness_result.json", result)
    return result
