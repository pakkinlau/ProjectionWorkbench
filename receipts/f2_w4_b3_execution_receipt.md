# F2.W4.B3 Execution Receipt

```yaml
branch: F2.W4.B3
terminal_object: ProjectionPrivacyPortabilityHardeningWitness.v1
local_validation: PASS
unit_tests: 7/7
repository_base: pakkinlau/ProjectionWorkbench@e52bd80249e89741998ddf4faea974082acf629a
claim_ceiling: bounded local privacy and portability membrane only
```

## Local validation

```text
test_composite_true_allow_is_rejected ... ok
test_export_import_clean_room_round_trip ... ok
test_external_reference_modes_are_explicit ... ok
test_malicious_depth_is_rejected ... ok
test_projection_revocation_and_tombstone_do_not_mutate_source ... ok
test_recursive_allowlist_blocks_nested_private_fields ... ok
test_tampered_bundle_fails_closed ... ok

Ran 7 tests
OK
```

## Material hashes

```text
privacy.py: 9c4b3f47ff0c0a81ce372b70df173676f0ec84dbfa7160e177411319febac1b6
test_privacy_portability.py: 78328a5c4875be3774b33a0a605b0ab0cae168e25c5de6fc5d65db9a67033e71
documentation: c129a088b8333c0a4e7a94e44979ca2e628b5bfedbbb174805ea80ecf86a4864
```

This receipt does not establish production security, legal compliance, hosted
coordination readiness, external source truth, or owner acceptance.
