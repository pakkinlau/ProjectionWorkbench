"""Typed prospective-assignment repair for F.RUV.W3R.B5.

The module keeps assignment, exposure, carryover, reset, parity, missingness and
analysis evidence separate.  It emits lawful negative/right-censored terminals
and never promotes mechanical qualification into human value.
"""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from typing import Any, Mapping

PROGRAM_ID = "GVA06.F.repeat-use-value-discovery.v2"
WAVE_ID = "F.RUV.W3R"
BRANCH_ID = "F.RUV.W3R.B5"
STEWARDSTACK_COMMIT = "a644409f293609ec2e6f0cb230ba0799d455ec1d"
ROUTE_LAUNCH_DIGEST = "a4848d67212416935e25d8f4fc09b3aeee1b62b4c761c5cfd7055eb0e4b26baa"
PROJECTIONWORKBENCH_PARENT = "510c60889d9ed7d3014cb6d9d6607ef7305c141c"
CLAIM_CEILING = (
    "Controlled counterfactual-assignment repair and mechanical qualification "
    "only; no human repeat-use value, retention, accumulated-history benefit, "
    "product direction, interpersonal/network value, market demand, release, "
    "merge, cutover, or owner admission claim."
)
SCHEDULE_SCHEMA = "gva06.f.ruv.prospective-baseline-assignment-schedule.v1"
CARRYOVER_SCHEMA = "gva06.f.ruv.trajectory-carryover-contamination-ledger.v1"
RESET_SCHEMA = "gva06.f.ruv.reset-integrity-receipt.v1"
PARITY_SCHEMA = "gva06.f.ruv.comparator-parity-receipt.v1"
MISSINGNESS_SCHEMA = "gva06.f.ruv.missingness-attrition-abandonment-policy.v1"
ANALYSIS_SCHEMA = "gva06.f.ruv.counterfactual-analysis-plan.v1"
EXPOSURE_SCHEMA = "gva06.f.ruv.actual-exposure-compliance-receipt.v1"
BUNDLE_SCHEMA = "gva06.f.ruv.counterfactual-assignment-bundle.v1"
QUALIFICATION_SCHEMA = "gva06.f.ruv.counterfactual-assignment-qualification.v1"

COMPARATOR_ARMS = {
    "C0_MANUAL_ORDINARY_WORKFLOW", "C1_GENERIC_PROJECT_MEMORY",
    "C2_POINTER_INDEX_ONLY", "C3_F2_EMPTY_HISTORY",
    "C4_F2_ACCUMULATED_VALID_HISTORY", "C5_F2_HISTORY_NEGATIVE_CONTROL_FAMILY",
}
ASSIGNMENT_METHODS = {
    "SIMPLE_RANDOMIZED", "BLOCK_RANDOMIZED", "COUNTERBALANCED_CROSSOVER",
    "DETERMINISTIC_PREDECLARED", "OBSERVATIONAL_VOLUNTARY",
}
ALLOCATION_UNITS = {"EPISODE", "INQUIRY", "TRAJECTORY", "PARTICIPANT_PROJECT"}
EXPOSURE_STATUSES = {"AS_ASSIGNED", "PARTIAL_EXPOSURE", "NONCOMPLIANT", "CROSSOVER", "BYPASS", "NOT_EXPOSED"}
CARRYOVER_TYPES = {"TASK", "ANSWER", "SELECTED_ACTION", "PRODUCT", "HISTORY", "EVALUATOR", "OPERATOR"}
CARRYOVER_DECISIONS = {"CLEAN", "DELAY_REQUIRED", "SPLIT_OR_REPLAN", "NON_IDENTIFIABLE"}
MISSINGNESS_REASONS = {
    "REQUIRED_HUMAN_OUTCOME_ABSENT", "CONSENT_WITHDRAWN", "ACCESSIBILITY_BLOCKED",
    "BYPASS", "ABANDONMENT_UNKNOWN", "OUTCOME_DEPENDENT_ATTRITION",
    "TECHNICAL_FAILURE", "SCHEDULING_FAILURE",
}
PARITY_RULES = {
    "P01_SOURCE_SNAPSHOT", "P02_INFORMATION_VISIBILITY", "P03_TASK_BLOCKS",
    "P04_CLOCK", "P05_BUDGET", "P06_INTERFACE_FAMILIARIZATION",
    "P07_EVALUATOR_FREEZE", "P08_ORDER_BALANCE", "P09_CAPTURE_COST",
    "P10_NO_IMPUTATION", "P11_HISTORY_ELIGIBILITY", "P12_ARM_INTEGRITY",
}
LAWFUL = {
    "COUNTERFACTUAL_ASSIGNMENT_ADMISSIBLE", "INVALID_NO_PROSPECTIVE_ASSIGNMENT",
    "INVALID_OUTCOME_BLINDNESS", "INVALID_CONDITION_ASSIGNMENT",
    "CARRYOVER_UNCONTROLLED", "INVALID_ASSIGNMENT_METHOD",
    "INVALID_RETROSPECTIVE_SUBSTITUTION", "NON_IDENTIFIABLE",
    "ASSIGNMENT_OR_SURFACE_DRIFT", "SENSITIVITY_DOWNGRADE", "SPLIT_OR_REPLAN",
    "HISTORY_CONDITION_INVALID", "MEASUREMENT_OR_PRODUCT_DRIFT", "RIGHT_CENSORED",
    "CONSENT_WITHDRAWN_STOP", "ACCESSIBILITY_BLOCKED_NOT_NEGATIVE_VALUE",
    "BYPASS_SEPARATE_AGENCY", "RIGHT_CENSORED_OR_MISSINGNESS_REVIEW",
    "CLUSTER_AWARE_ANALYSIS_REQUIRED", "OBSERVATIONAL_ASSOCIATION_ONLY",
    "COMPLIANCE_OR_AS_TREATED_SENSITIVITY_REQUIRED", "ANALYSIS_POLICY_DRIFT",
    "MULTIPLICITY_REPAIR_REQUIRED", "COMPARATOR_CONTAMINATION",
}


class CounterfactualValidationError(ValueError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message); self.code = code; self.message = message


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def content_digest(value: Any) -> str:
    return "sha256:" + hashlib.sha256(canonical_bytes(value)).hexdigest()


def _need(r: Mapping[str, Any], fields: tuple[str, ...], kind: str) -> None:
    missing = [f for f in fields if f not in r]
    if missing: raise CounterfactualValidationError("REPAIR_REQUIRED", f"{kind} missing {missing}")


def _text(r: Mapping[str, Any], fields: tuple[str, ...], kind: str) -> None:
    _need(r, fields, kind)
    if any(not isinstance(r[f], str) or not r[f].strip() for f in fields):
        raise CounterfactualValidationError("REPAIR_REQUIRED", f"{kind} requires nonempty text")


def _ts(value: Any, field: str) -> datetime:
    if not isinstance(value, str): raise CounterfactualValidationError("REPAIR_REQUIRED", f"{field} timestamp absent")
    try: d = datetime.fromisoformat(value[:-1] + "+00:00" if value.endswith("Z") else value)
    except ValueError as exc: raise CounterfactualValidationError("REPAIR_REQUIRED", f"invalid {field}") from exc
    if d.tzinfo is None: raise CounterfactualValidationError("REPAIR_REQUIRED", f"{field} timezone absent")
    return d.astimezone(timezone.utc)


def _digest(value: Any, field: str) -> None:
    if not isinstance(value, str) or not value.startswith("sha256:") or len(value) != 71:
        raise CounterfactualValidationError("REPAIR_REQUIRED", f"{field} digest absent")
    try: int(value[7:], 16)
    except ValueError as exc: raise CounterfactualValidationError("REPAIR_REQUIRED", f"invalid {field} digest") from exc


def _ceiling(r: Mapping[str, Any]) -> None:
    if r.get("claim_ceiling") != CLAIM_CEILING: raise CounterfactualValidationError("REPAIR_REQUIRED", "claim ceiling drift")


def validate_assignment_schedule(s: Mapping[str, Any], *, epoch: Mapping[str, Any] | None = None) -> None:
    k = "ProspectiveBaselineAndAssignmentSchedule.v1"
    _text(s, ("schema_version","schedule_id","participant_id","trajectory_id","epoch_id","project_id","inquiry_id","allocation_unit","stratum_id","block_id","sequence_id","condition_id","assignment_method","allocation_rule_digest","assigned_at","first_exposure_not_before","outcome_visibility_snapshot_digest","source_snapshot_digest","product_phase_id","measurement_policy_digest","evaluator_policy_digest","history_state_digest","claim_ceiling"), k)
    _need(s, ("period_index","period_count","allocation_probability_or_rule","outcome_blind"), k)
    if s["schema_version"] != SCHEDULE_SCHEMA: raise CounterfactualValidationError("REPAIR_REQUIRED", "schedule schema drift")
    if s["allocation_unit"] not in ALLOCATION_UNITS: raise CounterfactualValidationError("REPAIR_REQUIRED", "allocation unit invalid")
    if s["condition_id"] not in COMPARATOR_ARMS: raise CounterfactualValidationError("INVALID_CONDITION_ASSIGNMENT", "condition invalid")
    if s["assignment_method"] not in ASSIGNMENT_METHODS: raise CounterfactualValidationError("INVALID_ASSIGNMENT_METHOD", "assignment method invalid")
    if s["outcome_blind"] is not True: raise CounterfactualValidationError("INVALID_OUTCOME_BLINDNESS", "outcome not blind")
    if not isinstance(s["period_index"], int) or not isinstance(s["period_count"], int) or not 1 <= s["period_index"] <= s["period_count"]:
        raise CounterfactualValidationError("REPAIR_REQUIRED", "period invalid")
    if _ts(s["assigned_at"], "assigned_at") >= _ts(s["first_exposure_not_before"], "first_exposure_not_before"):
        raise CounterfactualValidationError("INVALID_RETROSPECTIVE_SUBSTITUTION", "assignment not pre-exposure")
    for f in ("allocation_rule_digest","outcome_visibility_snapshot_digest","source_snapshot_digest","measurement_policy_digest","evaluator_policy_digest","history_state_digest"): _digest(s[f], f)
    rule = s["allocation_probability_or_rule"]
    if s["assignment_method"] in {"SIMPLE_RANDOMIZED","BLOCK_RANDOMIZED"}:
        if not isinstance(rule,(int,float)) or not 0 < float(rule) < 1: raise CounterfactualValidationError("REPAIR_REQUIRED", "probability invalid")
    elif not isinstance(rule,str) or not rule: raise CounterfactualValidationError("REPAIR_REQUIRED", "allocation rule absent")
    if epoch:
        if s["epoch_id"] != epoch.get("epoch_id") or s["product_phase_id"] != epoch.get("product_phase_id") or s["source_snapshot_digest"] != epoch.get("source_snapshot_digest"):
            raise CounterfactualValidationError("ASSIGNMENT_OR_SURFACE_DRIFT", "schedule/epoch drift")
        if s["measurement_policy_digest"] != epoch.get("measurement_policy_digest"): raise CounterfactualValidationError("MEASUREMENT_OR_PRODUCT_DRIFT", "measurement drift")
        if s["evaluator_policy_digest"] != epoch.get("evaluator_policy_digest") or s["outcome_visibility_snapshot_digest"] != epoch.get("outcome_visibility_snapshot_digest"):
            raise CounterfactualValidationError("NON_IDENTIFIABLE", "evaluator/visibility drift")
    _ceiling(s)


def validate_carryover_ledger(r: Mapping[str, Any]) -> None:
    _text(r,("schema_version","ledger_id","participant_id","trajectory_id","assessed_at","decision","claim_ceiling"),"TrajectoryCarryoverAndContaminationLedger.v1")
    _need(r,("prior_exposures","non_overlap_confirmed","minimum_delay_seconds","irreversible_learning_carryover"),"carryover")
    if r["schema_version"] != CARRYOVER_SCHEMA or r["decision"] not in CARRYOVER_DECISIONS: raise CounterfactualValidationError("REPAIR_REQUIRED", "carryover schema/decision invalid")
    _ts(r["assessed_at"],"assessed_at")
    if not isinstance(r["prior_exposures"],list): raise CounterfactualValidationError("REPAIR_REQUIRED","prior exposures invalid")
    for e in r["prior_exposures"]:
        _text(e,("exposure_type","source_ref","occurred_at"),"prior exposure"); _need(e,("relevant_to_current_inquiry",),"prior exposure")
        if e["exposure_type"] not in CARRYOVER_TYPES: raise CounterfactualValidationError("REPAIR_REQUIRED","carryover type invalid")
        _ts(e["occurred_at"],"occurred_at")
    if not isinstance(r["minimum_delay_seconds"],(int,float)) or r["minimum_delay_seconds"] < 0: raise CounterfactualValidationError("REPAIR_REQUIRED","delay invalid")
    if r["decision"] == "CLEAN" and r["non_overlap_confirmed"] is not True: raise CounterfactualValidationError("CARRYOVER_UNCONTROLLED","non-overlap absent")
    if r["irreversible_learning_carryover"] is True and r["decision"] not in {"SPLIT_OR_REPLAN","NON_IDENTIFIABLE"}: raise CounterfactualValidationError("CARRYOVER_UNCONTROLLED","irreversible carryover")
    _ceiling(r)


def validate_reset_integrity_receipt(r: Mapping[str, Any]) -> None:
    _text(r,("schema_version","receipt_id","participant_id","trajectory_id","history_condition","empty_state_digest","verification_method","verified_at","verifier_id","claim_ceiling"),"ResetIntegrityReceipt.v1")
    _need(r,("prior_history_refs","cleared_store_digests","complete","operator_assertion_only"),"reset")
    if r["schema_version"] != RESET_SCHEMA or r["history_condition"] not in COMPARATOR_ARMS: raise CounterfactualValidationError("HISTORY_CONDITION_INVALID","reset identity invalid")
    _digest(r["empty_state_digest"],"empty_state_digest"); _ts(r["verified_at"],"verified_at")
    if r["complete"] is not True or r["operator_assertion_only"] is True: raise CounterfactualValidationError("HISTORY_CONDITION_INVALID","reset unverified")
    for d in r["cleared_store_digests"]: _digest(d,"cleared_store_digest")
    _ceiling(r)


def validate_comparator_parity_receipt(r: Mapping[str, Any]) -> None:
    _text(r,("schema_version","receipt_id","source_snapshot_digest","task_block_digest","clock_policy_digest","budget_digest","familiarization_digest","interface_digest","measurement_dose_digest","evaluator_policy_digest","assistance_policy_digest","formed_at","claim_ceiling"),"ComparatorParityReceipt.v1")
    _need(r,("arm_ids","parity_checks"),"parity")
    if r["schema_version"] != PARITY_SCHEMA or not isinstance(r["arm_ids"],list) or len(set(r["arm_ids"])) < 2: raise CounterfactualValidationError("NON_IDENTIFIABLE","parity arms invalid")
    if not set(r["arm_ids"]).issubset(COMPARATOR_ARMS): raise CounterfactualValidationError("INVALID_CONDITION_ASSIGNMENT","parity arm invalid")
    for f in ("source_snapshot_digest","task_block_digest","clock_policy_digest","budget_digest","familiarization_digest","interface_digest","measurement_dose_digest","evaluator_policy_digest","assistance_policy_digest"): _digest(r[f],f)
    _ts(r["formed_at"],"formed_at")
    if not isinstance(r["parity_checks"],Mapping) or set(r["parity_checks"]) != PARITY_RULES: raise CounterfactualValidationError("REPAIR_REQUIRED","parity checks incomplete")
    _ceiling(r)


def validate_missingness_policy(r: Mapping[str, Any]) -> None:
    _text(r,("schema_version","policy_id","formed_at","claim_ceiling"),"MissingnessAttritionAndAbandonmentPolicy.v1"); _need(r,("records","no_imputation","terminal_precedence"),"missingness")
    if r["schema_version"] != MISSINGNESS_SCHEMA or r["no_imputation"] is not True: raise CounterfactualValidationError("REPAIR_REQUIRED","missingness policy invalid")
    _ts(r["formed_at"],"formed_at"); p=r["terminal_precedence"]
    if not isinstance(p,list) or "NON_IDENTIFIABLE" not in p or "RIGHT_CENSORED" not in p or p.index("NON_IDENTIFIABLE") > p.index("RIGHT_CENSORED"): raise CounterfactualValidationError("REPAIR_REQUIRED","terminal precedence invalid")
    for m in r["records"]:
        _text(m,("episode_id","reason","observed_at","censoring_effect"),"missingness record"); _need(m,("before_exposure","condition_dependent","outcome_related"),"missingness record")
        if m["reason"] not in MISSINGNESS_REASONS: raise CounterfactualValidationError("REPAIR_REQUIRED","missingness reason invalid")
        _ts(m["observed_at"],"observed_at")
    _ceiling(r)


def validate_analysis_plan(r: Mapping[str, Any], *, first_outcome_visible_at: str | None = None) -> None:
    _text(r,("schema_version","plan_id","design","unit_of_analysis","cluster_unit","paired_unit","repeated_measures_method","sequence_period_sensitivity","carryover_sensitivity","missingness_strategy","multiplicity_control","frozen_at","policy_digest","claim_ceiling"),"CounterfactualAnalysisPlan.v1")
    _need(r,("estimands","thresholds","claim_consequences"),"analysis")
    if r["schema_version"] != ANALYSIS_SCHEMA or not isinstance(r["estimands"],list) or not r["estimands"]: raise CounterfactualValidationError("REPAIR_REQUIRED","analysis plan invalid")
    _digest(r["policy_digest"],"policy_digest"); frozen=_ts(r["frozen_at"],"frozen_at")
    if first_outcome_visible_at and frozen >= _ts(first_outcome_visible_at,"first_outcome_visible_at"): raise CounterfactualValidationError("ANALYSIS_POLICY_DRIFT","analysis frozen after outcome")
    _ceiling(r)


def validate_actual_exposure_receipt(r: Mapping[str, Any]) -> None:
    _text(r,("schema_version","receipt_id","schedule_id","episode_id","assigned_condition_id","received_condition_id","exposure_started_at","exposure_ended_at","exposure_status","formed_at","claim_ceiling"),"ActualExposureAndComplianceReceipt.v1")
    _need(r,("dose","bypass","noncompliance_reason","crossover_from","crossover_to"),"exposure")
    if r["schema_version"] != EXPOSURE_SCHEMA or r["assigned_condition_id"] not in COMPARATOR_ARMS or r["received_condition_id"] not in COMPARATOR_ARMS: raise CounterfactualValidationError("INVALID_CONDITION_ASSIGNMENT","exposure condition invalid")
    if r["exposure_status"] not in EXPOSURE_STATUSES: raise CounterfactualValidationError("REPAIR_REQUIRED","exposure status invalid")
    if _ts(r["exposure_started_at"],"exposure_started_at") > _ts(r["exposure_ended_at"],"exposure_ended_at"): raise CounterfactualValidationError("REPAIR_REQUIRED","exposure chronology invalid")
    _ts(r["formed_at"],"formed_at")
    if not isinstance(r["dose"],(int,float)) or not 0 <= float(r["dose"]) <= 1: raise CounterfactualValidationError("REPAIR_REQUIRED","dose invalid")
    if r["bypass"] is True and r["exposure_status"] != "BYPASS": raise CounterfactualValidationError("REPAIR_REQUIRED","bypass status invalid")
    if r["received_condition_id"] != r["assigned_condition_id"] and r["exposure_status"] not in {"CROSSOVER","NONCOMPLIANT"}: raise CounterfactualValidationError("REPAIR_REQUIRED","assignment/exposure mismatch unclassified")
    _ceiling(r)


def validate_counterfactual_bundle(b: Mapping[str, Any], *, epoch: Mapping[str, Any] | None = None) -> None:
    _text(b,("schema_version","bundle_id","program_id","claim_ceiling"),"CounterfactualAssignmentBundle.v1"); _need(b,("schedules","carryover_ledger","reset_integrity_receipts","comparator_parity_receipt","missingness_policy","analysis_plan","exposure_receipts","human_outcomes_complete"),"bundle")
    if b["schema_version"] != BUNDLE_SCHEMA or b["program_id"] != PROGRAM_ID: raise CounterfactualValidationError("REPAIR_REQUIRED","bundle identity invalid")
    if not isinstance(b["schedules"],list) or not b["schedules"]: raise CounterfactualValidationError("INVALID_NO_PROSPECTIVE_ASSIGNMENT","schedule absent")
    for s in b["schedules"]: validate_assignment_schedule(s,epoch=epoch)
    if len({s["schedule_id"] for s in b["schedules"]}) != len(b["schedules"]): raise CounterfactualValidationError("REPAIR_REQUIRED","schedule id duplicate")
    groups: dict[str,list[Mapping[str,Any]]] = {}
    for s in b["schedules"]: groups.setdefault(s["trajectory_id"],[]).append(s)
    for ss in groups.values():
        if len({s["period_index"] for s in ss}) != len(ss): raise CounterfactualValidationError("REPAIR_REQUIRED","period duplicate")
        q: dict[str,set[str]] = {}
        for s in ss: q.setdefault(s["inquiry_id"],set()).add(s["condition_id"])
        if any(len(x)>1 for x in q.values()): raise CounterfactualValidationError("SPLIT_OR_REPLAN","same inquiry reused across arms")
    validate_carryover_ledger(b["carryover_ledger"])
    for r in b["reset_integrity_receipts"]: validate_reset_integrity_receipt(r)
    if any(s["condition_id"]=="C3_F2_EMPTY_HISTORY" for s in b["schedules"]) and not any(r["history_condition"]=="C3_F2_EMPTY_HISTORY" for r in b["reset_integrity_receipts"]): raise CounterfactualValidationError("HISTORY_CONDITION_INVALID","reset receipt absent")
    validate_comparator_parity_receipt(b["comparator_parity_receipt"]); validate_missingness_policy(b["missingness_policy"]); validate_analysis_plan(b["analysis_plan"],first_outcome_visible_at=b.get("first_outcome_visible_at"))
    sm={s["schedule_id"]:s for s in b["schedules"]}
    for r in b["exposure_receipts"]:
        validate_actual_exposure_receipt(r); s=sm.get(r["schedule_id"])
        if not s: raise CounterfactualValidationError("REPAIR_REQUIRED","unknown schedule in exposure")
        if r["assigned_condition_id"] != s["condition_id"]: raise CounterfactualValidationError("INVALID_CONDITION_ASSIGNMENT","exposure/schedule mismatch")
        if _ts(r["exposure_started_at"],"exposure_started_at") < _ts(s["first_exposure_not_before"],"first_exposure_not_before"): raise CounterfactualValidationError("INVALID_RETROSPECTIVE_SUBSTITUTION","exposure too early")
    _ceiling(b)


def qualify_counterfactual_assignment(b: Mapping[str, Any], *, epoch: Mapping[str, Any] | None = None) -> dict[str, Any]:
    try:
        validate_counterfactual_bundle(b,epoch=epoch)
        s=b["schedules"]; l=b["carryover_ledger"]; p=b["comparator_parity_receipt"]; m=b["missingness_policy"]; a=b["analysis_plan"]; x=b["exposure_receipts"]
        reasons={r["reason"] for r in m["records"]}
        if "CONSENT_WITHDRAWN" in reasons: d="CONSENT_WITHDRAWN_STOP"
        elif "ACCESSIBILITY_BLOCKED" in reasons: d="ACCESSIBILITY_BLOCKED_NOT_NEGATIVE_VALUE"
        elif "OUTCOME_DEPENDENT_ATTRITION" in reasons or any(r["condition_dependent"] or r["outcome_related"] for r in m["records"]): d="NON_IDENTIFIABLE"
        elif any(e["relevant_to_current_inquiry"] for e in l["prior_exposures"]) or l["decision"]=="NON_IDENTIFIABLE": d="NON_IDENTIFIABLE"
        elif l["decision"]=="SPLIT_OR_REPLAN": d="SPLIT_OR_REPLAN"
        elif any(v is not True for v in p["parity_checks"].values()): d="COMPARATOR_CONTAMINATION" if p["parity_checks"].get("P06_INTERFACE_FAMILIARIZATION") is False else "NON_IDENTIFIABLE"
        elif any(r["exposure_status"]=="BYPASS" for r in x) or "BYPASS" in reasons: d="BYPASS_SEPARATE_AGENCY"
        elif any(r["exposure_status"] in {"NONCOMPLIANT","CROSSOVER","PARTIAL_EXPOSURE","NOT_EXPOSED"} for r in x): d="COMPLIANCE_OR_AS_TREATED_SENSITIVITY_REQUIRED"
        elif "ABANDONMENT_UNKNOWN" in reasons: d="RIGHT_CENSORED_OR_MISSINGNESS_REVIEW"
        elif len(a["estimands"])>1 and a["multiplicity_control"]=="NONE": d="MULTIPLICITY_REPAIR_REQUIRED"
        elif a["repeated_measures_method"]=="NONE" and len({q["participant_id"] for q in s})<len(s): d="CLUSTER_AWARE_ANALYSIS_REQUIRED"
        elif any(q["assignment_method"]=="OBSERVATIONAL_VOLUNTARY" for q in s): d="OBSERVATIONAL_ASSOCIATION_ONLY"
        elif any(q["assignment_method"]=="DETERMINISTIC_PREDECLARED" for q in s): d="SENSITIVITY_DOWNGRADE"
        elif b["human_outcomes_complete"] is not True or "REQUIRED_HUMAN_OUTCOME_ABSENT" in reasons: d="RIGHT_CENSORED"
        else: d="COUNTERFACTUAL_ASSIGNMENT_ADMISSIBLE"
        checks=[{"check":"typed_record_validation","status":"PASS"}]
    except CounterfactualValidationError as exc:
        d=exc.code; checks=[{"check":"typed_record_validation","status":"FAIL_CLOSED","detail":exc.message}]
    if d not in LAWFUL: d="NON_IDENTIFIABLE"
    r={"schema_version":QUALIFICATION_SCHEMA,"program_id":PROGRAM_ID,"branch_id":BRANCH_ID,"bundle_id":b.get("bundle_id"),"disposition":d,"lawful_terminal":True,"counterfactual_claim_eligible":d=="COUNTERFACTUAL_ASSIGNMENT_ADMISSIBLE","human_value_supported":False,"checks":checks,"bundle_digest":content_digest(b),"claim_ceiling":CLAIM_CEILING}
    r["qualification_digest"]=content_digest(r); return r


def build_repair_manifest() -> dict[str, Any]:
    r={"schema_version":"gva06.f.ruv.counterfactual-assignment-repair.v1","artifact_id":"CounterfactualAssignmentRepair.v1","artifact_state":"EXECUTED_VALIDATED_MERGEABLE_CANDIDATE","program_id":PROGRAM_ID,"wave_id":WAVE_ID,"branch_id":BRANCH_ID,"source_pins":{"stewardstack_commit":STEWARDSTACK_COMMIT,"route_launch_digest":ROUTE_LAUNCH_DIGEST,"projectionworkbench_parent":PROJECTIONWORKBENCH_PARENT},"typed_records":["ProspectiveBaselineAndAssignmentSchedule.v1","TrajectoryCarryoverAndContaminationLedger.v1","ResetIntegrityReceipt.v1","ComparatorParityReceipt.v1","MissingnessAttritionAndAbandonmentPolicy.v1","CounterfactualAnalysisPlan.v1","ActualExposureAndComplianceReceipt.v1"],"positive_human_terminal_enabled":False,"prior_wave_payload_bytes_embedded":0,"claim_ceiling":CLAIM_CEILING}
    r["artifact_digest"]=content_digest(r); return r
