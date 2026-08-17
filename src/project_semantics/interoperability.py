"""Bounded v0->v1 schema migration and exchange witness."""
from __future__ import annotations
from copy import deepcopy
import hashlib, json
from pathlib import Path
from typing import Any, Mapping

V0="project-semantics.exchange-bundle.v0"; V1="project-semantics.exchange-bundle.v1"
KINDS={"WorkModuleManifest","ConnectorManifest","ViewMappingReceipt","ContributionRecord","EvidenceScope","Attestation","CompositionReceipt"}
IDS=("module_id","connector_id","mapping_receipt_id","contribution_id","evidence_scope_id","attestation_id","receipt_id")
class InteroperabilityError(ValueError): pass

def cbytes(v:Any)->bytes: return json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()
def digest(v:Any)->str: return "sha256:"+hashlib.sha256(cbytes(v)).hexdigest()
def req(v:Mapping[str,Any],*fs:str)->None:
    missing=[f for f in fs if f not in v]
    if missing: raise InteroperabilityError("missing required fields: "+", ".join(missing))
def rid(v:Mapping[str,Any])->str:
    for f in IDS:
        if v.get(f): return str(v[f])
    raise InteroperabilityError("record has no stable identity")

def validate_v0(b:Mapping[str,Any])->None:
    req(b,"schema_version","bundle_id","records","provenance")
    if b["schema_version"]!=V0 or not b["records"]: raise InteroperabilityError("invalid v0 bundle")
    seen=set()
    for x in b["records"]:
        req(x,"kind","payload")
        if x["kind"] not in KINDS: raise InteroperabilityError("unsupported record kind")
        i=rid(x["payload"])
        if i in seen: raise InteroperabilityError("duplicate record identity")
        seen.add(i)

def migrate_record(kind:str,p:Mapping[str,Any])->tuple[dict[str,Any],list[str]]:
    q=deepcopy(dict(p)); losses=[]
    required={
      "WorkModuleManifest":("module_id","version","inputs","outputs","semantic_contract","permissions","attribution","evidence_policy","claim_ceiling"),
      "ConnectorManifest":("connector_id","version","source_type","target_type","accepted_source_versions","accepted_target_versions","semantic_mapping","permissions","attribution_policy","evidence_continuity","claim_ceiling"),
      "ViewMappingReceipt":("mapping_receipt_id","mapping_kind","source_lens_ref","target_lens_ref","disposition","claim_ceiling"),
      "ContributionRecord":("contribution_id","episode_ref","actor_ref","contribution_role","contribution_mode","assertion_state","scope","evidence_refs","source_refs","claim_ceiling"),
      "EvidenceScope":("evidence_scope_id","observation_class","assessor_ref","independence","observed_at","currentness","covered_actions","covered_contexts","evidence_refs","limitations","claim_ceiling"),
      "Attestation":("attestation_id","attestor_ref","subject_ref","relationship","observation_scope","evidence_access","independence","state","evidence_scope_refs","nonclaims","claim_ceiling"),
      "CompositionReceipt":("receipt_id","module_a","module_b","connector","gate_results","disposition","claim_ceiling")}[kind]
    req(q,*required)
    versions={"WorkModuleManifest":"work-module-manifest.v1","ConnectorManifest":"connector-manifest.v1","ViewMappingReceipt":"view-mapping-receipt.v2","ContributionRecord":"contribution-record.v1","EvidenceScope":"evidence-scope.v1","Attestation":"attestation.v1","CompositionReceipt":"composition-receipt.v1"}
    q["schema_version"]="project-semantics."+versions[kind]
    if kind=="WorkModuleManifest": q.setdefault("side_effects",[]); q.setdefault("source_refs",[]); q.setdefault("currentness","unknown")
    if kind=="ConnectorManifest": q.setdefault("side_effect_policy",{"allowed":True}); q.setdefault("information_loss",q["semantic_mapping"].get("information_loss",[])); q.setdefault("currentness","unknown")
    if kind=="ViewMappingReceipt":
        for k,d in (("shared_object_refs",[]),("source_local_refinements",[]),("target_local_refinements",[]),("semantic_correspondences",[]),("information_loss",{}),("obstruction",None),("currentness","unknown")): q.setdefault(k,d)
        q["source_schema_version"]=p.get("schema_version","project-semantics.view-mapping-receipt.v1")
    if kind=="ContributionRecord":
        q.setdefault("origin","unknown"); q.setdefault("currentness","unknown"); q["capability_promotion_allowed"]=False
        if q["assertion_state"] in {"human_confirmed","third_party_attested","independently_assessed"} and not q["evidence_refs"]:
            q["assertion_state"]="unresolved"; losses.append("promoted state downgraded because v0 record lacked evidence")
    if kind=="EvidenceScope": q.setdefault("expiry",None); q.setdefault("revocation_state","active")
    if kind=="Attestation": q.setdefault("issued_at","unknown"); q.setdefault("currentness","unknown")
    if kind=="CompositionReceipt": q.setdefault("source_refs",[]); q.setdefault("information_loss",[]); q.setdefault("attribution",{})
    return q,losses

def index(b:Mapping[str,Any],kind:str,key:str)->dict[str,Mapping[str,Any]]:
    return {str(x["payload"][key]):x["payload"] for x in b["records"] if x["kind"]==kind}

def revalidate(b:Mapping[str,Any])->dict[str,Any]:
    if b.get("schema_version")!=V1: raise InteroperabilityError("revalidation requires v1")
    mods=index(b,"WorkModuleManifest","module_id"); conns=index(b,"ConnectorManifest","connector_id")
    maps=index(b,"ViewMappingReceipt","mapping_receipt_id"); scopes=index(b,"EvidenceScope","evidence_scope_id"); atts=index(b,"Attestation","attestation_id")
    checks={}; issues=[]
    for c in conns.values():
        src=[m for m in mods.values() if c["source_type"] in {p.get("type") for p in m["outputs"]}]
        dst=[m for m in mods.values() if c["target_type"] in {p.get("type") for p in m["inputs"]}]
        vals={"structural":bool(src and dst),"version":any(m["version"] in c["accepted_source_versions"] for m in src) and any(m["version"] in c["accepted_target_versions"] for m in dst),"semantic":bool(c["semantic_mapping"].get("correspondences")) and bool(c["semantic_mapping"].get("preserved_invariants")),"evidence":bool(c["evidence_continuity"].get("preserve_source_refs")),"attribution":c["attribution_policy"].get("preserve_lineage") is True}
        for k,v in vals.items(): checks[f"connector:{c['connector_id']}:{k}"]=v
        if not all(vals.values()): issues.append(f"connector {c['connector_id']} failed noncompensatory revalidation")
    for m in maps.values():
        ok=m["disposition"] in {"IDENTITY_MAPPING","PARTIAL_MAPPING_WITH_DECLARED_LOSS","NO_SAFE_GLOBALIZATION","NON_IDENTIFIABLE"} and "information_loss" in m and "currentness" in m
        checks[f"mapping:{m['mapping_receipt_id']}:conformant"]=ok
        if not ok: issues.append("mapping lacks v2 conformance")
    for a in atts.values():
        ok=all(r in scopes for r in a["evidence_scope_refs"]); checks[f"attestation:{a['attestation_id']}:scope_bound"]=ok
        if not ok: issues.append("attestation references unknown evidence scope")
    return {"checks":checks,"issues":issues,"disposition":"INTEROPERABLE" if checks and all(checks.values()) else "INCOMPATIBLE"}

def migrate_v0_to_v1(b:Mapping[str,Any])->tuple[dict[str,Any],dict[str,Any]]:
    validate_v0(b); records=[]; losses=[]; idmap={}
    for x in b["records"]:
        old=rid(x["payload"]); new,ls=migrate_record(x["kind"],x["payload"]); idmap[old]=rid(new); records.append({"kind":x["kind"],"payload":new})
        losses += [{"record_id":old,"loss":s,"material":True} for s in ls]
    out={"schema_version":V1,"bundle_id":b["bundle_id"],"source_bundle_digest":digest(b),"records":records,"provenance":deepcopy(b["provenance"]),"migration":{"from":V0,"to":V1,"id_map":idmap,"information_loss":losses,"canonical_source_mutated":False}}
    out["bundle_digest"]=digest(out); rv=revalidate(out)
    receipt={"schema_version":"project-semantics.schema-migration-receipt.v1","source_bundle_digest":digest(b),"target_bundle_digest":out["bundle_digest"],"id_map":idmap,"information_loss":losses,"provenance_preserved":out["provenance"]==b["provenance"],"canonical_source_mutated":False,"revalidation":rv,"disposition":"MIGRATED_WITH_DECLARED_LOSS" if losses else "MIGRATED_LOSSLESSLY","claim_ceiling":"Local schema migration and exchange mechanics only."}
    receipt["receipt_id"]=digest(receipt); return out,receipt

def export_bundle(b:Mapping[str,Any],root:str|Path)->dict[str,Any]:
    if b.get("schema_version")!=V1: raise InteroperabilityError("only v1 bundles can be exported")
    root=Path(root); root.mkdir(parents=True,exist_ok=True); data=json.dumps(b,indent=2,sort_keys=True).encode()+b"\n"; (root/"exchange_bundle.json").write_bytes(data)
    m={"schema_version":"project-semantics.exchange-manifest.v1","files":[{"path":"exchange_bundle.json","sha256":"sha256:"+hashlib.sha256(data).hexdigest(),"size":len(data)}],"bundle_digest":b["bundle_digest"],"canonical_source_mutated":False}; m["manifest_digest"]=digest(m)
    (root/"manifest.json").write_text(json.dumps(m,indent=2,sort_keys=True)+"\n"); return m

def import_bundle(root:str|Path)->tuple[dict[str,Any],dict[str,Any]]:
    root=Path(root); m=json.loads((root/"manifest.json").read_text()); data=(root/"exchange_bundle.json").read_bytes(); f=m["files"][0]
    if "sha256:"+hashlib.sha256(data).hexdigest()!=f["sha256"] or len(data)!=f["size"]: raise InteroperabilityError("exchange bundle integrity failure")
    b=json.loads(data)
    if b.get("bundle_digest")!=m["bundle_digest"]: raise InteroperabilityError("manifest bundle digest mismatch")
    rv=revalidate(b); r={"schema_version":"project-semantics.exchange-import-receipt.v1","manifest_digest":m["manifest_digest"],"bundle_digest":b["bundle_digest"],"integrity":"PASS","revalidation":rv,"canonical_source_mutated":False}; r["receipt_id"]=digest(r); return b,r

revalidate_exchange = revalidate
