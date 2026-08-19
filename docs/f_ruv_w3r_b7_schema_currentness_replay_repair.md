# F.RUV.W3R.B7 — Schema, Currentness, and Replay Repair

## Route

```text
web.route
-> web.reentry
-> local.task
-> core.intake
-> core.work
-> local.worker / core.action
-> local.cross-home
-> web.branch
-> F.RUV.W3R.RollingSynthesis
```

The branch implements the five local repair packages returned by the accepted
`F.RUV.W3.B7` qualification. It does not perform the independent R6
requalification and cannot open Wave 4 by itself.

## Implemented repair surfaces

1. Strict finite JSON parsing, duplicate-key rejection, resource limits, and
   receipt-bearing schema envelopes.
2. Explicit migration and terminal-mapping receipts with source/target digests,
   identity aliases, information-loss fields, and rollback references.
3. Content-bound event identities, contiguous sequences, monotone time,
   trajectory/participant/project/inquiry binding, and deterministic chain roots.
4. Noncompensatory route-policy, source-snapshot, product-phase, consent,
   human-authority, and claim-ceiling bindings.
5. Tombstone/revocation/delete invalidation that prevents replay resurrection.

## R6 boundary

`CrossVersionReplayOperand.v1` is prepared for a later independent fresh-agent
qualification covering exact v1, additive minor migration, unknown major
rejection, migrated export/import, rollback replay, and tombstone non-resurrection.

## Claim boundary

Local implementation and deterministic repair validation only. No independent
Wave-3 qualification, human repeat-use value, retention, product direction,
release, merge, cutover, or owner admission is established.
