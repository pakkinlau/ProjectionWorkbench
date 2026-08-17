"""Bounded cross-domain representation and mapping pressure witness.

This module does not globalize cookery semantics. It tests whether a small
brand-neutral shared core can host explicit mappings while preserving local
extensions, ambiguity, information loss, and lawful refusal to globalize.
"""
from __future__ import annotations

import hashlib
import json
from typing import Any, Mapping

SCHEMA_VERSION = "project-semantics.cross-domain-pressure.v1"
MAPPING_RECEIPT_VERSION = "project-semantics.cross-domain-mapping-receipt.v1"

LAWFUL_DISPOSITIONS = {
    "SHARED_CORE_PLUS_LOCAL_EXTENSION",
    "NO_SAFE_GLOBALIZATION",
    "GRAMMAR_INSUFFICIENT",
    "NON_IDENTIFIABLE",
    "CORE_TOO_SOFTWARE_SPECIFIC",
}


class CrossDomainValidationError(ValueError):
    """Raised when the pressure fixture is malformed, not when a mapping fails."""


def _digest(value: Any) -> str:
    payload = json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _require(record: Mapping[str, Any], fields: tuple[str, ...], kind: str) -> None:
    missing = [field for field in fields if field not in record]
    if missing:
        raise CrossDomainValidationError(
            f"{kind} missing required fields: {', '.join(missing)}"
        )


def validate_chart(chart: Mapping[str, Any]) -> None:
    _require(
        chart,
        (
            "domain_id",
            "shared_core_version",
            "local_types",
            "protected_distinctions",
            "claim_ceiling",
        ),
        "DomainChart",
    )
    local_ids = [item.get("local_type") for item in chart["local_types"]]
    if not local_ids or any(not isinstance(item, str) or not item for item in local_ids):
        raise CrossDomainValidationError("DomainChart requires non-empty local_type IDs")
    if len(local_ids) != len(set(local_ids)):
        raise CrossDomainValidationError("DomainChart local_type IDs must be unique")


def _mapping_pairs(case: Mapping[str, Any]) -> list[tuple[str, str]]:
    return [
        (str(item["local_type"]), str(item["target_type"]))
        for item in case.get("proposed_mappings", [])
    ]


def _protected_collision(
    chart: Mapping[str, Any], mapping: Mapping[str, str]
) -> dict[str, Any] | None:
    for distinction in chart["protected_distinctions"]:
        left = distinction["left"]
        right = distinction["right"]
        if left in mapping and right in mapping and mapping[left] == mapping[right]:
            return {
                "kind": "SEMANTIC_ROLE_COLLISION",
                "left": left,
                "right": right,
                "collapsed_target": mapping[left],
                "reason": distinction["reason"],
            }
    return None


def assess_case(
    *,
    shared_core: Mapping[str, Any],
    chart: Mapping[str, Any],
    case: Mapping[str, Any],
) -> dict[str, Any]:
    """Return one typed pressure disposition without inventing equivalence."""
    validate_chart(chart)
    _require(case, ("case_id", "mode", "claim_ceiling"), "PressureCase")
    core_types = set(shared_core.get("types", []))
    local_types = {item["local_type"]: item for item in chart["local_types"]}
    proposed_pairs = _mapping_pairs(case)
    proposed = dict(proposed_pairs)
    unknown_local = sorted(set(proposed) - set(local_types))
    unknown_targets = sorted(set(proposed.values()) - core_types)

    obstruction: dict[str, Any] | None = None
    information_loss: list[str] = []
    local_extensions: list[str] = []

    if case["mode"] == "core_specificity_probe":
        required = set(case.get("required_neutral_roles", []))
        software_markers = set(case.get("software_specific_markers", []))
        missing = sorted(required - core_types)
        software_density = (
            len(core_types & software_markers) / len(core_types) if core_types else 0.0
        )
        if missing and software_density >= case.get("software_density_threshold", 0.5):
            disposition = "CORE_TOO_SOFTWARE_SPECIFIC"
            obstruction = {
                "kind": "MISSING_NEUTRAL_SHARED_ROLES",
                "missing_roles": missing,
                "software_density": software_density,
            }
        else:
            disposition = "SHARED_CORE_PLUS_LOCAL_EXTENSION"

    elif case["mode"] == "ambiguous_mapping":
        candidates = case.get("candidate_targets", [])
        distinct_targets = sorted({item["target_type"] for item in candidates})
        discriminators = case.get("discriminators", [])
        if len(distinct_targets) > 1 and not discriminators:
            disposition = "NON_IDENTIFIABLE"
            obstruction = {
                "kind": "MULTIPLE_UNRESOLVED_TARGETS",
                "local_type": case.get("local_type"),
                "candidate_targets": distinct_targets,
            }
        else:
            disposition = "SHARED_CORE_PLUS_LOCAL_EXTENSION"

    elif case["mode"] == "grammar_probe":
        missing_types = [
            item["local_type"]
            for item in chart["local_types"]
            if item.get("requires_extension") is True
            and item["local_type"] not in proposed
        ]
        if missing_types:
            disposition = "GRAMMAR_INSUFFICIENT"
            obstruction = {
                "kind": "UNREPRESENTED_DOMAIN_PRIMITIVE",
                "local_types": sorted(missing_types),
            }
        else:
            disposition = "SHARED_CORE_PLUS_LOCAL_EXTENSION"

    else:
        collision = (
            None
            if case.get("preserve_local_types") is True
            else _protected_collision(chart, proposed)
        )
        if unknown_local or unknown_targets:
            disposition = "GRAMMAR_INSUFFICIENT"
            obstruction = {
                "kind": "UNBOUND_MAPPING_SYMBOL",
                "unknown_local_types": unknown_local,
                "unknown_target_types": unknown_targets,
            }
        elif collision:
            disposition = "NO_SAFE_GLOBALIZATION"
            obstruction = collision
        else:
            mapped = set(proposed)
            local_extensions = sorted(set(local_types) - mapped)
            information_loss = sorted(
                item["local_type"]
                for item in chart["local_types"]
                if item.get("loss_if_globalized") is True
            )
            disposition = "SHARED_CORE_PLUS_LOCAL_EXTENSION"

    receipt = {
        "schema_version": MAPPING_RECEIPT_VERSION,
        "receipt_kind": "CrossDomainMappingReceipt",
        "case_id": case["case_id"],
        "domain_id": chart["domain_id"],
        "shared_core_version": chart["shared_core_version"],
        "mode": case["mode"],
        "proposed_mappings": [
            {"local_type": local, "target_type": target}
            for local, target in proposed_pairs
        ],
        "local_extensions": local_extensions,
        "information_loss_if_forced_global": information_loss,
        "obstruction": obstruction,
        "disposition": disposition,
        "claim_ceiling": case["claim_ceiling"],
        "nonclaims": [
            "no universal ontology",
            "no domain adequacy or culinary truth",
            "no human skill or capability inference",
            "no automatic semantic equivalence",
        ],
    }
    receipt["receipt_id"] = f"cross-domain:{_digest(receipt)[:24]}"
    return receipt


def run_cross_domain_pressure(bundle: Mapping[str, Any]) -> dict[str, Any]:
    _require(bundle, ("shared_core", "domain_chart", "cases"), "PressureBundle")
    chart = bundle["domain_chart"]
    validate_chart(chart)
    receipts = [
        assess_case(shared_core=bundle["shared_core"], chart=chart, case=case)
        for case in bundle["cases"]
    ]
    expected = {case["case_id"]: case["expected_disposition"] for case in bundle["cases"]}
    actual = {receipt["case_id"]: receipt["disposition"] for receipt in receipts}
    matches = {
        case_id: actual[case_id] == disposition
        for case_id, disposition in expected.items()
    }
    primary = next(
        receipt for receipt in receipts if receipt["case_id"] == bundle["primary_case_id"]
    )
    result = {
        "schema_version": SCHEMA_VERSION,
        "witness_id": "F2.W5.B4.cross-domain-cookery-pressure.v1",
        "domain_id": chart["domain_id"],
        "primary_disposition": primary["disposition"],
        "case_results": receipts,
        "expected_dispositions": expected,
        "policy_matches": matches,
        "passed": all(matches.values()),
        "supported": [
            "a small neutral core can host a bounded cookery chart through explicit mappings",
            "domain-local types and distinctions can remain local",
            "unsafe role unification can fail closed",
            "ambiguity and grammar insufficiency can remain lawful terminals",
        ],
        "not_supported": [
            "cross-domain generality beyond the fixture",
            "culinary adequacy or expertise",
            "automatic ontology induction",
            "product value, adoption, or authority",
        ],
    }
    result["witness_digest"] = _digest(result)
    return result
