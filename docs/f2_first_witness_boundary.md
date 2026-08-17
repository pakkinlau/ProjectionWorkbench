# F2 First-Witness Boundary

Status: local prototype candidate.

## Implemented boundary

The package provides deterministic local records for:

- `ProjectRef` and external source links;
- `TaskContext` and derived `ProjectLens` objects;
- `WorkEpisode` and contribution-state records;
- `WorkModuleManifest` and `ConnectorManifest` objects;
- noncompensatory composition gates and `CompositionReceipt`;
- selective projections governed by `ProjectionPolicy`;
- deterministic export and replay fixtures.

## Canonical versus derived

Canonical local records are append-only JSON documents inside a local project
store. Lenses and public/collaborator projections are derived. Deleting or
regenerating a projection does not rewrite the canonical local history.

## Nonclaims

- The schema is not a universal ontology.
- A lens is not the one optimal representation.
- An observed activity is not automatically a contribution.
- An agent proposal is not human confirmation.
- A composition that executes is not scientifically adequate by implication.
- The package does not host the authoritative bytes of linked projects.
- No hosted identity, registry, social, trust, or admission layer is included.
- No package release is authorized by this witness.
