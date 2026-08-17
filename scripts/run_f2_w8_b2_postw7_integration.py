from __future__ import annotations

import json
from pathlib import Path
import tempfile

from project_semantics.cross_domain import run_cross_domain_pressure
from project_semantics.event_spine import migrate_v0_project_to_shadow
from project_semantics.interoperability_v2 import (
    export_exchange_bundle,
    import_exchange_bundle,
    migrate_native_bundle,
)

ROOT = Path(__file__).resolve().parents[1]


def run() -> dict:
    native = json.loads((ROOT / "fixtures/view_mapping_waist/native_bundle.json").read_text())
    mapping = next(x["payload"] for x in native["records"] if x["kind"] == "ViewMappingReceipt")
    policy = {mapping["mapping_id"]: {"mapping_kind": "ALIGNMENT", "claim_ceiling": "bounded integration mechanics", "currentness": "current", "provenance_refs": ["W7.B2", "W8.B2"]}}
    migrated, migration_receipt = migrate_native_bundle(native, mapping_policies=policy)
    with tempfile.TemporaryDirectory() as tmp:
        export_exchange_bundle(migrated, tmp)
        imported, import_receipt = import_exchange_bundle(tmp)
    domains = {}
    for domain in ("cookery", "farming"):
        bundle = json.loads((ROOT / f"fixtures/{domain}/bundle.json").read_text())
        domains[domain] = run_cross_domain_pressure(bundle)
    shadow = migrate_v0_project_to_shadow(
        {"project_ref": {"project_id": "integration-fixture"}, "source_links": [], "episodes": [], "contributions": [], "lenses": [], "projections": []},
        source_horizon_refs=["PR17:19478eda855d39d4a6477873e28bf0248e59a16f"],
        migration_recorded_at="2026-08-17T16:00:00Z",
        policy={"canonical_cutover": False},
    )
    checks = {
        "exchange_interoperable": migration_receipt["revalidation"]["disposition"] == "INTEROPERABLE",
        "round_trip_equal": imported == migrated and import_receipt["integrity"] == "PASS",
        "cookery_regression": domains["cookery"]["passed"],
        "farming_regression": domains["farming"]["passed"],
        "event_spine_cutover_disabled": shadow["canonical_cutover_authorized"] is False,
        "canonical_source_not_mutated": migration_receipt["canonical_source_mutated"] is False,
    }
    return {"schema_version": "gva06.f2.w8.b2.integration-witness.v1", "checks": checks, "passed": all(checks.values()), "terminal": "POST_W7_EXCHANGE_DOMAIN_NEUTRAL_INTEGRATION_PASS" if all(checks.values()) else "REPAIR_REQUIRED", "claim_ceiling": "Controlled local integration mechanics only."}


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    result = run()
    Path(args.output).write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps(result, sort_keys=True))
