# F2.W3.B4 — Contribution and Evidence Adversarial Assessment

## Identity

```yaml
programme_id: GVA06.F2.open-work-semantics-mvp.v1
wave_id: F2.W3
branch_id: F2.W3.B4
terminal_object: ContributionBoundaryAdversarialAssessment.v1
source_kernel_repository: pakkinlau/ProjectionWorkbench
source_kernel_commit: 2d5af1ea356258bd163e55bbf30cf988da5e2970
source_kernel_blob: 0aa0337840a15feb3f247a57a9834848960ff614
route: web.route -> web.reentry -> local.task -> web.branch
artifact_state: EXECUTED_VALIDATED
terminal_disposition: REPAIR_REQUIRED
```

## Question

Can the current local kernel preserve useful human, AI, tool, joint, uncertain, disputed, and attested contribution distinctions without becoming an automatic authorship or capability oracle?

## Controlled witness

Fifteen controlled cases were executed against the pinned `validate_contribution` semantics.

```yaml
cases: 15
policy_matches: 9
policy_mismatches: 6
unit_tests: 6/6 PASS
```

## Requirement disposition

| Requirement | Disposition |
|---|---|
| uncertainty and dispute states | PASS |
| agent self-promotion is blocked | PASS |
| human/AI/joint contribution modes are representable | PASS, but relationships are free-text rather than typed |
| AI proposal can remain proposed | PASS |
| promoted states require non-empty evidence references | PASS |
| artifact output cannot imply mastery | FAIL |
| activity volume cannot imply capability | FAIL |
| third-party attestation identifies attestor, relationship and scope | FAIL |
| claim narrowing/revocation is a governed transition | FAIL |
| structured evidence scope and assessor identity are exposed | FAIL |

## Material findings

### Supported

- Agent-originated records cannot enter directly as `human_confirmed`, `third_party_attested`, or `independently_assessed`.
- `unresolved`, `disputed`, `joint_inseparable`, human-framed/AI-executed, and bounded human correction records are representable.
- Promoted contribution states require at least one evidence reference.

### First zeros

```text
CAPABILITY_ASSERTION_SEPARATION_ABSENT
ATTESTATION_AND_ASSESSOR_SCOPE_CONTRACT_ABSENT
ASSERTION_TRANSITION_CONTRACT_ABSENT
STRUCTURED_EVIDENCE_SCOPE_ABSENT
```

The current validator accepts records that:

- infer broad expertise from activity counts;
- infer mastery from an AI-produced artifact;
- claim third-party attestation without an attestor contract;
- revoke or supersede a claim without naming the prior assertion, reason, evidence, or authority;
- claim independent assessment without structured evaluator identity or evidence scope.

## Minimal repair frontier

1. Separate `ContributionRecord` from `CapabilityAssertion`.
2. Add `EvidenceScope` with observation class, coverage, independence, assessor/evaluator identity, currentness, and claim ceiling.
3. Add a scoped `Attestation` object with attestor, relationship, observed facts, evidence access, independence, and nonclaims.
4. Add `AssertionTransition` with prior assertion, from/to state, authority actor, reason, evidence, and exact claim delta.
5. Add typed relations linking AI proposals to human rejection, correction, selection, or verification.
6. Require recurrence, transfer, currentness, and independent-assessment gates before capability projection; activity volume is not sufficient evidence.
7. Forbid mastery or universal-expertise semantics inside the contribution-record layer.

## Claim ceiling

This branch establishes only a bounded adversarial assessment of the pinned local kernel. It does not determine legal authorship, true intent, human mastery, general capability, market trust, or external authority.

## N3 return

```yaml
completion_predicate_result: PASS
branch_terminal: REPAIR_REQUIRED
merge_role: QUALIFICATION
merge_target: web.synthesize -> web.steer
frontier_effect: contribution mechanics are partially supported; capability, attestation, transition, and evidence-scope semantics require a bounded repair route
```
