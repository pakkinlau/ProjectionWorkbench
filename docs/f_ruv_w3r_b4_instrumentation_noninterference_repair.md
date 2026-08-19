# F.RUV.W3R.B4 — Instrumentation Noninterference Repair

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
```

Control source: `pakkinlau/StewardStack@a644409f293609ec2e6f0cb230ba0799d455ec1d`  
Route launch digest: `a4848d67212416935e25d8f4fc09b3aeee1b62b4c761c5cfd7055eb0e4b26baa`  
Common repair base: `pakkinlau/ProjectionWorkbench@510c60889d9ed7d3014cb6d9d6607ef7305c141c`

## Result

This branch implements `InstrumentationNoninterferenceRepair.v1` as a strict, stdlib-only qualification envelope around the repeat-use harness.

It closes the six repair coordinates identified by the Wave-3 instrumentation-reactivity audit:

1. full experiment-epoch and surface-snapshot binding;
2. the complete fourteen-flag registry plus twelve content-addressed surface digests;
3. surface-change, typed epoch close/restart/right-censor, pooling, and development/qualification firewall;
4. prospective familiarization plus product-constant instrumentation-dose contrast;
5. frozen threshold/evidence/evaluator/value/analysis policy and exact independent-review binding;
6. explicit loss-declared migration from the low-burden B6 event vocabulary to the canonical B1 event vocabulary.

## New public surface

`repeat_use_harness.noninterference` provides:

- `FrozenQualificationPolicy.v1` construction and validation;
- `ExperimentEpoch.v1` construction and validation;
- `EpisodeSurfaceSnapshot.v1` construction and validation;
- event-to-epoch/snapshot/policy binding;
- `SurfaceChangeReceipt.v1` and `EpochBoundaryReceipt.v1`;
- `PoolingEligibilityReceipt.v1`;
- `InterfaceFamiliarizationReceipt.v1`;
- `InstrumentationReactivityContrast.v1` and bounded evaluation;
- exact independent-review content binding;
- no replay-time policy override in qualification mode;
- B6-to-B1 event migration with `EventSchemaMappingReceipt.v1`;
- a deterministic `InstrumentationNoninterferenceRepair.v1` witness.

## Validation

```text
PYTHONPATH=src python -m unittest discover -s tests -v
PYTHONPATH=src python scripts/run_f_ruv_w3r_b4_noninterference_repair.py
```

The dedicated test module exercises policy freezing, epoch/surface binding, full flag closure, event binding, product and measurement drift, typed epoch closure, pooling, familiarization, instrumentation reactivity, independent review, development/qualification separation, event migration, and deterministic replay.

## Terminal

```text
INSTRUMENTATION_NONINTERFERENCE_REPAIR_READY
```

This is a repair-component completion terminal. Wave 4 remains closed until the W3R returns are integrated on one current harness line and survive independent W3Q requalification.

## Claim boundary

No human repeat-use value, retention, accumulated-history benefit, product direction, interpersonal/network value, market demand, release, merge, cutover, or owner admission is established.
