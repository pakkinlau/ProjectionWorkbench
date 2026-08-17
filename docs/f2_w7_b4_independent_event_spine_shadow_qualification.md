# F2.W7.B4 Independent Event-Spine Shadow Qualification

## Route

```text
web.route -> web.reentry -> local.task
```

Base: `pakkinlau/ProjectionWorkbench@ed8ca19aec46f76a859bd626da59f6499e556357`

This branch independently attacks the Wave-6 shadow event/provenance candidate. It adds no cutover and does not modify `project_semantics.event_spine`.

## Result

```yaml
terminal: KEEP_CURRENT_COMPATIBILITY_MODEL
cases: 16
policy_matches: 9
findings: 7
critical_findings: 1
high_findings: 5
first_zero: ES09
canonical_cutover_recommendation: DO_NOT_CUT_OVER
```

## Supported coordinates

- stable content-bound event identity;
- payload tamper detection;
- ordered-chain and duplicate rejection inside one supplied ledger;
- deterministic bounded reducer replay;
- bounded v0 parity;
- prefix rollback to a compatibility state;
- fail-closed unknown event and event-schema drift.

## Exact findings

1. **Cross-stream injection:** a chain can switch `stream_id` without rejection.
2. **Payload schema:** envelope integrity accepts event-type payloads that reducers cannot lawfully interpret.
3. **Transition replay:** an unbound transition with a false `from_state` can resurrect a revoked contribution into `CurrentCapabilityProjection`.
4. **Expiry:** an already expired materialized view remains labelled current.
5. **Source horizon:** unrelated caller-supplied source horizons are accepted without continuity checks against observed source events.
6. **Concurrent forks:** two valid children of one parent have no conflict, compare-and-swap, merge or rollback disposition.
7. **Chronology:** `recorded_at < happened_at` is accepted without a declared exception policy.

## Decision

The shadow spine remains a useful architecture candidate, but it should not become canonical now. The current compatibility model should remain authoritative while the smallest affected coordinates are repaired and independently rerun.

## Nonclaim

This branch does not establish production event-store correctness, full migration safety, historical completeness, concurrent-write safety, security, user value, release, owner admission or cutover.
