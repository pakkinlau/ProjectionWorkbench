#!/usr/bin/env python3
"""Independent F2.W5.B2 adversarial qualification of contribution/capability semantics."""
from __future__ import annotations

import argparse
import json
import tempfile
from pathlib import Path
from typing import Any, Callable

from project_semantics import (
    ValidationError,
    init_project,
    load_project,
    record_contribution,
    record_episode,
    save_project,
)
from project_semantics.contribution import (
    create_capability_projection,
    record_assertion_transition,
    record_attestation,
    record_capability_assertion,
    record_evidence_scope,
)

def _setup() -> Path:
    root = Path(tempfile.mkdtemp(prefix="f2-w5-b2-"))
    init_project(root, project_id="redteam.project", title="Independent contribution red-team")
    record_episode(root, {
        "episode_id": "episode-1",
        "project_ref": "redteam.project",
        "happened_at": "2026-08-17T00:00:00Z",
        "recorded_at": "2026-08-17T00:00:00Z",
        "task_context_ref": "task-1",
        "activities": [],
        "artifact_refs": [],
        "outcome_state": "completed",
    })
    record_contribution(root, {
        "contribution_id": "contribution-1",
        "episode_ref": "episode-1",
        "actor_ref": "human-1",
        "contribution_role": "framed",
        "contribution_mode": "human_directed_ai_executed",
        "assertion_state": "human_confirmed",
        "claim_ceiling": "bounded episode contribution",
        "scope": "episode-1",
        "evidence_refs": ["evidence-1"],
        "source_refs": ["source-1"],
    })
    return root

def _scope(*, actions=None, contexts=None, currentness="current"):
    return {
        "evidence_scope_id": "scope-1",
        "observation_class": "review",
        "assessor_ref": "assessor-1",
        "independence": "independent",
        "observed_at": "2026-08-17T00:00:00Z",
        "currentness": currentness,
        "claim_ceiling": "bounded observation",
        "covered_actions": actions or ["framed"],
        "covered_contexts": contexts or ["redteam.project"],
        "evidence_refs": ["evidence-1"],
        "limitations": [],
    }

def _attestation(*, subject="human-1", relationship="independent-reviewer", independence="independent", state="active", observation_scope="framing"):
    return {
        "attestation_id": "attestation-1",
        "attestor_ref": "reviewer-1",
        "subject_ref": subject,
        "relationship": relationship,
        "observation_scope": observation_scope,
        "evidence_access": "full",
        "independence": independence,
        "state": state,
        "claim_ceiling": "bounded attestation",
        "evidence_scope_refs": ["scope-1"],
        "nonclaims": ["not mastery"],
    }

def _assertion(*, state="supported_bounded", actor_ref="human-1", contribution_refs=None, evidence_scope_refs=None, attestation_refs=None, independent_assessment_refs=None, recurrence_count=2, transfer_contexts=None, currentness="current", capability_ref="problem-framing"):
    return {
        "assertion_id": "assertion-1",
        "actor_ref": actor_ref,
        "capability_ref": capability_ref,
        "claim_text": "bounded capability assertion",
        "claim_level": "task_bounded",
        "state": state,
        "currentness": currentness,
        "claim_ceiling": "task-bounded only",
        "scope": "task-1",
        "contribution_refs": ["contribution-1"] if contribution_refs is None else contribution_refs,
        "evidence_scope_refs": ["scope-1"] if evidence_scope_refs is None else evidence_scope_refs,
        "attestation_refs": ["attestation-1"] if attestation_refs is None else attestation_refs,
        "independent_assessment_refs": ["assessment:independent"] if independent_assessment_refs is None else independent_assessment_refs,
        "recurrence_count": recurrence_count,
        "transfer_contexts": ["project-b"] if transfer_contexts is None else transfer_contexts,
        "limitations": [],
    }

def _record_supported(root, *, scope=None, attestation=None, assertion=None):
    record_evidence_scope(str(root), scope or _scope())
    record_attestation(str(root), attestation or _attestation())
    record_capability_assertion(str(root), assertion or _assertion())

def _case_transition_bypass():
    root = _setup()
    record_capability_assertion(str(root), _assertion(state="proposed", contribution_refs=[], evidence_scope_refs=[], attestation_refs=[], independent_assessment_refs=[], recurrence_count=0, transfer_contexts=[]))
    record_assertion_transition(str(root), {
        "transition_id": "transition-1", "assertion_ref": "assertion-1", "from_state": "proposed", "to_state": "supported_bounded",
        "authority_actor_ref": "unbound-actor", "reason": "promotion", "occurred_at": "2026-08-17T00:00:00Z",
        "claim_delta": "promote", "evidence_refs": ["unbound-evidence"],
    })
    create_capability_projection(str(root), actor_ref="human-1")

def _case_recurrence_laundering():
    root = _setup(); _record_supported(root, assertion=_assertion(recurrence_count=999)); create_capability_projection(str(root), actor_ref="human-1")

def _case_collusive_attestation():
    root = _setup(); _record_supported(root, attestation=_attestation(relationship="close-collaborator", independence="independent")); create_capability_projection(str(root), actor_ref="human-1")

def _case_stale_evidence_drift():
    root = _setup(); _record_supported(root); project = load_project(root); project["evidence_scopes"][0]["currentness"] = "stale"; save_project(root, project); create_capability_projection(str(root), actor_ref="human-1")

def _case_irrelevant_transfer():
    root = _setup(); _record_supported(root, scope=_scope(actions=["unrelated-action"], contexts=["unrelated-context"]), attestation=_attestation(observation_scope="unrelated-observation"), assertion=_assertion(transfer_contexts=["irrelevant-context"])); create_capability_projection(str(root), actor_ref="human-1")

def _case_revoked_attestation_drift():
    root = _setup(); _record_supported(root); project = load_project(root); project["attestations"][0]["state"] = "revoked"; save_project(root, project); create_capability_projection(str(root), actor_ref="human-1")

def _case_superseded_assertion_excluded():
    root = _setup(); _record_supported(root)
    record_assertion_transition(str(root), {"transition_id": "transition-1", "assertion_ref": "assertion-1", "from_state": "supported_bounded", "to_state": "superseded", "authority_actor_ref": "governance-actor", "reason": "newer evidence", "occurred_at": "2026-08-17T00:00:00Z", "claim_delta": "remove", "evidence_refs": ["evidence-2"]})
    if create_capability_projection(str(root), actor_ref="human-1")["assertions"]:
        raise ValidationError("superseded assertion remained projected")

def _case_scope_laundering_subject_mismatch():
    root = _setup(); _record_supported(root, attestation=_attestation(subject="different-person")); create_capability_projection(str(root), actor_ref="human-1")

def _case_unbound_independent_assessment():
    root = _setup(); _record_supported(root, assertion=_assertion(independent_assessment_refs=["assessment:any-unbound-string"])); create_capability_projection(str(root), actor_ref="human-1")

def _case_mastery_level_rejected():
    root = _setup(); value = _assertion(state="proposed"); value["claim_level"] = "mastery"; record_capability_assertion(str(root), value)

def _case_empty_direct_support_rejected():
    root = _setup(); record_capability_assertion(str(root), _assertion(contribution_refs=[], evidence_scope_refs=[], attestation_refs=[], independent_assessment_refs=[], recurrence_count=0, transfer_contexts=[]))

def _case_self_attestation_mismatch_rejected():
    root = _setup(); record_evidence_scope(str(root), _scope()); value = _attestation(independence="independent"); value["attestor_ref"] = "human-1"; value["subject_ref"] = "human-1"; record_attestation(str(root), value)

CASES = (
    ("RT-01", "AI execution -> false human capability promotion", True, _case_transition_bypass),
    ("RT-02", "activity volume / recurrence laundering", True, _case_recurrence_laundering),
    ("RT-03", "collusive / weak attestation", True, _case_collusive_attestation),
    ("RT-04", "stale recurrence / evidence drift", True, _case_stale_evidence_drift),
    ("RT-05", "irrelevant transfer", True, _case_irrelevant_transfer),
    ("RT-06", "revoked evidence", True, _case_revoked_attestation_drift),
    ("RT-07", "superseded assertion exclusion", False, _case_superseded_assertion_excluded),
    ("RT-08", "scope laundering / attestation subject mismatch", True, _case_scope_laundering_subject_mismatch),
    ("RT-09", "independent-assessment identity mismatch", True, _case_unbound_independent_assessment),
    ("RT-10", "mastery level promotion", True, _case_mastery_level_rejected),
    ("RT-11", "empty evidence direct support", True, _case_empty_direct_support_rejected),
    ("RT-12", "self-attestation independence mismatch", True, _case_self_attestation_mismatch_rejected),
)

def run():
    results = []
    for case_id, family, should_block, action in CASES:
        try:
            action(); observed_block = False; detail = "operation completed"
        except ValidationError as exc:
            observed_block = True; detail = str(exc)
        results.append({"case_id": case_id, "family": family, "expected": "BLOCK" if should_block else "ALLOW", "observed": "BLOCK" if observed_block else "ALLOW", "policy_match": observed_block == should_block, "detail": detail})
    false_accepts = sum(item["expected"] == "BLOCK" and item["observed"] == "ALLOW" for item in results)
    false_rejects = sum(item["expected"] == "ALLOW" and item["observed"] == "BLOCK" for item in results)
    return {
        "schema_version": "gva06.f2.independent-contribution-capability-redteam.v1",
        "terminal": "REPAIR_REQUIRED" if false_accepts or false_rejects else "PASS",
        "case_count": len(results), "policy_matches": sum(item["policy_match"] for item in results),
        "false_accepts": false_accepts, "false_rejects": false_rejects, "cases": results,
        "claim_boundary": "Controlled local semantic red-team only; not legal authorship, human capability truth, employment suitability, domain authority, or release.",
    }

def main():
    parser = argparse.ArgumentParser(); parser.add_argument("--output", type=Path); args = parser.parse_args()
    payload = run(); text = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True); args.output.write_text(text, encoding="utf-8")
    else:
        print(text, end="")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
