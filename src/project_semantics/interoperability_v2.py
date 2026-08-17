"""Versioned ViewMappingReceipt and exchange-waist repair.

This module is brand-neutral and dependency-free. It keeps native view mappings,
schema migration records, privacy export manifests, and exchange manifests as
separate typed objects connected only by explicit adapters/bridges.
"""
from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from pathlib import Path, PurePosixPath
from typing import Any, Mapping, Sequence

NATIVE_MAPPING_V1 = "project-semantics.view-mapping-receipt.v1"
CANONICAL_MAPPING_V2 = "project-semantics.view-mapping-receipt.v2"
EXCHANGE_BUNDLE_V1 = "project-semantics.exchange-bundle.v1"
EXCHANGE_MANIFEST_V2 = "project-semantics.exchange-manifest.v2"
PRIVACY_EXPORT_V1 = "project-semantics.export.v1"
BRIDGE_V1 = "project-semantics.exchange-waist-bridge.v1"
MAPPING_KINDS = {"RESTRICTION", "PROJECTION", "TRANSLATION", "ALIGNMENT", "ADAPTER", "COMPOSITION", "ATTESTATION"}
MAPPING_DISPOSITIONS = {"IDENTITY_MAPPING", "PARTIAL_MAPPING_WITH_DECLARED_LOSS", "NO_SAFE_GLOBALIZATION", "NON_IDENTIFIABLE", "GRAMMAR_INSUFFICIENT"}
RECORD_KINDS = {"WorkModuleManifest", "ConnectorManifest", "ViewMappingReceipt", "ContributionRecord", "EvidenceScope", "Attestation", "CompositionReceipt"}
ID_FIELDS = ("module_id", "connector_id", "mapping_receipt_id", "contribution_id", "evidence_scope_id", "attestation_id", "receipt_id")


class InteroperabilityV2Error(ValueError):
    """A mapping or exchange-waist contract failed closed."""


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")


def digest(value: Any) -> str:
    return "sha256:" + hashlib.sha256(canonical_bytes(value)).hexdigest()


def _require(record: Mapping[str, Any], *fields: str) -> None:
    missing = [field for field in fields if field not in record]
    if missing:
        raise InteroperabilityV2Error("missing required fields: " + ", ".join(missing))


def _require_text(record: Mapping[str, Any], *fields: str) -> None:
    _require(record, *fields)
    bad = [field for field in fields if not isinstance(record[field], str) or not record[field].strip()]
    if bad:
        raise InteroperabilityV2Error("requires non-empty text: " + ", ".join(bad))


def record_identity(payload: Mapping[str, Any]) -> str:
    aliases = [str(payload[field]) for field in ("mapping_receipt_id", "mapping_id") if payload.get(field)]
    if len(set(aliases)) > 1:
        raise InteroperabilityV2Error("mapping identity aliases conflict")
    if aliases:
        return aliases[0]
    for field in ID_FIELDS:
        if payload.get(field):
            return str(payload[field])
    raise InteroperabilityV2Error("record has no stable identity")


def validate_mapping_v2(payload: Mapping[str, Any]) -> None:
    _require_text(
        payload,
        "schema_version",
        "mapping_receipt_id",
        "mapping_kind",
        "source_lens_ref",
        "target_lens_ref",
        "disposition",
        "claim_ceiling",
        "currentness",
    )
    if payload["schema_version"] != CANONICAL_MAPPING_V2:
        raise InteroperabilityV2Error("unsupported canonical mapping schema")
    if payload["mapping_kind"] not in MAPPING_KINDS:
        raise InteroperabilityV2Error("unsupported mapping kind")
    if payload["disposition"] not in MAPPING_DISPOSITIONS:
        raise InteroperabilityV2Error("unsupported mapping disposition")
    if payload.get("mapping_id") not in (None, payload["mapping_receipt_id"]):
        raise InteroperabilityV2Error("mapping identity alias mismatch")
    _require(payload, "shared_object_refs", "source_local_refinements", "target_local_refinements", "semantic_correspondences", "information_loss", "obstruction", "provenance_refs")
    if payload["disposition"] == "PARTIAL_MAPPING_WITH_DECLARED_LOSS" and not payload["information_loss"]:
        raise InteroperabilityV2Error("partial mapping requires declared information loss")


def adapt_native_view_mapping(
    payload: Mapping[str, Any],
    *,
    mapping_kind: str,
    claim_ceiling: str,
    currentness: str,
    provenance_refs: Sequence[str],
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Convert a PR11-native mapping to the migration envelope explicitly.

    The adapter does not infer missing semantic authority. Callers must supply
    mapping kind, claim ceiling, currentness and provenance.
    """
    if payload.get("schema_version") != NATIVE_MAPPING_V1:
        raise InteroperabilityV2Error("adapter requires native mapping v1")
    _require_text(payload, "source_lens_ref", "target_lens_ref", "disposition")
    if mapping_kind not in MAPPING_KINDS:
        raise InteroperabilityV2Error("adapter requires supported mapping kind")
    if not claim_ceiling.strip() or not currentness.strip() or not provenance_refs:
        raise InteroperabilityV2Error("adapter requires claim ceiling, currentness and provenance")
    stable = record_identity(payload)
    out = {
        "schema_version": CANONICAL_MAPPING_V2,
        "mapping_receipt_id": stable,
        "mapping_id": stable,
        "mapping_kind": mapping_kind,
        "source_lens_ref": payload["source_lens_ref"],
        "target_lens_ref": payload["target_lens_ref"],
        "disposition": payload["disposition"],
        "shared_object_refs": deepcopy(payload.get("shared_object_refs", payload.get("shared_refs", []))),
        "source_local_refinements": deepcopy(payload.get("source_local_refinements", [])),
        "target_local_refinements": deepcopy(payload.get("target_local_refinements", [])),
        "semantic_correspondences": deepcopy(payload.get("semantic_correspondences", [])),
        "information_loss": deepcopy(payload.get("information_loss", [])),
        "obstruction": deepcopy(payload.get("obstruction")),
        "claim_ceiling": claim_ceiling,
        "currentness": currentness,
        "provenance_refs": list(provenance_refs),
        "source_schema_version": NATIVE_MAPPING_V1,
        "adapter_version": "native-view-mapping-to-exchange.v1",
    }
    validate_mapping_v2(out)
    receipt = {
        "schema_version": "project-semantics.view-mapping-adapter-receipt.v1",
        "adapter_version": out["adapter_version"],
        "source_identity": stable,
        "target_identity": stable,
        "source_schema_version": NATIVE_MAPPING_V1,
        "target_schema_version": CANONICAL_MAPPING_V2,
        "identity_preserved": True,
        "information_loss": [],
        "canonical_source_mutated": False,
        "claim_ceiling": "Adapter mechanics only; not semantic equivalence or admission.",
    }
    receipt["receipt_id"] = digest(receipt)
    return out, receipt


def validate_exchange_bundle(bundle: Mapping[str, Any]) -> dict[str, Any]:
    _require(bundle, "schema_version", "bundle_id", "records", "provenance")
    if bundle["schema_version"] != EXCHANGE_BUNDLE_V1:
        raise InteroperabilityV2Error("unsupported exchange bundle schema")
    if not isinstance(bundle["records"], list) or not bundle["records"]:
        raise InteroperabilityV2Error("exchange bundle requires records")
    ids: set[str] = set()
    modules: dict[str, Mapping[str, Any]] = {}
    connectors: list[Mapping[str, Any]] = []
    scopes: set[str] = set()
    attestations: list[Mapping[str, Any]] = []
    checks: dict[str, bool] = {}
    for record in bundle["records"]:
        _require(record, "kind", "payload")
        if record["kind"] not in RECORD_KINDS:
            raise InteroperabilityV2Error("unsupported record kind")
        ident = record_identity(record["payload"])
        if ident in ids:
            raise InteroperabilityV2Error("duplicate record identity")
        ids.add(ident)
        if record["kind"] == "ViewMappingReceipt":
            validate_mapping_v2(record["payload"])
            checks[f"mapping:{ident}:conformant"] = True
        elif record["kind"] == "WorkModuleManifest":
            modules[ident] = record["payload"]
        elif record["kind"] == "ConnectorManifest":
            connectors.append(record["payload"])
        elif record["kind"] == "EvidenceScope":
            scopes.add(ident)
        elif record["kind"] == "Attestation":
            attestations.append(record["payload"])
    for connector in connectors:
        _require(connector, "connector_id", "source_type", "target_type", "accepted_source_versions", "accepted_target_versions", "semantic_mapping", "evidence_continuity", "attribution_policy")
        source = [module for module in modules.values() if connector["source_type"] in {port.get("type") for port in module.get("outputs", [])}]
        target = [module for module in modules.values() if connector["target_type"] in {port.get("type") for port in module.get("inputs", [])}]
        ok = bool(source and target)
        ok = ok and any(module.get("version") in connector["accepted_source_versions"] for module in source)
        ok = ok and any(module.get("version") in connector["accepted_target_versions"] for module in target)
        ok = ok and bool(connector["semantic_mapping"].get("correspondences"))
        ok = ok and bool(connector["semantic_mapping"].get("preserved_invariants"))
        ok = ok and connector["evidence_continuity"].get("preserve_source_refs") is True
        ok = ok and connector["attribution_policy"].get("preserve_lineage") is True
        checks[f"connector:{connector['connector_id']}:conformant"] = ok
    for attestation in attestations:
        bound = all(ref in scopes for ref in attestation.get("evidence_scope_refs", []))
        checks[f"attestation:{attestation.get('attestation_id')}:scope_bound"] = bound
    disposition = "INTEROPERABLE" if checks and all(checks.values()) else "INCOMPATIBLE"
    return {"checks": checks, "disposition": disposition}


def migrate_native_bundle(
    native_bundle: Mapping[str, Any],
    *,
    mapping_policies: Mapping[str, Mapping[str, Any]],
) -> tuple[dict[str, Any], dict[str, Any]]:
    _require(native_bundle, "bundle_id", "records", "provenance")
    records = []
    adapter_receipts = []
    for record in native_bundle["records"]:
        kind = record["kind"]
        payload = deepcopy(record["payload"])
        if kind == "ViewMappingReceipt":
            stable = record_identity(payload)
            policy = mapping_policies.get(stable)
            if policy is None:
                raise InteroperabilityV2Error("native mapping requires explicit adapter policy")
            payload, receipt = adapt_native_view_mapping(payload, **policy)
            adapter_receipts.append(receipt)
        records.append({"kind": kind, "payload": payload})
    out = {
        "schema_version": EXCHANGE_BUNDLE_V1,
        "bundle_id": native_bundle["bundle_id"],
        "records": records,
        "provenance": deepcopy(native_bundle["provenance"]),
        "migration": {
            "source_schema_version": native_bundle.get("schema_version"),
            "target_schema_version": EXCHANGE_BUNDLE_V1,
            "mapping_adapters": adapter_receipts,
            "canonical_source_mutated": False,
        },
    }
    out["bundle_digest"] = digest({k: v for k, v in out.items() if k != "bundle_digest"})
    revalidation = validate_exchange_bundle(out)
    receipt = {
        "schema_version": "project-semantics.native-exchange-migration-receipt.v1",
        "source_bundle_digest": digest(native_bundle),
        "target_bundle_digest": out["bundle_digest"],
        "mapping_adapter_receipts": adapter_receipts,
        "provenance_preserved": out["provenance"] == native_bundle["provenance"],
        "canonical_source_mutated": False,
        "revalidation": revalidation,
        "disposition": "MIGRATED_LOSSLESSLY" if revalidation["disposition"] == "INTEROPERABLE" else "MIGRATED_BUT_INCOMPATIBLE",
        "claim_ceiling": "Local migration/exchange mechanics only.",
    }
    receipt["receipt_id"] = digest(receipt)
    return out, receipt


def _safe_relative_path(text: str) -> Path:
    path = PurePosixPath(text)
    if path.is_absolute() or ".." in path.parts or not path.parts:
        raise InteroperabilityV2Error("unsafe exchange path")
    return Path(*path.parts)


def export_exchange_bundle(bundle: Mapping[str, Any], root: str | Path) -> dict[str, Any]:
    if validate_exchange_bundle(bundle)["disposition"] != "INTEROPERABLE":
        raise InteroperabilityV2Error("only interoperable bundles can be exported")
    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)
    data = canonical_bytes(bundle) + b"\n"
    (root / "exchange_bundle.json").write_bytes(data)
    manifest = {
        "schema_version": EXCHANGE_MANIFEST_V2,
        "manifest_role": "SEMANTIC_EXCHANGE",
        "files": [{"path": "exchange_bundle.json", "sha256": "sha256:" + hashlib.sha256(data).hexdigest(), "size": len(data)}],
        "bundle_digest": bundle["bundle_digest"],
        "security_currentness_policy": {"require_current_mapping": True, "reject_unmanifested_files": True},
        "canonical_source_mutated": False,
    }
    manifest["manifest_digest"] = digest({k: v for k, v in manifest.items() if k != "manifest_digest"})
    (root / "manifest.json").write_bytes(canonical_bytes(manifest) + b"\n")
    return manifest


def import_exchange_bundle(root: str | Path) -> tuple[dict[str, Any], dict[str, Any]]:
    root = Path(root)
    manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    if manifest.get("schema_version") != EXCHANGE_MANIFEST_V2 or manifest.get("manifest_role") != "SEMANTIC_EXCHANGE":
        raise InteroperabilityV2Error("not an exchange manifest")
    expected_manifest = digest({k: v for k, v in manifest.items() if k != "manifest_digest"})
    if manifest.get("manifest_digest") != expected_manifest:
        raise InteroperabilityV2Error("exchange manifest identity mismatch")
    expected_paths = {item["path"] for item in manifest["files"]}
    actual_paths = {path.name for path in root.iterdir() if path.is_file() and path.name != "manifest.json"}
    if actual_paths != expected_paths:
        raise InteroperabilityV2Error("unmanifested or missing exchange resource")
    item = manifest["files"][0]
    path = root / _safe_relative_path(item["path"])
    data = path.read_bytes()
    if len(data) != item["size"] or "sha256:" + hashlib.sha256(data).hexdigest() != item["sha256"]:
        raise InteroperabilityV2Error("exchange payload integrity failure")
    bundle = json.loads(data)
    if bundle.get("bundle_digest") != manifest.get("bundle_digest"):
        raise InteroperabilityV2Error("exchange bundle digest mismatch")
    revalidation = validate_exchange_bundle(bundle)
    receipt = {
        "schema_version": "project-semantics.exchange-import-receipt.v2",
        "manifest_digest": expected_manifest,
        "bundle_digest": bundle["bundle_digest"],
        "integrity": "PASS",
        "revalidation": revalidation,
        "canonical_source_mutated": False,
    }
    receipt["receipt_id"] = digest(receipt)
    return bundle, receipt


def bridge_privacy_export_to_exchange(
    privacy_manifest: Mapping[str, Any],
    exchange_manifest: Mapping[str, Any],
    *,
    currentness_policy: str,
    security_policy: str,
    information_loss: Sequence[str],
) -> dict[str, Any]:
    """Create a typed bridge; manifests never become interchangeable by renaming."""
    if privacy_manifest.get("schema_version") != PRIVACY_EXPORT_V1:
        raise InteroperabilityV2Error("bridge requires privacy export v1")
    if exchange_manifest.get("schema_version") != EXCHANGE_MANIFEST_V2:
        raise InteroperabilityV2Error("bridge requires exchange manifest v2")
    if privacy_manifest.get("manifest_role") == exchange_manifest.get("manifest_role"):
        raise InteroperabilityV2Error("privacy and exchange roles must remain distinct")
    if not currentness_policy.strip() or not security_policy.strip():
        raise InteroperabilityV2Error("bridge requires explicit currentness and security policy")
    receipt = {
        "schema_version": BRIDGE_V1,
        "bridge_kind": "PRIVACY_EXPORT_TO_SEMANTIC_EXCHANGE_POINTER",
        "source_manifest_schema": PRIVACY_EXPORT_V1,
        "target_manifest_schema": EXCHANGE_MANIFEST_V2,
        "source_manifest_digest": privacy_manifest.get("manifest_digest") or digest(privacy_manifest),
        "target_manifest_digest": exchange_manifest.get("manifest_digest") or digest(exchange_manifest),
        "currentness_policy": currentness_policy,
        "security_policy": security_policy,
        "information_loss": list(information_loss),
        "payload_relabelled": False,
        "canonical_source_mutated": False,
        "claim_ceiling": "Typed bridge only; privacy export is not exchange admission.",
    }
    receipt["receipt_id"] = digest(receipt)
    return receipt
