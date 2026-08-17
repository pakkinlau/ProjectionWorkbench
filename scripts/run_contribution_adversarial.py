#!/usr/bin/env python3
"""F2.W3.B4 controlled contribution/evidence adversarial witness."""
from __future__ import annotations
import argparse, json
from pathlib import Path
from project_semantics import ValidationError, validate_contribution

BASE={"episode_ref":"episode:test","source_refs":["trace:test"],"origin":"human"}
def rec(cid,actor,role,mode,state,ceiling,scope,evidence=(),origin="human"):
    return {**BASE,"contribution_id":cid,"actor_ref":actor,"contribution_role":role,
      "contribution_mode":mode,"assertion_state":state,"claim_ceiling":ceiling,
      "scope":scope,"evidence_refs":list(evidence),"origin":origin}
CASES=[
("AI_EXECUTED_HUMAN_FRAMED",True,rec("c01","human:alice","frame","human_directed_ai_executed","human_confirmed","framing only","selected objective",["decision:1"])),
("AI_PROPOSAL_REMAINS_PROPOSED",True,rec("c02","ai:model","propose","ai_primary_human_reviewed","proposed","proposal only","candidate",origin="agent")),
("HUMAN_REJECTS_AI",True,rec("c03","human:alice","reject","human_directed_ai_executed","human_confirmed","rejection only","rejected c02",["decision:3"])),
("HUMAN_CORRECTS_AI_ASSUMPTION",True,rec("c04","human:bob","correct","human_directed_ai_executed","human_confirmed","correction only","removed leakage",["diff:4"])),
("REVIEW_NOT_VERIFY",True,rec("c05","human:carol","review","ai_primary_human_reviewed","observed","review only; not independently verified","requested revisions")),
("JOINT_INSEPARABLE",True,rec("c06","collective:human-ai","joint_design","joint_inseparable","unresolved","joint and unresolved","co-construction",origin="collective")),
("DISPUTED",True,rec("c07","human:dana","select","joint_separable","disputed","disputed","candidate selection",["statement:a","statement:b"])),
("ATTESTATION_WITHOUT_ATTESTOR",False,rec("c08","human:erin","verify","independent","third_party_attested","bounded observation","anonymous attestation",["attestation:anonymous"])),
("AI_SELF_PROMOTION",False,rec("c09","ai:model","expert","ai_primary_human_reviewed","independently_assessed","expert","self assessment",["trace:9"],"agent")),
("ACTIVITY_VOLUME_TO_CAPABILITY",False,rec("c10","human:frank","universal_expert","tool_mediated","independently_assessed","expert across domain","activity count",["activity:1","activity:2","activity:3"])),
("OUTPUT_TO_MASTERY",False,rec("c11","human:gina","mastered_entire_system","ai_primary_human_reviewed","human_confirmed","full mastery","AI artifact delivered",["artifact:11"])),
("REVOKE_WITHOUT_TRANSITION",False,rec("c12","human:henry","frame","independent","revoked","revoked","unspecified revocation")),
("SUPERSEDE_WITHOUT_PRIOR_REF",False,rec("c13","human:iris","correct","independent","superseded","narrower claim","no prior assertion ref")),
("ASSESSMENT_WITHOUT_EVIDENCE_SCOPE",False,rec("c14","human:jules","verify","independent","independently_assessed","bounded verification","unspecified protocol",["report:14"])),
("PROMOTED_WITH_EMPTY_EVIDENCE",False,rec("c15","human:kai","verify","independent","human_confirmed","confirmation","no evidence")),
]

def run():
    rows=[]
    for cid,desired,record in CASES:
        accepted=True; error=None
        try: validate_contribution(record)
        except ValidationError as exc: accepted=False; error=str(exc)
        rows.append({"case_id":cid,"desired_accept":desired,"kernel_accepted":accepted,
                     "policy_match":accepted is desired,"kernel_error":error})
    mismatches=[r for r in rows if not r["policy_match"]]
    return {"schema_version":"gva06.f2.contribution-boundary-adversarial-assessment.v1",
      "source_kernel":{"repository":"pakkinlau/ProjectionWorkbench","commit":"2d5af1ea356258bd163e55bbf30cf988da5e2970"},
      "case_count":len(rows),"policy_match_count":len(rows)-len(mismatches),
      "policy_mismatch_count":len(mismatches),"disposition":"REPAIR_REQUIRED" if mismatches else "PASS",
      "case_results":rows,
      "first_zeros":["CAPABILITY_ASSERTION_SEPARATION_ABSENT","ATTESTATION_AND_ASSESSOR_SCOPE_CONTRACT_ABSENT","ASSERTION_TRANSITION_CONTRACT_ABSENT","STRUCTURED_EVIDENCE_SCOPE_ABSENT"],
      "claim_ceiling":"Bounded adversarial assessment only; no authorship, mastery, capability, market, or authority claim."}

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--output",type=Path,required=True); args=ap.parse_args()
    report=run(); args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(report,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print(json.dumps({k:report[k] for k in ["case_count","policy_mismatch_count","disposition"]},sort_keys=True))
    return 0
if __name__=="__main__": raise SystemExit(main())
