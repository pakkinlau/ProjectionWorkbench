# F.RUV.W3Q.B3 — Integrated clean-room / fresh-agent qualification

This qualification branch implements the current StewardStack `web.branch` route for `F.RUV.W3Q.B3` without modifying the seven repair candidates.

It independently reconstructs `W3RIntegrationRecipe.v1` twice from the exact PR heads frozen by the Wave-3R N3 SteeringDecision, compares the resulting content-addressed trees, runs the integrated repository suite, and executes the installed source/wheel clean-room witness from fresh environments outside the checkout.

The qualifier fails closed on source drift, integration conflict, reconstruction mismatch, ambient dependency, test failure, or source/wheel replay mismatch. A negative or repair disposition is a valid branch completion when the execution itself is current and exact.

## Frozen source coordinates

- StewardStack route source: `a644409f293609ec2e6f0cb230ba0799d455ec1d`
- Current StewardStack main observation: `5713f1fffdea8e56dd6f0242a4c247c7b4ae7659`
- Equal StewardStack source tree: `1b30eec0f7967f8ad24fab6a55bfaea2ddaec719`
- ProjectionWorkbench integration base: `e289a2ff01ee31f2f32e85247a2956a835e3c175`
- Route-launch digest: `a4848d67212416935e25d8f4fc09b3aeee1b62b4c761c5cfd7055eb0e4b26baa`

## Claim boundary

This branch establishes only independent integrated clean-room, deterministic reconstruction, source/wheel installation, fresh-agent rehydration, and R0 mechanical replay evidence. It does not open Wave 4 by itself and does not establish human repeat-use value, retention, product direction, release, merge, cutover, or owner admission.
