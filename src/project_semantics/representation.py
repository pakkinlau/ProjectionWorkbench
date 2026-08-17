"""Task-relative architecture/method lenses and explicit view mappings."""
from __future__ import annotations
from typing import Any, Mapping
from . import ValidationError, canonical_digest, load_project, stable_id

def derive_lens(root:str, task:Mapping[str,Any], kind:str)->dict[str,Any]:
    if kind not in {"architecture","reusable_method"}: raise ValidationError("unsupported integration lens")
    p=load_project(root); modules=p.get("modules",[]); connectors=p.get("connectors",[])
    if kind=="architecture":
        selected=[{"kind":"Module","ref":m["module_id"],"role":"component"} for m in modules]+[{"kind":"Connector","ref":c["connector_id"],"role":"dependency"} for c in connectors]
        omitted=["human contribution semantics","private source bytes"]
    else:
        selected=[{"kind":"Module","ref":m["module_id"],"role":"reusable_method","inputs":m.get("inputs",[]),"outputs":m.get("outputs",[])} for m in modules]
        omitted=["runtime deployment topology","private source bytes"]
    payload={"project_snapshot_ref":stable_id("snapshot",{"project_ref":p["project_ref"],"modules":modules,"connectors":connectors}),"task_context_ref":task["task_context_id"],"lens_kind":kind,"selected_objects":selected,"omitted_objects":omitted,"information_loss":{"declared":True,"details":omitted},"privacy_projection":"private","claim_ceiling":task["claim_ceiling"]}
    payload["lens_id"]=stable_id("lens",payload); return payload

def create_view_mapping(source:Mapping[str,Any], target:Mapping[str,Any], *, proposed_global_term:str|None=None)->dict[str,Any]:
    if proposed_global_term in {"owner","authority","mastery","expert"}:
        return {"schema_version":"project-semantics.view-mapping-receipt.v1","source_lens_ref":source["lens_id"],"target_lens_ref":target["lens_id"],"disposition":"NO_SAFE_GLOBALIZATION","failed_reason":"unsafe semantic unification","information_loss":["role semantics cannot be globalized"]}
    source_refs={x["ref"] for x in source.get("selected_objects",[])}; target_refs={x["ref"] for x in target.get("selected_objects",[])}
    shared=sorted(source_refs & target_refs); lost=sorted(source_refs-target_refs)
    receipt={"schema_version":"project-semantics.view-mapping-receipt.v1","source_lens_ref":source["lens_id"],"target_lens_ref":target["lens_id"],"disposition":"PARTIAL_MAPPING_WITH_DECLARED_LOSS","shared_refs":shared,"information_loss":lost,"obstruction":None if shared else "NON_IDENTIFIABLE"}
    receipt["mapping_id"]="mapping:"+canonical_digest(receipt)[:24]; return receipt
