# F2.W7.B2 Execution Receipt

```yaml
branch_id: F2.W7.B2
terminal: VIEW_MAPPING_AND_EXCHANGE_WAIST_REPAIR_PASS
base_commit: dac5ba1f49056dad5d4273e1d53c25bcea73eccd
working_branch: agent/f2-w7-b2-view-mapping-exchange-waist-repair
integrated_native_cases: 13/13 PASS
false_accepts: 0
false_rejects: 0
native_direct_compatibility: FAIL_CLOSED
explicit_adapter: MIGRATED_LOSSLESSLY__INTEROPERABLE
privacy_exchange_waist: DISTINCT_WITH_TYPED_BRIDGE
```

## Material hashes

- `src/project_semantics/interoperability_v2.py` — `d1a17793d00d7c853ce3197c870b605ab138d54e8c98ee7391720dc693480d17`
- `scripts/run_f2_w7_b2_mapping_waist_repair.py` — `d1b12635ba94056671c3ca6eaaebe36089ae1b6967894b5814444877e20f3223`
- `tests/test_interoperability_v2.py` — `6a4b9342fa5deead934735862b4ce5f90ff178a2d5e87570855095ac5654bfac`
- `fixtures/view_mapping_waist/native_bundle.json` — `5cf82553d626b2f9a147deb298171560ed9221de3ec3004991730d6624b8acba`
- `fixtures/view_mapping_waist/result.json` — `902c254ccd4c21898882d5607c36031287d45c9a6e1612cb056116f92d75d08a`

## Validation

```text
PYTHONPATH=src python scripts/run_f2_w7_b2_mapping_waist_repair.py --output fixtures/view_mapping_waist/result.json
{"case_count": 13, "failed": 0, "passed": 13, "terminal": "VIEW_MAPPING_AND_EXCHANGE_WAIST_REPAIR_PASS"}

PYTHONPATH=src:. pytest -q tests/test_interoperability_v2.py
1 passed
```

## Claim boundary

Controlled local mapping/migration/exchange-waist mechanics only. No universal schema, production migration, hosted registry, release, merge, or owner-admission claim is made.
