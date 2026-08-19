# ProjectionWorkbench

ProjectionWorkbench is the provisional implementation home for the GVA v0.6 F2
**Open Work Semantics Stack** first witness. It preserves the earlier v0.3
projection/compiler-boundary incubation history while adding a small, local-first,
brand-neutral Python kernel.

The kernel helps a person:

1. initialize or link a project without migrating the source of truth;
2. declare a task context and derive a task-relative project lens;
3. record bounded human, AI, tool, joint, disputed, or unresolved contributions;
4. package work modules and typed connectors;
5. compose modules through noncompensatory compatibility gates;
6. emit a composition receipt and a selective portable projection.

## Nonclaims

This repository does not provide a universal project ontology, automatic
authorship truth, one optimal representation, market validation, hosted social
network, scientific admission, or production readiness. A successful local
composition is not evidence of scientific adequacy.

## Quick witness

```bash
python -m project_semantics witness \
  --fixture fixtures/first_witness/bundle.json \
  --workspace /tmp/pws-demo \
  --output /tmp/pws-demo-output
```

Run tests and build local distributions:

```bash
python -m unittest discover -s tests -v
python setup.py sdist bdist_wheel
```

## Repeat-use value-discovery harness

Wave-2 Branch 1 adds a local, dependency-free repeat-use episode and trajectory
harness under `src/repeat_use_harness/`. It implements append-only event capture,
deterministic replay, human-only field non-imputation, comparator/agency controls,
and lawful negative terminals from the completed Wave-1 constitution.

```bash
PYTHONPATH=src python -m repeat_use_harness fixture --output /tmp/ruv-fixture
PYTHONPATH=src python -m unittest discover -s tests -v
```

The fixture's lawful terminal is `RIGHT_CENSORED`. Successful mechanics do not
establish human repeat-use value or authorize product steering.

## Canonical surfaces

- `src/project_semantics/`: neutral local kernel.
- `src/repeat_use_harness/`: repeat-use event/trajectory harness at R0 mechanical ceiling.
- `fixtures/first_witness/`: deterministic positive and negative witness.
- `fixtures/repeat_use/`: deterministic right-censored repeat-use fixture.
- `docs/f2_first_witness_boundary.md`: current boundary and nonclaims.
- `docs/f_ruv_w2_b1_repeat_use_value_harness.md`: Wave-2 harness boundary.
- `registry/manifest.yaml`: current repository role and schema surface.
- `receipts/f2_w2_k1_execution_receipt.md`: branch-local execution receipt.
- `receipts/f_ruv_w2_b1_execution_receipt.md`: repeat-use harness execution receipt.

`Cast My Spells`, `Spell`, `Cast`, `Plate`, and `Bolt` remain optional product
vocabulary. They are not canonical root types in this package.
