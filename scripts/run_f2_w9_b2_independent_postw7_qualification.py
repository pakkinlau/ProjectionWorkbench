from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess
import tomllib
from typing import Any

from scripts.run_f2_w8_b2_postw7_integration import run as run_integrated_witness

ROOT = Path(__file__).resolve().parents[1]
PR17_BASE = "19478eda855d39d4a6477873e28bf0248e59a16f"
PR19_CANDIDATE = "19cab543f1350a3fb51770745b68b91980ad4a03"

EXPECTED_BLOBS = {
    "src/project_semantics/interoperability_v2.py": "3897e0bdb33d3086e43018d8d605be8b97e016f0",
    "src/project_semantics/cross_domain.py": "ef8848180df51239cd62a3a8cfc08d8cb10e693f",
    "src/project_semantics/privacy_v2.py": "016d5a5d8c59b8b8b857b27d9871979ceebecdc7",
    "src/project_semantics/source_ingestion.py": "71c9d28d8bc20c95961cc92cd40e869ab98085f1",
    "src/project_semantics/event_spine.py": "4aba40b2e97f47350396a8dc343e2cad9df424f4",
    "scripts/run_f2_w8_b2_postw7_integration.py": "4d8f11fecdf210d16d0204025da5dd94951f719a",
    "fixtures/cookery/bundle.json": "455235260e86e7e320152d8bf8751c3061b2b9a7",
    "fixtures/farming/bundle.json": "6c3ab82835b80112d2a5adbb202f7d2ecfa2511a",
}

QUALIFICATION_PREFIXES = (
    ".github/workflows/f2-w9-b2-",
    "docs/f2_w9_b2_",
    "fixtures/post_w7_qualification/",
    "receipts/f2_w9_b2_",
    "scripts/run_f2_w9_b2_",
    "tests/test_f2_w9_b2_",
)

BANNED_HOSTED_IMPORTS = (
    "import requests",
    "from requests",
    "import httpx",
    "from httpx",
    "import boto3",
    "from boto3",
    "import socket",
    "from socket",
)


def git(*args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=check,
    )


def is_ancestor(ancestor: str, descendant: str) -> bool:
    return git("merge-base", "--is-ancestor", ancestor, descendant, check=False).returncode == 0


def blob_at(commit: str, path: str) -> str:
    return git("rev-parse", f"{commit}:{path}").stdout.strip()


def qualification_only_delta() -> tuple[bool, list[str]]:
    changed = [
        line.strip()
        for line in git("diff", "--name-only", f"{PR19_CANDIDATE}..HEAD").stdout.splitlines()
        if line.strip()
    ]
    illegal = [path for path in changed if not path.startswith(QUALIFICATION_PREFIXES)]
    return not illegal, changed


def source_controls_present() -> dict[str, bool]:
    source = (ROOT / "src/project_semantics/source_ingestion.py").read_text(encoding="utf-8")
    privacy = (ROOT / "src/project_semantics/privacy_v2.py").read_text(encoding="utf-8")
    event_spine = (ROOT / "src/project_semantics/event_spine.py").read_text(encoding="utf-8")
    return {
        "source_currentness_rank": "_CURRENTNESS_RANK" in source,
        "source_semantic_envelope_fail_closed": "_validate_semantic_envelope" in source,
        "source_content_identity": "content_identity" in source,
        "source_supersession": "supersedes" in source,
        "source_reentry_eligibility": "eligible_for_reentry" in source,
        "privacy_manifest_identity": "manifest_digest" in privacy,
        "privacy_currentness": "currentness" in privacy,
        "privacy_revocation_tombstone": "TOMBSTONED" in privacy and "REVOKED" in privacy,
        "event_spine_no_cutover_field": "canonical_cutover_authorized" in event_spine,
    }


def hosted_dependency_check() -> dict[str, Any]:
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    dependencies = list(project.get("project", {}).get("dependencies", []))
    source_text = "\n".join(
        path.read_text(encoding="utf-8")
        for path in sorted((ROOT / "src/project_semantics").glob("*.py"))
    ).casefold()
    banned = [token for token in BANNED_HOSTED_IMPORTS if token in source_text]
    return {
        "declared_dependencies": dependencies,
        "banned_hosted_imports": banned,
        "pass": not dependencies and not banned,
    }


def run() -> dict[str, Any]:
    head = git("rev-parse", "HEAD").stdout.strip()
    lineage = {
        "pr17_is_ancestor_of_pr19": is_ancestor(PR17_BASE, PR19_CANDIDATE),
        "pr19_is_ancestor_of_qualification_head": is_ancestor(PR19_CANDIDATE, head),
    }
    blob_checks = {
        path: blob_at(PR19_CANDIDATE, path) == expected
        for path, expected in EXPECTED_BLOBS.items()
    }
    qualification_delta_ok, qualification_delta = qualification_only_delta()

    integrated = run_integrated_witness()
    integrated_checks = dict(integrated.get("checks", {}))
    required_integrated = {
        "canonical_source_not_mutated",
        "cookery_regression",
        "event_spine_cutover_disabled",
        "exchange_interoperable",
        "farming_regression",
        "round_trip_equal",
    }
    integrated_ok = (
        integrated.get("terminal") == "POST_W7_EXCHANGE_DOMAIN_NEUTRAL_INTEGRATION_PASS"
        and integrated.get("passed") is True
        and required_integrated.issubset(integrated_checks)
        and all(integrated_checks[name] is True for name in required_integrated)
    )

    controls = source_controls_present()
    hosted = hosted_dependency_check()
    claim_ceiling = str(integrated.get("claim_ceiling", ""))
    claim_ceiling_ok = bool(claim_ceiling.strip()) and "only" in claim_ceiling.casefold()

    checks: dict[str, bool] = {
        "exact_pr17_base_lineage": all(lineage.values()),
        "w7_b2_mapping_exchange_presence": all(
            blob_checks[path]
            for path in (
                "src/project_semantics/interoperability_v2.py",
                "scripts/run_f2_w8_b2_postw7_integration.py",
            )
        ),
        "w7_b3_domain_neutral_presence": all(
            blob_checks[path]
            for path in (
                "src/project_semantics/cross_domain.py",
                "fixtures/cookery/bundle.json",
                "fixtures/farming/bundle.json",
            )
        ),
        "privacy_currentness_controls": all(
            controls[name]
            for name in (
                "privacy_manifest_identity",
                "privacy_currentness",
                "privacy_revocation_tombstone",
            )
        ),
        "source_ingestion_controls": all(
            controls[name]
            for name in (
                "source_currentness_rank",
                "source_semantic_envelope_fail_closed",
                "source_content_identity",
                "source_supersession",
                "source_reentry_eligibility",
            )
        ),
        "exchange_round_trip": integrated_checks.get("round_trip_equal") is True,
        "cookery_farming_regressions": integrated_checks.get("cookery_regression") is True
        and integrated_checks.get("farming_regression") is True,
        "no_event_spine_cutover": integrated_checks.get("event_spine_cutover_disabled") is True
        and controls["event_spine_no_cutover_field"],
        "no_hosted_dependency": hosted["pass"],
        "canonical_source_not_mutated": integrated_checks.get("canonical_source_not_mutated") is True,
        "claim_ceiling_continuity": claim_ceiling_ok,
        "qualification_branch_does_not_modify_product_code": qualification_delta_ok,
        "integrated_witness_replay": integrated_ok,
        "exact_candidate_blobs": all(blob_checks.values()),
    }

    passed = all(checks.values())
    terminal = (
        "POST_W7_INTEGRATED_CANDIDATE_INDEPENDENTLY_QUALIFIED"
        if passed
        else "REPAIR_REQUIRED"
    )
    return {
        "schema_version": "gva06.f2.w9.b2.independent-postw7-qualification.v1",
        "qualified_candidate_commit": PR19_CANDIDATE,
        "qualification_head": head,
        "lineage": lineage,
        "blob_checks": blob_checks,
        "qualification_delta": qualification_delta,
        "source_control_checks": controls,
        "hosted_dependency_check": hosted,
        "integrated_witness": integrated,
        "checks": checks,
        "passed": passed,
        "terminal": terminal,
        "claim_boundary": (
            "Independent controlled local qualification only; no human/private value, "
            "production security, hosted necessity, release, merge, or owner-admission claim."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    result = run()
    Path(args.output).write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "passed": result["passed"],
        "terminal": result["terminal"],
        "checks_passed": sum(result["checks"].values()),
        "checks_total": len(result["checks"]),
    }, sort_keys=True))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
