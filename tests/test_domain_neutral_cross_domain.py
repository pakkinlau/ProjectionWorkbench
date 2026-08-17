from __future__ import annotations

import json
from pathlib import Path

from project_semantics.cross_domain import run_cross_domain_pressure

ROOT = Path(__file__).resolve().parents[1]


def _load(domain: str):
    return json.loads((ROOT / "fixtures" / domain / "bundle.json").read_text())


def test_cookery_and_farming_preserve_positive_and_negative_dispositions():
    cookery = run_cross_domain_pressure(_load("cookery"))
    farming = run_cross_domain_pressure(_load("farming"))
    assert cookery["passed"] and farming["passed"]
    assert len(cookery["case_results"]) == 5
    assert len(farming["case_results"]) == 6
    assert cookery["primary_disposition"] == "SHARED_CORE_PLUS_LOCAL_EXTENSION"
    assert farming["primary_disposition"] == "SHARED_CORE_PLUS_LOCAL_EXTENSION"
    dispositions = {x["disposition"] for x in cookery["case_results"] + farming["case_results"]}
    assert {"NO_SAFE_GLOBALIZATION", "NON_IDENTIFIABLE", "GRAMMAR_INSUFFICIENT"} <= dispositions


def test_shared_evaluator_does_not_leak_other_domain_terms():
    cookery = json.dumps(run_cross_domain_pressure(_load("cookery")), sort_keys=True).casefold()
    farming = json.dumps(run_cross_domain_pressure(_load("farming")), sort_keys=True).casefold()
    assert "farming" not in cookery and "agronomic" not in cookery
    assert "cookery" not in farming and "culinary" not in farming
