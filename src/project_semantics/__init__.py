"""Brand-neutral local project semantics kernel."""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib, json, shutil
from pathlib import Path
from typing import Any, Iterable, Mapping

__version__ = "0.1.0.dev0"
SCHEMA_VERSION = "project-semantics.kernel.v0"
STORE_DIR = ".project-semantics"
PROJECT_FILE = "project.json"
CONTRIBUTION_STATES = {"observed","proposed","human_confirmed","third_party_attested","independently_assessed","disputed","adjudicated","superseded","revoked","unresolved"}
CONTRIBUTION_MODES = {"independent","human_directed_ai_executed","ai_primary_human_reviewed","joint_separable","joint_inseparable","tool_mediated","collective_emergent","unknown"}
MAPPING_KINDS = {"RESTRICTION","PROJECTION","TRANSLATION","ALIGNMENT","ADAPTER","COMPOSITION","ATTESTATION"}
GATE_NAMES = ("structural","semantic","permission","version","evidence","attribution","side_effect")

class ValidationError(ValueError):
    """Bounded contract validation failure."""

def canonical_bytes(value: Any) -> bytes:
    return json.dumps(value,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode("utf-8")
def canonical_digest(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()
def stable_id(prefix: str, payload: Any) -> str:
    return f"{prefix}:{canonical_digest(payload)[:24]}"
def load_json(path: str|Path) -> Any:
    with Path(path).open("r",encoding="utf-8") as handle: return json.load(handle)
def write_json(path: str|Path, value: Any) -> Path:
    target=Path(path); target.parent.mkdir(parents=True,exist_ok=True)
    target.write_text(json.dumps(value,indent=2,sort_keys=True,ensure_ascii=False)+"\n",encoding="utf-8")
    return target
def require_fields(record: Mapping[str,Any], fields: Iterable[str], kind: str) -> None:
    missing=[f for f in fields if f not in record]
    if missing: raise ValidationError(f"{kind} missing required fields: {', '.join(missing)}")
def require_text(record: Mapping[str,Any], fields: Iterable[str], kind: str) -> None:
    require_fields(record,fields,kind)
    bad=[f for f in fields if not isinstance(record[f],str) or not record[f].strip()]
    if bad: raise ValidationError(f"{kind} requires non-empty text: {', '.join(bad)}")

def validate_project_ref(v: Mapping[str,Any]) -> None:
    require_text(v,["project_id","canonical_location","project_kind"],"ProjectRef"); require_fields(v,["source_identity","access_policy","currentness_policy"],"ProjectRef")
def validate_task(v: Mapping[str,Any]) -> None:
    require_text(v,["task_context_id","goal","target_use","claim_ceiling"],"TaskContext"); require_fields(v,["questions","allowed_semantics","forbidden_semantics","privacy_policy"],"TaskContext")
def validate_episode(v: Mapping[str,Any]) -> None:
    require_text(v,["episode_id","happened_at","recorded_at","task_context_ref"],"WorkEpisode"); require_fields(v,["project_ref","activities","artifact_refs","outcome_state"],"WorkEpisode")
def validate_contribution(v: Mapping[str,Any]) -> None:
    require_text(v,["contribution_id","episode_ref","actor_ref","contribution_role","contribution_mode","assertion_state","claim_ceiling"],"ContributionRecord"); require_fields(v,["scope","evidence_refs","source_refs"],"ContributionRecord")
    if v["assertion_state"] not in CONTRIBUTION_STATES: raise ValidationError("unsupported contribution state")
    if v["contribution_mode"] not in CONTRIBUTION_MODES: raise ValidationError("unsupported contribution mode")
    if v["assertion_state"] in {"human_confirmed","third_party_attested","independently_assessed"} and not v["evidence_refs"]: raise ValidationError("promoted contribution states require evidence")
    if v.get("origin")=="agent" and v["assertion_state"]!="proposed": raise ValidationError("agent-originated contributions may only enter as proposed")
def validate_module(v: Mapping[str,Any]) -> None:
    require_text(v,["module_id","version","title","claim_ceiling"],"WorkModuleManifest"); require_fields(v,["inputs","outputs","semantic_contract","permissions","attribution","evidence_policy","side_effects"],"WorkModuleManifest")
def validate_connector(v: Mapping[str,Any]) -> None:
    require_text(v,["connector_id","version","source_type","target_type","claim_ceiling"],"ConnectorManifest"); require_fields(v,["mapping_kind","semantic_mapping","accepted_source_versions","accepted_target_versions","permissions","attribution_policy","evidence_continuity","side_effect_policy"],"ConnectorManifest")
    if v["mapping_kind"] not in MAPPING_KINDS: raise ValidationError("unsupported mapping kind")
def validate_policy(v: Mapping[str,Any]) -> None:
    require_text(v,["policy_id","audience"],"ProjectionPolicy"); require_fields(v,["allowed_fields","redaction_rules","subject_approval_requirement"],"ProjectionPolicy")

def _now() -> str: return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00","Z")
def store_path(root: str|Path) -> Path: return Path(root)/STORE_DIR/PROJECT_FILE
def load_project(root: str|Path) -> dict[str,Any]:
    path=store_path(root)
    if not path.exists(): raise ValidationError(f"project store not found: {path}")
    value=load_json(path)
    if value.get("schema_version")!=SCHEMA_VERSION: raise ValidationError("unsupported project store schema_version")
    validate_project_ref(value["project_ref"]); return value
def save_project(root: str|Path, value: Mapping[str,Any]) -> Path: return write_json(store_path(root),value)
def init_project(root: str|Path, *, project_id: str, title: str, project_kind: str="research_software", canonical_location: str|None=None, recorded_at: str|None=None) -> dict[str,Any]:
    base=Path(root); base.mkdir(parents=True,exist_ok=True); target=store_path(base)
    if target.exists(): raise ValidationError(f"project already initialized: {target}")
    location=canonical_location or str(base.resolve())
    ref={"project_id":project_id,"title":title,"canonical_location":location,"project_kind":project_kind,"owner_or_custodian":"local_user","source_identity":stable_id("project-source",[project_id,location]),"access_policy":"local_private_by_default","currentness_policy":"explicit_snapshot_or_relink"}
    validate_project_ref(ref)
    record={"schema_version":SCHEMA_VERSION,"project_ref":ref,"created_at":recorded_at or _now(),"source_links":[],"episodes":[],"contributions":[],"lenses":[],"projections":[]}
    save_project(base,record); return record
def link_source(root: str|Path, link: Mapping[str,Any]) -> dict[str,Any]:
    project=load_project(root); require_fields(link,["link_id","kind","locator","content_identity","custody","access_policy"],"SourceLink")
    if any(x["link_id"]==link["link_id"] for x in project["source_links"]): raise ValidationError("duplicate source link")
    project["source_links"].append(dict(link)); save_project(root,project); return project
def record_episode(root: str|Path, episode: Mapping[str,Any]) -> dict[str,Any]:
    validate_episode(episode); project=load_project(root)
    if episode["project_ref"]!=project["project_ref"]["project_id"]: raise ValidationError("episode project_ref mismatch")
    project["episodes"].append(dict(episode)); save_project(root,project); return project
def record_contribution(root: str|Path, contribution: Mapping[str,Any]) -> dict[str,Any]:
    validate_contribution(contribution); project=load_project(root)
    if not any(x["episode_id"]==contribution["episode_ref"] for x in project["episodes"]): raise ValidationError("unknown contribution episode")
    project["contributions"].append(dict(contribution)); save_project(root,project); return project

def derive_lens(root: str|Path, task: Mapping[str,Any], *, lens_kind: str) -> dict[str,Any]:
    validate_task(task); project=load_project(root); latest=project["episodes"][-1] if project["episodes"] else None
    questions=task.get("questions") or []; next_action=questions[0] if questions else task["goal"]
    selected=[{"kind":"ProjectRef","ref":project["project_ref"]["project_id"],"title":project["project_ref"].get("title")}]
    selected += [{"kind":"SourceLink","ref":x["link_id"],"locator":x["locator"]} for x in project["source_links"]]
    if latest: selected.append({"kind":"WorkEpisode","ref":latest["episode_id"],"outcome_state":latest["outcome_state"]})
    if lens_kind=="contribution": selected += [{"kind":"ContributionRecord","ref":x["contribution_id"],"state":x["assertion_state"]} for x in project["contributions"]]
    if lens_kind=="collaboration": selected.append({"kind":"OpenSeam","ref":stable_id("seam",[project["project_ref"]["project_id"],task["task_context_id"]]),"need":next_action})
    payload={"project_snapshot_ref":stable_id("snapshot",{"project_ref":project["project_ref"],"source_links":project["source_links"],"episodes":project["episodes"]}),"task_context_ref":task["task_context_id"],"lens_kind":lens_kind,"construction_rule":f"reference:{lens_kind}:v0","selected_objects":selected,"selected_relations":[{"predicate":"derived_from","subject":task["task_context_id"],"object":project["project_ref"]["project_id"]}],"omitted_objects":["private_raw_source_bytes","sealed_evaluator_internals"],"omitted_relations":["unconfirmed_intent","automatic_authorship"],"assumptions":["linked source metadata is current only at observation time"],"information_loss":{"semantic_loss":"raw domain semantics remain in external sources","privacy_redaction":"private source bytes omitted","materiality_by_task":"acceptable for first-witness clarity only"},"provenance_refs":[x["link_id"] for x in project["source_links"]],"currentness":"source_bound_local_snapshot","privacy_projection":"private","claim_ceiling":task["claim_ceiling"],"actionable_private_value":{"current_state":latest["outcome_state"] if latest else "INITIALIZED_NO_EPISODE","next_action_or_reentry":next_action,"unresolved_assumptions":task.get("forbidden_semantics",[]),"evidence_needed":task.get("evaluator_or_success_conditions",[])}}
    payload["lens_id"]=stable_id("lens",payload); project["lenses"].append(payload); save_project(root,project); return payload

def _types(ports: list[Mapping[str,Any]]) -> set[str]: return {str(x.get("type")) for x in ports if x.get("type")}
def compose(a: Mapping[str,Any], b: Mapping[str,Any], c: Mapping[str,Any]) -> dict[str,Any]:
    validate_module(a); validate_module(b); validate_connector(c)
    gates={"structural":c["source_type"] in _types(a["outputs"]) and c["target_type"] in _types(b["inputs"]),"semantic":bool(c["semantic_mapping"].get("correspondences")) and bool(c["semantic_mapping"].get("preserved_invariants")),"permission":bool(a["permissions"].get("allow_composition")) and bool(b["permissions"].get("allow_composition")) and bool(c["permissions"].get("allow_use")),"version":a["version"] in c["accepted_source_versions"] and b["version"] in c["accepted_target_versions"],"evidence":bool(c["evidence_continuity"].get("preserve_source_refs")) and bool(a["evidence_policy"].get("emit_receipt")) and bool(b["evidence_policy"].get("emit_receipt")),"attribution":bool(a["attribution"].get("contributors")) and bool(b["attribution"].get("contributors")) and c["attribution_policy"].get("preserve_lineage") is True,"side_effect":c["side_effect_policy"].get("allowed") is True and not set(a["side_effects"]).intersection(b["side_effects"])}
    receipt={"receipt_kind":"CompositionReceipt","module_a":{"id":a["module_id"],"version":a["version"]},"module_b":{"id":b["module_id"],"version":b["version"]},"connector":{"id":c["connector_id"],"version":c["version"]},"gate_results":gates,"disposition":"COMPOSED" if all(gates.values()) else "FAILED_CLOSED","failed_gates":[n for n in GATE_NAMES if not gates[n]],"semantic_mapping":c["semantic_mapping"],"information_loss":c["semantic_mapping"].get("information_loss",[]),"attribution":{"module_a":a["attribution"],"module_b":b["attribution"],"connector":c["attribution_policy"]},"evidence_continuity":c["evidence_continuity"],"claim_ceiling":"Local composition mechanics only; gate passage does not imply scientific adequacy, universal compatibility, market value, or external admission."}
    receipt["receipt_id"]=stable_id("composition",receipt); return receipt

def create_projection(root: str|Path, policy: Mapping[str,Any]) -> dict[str,Any]:
    validate_policy(policy); project=load_project(root)
    source={k:project.get(k) for k in ["project_ref","source_links","episodes","contributions","lenses"]}; allowed=set(policy["allowed_fields"])
    projection={"projection_kind":"SelectiveProjectProjection","policy_ref":policy["policy_id"],"audience":policy["audience"],"visible":{k:v for k,v in source.items() if k in allowed},"redactions":policy["redaction_rules"],"subject_approval_requirement":policy["subject_approval_requirement"],"canonical_history_mutated":False,"claim_ceiling":"Derived view only; not canonical history, trust, capability, or admission."}
    projection["projection_id"]=stable_id("projection",projection); project["projections"].append({"projection_id":projection["projection_id"],"policy_ref":policy["policy_id"]}); save_project(root,project); return projection

def run_witness(bundle_path: str|Path, workspace: str|Path, output: str|Path) -> dict[str,Any]:
    bundle=load_json(bundle_path); work=Path(workspace); out=Path(output)
    for p in (work,out):
        if p.exists(): shutil.rmtree(p)
        p.mkdir(parents=True)
    init_project(work,project_id="demo.research.project",title="Deterministic research fixture",canonical_location="external://demo/research-project",recorded_at="2026-08-17T00:00:00Z")
    link_source(work,bundle["source_link"]); task=bundle["task_context"]; first=derive_lens(work,task,lens_kind="continuation")
    record_episode(work,bundle["episode"]); record_contribution(work,bundle["contribution"]); contrib=derive_lens(work,task,lens_kind="contribution")
    positive=compose(bundle["module_a"],bundle["module_b"],bundle["connector"]); negative=compose(bundle["module_a"],bundle["module_b"],bundle["connector_invalid"]); projection=create_projection(work,bundle["projection_policy"])
    outputs={"first_lens.json":first,"contribution_lens.json":contrib,"composition_receipt.json":positive,"negative_composition_receipt.json":negative,"selective_projection.json":projection}
    for name,value in outputs.items(): write_json(out/name,value)
    project=load_project(work); write_json(out/"project_export.json",project)
    checks={"private_lens_before_publication":first["privacy_projection"]=="private","positive_composition":positive["disposition"]=="COMPOSED","negative_fails_closed":negative["disposition"]=="FAILED_CLOSED","agent_proposal_not_auto_confirmed":project["contributions"][0]["assertion_state"]=="proposed","projection_does_not_mutate_canonical_history":projection["canonical_history_mutated"] is False}
    result={"witness_id":"F2.W2.K1.first-runnable-witness.v0","checks":checks,"passed":all(checks.values()),"output_digests":{n:canonical_digest(v) for n,v in outputs.items()},"project_export_digest":canonical_digest(project),"claim_ceiling":"Local deterministic prototype mechanics only."}; write_json(out/"witness_result.json",result); return result
