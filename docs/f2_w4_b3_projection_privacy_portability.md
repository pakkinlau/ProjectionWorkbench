# F2.W4.B3 Projection Privacy and Portability Hardening

Status: bounded implementation candidate.

## Added surface

`project_semantics.privacy` adds:

- recursive schema-shaped projection allowlists;
- explicit nested redaction and omission receipts;
- immutable content-addressed references and typed mutable-currentness references;
- projection expiry, revocation, and tombstone transitions;
- deterministic export manifests and clean-room import receipts;
- path traversal, symlink, digest, file-count, total-size, JSON-depth, node-count,
  and string-size checks for untrusted local imports.

## Non-collapse laws

```text
public projection != canonical local history
mutable locator != immutable content identity
projection deletion != private history deletion
successful import != source admission
allowing one object != allowing every nested field
```

## Validation

```bash
PYTHONPATH=src python -m unittest tests/test_privacy_portability.py -v
```

The branch does not establish production security, legal compliance, hosted
coordination readiness, external source truth, or user trust. It supplies a
bounded local privacy/portability membrane and deterministic negative fixtures.
