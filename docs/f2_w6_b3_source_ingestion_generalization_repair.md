# F2.W6.B3 — Source-ingestion generalization repair and replay

This branch repairs the exact first zeros returned by the independent Wave-5 source-ingestion assessment.

## Material changes

- source currentness metadata and deterministic precedence;
- content-identity deduplication with alias locators;
- source refresh receipts and stale-state invalidation;
- format-uniform privacy filtering for Markdown/text and JSON;
- heading-ancestry preservation with archived/deprecated/example exclusion from current reentry;
- fail-closed semantic-envelope validation;
- Git porcelain branch/upstream/ahead/behind parsing plus dirty-state capture;
- non-finite JSON rejection;
- currentness-aware source-derived lenses.

## Validation

The integrated Wave-5 candidate harness was replayed with:

```bash
PYTHONPATH=src python -m unittest discover -s tests -v
```

Result: 20/20 tests passed, consisting of three integrated-candidate controls, four inherited source-ingestion controls, and thirteen generalization cases.

## Claim boundary

The branch establishes a bounded source-ingestion repair candidate over the current research/software prototype. It does not establish general document understanding, legal privacy compliance, production security, human usefulness, arbitrary Git history parsing, cross-domain semantic adequacy, release, or owner admission.
