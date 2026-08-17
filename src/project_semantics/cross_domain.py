"""Domain-neutral cross-domain representation pressure evaluator.

All domain witness identities, support statements and nonclaims are supplied by
DomainChart envelopes. Shared evaluator code contains no domain-specific prose.
"""
from __future__ import annotations

import hashlib
import json
from typing import Any, Mapping

SCHEMA_VERSION = "project-semantics.cross-domain-pressure.v2"
MAPPING_RECEIPT_VERSION = "project-semantics.cross-domain-mapping-receipt.v2"
DOMAIN_ENVELOPE_VERSION = "project-semantics.domain-execution-envelope.v1"
LAWFUL = {
    "SHARED_CORE_PLUS_LOCAL_EXTENSION",
    "NO_SAFE_GLOBALIZATION",
    "GRAMMAR_INSUFFICIENT",
    "NON_IDENTIFIABLE",
    "CORE_TOO_SOFTWARE_SPECIFIC",
}


class CrossDomainValidationError(ValueError):
    pass


def _digest(value: Any) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    return hashlib.sha256(raw).hexdigest()


def _require(record: Mapping[str, Any], *fields: str) -> None:
    missing = [field for field in fields if field not in record]
    if missing:
        raise CrossDomainValidationError("missing fields: " + ", ".join(missing))


def _text_list(value: Any, field: str) -> list[str]:
    if not isinstance(value, list) or not value or any(not isinstance(x, str) or not x.strip() for x in value):
        raise CrossDomainValidationError(f"{field} must be a non-empty text list")
    return list(value)


def validate_execution_envelope(envelope: Mapping[str, Any]) -> None:
    _require(envelope, "schema_version", "witness_id", "supported", "not_supported", "receipt_nonclaims")
    if envelope["schema_version"] != DOMAIN_ENVELOPE_VERSION:
        raise CrossDomainValidationError("unsupported execution envelope")
    if not isinstance(envelope["witness_id"], str) or not envelope["witness_id"].strip():
        raise CrossDomainValidationError("witness_id required")
    for field in ("supported", "not_supported", "receipt_nonclaims"):
        _text_list(envelope[field], field)


def validate_chart(chart: Mapping[str, Any]) -> None:
    _require(chart, "domain_id", "shared_core_version", "local_types", "protected_distinctions", "claim_ceiling", "execution_envelope")
    ids = [item.get("local_type") for item in chart["local_types"]]
    if not ids or any(not isinstance(x, str) or not x for x in ids) or len(ids) != len(set(ids)):
        raise CrossDomainValidationError("local_type IDs must be non-empty and unique")
    validate_execution_envelope(chart["execution_envelope"])


def assess_case(*, shared_core: Mapping[str, Any], chart: Mapping[str, Any], case: Mapping[str, Any]) -> dict[str, Any]:
    validate_chart(chart)
    _require(case, "case_id", "mode", "claim_ceiling")
    core = set(shared_core.get("types", []))
    local = {item["local_type"]: item for item in chart["local_types"]}
    pairs = [(str(x["local_type"]), str(x["target_type"])) for x in case.get("proposed_mappings", [])]
    mapping = dict(pairs)
    obstruction = None
    loss: list[str] = []
    extensions: list[str] = []

    if case["mode"] == "ambiguous_mapping":
        targets = sorted({x["target_type"] for x in case.get("candidate_targets", [])})
        disposition = "NON_IDENTIFIABLE" if len(targets) > 1 and not case.get("discriminators") else "SHARED_CORE_PLUS_LOCAL_EXTENSION"
        if disposition == "NON_IDENTIFIABLE":
            obstruction = {"kind": "MULTIPLE_UNRESOLVED_TARGETS", "candidate_targets": targets}
    elif case["mode"] == "grammar_probe":
        missing = sorted(x["local_type"] for x in chart["local_types"] if x.get("requires_extension") and x["local_type"] not in mapping)
        disposition = "GRAMMAR_INSUFFICIENT" if missing else "SHARED_CORE_PLUS_LOCAL_EXTENSION"
        if missing:
            obstruction = {"kind": "UNREPRESENTED_DOMAIN_PRIMITIVE", "local_types": missing}
    elif case["mode"] == "core_specificity_probe":
        required = set(case.get("required_neutral_roles", []))
        missing = sorted(required - core)
        disposition = "CORE_TOO_SOFTWARE_SPECIFIC" if missing else "SHARED_CORE_PLUS_LOCAL_EXTENSION"
        if missing:
            obstruction = {"kind": "MISSING_NEUTRAL_SHARED_ROLES", "missing_roles": missing}
    else:
        unknown_local = sorted(set(mapping) - set(local))
        unknown_target = sorted(set(mapping.values()) - core)
        collision = None
        for item in chart["protected_distinctions"]:
            if item["left"] in mapping and item["right"] in mapping and mapping[item["left"]] == mapping[item["right"]]:
                collision = {"kind": "SEMANTIC_ROLE_COLLISION", **item, "collapsed_target": mapping[item["left"]]}
                break
        if unknown_local or unknown_target:
            disposition = "GRAMMAR_INSUFFICIENT"
            obstruction = {"kind": "UNBOUND_MAPPING_SYMBOL", "unknown_local_types": unknown_local, "unknown_target_types": unknown_target}
        elif collision and not case.get("preserve_local_types"):
            disposition = "NO_SAFE_GLOBALIZATION"
            obstruction = collision
        else:
            disposition = "SHARED_CORE_PLUS_LOCAL_EXTENSION"
            extensions = sorted(set(local) - set(mapping))
            loss = sorted(x["local_type"] for x in chart["local_types"] if x.get("loss_if_globalized"))

    if disposition not in LAWFUL:
        raise CrossDomainValidationError("unlawful disposition")
    envelope = chart["execution_envelope"]
    receipt = {
        "schema_version": MAPPING_RECEIPT_VERSION,
        "receipt_kind": "CrossDomainMappingReceipt",
        "case_id": case["case_id"],
        "domain_id": chart["domain_id"],
        "shared_core_version": chart["shared_core_version"],
        "mode": case["mode"],
        "proposed_mappings": [{"local_type": a, "target_type": b} for a, b in pairs],
        "local_extensions": extensions,
        "information_loss_if_forced_global": loss,
        "obstruction": obstruction,
        "disposition": disposition,
        "claim_ceiling": case["claim_ceiling"],
        "nonclaims": list(envelope["receipt_nonclaims"]),
    }
    receipt["receipt_id"] = "cross-domain:" + _digest(receipt)[:24]
    return receipt


def run_cross_domain_pressure(bundle: Mapping[str, Any]) -> dict[str, Any]:
    _require(bundle, "shared_core", "domain_chart", "cases", "primary_case_id")
    chart = bundle["domain_chart"]
    validate_chart(chart)
    receipts = [assess_case(shared_core=bundle["shared_core"], chart=chart, case=case) for case in bundle["cases"]]
    expected = {case["case_id"]: case["expected_disposition"] for case in bundle["cases"]}
    matches = {receipt["case_id"]: receipt["disposition"] == expected[receipt["case_id"]] for receipt in receipts}
    primary = next(x for x in receipts if x["case_id"] == bundle["primary_case_id"])
    envelope = chart["execution_envelope"]
    result = {
        "schema_version": SCHEMA_VERSION,
        "witness_id": envelope["witness_id"],
        "domain_id": chart["domain_id"],
        "domain_chart_digest": _digest(chart),
        "execution_envelope_schema_version": envelope["schema_version"],
        "primary_disposition": primary["disposition"],
        "case_results": receipts,
        "expected_dispositions": expected,
        "policy_matches": matches,
        "passed": all(matches.values()),
        "supported": list(envelope["supported"]),
        "not_supported": list(envelope["not_supported"]),
        "claim_ceiling": chart["claim_ceiling"],
    }
    result["witness_digest"] = _digest(result)
    return result
