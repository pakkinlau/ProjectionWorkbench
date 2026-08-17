# F2.W3.B3 — Interpersonal exchange without a hosted network

This witness uses two independently initialized local process contexts.

Instance A exports only a content-addressed semantic bundle containing a source
pointer, one work-module manifest, one connector manifest, permissions and an
open collaboration seam. Source bytes and A's private project state remain local.

Instance B receives only the exported bundle, creates its own local target module,
performs a typed semantic adaptation and composition, and returns a receipt with:

- source lineage;
- version identity;
- semantic mapping;
- assumption delta;
- attribution;
- outcome;
- compatibility or failure evidence.

A second, deliberately incompatible version case must fail closed. A final A-side
step accepts the returned receipt and records an exact local reentry without
claiming trust, capability, market value or hosted-network necessity.
