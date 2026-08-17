"""F2.W6.B4 append-only event/provenance shadow architecture.

Additive only: the v0 mutable store remains untouched and authoritative until an
explicit owner-reviewed cutover generation.
"""
from __future__ import annotations
from copy import deepcopy
from datetime import datetime
import hashlib, json
from typing import Any, Mapping, Sequence

EVENT_SCHEMA_VERSION="project-semantics.event-envelope.v1"
MIGRATION_SCHEMA_VERSION="project-semantics.shadow-migration.v1"
REDUCER_VERSION="project-semantics.shadow-reducer.v1"
EVENT_TYPES={"project.registered","source.observed","episode.recorded","activity.recorded","contribution.asserted","attestation.recorded","evidence.recorded","assertion.transitioned","receipt.recorded","view.materialized","projection.published","projection.used"}
DERIVED_VIEW_KINDS=VIEW_KINDS={"ProjectLens","ProvisionalSemanticState","CurrentCapabilityProjection","Profile","PublicProjection","CurrentnessView"}
LAWFUL_TERMINALS={"SHADOW_MIGRATION_PARITY_SUPPORTED","DERIVED_STATE_INSUFFICIENT","MIGRATION_SEMANTIC_DRIFT","KEEP_CURRENT_COMPATIBILITY_MODEL","NO_SAFE"}

class EventSpineError(ValueError): pass

def canonical_bytes(v:Any)->bytes:
    return json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=False,allow_nan=False).encode()
def digest(v:Any)->str: return hashlib.sha256(canonical_bytes(v)).hexdigest()
def _text(v:Any,name:str)->str:
    if not isinstance(v,str) or not v.strip(): raise EventSpineError(f"{name} must be non-empty text")
    return v
def _time(v:Any,name:str)->str:
    s=_text(v,name)
    try: datetime.fromisoformat(s.replace("Z","+00:00"))
    except ValueError as exc: raise EventSpineError(f"{name} must be ISO-8601") from exc
    return s

def make_event(*,stream_id:str,sequence:int,event_type:str,payload:Mapping[str,Any],happened_at:str,recorded_at:str,actor_ref:str,source_refs:Sequence[str]=(),previous_event_id:str|None=None)->dict[str,Any]:
    _text(stream_id,"stream_id"); _text(actor_ref,"actor_ref"); _time(happened_at,"happened_at"); _time(recorded_at,"recorded_at")
    if not isinstance(sequence,int) or sequence<0: raise EventSpineError("sequence must be non-negative")
    if event_type not in EVENT_TYPES: raise EventSpineError(f"unsupported event_type: {event_type}")
    if not isinstance(payload,Mapping): raise EventSpineError("payload must be mapping")
    if not all(isinstance(x,str) and x for x in source_refs): raise EventSpineError("invalid source_refs")
    p=deepcopy(dict(payload)); pd=digest(p)
    identity={"schema_version":EVENT_SCHEMA_VERSION,"stream_id":stream_id,"sequence":sequence,"event_type":event_type,"happened_at":happened_at,"recorded_at":recorded_at,"actor_ref":actor_ref,"source_refs":list(source_refs),"payload_digest":pd,"previous_event_id":previous_event_id}
    return {**identity,"event_id":f"event:{digest(identity)[:32]}","payload":p}

def validate_event(e:Mapping[str,Any])->None:
    required={"schema_version","event_id","stream_id","sequence","event_type","happened_at","recorded_at","actor_ref","source_refs","payload_digest","previous_event_id","payload"}
    missing=required-set(e)
    if missing: raise EventSpineError(f"missing event fields: {sorted(missing)}")
    rebuilt=make_event(stream_id=e["stream_id"],sequence=e["sequence"],event_type=e["event_type"],payload=e["payload"],happened_at=e["happened_at"],recorded_at=e["recorded_at"],actor_ref=e["actor_ref"],source_refs=e["source_refs"],previous_event_id=e["previous_event_id"])
    if any(e[k]!=rebuilt[k] for k in ("schema_version","event_id","payload_digest")): raise EventSpineError("event integrity mismatch")
def validate_ledger(events:Sequence[Mapping[str,Any]])->str:
    prev=None; seen=set()
    for i,e in enumerate(events):
        validate_event(e)
        if e["sequence"]!=i or e["previous_event_id"]!=prev: raise EventSpineError("ledger chain mismatch")
        if e["event_id"] in seen: raise EventSpineError("duplicate event")
        seen.add(e["event_id"]); prev=e["event_id"]
    return digest([e["event_id"] for e in events])
def append_event(events:Sequence[Mapping[str,Any]],**kw:Any)->list[dict[str,Any]]:
    out=[deepcopy(dict(e)) for e in events]; validate_ledger(out)
    kw={**kw,"sequence":len(out),"previous_event_id":out[-1]["event_id"] if out else None}; out.append(make_event(**kw)); validate_ledger(out); return out

def _add(ledger:list[dict[str,Any]],stream:str,kind:str,payload:Mapping[str,Any],when:str,actor:str="actor:migration",refs:Sequence[str]=())->list[dict[str,Any]]:
    return append_event(ledger,stream_id=stream,event_type=kind,payload=payload,happened_at=when,recorded_at=when,actor_ref=actor,source_refs=refs)
def _when(record:Mapping[str,Any],fallback:str)->str: return str(record.get("happened_at") or record.get("observed_at") or record.get("recorded_at") or fallback)

def migrate_v0_project_to_shadow(v0_project:Mapping[str,Any],*,source_horizon_refs:Sequence[str],migration_recorded_at:str,policy:Mapping[str,Any])->dict[str,Any]:
    v0=deepcopy(dict(v0_project)); required={"project_ref","source_links","episodes","contributions","lenses","projections"}
    if required-set(v0): raise EventSpineError(f"v0 missing fields: {sorted(required-set(v0))}")
    pid=_text(v0["project_ref"].get("project_id"),"project_id"); stream=f"project:{pid}"; _time(migration_recorded_at,"migration_recorded_at")
    ledger=[]
    ledger=_add(ledger,stream,"project.registered",{"project_ref":v0["project_ref"]},str(v0.get("created_at") or migration_recorded_at),refs=source_horizon_refs)
    for s in v0["source_links"]: ledger=_add(ledger,stream,"source.observed",{"source_link":s},_when(s,migration_recorded_at),refs=[str(s.get("link_id"))])
    for ep in v0["episodes"]:
        when=_when(ep,migration_recorded_at); ledger=_add(ledger,stream,"episode.recorded",{"episode":ep},when,refs=ep.get("artifact_refs",[]))
        for i,a in enumerate(ep.get("activities",[])): ledger=_add(ledger,stream,"activity.recorded",{"episode_ref":ep["episode_id"],"index":i,"activity":a},when,actor=str(a.get("actor_ref") or "actor:unknown"),refs=ep.get("artifact_refs",[]))
    specs=[("contributions","contribution.asserted","contribution","actor_ref","source_refs"),("attestations","attestation.recorded","attestation","attestor_ref","evidence_scope_refs"),("evidence","evidence.recorded","evidence","assessor_ref","source_refs"),("transitions","assertion.transitioned","transition","authority_actor_ref","evidence_refs"),("receipts","receipt.recorded","receipt",None,"source_refs")]
    for field,kind,key,actor_key,refs_key in specs:
        for record in v0.get(field,[]): ledger=_add(ledger,stream,kind,{key:record},_when(record,migration_recorded_at),actor=str(record.get(actor_key) or "actor:migration") if actor_key else "actor:migration",refs=record.get(refs_key,[]))
    for lens in v0["lenses"]: ledger=_add(ledger,stream,"view.materialized",{"view_kind":"ProjectLens","view":lens},migration_recorded_at,refs=lens.get("provenance_refs",[]))
    for projection in v0["projections"]: ledger=_add(ledger,stream,"projection.published",{"projection":projection},migration_recorded_at)
    eh=validate_ledger(ledger); sh=digest(sorted(source_horizon_refs)); reduced=reduce_v0_compatibility_state(ledger); parity=compare_v0_parity(v0,reduced); terminal="SHADOW_MIGRATION_PARITY_SUPPORTED" if parity["equal"] else "MIGRATION_SEMANTIC_DRIFT"
    return {"schema_version":MIGRATION_SCHEMA_VERSION,"migration_id":f"shadow-migration:{digest([pid,eh,sh])[:32]}","project_ref":v0["project_ref"],"mode":"shadow_compatible_no_cutover","events":ledger,"event_horizon_digest":eh,"source_horizon_digest":sh,"reducer_version":REDUCER_VERSION,"policy":deepcopy(dict(policy)),"parity":parity,"terminal":terminal,"canonical_cutover_authorized":False,"claim_ceiling":"Shadow migration and deterministic fixture parity only."}

def reduce_v0_compatibility_state(events:Sequence[Mapping[str,Any]])->dict[str,Any]:
    validate_ledger(events); state={"project_ref":None,"source_links":[],"episodes":[],"contributions":[],"lenses":[],"projections":[],"attestations":[],"evidence":[],"transitions":[],"receipts":[]}
    mapping={"source.observed":("source_links","source_link"),"episode.recorded":("episodes","episode"),"contribution.asserted":("contributions","contribution"),"attestation.recorded":("attestations","attestation"),"evidence.recorded":("evidence","evidence"),"assertion.transitioned":("transitions","transition"),"receipt.recorded":("receipts","receipt"),"projection.published":("projections","projection")}
    for e in events:
        p=e["payload"]; kind=e["event_type"]
        if kind=="project.registered": state["project_ref"]=deepcopy(p["project_ref"])
        elif kind=="view.materialized" and p.get("view_kind")=="ProjectLens": state["lenses"].append(deepcopy(p["view"]))
        elif kind in mapping: field,key=mapping[kind]; state[field].append(deepcopy(p[key]))
    return state

def compare_v0_parity(v0:Mapping[str,Any],reduced:Mapping[str,Any])->dict[str,Any]:
    fields=["project_ref","source_links","episodes","contributions","lenses","projections"]+[x for x in ("attestations","evidence","transitions","receipts") if x in v0]
    checks={f:digest(v0.get(f))==digest(reduced.get(f)) for f in fields}
    return {"equal":all(checks.values()),"fields":checks,"v0_digest":digest({f:v0.get(f) for f in fields}),"reduced_digest":digest({f:reduced.get(f) for f in fields})}

def _states(events:Sequence[Mapping[str,Any]])->dict[str,str]:
    out={}
    for e in events:
        if e["event_type"]=="contribution.asserted": c=e["payload"]["contribution"]; out[str(c["contribution_id"])]=str(c["assertion_state"])
        elif e["event_type"]=="assertion.transitioned": t=e["payload"]["transition"]; out[str(t["assertion_ref"])]=str(t["to_state"])
    return out

def derive_views(events:Sequence[Mapping[str,Any]],*,source_horizon_refs:Sequence[str],policy:Mapping[str,Any],expires_at:str)->dict[str,dict[str,Any]]:
    eh=validate_ledger(events); sh=digest(sorted(source_horizon_refs)); _time(expires_at,"expires_at"); reduced=reduce_v0_compatibility_state(events); states=_states(events)
    active=[c for c in reduced["contributions"] if states.get(c["contribution_id"],c.get("assertion_state")) not in {"revoked","superseded"}]
    payloads={"ProjectLens":reduced["lenses"],"ProvisionalSemanticState":{"project_ref":reduced["project_ref"],"source_links":reduced["source_links"],"episodes":reduced["episodes"]},"CurrentCapabilityProjection":{"contributions":active,"claim_ceiling":"Current bounded contribution state only; not mastery or authority."},"Profile":{"project_ref":reduced["project_ref"],"active_contribution_count":len(active),"claim_ceiling":"Derived local profile only."},"PublicProjection":reduced["projections"],"CurrentnessView":{"event_count":len(events),"latest_event_id":events[-1]["event_id"] if events else None,"source_refs":list(source_horizon_refs),"assertion_states":states}}
    views={}
    for kind,payload in payloads.items():
        meta={"view_kind":kind,"event_horizon_digest":eh,"source_horizon_digest":sh,"reducer_version":REDUCER_VERSION,"policy":deepcopy(dict(policy)),"expires_at":expires_at,"currentness":"source_bound_shadow_snapshot"}
        receipt={"input_event_ids":[e["event_id"] for e in events],"event_horizon_digest":eh,"source_horizon_digest":sh,"reducer_version":REDUCER_VERSION,"policy_digest":digest(policy),"output_digest":digest(payload)}
        views[kind]={"view_id":f"view:{kind.lower()}:{digest([meta,receipt])[:24]}",**meta,"payload":deepcopy(payload),"reproduction_receipt":receipt,"canonical":False}
    return views

def run_shadow_migration_witness(bundle:Mapping[str,Any])->dict[str,Any]:
    migration=migrate_v0_project_to_shadow(bundle["v0_project"],source_horizon_refs=bundle["source_horizon_refs"],migration_recorded_at=bundle["migration_recorded_at"],policy=bundle["policy"])
    views=derive_views(migration["events"],source_horizon_refs=bundle["source_horizon_refs"],policy=bundle["policy"],expires_at=bundle["expires_at"])
    checks={"parity":migration["parity"]["equal"],"append_only_chain":bool(validate_ledger(migration["events"])),"all_required_views":set(views)==VIEW_KINDS,"views_bind_horizons":all(v["event_horizon_digest"]==migration["event_horizon_digest"] and v["source_horizon_digest"]==migration["source_horizon_digest"] for v in views.values()),"views_bind_reducer_policy_expiry":all(v["reducer_version"]==REDUCER_VERSION and v["policy"]==bundle["policy"] and v["expires_at"]==bundle["expires_at"] for v in views.values()),"reproduction_receipts":all(v["reproduction_receipt"]["output_digest"]==digest(v["payload"]) for v in views.values()),"no_cutover":migration["canonical_cutover_authorized"] is False}
    terminal="SHADOW_MIGRATION_PARITY_SUPPORTED" if all(checks.values()) else "DERIVED_STATE_INSUFFICIENT"
    return {"witness_id":f"event-spine-witness:{digest([migration['migration_id'],checks])[:24]}","terminal":terminal,"checks":checks,"migration":migration,"views":views,"claim_ceiling":"Controlled shadow migration and deterministic parity witness only."}
