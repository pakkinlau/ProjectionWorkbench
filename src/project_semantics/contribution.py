"""Bounded contribution, evidence, attestation, capability, and transition contracts.

F2.W6.B1 repair: contribution records remain distinct from capability
assertions. A supported capability is admitted only after typed, identity-bound,
current, noncompensatory gates are replayed against canonical local state.
"""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Iterable, Mapping, Sequence

from . import ValidationError, load_project, save_project

CONTRIBUTION_RELATION_TYPES = {
    "human_rejected_ai_proposal",
    "human_corrected_ai_assumption",
    "human_selected_ai_proposal",
    "reviewed_not_verified",
    "verified",
    "derived_from",
}
CAPABILITY_ASSERTION_STATES = {"proposed", "supported_bounded", "disputed", "superseded", "revoked"}
CAPABILITY_LEVELS = {"task_bounded", "role_bounded", "process_bounded"}
CURRENTNESS_STATES = {"current", "recent", "stale", "unknown"}
INDEPENDENCE_STATES = {"self", "collaborator", "independent"}
ATTESTATION_STATES = {"active", "revoked", "superseded"}
ASSESSMENT_STATES = {"active", "revoked", "superseded"}
INDEPENDENT_RELATIONSHIPS = {
    "independent-reviewer",
    "independent_evaluator",
    "external-reviewer",
    "external_evaluator",
    "independent-assessor",
}
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
    bad = [field for field in fields if not isinstance(record[field], str) or not record[field].strip()]
    if bad:
        raise ValidationError(f"{kind} requires non-empty text: {', '.join(bad)}")


def _require_nonempty_list(record: Mapping[str, Any], fields: Iterable[str], kind: str) -> None:
    _require_fields(record, fields, kind)
    bad = [field for field in fields if not isinstance(record[field], list) or not record[field]]
    if bad:
        raise ValidationError(f"{kind} requires non-empty list: {', '.join(bad)}")


def _load(root: str) -> dict[str, Any]:
    project = load_project(root)
    for key in (
        "contribution_relations",
        "evidence_scopes",
        "attestations",
        "independent_assessments",
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
    _require_nonempty_list(value, ["covered_actions", "covered_contexts", "evidence_refs"], "EvidenceScope")
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
    _require_nonempty_list(value, ["evidence_scope_refs", "nonclaims"], "Attestation")
    _require_fields(value, ["authority_effect"], "Attestation")
    if value["authority_effect"] != "none":
        raise ValidationError("attestation cannot grant authority")
    if value["independence"] not in INDEPENDENCE_STATES:
        raise ValidationError("unsupported attestation independence state")
    if value["state"] not in ATTESTATION_STATES:
        raise ValidationError("unsupported attestation state")
    if value["attestor_ref"] == value["subject_ref"] and value["independence"] != "self":
        raise ValidationError("self-attestation must declare self independence")
    if value["independence"] == "independent" and value["relationship"] not in INDEPENDENT_RELATIONSHIPS:
        raise ValidationError("attestation relationship is not independently scoped")


def validate_independent_assessment(value: Mapping[str, Any]) -> None:
    _require_text(
        value,
        [
            "assessment_id",
            "assessor_ref",
            "subject_ref",
            "capability_ref",
            "observation_scope",
            "independence",
            "state",
            "observed_at",
            "currentness",
            "claim_ceiling",
        ],
        "IndependentAssessment",
    )
    _require_nonempty_list(value, ["evidence_scope_refs", "evidence_refs", "nonclaims"], "IndependentAssessment")
    _require_fields(value, ["authority_effect", "limitations"], "IndependentAssessment")
    if value["authority_effect"] != "none":
        raise ValidationError("independent assessment cannot grant authority")
    if value["independence"] != "independent":
        raise ValidationError("independent assessment must declare independent")
    if value["state"] not in ASSESSMENT_STATES:
        raise ValidationError("unsupported independent assessment state")
    if value["currentness"] not in CURRENTNESS_STATES:
        raise ValidationError("unsupported independent assessment currentness")


def _validate_transfer_evidence(item: Mapping[str, Any], capability_ref: str) -> None:
    _require_text(
        item,
        [
            "source_context_ref",
            "target_context_ref",
            "capability_ref",
            "evidence_scope_ref",
            "relevance",
        ],
        "TransferEvidence",
    )
    _require_nonempty_list(item, ["evidence_refs"], "TransferEvidence")
    if item["source_context_ref"] == item["target_context_ref"]:
        raise ValidationError("transfer requires distinct source and target contexts")
    if item["capability_ref"] != capability_ref:
        raise ValidationError("transfer evidence capability mismatch")


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
            "scope",
        ],
        "CapabilityAssertion",
    )
    _require_fields(
        value,
        [
            "contribution_refs",
            "evidence_scope_refs",
            "attestation_refs",
            "independent_assessment_refs",
            "recurrence_episode_refs",
            "transfer_evidence",
            "limitations",
            "authority_effect",
        ],
        "CapabilityAssertion",
    )
    if value["authority_effect"] != "none":
        raise ValidationError("capability assertion cannot grant authority")
    if value["claim_level"] not in CAPABILITY_LEVELS:
        raise ValidationError("mastery/expertise and unsupported capability levels are forbidden")
    if value["state"] not in CAPABILITY_ASSERTION_STATES:
        raise ValidationError("unsupported capability assertion state")
    if value["state"] in {"revoked", "superseded"}:
        raise ValidationError("terminal capability states require AssertionTransition")
    if value["currentness"] not in CURRENTNESS_STATES:
        raise ValidationError("unsupported capability currentness state")
    refs = value["recurrence_episode_refs"]
    if not isinstance(refs, list):
        raise ValidationError("recurrence_episode_refs must be a list")
    if len(refs) != len(set(refs)):
        raise ValidationError("recurrence episode identities must be distinct")
    if "recurrence_count" in value and value["recurrence_count"] != len(refs):
        raise ValidationError("recurrence_count must equal bound recurrence episode identities")
    if not isinstance(value["transfer_evidence"], list):
        raise ValidationError("transfer_evidence must be a list")
    for item in value["transfer_evidence"]:
        if not isinstance(item, Mapping):
            raise ValidationError("transfer_evidence entries must be objects")
        _validate_transfer_evidence(item, value["capability_ref"])
    if value["state"] == "supported_bounded":
        _require_nonempty_list(
            value,
            [
                "contribution_refs",
                "evidence_scope_refs",
                "attestation_refs",
                "independent_assessment_refs",
                "recurrence_episode_refs",
                "transfer_evidence",
            ],
            "CapabilityAssertion",
        )
        if len(value["recurrence_episode_refs"]) < 2:
            raise ValidationError("supported capability requires at least two bound recurrence episodes")
        if value["currentness"] not in {"current", "recent"}:
            raise ValidationError("supported capability requires current or recent assertion state")


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
            "claim_ceiling",
        ],
        "AssertionTransition",
    )
    _require_nonempty_list(value, ["evidence_refs", "authority_basis_refs"], "AssertionTransition")
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
        raise ValidationError(f"attestation references unknown evidence scopes: {', '.join(missing)}")
    project["attestations"].append(dict(attestation))
    save_project(root, project)
    return project


def record_independent_assessment(root: str, assessment: Mapping[str, Any]) -> dict[str, Any]:
    validate_independent_assessment(assessment)
    project = _load(root)
    scope_ids = {item["evidence_scope_id"] for item in project["evidence_scopes"]}
    missing = [ref for ref in assessment["evidence_scope_refs"] if ref not in scope_ids]
    if missing:
        raise ValidationError(f"independent assessment references unknown evidence scopes: {', '.join(missing)}")
    project["independent_assessments"].append(dict(assessment))
    save_project(root, project)
    return project


def _index(items: Sequence[Mapping[str, Any]], key: str) -> dict[str, Mapping[str, Any]]:
    return {str(item[key]): item for item in items}


def _admit_supported(project: Mapping[str, Any], assertion: Mapping[str, Any]) -> None:
    validate_capability_assertion(assertion)
    if assertion["state"] != "supported_bounded":
        return

    contributions = _index(project.get("contributions", []), "contribution_id")
    episodes = _index(project.get("episodes", []), "episode_id")
    scopes = _index(project.get("evidence_scopes", []), "evidence_scope_id")
    attestations = _index(project.get("attestations", []), "attestation_id")
    assessments = _index(project.get("independent_assessments", []), "assessment_id")

    def _missing(refs: Sequence[str], index: Mapping[str, Any], label: str) -> None:
        missing = [ref for ref in refs if ref not in index]
        if missing:
            raise ValidationError(f"capability assertion references unknown {label}: {', '.join(missing)}")

    _missing(assertion["contribution_refs"], contributions, "contributions")
    _missing(assertion["recurrence_episode_refs"], episodes, "recurrence episodes")
    _missing(assertion["evidence_scope_refs"], scopes, "evidence scopes")
    _missing(assertion["attestation_refs"], attestations, "attestations")
    _missing(assertion["independent_assessment_refs"], assessments, "independent assessments")

    selected_contributions = [contributions[ref] for ref in assertion["contribution_refs"]]
    if any(item.get("actor_ref") != assertion["actor_ref"] for item in selected_contributions):
        raise ValidationError("capability contribution actor mismatch")
    cited_episode_refs = {item.get("episode_ref") for item in selected_contributions}
    if not set(assertion["recurrence_episode_refs"]).issubset(cited_episode_refs):
        raise ValidationError("recurrence episodes must be bound to cited contributions")

    selected_scopes = [scopes[ref] for ref in assertion["evidence_scope_refs"]]
    if not any(
        item.get("independence") == "independent"
        and item.get("currentness") in {"current", "recent"}
        for item in selected_scopes
    ):
        raise ValidationError("supported capability requires current independent evidence scope")
    if any(item.get("currentness") not in {"current", "recent"} for item in selected_scopes):
        raise ValidationError("capability projection cannot use stale or unknown evidence scope")

    roles = {str(item.get("contribution_role")) for item in selected_contributions}
    covered_actions = {str(action) for item in selected_scopes for action in item.get("covered_actions", [])}
    if not roles.issubset(covered_actions):
        raise ValidationError("evidence scope does not cover cited contribution roles")

    episode_contexts = {
        str(episodes[ref].get("task_context_ref")) for ref in assertion["recurrence_episode_refs"]
    }
    covered_contexts = {str(ctx) for item in selected_scopes for ctx in item.get("covered_contexts", [])}
    if not episode_contexts.issubset(covered_contexts):
        raise ValidationError("evidence scope does not cover recurrence contexts")

    selected_attestations = [attestations[ref] for ref in assertion["attestation_refs"]]
    for item in selected_attestations:
        if item.get("subject_ref") != assertion["actor_ref"]:
            raise ValidationError("attestation subject mismatch")
        if item.get("state") != "active" or item.get("independence") != "independent":
            raise ValidationError("supported capability requires active independent attestation")
        if item.get("relationship") not in INDEPENDENT_RELATIONSHIPS:
            raise ValidationError("attestation relationship is not independently scoped")
        if item.get("authority_effect") != "none":
            raise ValidationError("attestation authority effect is not bounded")
        if not set(item.get("evidence_scope_refs", [])).intersection(assertion["evidence_scope_refs"]):
            raise ValidationError("attestation is not bound to assertion evidence scope")

    selected_assessments = [assessments[ref] for ref in assertion["independent_assessment_refs"]]
    for item in selected_assessments:
        if item.get("subject_ref") != assertion["actor_ref"]:
            raise ValidationError("independent assessment subject mismatch")
        if item.get("capability_ref") != assertion["capability_ref"]:
            raise ValidationError("independent assessment capability mismatch")
        if item.get("state") != "active" or item.get("independence") != "independent":
            raise ValidationError("supported capability requires active independent assessment")
        if item.get("currentness") not in {"current", "recent"}:
            raise ValidationError("supported capability requires current independent assessment")
        if item.get("authority_effect") != "none":
            raise ValidationError("independent assessment authority effect is not bounded")
        if not set(item.get("evidence_scope_refs", [])).intersection(assertion["evidence_scope_refs"]):
            raise ValidationError("independent assessment is not bound to assertion evidence scope")

    for transfer in assertion["transfer_evidence"]:
        scope_ref = transfer["evidence_scope_ref"]
        if scope_ref not in assertion["evidence_scope_refs"]:
            raise ValidationError("transfer evidence is not bound to assertion evidence scope")
        if transfer["source_context_ref"] not in episode_contexts or transfer["target_context_ref"] not in episode_contexts:
            raise ValidationError("transfer evidence contexts are not bound to recurrence episodes")
        if transfer["source_context_ref"] not in covered_contexts or transfer["target_context_ref"] not in covered_contexts:
            raise ValidationError("transfer evidence contexts are not covered by evidence scope")


def record_capability_assertion(root: str, assertion: Mapping[str, Any]) -> dict[str, Any]:
    validate_capability_assertion(assertion)
    project = _load(root)
    if assertion["state"] == "supported_bounded":
        _admit_supported(project, assertion)
    project["capability_assertions"].append(deepcopy(dict(assertion)))
    save_project(root, project)
    return project


def _eligible_transition_actors(project: Mapping[str, Any], assertion: Mapping[str, Any]) -> set[str]:
    actors = {str(assertion["actor_ref"])}
    for item in project.get("attestations", []):
        if item.get("subject_ref") == assertion["actor_ref"] and item.get("state") == "active":
            actors.add(str(item.get("attestor_ref")))
    for item in project.get("independent_assessments", []):
        if item.get("subject_ref") == assertion["actor_ref"] and item.get("state") == "active":
            actors.add(str(item.get("assessor_ref")))
    return actors


def record_assertion_transition(root: str, transition: Mapping[str, Any]) -> dict[str, Any]:
    validate_assertion_transition(transition)
    project = _load(root)
    assertions = {item["assertion_id"]: item for item in project["capability_assertions"]}
    assertion = assertions.get(transition["assertion_ref"])
    if assertion is None:
        raise ValidationError("assertion transition requires a bound prior assertion")
    if assertion["state"] != transition["from_state"]:
        raise ValidationError("assertion transition from_state does not match current assertion state")
    if transition["claim_ceiling"] != assertion["claim_ceiling"]:
        raise ValidationError("assertion transition may not silently widen or replace the claim ceiling")
    if transition["authority_actor_ref"] not in _eligible_transition_actors(project, assertion):
        raise ValidationError("assertion transition authority actor is not bound")

    known_basis = (
        set(assertion.get("evidence_scope_refs", []))
        | set(assertion.get("attestation_refs", []))
        | set(assertion.get("independent_assessment_refs", []))
        | set(transition.get("evidence_refs", []))
    )
    if not set(transition["authority_basis_refs"]).issubset(known_basis):
        raise ValidationError("assertion transition authority basis is unbound")

    candidate = deepcopy(assertion)
    candidate["state"] = transition["to_state"]
    if candidate["state"] == "supported_bounded":
        _admit_supported(project, candidate)
    assertion["state"] = transition["to_state"]
    assertion["last_transition_ref"] = transition["transition_id"]
    project["assertion_transitions"].append(deepcopy(dict(transition)))
    save_project(root, project)
    return project


def create_capability_projection(root: str, *, actor_ref: str) -> dict[str, Any]:
    project = _load(root)
    supported = []
    for item in project["capability_assertions"]:
        if item.get("actor_ref") != actor_ref or item.get("state") != "supported_bounded":
            continue
        _admit_supported(project, item)
        supported.append(deepcopy(item))
    return {
        "projection_kind": "BoundedCapabilityProjection",
        "actor_ref": actor_ref,
        "assertions": supported,
        "excluded_states": sorted(CAPABILITY_ASSERTION_STATES - {"supported_bounded"}),
        "admission_replayed": True,
        "nonclaims": [
            "No mastery or expertise is inferred.",
            "Activity volume and artifact count are not capability evidence.",
            "This projection does not grant authority or admission.",
        ],
        "claim_ceiling": "Only assertions that replay bound recurrence, relevant transfer, current evidence, active independent attestation, typed independent assessment, and governed transition state are projected.",
    }
