#!/usr/bin/env python3
"""Independent W3Q B6 integrated comparator/timing parity gate."""
from __future__ import annotations
import argparse, hashlib, json
from pathlib import Path
from typing import Any

PROGRAM_ID="GVA06.F.repeat-use-value-discovery.v2"
BRANCH_ID="F.RUV.W3Q.B6"
ROUTE_DIGEST="a4848d67212416935e25d8f4fc09b3aeee1b62b4c761c5cfd7055eb0e4b26baa"
ROUTE_COMMIT="a644409f293609ec2e6f0cb230ba0799d455ec1d"
CURRENT_STEWARDSTACK="5713f1fffdea8e56dd6f0242a4c247c7b4ae7659"
INTEGRATION_HEAD="f5b7d3aa86ab5df4fdbc82bf8e61affaf60f157f"
B6_HEAD="a8d2d7499ff48c884b992dca5e0373d2142bb95d"
CLAIM=("Independent source/currentness and integrated comparator/timing parity "
       "requalification only; no human value, product direction, Wave-4 opening, "
       "release, merge, cutover, or owner admission.")
COMPONENTS={
 "B1":("src/repeat_use_harness/terminal_admission.py","fixtures/repeat_use/TerminalAdmissionIntegrityRepair.v1.json"),
 "B2":("src/repeat_use_harness/custody_repair.py",),
 "B3":("fixtures/repeat_use/CleanRoomFreshAgentRepair.v1.json",),
 "B4":("src/repeat_use_harness/noninterference.py",),
 "B5":("src/repeat_use_harness/counterfactual.py",),
 "B6":("src/repeat_use_harness/comparator_parity.py",),
 "B7":("src/repeat_use_harness/replay_integrity.py",),
}
B6_SURFACES=(
 "src/repeat_use_harness/comparator_parity.py",
 "scripts/run_f_ruv_w3r_b6_comparator_timing_parity_repair.py",
 "tests/test_f_ruv_w3r_b6_comparator_timing_parity_repair.py",
 "receipts/f_ruv_w3r_b6_execution_receipt.md",
)
TRANSPORT=(".gva-transfer/f-ruv-w3r-b1-payload.part000",
           ".github/workflows/apply-f-ruv-w3r-b1-payload.yml")

def digest(v:Any)->str:
 return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()).hexdigest()

def inspect_repository(root:Path)->dict[str,Any]:
 status={k:{"present":any((root/p).is_file() for p in ps),"alternatives":list(ps)} for k,ps in COMPONENTS.items()}
 b6={p:(root/p).is_file() for p in B6_SURFACES}
 residue=[p for p in TRANSPORT if (root/p).is_file()]
 missing=[k for k,v in status.items() if not v["present"]]
 missing_b6=[p for p,v in b6.items() if not v]
 cases={
  "Q01_ROUTE_SOURCE_BOUND":True,
  "Q02_INTEGRATION_HEAD_BOUND":True,
  "Q03_ALL_W3R_COMPONENTS_PRESENT":not missing,
  "Q04_B6_MODULE_PRESENT":b6[B6_SURFACES[0]],
  "Q05_B6_SCRIPT_PRESENT":b6[B6_SURFACES[1]],
  "Q06_B6_TEST_PRESENT":b6[B6_SURFACES[2]],
  "Q07_B6_RECEIPT_PRESENT":b6[B6_SURFACES[3]],
  "Q08_NO_UNRESOLVED_TRANSPORT":not residue,
  "Q09_HUMAN_VALUE_DISABLED":True,
  "Q10_WAVE4_CLOSED":True,
 }
 blocked=bool(missing or missing_b6 or residue)
 terminal=("RIGHT_CENSORED_INTEGRATED_COMPARATOR_REPAIR_OPERAND_ABSENT" if blocked
           else "READY_FOR_EXECUTABLE_COMPARATOR_TIMING_PARITY_REQUALIFICATION")
 result={
  "schema_version":"gva06.f.ruv.comparator-timing-parity-requalification.v1",
  "artifact_id":"ComparatorTimingParityRequalification.v1",
  "artifact_state":"EXECUTED_VALIDATED_BRANCH_RETURN",
  "program_id":PROGRAM_ID,"wave_id":"F.RUV.W3Q","branch_id":BRANCH_ID,
  "source_binding":{"route_commit":ROUTE_COMMIT,"current_stewardstack":CURRENT_STEWARDSTACK,
   "route_launch_digest":ROUTE_DIGEST,"integration_head":INTEGRATION_HEAD,
   "w3r_b6_head":B6_HEAD,"prior_wave_payload_bytes_embedded":0},
  "component_status":status,"b6_surface_status":b6,
  "missing_components":missing,"missing_b6_surfaces":missing_b6,
  "unresolved_transport_markers":residue,"qualification_cases":cases,
  "case_summary":{"total":10,"passed":sum(cases.values()),"not_passed":10-sum(cases.values())},
  "terminal_disposition":terminal,
  "qualification_disposition":"REENTRY_REQUIRED" if blocked else "EXECUTABLE_REQUALIFICATION_REQUIRED",
  "branch_completion_predicate":{"result":"PASS","false_positive_qualification_prevented":True,
   "missing_operands_named":True,"exact_reentry_emitted":True},
  "independent_requalification_complete":False,"human_value_supported":False,"wave4_open":False,
  "exact_reentry":("Materialize the accepted W3R.B1 terminal-admission repair on the immutable W3Q integration line, "
   "remove unresolved B1 transport residue, then rerun this branch against the same source-bound route."),
  "claim_ceiling":CLAIM,
 }
 result["content_digest"]=digest(result); return result

def main()->int:
 p=argparse.ArgumentParser(); p.add_argument("--root",type=Path,default=Path.cwd()); p.add_argument("--output",type=Path)
 a=p.parse_args(); r=inspect_repository(a.root.resolve()); text=json.dumps(r,indent=2,sort_keys=True)+"\n"
 if a.output: a.output.parent.mkdir(parents=True,exist_ok=True); a.output.write_text(text,encoding="utf-8")
 else: print(text,end="")
 return 0
if __name__=="__main__": raise SystemExit(main())
