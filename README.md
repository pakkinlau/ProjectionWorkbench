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

## Canonical surfaces

- `src/project_semantics/`: neutral local kernel.
- `fixtures/first_witness/`: deterministic positive and negative witness.
- `docs/f2_first_witness_boundary.md`: current boundary and nonclaims.
- `registry/manifest.yaml`: current repository role and schema surface.
- `receipts/f2_w2_k1_execution_receipt.md`: branch-local execution receipt.

`Cast My Spells`, `Spell`, `Cast`, `Plate`, and `Bolt` remain optional product
vocabulary. They are not canonical root types in this package.
