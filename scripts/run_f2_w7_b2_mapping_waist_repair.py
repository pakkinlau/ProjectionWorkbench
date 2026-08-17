from __future__ import annotations

import json
import tempfile
from copy import deepcopy
from pathlib import Path

from project_semantics.interoperability_v2 import *

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures/view_mapping_waist/native_bundle.json"


def run() -> dict:
    source = json.loads(FIXTURE.read_text())
    mapping = next(x["payload"] for x in source["records"] if x["kind"] == "ViewMappingReceipt")
    policy = {
        mapping["mapping_id"]: {
            "mapping_kind": "ALIGNMENT",
            "claim_ceiling": "View relation only; explicit W7 adapter",
            "currentness": "current",
            "provenance_refs": ["PR11:representation.py", "W6.B6:independent-fixture"],
        }
    }
    cases = []

    def case(case_id: str, expected: str, fn) -> None:
        try:
            value = fn()
            observed = "PASS" if value is not False else "FAIL"
        except Exception:
            observed = "FAIL"
        cases.append(
            {
                "case_id": case_id,
                "expected": expected,
                "observed": observed,
                "policy_match": expected == observed,
            }
        )

    case("RT01", "FAIL", lambda: validate_mapping_v2(mapping))
    alias = deepcopy(mapping)
    alias["mapping_receipt_id"] = alias.pop("mapping_id")
    case("RT02", "FAIL", lambda: validate_mapping_v2(alias))
    case(
        "RT03",
        "PASS",
        lambda: validate_mapping_v2(
            adapt_native_view_mapping(mapping, **policy[mapping["mapping_id"]])[0]
        )
        or True,
    )
    conflict = deepcopy(mapping)
    conflict["mapping_receipt_id"] = "mapping:other"
    case("RT04", "FAIL", lambda: record_identity(conflict))
    case(
        "RT05",
        "PASS",
        lambda: adapt_native_view_mapping(mapping, **policy[mapping["mapping_id"]])[1][
            "identity_preserved"
        ],
    )
    bad_policy = deepcopy(policy[mapping["mapping_id"]])
    bad_policy["mapping_kind"] = ""
    case("RT06", "FAIL", lambda: adapt_native_view_mapping(mapping, **bad_policy))
    bad_policy2 = deepcopy(policy[mapping["mapping_id"]])
    bad_policy2["claim_ceiling"] = ""
    case("RT07", "FAIL", lambda: adapt_native_view_mapping(mapping, **bad_policy2))

    migrated, receipt = migrate_native_bundle(source, mapping_policies=policy)
    case(
        "RT08",
        "PASS",
        lambda: receipt["disposition"] == "MIGRATED_LOSSLESSLY"
        and receipt["revalidation"]["disposition"] == "INTEROPERABLE",
    )

    broken = deepcopy(migrated)
    connector = next(
        x["payload"] for x in broken["records"] if x["kind"] == "ConnectorManifest"
    )
    connector["accepted_target_versions"] = ["9.9.9"]
    case(
        "RT09",
        "PASS",
        lambda: validate_exchange_bundle(broken)["disposition"] == "INCOMPATIBLE",
    )

    broken2 = deepcopy(migrated)
    attestation = next(
        x["payload"] for x in broken2["records"] if x["kind"] == "Attestation"
    )
    attestation["evidence_scope_refs"] = ["scope:missing"]
    case(
        "RT10",
        "PASS",
        lambda: validate_exchange_bundle(broken2)["disposition"] == "INCOMPATIBLE",
    )

    def roundtrip() -> bool:
        with tempfile.TemporaryDirectory() as tmp:
            manifest = export_exchange_bundle(migrated, Path(tmp))
            imported, import_receipt = import_exchange_bundle(Path(tmp))
            return (
                imported == migrated
                and import_receipt["integrity"] == "PASS"
                and manifest["manifest_role"] == "SEMANTIC_EXCHANGE"
            )

    case("RT11", "PASS", roundtrip)

    def tamper() -> None:
        with tempfile.TemporaryDirectory() as tmp:
            export_exchange_bundle(migrated, Path(tmp))
            payload = Path(tmp) / "exchange_bundle.json"
            payload.write_text("{}\n")
            import_exchange_bundle(Path(tmp))

    case("RT12", "FAIL", tamper)

    privacy = {
        "schema_version": PRIVACY_EXPORT_V1,
        "manifest_role": "SELECTIVE_PRIVACY_EXPORT",
        "manifest_digest": "sha256:" + "a" * 64,
    }
    with tempfile.TemporaryDirectory() as tmp:
        exchange = export_exchange_bundle(migrated, Path(tmp))
        bridge = bridge_privacy_export_to_exchange(
            privacy,
            exchange,
            currentness_policy="RECHECK_BEFORE_EXCHANGE",
            security_policy="VERIFY_BOTH_MANIFESTS",
            information_loss=["private payload omitted"],
        )
    case(
        "RT13",
        "PASS",
        lambda: bridge["payload_relabelled"] is False
        and bridge["bridge_kind"]
        == "PRIVACY_EXPORT_TO_SEMANTIC_EXCHANGE_POINTER",
    )

    return {
        "schema_version": "gva06.f2.w7.b2.repair-witness.v1",
        "case_count": len(cases),
        "passed": sum(x["policy_match"] for x in cases),
        "failed": sum(not x["policy_match"] for x in cases),
        "cases": cases,
        "terminal": "VIEW_MAPPING_AND_EXCHANGE_WAIST_REPAIR_PASS"
        if all(x["policy_match"] for x in cases)
        else "REPAIR_REQUIRED",
        "adapter_receipt": receipt["mapping_adapter_receipts"][0],
        "migration_receipt": receipt,
        "bridge_receipt": bridge,
        "claim_boundary": "Controlled local mapping/exchange-waist mechanics only.",
    }


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    result = run()
    Path(args.output).write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(
        json.dumps(
            {key: result[key] for key in ("case_count", "passed", "failed", "terminal")},
            sort_keys=True,
        )
    )
