# F.RUV.W3Q2Q.B2 — Corrected-Target Q8 Independent Rerun

## Route

```text
web.route -> web.branch -> web.reentry -> local.task
-> core.intake -> core.work -> local.worker / core.action
-> local.cross-home -> web.branch return
```

Control source: `pakkinlau/StewardStack@5713f1fffdea8e56dd6f0242a4c247c7b4ae7659`  
Route-semantic tree: `1b30eec0f7967f8ad24fab6a55bfaea2ddaec719`  
Route-launch digest: `a4848d67212416935e25d8f4fc09b3aeee1b62b4c761c5cfd7055eb0e4b26baa`

## Target

```text
FinalIntegratedW3RTarget.v2
identity: sha256:208226ea0c9aa010dd7d9820d4e64d6ec2e6c44fb26fc29074713a0cc6aab611
tree: 1a5ce04666a042d8789a3ee0dc0761e530250a633b15a3d0f40cd2a896bfa0d7
archive: 3a247cc88c9a5a6ccce83ad0b645c87330e6cb471ce0a3663771cc8a65dd6b98
```

The 171-file target was verified before and after execution and was not modified.

## Result

```text
target/currentness/integration controls: 13/14 PASS
integrated unit suite:                 128/128 PASS
original W3.B8 attacks:                  5/5 PASS
expanded attacks:                       27/32 PASS
terminal: REPAIR_REQUIRED_AFTER_VALIDITY_ATTACK
first zero: IC05
```

Residuals:

- `IC05`: public replay omits typed evidence and comparator admission operands;
- `CS04`: consent receipt time is not ordered before event capture;
- `TR02`: right censoring masks observed non-identifiability;
- `HS04`: threshold policy may change inside one experiment epoch without a frozen receipt;
- `SD02`: semantically material additive fields default to `claim_impact=NONE`;
- `AF03`: positive admission ignores an explicit unchanged-next-action judgment.

This repair terminal is the completed output of the qualification branch. It does not open Wave 4.

## Boundary

Controlled mechanical qualification only. No prospective-human readiness, repeat-use value, retention, accumulated-history benefit, product direction, production security, release, merge, cutover, or owner admission is established.
