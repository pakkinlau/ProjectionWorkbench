"""Task-relative project lens and local-to-global gluing kernel.

The module is intentionally small and brand-neutral. It implements a bounded
subset of TaskRelativeRepresentationContract.v1 without claiming a universal
ontology or a globally optimal project representation.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import Enum
import hashlib
import json
from typing import Any, Mapping, Sequence


class MappingKind(str, Enum):
    RESTRICTION = "RESTRICTION"
    PROJECTION = "PROJECTION"
    TRANSLATION = "TRANSLATION"
    ALIGNMENT = "ALIGNMENT"
    ADAPTER = "ADAPTER"
    COMPOSITION = "COMPOSITION"
    ATTESTATION = "ATTESTATION"


class ObstructionKind(str, Enum):
    INSUFFICIENT_OBSERVATION = "INSUFFICIENT_OBSERVATION"
    IDENTITY_INCOHERENCE = "IDENTITY_INCOHERENCE"
    SEMANTIC_MISMATCH = "SEMANTIC_MISMATCH"
    TYPE_MISMATCH = "TYPE_MISMATCH"
    EVIDENCE_SCOPE_MISMATCH = "EVIDENCE_SCOPE_MISMATCH"
    ATTRIBUTION_COLLAPSE = "ATTRIBUTION_COLLAPSE"
    TEMPORAL_INCOHERENCE = "TEMPORAL_INCOHERENCE"
    VERSION_INCOMPATIBLE = "VERSION_INCOMPATIBLE"
    PRIVACY_POLICY_CONFLICT = "PRIVACY_POLICY_CONFLICT"
    PERMISSION_CONFLICT = "PERMISSION_CONFLICT"
    INFORMATION_LOSS_MATERIAL = "INFORMATION_LOSS_MATERIAL"
    GRAMMAR_INSUFFICIENT = "GRAMMAR_INSUFFICIENT"
    NON_IDENTIFIABLE = "NON_IDENTIFIABLE"


class GlobalizationDisposition(str, Enum):
    GLOBAL_SECTION = "GLOBAL_SECTION"
    SHARED_CORE_WITH_LOCAL_REFINEMENTS = "SHARED_CORE_WITH_LOCAL_REFINEMENTS"
    PARTIAL_GLUE = "PARTIAL_GLUE"
    NO_SAFE_GLOBALIZATION = "NO_SAFE_GLOBALIZATION"
    NON_IDENTIFIABLE = "NON_IDENTIFIABLE"
    GRAMMAR_INSUFFICIENT = "GRAMMAR_INSUFFICIENT"
    SOURCE_REENTRY_REQUIRED = "SOURCE_REENTRY_REQUIRED"


def _plain(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if hasattr(value, "__dataclass_fields__"):
        return {key: _plain(item) for key, item in asdict(value).items()}
    if isinstance(value, Mapping):
        return {str(key): _plain(item) for key, item in value.items()}
    if isinstance(value, (tuple, list, set, frozenset)):
        return [_plain(item) for item in value]
    return value


def canonical_json(value: Any) -> str:
    return json.dumps(_plain(value), sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def stable_digest(value: Any) -> str:
    return "sha256:" + hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class ProjectRef:
    project_id: str
    canonical_location: str
    project_kind: str
    owner_or_custodian: str
    source_identity: str
    access_policy: str
    currentness_policy: str


@dataclass(frozen=True)
class ProjectSnapshot:
    snapshot_id: str
    project_ref: ProjectRef
    observed_at: str
    source_refs: tuple[str, ...]
    source_digests: tuple[str, ...]
    observation_boundary: str
    currentness: str
    privacy_class: str


@dataclass(frozen=True)
class TaskContext:
    task_context_id: str
    goal: str
    target_use: str
    questions: tuple[str, ...]
    audience_or_actor: str
    temporal_horizon: str
    observation_handles: tuple[str, ...]
    allowed_semantics: tuple[str, ...]
    forbidden_semantics: tuple[str, ...]
    budget: Mapping[str, Any]
    privacy_policy: str
    claim_ceiling: str
    evaluator_or_success_conditions: tuple[str, ...]


@dataclass(frozen=True)
class DomainChart:
    chart_id: str
    domain: str
    version: str
    local_types: tuple[str, ...]
    local_relations: tuple[str, ...]
    identity_rules: tuple[str, ...]
    local_invariants: tuple[str, ...]
    local_failure_states: tuple[str, ...]
    shared_core_mappings: Mapping[str, str]
    known_nonmappings: tuple[str, ...]


@dataclass(frozen=True)
class InformationLossReport:
    structural_loss: tuple[str, ...] = ()
    semantic_loss: tuple[str, ...] = ()
    evidential_loss: tuple[str, ...] = ()
    attribution_loss: tuple[str, ...] = ()
    temporal_loss: tuple[str, ...] = ()
    uncertainty_loss: tuple[str, ...] = ()
    privacy_redaction: tuple[str, ...] = ()
    execution_loss: tuple[str, ...] = ()
    reversibility: str = "UNKNOWN"
    materiality_by_task: Mapping[str, str] | None = None

    @property
    def report_id(self) -> str:
        return stable_digest(self)


@dataclass(frozen=True)
class ProjectLens:
    lens_id: str
    project_snapshot_ref: str
    task_context_ref: str
    domain_chart_refs: tuple[str, ...]
    construction_rule: str
    selected_objects: tuple[str, ...]
    selected_relations: tuple[str, ...]
    omitted_objects: tuple[str, ...]
    omitted_relations: tuple[str, ...]
    assumptions: tuple[str, ...]
    information_loss_ref: str
    provenance_refs: tuple[str, ...]
    currentness: str
    privacy_projection: str
    claim_ceiling: str


@dataclass(frozen=True)
class LensMapping:
    mapping_id: str
    kind: MappingKind
    source_lens_or_chart: str
    target_lens_or_chart: str
    correspondences: Mapping[str, str]
    preconditions: tuple[str, ...]
    preserved_invariants: tuple[str, ...]
    added_assumptions: tuple[str, ...]
    information_loss: InformationLossReport
    provenance_continuity: bool
    attribution_continuity: bool
    privacy_compatibility: bool
    version_compatibility: bool
    claim_ceiling: str
    type_compatible: bool = True
    semantic_compatible: bool | None = True
    identity_coherent: bool | None = True
    permission_compatible: bool = True
    evidence_scope_compatible: bool | None = True
    material_loss_acceptable: bool = True
    vocabulary_available: bool = True
    bounded_partial_relation: bool = False
    local_refinements_preserved: bool = False


@dataclass(frozen=True)
class ObstructionReport:
    obstruction_id: str
    location: str
    kinds: tuple[ObstructionKind, ...]
    evidence_refs: tuple[str, ...]
    affected_task: str
    affected_claim: str
    first_zero: str
    missing_operand: str
    owner_class: str
    repair_options: tuple[str, ...]
    exact_reentry: str


@dataclass(frozen=True)
class GlobalizationResult:
    disposition: GlobalizationDisposition
    mapping_id: str
    shared_core: tuple[str, ...]
    local_refinements: Mapping[str, tuple[str, ...]]
    information_loss: InformationLossReport
    obstruction: ObstructionReport | None
    claim_ceiling: str


def build_lens(
    *,
    snapshot: ProjectSnapshot,
    task: TaskContext,
    charts: Sequence[DomainChart],
    construction_rule: str,
    selected_objects: Sequence[str],
    selected_relations: Sequence[str],
    omitted_objects: Sequence[str],
    omitted_relations: Sequence[str],
    assumptions: Sequence[str],
    information_loss: InformationLossReport,
    provenance_refs: Sequence[str],
    currentness: str,
    privacy_projection: str,
    claim_ceiling: str,
) -> ProjectLens:
    identity_payload = {
        "project_snapshot": snapshot.snapshot_id,
        "task_context": task.task_context_id,
        "chart_versions": [(chart.chart_id, chart.version) for chart in charts],
        "construction_rule": construction_rule,
        "selected_objects": tuple(selected_objects),
        "selected_relations": tuple(selected_relations),
        "omitted_objects": tuple(omitted_objects),
        "omitted_relations": tuple(omitted_relations),
        "assumptions": tuple(assumptions),
        "information_loss_ref": information_loss.report_id,
        "privacy_projection": privacy_projection,
        "claim_ceiling": claim_ceiling,
    }
    return ProjectLens(
        lens_id=stable_digest(identity_payload),
        project_snapshot_ref=snapshot.snapshot_id,
        task_context_ref=task.task_context_id,
        domain_chart_refs=tuple(chart.chart_id for chart in charts),
        construction_rule=construction_rule,
        selected_objects=tuple(selected_objects),
        selected_relations=tuple(selected_relations),
        omitted_objects=tuple(omitted_objects),
        omitted_relations=tuple(omitted_relations),
        assumptions=tuple(assumptions),
        information_loss_ref=information_loss.report_id,
        provenance_refs=tuple(provenance_refs),
        currentness=currentness,
        privacy_projection=privacy_projection,
        claim_ceiling=claim_ceiling,
    )


def _obstruction(mapping: LensMapping, kinds: Sequence[ObstructionKind]) -> ObstructionReport:
    kinds_tuple = tuple(dict.fromkeys(kinds))
    first = kinds_tuple[0].value if kinds_tuple else "UNKNOWN"
    return ObstructionReport(
        obstruction_id=stable_digest({"mapping": mapping.mapping_id, "kinds": kinds_tuple}),
        location=f"{mapping.source_lens_or_chart}->{mapping.target_lens_or_chart}",
        kinds=kinds_tuple,
        evidence_refs=(mapping.mapping_id,),
        affected_task="mapping task declared by caller",
        affected_claim=mapping.claim_ceiling,
        first_zero=first,
        missing_operand="explicit repair, translation, evidence, or vocabulary required",
        owner_class="mapping or domain-chart owner",
        repair_options=(
            "supply an explicit semantic translation",
            "supply bounded evidence and attribution continuity",
            "retain local refinements without global identity",
        ),
        exact_reentry="rerun attempt_glue with a revised mapping and unchanged source lens identities",
    )


def attempt_glue(
    source: ProjectLens,
    target: ProjectLens,
    mapping: LensMapping,
    *,
    shared_core: Sequence[str] = (),
    local_refinements: Mapping[str, Sequence[str]] | None = None,
) -> GlobalizationResult:
    """Attempt a task-relative gluing under noncompensatory gates."""

    local = {key: tuple(value) for key, value in (local_refinements or {}).items()}

    if not mapping.vocabulary_available:
        obstruction = _obstruction(mapping, [ObstructionKind.GRAMMAR_INSUFFICIENT])
        return GlobalizationResult(
            GlobalizationDisposition.GRAMMAR_INSUFFICIENT,
            mapping.mapping_id,
            tuple(shared_core),
            local,
            mapping.information_loss,
            obstruction,
            mapping.claim_ceiling,
        )

    unknowns = [mapping.semantic_compatible, mapping.identity_coherent, mapping.evidence_scope_compatible]
    if any(value is None for value in unknowns):
        obstruction = _obstruction(mapping, [ObstructionKind.NON_IDENTIFIABLE])
        return GlobalizationResult(
            GlobalizationDisposition.NON_IDENTIFIABLE,
            mapping.mapping_id,
            tuple(shared_core),
            local,
            mapping.information_loss,
            obstruction,
            mapping.claim_ceiling,
        )

    failures: list[ObstructionKind] = []
    if not mapping.type_compatible:
        failures.append(ObstructionKind.TYPE_MISMATCH)
    if not mapping.semantic_compatible:
        failures.append(ObstructionKind.SEMANTIC_MISMATCH)
    if not mapping.identity_coherent:
        failures.append(ObstructionKind.IDENTITY_INCOHERENCE)
    if not mapping.permission_compatible:
        failures.append(ObstructionKind.PERMISSION_CONFLICT)
    if not mapping.version_compatibility:
        failures.append(ObstructionKind.VERSION_INCOMPATIBLE)
    if not mapping.evidence_scope_compatible:
        failures.append(ObstructionKind.EVIDENCE_SCOPE_MISMATCH)
    if not mapping.attribution_continuity:
        failures.append(ObstructionKind.ATTRIBUTION_COLLAPSE)
    if not mapping.privacy_compatibility:
        failures.append(ObstructionKind.PRIVACY_POLICY_CONFLICT)
    if not mapping.material_loss_acceptable:
        failures.append(ObstructionKind.INFORMATION_LOSS_MATERIAL)

    if failures:
        disposition = (
            GlobalizationDisposition.PARTIAL_GLUE
            if mapping.bounded_partial_relation and mapping.type_compatible and mapping.permission_compatible
            else GlobalizationDisposition.NO_SAFE_GLOBALIZATION
        )
        return GlobalizationResult(
            disposition,
            mapping.mapping_id,
            tuple(shared_core),
            local,
            mapping.information_loss,
            _obstruction(mapping, failures),
            mapping.claim_ceiling,
        )

    disposition = (
        GlobalizationDisposition.SHARED_CORE_WITH_LOCAL_REFINEMENTS
        if mapping.local_refinements_preserved or local
        else GlobalizationDisposition.GLOBAL_SECTION
    )
    return GlobalizationResult(
        disposition,
        mapping.mapping_id,
        tuple(shared_core),
        local,
        mapping.information_loss,
        None,
        mapping.claim_ceiling,
    )
