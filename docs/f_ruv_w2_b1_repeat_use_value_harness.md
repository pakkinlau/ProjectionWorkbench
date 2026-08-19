# F.RUV.W2.B1 — Repeat-Use Value Discovery Harness

`RepeatUseValueDiscoveryHarness.v1` is a dependency-free, local-first,
append-only harness for the Wave-1 repeat-use measurement constitution.

It implements deterministic event capture, episode/trajectory replay, source and
feature-flag freezing, separately revocable consent scopes, burden accounting,
comparator identifiers, agency events, lawful negative terminals, and explicit
export/deletion receipts.

The default fixture deliberately ends at `RIGHT_CENSORED`. Mechanical markers
such as source reopening, lens construction, exact reentry, successful replay,
or elapsed time never populate human-only judgment fields.

## Canonical execution route

```text
web.reentry
-> local.task
-> core.intake
-> core.work
-> local.worker / core.action
-> local.cross-home
-> web.branch return
-> F.RUV.W2.RollingSynthesis
```

## Validation

```bash
PYTHONPATH=src python -m unittest discover -s tests -v
PYTHONPATH=src python -m repeat_use_harness fixture --output /tmp/ruv-fixture-a
PYTHONPATH=src python -m repeat_use_harness fixture --output /tmp/ruv-fixture-b
```

The two fixture receipts must have the same digest and must report
`RIGHT_CENSORED` with `human_value_supported=false`.

## Claim boundary

Harness/component construction and R0 mechanical replay only. No human
repeat-use value, retention, product direction, interpersonal value, hosted
necessity, market demand, release, merge, or owner admission is established.
