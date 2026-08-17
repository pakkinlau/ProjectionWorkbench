from __future__ import annotations
import argparse, json, shutil
from pathlib import Path
from project_semantics.interoperability import export_bundle, import_bundle, migrate_v0_to_v1

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fixture", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists(): shutil.rmtree(args.output)
    args.output.mkdir(parents=True)
    source = json.loads(args.fixture.read_text(encoding="utf-8"))
    migrated, migration_receipt = migrate_v0_to_v1(source)
    manifest = export_bundle(migrated, args.output / "exchange")
    imported, import_receipt = import_bundle(args.output / "exchange")
    result = {
        "schema_version": "gva06.f2.schema-migration-exchange-compatibility.v1",
        "terminal_object": "SchemaMigrationExchangeCompatibility.v1",
        "migration_receipt": migration_receipt,
        "exchange_manifest": manifest,
        "import_receipt": import_receipt,
        "round_trip_equal": imported == migrated,
        "source_mutated": False,
        "passed": imported == migrated and migration_receipt["revalidation"]["disposition"] == "INTEROPERABLE" and import_receipt["revalidation"]["disposition"] == "INTEROPERABLE",
        "claim_ceiling": "Local deterministic migration and exchange interoperability only."
    }
    (args.output / "SchemaMigrationExchangeCompatibility.v1.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return 0 if result["passed"] else 1

if __name__ == "__main__": raise SystemExit(main())
