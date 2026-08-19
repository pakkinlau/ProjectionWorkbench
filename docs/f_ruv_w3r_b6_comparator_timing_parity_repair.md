# F.RUV.W3R.B6 — Comparator Timing Parity Repair

## Canonical route

```text
web.reentry
-> local.task
-> core.intake
-> core.work
-> local.worker / core.action
-> local.cross-home
-> web.branch
-> F.RUV.W3R.RollingSynthesis
```

Control source: `pakkinlau/StewardStack@a644409f293609ec2e6f0cb230ba0799d455ec1d`  
Route-launch digest: `a4848d67212416935e25d8f4fc09b3aeee1b62b4c761c5cfd7055eb0e4b26baa`  
Repair base: `pakkinlau/ProjectionWorkbench@e289a2ff01ee31f2f32e85247a2956a835e3c175`

## Repair result

The branch implements all seven repair objects identified by the accepted Wave-3 B6 qualification:

1. `ComparatorArmIdentityMap.v1`
2. `CanonicalComparatorEvent.v1`
3. `ComparatorEventAdapterSet.v1`
4. `CanonicalHistoryCondition.v1`
5. `GenericBaselineCaptureAdapter.v1`
6. `BaselineTimingParityReceipt.v1`
7. `SyntheticTimingParityCorpus.v2`

The canonical event contract binds comparator/history identity, strict sequence, monotonic active time, UTC audit time, content-bound event identity, hash-chain integrity, source/task/evaluator/public-information digests, measurement dose, assistance policy, familiarization, budget, carryover plan, consent, feature namespace, and burden separation.

Adapters for B1, B4, B6, and B7 fail closed when a monotonic witness or an explicit consent/feature/history mapping is absent. No wall-clock value is silently promoted into monotonic time.

The generic-project-memory baseline is valid only when it has matched source, task, evaluator, public-information, assistance, timing, familiarization, measurement-dose, and carryover envelopes while remaining blind to Task-F semantic objects, Task-F history, and hidden chat state.

`BaselineTimingParityReceipt.v1` evaluates P01–P12 noncompensatorily. One failed gate blocks causal comparison. The deterministic six-arm fixture passes all twelve gates at the controlled-fixture ceiling.

## Terminal

```text
COMPARATOR_TIMING_PARITY_REPAIR_IMPLEMENTED_AT_CONTROLLED_FIXTURE_CEILING
```

This does not open Wave 4. The repair must be integrated with the other W3R branches and survive independent W3Q requalification.

## Claim boundary

Comparator identity, timing, exposure, burden, adapter, and controlled-fixture parity repair only. No prospective human comparison, repeat-use value, retention, accumulated-history benefit, product direction, interpersonal/network value, market demand, release, merge, cutover, or owner admission is established.
