# F2.W6.B4 Event/Provenance Spine Shadow Migration

Status: bounded shadow-compatible candidate; no canonical cutover.

## Added surface

- append-only event envelopes with stable content-bound event IDs;
- previous-event chaining and deterministic event/source horizon digests;
- migration from the current mutable v0 project record into a shadow ledger;
- immutable receipt events and source-bound provenance;
- reducers for the existing v0 compatibility state;
- derived `ProjectLens`, provisional semantic state, capability projection,
  profile, public projection, and currentness views;
- materialized-view envelopes binding event horizon, source horizon, reducer
  version, policy, expiry/currentness, and a reproduction receipt;
- explicit revocation replay in the current capability projection.

## Nonclaims

The shadow ledger is not the canonical store, does not rewrite prior history, and
does not authorize a cutover. Fixture parity does not establish production
migration safety, full historical completeness, semantic equivalence for every
future object, user value, release, or owner admission.

## Validation

```bash
PYTHONPATH=src python -m unittest tests/test_event_spine_shadow.py -v
PYTHONPATH=src python scripts/run_event_spine_shadow_witness.py \
  --fixture fixtures/event_spine_shadow/bundle.json \
  --output /tmp/f2-w6-b4-shadow-result.json
```
