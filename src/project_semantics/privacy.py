"""Projection privacy, portable exports, and clean-room import checks.

This module is intentionally dependency-free and brand-neutral. It operates on
ordinary JSON-compatible project records and produces derived projections and
receipts without mutating canonical project history.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path, PurePosixPath
import shutil
from typing import Any, Mapping, Sequence

EXPORT_SCHEMA_VERSION = "project-semantics.export.v1"
PROJECTION_SCHEMA_VERSION = "project-semantics.projection.v1"
REFERENCE_SCHEMA_VERSION = "project-semantics.external-ref.v1"
PROJECTION_STATES = {"ACTIVE", "EXPIRED", "REVOKED", "TOMBSTONED"}


class PrivacyValidationError(ValueError):
    """A privacy, currentness, or portability contract failed closed."""


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def canonical_digest(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def _file_digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def validate_json_limits(
    value: Any,
    *,
    max_depth: int = 16,
    max_nodes: int = 20_000,
    max_string_bytes: int = 1_000_000,
) -> None:
    """Reject maliciously deep, wide, or oversized JSON-compatible metadata."""

    nodes = 0

    def visit(item: Any, depth: int) -> None:
        nonlocal nodes
        nodes += 1
        if nodes > max_nodes:
            raise PrivacyValidationError("metadata node limit exceeded")
        if depth > max_depth:
            raise PrivacyValidationError("metadata depth limit exceeded")
        if isinstance(item, str):
            if len(item.encode("utf-8")) > max_string_bytes:
                raise PrivacyValidationError("metadata string size limit exceeded")
        elif isinstance(item, Mapping):
            for key, child in item.items():
                if not isinstance(key, str):
                    raise PrivacyValidationError("metadata object keys must be strings")
                visit(key, depth + 1)
                visit(child, depth + 1)
        elif isinstance(item, Sequence) and not isinstance(item, (str, bytes, bytearray)):
            for child in item:
                visit(child, depth + 1)
        elif item is not None and not isinstance(item, (bool, int, float)):
            raise PrivacyValidationError(f"unsupported metadata type: {type(item).__name__}")

    visit(value, 0)


def validate_external_reference(reference: Mapping[str, Any]) -> None:
    """Require either immutable content identity or explicit mutable currentness."""

    if reference.get("schema_version") != REFERENCE_SCHEMA_VERSION:
        raise PrivacyValidationError("unsupported external reference schema")
    locator = reference.get("locator")
    if not isinstance(locator, str) or not locator.strip() or len(locator) > 4096:
        raise PrivacyValidationError("external reference requires a bounded locator")
    mode = reference.get("identity_mode")
    if mode == "IMMUTABLE_CONTENT":
        digest = reference.get("sha256")
        if not isinstance(digest, str) or len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest):
            raise PrivacyValidationError("immutable external reference requires lowercase sha256")
        if reference.get("mutable_currentness") is not None:
            raise PrivacyValidationError("immutable reference cannot carry mutable currentness")
    elif mode == "MUTABLE_CURRENTNESS":
        currentness = reference.get("mutable_currentness")
        if not isinstance(currentness, Mapping):
            raise PrivacyValidationError("mutable reference requires currentness object")
        for field in ("observed_at", "revision_token", "refresh_policy"):
            if not isinstance(currentness.get(field), str) or not currentness[field].strip():
                raise PrivacyValidationError(f"mutable currentness requires {field}")
        if reference.get("sha256") is not None:
            raise PrivacyValidationError("mutable reference must not masquerade as immutable content")
    else:
        raise PrivacyValidationError("identity_mode must be IMMUTABLE_CONTENT or MUTABLE_CURRENTNESS")


def make_external_reference(
    *,
    locator: str,
    sha256: str | None = None,
    observed_at: str | None = None,
    revision_token: str | None = None,
    refresh_policy: str | None = None,
) -> dict[str, Any]:
    if sha256 is not None:
        value = {
            "schema_version": REFERENCE_SCHEMA_VERSION,
            "locator": locator,
            "identity_mode": "IMMUTABLE_CONTENT",
            "sha256": sha256,
            "mutable_currentness": None,
        }
    else:
        value = {
            "schema_version": REFERENCE_SCHEMA_VERSION,
            "locator": locator,
            "identity_mode": "MUTABLE_CURRENTNESS",
            "sha256": None,
            "mutable_currentness": {
                "observed_at": observed_at or _now(),
                "revision_token": revision_token or "UNBOUND",
                "refresh_policy": refresh_policy or "EXPLICIT_RECHECK",
            },
        }
    validate_external_reference(value)
    return value


@dataclass
class _ProjectionAudit:
    omitted_paths: list[str]
    redacted_paths: list[str]


def _path_text(parts: tuple[str, ...]) -> str:
    return ".".join(parts) if parts else "$"


def _redaction_for(path: str, rules: Mapping[str, Any]) -> tuple[bool, Any]:
    if path in rules:
        replacement = rules[path]
        if isinstance(replacement, Mapping) and replacement.get("action") == "DROP":
            return True, None
        if isinstance(replacement, Mapping) and replacement.get("action") == "REPLACE":
            return False, replacement.get("value", "[REDACTED]")
        return False, replacement
    return False, None


def _project_value(
    value: Any,
    allow: Any,
    rules: Mapping[str, Any],
    audit: _ProjectionAudit,
    path: tuple[str, ...],
) -> Any:
    path_text = _path_text(path)
    drop, replacement = _redaction_for(path_text, rules)
    if drop:
        audit.redacted_paths.append(path_text)
        return _DROP
    if path_text in rules:
        audit.redacted_paths.append(path_text)
        return replacement

    if allow is True:
        # True is allowed only for scalar leaves; whole mappings/lists require an
        # explicit nested shape so private descendants cannot leak accidentally.
        if isinstance(value, (Mapping, list, tuple)):
            raise PrivacyValidationError(f"composite path requires nested allowlist: {path_text}")
        return value
    if isinstance(value, Mapping):
        if not isinstance(allow, Mapping):
            audit.omitted_paths.append(path_text)
            return _DROP
        result: dict[str, Any] = {}
        for key, child in value.items():
            if key not in allow:
                audit.omitted_paths.append(_path_text(path + (str(key),)))
                continue
            projected = _project_value(child, allow[key], rules, audit, path + (str(key),))
            if projected is not _DROP:
                result[str(key)] = projected
        return result
    if isinstance(value, (list, tuple)):
        if not isinstance(allow, Mapping) or "*" not in allow:
            audit.omitted_paths.append(path_text)
            return _DROP
        result_list = []
        for index, child in enumerate(value):
            projected = _project_value(child, allow["*"], rules, audit, path + (str(index),))
            if projected is not _DROP:
                result_list.append(projected)
        return result_list
    audit.omitted_paths.append(path_text)
    return _DROP


_DROP = object()


def create_projection(
    project: Mapping[str, Any],
    policy: Mapping[str, Any],
    *,
    created_at: str | None = None,
) -> dict[str, Any]:
    """Create a recursive allowlist projection without mutating canonical history."""

    validate_json_limits(project)
    if not isinstance(policy.get("policy_id"), str) or not policy["policy_id"].strip():
        raise PrivacyValidationError("projection policy requires policy_id")
    if not isinstance(policy.get("audience"), str) or not policy["audience"].strip():
        raise PrivacyValidationError("projection policy requires audience")
    allowlist = policy.get("allowlist")
    if not isinstance(allowlist, Mapping):
        raise PrivacyValidationError("projection policy requires recursive allowlist")
    rules = policy.get("redactions", {})
    if not isinstance(rules, Mapping):
        raise PrivacyValidationError("redactions must be an object")
    audit = _ProjectionAudit([], [])
    visible = _project_value(project, allowlist, rules, audit, ())
    if visible is _DROP:
        visible = {}
    created = created_at or _now()
    lifecycle = {
        "state": "ACTIVE",
        "created_at": created,
        "expires_at": policy.get("expires_at"),
        "currentness_policy": policy.get("currentness_policy", "EXPLICIT_REFRESH"),
        "revocation": None,
        "tombstone": None,
    }
    payload = {
        "schema_version": PROJECTION_SCHEMA_VERSION,
        "policy_ref": policy["policy_id"],
        "audience": policy["audience"],
        "visible": visible,
        "redacted_paths": sorted(set(audit.redacted_paths)),
        "omitted_paths": sorted(set(audit.omitted_paths)),
        "subject_approval_requirement": policy.get("subject_approval_requirement", "REQUIRED"),
        "lifecycle": lifecycle,
        "canonical_history_mutated": False,
        "claim_ceiling": "Derived selective view only; not canonical history, trust, capability, or admission.",
    }
    payload["projection_id"] = f"projection:{canonical_digest(payload)[:24]}"
    return payload


def transition_projection(
    projection: Mapping[str, Any],
    *,
    action: str,
    actor: str,
    reason: str,
    at: str | None = None,
) -> dict[str, Any]:
    """Return a new lifecycle record; never mutate the input projection."""

    if projection.get("schema_version") != PROJECTION_SCHEMA_VERSION:
        raise PrivacyValidationError("unsupported projection schema")
    if action not in {"EXPIRE", "REVOKE", "TOMBSTONE"}:
        raise PrivacyValidationError("unsupported projection transition")
    if not actor.strip() or not reason.strip():
        raise PrivacyValidationError("projection transition requires actor and reason")
    result = json.loads(json.dumps(projection))
    timestamp = at or _now()
    if action == "EXPIRE":
        result["lifecycle"]["state"] = "EXPIRED"
        result["lifecycle"]["expired_at"] = timestamp
    elif action == "REVOKE":
        result["lifecycle"]["state"] = "REVOKED"
        result["lifecycle"]["revocation"] = {"at": timestamp, "actor": actor, "reason": reason}
    else:
        result["lifecycle"]["state"] = "TOMBSTONED"
        result["lifecycle"]["tombstone"] = {"at": timestamp, "actor": actor, "reason": reason}
        result["visible"] = {}
    result["supersedes_projection_id"] = projection["projection_id"]
    result["projection_id"] = f"projection:{canonical_digest(result)[:24]}"
    result["canonical_history_mutated"] = False
    if result["lifecycle"]["state"] not in PROJECTION_STATES:
        raise PrivacyValidationError("invalid projection lifecycle state")
    return result


def _safe_relative_path(text: str) -> Path:
    posix = PurePosixPath(text)
    if posix.is_absolute() or ".." in posix.parts or not posix.parts:
        raise PrivacyValidationError(f"unsafe bundle path: {text}")
    if any(part in {"", "."} for part in posix.parts):
        raise PrivacyValidationError(f"unsafe bundle path: {text}")
    return Path(*posix.parts)


def export_bundle(
    *,
    project: Mapping[str, Any],
    projections: Sequence[Mapping[str, Any]],
    destination: str | Path,
    migration_disposition: str = "CURRENT_SCHEMA",
    created_at: str | None = None,
) -> dict[str, Any]:
    """Write a deterministic directory bundle and digest manifest."""

    validate_json_limits(project)
    target = Path(destination)
    if target.exists():
        shutil.rmtree(target)
    (target / "payload" / "projections").mkdir(parents=True)
    files: dict[str, Any] = {"payload/project.json": project}
    for projection in projections:
        if projection.get("schema_version") != PROJECTION_SCHEMA_VERSION:
            raise PrivacyValidationError("cannot export unsupported projection schema")
        rel = f"payload/projections/{projection['projection_id'].replace(':', '_')}.json"
        files[rel] = projection
    entries = []
    for rel, payload in sorted(files.items()):
        path = target / _safe_relative_path(rel)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(canonical_bytes(payload) + b"\n")
        entries.append({"path": rel, "sha256": _file_digest(path), "size": path.stat().st_size})
    manifest = {
        "schema_version": EXPORT_SCHEMA_VERSION,
        "created_at": created_at or _now(),
        "migration_disposition": migration_disposition,
        "project_schema_version": project.get("schema_version"),
        "projection_schema_version": PROJECTION_SCHEMA_VERSION,
        "files": entries,
        "limits": {"max_files": 512, "max_total_bytes": 50_000_000, "max_json_depth": 16},
        "claim_ceiling": "Portable local export only; not hosted admission or proof of source truth.",
    }
    manifest["bundle_digest"] = canonical_digest({"files": entries, "migration_disposition": migration_disposition})
    manifest_path = target / "MANIFEST.json"
    manifest_path.write_bytes(canonical_bytes(manifest) + b"\n")
    return manifest


def verify_bundle(
    source: str | Path,
    *,
    max_files: int = 512,
    max_total_bytes: int = 50_000_000,
    max_json_depth: int = 16,
) -> dict[str, Any]:
    root = Path(source)
    manifest_path = root / "MANIFEST.json"
    if not manifest_path.is_file():
        raise PrivacyValidationError("bundle manifest missing")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("schema_version") != EXPORT_SCHEMA_VERSION:
        raise PrivacyValidationError("unsupported export schema")
    files = manifest.get("files")
    if not isinstance(files, list) or len(files) > max_files:
        raise PrivacyValidationError("bundle file count limit exceeded")
    total = 0
    verified = []
    for item in files:
        if not isinstance(item, Mapping):
            raise PrivacyValidationError("manifest file entry must be an object")
        rel = _safe_relative_path(str(item.get("path", "")))
        path = root / rel
        if path.is_symlink() or not path.is_file():
            raise PrivacyValidationError(f"bundle file missing or unsafe: {rel.as_posix()}")
        total += path.stat().st_size
        if total > max_total_bytes:
            raise PrivacyValidationError("bundle total size limit exceeded")
        if path.stat().st_size != item.get("size") or _file_digest(path) != item.get("sha256"):
            raise PrivacyValidationError(f"bundle digest mismatch: {rel.as_posix()}")
        payload = json.loads(path.read_text(encoding="utf-8"))
        validate_json_limits(payload, max_depth=max_json_depth)
        verified.append(rel.as_posix())
    expected = canonical_digest({"files": files, "migration_disposition": manifest.get("migration_disposition")})
    if expected != manifest.get("bundle_digest"):
        raise PrivacyValidationError("bundle manifest digest mismatch")
    return {
        "schema_version": "project-semantics.bundle-verification.v1",
        "bundle_digest": expected,
        "verified_files": verified,
        "total_bytes": total,
        "migration_disposition": manifest.get("migration_disposition"),
        "result": "PASS",
    }


def import_bundle(
    source: str | Path,
    destination: str | Path,
    *,
    max_files: int = 512,
    max_total_bytes: int = 50_000_000,
    max_json_depth: int = 16,
) -> dict[str, Any]:
    """Verify and copy a bundle into a fresh local destination."""

    verification = verify_bundle(
        source,
        max_files=max_files,
        max_total_bytes=max_total_bytes,
        max_json_depth=max_json_depth,
    )
    source_root = Path(source)
    target = Path(destination)
    if target.exists() and any(target.iterdir()):
        raise PrivacyValidationError("clean-room import destination must be empty")
    target.mkdir(parents=True, exist_ok=True)
    manifest = json.loads((source_root / "MANIFEST.json").read_text(encoding="utf-8"))
    for item in manifest["files"]:
        rel = _safe_relative_path(item["path"])
        destination_path = target / rel
        destination_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source_root / rel, destination_path)
    shutil.copyfile(source_root / "MANIFEST.json", target / "MANIFEST.json")
    second = verify_bundle(
        target,
        max_files=max_files,
        max_total_bytes=max_total_bytes,
        max_json_depth=max_json_depth,
    )
    if verification["bundle_digest"] != second["bundle_digest"]:
        raise PrivacyValidationError("clean-room import changed bundle identity")
    return {
        "schema_version": "project-semantics.import-receipt.v1",
        "source_bundle_digest": verification["bundle_digest"],
        "imported_bundle_digest": second["bundle_digest"],
        "migration_disposition": second["migration_disposition"],
        "clean_room": True,
        "result": "PASS",
        "claim_ceiling": "Verified local import only; not canonical source admission.",
    }
