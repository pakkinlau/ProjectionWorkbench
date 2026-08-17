# F2.W5.B6 Schema Migration and Exchange Interoperability

This bounded branch adds a deterministic v0-to-v1 exchange migration witness for:

- work modules;
- connectors;
- view-mapping receipts;
- contribution records;
- evidence scopes;
- attestations;
- composition receipts.

The migration preserves source provenance and stable identities, records material information loss, revalidates connectors and mappings noncompensatorily, and round-trips through a digest-manifest exchange package without rewriting canonical source state.

It is local interoperability research only. It does not establish a public registry, universal schema, semantic equivalence, release compatibility, or owner admission.
