# F.RUV.W3R.B2 — Custody, Privacy, and Burden Repair

## Route

```text
web.branch
-> web.reentry
-> local.task
-> core.intake
-> core.work
-> local.worker / core.action
-> local.cross-home
-> web.branch return
-> F.RUV.W3R.RollingSynthesis
```

Control source: `pakkinlau/StewardStack@a644409f293609ec2e6f0cb230ba0799d455ec1d`  
Route-launch digest: `a4848d67212416935e25d8f4fc09b3aeee1b62b4c761c5cfd7055eb0e4b26baa`  
Stacked repair base: `pakkinlau/ProjectionWorkbench@e289a2ff01ee31f2f32e85247a2956a835e3c175`

## Repair

`CustodyPrivacyBurdenRepair.v1` preserves one controlled-local custody/export/import/delete authority and adds one typed low-burden adapter over it.

The repair closes the eight findings returned by `F.RUV.W3.B2`:

- undeclared events and payload fields fail closed;
- raw, private, sealed, credential, and secret payload coordinates fail before capture;
- export purpose and matching revocable scopes are bound before byte production;
- every portable export uses the canonical verify/import surface;
- deletion cascades, tombstones records, and emits typed export-handle revocation notices;
- burden observations are append-only and aggregate monotonically;
- B1/B6 human-only fields map through a missingness-preserving adapter;
- B1/B6 burden fields map through a canonical schema including `lock_in_dependence`.

## Validation

```text
Inherited custody membrane: 30/30 PASS
Focused repair unit tests: 12/12 PASS
Independent B2 requalification: 20 PASS / 0 FAIL / 2 RIGHT_CENSORED
```

The right-censored coordinates remain real human burden acceptability, trust/control judgment, production security/legal compliance, secure erase, and universal cross-platform portability.

## Claim boundary

Controlled-local custody, privacy, burden, portability, and schema-adapter repair only. No human repeat-use value, retention, production security, legal compliance, product direction, release, merge, cutover, or owner admission is established.
