# F2.W8.B1 — Integrated-head lineage/currentness requalification

Status: `INDEPENDENT_REQUALIFICATION_CANDIDATE`.

This observer branch binds the exact Wave-7 integrated candidate at PR17/head
`19478eda855d39d4a6477873e28bf0248e59a16f` and executes the reentry required by
F2.W7.B5.

## Qualification coordinates

- exact candidate commit remains an ancestor of the observer branch;
- core repair blobs at the candidate commit match their frozen identities;
- only observer/qualification files differ after the candidate commit;
- one canonical owner remains for every public object family;
- contribution requalification remains 12/12 with zero false accepts/rejects;
- privacy requalification remains 20/20 with zero findings;
- source-ingestion generalization repair remains present and executable;
- shadow event-spine parity remains supported;
- the compatibility model remains authoritative;
- event-spine cutover remains disabled;
- claim ceilings remain non-expansive.

## Lawful terminal outcomes

```text
CURRENT_HEAD_QUALIFIED_FOR_HUMAN_VALUE_PILOT
REPAIR_REQUIRED
SOURCE_CURRENTNESS_DRIFT
LINEAGE_GAP
CLAIM_CEILING_DRIFT
NO_SAFE
```

## Claim boundary

This branch independently qualifies exact repository lineage/currentness and
controlled clean-room fixture replay. It does not establish owner merge,
release, production security, actual human-observed value, event-spine cutover,
or Wave-8 completion.
