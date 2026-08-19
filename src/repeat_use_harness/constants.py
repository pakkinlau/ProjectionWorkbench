"""Canonical constants for F.RUV.W2.B1."""
PROGRAM_ID = "GVA06.F.repeat-use-value-discovery.v2"
BRANCH_ID = "F.RUV.W2.B1"
WAVE_ID = "F.RUV.W2"
HARNESS_SCHEMA_VERSION = "gva06.f.ruv.repeat-use-value-discovery-harness.v1"
EVENT_SCHEMA_VERSION = "gva06.f.ruv.repeat-use-event.v1"
EPISODE_SCHEMA_VERSION = "gva06.f.ruv.user-value-episode.v1"
TRAJECTORY_SCHEMA_VERSION = "gva06.f.ruv.user-value-trajectory.v1"
CLAIM_CEILING = (
    "Harness/component construction and R0 mechanical replay only; no human "
    "repeat-use value, retention, product direction, interpersonal value, "
    "hosted necessity, market demand, release, or owner admission claim."
)
ROUTE_LAUNCH_DIGEST = "a4848d67212416935e25d8f4fc09b3aeee1b62b4c761c5cfd7055eb0e4b26baa"
STEWARDSTACK_COMMIT = "a644409f293609ec2e6f0cb230ba0799d455ec1d"
PROJECTIONWORKBENCH_BASE = "19cab543f1350a3fb51770745b68b91980ad4a03"

SOURCE_TERMINALS = (
    "ComparatorBaselinePortfolio.v1",
    "FRepeatUseSourceControlBoundary.v2",
    "ParticipantAgencyHeterogeneityProtocol.v1",
    "RepeatUseInstrumentationContract.v2",
    "RepeatUseTrajectoryProtocol.v2",
    "RepeatUseValueCausalModel.v2",
    "TemporalResumptionDesign.v1",
    "ValueDiscoveryIdentifiabilityAudit.v2",
)

REQUIRED_CONTROL_SURFACES = (
    "RepeatUseExperimentEpoch.v1",
    "ProspectiveBaselineAndAssignmentSchedule.v1",
    "TrajectoryCarryoverAndContaminationLedger.v1",
    "InstrumentationDoseAndBurdenPolicy.v1",
    "NoncompensatoryOutcomeVectorAndDecisionLaw.v1",
    "MissingnessAttritionAndAbandonmentPolicy.v1",
    "VoluntaryReuseObservationWindow.v1",
    "IndependentOutcomeReviewContract.v1",
    "AnalysisMultiplicityAndPolicyDigestRegister.v1",
    "DelayedReentrySchedule.v1",
)

EVENT_REQUIRED_METADATA = (
    "program_id",
    "trajectory_id",
    "episode_id",
    "condition_id",
    "schema_version",
    "event_type",
    "timestamp",
    "source_refs",
    "consent_scope_snapshot",
    "feature_flag_snapshot",
    "claim_ceiling",
)

REQUIRED_FEATURE_FLAGS = (
    "history_enabled",
    "semantic_lens_enabled",
    "provenance_view_enabled",
    "capture_tier",
    "fresh_agent_mode",
)

CONSENT_SCOPES = (
    "local_operational_capture",
    "human_judgment_capture",
    "artifact_export",
    "share_or_merge_with_another_party",
    "research_reuse_or_training",
    "future_recontact",
)

HUMAN_ONLY_FIELDS = (
    "capture_review_burden_acceptable_confirmed_by_human",
    "contribution_proposal_correction_by_human",
    "future_reuse_intent",
    "history_materially_helped_confirmed_by_human",
    "next_action_changed_confirmed_by_human",
    "reentry_better_than_baseline_confirmed_by_human",
    "reentry_better_than_baseline_judgment",
    "representation_fit_judgment",
    "trust_and_control_judgment",
    "usefulness_confirmed_by_human",
    "usefulness_judgment",
    "would_voluntarily_reuse_confirmed_by_human",
    "human_usefulness_judgment",
    "human_next_action_change_judgment",
    "history_reuse_judgment",
    "voluntary_reuse_or_bypass",
    "correction_reason",
)

BURDEN_DIMENSIONS = (
    "capture_minutes",
    "review_and_correction_minutes",
    "cognitive_load",
    "switching_friction",
    "privacy_concern",
    "trust_or_control_loss",
    "lock_in_dependence",
    "error_recovery_cost",
)

COMPARATOR_ARMS = (
    "C0_MANUAL_ORDINARY_WORKFLOW",
    "C1_GENERIC_PROJECT_MEMORY",
    "C2_POINTER_INDEX_ONLY",
    "C3_F2_EMPTY_HISTORY",
    "C4_F2_ACCUMULATED_VALID_HISTORY",
    "C5_F2_HISTORY_NEGATIVE_CONTROL_FAMILY",
)
MANDATORY_COMPARATOR_ARMS = (
    "C0_MANUAL_ORDINARY_WORKFLOW",
    "C1_GENERIC_PROJECT_MEMORY",
    "C3_F2_EMPTY_HISTORY",
    "C4_F2_ACCUMULATED_VALID_HISTORY",
)

PARITY_RULES = (
    "P01_SOURCE_SNAPSHOT",
    "P02_INFORMATION_VISIBILITY",
    "P03_TASK_BLOCKS",
    "P04_CLOCK",
    "P05_BUDGET",
    "P06_INTERFACE_FAMILIARIZATION",
    "P07_EVALUATOR_FREEZE",
    "P08_ORDER_BALANCE",
    "P09_CAPTURE_COST",
    "P10_NO_IMPUTATION",
    "P11_HISTORY_ELIGIBILITY",
    "P12_ARM_INTEGRITY",
)

AGENCY_EVENT_TYPES = (
    "VOLUNTARY_REUSE",
    "PROMPTED_REUSE",
    "FORCED_PROTOCOL_USE",
    "BYPASS",
    "ABANDONMENT",
    "CONSENT_WITHDRAWN",
    "ACCESSIBILITY_BLOCKED",
    "AGENCY_UNIDENTIFIABLE",
)

EVENT_TYPES = (
    "EPISODE_STARTED",
    "SOURCE_POINTER_OPENED",
    "FIRST_USEFUL_LENS_MARKED",
    "EXACT_REENTRY_IDENTIFIED",
    "BURDEN_RECORDED",
    "HUMAN_JUDGMENT_RECORDED",
    "CONTAMINATION_RECORDED",
    "HIDDEN_STATE_DEPENDENCE_RECORDED",
    "MEASUREMENT_REACTIVITY_RECORDED",
    "EPISODE_ENDED",
    *AGENCY_EVENT_TYPES,
)

INSTRUMENTATION_TERMINALS = (
    "INSTRUMENTATION_READY",
    "CAPTURE_COST_TOO_HIGH",
    "MEASUREMENT_REACTIVE",
    "CONSENT_SCOPE_ABSENT",
    "ACCESSIBILITY_BLOCKED",
    "HIDDEN_STATE_DEPENDENCE",
    "NON_IDENTIFIABLE",
    "RIGHT_CENSORED",
    "NO_SAFE",
)

TRAJECTORY_TERMINALS = (
    "REPEAT_USE_SUPPORTED",
    "IMMEDIATE_VALUE_ONLY",
    "ACCUMULATION_NOT_SUPPORTED",
    "CAPTURE_COST_TOO_HIGH",
    "NO_VOLUNTARY_REUSE",
    "NEGATIVE_NET_VALUE",
    "NON_IDENTIFIABLE",
    "RIGHT_CENSORED",
    "PROTOCOL_VIOLATION",
)

CAUSAL_TERMINAL_PRIORITY = (
    "HARM_OR_TRUST_BREACH",
    "RIGHT_CENSORED",
    "NON_IDENTIFIABLE",
    "MEASUREMENT_REACTIVE",
    "CAPTURE_COST_TOO_HIGH",
    "NEGATIVE_NET_VALUE",
    "RETENTION_WITHOUT_VALUE",
    "ACCUMULATION_EFFECT_NOT_OBSERVED",
    "EPISODE_VALUE_ONLY",
    "VALUE_WITHOUT_REPEAT_NEED",
    "HETEROGENEOUS_CONTEXT_DEPENDENT",
    "REPEAT_USE_VALUE_SUPPORTED_BOUNDED",
    "NO_SAFE_PRODUCT_STEERING",
)

POSITIVE_TERMINALS = {
    "REPEAT_USE_SUPPORTED",
    "REPEAT_USE_VALUE_SUPPORTED_BOUNDED",
    "REPEAT_USE_VALUE_SUPPORTED_AT_BOUND_N_OF_1_CEILING",
}

FORBIDDEN_RAW_PAYLOAD_KEYS = {
    "raw_content",
    "raw_source_bytes",
    "source_bytes",
    "message_body",
    "document_body",
    "private_raw_text",
}

EVIDENCE_RUNG_ORDER = {
    "R0_MECHANICAL": 0,
    "R1_HUMAN_BOUND_EPISODE": 1,
    "R2_PAIRED_EPISODE": 2,
    "R3_REPEAT_TRAJECTORY": 3,
    "R4_MECHANISM_SPECIFIC": 4,
    "R5_GENERALIZATION": 5,
}
