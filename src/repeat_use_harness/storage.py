"""Explicit export and deletion receipts."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from .constants import CLAIM_CEILING
from .core import HarnessValidationError, stable_id, validate_consent, validate_event

def export_event_log(
    events: Sequence[Mapping[str, Any]],
    destination: str | Path,
    *,
    consent: Mapping[str, Any],
) -> dict[str, Any]:
    validate_consent(consent)
    if consent["scopes"]["artifact_export"] is not True:
        raise HarnessValidationError("artifact export consent is absent")
    for event in events:
        validate_event(event)
    target = Path(destination)
    if target.exists():
        raise HarnessValidationError("export target already exists")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        "".join(
            json.dumps(event, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
            + "\n"
            for event in events
        ),
        encoding="utf-8",
    )
    receipt = {
        "receipt_kind": "RepeatUseEventExportReceipt.v1",
        "destination": target.name,
        "event_count": len(events),
        "content_digest": hashlib.sha256(target.read_bytes()).hexdigest(),
        "raw_content_included": False,
        "consent_ref": consent["receipt_id"],
        "claim_ceiling": CLAIM_CEILING,
    }
    receipt["receipt_id"] = stable_id("ruv-export", receipt)
    return receipt


def delete_export(
    path: str | Path, *, consent: Mapping[str, Any], explicit_confirmation: bool
) -> dict[str, Any]:
    validate_consent(consent)
    if explicit_confirmation is not True:
        raise HarnessValidationError("deletion requires explicit confirmation")
    target = Path(path)
    if not target.exists() or not target.is_file():
        raise HarnessValidationError("deletion target is not a regular file")
    before = hashlib.sha256(target.read_bytes()).hexdigest()
    target.unlink()
    receipt = {
        "receipt_kind": "RepeatUseDeletionReceipt.v1",
        "target_name": target.name,
        "deleted_content_digest": before,
        "deleted": True,
        "claim_ceiling": CLAIM_CEILING,
    }
    receipt["receipt_id"] = stable_id("ruv-delete", receipt)
    return receipt
