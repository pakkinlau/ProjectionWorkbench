# F.RUV.W3Q2Q.B2 — Corrected-Target Full Independent Validity Attack Qualification

## Canonical route

```text
web.route -> web.branch -> web.reentry -> local.task
-> core.intake -> core.work -> local.worker / core.action
-> local.cross-home -> web.branch return
```

Control source: `pakkinlau/StewardStack@5713f1fffdea8e56dd6f0242a4c247c7b4ae7659`  
Route-semantic tree: `1b30eec0f7967f8ad24fab6a55bfaea2ddaec719`  
Route-launch digest: `a4848d67212416935e25d8f4fc09b3aeee1b62b4c761c5cfd7055eb0e4b26baa`

## Corrected immutable target

```text
FinalIntegratedW3RTarget.v2
identity: sha256:208226ea0c9aa010dd7d9820d4e64d6ec2e6c44fb26fc29074713a0cc6aab611
tree: 1a5ce04666a042d8789a3ee0dc0761e530250a633b15a3d0f40cd2a896bfa0d7
archive: 3a247cc88c9a5a6ccce83ad0b645c87330e6cb471ce0a3663771cc8a65dd6b98
```

The target was verified against its 171-entry tree manifest before and after qualification and was not mutated.

## Qualification result

```text
target/currentness gates: 13/13 PASS
integrated unit suite:     128/128 PASS
original W3.B8 attacks:      5/5 PASS
expanded attacks:           27/32 PASS
terminal: REPAIR_REQUIRED_AFTER_VALIDITY_ATTACK
first zero: CS04_CONSENT_ISSUED_AFTER_EVENT_NOT_REJECTED
```

Residual coordinates:

1. `CS04` — consent receipt temporal ordering is not enforced;
2. `TR02` — ordinary right-censor precedence masks observed contamination;
3. `HS04` — mutable thresholds are outcome-sensitive and not bound to a frozen policy receipt;
4. `SD02` — additive minor-version semantic fields default to `claim_impact=NONE`;
5. `AF03` — a positive terminal remains reachable when the human-confirmed next action is unchanged.

A repair terminal is the successful scientific output of this independent branch. It is not a failed execution and does not permit Wave 4 to open.

## Claim boundary

Controlled mechanical qualification only. No prospective-human readiness, repeat-use value, retention, accumulated-history benefit, product direction, production security, release, merge, cutover, or owner admission is established.
