# 4e-20-R9: versioned authority-lifetime implementation boundary

## 1. R8 baseline and result

[R8](recognition-runtime-security-lifetime-v2-300-second-policy-decision-4e-20-R8.md)
assesses 300 seconds as a defensible prospective v2 ceiling under immutable policy
binding, historical v1 preservation, original credential clipping and unchanged
security gates. It does not prove complete-lifecycle feasibility or activate v2.

**B - VERSIONED LIFETIME POLICY BLOCKED.** A safe persisted v1/v2 implementation
requires an explicit schema/manifest compatibility migration. R9 expressly says
to stop and report that boundary rather than invent such a migration. No partial
policy helper, codec, issuance selector, schema change or migration is implemented.

## 2. Required representation and current v1 compatibility

The minimal future model would resolve the authority's own immutable policy:
existing `recognition-runtime-authority-lifetime-120s-v1` means 120 seconds;
a distinct explicitly supported prospective v2 means 300 seconds. Current default
must remain v1; no caller-selected arbitrary number or environment override.

The canonical body already contains `lifetime_policy` plus original issue/expiry,
covered by the body digest. No new column is assumed necessary to represent
identity. Existing records must keep all original bytes, digests, indexes, source
consent, policy meaning and expiry. Updating an active default must never change
historical interpretation or turn an existing v1 source into v2.

This describes required semantics, not an implemented new accepted policy or
permission to select v2. No real or synthetic v2 authority was issued in R9.

## 3. Effective expiration

For each future supported policy, expiry must be reconstructed as:

```text
min(original issue time + original policy ceiling,
    original primary expiry, original session expiry,
    original producer step expiry, original confirmation expiry)
```

Retain canonical integer UTC, overflow limits, positive finite interval, strict
current-time-before-expiry and clock-anomaly checks. Never refresh credentials,
restamp issue time, extend consent or alter an existing source to obtain the new
ceiling. Attempt/entry scope continues to inherit exact original authority expiry.

## 4. Exact persistence blocker

Inspected code is under `src/review/recognition/`:

| Enforcement point | Why a code-only v2 addition is unsafe/incomplete |
| --- | --- |
| `runtime_activation_authority_schema.definitions()` authority table | Persisted `CHECK(issued_at<expires_at AND expires_at<=issued_at+120)` rejects a genuine longer row regardless of Python policy resolution |
| Same package's authority scope trigger | Requires exact v1 `lifetime_policy`; a distinct v2 body is rejected independently of the interval CHECK |
| Same package's issue-time range | Uses `MAX_TIME-120`; any multiple-ceiling policy needs consistent overflow/range handling |
| `administration_schema.check_control()` | Compares actual SQL objects to exact expected definitions; editing definitions does not upgrade an existing database |
| Authority `check_manifest_transition()` | Verifies exact installed package plus historical migration audit/schema projections; replacing expected SQL silently invalidates original lineage |
| Attempt/enrollment-transition historical manifest readers | Depend on original authority package and predecessor projection; changing expected definitions without an explicit verified successor violates those relationships |
| Existing authority `migrate()` | Installs the inert package when absent; when present, validates and returns idempotent inspection. It is not an existing v1-to-multiple-policy upgrade |

SQL CHECK constraints are part of the installed table definition. Accepting v2
needs an explicitly designed supported schema upgrade or another separately
reviewed persistence representation. Merely modifying `definitions()`, dropping
the guard, disabling CHECK/FKs, using writable schema, changing a Python constant
or rebuilding only new fixtures is not a safe upgrade for existing stores.
No particular replacement table or migration framework is invented here.

## 5. Exact migration boundary to authorize separately

The missing boundary is a **trusted-local, transactional authority-storage policy
upgrade that preserves immutable v1 records and original migration lineage while
explicitly admitting v2**. It must specify before implementation:

- Exact old/new SQL package and a fail-closed installed-version discriminator;
  no reinterpretation of an old audit or wildcard acceptance of altered definitions.
- How the existing table CHECK/trigger is upgraded, preserving authority/genesis
  bytes/digests, uniqueness, deferred audit links, profile/generation/activation/
  approval/confirmation FKs and downstream attempt relationships.
- Explicit predecessor/successor manifest/audit treatment across authority,
  attempt and enrollment-transition readers; no rewriting old migration records.
- Expected-generation/deployment-identity prerequisites, activation-state treatment,
  control-first reservations and target retained through control commit, with
  zero target DML and complete rollback on any failure.
- Transaction/savepoint, idempotence, concurrency, interruption and rollback proof,
  including mixed old/new records and unknown/partial package rejection.
- Prospective issuance selection and policy provenance, default still v1, with
  no operation/credential/authority substitution or broader downstream permission.

R9 does not define a new migration ID, table, audit format, generation transition,
replacement procedure or new permission to fill those missing details. No
production migration is performed or required as part of this blocked assessment.

## 6. Codec/readers and security invariants

After a separately approved storage upgrade, canonical validation, SQL/body/index
guards and historical `_historical_scope()` must resolve exact original policy
instead of a mutable default. The issuer `_body()` must preserve all original
clipping and final validation; any explicit v2 selection must be closed and
non-default. Unknown/unavailable/inconsistent resolution rejects, never falls back
to a larger ceiling. v1 still rejects any interval exceeding its original 120.

No such reader/issuer change is made before persistence is safe. Existing strict
identity, freshness, replay/duplicate/concurrency fences, fail-closed errors,
uncertain-commit behavior and all downstream authorization boundaries remain.
No G1 producer, new producer, enforcer or target/business mutation is introduced.

## 7. Focused tests and production-behavior preservation

**No tests were added or run**, because R9's explicit migration stop condition
was reached before implementation. Reporting focused unit tests as successful
would misrepresent the missing persistence support. There are no v2 test fixtures
or source-policy overrides in this slice.

Required future focused coverage remains v1/v2 resolution, body/index/policy
binding, original credential clipping, strict boundary, unknown/failed resolver,
immutable historical v1 and attempted retroactive substitution. The separately
authorized migration would additionally need its specific integrity/rollback
coverage before any genuine v2 persistence claim.

Read-only inspection, AST parsing of relevant unchanged code, before/after hashes,
document whitespace/local links and `git diff --check` validate this blocked result.
Only this document is added. Existing source/schema/validator/issuer behavior stays
exactly as inspected, default v1/120. No database was opened and no production
configuration, hosted resource or deployment key was accessed.

## 8. Decision B and stop

**B - VERSIONED LIFETIME POLICY BLOCKED:** the persisted authority CHECK and v1-only
trigger cannot admit v2 without a supported schema transition, which must also
preserve exact schema validation and historical migration manifests. Stop here
as R9 requires. R10 is not announced as an authorized next measurement because
versioned persistence/issuance is not implemented.

No production policy adoption, migration, authority issuance, permissions,
G1 implementation, lifecycle run, Z18, T, broad suite, commit or push.

PRODUCTION AUTHORIZATION: BLOCKED

PRODUCTION EXECUTION: BLOCKED

PRODUCTION ACTIVATION: BLOCKED
