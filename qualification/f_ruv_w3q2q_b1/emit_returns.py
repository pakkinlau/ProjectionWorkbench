#!/usr/bin/env python3
"""Emit canonical pointer-slim N2B returns for F.RUV.W3Q2Q.B1."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
from typing import Any


def canonical_digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()).hexdigest()


def write(path: Path, value: dict[str, Any]) -> None:
    value = dict(value)
    value["artifact_digest"] = canonical_digest(value)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--result", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    out = args.output_dir
    out.mkdir(parents=True, exist_ok=True)
    result = json.loads(args.result.read_text(encoding="utf-8"))
    success = result["coordinate_pass"] is True
    common = {
        "schema_version": "stewardstack.branch-return.v1",
        "program_id": result["program_id"],
        "wave_id": result["wave_id"],
        "branch_id": result["branch_id"],
        "route_launch_digest": result["target_binding"]["route_launch_digest"],
        "stewardstack_commit": result["target_binding"]["stewardstack_commit"],
        "route_semantic_tree": result["target_binding"]["route_semantic_tree"],
        "execution_posture": "GITHUB_ACTIONS_INDEPENDENT_TARGET_NONMUTATING_QUALIFICATION",
        "authorization_basis": "owner request in active GVA v0.6 Task F chat",
        "claim_boundary": result["claim_ceiling"],
    }
    branch_return = {
        **common,
        "artifact_id": "F.RUV.W3Q2Q.B1.BranchReturn.v1",
        "artifact_state": result["artifact_state"],
        "inputs_consumed": [
            "F.RUV.W3Q2R.N3.RollingSynthesisAndSteeringDecision",
            "FinalIntegratedW3RTarget.v2@sha256:208226ea0c9aa010dd7d9820d4e64d6ec2e6c44fb26fc29074713a0cc6aab611",
            "GitHubArtifact:pakkinlau/ProjectionWorkbench/actions/artifacts/9383501449",
            "W3Q2TargetCompatibilitySet.v1[Q7=RERUN_REQUIRED]",
        ],
        "source_pins": {
            "projectionworkbench_target_carrier_head": "1097ca27503e6ee02abfbc080d6f8df2e1d023fc",
            "target_carrier_workflow_run": 32302418259,
            "target_carrier_artifact_id": 9383501449,
            "target_carrier_zip_sha256": "19ec1745dcab9ab269d5ef5cc62bc83beefb5d41d45135348dcb2de437222e6f",
            "target_archive_sha256": result["target_binding"]["archive_sha256"],
            "target_identity": result["target_binding"]["target_identity"],
        },
        "work_performed": [
            "verified the complete target-carrier artifact, target identity, archive digest and 171-file manifest",
            "executed the 128-test integrated repository suite from the corrected target",
            "reran the 31-case R1-R5 schema/currentness/tamper/revocation witness",
            "executed four isolated fresh-agent R6 source/wheel installations with six cases each",
            "verified source/source/wheel byte parity and target nonmutation",
            "preserved the human-value and Wave-4 claim ceiling",
        ],
        "material_outputs": [
            "CorrectedTargetSchemaCurrentnessReplayQualification.v1.json",
            "SchemaCurrentnessReplayRepair.rerun.json",
            "fresh-source-a.json",
            "fresh-source-b.json",
            "fresh-wheel-a.json",
            "fresh-wheel-b.json",
            "TargetVerificationReceipt.v1.json",
            "TargetNonmutationReceipt.v1.json",
            "BranchCompletionReceipt.v1.json",
            "WorkerReturn.*.json",
        ],
        "terminal_object": {
            "artifact_id": result["artifact_id"],
            "artifact_digest": result["artifact_digest"],
            "terminal_disposition": result["terminal_disposition"],
            "coordinate": result["coordinate"],
            "coordinate_pass": result["coordinate_pass"],
        },
        "completion_predicate_result": "PASS" if success else "FAIL",
        "validation_or_review": result["qualification_summary"],
        "claim_updates": {
            "Q7": "PASS_CANDIDATE_PENDING_N3" if success else "REPAIR_REQUIRED",
            "Q1_Q6": "UNCHANGED_PRESERVED",
            "Q8": "PENDING_SIBLING_RETURN",
            "wave_4_open": False,
        },
        "design_gaps": [
            "F.RUV.W3Q2Q.B2 full independent validity attack return remains required",
            "N3 conjunctive acceptance of preserved Q1-Q6 plus fresh Q7-Q8 remains pending",
        ],
        "merge_payload": {
            "destination": "F.RUV.W3Q2Q.RollingSynthesis",
            "coordinate": "Q7",
            "terminal": result["terminal_disposition"],
            "target_identity": result["target_binding"]["target_identity"],
        },
        "blockers_and_reentry": result["exact_reentry"],
        "learning_or_no_learning_consequence": "NoLearningConsequence",
    }
    write(out / "BranchReturn.v1.json", branch_return)

    worker_specs = [
        (
            "W1",
            "TARGET_CARRIER_AND_CURRENTNESS_VERIFICATION",
            {
                "target_identity": result["target_binding"]["target_identity"],
                "tree_digest": result["target_binding"]["tree_digest"],
                "archive_sha256": result["target_binding"]["archive_sha256"],
                "manifest": result["manifest_verification"],
            },
        ),
        (
            "W2",
            "R1_R5_SCHEMA_CURRENTNESS_TAMPER_REVOCATION_REPLAY",
            result["r1_r5"],
        ),
        (
            "W3",
            "R6_FRESH_AGENT_SOURCE_WHEEL_REPLAY",
            result["r6"],
        ),
        (
            "W4",
            "QUALIFICATION_SYNTHESIS_NONMUTATION_AND_CLAIM_CEILING",
            {
                "checks": result["checks"],
                "target_nonmutation": result["target_nonmutation"],
                "coordinate_pass": result["coordinate_pass"],
                "terminal_disposition": result["terminal_disposition"],
                "human_value_supported": False,
                "wave_4_open": False,
            },
        ),
    ]
    for worker_id, role, payload in worker_specs:
        worker = {
            "schema_version": "stewardstack.worker-return.v1",
            "artifact_id": f"F.RUV.W3Q2Q.B1.WorkerReturn.{worker_id}.v1",
            "program_id": result["program_id"],
            "wave_id": result["wave_id"],
            "branch_id": result["branch_id"],
            "worker_id": worker_id,
            "role": role,
            "status": "PASS" if success else "REPAIR_REQUIRED",
            "payload": payload,
            "source_pointers_only": True,
            "predecessor_payload_embedded_bytes": 0,
            "claim_boundary": result["claim_ceiling"],
        }
        write(out / f"WorkerReturn.{worker_id}.v1.json", worker)

    completion = {
        "schema_version": "stewardstack.branch-completion-receipt.v1",
        "artifact_id": "F.RUV.W3Q2Q.B1.BranchCompletionReceipt.v1",
        "program_id": result["program_id"],
        "wave_id": result["wave_id"],
        "branch_id": result["branch_id"],
        "route_launch_digest": result["target_binding"]["route_launch_digest"],
        "terminal_object": result["artifact_id"],
        "terminal_object_digest": result["artifact_digest"],
        "completion_predicate": "corrected target verified; R1-R5 31/31; R6 four installations 6/6 with parity; target unmodified; claim ceiling preserved",
        "completion_predicate_result": "PASS" if success else "FAIL",
        "accepted_current": False,
        "acceptance_authority": "F.RUV.W3Q2Q N3 web.synthesize -> web.steer",
        "exact_reentry": result["exact_reentry"],
    }
    write(out / "BranchCompletionReceipt.v1.json", completion)

    no_learning = {
        "schema_version": "stewardstack.no-learning-consequence.v1",
        "artifact_id": "F.RUV.W3Q2Q.B1.NoLearningConsequence.v1",
        "program_id": result["program_id"],
        "branch_id": result["branch_id"],
        "policy_or_model_updated": False,
        "accepted_project_state_mutated": False,
        "prospective_human_trajectory_executed": False,
        "frontier_changes": [
            "fresh corrected-target Q7 qualification candidate produced",
            "Wave 4 remains closed pending Q8 and N3 conjunction",
        ],
    }
    write(out / "NoLearningConsequence.v1.json", no_learning)

    cross_home = {
        "schema_version": "stewardstack.cross-home-return.v1",
        "artifact_id": "F.RUV.W3Q2Q.B1.CrossHomeReturn.v1",
        "from_home": "GitHubActions/local.task",
        "to_home": "web.branch",
        "branch_id": result["branch_id"],
        "status": "RETURNED",
        "terminal": result["terminal_disposition"],
        "merge_destination": "F.RUV.W3Q2Q.RollingSynthesis",
        "claim_boundary": result["claim_ceiling"],
    }
    write(out / "CrossHomeReturn.v1.json", cross_home)

    action_transition = {
        "schema_version": "stewardstack.action-transition-return.v1",
        "artifact_id": "F.RUV.W3Q2Q.B1.ActionTransitionReturn.v1",
        "branch_id": result["branch_id"],
        "route": "web.route -> web.branch -> web.reentry -> local.task -> core.intake -> core.work -> local.worker/core.action -> local.cross-home -> web.branch",
        "status": "COMPLETE" if success else "REPAIR_REQUIRED",
        "next_prompt_id": "web.synthesize",
        "next_merge_requires": ["F.RUV.W3Q2Q.B1", "F.RUV.W3Q2Q.B2"],
    }
    write(out / "ActionTransitionReturn.v1.json", action_transition)

    index = sorted(path.name for path in out.iterdir() if path.is_file())
    (out / "ARTIFACT_INDEX.txt").write_text("\n".join(index) + "\n", encoding="utf-8")
    return 0 if success else 1


if __name__ == "__main__":
    raise SystemExit(main())
