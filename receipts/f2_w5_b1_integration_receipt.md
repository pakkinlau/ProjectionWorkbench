# F2.W5.B1 Integration Receipt

```yaml
branch: F2.W5.B1
terminal_object: IntegratedRepairCandidateAndLineageReceipt.v1
base: pakkinlau/ProjectionWorkbench@e52bd80249e89741998ddf4faea974082acf629a
integration_strategy: exact_B1_B2_B3_deltas_plus_B4_extension_migration
local_combined_tests: 12/12 PASS
claim_ceiling: reviewable integration candidate only
```

The receipt records one canonical core plus four non-overlapping extension owners. The B4 replacement patch is preserved as lineage and migrated to an extension to avoid duplicate canonical ownership. Owner merge, release, and external admission remain separate.
