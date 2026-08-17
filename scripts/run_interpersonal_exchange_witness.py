#!/usr/bin/env python3
"""F2.W3.B3: deterministic two-process exchange witness, stdlib only."""
from __future__ import annotations
import argparse, hashlib, json, shutil, subprocess, sys
from pathlib import Path
from typing import Any

GATES=("structural","semantic","permission","version","evidence","attribution","side_effect","custody")
def cb(v:Any)->bytes:return json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()
def dg(v:Any)->str:return hashlib.sha256(cb(v)).hexdigest()
def wr(p:Path,v:Any)->None:p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(v,indent=2,sort_keys=True)+"\n")
def rd(p:Path)->Any:return json.loads(p.read_text())
def a_module():return {"module_id":"example.evidence-graph-producer","version":"1.0.0","outputs":[{"type":"evidence-graph.v1"}],"permissions":{"allow_composition":True},"attribution":{"contributors":["instance-a"]},"evidence_policy":{"emit_receipt":True},"side_effects":["write-a"]}
def b_module():return {"module_id":"example.local-claim-auditor","version":"1.0.0","inputs":[{"type":"audit-input.v1"}],"permissions":{"allow_composition":True},"attribution":{"contributors":["instance-b"]},"evidence_policy":{"emit_receipt":True},"side_effects":["write-b"]}
def conn(valid=True):return {"connector_id":"example.graph-to-audit","version":"1.0.0","source_type":"evidence-graph.v1","target_type":"audit-input.v1","semantic_mapping":{"correspondences":[["claim_nodes","audit_claims"],["evidence_edges","audit_links"]],"preserved_invariants":["source_identity","evidence_lineage"],"information_loss":["rendering_metadata"]},"accepted_source_versions":["1.0.0"],"accepted_target_versions":["1.0.0"] if valid else ["9.9.9"],"permissions":{"allow_use":True},"attribution_policy":{"preserve_lineage":True},"evidence_continuity":{"preserve_source_refs":True},"side_effect_policy":{"allowed":True}}
def export(root:Path,path:Path,valid=True):
    if root.exists():shutil.rmtree(root)
    root.mkdir(parents=True);wr(root/"private.json",{"private":"not-exported","source_bytes":"local-only"})
    v={"exchange_id":"f2-w3-b3-001","origin":"instance-a","source":{"project_id":"project-a","canonical_location":"external://a/project","source_identity":dg(["project-a","external://a/project"]),"custody":"external_authoritative","source_bytes_included":False},"module":a_module(),"connector":conn(valid),"permissions":{"hosted_republication":False}}
    v["export_digest"]=dg(v);wr(path,v);return {"role":"A_EXPORT","digest":v["export_digest"]}
def consume(root:Path,path:Path,ret:Path):
    if root.exists():shutil.rmtree(root)
    root.mkdir(parents=True);x=rd(path);sig=x.pop("export_digest");integrity=sig==dg(x);x["export_digest"]=sig;b=b_module();c=x["connector"]
    st={p["type"] for p in x["module"]["outputs"]};tt={p["type"] for p in b["inputs"]}
    g={"structural":c["source_type"] in st and c["target_type"] in tt,"semantic":bool(c["semantic_mapping"]["correspondences"]) and bool(c["semantic_mapping"]["preserved_invariants"]),"permission":x["module"]["permissions"]["allow_composition"] and b["permissions"]["allow_composition"] and c["permissions"]["allow_use"],"version":x["module"]["version"] in c["accepted_source_versions"] and b["version"] in c["accepted_target_versions"],"evidence":x["module"]["evidence_policy"]["emit_receipt"] and b["evidence_policy"]["emit_receipt"] and c["evidence_continuity"]["preserve_source_refs"],"attribution":bool(x["module"]["attribution"]["contributors"]) and bool(b["attribution"]["contributors"]) and c["attribution_policy"]["preserve_lineage"],"side_effect":c["side_effect_policy"]["allowed"] and not set(x["module"]["side_effects"]).intersection(b["side_effects"]),"custody":x["source"]["custody"]=="external_authoritative" and x["source"]["source_bytes_included"] is False}
    if not integrity:g={k:False for k in GATES}
    failed=[k for k in GATES if not g[k]];disp="COMPOSED_AND_ADAPTED" if not failed else "FAILED_CLOSED"
    r={"receipt_id":"receipt:"+dg([x["exchange_id"],disp,g])[:24],"exchange_id":x["exchange_id"],"second_party_action":"local import, adaptation and composition","source_lineage":x["source"],"version_identity":{"module_a":x["module"]["version"],"module_b":b["version"],"connector":c["version"]},"semantic_mapping":c["semantic_mapping"],"assumption_delta":{"added_assumption":"Imported graph is audit input, not domain truth.","reversible":True},"attribution":{"originator":x["module"]["attribution"],"adapter":b["attribution"],"connector":c["attribution_policy"]},"gate_results":g,"failed_gates":failed,"disposition":disp,"outcome":{"artifact":"local-audit.json" if not failed else None},"canonical_source_migrated":False,"hosted_network_used":False}
    if not failed:wr(root/"local-audit.json",r["outcome"])
    wr(ret,r);return {"role":"B_CONSUME","disposition":disp,"failed_gates":failed}
def accept(root:Path,exp:Path,ret:Path,out:Path):
    x,r=rd(exp),rd(ret);v={"returned_to_origin":True,"exchange_id_matches":x["exchange_id"]==r["exchange_id"],"source_lineage_matches":x["source"]["source_identity"]==r["source_lineage"]["source_identity"],"origin_private_state_unchanged":rd(root/"private.json")["private"]=="not-exported","accepted_at_branch_ceiling":r["disposition"]=="COMPOSED_AND_ADAPTED"};wr(out,v);return {"role":"A_ACCEPT","accepted":v["accepted_at_branch_ceiling"]}
def call(*a):return json.loads(subprocess.run([sys.executable,__file__,*a],check=True,capture_output=True,text=True).stdout)
def allrun(w:Path,o:Path):
    for p in (w,o):
        if p.exists():shutil.rmtree(p)
        p.mkdir(parents=True)
    t=w/"transport";t.mkdir();ae=t/"a.json";br=t/"b.json";aa=t/"accept.json";ai=t/"a-invalid.json";bi=t/"b-invalid.json"
    rs=[call("export",str(w/"a"),str(ae)),call("consume",str(w/"b"),str(ae),str(br)),call("accept",str(w/"a"),str(ae),str(br),str(aa)),call("export-invalid",str(w/"a-invalid"),str(ai)),call("consume",str(w/"b-invalid"),str(ai),str(bi))]
    for p in (ae,br,aa,ai,bi):shutil.copy2(p,o/p.name)
    p,n,a=rd(br),rd(bi),rd(aa);checks={"separate_processes":True,"only_bundle_crossed":not (w/"b"/"private.json").exists(),"positive_action":p["disposition"]=="COMPOSED_AND_ADAPTED","return_to_origin":a["returned_to_origin"],"lineage":a["source_lineage_matches"],"semantic_mapping":bool(p["semantic_mapping"]["correspondences"]),"assumption_delta":bool(p["assumption_delta"]),"attribution":set(p["attribution"])=={"originator","adapter","connector"},"no_migration":not p["canonical_source_migrated"],"no_hosted_network":not p["hosted_network_used"],"negative_fails_closed":n["disposition"]=="FAILED_CLOSED" and "version" in n["failed_gates"],"private_unchanged":a["origin_private_state_unchanged"]}
    result={"witness_id":"F2.W3.B3.interpersonal-exchange.v1","checks":checks,"passed":all(checks.values()),"positive_receipt_id":p["receipt_id"],"negative_receipt_id":n["receipt_id"],"subprocess_returns":rs,"claim_ceiling":"One deterministic two-instance witness only."};wr(o/"result.json",result);return result
def main():
    q=argparse.ArgumentParser();q.add_argument("role",choices=["all","export","export-invalid","consume","accept"]);q.add_argument("args",nargs="+");a=q.parse_args()
    if a.role=="all":r=allrun(Path(a.args[0]),Path(a.args[1]))
    elif a.role.startswith("export"):r=export(Path(a.args[0]),Path(a.args[1]),a.role=="export")
    elif a.role=="consume":r=consume(Path(a.args[0]),Path(a.args[1]),Path(a.args[2]))
    else:r=accept(Path(a.args[0]),Path(a.args[1]),Path(a.args[2]),Path(a.args[3]))
    print(json.dumps(r,sort_keys=True))
if __name__=="__main__":main()
