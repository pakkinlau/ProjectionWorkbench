# F.RUV.W3R.B3 — Clean-Room Fresh-Agent Repair

This branch closes the exact noncompensatory hold identified by
`F.RUV.W3.B3 — CleanRoomRehydrationQualification.v1`:

- local source installation was not previously observed;
- the installed `pws-ruv` entrypoint was not previously invoked;
- a built wheel was not previously installed and replayed in an isolated environment.

The repair script creates three distinct virtual environments outside the repository:

1. source-install environment;
2. wheel-build environment;
3. wheel-install environment.

Build tools are exactly pinned. Project installation and wheel construction run with
`PIP_NO_INDEX=1`, `--no-deps`, and `--no-build-isolation` after those build tools are
installed. The installed console entrypoint is invoked from a fresh working directory
with `PYTHONPATH` removed, the user site disabled, and pip caches disabled.

Both source and wheel installations must reproduce:

```text
fixture digest: 87e733e018764d38cce55d00082dc614122b9c8a0fcd19bdc6bffa0f04a34d29
replay digest: 33b58812596daac7d3f1e6d7fe1776d3bd28e65426c81ded596b6642bd7c5ab2
causal terminal: RIGHT_CENSORED
human_value_supported: false
```

The two source runs, two wheel runs, and source-versus-wheel fixture trees must be
byte-identical. Prior Wave-3 material is referenced by artifact identity and digest;
no predecessor archive is embedded in this branch.

A passing result establishes clean-room machinery portability at the R0 mechanical
ceiling only. It does not establish human repeat-use value, retention, product
selection, release, merge, cutover, or owner admission.
