# F2.W5.B2 — Independent Contribution / Capability Red-Team

Status: `REPAIR_REQUIRED`

## Bound source

- Repository: `pakkinlau/ProjectionWorkbench`
- Hardened source branch: `agent/f2-w4-contribution-evidence-hardening`
- Hardened source commit: `3240553dcc4358c2609e95aa002d7b89c9eba61b`
- Current WaveRoute branch: `F2.W5.B2 — IndependentContributionCapabilityRedTeam`

## Independent adversarial families

The red-team independently authored and executed twelve controlled cases covering:

1. AI execution promoted into false human capability through an assertion transition;
2. activity volume / forged recurrence;
3. collusive or weak attestation declared independent;
4. stale evidence after support;
5. irrelevant transfer context;
6. revoked evidence after support;
7. superseded assertion exclusion;
8. attestation subject mismatch and scope laundering;
9. unbound independent-assessment identity;
10. mastery-level promotion;
11. empty-evidence direct support;
12. self-attestation independence mismatch.

## Result

```yaml
cases: 12
policy_matches: 4
false_accepts: 8
false_rejects: 0
terminal: REPAIR_REQUIRED
```

### Controls that held

- mastery/expertise claim levels are rejected;
- empty-evidence direct support is rejected;
- self-attestation cannot claim independent status;
- a superseded assertion is excluded from the capability projection.

### First zeros exposed

- `proposed -> supported_bounded` transition bypasses the capability admission gates;
- recurrence is accepted as an unverified integer rather than distinct eligible episodes;
- attestation independence is self-declared and not checked against relationship or subject;
- projection does not dynamically re-evaluate stale or revoked evidence;
- transfer-context relevance is not bound to evidence scope;
- capability assertion scope is not required to align with attestation/evidence scope;
- independent-assessment references are unbound strings;
- projection trusts previously supported state without replaying current evidence and authority conditions.

## Required repair coordinates

1. Re-run all noncompensatory admission gates on every transition into `supported_bounded`.
2. Replace scalar recurrence with references to distinct eligible episodes.
3. Bind attestation subject, scope, relationship, independence, and evidence access.
4. Add governed lifecycle records for evidence scopes, attestations, and independent assessments.
5. Re-evaluate all referenced currentness/revocation state at projection time.
6. Bind transfer contexts to distinct evidence-bearing contexts and relevance criteria.
7. Introduce a typed `IndependentAssessment` registry and identity/currentness checks.
8. Preserve exact claim ceilings during transitions and projection.

## Validation

```text
PYTHONPATH=src python scripts/run_f2_w5_b2_independent_redteam.py --output /tmp/result.json
PYTHONPATH=src python -m unittest tests/test_independent_contribution_capability_redteam.py -v

Ran 1 test
OK
```

## Claim boundary

This is an independent controlled-fixture semantic qualification. It does not establish legal authorship, human intent, true mastery, general capability, employment suitability, domain authority, market trust, release, or owner admission.
