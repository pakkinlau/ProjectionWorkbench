# F.RUV.W3R.B5 — Counterfactual Assignment Repair

This branch repairs the prospective assignment and counterfactual-identifiability surface identified by `F.RUV.W3.B5` and accepted by the Wave-3 N3 hold.

## Added typed records

- `ProspectiveBaselineAndAssignmentSchedule.v1`
- `TrajectoryCarryoverAndContaminationLedger.v1`
- `ResetIntegrityReceipt.v1`
- `ComparatorParityReceipt.v1`
- `MissingnessAttritionAndAbandonmentPolicy.v1`
- `CounterfactualAnalysisPlan.v1`
- `ActualExposureAndComplianceReceipt.v1`

## Mechanical qualification law

A counterfactual assignment becomes admissible only after chronology, visibility, condition identity, crossover/period structure, carryover, reset integrity, comparator parity, actual exposure, missingness, repeated-measures analysis, and policy-freeze checks pass.

`NON_IDENTIFIABLE` now precedes `RIGHT_CENSORED`, so contamination cannot be hidden by absent human outcomes. Consent withdrawal and accessibility blockage remain separate non-value terminals. Observational and deterministic assignment modes receive bounded claim downgrades rather than randomized-treatment-effect semantics.

## Validation

The branch includes a 36-scenario deterministic suite corresponding to the prior B5 audit matrix, including crossover, carryover, reset, comparator drift, outcome-dependent attrition, noncompliance, analysis drift, multiplicity, and matched non-overlapping assignment.

## Nonclaims

This repair establishes only typed counterfactual-assignment mechanics and controlled qualification. It does not establish human repeat-use value, retention, accumulated-history benefit, product direction, interpersonal/network value, market demand, release, merge, cutover, or owner admission.
