from __future__ import annotations

from copy import deepcopy
import unittest

from repeat_use_harness.counterfactual import (
    ANALYSIS_SCHEMA,
    BUNDLE_SCHEMA,
    CARRYOVER_SCHEMA,
    CLAIM_CEILING,
    EXPOSURE_SCHEMA,
    MISSINGNESS_SCHEMA,
    PARITY_RULES,
    PARITY_SCHEMA,
    PROGRAM_ID,
    RESET_SCHEMA,
    SCHEDULE_SCHEMA,
    build_repair_manifest,
    content_digest,
    qualify_counterfactual_assignment,
)

D = lambda text: "sha256:" + (text.encode().hex() + "0" * 64)[:64]


def base_epoch():
    return {
        "epoch_id": "epoch:cf:v1",
        "product_phase_id": "phase:ruv:v1",
        "source_snapshot_digest": D("source"),
        "measurement_policy_digest": D("measure"),
        "evaluator_policy_digest": D("evaluator"),
        "outcome_visibility_snapshot_digest": D("blind"),
    }


def schedule(*, sid="schedule:1", participant="participant:1", trajectory="trajectory:1", inquiry="inquiry:1", condition="C0_MANUAL_ORDINARY_WORKFLOW", method="SIMPLE_RANDOMIZED", period=1, period_count=1, assigned_at="2026-08-19T09:00:00Z", first_exposure="2026-08-19T09:05:00Z"):
    return {
        "schema_version": SCHEDULE_SCHEMA,
        "schedule_id": sid,
        "participant_id": participant,
        "trajectory_id": trajectory,
        "epoch_id": "epoch:cf:v1",
        "project_id": "project:real",
        "inquiry_id": inquiry,
        "allocation_unit": "INQUIRY",
        "stratum_id": "stratum:matched",
        "block_id": "block:1",
        "sequence_id": "sequence:AB",
        "period_index": period,
        "period_count": period_count,
        "condition_id": condition,
        "assignment_method": method,
        "allocation_probability_or_rule": 0.5 if method in {"SIMPLE_RANDOMIZED", "BLOCK_RANDOMIZED"} else "predeclared-rule:v1",
        "allocation_rule_digest": D("allocation"),
        "assigned_at": assigned_at,
        "first_exposure_not_before": first_exposure,
        "outcome_blind": True,
        "outcome_visibility_snapshot_digest": D("blind"),
        "source_snapshot_digest": D("source"),
        "product_phase_id": "phase:ruv:v1",
        "measurement_policy_digest": D("measure"),
        "evaluator_policy_digest": D("evaluator"),
        "history_state_digest": D("history"),
        "claim_ceiling": CLAIM_CEILING,
    }


def carryover():
    return {
        "schema_version": CARRYOVER_SCHEMA,
        "ledger_id": "ledger:1",
        "participant_id": "participant:1",
        "trajectory_id": "trajectory:1",
        "assessed_at": "2026-08-19T08:55:00Z",
        "prior_exposures": [],
        "non_overlap_confirmed": True,
        "minimum_delay_seconds": 0,
        "irreversible_learning_carryover": False,
        "decision": "CLEAN",
        "claim_ceiling": CLAIM_CEILING,
    }


def reset_receipt():
    return {
        "schema_version": RESET_SCHEMA,
        "receipt_id": "reset:1",
        "participant_id": "participant:1",
        "trajectory_id": "trajectory:1",
        "history_condition": "C3_F2_EMPTY_HISTORY",
        "prior_history_refs": ["history:old"],
        "cleared_store_digests": [D("old-store")],
        "empty_state_digest": D("empty"),
        "verification_method": "independent content-addressed empty-state check",
        "verified_at": "2026-08-19T08:58:00Z",
        "verifier_id": "verifier:independent",
        "complete": True,
        "operator_assertion_only": False,
        "claim_ceiling": CLAIM_CEILING,
    }


def parity():
    return {
        "schema_version": PARITY_SCHEMA,
        "receipt_id": "parity:1",
        "arm_ids": ["C0_MANUAL_ORDINARY_WORKFLOW", "C4_F2_ACCUMULATED_VALID_HISTORY"],
        "source_snapshot_digest": D("source"),
        "task_block_digest": D("task"),
        "clock_policy_digest": D("clock"),
        "budget_digest": D("budget"),
        "familiarization_digest": D("familiarization"),
        "interface_digest": D("interface"),
        "measurement_dose_digest": D("dose"),
        "evaluator_policy_digest": D("evaluator"),
        "assistance_policy_digest": D("assistance"),
        "parity_checks": {rule: True for rule in PARITY_RULES},
        "formed_at": "2026-08-19T08:59:00Z",
        "claim_ceiling": CLAIM_CEILING,
    }


def missingness(records=None):
    return {
        "schema_version": MISSINGNESS_SCHEMA,
        "policy_id": "missingness:1",
        "records": list(records or []),
        "no_imputation": True,
        "terminal_precedence": [
            "CONSENT_WITHDRAWN_STOP",
            "ACCESSIBILITY_BLOCKED_NOT_NEGATIVE_VALUE",
            "NON_IDENTIFIABLE",
            "RIGHT_CENSORED_OR_MISSINGNESS_REVIEW",
            "RIGHT_CENSORED",
        ],
        "formed_at": "2026-08-19T08:54:00Z",
        "claim_ceiling": CLAIM_CEILING,
    }


def analysis():
    return {
        "schema_version": ANALYSIS_SCHEMA,
        "plan_id": "analysis:1",
        "design": "PARALLEL_RANDOMIZED",
        "estimands": ["bounded assignment effect on reentry burden"],
        "unit_of_analysis": "episode",
        "cluster_unit": "participant_project",
        "paired_unit": "matched_inquiry_stratum",
        "repeated_measures_method": "cluster_robust_within_participant",
        "sequence_period_sensitivity": "predeclared",
        "carryover_sensitivity": "exclude contaminated and report split",
        "missingness_strategy": "typed censoring; no imputation",
        "multiplicity_control": "HOLM",
        "thresholds": {"alpha": 0.05},
        "claim_consequences": {"positive": "bounded assignment evidence only", "negative": "no safe counterfactual claim"},
        "frozen_at": "2026-08-19T08:50:00Z",
        "policy_digest": D("analysis"),
        "claim_ceiling": CLAIM_CEILING,
    }


def exposure(*, sid="schedule:1", eid="episode:1", assigned="C0_MANUAL_ORDINARY_WORKFLOW", received=None, status="AS_ASSIGNED", bypass=False):
    if received is None:
        received = assigned
    return {
        "schema_version": EXPOSURE_SCHEMA,
        "receipt_id": "exposure:" + eid,
        "schedule_id": sid,
        "episode_id": eid,
        "assigned_condition_id": assigned,
        "received_condition_id": received,
        "exposure_started_at": "2026-08-19T09:05:00Z",
        "exposure_ended_at": "2026-08-19T09:25:00Z",
        "exposure_status": status,
        "dose": 1.0 if status == "AS_ASSIGNED" else 0.5,
        "bypass": bypass,
        "noncompliance_reason": None if status == "AS_ASSIGNED" else "fixture",
        "crossover_from": assigned if status == "CROSSOVER" else None,
        "crossover_to": received if status == "CROSSOVER" else None,
        "formed_at": "2026-08-19T09:26:00Z",
        "claim_ceiling": CLAIM_CEILING,
    }


def bundle():
    return {
        "schema_version": BUNDLE_SCHEMA,
        "bundle_id": "bundle:counterfactual:1",
        "program_id": PROGRAM_ID,
        "schedules": [schedule()],
        "carryover_ledger": carryover(),
        "reset_integrity_receipts": [],
        "comparator_parity_receipt": parity(),
        "missingness_policy": missingness(),
        "analysis_plan": analysis(),
        "exposure_receipts": [exposure()],
        "human_outcomes_complete": True,
        "first_outcome_visible_at": "2026-08-19T09:30:00Z",
        "claim_ceiling": CLAIM_CEILING,
    }


def missing_record(reason, *, outcome_related=False, condition_dependent=False):
    return {
        "episode_id": "episode:1",
        "reason": reason,
        "observed_at": "2026-08-19T09:27:00Z",
        "before_exposure": False,
        "condition_dependent": condition_dependent,
        "outcome_related": outcome_related,
        "censoring_effect": "typed fixture consequence",
    }


class CounterfactualAssignmentRepairTests(unittest.TestCase):
    def q(self, value):
        return qualify_counterfactual_assignment(value, epoch=base_epoch())["disposition"]

    def test_manifest_is_pointer_slim_and_nonpromoting(self):
        manifest = build_repair_manifest()
        self.assertEqual(manifest["artifact_id"], "CounterfactualAssignmentRepair.v1")
        self.assertEqual(manifest["prior_wave_payload_bytes_embedded"], 0)
        self.assertFalse(manifest["positive_human_terminal_enabled"])
        digest = manifest.pop("artifact_digest")
        self.assertEqual(digest, content_digest(manifest))

    def test_s01_to_s10(self):
        cases = []
        b = bundle(); cases.append(("S01", b, "COUNTERFACTUAL_ASSIGNMENT_ADMISSIBLE"))
        b = bundle(); b["schedules"] = []; cases.append(("S02", b, "INVALID_NO_PROSPECTIVE_ASSIGNMENT"))
        b = bundle(); b["schedules"][0]["outcome_blind"] = False; cases.append(("S03", b, "INVALID_OUTCOME_BLINDNESS"))
        b = bundle(); b["schedules"][0]["condition_id"] = "UNKNOWN"; cases.append(("S04", b, "INVALID_CONDITION_ASSIGNMENT"))
        b = bundle(); b["carryover_ledger"]["non_overlap_confirmed"] = False; cases.append(("S05", b, "CARRYOVER_UNCONTROLLED"))
        b = bundle(); b["schedules"][0]["assignment_method"] = "whatever"; cases.append(("S06", b, "INVALID_ASSIGNMENT_METHOD"))
        b = bundle(); b["schedules"][0]["assigned_at"] = "2026-08-19T09:06:00Z"; cases.append(("S07", b, "INVALID_RETROSPECTIVE_SUBSTITUTION"))
        b = bundle(); b["schedules"][0]["outcome_visibility_snapshot_digest"] = D("visible"); cases.append(("S08", b, "NON_IDENTIFIABLE"))
        b = bundle(); b["exposure_receipts"][0]["assigned_condition_id"] = "C1_GENERIC_PROJECT_MEMORY"; b["exposure_receipts"][0]["received_condition_id"] = "C1_GENERIC_PROJECT_MEMORY"; cases.append(("S09", b, "INVALID_CONDITION_ASSIGNMENT"))
        b = bundle(); b["schedules"][0]["product_phase_id"] = "phase:drift"; cases.append(("S10", b, "ASSIGNMENT_OR_SURFACE_DRIFT"))
        for sid, value, expected in cases:
            with self.subTest(sid=sid): self.assertEqual(self.q(value), expected)

    def test_s11_to_s20(self):
        cases = []
        b = bundle(); b["schedules"] = [
            schedule(sid="schedule:a", inquiry="inquiry:a", condition="C0_MANUAL_ORDINARY_WORKFLOW", method="COUNTERBALANCED_CROSSOVER", period=1, period_count=2),
            schedule(sid="schedule:b", inquiry="inquiry:b", condition="C4_F2_ACCUMULATED_VALID_HISTORY", method="COUNTERBALANCED_CROSSOVER", period=2, period_count=2, first_exposure="2026-08-20T09:05:00Z"),
        ]; b["exposure_receipts"] = [
            exposure(sid="schedule:a", eid="episode:a"),
            {**exposure(sid="schedule:b", eid="episode:b", assigned="C4_F2_ACCUMULATED_VALID_HISTORY"), "exposure_started_at":"2026-08-20T09:05:00Z", "exposure_ended_at":"2026-08-20T09:25:00Z", "formed_at":"2026-08-20T09:26:00Z"},
        ]; cases.append(("S11", b, "COUNTERFACTUAL_ASSIGNMENT_ADMISSIBLE"))
        b2 = deepcopy(b); b2["schedules"][0]["sequence_id"]="sequence:AB"; b2["schedules"][1]["sequence_id"]="sequence:BA"; cases.append(("S12", b2, "COUNTERFACTUAL_ASSIGNMENT_ADMISSIBLE"))
        b = bundle(); b["schedules"][0]["assignment_method"]="DETERMINISTIC_PREDECLARED"; b["schedules"][0]["allocation_probability_or_rule"]="alternating:v1"; cases.append(("S13", b, "SENSITIVITY_DOWNGRADE"))
        b = deepcopy(b2); b["schedules"][1]["inquiry_id"] = b["schedules"][0]["inquiry_id"]; cases.append(("S14", b, "SPLIT_OR_REPLAN"))
        for sid, etype in (("S15","TASK"),("S16","ANSWER"),("S17","SELECTED_ACTION")):
            b = bundle(); b["carryover_ledger"]["prior_exposures"]=[{"exposure_type":etype,"source_ref":"prior:1","occurred_at":"2026-08-18T09:00:00Z","relevant_to_current_inquiry":True}]; cases.append((sid,b,"NON_IDENTIFIABLE"))
        b = bundle(); b["schedules"][0]["condition_id"]="C3_F2_EMPTY_HISTORY"; b["exposure_receipts"][0]["assigned_condition_id"]="C3_F2_EMPTY_HISTORY"; b["exposure_receipts"][0]["received_condition_id"]="C3_F2_EMPTY_HISTORY"; b["reset_integrity_receipts"]=[{**reset_receipt(),"complete":False}]; cases.append(("S18",b,"HISTORY_CONDITION_INVALID"))
        b = bundle(); b["schedules"][0]["product_phase_id"]="phase:drift"; cases.append(("S19",b,"ASSIGNMENT_OR_SURFACE_DRIFT"))
        b = bundle(); b["schedules"][0]["measurement_policy_digest"] = D("drift"); cases.append(("S20",b,"MEASUREMENT_OR_PRODUCT_DRIFT"))
        for sid, value, expected in cases:
            with self.subTest(sid=sid): self.assertEqual(self.q(value), expected)

    def test_s21_to_s30(self):
        cases=[]
        b=bundle(); b["schedules"][0]["source_snapshot_digest"] = D("different"); cases.append(("S21",b,"ASSIGNMENT_OR_SURFACE_DRIFT"))
        b=bundle(); b["schedules"][0]["evaluator_policy_digest"] = D("changed"); cases.append(("S22",b,"NON_IDENTIFIABLE"))
        b=bundle(); b["human_outcomes_complete"]=False; b["missingness_policy"]=missingness([missing_record("REQUIRED_HUMAN_OUTCOME_ABSENT")]); cases.append(("S23",b,"RIGHT_CENSORED"))
        b=deepcopy(b); b["carryover_ledger"]["prior_exposures"]=[{"exposure_type":"HISTORY","source_ref":"prior:history","occurred_at":"2026-08-18T09:00:00Z","relevant_to_current_inquiry":True}]; cases.append(("S24",b,"NON_IDENTIFIABLE"))
        b=bundle(); b["missingness_policy"]=missingness([missing_record("CONSENT_WITHDRAWN")]); cases.append(("S25",b,"CONSENT_WITHDRAWN_STOP"))
        b=bundle(); b["missingness_policy"]=missingness([missing_record("ACCESSIBILITY_BLOCKED")]); cases.append(("S26",b,"ACCESSIBILITY_BLOCKED_NOT_NEGATIVE_VALUE"))
        b=bundle(); b["exposure_receipts"]=[exposure(status="BYPASS", bypass=True)]; cases.append(("S27",b,"BYPASS_SEPARATE_AGENCY"))
        b=bundle(); b["missingness_policy"]=missingness([missing_record("ABANDONMENT_UNKNOWN")]); cases.append(("S28",b,"RIGHT_CENSORED_OR_MISSINGNESS_REVIEW"))
        b=bundle(); b["missingness_policy"]=missingness([missing_record("OUTCOME_DEPENDENT_ATTRITION", outcome_related=True, condition_dependent=True)]); cases.append(("S29",b,"NON_IDENTIFIABLE"))
        b=bundle(); b["schedules"].append(schedule(sid="schedule:2", inquiry="inquiry:2", condition="C4_F2_ACCUMULATED_VALID_HISTORY", period=2, period_count=2, first_exposure="2026-08-20T09:05:00Z")); b["exposure_receipts"].append({**exposure(sid="schedule:2",eid="episode:2",assigned="C4_F2_ACCUMULATED_VALID_HISTORY"),"exposure_started_at":"2026-08-20T09:05:00Z","exposure_ended_at":"2026-08-20T09:25:00Z","formed_at":"2026-08-20T09:26:00Z"}); b["analysis_plan"]["repeated_measures_method"]="NONE"; cases.append(("S30",b,"CLUSTER_AWARE_ANALYSIS_REQUIRED"))
        for sid,value,expected in cases:
            with self.subTest(sid=sid): self.assertEqual(self.q(value), expected)

    def test_s31_to_s36(self):
        cases=[]
        b=bundle(); b["schedules"][0]["assignment_method"]="OBSERVATIONAL_VOLUNTARY"; b["schedules"][0]["allocation_probability_or_rule"]="voluntary-choice:v1"; cases.append(("S31",b,"OBSERVATIONAL_ASSOCIATION_ONLY"))
        b=bundle(); b["exposure_receipts"]=[exposure(status="NONCOMPLIANT")]; cases.append(("S32",b,"COMPLIANCE_OR_AS_TREATED_SENSITIVITY_REQUIRED"))
        b=bundle(); b["analysis_plan"]["frozen_at"]="2026-08-19T09:31:00Z"; cases.append(("S33",b,"ANALYSIS_POLICY_DRIFT"))
        b=bundle(); b["analysis_plan"]["estimands"]=["a","b"]; b["analysis_plan"]["multiplicity_control"]="NONE"; cases.append(("S34",b,"MULTIPLICITY_REPAIR_REQUIRED"))
        b=bundle(); b["comparator_parity_receipt"]["parity_checks"]["P06_INTERFACE_FAMILIARIZATION"]=False; cases.append(("S35",b,"COMPARATOR_CONTAMINATION"))
        b=bundle(); b["schedules"].append(schedule(sid="schedule:2",participant="participant:2",trajectory="trajectory:2",inquiry="inquiry:2",condition="C4_F2_ACCUMULATED_VALID_HISTORY")); b["exposure_receipts"].append(exposure(sid="schedule:2",eid="episode:2",assigned="C4_F2_ACCUMULATED_VALID_HISTORY")); cases.append(("S36",b,"COUNTERFACTUAL_ASSIGNMENT_ADMISSIBLE"))
        for sid,value,expected in cases:
            with self.subTest(sid=sid): self.assertEqual(self.q(value), expected)


if __name__ == "__main__":
    unittest.main()
