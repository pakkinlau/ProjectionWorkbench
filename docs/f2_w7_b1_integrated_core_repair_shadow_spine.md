# F2.W7.B1 — Integrated core repair and shadow-spine assembly

Status: `INTEGRATION_CANDIDATE` pending independent Wave-7 synthesis, owner review, and merge authority.

## Assembly boundary

This branch assembles the accepted bounded Wave-6 material surfaces over the Wave-5 integrated candidate:

- contribution/evidence/capability repair;
- privacy/portability repair membrane;
- source-ingestion generalization repair;
- append-only event/provenance shadow spine.

It preserves one canonical owner for each public object family:

```text
project_semantics.__init__         canonical v0 compatibility state
project_semantics.contribution     contribution/evidence/capability extension
project_semantics.privacy_v2       versioned privacy and portability repair membrane
project_semantics.source_ingestion source-derived semantic and reentry extension
project_semantics.event_spine      shadow-only event/provenance candidate
```

## Non-collapse and cutover law

```text
integration candidate != owner merge
shadow parity != canonical cutover
current compatibility state != event-derived view
passing local fixtures != production security or human value
```

The event spine remains `shadow_compatible_no_cutover`; the branch does not rewrite canonical local history.

## Validation

The integrated witness replays the inherited contribution red-team, the independent privacy suite, source-ingestion generalization controls, and event-spine parity/no-cutover checks. GitHub Actions runs the full unittest suite and returns the terminal witness plus logs.

## Claim boundary

This branch may establish one coherent current local integration candidate at controlled-fixture ceiling. It does not establish owner admission, canonical event-spine cutover, production privacy/security, general source understanding, human-observed value, market demand, release, or Wave-7 completion.
