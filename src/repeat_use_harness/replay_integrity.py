"""Content-bound append/replay and currentness/consent/claim binding."""
from __future__ import annotations
from copy import deepcopy
from pathlib import Path
from typing import Any, Mapping, Sequence

from .constants import CLAIM_CEILING, PROGRAM_ID
from .core import _parse_timestamp
from .replay import replay as _legacy_replay
from .strict_schema import (
    ReplayIntegrityError, SourceCurrentnessError, StateInvalidatedError,
    canonical_bytes, canonical_digest, normalize_event, read_jsonl, stable_id,
    validate_assignment, validate_consent, validate_epoch,
)

def _identity(event): return (str(event.get("trajectory_id","")),str(event.get("participant_id","")),str(event.get("project_id","")),str(event.get("inquiry_id","")))
def _bind(event,epoch,assignment,consent):
    if event["program_id"]!=epoch["program_id"]: raise SourceCurrentnessError("event program_id does not match epoch")
    if event.get("product_phase_id")!=epoch["product_phase_id"]: raise SourceCurrentnessError("event product phase drift")
    if assignment["version_phase"]!=epoch["product_phase_id"]: raise SourceCurrentnessError("assignment/product phase mismatch")
    if event["condition_id"]!=assignment["condition_id"]: raise SourceCurrentnessError("event/assignment condition mismatch")
    if set(event["source_refs"])!=set(epoch["source_snapshot_refs"]): raise SourceCurrentnessError("event source snapshot does not match epoch")
    if dict(event["feature_flag_snapshot"])!=dict(epoch["feature_flags"]): raise SourceCurrentnessError("event feature flags drifted")
    if event["claim_ceiling"]!=epoch["claim_ceiling"] or consent["claim_ceiling"]!=epoch["claim_ceiling"]: raise SourceCurrentnessError("claim ceiling drift")
    if consent["scopes"]["local_operational_capture"] is False: return
    if dict(event["consent_scope_snapshot"])!=dict(consent["scopes"]): raise SourceCurrentnessError("event consent snapshot does not match active receipt")
    if event["event_type"]=="HUMAN_JUDGMENT_RECORDED":
        if consent["scopes"]["human_judgment_capture"] is not True: raise SourceCurrentnessError("human judgment capture consent is absent")
        if event.get("participant_id") and event.get("participant_id")!=consent["participant_id"]: raise SourceCurrentnessError("human judgment participant/consent mismatch")

def make_tombstone(*,target_kind,target_id,reason,effective_at,source_receipt_ref):
    _parse_timestamp(effective_at)
    item={"object_type":"RepeatUseTombstone.v1","target_kind":target_kind,"target_id":target_id,"reason":reason,
        "effective_at":effective_at,"source_receipt_ref":source_receipt_ref,"claim_ceiling":CLAIM_CEILING}
    item["tombstone_id"]=stable_id("ruv-tombstone",item); return item

def _tombstones(items):
    active=[]
    for item in items or ():
        if item.get("object_type")!="RepeatUseTombstone.v1": raise ReplayIntegrityError("unsupported tombstone object")
        expected=stable_id("ruv-tombstone",{k:v for k,v in item.items() if k!="tombstone_id"})
        if item.get("tombstone_id")!=expected: raise ReplayIntegrityError("tombstone identity mismatch")
        active.append(dict(item))
    return active

def _invalidation(events,tombstones):
    event_ids={str(x.get("event_id")) for x in events}; episode_ids={str(x.get("episode_id")) for x in events}; trajectory_ids={str(x.get("trajectory_id")) for x in events}
    for t in tombstones:
        kind,target=t["target_kind"],t["target_id"]
        if kind=="all-derived-state" or (kind=="event" and target in event_ids) or (kind=="episode" and target in episode_ids) or (kind=="trajectory" and target in trajectory_ids):
            receipt={"receipt_kind":"ReplayInvalidationReceipt.v1","tombstone_ref":t["tombstone_id"],"target_kind":kind,"target_id":target,
                "disposition":"STATE_INVALIDATED_NO_RESURRECTION","claim_ceiling":CLAIM_CEILING}
            receipt["receipt_id"]=stable_id("replay-invalid",receipt); return receipt
    return None

def verify_event_log(events, *, epoch, assignment, consent, tombstones=None, allow_multi_project=False):
    validate_epoch(epoch); validate_assignment(assignment); validate_consent(consent)
    if not events: raise ReplayIntegrityError("event log is empty")
    active=_tombstones(tombstones); invalid=_invalidation(events,active)
    if invalid: raise StateInvalidatedError("replay invalidated by tombstone",invalid)
    normalized=[]; migrations=[]; identities=set()
    for event in events:
        item,migration=normalize_event(event); _bind(item,epoch,assignment,consent)
        for ident in {str(event.get("event_id")),item["event_id"]}:
            if ident in identities: raise ReplayIntegrityError("duplicate event identity or alias")
            identities.add(ident)
        normalized.append(item); migrations.append(migration)
    trajectories={x["trajectory_id"] for x in normalized}; participants={x.get("participant_id") for x in normalized}; projects={x.get("project_id") for x in normalized}
    if len(trajectories)!=1: raise ReplayIntegrityError("mixed trajectories require explicit batch envelope")
    if len(participants)!=1: raise ReplayIntegrityError("mixed participants are forbidden in one trajectory")
    if len(projects)>1 and not allow_multi_project:
        declared=set(epoch.get("trajectory_scope",{}).get("allowed_project_ids",[]))
        if not declared or projects!=declared: raise ReplayIntegrityError("multi-project trajectory lacks exact scope envelope")
    grouped={}
    for event in normalized: grouped.setdefault(event["episode_id"],[]).append(event)
    ordered=[]; nodes=[]; previous="GENESIS"
    for episode_id in sorted(grouped):
        episode=sorted(grouped[episode_id],key=lambda x:x["sequence"])
        seq=[x["sequence"] for x in episode]
        if seq!=list(range(1,len(episode)+1)): raise ReplayIntegrityError(f"episode {episode_id} sequence must be unique and contiguous: {seq}")
        if len({_identity(x)[1:] for x in episode})!=1: raise ReplayIntegrityError(f"episode {episode_id} identity mismatch")
        times=[_parse_timestamp(x["timestamp"]) for x in episode]
        if times!=sorted(times): raise ReplayIntegrityError(f"episode {episode_id} timestamp regression")
        for event in episode:
            digest=canonical_digest({k:v for k,v in event.items() if k not in {"event_id","content_digest","previous_event_digest","chain_root","migration_receipt_ref"}})
            node={"event_id":event["event_id"],"event_digest":digest,"previous_event_digest":previous}; node["chain_node_digest"]=canonical_digest(node); previous=node["chain_node_digest"]
            nodes.append(node); ordered.append(event)
    receipt={"receipt_kind":"EventLogIntegrityReceipt.v1","trajectory_id":next(iter(trajectories)),"episode_ids":sorted(grouped),"event_count":len(ordered),
        "chain_root":previous,"chain_nodes":nodes,"migration_receipts":migrations,"route_policy_digest":epoch["policy_digest"],
        "source_snapshot_digest":canonical_digest(sorted(epoch["source_snapshot_refs"])),"product_phase_id":epoch["product_phase_id"],
        "consent_receipt_ref":consent["receipt_id"],"claim_ceiling":CLAIM_CEILING}
    receipt["receipt_id"]=stable_id("event-log-integrity",receipt); return {"events":ordered,"receipt":receipt}

def append_event_file(path,event,*,epoch,consent,assignment=None):
    validate_epoch(epoch); validate_consent(consent)
    if consent["scopes"]["local_operational_capture"] is not True: raise SourceCurrentnessError("local operational capture consent is absent")
    item,migration=normalize_event(event)
    if assignment is None:
        assignment={"object_type":"EpisodeAssignment.v1","assignment_id":"assignment:append-bound","eligible_inquiry_stratum":"append-bound",
            "condition_id":item["condition_id"],"assignment_method":"bound-by-caller","assignment_seed_or_rule":"append-event-file",
            "assigned_before_start":True,"outcome_blind":True,"carryover_firewall":"one-event-log-one-episode","version_phase":epoch["product_phase_id"]}
    validate_assignment(assignment); _bind(item,epoch,assignment,consent)
    target=Path(path); target.parent.mkdir(parents=True,exist_ok=True); existing=[normalize_event(x)[0] for x in read_jsonl(target)]
    if existing:
        prev=existing[-1]
        if item["episode_id"]!=prev["episode_id"]: raise ReplayIntegrityError("one event log file may contain one episode only")
        if item["sequence"]!=prev["sequence"]+1: raise ReplayIntegrityError("event sequence must be contiguous append-only")
        if _parse_timestamp(item["timestamp"])<_parse_timestamp(prev["timestamp"]): raise ReplayIntegrityError("event timestamp moved backwards")
        if _identity(item)!=_identity(prev): raise ReplayIntegrityError("event identity drift within append log")
        previous=canonical_digest({k:v for k,v in prev.items() if k!="event_id"})
    else:
        if item["sequence"]!=1: raise ReplayIntegrityError("first event sequence must be 1")
        previous="GENESIS"
    if item["event_id"] in {x["event_id"] for x in existing}: raise ReplayIntegrityError("duplicate event_id")
    with target.open("a",encoding="utf-8") as handle: handle.write(canonical_bytes(item).decode("utf-8")+"\n")
    receipt={"receipt_kind":"AppendOnlyEventReceipt.v2","event_id":item["event_id"],"event_digest":canonical_digest(item),"previous_event_digest":previous,
        "sequence":item["sequence"],"migration_receipt":migration,"log_path":target.as_posix(),"claim_ceiling":CLAIM_CEILING}
    receipt["chain_root"]=canonical_digest(receipt); receipt["receipt_id"]=stable_id("append-event-v2",receipt); return receipt

def replay(events, *, epoch, assignment, consent, thresholds=None, independent_review=None, tombstones=None, allow_multi_project=False):
    verified=verify_event_log(events,epoch=epoch,assignment=assignment,consent=consent,tombstones=tombstones,allow_multi_project=allow_multi_project)
    result=_legacy_replay(verified["events"],epoch=epoch,assignment=assignment,consent=consent,thresholds=thresholds,independent_review=independent_review)
    result=deepcopy(result); result["schema_currentness_repair"]={"schema_version":"gva06.f.ruv.schema-currentness-replay-repair.v1",
        "integrity_receipt":verified["receipt"],"route_policy_digest_bound":True,"source_snapshot_bound":True,"assignment_phase_bound":True,
        "consent_snapshot_bound":consent["scopes"]["local_operational_capture"] is True,"claim_ceiling_bound":True,"tombstone_count":len(tombstones or ())}
    result["replay_digest"]=canonical_digest({k:v for k,v in result.items() if k!="replay_digest"}); return result
