# F2.W7.B2 — ViewMappingReceipt compatibility and exchange-waist repair

This branch implements the minimum Wave-6 B6 repair without collapsing native representation mappings, migration records, privacy exports, and semantic exchange manifests into one protocol.

## Material delta

- accepts `mapping_id` only through an explicit versioned adapter;
- emits canonical `mapping_receipt_id` while preserving the legacy alias;
- requires `mapping_kind`, `claim_ceiling`, `currentness`, and provenance;
- preserves identity and source/target lens references;
- keeps privacy export and exchange manifests as different semantic roles;
- provides a typed bridge receipt rather than field renaming;
- verifies deterministic exchange export/import and fails closed on tampering;
- reruns the integrated-native 13-case fixture.

## Result

```yaml
cases: 13
passed: 13
failed: 0
terminal: VIEW_MAPPING_AND_EXCHANGE_WAIST_REPAIR_PASS
```

## Nonclaims

This is controlled local migration and exchange-waist evidence only. It does not establish universal schema equivalence, production migration safety, registry/federation support, hosted coordination, release, or owner admission.
