"""Deterministic first-witness fixture for task-relative project lenses."""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

from .representation import (
    DomainChart,
    InformationLossReport,
    LensMapping,
    MappingKind,
    ProjectRef,
    ProjectSnapshot,
    TaskContext,
    attempt_glue,
    build_lens,
    canonical_json,
    stable_digest,
)


def build_fixture() -> dict[str, Any]:
    project = ProjectRef(
        project_id="fixture.research-software",
        canonical_location="pointer:examples/research_software_witness",
        project_kind="ai-assisted-research-software",
        owner_or_custodian="fixture-owner",
        source_identity="fixture-source-v1",
        access_policy="local-public-fixture",
        currentness_policy="pinned-digest",
    )
    snapshot = ProjectSnapshot(
        snapshot_id="snapshot:fixture-v1",
        project_ref=project,
        observed_at="2026-08-17T00:00:00+00:00",
        source_refs=("pointer:README", "pointer:issue-1", "pointer:commit-a"),
        source_digests=(stable_digest("README"), stable_digest("issue-1"), stable_digest("commit-a")),
        observation_boundary="fixture metadata only",
        currentness="PINNED",
        privacy_class="PUBLIC_FIXTURE",
    )
    chart = DomainChart(
        chart_id="chart:software-research:v1",
        domain="software-research",
        version="1",
        local_types=("task", "blocker", "decision", "artifact", "actor", "episode", "evidence", "assertion"),
        local_relations=("blocks", "depends_on", "produced", "proposed_by", "executed_by", "verified_by"),
        identity_rules=("commit identity is not scientific-contribution identity",),
        local_invariants=("source pointers remain external-authoritative",),
        local_failure_states=("stale source", "ambiguous attribution"),
        shared_core_mappings={"task": "EpisodeRef", "artifact": "ArtifactRef", "actor": "ActorRef"},
        known_nonmappings=("commit_author != scientific_contributor",),
    )
    continuation_task = TaskContext(
        task_context_id="task:continuation:v1",
        goal="resume the project and identify the next lawful action",
        target_use="private project reentry",
        questions=("what blocks continuation?", "where should work reenter?"),
        audience_or_actor="project owner",
        temporal_horizon="next bounded work episode",
        observation_handles=("issues", "decisions", "artifacts"),
        allowed_semantics=("task", "blocker", "dependency", "currentness", "reentry"),
        forbidden_semantics=("automatic authorship", "scientific truth"),
        budget={"max_objects": 20},
        privacy_policy="private-by-default",
        claim_ceiling="operational reentry candidate only",
        evaluator_or_success_conditions=("exact blocker and reentry are present",),
    )
    contribution_task = TaskContext(
        task_context_id="task:contribution:v1",
        goal="explain bounded human, AI, tool, and joint contributions",
        target_use="contribution review",
        questions=("who proposed?", "who executed?", "what evidence exists?"),
        audience_or_actor="project owner or selected collaborator",
        temporal_horizon="bounded project episode",
        observation_handles=("activity", "artifacts", "evidence"),
        allowed_semantics=("actor", "episode", "intervention", "evidence", "assertion"),
        forbidden_semantics=("sole authorship inference", "mastery inference"),
        budget={"max_objects": 20},
        privacy_policy="selective projection",
        claim_ceiling="bounded contribution description only",
        evaluator_or_success_conditions=("ambiguous and joint states remain explicit",),
    )
    continuation_loss = InformationLossReport(
        semantic_loss=("detailed human/AI contribution semantics",),
        attribution_loss=("typed contribution roles omitted",),
        reversibility="PARTIAL",
        materiality_by_task={"continuation": "acceptable", "contribution": "disqualifying"},
    )
    contribution_loss = InformationLossReport(
        structural_loss=("complete operational dependency state",),
        execution_loss=("exact runtime reentry omitted",),
        reversibility="PARTIAL",
        materiality_by_task={"contribution": "acceptable", "continuation": "disqualifying"},
    )
    continuation_lens = build_lens(
        snapshot=snapshot,
        task=continuation_task,
        charts=(chart,),
        construction_rule="select operational continuation objects and relations",
        selected_objects=("task", "blocker", "decision", "artifact", "dependency", "currentness", "reentry"),
        selected_relations=("blocks", "depends_on", "produced", "supersedes", "reenter_at"),
        omitted_objects=("detailed contribution assertion",),
        omitted_relations=("proposed_by", "verified_by"),
        assumptions=("fixture currentness is pinned",),
        information_loss=continuation_loss,
        provenance_refs=snapshot.source_refs,
        currentness="PINNED",
        privacy_projection="PRIVATE",
        claim_ceiling=continuation_task.claim_ceiling,
    )
    contribution_lens = build_lens(
        snapshot=snapshot,
        task=contribution_task,
        charts=(chart,),
        construction_rule="select contribution, intervention, evidence, and assertion objects",
        selected_objects=("actor", "episode", "intervention", "decision", "artifact", "evidence", "assertion"),
        selected_relations=("proposed_by", "selected_by", "executed_by", "corrected_by", "verified_by", "attested_by"),
        omitted_objects=("complete dependency graph", "runtime reentry"),
        omitted_relations=("blocks", "reenter_at"),
        assumptions=("fixture identities are bounded to one episode",),
        information_loss=contribution_loss,
        provenance_refs=snapshot.source_refs,
        currentness="PINNED",
        privacy_projection="SELECTIVE",
        claim_ceiling=contribution_task.claim_ceiling,
    )
    shared_mapping = LensMapping(
        mapping_id="mapping:continuation-contribution-shared-core:v1",
        kind=MappingKind.ALIGNMENT,
        source_lens_or_chart=continuation_lens.lens_id,
        target_lens_or_chart=contribution_lens.lens_id,
        correspondences={"artifact": "artifact", "decision": "decision", "task": "episode"},
        preconditions=("same project snapshot",),
        preserved_invariants=("source identity", "artifact identity"),
        added_assumptions=(),
        information_loss=InformationLossReport(reversibility="PARTIAL"),
        provenance_continuity=True,
        attribution_continuity=True,
        privacy_compatibility=True,
        version_compatibility=True,
        claim_ceiling="shared core only",
        local_refinements_preserved=True,
    )
    shared_result = attempt_glue(
        continuation_lens,
        contribution_lens,
        shared_mapping,
        shared_core=("artifact", "decision", "episode/task"),
        local_refinements={
            "continuation": ("blocker", "dependency", "reentry"),
            "contribution": ("actor", "intervention", "evidence", "assertion"),
        },
    )
    invalid_mapping = LensMapping(
        mapping_id="mapping:commit-author-to-scientific-contributor:v1",
        kind=MappingKind.TRANSLATION,
        source_lens_or_chart="lens:git-commit-author",
        target_lens_or_chart=contribution_lens.lens_id,
        correspondences={"commit.author": "scientific_contributor"},
        preconditions=("same identity string",),
        preserved_invariants=(),
        added_assumptions=("commit authorship equals scientific contribution",),
        information_loss=InformationLossReport(
            semantic_loss=("scientific role semantics",),
            evidential_loss=("contribution evidence",),
            attribution_loss=("typed roles",),
            reversibility="NO",
            materiality_by_task={"contribution": "disqualifying"},
        ),
        provenance_continuity=True,
        attribution_continuity=False,
        privacy_compatibility=True,
        version_compatibility=True,
        claim_ceiling="no scientific-contribution claim",
        semantic_compatible=False,
        identity_coherent=True,
        evidence_scope_compatible=False,
        material_loss_acceptable=False,
    )
    invalid_result = attempt_glue(continuation_lens, contribution_lens, invalid_mapping)
    payload = {
        "schema_version": "project-semantics.fixture.project-lens.v0",
        "project_ref": asdict(project),
        "snapshot": asdict(snapshot),
        "domain_chart": asdict(chart),
        "lenses": {"continuation": asdict(continuation_lens), "contribution": asdict(contribution_lens)},
        "loss_reports": {
            continuation_loss.report_id: asdict(continuation_loss),
            contribution_loss.report_id: asdict(contribution_loss),
        },
        "gluing": {
            "shared_core": asdict(shared_result),
            "invalid_commit_author_claim": asdict(invalid_result),
        },
        "nonclaims": [
            "no canonical project representation",
            "no globally optimal lens",
            "no automatic scientific-contribution inference",
            "no external authority admission",
        ],
    }
    payload["fixture_digest"] = stable_digest(payload)
    return payload


def fixture_json() -> str:
    return canonical_json(build_fixture()) + "\n"
