"""Bounded contribution, evidence, attestation, and capability contracts.

This module extends the v0 kernel without changing the canonical project schema.
It keeps contribution facts distinct from capability assertions and requires
explicit, noncompensatory gates before a capability can be projected.
"""
from __future__ import annotations

from typing import Any, Iterable, Mapping

from . import ValidationError, load_project, save_project

CONTRIBUTION_RELATION_TYPES = {
    "human_rejected_ai_proposal",
    "human_corrected_ai_assumption",
    "human_selected_ai_proposal",
    "reviewed_not_verified",
    "verified",
    "derived_from",
}
CAPABILITY_ASSERTION_STATES = {
    "proposed",
    "supported_bounded",
    "disputed",
    "superseded",
    "revoked",
}
CAPABILITY_LEVELS = {"task_bounded", "role_bounded", "process_bounded"}
CURRENTNESS_STATES = {"current", "recent", "stale", "unknown"}
INDEPENDENCE_STATES = {"self", "collaborator", "independent"}
ATTESTATION_STATES = {"active", "revoked", "superseded"}
ASSERTION_TRANSITIONS = {
    ("proposed", "supported_bounded"),
    ("proposed", "disputed"),
    ("supported_bounded", "disputed"),
    ("supported_bounded", "superseded"),
    ("supported_bounded", "revoked"),
    ("disputed", "supported_bounded"),
    ("disputed", "revoked"),
    ("disputed", "superseded"),
}


def _require_fields(record: Mapping[str, Any], fields: Iterable[str], kind: str) -> None:
    missing = [field for field in fields if field not in record]
    if missing:
        raise ValidationError(f"{kind} missing required fields: {', '.join(missing)}")


def _require_text(record: Mapping[str, Any], fields: Iterable[str], kind: str) -> None:
    _require_fields(record, fields, kind)
    bad = [
        field
        for field in fields
        if not isinstance(record[field], str) or not record[field].strip()
    ]
    if bad:
        raise ValidationError(f"{kind} requires non-empty text: {', '.join(bad)}")


def _require_nonempty_list(
    record: Mapping[str, Any], fields: Iterable[str], kind: str
) -> None:
    _require_fields(record, fields, kind)
    bad = [
        field
        for field in fields
        if not isinstance(record[field], list) or not record[field]
    ]
    if bad:
        raise ValidationError(f"{kind} requires non-empty list: {', '.join(bad)}")


def _load(root: str) -> dict[str, Any]:
    project = load_project(root)
    for key in (
        "contribution_relations",
        "evidence_scopes",
        "attestations",
        "capability_assertions",
        "assertion_transitions",
    ):
        project.setdefault(key, [])
    return project


def validate_contribution_relation(value: Mapping[str, Any]) -> None:
    _require_text(
        value,
        [
            "relation_id",
            "relation_type",
            "actor_ref",
            "source_contribution_ref",
            "target_ref",
            "scope",
            "claim_ceiling",
        ],
        "ContributionRelation",
    )
    _require_fields(value, ["evidence_refs"], "ContributionRelation")
    if value["relation_type"] not in CONTRIBUTION_RELATION_TYPES:
        raise ValidationError("unsupported contribution relation type")
    if value["relation_type"] in {
        "human_rejected_ai_proposal",
        "human_corrected_ai_assumption",
        "verified",
    } and not value["evidence_refs"]:
        raise ValidationError("material contribution relations require evidence")


def validate_evidence_scope(value: Mapping[str, Any]) -> None:
    _require_text(
        value,
        [
            "evidence_scope_id",
            "observation_class",
            "assessor_ref",
            "independence",
            "observed_at",
            "currentness",
            "claim_ceiling",
        ],
        "EvidenceScope",
    )
    _require_nonempty_list(
        value,
        ["covered_actions", "covered_contexts", "evidence_refs"],
        "EvidenceScope",
    )
    _require_fields(value, ["limitations"], "EvidenceScope")
    if value["independence"] not in INDEPENDENCE_STATES:
        raise ValidationError("unsupported evidence independence state")
    if value["currentness"] not in CURRENTNESS_STATES:
        raise ValidationError("unsupported evidence currentness state")


def validate_attestation(value: Mapping[str, Any]) -> None:
    _require_text(
        value,
        [
            "attestation_id",
            "attestor_ref",
            "subject_ref",
            "relationship",
            "observation_scope",
            "evidence_access",
            "independence",
            "state",
            "claim_ceiling",
        ],
        "Attestation",
    )
    _require_nonempty_list(
        value, ["evidence_scope_refs", "nonclaims"], "Attestation"
    )
    if value["independence"] not in INDEPENDENCE_STATES:
        raise ValidationError("unsupported attestation independence state")
    if value["state"] not in ATTESTATION_STATES:
        raise ValidationError("unsupported attestation state")
    if value["attestor_ref"] == value["subject_ref"] and value["independence"] != "self":
        raise ValidationError("self-attestation must declare self independence")


def validate_capability_assertion(value: Mapping[str, Any]) -> None:
    _require_text(
        value,
        [
            "assertion_id",
            "actor_ref",
            "capability_ref",
            "claim_text",
            "claim_level",
            "state",
            "currentness",
            "claim_ceiling",
        ],
        "CapabilityAssertion",
    )
    _require_fields(
        value,
        [
            "scope",
            "contribution_refs",
            "evidence_scope_refs",
            "attestation_refs",
            "independent_assessment_refs",
            "recurrence_count",
            "transfer_contexts",
            "limitations",
        ],
        "CapabilityAssertion",
    )
    if value["claim_level"] not in CAPABILITY_LEVELS:
        raise ValidationError("mastery/expertise and unsupported capability levels are forbidden")
    if value["state"] not in CAPABILITY_ASSERTION_STATES:
        raise ValidationError("unsupported capability assertion state")
    if value["state"] in {"revoked", "superseded"}:
        raise ValidationError("terminal capability states require AssertionTransition")
    if value["currentness"] not in CURRENTNESS_STATES:
        raise ValidationError("unsupported capability currentness state")
    if not isinstance(value["recurrence_count"], int) or value["recurrence_count"] < 0:
        raise ValidationError("recurrence_count must be a non-negative integer")
    if value["state"] == "supported_bounded":
        if not value["contribution_refs"]:
            raise ValidationError("supported capability requires contribution references")
        if not value["evidence_scope_refs"]:
            raise ValidationError("supported capability requires structured evidence scope")
        if value["recurrence_count"] < 2:
            raise ValidationError("supported capability requires recurrence across at least two episodes")
        if not value["transfer_contexts"]:
            raise ValidationError("supported capability requires at least one transfer context")
        if value["currentness"] not in {"current", "recent"}:
            raise ValidationError("supported capability requires current or recent evidence")
        if not value["independent_assessment_refs"]:
            raise ValidationError("supported capability requires independent assessment")
        if not value["attestation_refs"]:
            raise ValidationError("supported capability requires scoped attestation")


def validate_assertion_transition(value: Mapping[str, Any]) -> None:
    _require_text(
        value,
        [
            "transition_id",
            "assertion_ref",
            "from_state",
            "to_state",
            "authority_actor_ref",
            "reason",
            "occurred_at",
            "claim_delta",
        ],
        "AssertionTransition",
    )
    _require_nonempty_list(value, ["evidence_refs"], "AssertionTransition")
    if (value["from_state"], value["to_state"]) not in ASSERTION_TRANSITIONS:
        raise ValidationError("unsupported assertion transition")


def record_contribution_relation(root: str, relation: Mapping[str, Any]) -> dict[str, Any]:
    validate_contribution_relation(relation)
    project = _load(root)
    contribution_ids = {item["contribution_id"] for item in project["contributions"]}
    if relation["source_contribution_ref"] not in contribution_ids:
        raise ValidationError("unknown source contribution")
    project["contribution_relations"].append(dict(relation))
    save_project(root, project)
    return project


def record_evidence_scope(root: str, evidence_scope: Mapping[str, Any]) -> dict[str, Any]:
    validate_evidence_scope(evidence_scope)
    project = _load(root)
    project["evidence_scopes"].append(dict(evidence_scope))
    save_project(root, project)
    return project


def record_attestation(root: str, attestation: Mapping[str, Any]) -> dict[str, Any]:
    validate_attestation(attestation)
    project = _load(root)
    scope_ids = {item["evidence_scope_id"] for item in project["evidence_scopes"]}
    missing = [ref for ref in attestation["evidence_scope_refs"] if ref not in scope_ids]
    if missing:
        raise ValidationError(
            f"attestation references unknown evidence scopes: {', '.join(missing)}"
        )
    project["attestations"].append(dict(attestation))
    save_project(root, project)
    return project


def record_capability_assertion(root: str, assertion: Mapping[str, Any]) -> dict[str, Any]:
    validate_capability_assertion(assertion)
    project = _load(root)
    contribution_ids = {item["contribution_id"] for item in project["contributions"]}
    evidence_scope_ids = {item["evidence_scope_id"] for item in project["evidence_scopes"]}
    attestation_ids = {item["attestation_id"] for item in project["attestations"]}
    missing_contributions = [
        ref for ref in assertion["contribution_refs"] if ref not in contribution_ids
    ]
    missing_scopes = [
        ref for ref in assertion["evidence_scope_refs"] if ref not in evidence_scope_ids
    ]
    missing_attestations = [
        ref for ref in assertion["attestation_refs"] if ref not in attestation_ids
    ]
    if missing_contributions:
        raise ValidationError(
            f"capability assertion references unknown contributions: {', '.join(missing_contributions)}"
        )
    if missing_scopes:
        raise ValidationError(
            f"capability assertion references unknown evidence scopes: {', '.join(missing_scopes)}"
        )
    if missing_attestations:
        raise ValidationError(
            f"capability assertion references unknown attestations: {', '.join(missing_attestations)}"
        )
    if assertion["state"] == "supported_bounded":
        scopes = [
            item
            for item in project["evidence_scopes"]
            if item["evidence_scope_id"] in assertion["evidence_scope_refs"]
        ]
        attestations = [
            item
            for item in project["attestations"]
            if item["attestation_id"] in assertion["attestation_refs"]
        ]
        if not any(
            item["independence"] == "independent"
            and item["currentness"] in {"current", "recent"}
            for item in scopes
        ):
            raise ValidationError(
                "supported capability requires current independent evidence scope"
            )
        if not any(
            item["independence"] == "independent" and item["state"] == "active"
            for item in attestations
        ):
            raise ValidationError(
                "supported capability requires active independent attestation"
            )
    project["capability_assertions"].append(dict(assertion))
    save_project(root, project)
    return project


def record_assertion_transition(root: str, transition: Mapping[str, Any]) -> dict[str, Any]:
    validate_assertion_transition(transition)
    project = _load(root)
    assertions = {item["assertion_id"]: item for item in project["capability_assertions"]}
    assertion = assertions.get(transition["assertion_ref"])
    if assertion is None:
        raise ValidationError("assertion transition requires a bound prior assertion")
    if assertion["state"] != transition["from_state"]:
        raise ValidationError(
            "assertion transition from_state does not match current assertion state"
        )
    assertion["state"] = transition["to_state"]
    project["assertion_transitions"].append(dict(transition))
    save_project(root, project)
    return project


def create_capability_projection(root: str, *, actor_ref: str) -> dict[str, Any]:
    project = _load(root)
    supported = [
        item
        for item in project["capability_assertions"]
        if item["actor_ref"] == actor_ref and item["state"] == "supported_bounded"
    ]
    return {
        "projection_kind": "BoundedCapabilityProjection",
        "actor_ref": actor_ref,
        "assertions": supported,
        "excluded_states": sorted(CAPABILITY_ASSERTION_STATES - {"supported_bounded"}),
        "nonclaims": [
            "No mastery or expertise is inferred.",
            "Activity volume and artifact count are not capability evidence.",
            "This projection does not grant authority or admission.",
        ],
        "claim_ceiling": "Only assertions that already pass recurrence, transfer, currentness, scoped attestation, structured evidence and independent-assessment gates are projected.",
    }
