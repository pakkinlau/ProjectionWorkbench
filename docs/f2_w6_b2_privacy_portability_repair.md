# F2.W6.B2 Privacy / Portability Repair and Requalification

Status: `PRIVACY_PORTABILITY_REQUALIFIED_AT_CONTROLLED_LOCAL_CEILING`

## Repair boundary

This branch repairs the exact findings returned by the independent Wave-5 privacy/portability red-team over PR #5. It remains a local, dependency-free, brand-neutral implementation and does not authorize hosted coordination.

## Material changes

- public projections expose aggregate omission/redaction counts rather than private schema paths;
- projection identities are derived from public-safe content and recomputed on lifecycle transitions;
- mutable references distinguish local-only unresolved state from exchangeable current state and enforce freshness at use/export/import;
- projection lifecycle transitions are monotone, so revoked and tombstoned states cannot reopen;
- non-active projections export as metadata-only records;
- the full security-relevant manifest is bound into the bundle digest;
- verify/import rejects unmanifested files, symlinks, duplicate or colliding paths, malformed roles, schema confusion, forged projection IDs, stale state, non-finite JSON, and resource-limit violations;
- clean-room import re-verifies copied material and preserves bundle identity.

## Requalification

- inherited PR #5 behavior tests: 7/7 pass;
- independent RT01-RT20 suite: 20/20 pass;
- findings: 0;
- false accepts: 0;
- false rejects: 0;
- branch terminal: `QUALIFIED_AT_CONTROLLED_LOCAL_CEILING`.

## Migration posture

The repaired behavior is introduced as `project_semantics.privacy_v2`; the v1 source remains immutable predecessor evidence. Canonical API cutover is deliberately deferred to a later integration/owner decision.

## Nonclaims

This branch does not establish production security, legal or regulatory compliance, cross-platform archive safety, hosted-network readiness, user trust, release, or owner admission. The Wave-5 negative result remains valid for its pinned predecessor commit and is not rewritten.
