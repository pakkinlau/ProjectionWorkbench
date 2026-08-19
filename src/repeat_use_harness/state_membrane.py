"""Purpose-bound export/delete integration and the R6 operand."""
from __future__ import annotations
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path

from .constants import CLAIM_CEILING, EVENT_SCHEMA_VERSION
from .storage import delete_export as _legacy_delete_export, export_event_log as _legacy_export_event_log
from .strict_schema import (
    EVENT_SCHEMA_VERSION_MINOR1, SchemaVersionError, StateInvalidatedError,
    canonical_digest, migrate_record, normalize_event, rollback_migration,
    schema_envelope_receipt, stable_id, validate_consent,
)
from .replay_integrity import _invalidation, _tombstones, make_tombstone, verify_event_log

def export_event_log(events,destination,*,consent,purpose="bounded_local_export",epoch=None,assignment=None,tombstones=None):
    if not purpose.strip(): raise ValueError("export purpose is required")
    validate_consent(consent); active=_tombstones(tombstones); invalid=_invalidation(events,active)
    if invalid: raise StateInvalidatedError("export invalidated by tombstone",invalid)
    normalized=[normalize_event(x)[0] for x in events]
    if epoch is not None and assignment is not None:
        capture_consent=deepcopy(dict(consent))
        capture_consent["scopes"]=deepcopy(dict(normalized[0]["consent_scope_snapshot"]))
        capture_consent["receipt_id"]=f"{consent['receipt_id']}:capture-snapshot"
        verify_event_log(normalized,epoch=epoch,assignment=assignment,consent=capture_consent,tombstones=tombstones)
    result=dict(_legacy_export_event_log(normalized,destination,consent=consent)); result.update({"receipt_kind":"RepeatUseEventExportReceipt.v2",
        "purpose":purpose,"purpose_bound":True,"event_log_digest":canonical_digest(normalized),"tombstone_count":len(active),"claim_ceiling":CLAIM_CEILING})
    result["receipt_id"]=stable_id("ruv-export-v2",result); return result

def delete_export(path,*,consent,explicit_confirmation,effective_at=None):
    target=Path(path); result=dict(_legacy_delete_export(target,consent=consent,explicit_confirmation=explicit_confirmation))
    timestamp=effective_at or datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00","Z")
    tombstone=make_tombstone(target_kind="all-derived-state",target_id=str(result.get("deleted_content_digest",target.name)),reason="explicit export deletion",
        effective_at=timestamp,source_receipt_ref=str(result.get("receipt_id","legacy-delete-receipt")))
    result.update({"receipt_kind":"RepeatUseDeletionReceipt.v2","tombstone":tombstone,"derived_state_invalidated":True}); result["receipt_id"]=stable_id("ruv-delete-v2",result); return result

def build_cross_version_replay_operand():
    from .fixture import make_fixture
    fixture=make_fixture(); source=deepcopy(fixture["events"][0]); source["schema_version"]=EVENT_SCHEMA_VERSION_MINOR1
    source["additive_metadata"]={"operand":"R6","semantics":"preserved"}; source["event_id"]="legacy-alias:R6"
    migrated,receipt=migrate_record(source,kind="event",target_schema_version=EVENT_SCHEMA_VERSION)
    unknown=deepcopy(fixture["events"][0]); unknown["schema_version"]="gva06.f.ruv.repeat-use-event.v2"; rejected=False
    try: schema_envelope_receipt(unknown,"event")
    except SchemaVersionError: rejected=True
    rolled=rollback_migration(source,receipt)
    operand={"object_type":"CrossVersionReplayOperand.v1","branch_id":"F.RUV.W3R.B7","source_fixture_ref":"F.RUV.W2.B1.mechanical-fixture.v1",
        "source_schema":EVENT_SCHEMA_VERSION_MINOR1,"target_schema":EVENT_SCHEMA_VERSION,"migration_receipt":receipt,
        "source_unchanged":canonical_digest(rolled)==canonical_digest(source),"migrated_event_digest":canonical_digest(migrated),"unknown_major_rejected":rejected,
        "expected_fresh_agent_cases":["EXACT_V1_REPLAY","ADDITIVE_MINOR_MIGRATION","UNKNOWN_MAJOR_REJECT","MIGRATED_EXPORT_IMPORT","ROLLBACK_REPLAY","TOMBSTONE_NO_RESURRECTION"],
        "independent_requalification_required":True,"claim_ceiling":"Local repair and deterministic operand preparation only; no independent cross-version qualification or human repeat-use claim."}
    operand["operand_digest"]=canonical_digest(operand); return operand
