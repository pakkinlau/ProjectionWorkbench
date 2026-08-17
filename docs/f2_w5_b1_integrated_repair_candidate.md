# F2.W5.B1 Integrated Repair Candidate

This candidate integrates the Wave-2 kernel with the four accepted Wave-4 repair surfaces while preserving one canonical owner for each public type.

## Canonical ownership

- `project_semantics.__init__`: canonical v0 project, episode, module, connector, lens, mapping, composition, and projection kernel.
- `project_semantics.source_ingestion`: source-derived semantic extraction and reentry extension.
- `project_semantics.contribution`: contribution/evidence/attestation/capability extension.
- `project_semantics.privacy`: recursive projection, reference identity, export/import, revocation, and portability membrane.
- `project_semantics.representation`: architecture/reusable-method lens and view-mapping extension.

No extension is permitted to redefine the canonical project store or silently promote evidence, capability, privacy, or representation claims.

## Integration method

Wave-4 B1/B2/B3 are incorporated as their exact branch deltas. Wave-4 B4 was a local replacement patch over the canonical core; to avoid a competing owner for `project_semantics.__init__`, its architecture/reusable-method and mapping behavior is migrated into the dedicated `project_semantics.representation` extension. The original B4 patch remains an immutable lineage pointer.

## Validation ceiling

Branch-local tests and witnesses are replayed together with an integration-specific representation test. Passing tests establish only a reviewable local integration candidate. They do not establish owner merge, release, production security, human value, market demand, general semantic adequacy, or external admission.
