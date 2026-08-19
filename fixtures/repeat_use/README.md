# Deterministic repeat-use fixture

This directory pins the small declarative inputs and content-bound receipt for
`F.RUV.W2.B1.mechanical-fixture.v1`.

Generate the append-only event log and replay outputs with:

```bash
PYTHONPATH=src python -m repeat_use_harness fixture --output /tmp/ruv-fixture
```

Expected result:

- events: 6
- causal terminal: `RIGHT_CENSORED`
- evidence rung: `R0_MECHANICAL`
- `human_value_supported=false`
- replay digest: `33b58812596daac7d3f1e6d7fe1776d3bd28e65426c81ded596b6642bd7c5ab2`

The generated event/replay files are deterministic but are not maintained as a
second canonical source. The package implementation and the pinned inputs below
are the reproduction source.
