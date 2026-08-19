"""Strict JSON, schema envelopes, and receipt-bearing migration."""
from __future__ import annotations
from copy import deepcopy
from dataclasses import dataclass
import hashlib, json, math, re
from pathlib import Path
from typing import Any, Mapping, Sequence

from .constants import (
    CLAIM_CEILING, EVENT_SCHEMA_VERSION, PROGRAM_ID, ROUTE_LAUNCH_DIGEST,
)
from .core import (
    HarnessValidationError,
    validate_assignment as _legacy_validate_assignment,
    validate_consent as _legacy_validate_consent,
    validate_epoch as _legacy_validate_epoch,
    validate_event as _legacy_validate_event,
)

SCHEMA_REPAIR_VERSION = "gva06.f.ruv.schema-currentness-replay-repair.v1"
REPAIR_BRANCH_ID = "F.RUV.W3R.B7"
EVENT_SCHEMA_VERSION_MINOR1 = "gva06.f.ruv.repeat-use-event.v1.1"
EPOCH_SCHEMA_VERSION = "gva06.f.ruv.repeat-use-experiment-epoch.v1"
ASSIGNMENT_SCHEMA_VERSION = "gva06.f.ruv.episode-assignment.v1"
CONSENT_SCHEMA_VERSION = "gva06.f.ruv.consent-receipt.v1"
EPISODE_SCHEMA_VERSION = "gva06.f.ruv.user-value-episode.v1"
TRAJECTORY_SCHEMA_VERSION = "gva06.f.ruv.user-value-trajectory.v1"
TERMINAL_NAMESPACE_V1 = "gva06.f.ruv.causal-terminal.v1"

class StrictJSONError(HarnessValidationError): pass
class SchemaVersionError(HarnessValidationError): pass
class SourceCurrentnessError(HarnessValidationError): pass
class ReplayIntegrityError(HarnessValidationError): pass
class StateInvalidatedError(HarnessValidationError):
    def __init__(self, message: str, receipt: Mapping[str, Any] | None = None) -> None:
        super().__init__(message); self.receipt = dict(receipt or {})

@dataclass(frozen=True)
class StrictJSONLimits:
    max_bytes: int = 2_000_000
    max_depth: int = 32
    max_nodes: int = 100_000
    max_string_length: int = 200_000
DEFAULT_JSON_LIMITS = StrictJSONLimits()
_VERSION_RE = re.compile(r"^(?P<base>.+)\.v(?P<major>\d+)(?:\.(?P<minor>\d+))?$")
_EVENT_DERIVED_FIELDS = {"event_id","content_digest","previous_event_digest","chain_root","migration_receipt_ref"}
_OBJECT_SPECS = {
    "epoch": {"object_type":"RepeatUseExperimentEpoch.v1","schema":EPOCH_SCHEMA_VERSION,
        "required":{"epoch_id","program_id","product_phase_id","policy_digest","instrumentation_tier","feature_flags","started_at","source_snapshot_refs","claim_ceiling"}},
    "assignment": {"object_type":"EpisodeAssignment.v1","schema":ASSIGNMENT_SCHEMA_VERSION,
        "required":{"assignment_id","eligible_inquiry_stratum","condition_id","assignment_method","assignment_seed_or_rule","assigned_before_start","outcome_blind","carryover_firewall","version_phase"}},
    "consent": {"object_type":"ConsentReceipt.v1","schema":CONSENT_SCHEMA_VERSION,
        "required":{"receipt_id","participant_id","issued_at","scopes","claim_ceiling"}},
    "event": {"object_type":"RepeatUseEvent.v1","schema":EVENT_SCHEMA_VERSION,
        "required":{"event_id","sequence","payload","program_id","trajectory_id","episode_id","condition_id","schema_version","event_type","timestamp","source_refs","consent_scope_snapshot","feature_flag_snapshot","claim_ceiling"}},
    "episode": {"object_type":"UserValueEpisode.v1","schema":EPISODE_SCHEMA_VERSION,
        "required":{"episode_id","participant_id","project_id","condition_id"}},
    "trajectory": {"object_type":"UserValueTrajectory.v1","schema":TRAJECTORY_SCHEMA_VERSION,
        "required":{"trajectory_id","participant_id","episode_ids","project_ids"}},
}

def _reject_constant(value: str) -> None: raise StrictJSONError(f"non-finite JSON constant is forbidden: {value}")
def _object_no_duplicates(pairs):
    result={}
    for key,value in pairs:
        if key in result: raise StrictJSONError(f"duplicate JSON key: {key}")
        result[key]=value
    return result

def _check_limits(value, limits, depth=0, counter=None):
    counter = [0] if counter is None else counter; counter[0]+=1
    if counter[0] > limits.max_nodes: raise StrictJSONError("JSON node-count limit exceeded")
    if depth > limits.max_depth: raise StrictJSONError("JSON depth limit exceeded")
    if isinstance(value,str) and len(value)>limits.max_string_length: raise StrictJSONError("JSON string-length limit exceeded")
    if isinstance(value,Mapping):
        for key,child in value.items():
            if not isinstance(key,str): raise StrictJSONError("JSON object keys must be text")
            _check_limits(child,limits,depth+1,counter)
    elif isinstance(value,list):
        for child in value: _check_limits(child,limits,depth+1,counter)
    elif isinstance(value,float) and not math.isfinite(value): raise StrictJSONError("non-finite numbers are forbidden")

def strict_loads(text: str, *, limits=DEFAULT_JSON_LIMITS):
    if len(text.encode("utf-8"))>limits.max_bytes: raise StrictJSONError("JSON byte-size limit exceeded")
    try: value=json.loads(text,object_pairs_hook=_object_no_duplicates,parse_constant=_reject_constant)
    except StrictJSONError: raise
    except (json.JSONDecodeError,UnicodeError) as exc: raise StrictJSONError(f"invalid strict JSON: {exc}") from exc
    _check_limits(value,limits); return value

def load_json(path, *, limits=DEFAULT_JSON_LIMITS):
    target=Path(path)
    if target.stat().st_size>limits.max_bytes: raise StrictJSONError("JSON file-size limit exceeded")
    return strict_loads(target.read_text(encoding="utf-8"),limits=limits)

def read_jsonl(path, *, limits=DEFAULT_JSON_LIMITS):
    target=Path(path)
    if not target.exists(): return []
    if target.stat().st_size>limits.max_bytes: raise StrictJSONError("JSONL file-size limit exceeded")
    values=[]
    for line_no,line in enumerate(target.read_text(encoding="utf-8").splitlines(),1):
        if not line.strip(): continue
        value=strict_loads(line,limits=limits)
        if not isinstance(value,dict): raise StrictJSONError(f"JSONL line {line_no} must be an object")
        values.append(value)
    return values

def canonical_bytes(value):
    try: return json.dumps(value,sort_keys=True,separators=(",",":"),ensure_ascii=False,allow_nan=False).encode("utf-8")
    except (TypeError,ValueError) as exc: raise StrictJSONError(f"value is not canonical finite JSON: {exc}") from exc
def canonical_digest(value): return hashlib.sha256(canonical_bytes(value)).hexdigest()
def stable_id(prefix,value): return f"{prefix}:{canonical_digest(value)[:24]}"
def write_json(path,value):
    target=Path(path); target.parent.mkdir(parents=True,exist_ok=True)
    target.write_text(json.dumps(value,indent=2,sort_keys=True,ensure_ascii=False,allow_nan=False)+"\n",encoding="utf-8")
    return target

def _parse_version(version):
    match=_VERSION_RE.match(version)
    if not match: raise SchemaVersionError(f"invalid schema version: {version}")
    return match.group("base"),int(match.group("major")),int(match.group("minor") or 0)
def _compatible(source,expected,max_minor=1):
    sb,sm,sn=_parse_version(source); eb,em,_=_parse_version(expected)
    return sb==eb and sm==em and sn<=max_minor

def schema_envelope_receipt(record,kind):
    if kind not in _OBJECT_SPECS: raise SchemaVersionError(f"unknown object kind: {kind}")
    spec=_OBJECT_SPECS[kind]
    if "object_type" in record and record["object_type"]!=spec["object_type"]: raise SchemaVersionError(f"{kind} object_type mismatch")
    source=record.get("schema_version") or spec["schema"]
    if not isinstance(source,str) or not _compatible(source,spec["schema"]): raise SchemaVersionError(f"unsupported {kind} schema version: {source}")
    missing=sorted(set(spec["required"])-set(record))
    if missing: raise SchemaVersionError(f"{kind} missing schema fields: {', '.join(missing)}")
    unknown=sorted(set(record)-set(spec["required"])-{"object_type","schema_version"})
    receipt={"receipt_kind":"SchemaEnvelopeReceipt.v1","kind":kind,"expected_object_type":spec["object_type"],
        "source_schema_version":source,"canonical_schema_version":spec["schema"],"legacy_schema_inferred":"schema_version" not in record,
        "unknown_fields_policy":"PRESERVE_WITH_RECEIPT","unknown_fields":unknown,"record_digest":canonical_digest(record),"claim_ceiling":CLAIM_CEILING}
    receipt["receipt_id"]=stable_id("schema-envelope",receipt); return receipt

def validate_epoch(epoch):
    schema_envelope_receipt(epoch,"epoch"); _legacy_validate_epoch(epoch)
    if epoch["policy_digest"]!=ROUTE_LAUNCH_DIGEST: raise SourceCurrentnessError("SOURCE_CURRENTNESS_DRIFT: epoch policy_digest")
    if epoch["program_id"]!=PROGRAM_ID: raise SourceCurrentnessError("epoch program_id mismatch")
    if epoch["claim_ceiling"]!=CLAIM_CEILING: raise SourceCurrentnessError("epoch claim ceiling is not route-bound")
    if len(epoch["source_snapshot_refs"])!=len(set(epoch["source_snapshot_refs"])): raise SourceCurrentnessError("duplicate source snapshot refs")
def validate_assignment(assignment): schema_envelope_receipt(assignment,"assignment"); _legacy_validate_assignment(assignment)
def validate_consent(consent):
    schema_envelope_receipt(consent,"consent"); _legacy_validate_consent(consent)
    if consent["claim_ceiling"]!=CLAIM_CEILING: raise SourceCurrentnessError("consent claim ceiling exceeds experiment ceiling")
def canonical_event_content(event): return {k:deepcopy(v) for k,v in event.items() if k not in _EVENT_DERIVED_FIELDS}
def expected_event_id(event): return stable_id("ruv-event",canonical_event_content(event))

def normalize_event(event):
    source=deepcopy(dict(event)); envelope=schema_envelope_receipt(source,"event")
    normalized=deepcopy(source); normalized["schema_version"]=EVENT_SCHEMA_VERSION; normalized.pop("object_type",None)
    for field in ("content_digest","previous_event_digest","chain_root","migration_receipt_ref"): normalized.pop(field,None)
    old_id=normalized.get("event_id"); normalized["event_id"]=expected_event_id(normalized); _legacy_validate_event(normalized)
    receipt={"receipt_kind":"MigrationReceipt.v1","adapter_id":"F.RUV.W3R.B7.event-normalize-to-strict-v1",
        "source_schema":envelope["source_schema_version"],"target_schema":EVENT_SCHEMA_VERSION,
        "source_digest":canonical_digest(source),"target_digest":canonical_digest(normalized),"source_unchanged":True,
        "identity_map":{str(old_id):normalized["event_id"]} if old_id else {},"field_mapping":{"schema_version":EVENT_SCHEMA_VERSION},
        "unknown_fields":envelope["unknown_fields"],"unknown_fields_policy":envelope["unknown_fields_policy"],
        "information_loss":[],"claim_impact":"NONE","rollback":{"source_digest":canonical_digest(source),"source_snapshot_embedded":False},
        "claim_ceiling":CLAIM_CEILING}
    receipt["receipt_id"]=stable_id("migration",receipt); return normalized,receipt

def validate_event(event):
    schema_envelope_receipt(event,"event")
    if event.get("schema_version")!=EVENT_SCHEMA_VERSION: raise SchemaVersionError("direct event validation requires canonical v1; migrate first")
    _legacy_validate_event(event)
    if event["event_id"]!=expected_event_id(event): raise ReplayIntegrityError("event_id is not bound to immutable event content")
    if "content_digest" in event and event["content_digest"]!=canonical_digest(canonical_event_content(event)): raise ReplayIntegrityError("event content_digest mismatch")

def migrate_record(record, *, kind, target_schema_version, field_mapping=None, information_loss=(), claim_impact="NONE"):
    envelope=schema_envelope_receipt(record,kind); spec=_OBJECT_SPECS[kind]
    if not _compatible(target_schema_version,spec["schema"]): raise SchemaVersionError(f"unsupported migration target: {target_schema_version}")
    source=deepcopy(dict(record)); target=deepcopy(source)
    if kind=="event" or "schema_version" in target: target["schema_version"]=target_schema_version
    target.setdefault("object_type",spec["object_type"])
    old=source.get("event_id") or source.get("receipt_id") or source.get("assignment_id") or source.get("epoch_id")
    if kind=="event": target["event_id"]=stable_id("ruv-event",canonical_event_content(target))
    new=target.get("event_id") or target.get("receipt_id") or target.get("assignment_id") or target.get("epoch_id")
    receipt={"receipt_kind":"MigrationReceipt.v1","adapter_id":f"F.RUV.W3R.B7.{kind}.{envelope['source_schema_version']}->{target_schema_version}",
        "source_schema":envelope["source_schema_version"],"target_schema":target_schema_version,"source_digest":canonical_digest(source),
        "target_digest":canonical_digest(target),"source_unchanged":True,"identity_map":{str(old):str(new)} if old is not None else {},
        "field_mapping":dict(field_mapping or {}),"unknown_fields":envelope["unknown_fields"],"unknown_fields_policy":"PRESERVE_WITH_RECEIPT",
        "information_loss":list(information_loss),"claim_impact":claim_impact,"rollback":{"source_digest":canonical_digest(source),"reproduction_ref":"source-record-by-digest"},
        "claim_ceiling":CLAIM_CEILING}
    receipt["receipt_id"]=stable_id("migration",receipt); return target,receipt
def rollback_migration(source_record,receipt):
    if canonical_digest(source_record)!=receipt.get("source_digest"): raise ReplayIntegrityError("rollback source digest mismatch")
    return deepcopy(dict(source_record))
def map_terminal(terminal, *, source_namespace=TERMINAL_NAMESPACE_V1, target_namespace=TERMINAL_NAMESPACE_V1):
    declared={"HARM_OR_TRUST_BREACH","RIGHT_CENSORED","NON_IDENTIFIABLE","MEASUREMENT_REACTIVE","CAPTURE_COST_TOO_HIGH","NEGATIVE_NET_VALUE","RETENTION_WITHOUT_VALUE","ACCUMULATION_EFFECT_NOT_OBSERVED","EPISODE_VALUE_ONLY","VALUE_WITHOUT_REPEAT_NEED","HETEROGENEOUS_CONTEXT_DEPENDENT","REPEAT_USE_VALUE_SUPPORTED_BOUNDED","NO_SAFE_PRODUCT_STEERING"}
    if source_namespace!=TERMINAL_NAMESPACE_V1 or target_namespace!=TERMINAL_NAMESPACE_V1: raise SchemaVersionError("terminal namespace migration requires explicit adapter")
    if terminal not in declared: raise SchemaVersionError(f"unregistered terminal: {terminal}")
    receipt={"receipt_kind":"TerminalMappingReceipt.v1","source_namespace":source_namespace,"target_namespace":target_namespace,
        "source_terminal":terminal,"target_terminal":terminal,"equivalence":"IDENTITY_EXACT","claim_ceiling":CLAIM_CEILING}
    receipt["receipt_id"]=stable_id("terminal-map",receipt); return terminal,receipt
