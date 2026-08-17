"""Brand-neutral local project semantics primitives."""

from .representation import (
    DomainChart,
    GlobalizationDisposition,
    GlobalizationResult,
    InformationLossReport,
    LensMapping,
    MappingKind,
    ObstructionKind,
    ObstructionReport,
    ProjectLens,
    ProjectRef,
    ProjectSnapshot,
    TaskContext,
    attempt_glue,
    build_lens,
    stable_digest,
)

__all__ = [
    "DomainChart",
    "GlobalizationDisposition",
    "GlobalizationResult",
    "InformationLossReport",
    "LensMapping",
    "MappingKind",
    "ObstructionKind",
    "ObstructionReport",
    "ProjectLens",
    "ProjectRef",
    "ProjectSnapshot",
    "TaskContext",
    "attempt_glue",
    "build_lens",
    "stable_digest",
]
