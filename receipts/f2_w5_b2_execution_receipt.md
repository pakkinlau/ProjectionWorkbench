# F2.W5.B2 Execution Receipt

```yaml
branch_id: F2.W5.B2
terminal_object: IndependentContributionCapabilityQualification.v1
terminal_disposition: REPAIR_REQUIRED
source_repository: pakkinlau/ProjectionWorkbench
source_commit: 3240553dcc4358c2609e95aa002d7b89c9eba61b
case_count: 12
policy_matches: 4
false_accepts: 8
false_rejects: 0
deterministic_replay: PASS
unit_test: PASS
accepted_state_mutation: false
release_effect: none
```

The red-team found eight independent false-accept paths and no false rejects. The strongest first zero is the `proposed -> supported_bounded` transition bypass, which can create a projected capability assertion without contribution, evidence-scope, attestation, recurrence, transfer, or independent-assessment admission.

Exact reentry: repair only the affected contribution/evidence/capability coordinates, then rerun this independent suite unchanged.

Claim ceiling: controlled local semantic qualification only.
