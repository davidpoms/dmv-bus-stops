# 4e-20-R10: versioned lifetime compatibility migration design

## 1. R9 blocker and design decision

[R9](recognition-runtime-security-versioned-lifetime-policy-implementation-4e-20-R9.md)
stopped because current authority SQL and historical schema validation cannot admit
v2 through a code-only change. This document designs the explicit control-store
compatibility transition; it executes nothing.

**A - MIGRATION DESIGN COMPLETE.** Use a closed two-policy definition, the existing
immutable `lifetime_policy` body field, a transactional rebuild of the authority
table preserving every original row, and one audited schema transition with exact
inverse historical projection. No mutable policy catalog or default change is
needed. The next boundary is R11 implementation and focused validation, not a
production migration, v2 issuance, G1 implementation or lifecycle measurement.

## 2. Inspected existing objects and dependencies

Source names below are under `src/review/recognition/`.

| Existing surface | Current contract / required treatment |
| --- | --- |
| `runtime_activation_authority_schema.AUTHORITIES` | `recognition_runtime_execution_authorities`; immutable original authority and body digest |
| `.LIFECYCLE` | `recognition_runtime_execution_lifecycle`; exact one AUTHORIZED genesis per authority, unchanged three-field genesis evidence |
| Authority table constraints | PK authority ID; unique operation ID, private manifest digest, confirmation digest, body digest, audit sequence; exact existing FKs preserved |
| Authority FKs | Generation -> admin binding; profile -> runtime profile; activation -> activation ledger; approval -> approvals; confirmation -> admin confirmations; deferred audit sequence -> admin audit |
| Incoming FKs | Lifecycle authority ID; `recognition_runtime_execution_attempts` authority ID and authority body digest. No cascade action is specified; preserve these NO ACTION relationships |
| Indexes | Authority `_scope_idx` on install/target/generation/profile/activation; lifecycle `_state_idx` on state/authority. Preserve exact columns and uniqueness |
| Triggers | Immutable UPDATE/DELETE/collision INSERT/REPLACE on authorities/lifecycle; authority scope, lifecycle sequence and authority audit guards. Attempt scope/history/audit guards also reference authority data |
| Issuer `_body()` | Original `min(issue+120, original step/confirmation/primary/session expiries)`, v1 default |
| Canonical/historical readers | Exact policy ID, <=120 bound and original min reconstruction; cannot resolve history using today's default |
| `administration_schema.check_control()` | Exact object-name/SQL equality, schema/row/FK validation; must distinguish original and upgraded authority packages |
| Authority/attempt/transition migration readers | Exact historical schema projections and ordered predecessor audit digests; cannot overwrite old expected manifests |

Read existing `definitions()`, `validate_authority()`, `_historical_scope()`,
`check_manifest_transition()`, `check_rows()` and `migrate()` in the authority
module; `authority_manifest()` and attempt definitions; transition
`historical_manifest()`; claims `manifest()`/historical readers; existing exact-
schema, immutability, rollback, populated-history and concurrent migration tests.
No database was opened or SQLite statement executed for this design.

## 3. Current numeric enforcement

Database: authority issue range uses `MAX_TIME-120`, table CHECK limits expiry to
issue+120, and the scope trigger fixes v1 policy. Canonical validator duplicates
the policy/range/ceiling rules. Issuer chooses the clipped interval. Historical
reader requires exact original min formula and resolves original consent/credential
evidence. Attempt/entry/witness readers inherit original authority deadline.
Test fixtures assert 120 and schema tests assert exact installed definitions.

These are distinct enforcement layers; changing only a Python constant, fixture
assertion or expected SQL is not a migration. Original schema definitions must
remain available as immutable historical definitions after implementation.

## 4. Target model: closed immutable policies

| Exact policy ID | Immutable ceiling | Selection |
| --- | ---: | --- |
| `recognition-runtime-authority-lifetime-120s-v1` | 120 | Existing default, unchanged |
| `recognition-runtime-authority-lifetime-300s-v2` | 300 | Explicit prospective supported selection only, never automatic default |

These are the only supported values in the proposed successor package. The second
ID is a proposed design constant, not an accepted runtime value yet. No numeric
caller override, mutable lookup table, policy row UPDATE or environment setting.
Body `lifetime_policy` already participates in the authority digest, so no new
policy column is necessary. Fixed SQL cases enforce the two exact meanings.

Actual expiry remains `min(issue + policy ceiling, original primary, session,
step and confirmation expiry)`. Keep canonical integers/UTC and strict boundary
checks. New overflow guard is policy-specific: issue <= MAX_TIME minus that
policy's ceiling. No earlier consent/credential deadline is extended.

## 5. Existing-row preservation and prospective fence

Before copying, validate the entire existing exact package/graph. Every original
authority must be valid v1; unknown/malformed/already-v2 rows fail migration.
Snapshot all columns/values, including exact JSON bytes, IDs, digest, issue/expiry,
audit sequence, profile/activation and confirmation reference. Copy without any
body parsing/reserialization or timestamp/policy change. Lifecycle, attempts,
consent, approval, activation, bindings and all old audits remain byte-identical.

The new migration audit is the schema-support cutover, not policy adoption.
Existing v1 rows remain v1 forever. A future v2 must have original source issue
audit and original source consent artifacts strictly after that cutover in audit
order, and issue time no earlier than cutover time. Historical validation must
resolve those facts. Old consent/source records cannot be reused to introduce
v2 retrospectively. v1 may still be issued after migration under its old meaning.

Migration installs representation only. It activates neither v2 nor a producer;
any later issuance selection must be explicitly authorized and recorded, keep
v1 default and use the existing complete protected source ceremony. This design
does not create an automatic policy-adoption mechanism or G1 entitlement.

## 6. Exact database enforcement changes

Keep all authority columns, keys/FKs and existing unrelated guards unchanged.
Replace only policy-dependent predicates. Let P be
`json_extract(body_json,'$.lifetime_policy')`; in the trigger use NEW.body_json.
The table lifetime CHECK must be fail-closed with explicit COALESCE, because
SQLite CHECK permits NULL results:

```text
CHECK(COALESCE(
  typeof(issued_at)='integer' AND typeof(expires_at)='integer'
  AND issued_at < expires_at
  AND (
    (P='recognition-runtime-authority-lifetime-120s-v1'
     AND issued_at <= MAX_TIME-120 AND expires_at <= issued_at+120)
    OR
    (P='recognition-runtime-authority-lifetime-300s-v2'
     AND issued_at <= MAX_TIME-300 AND expires_at <= issued_at+300)
  ), 0))
```

This is a design expression: MAX_TIME is the existing exact integer bound, and
P is expanded into its JSON expression, not a new SQL variable/function. Preserve
existing body JSON/NUL/size/canonical checks and nonnegative integer column ranges.
No float conversion is introduced. Missing/null/unknown policy rejects.

The authority scope guard must replace its v1-only equality with the same closed
policy cases, preserving **every other** actual scope/authentication/activation/
approval/confirmation/physical/stop predicate. For v2 add the original migration
cutover relationship: exact known upgrade audit exists once, consumed confirmation
and its original protected consent audit occur after it, issuance audit sequence
is later and issue time is not earlier. Resolve full cryptographic/history
relationships in the authoritative Python reader as existing SQL does not hash
canonical JSON. Do not claim SQL alone authenticates an arbitrary DB administrator.

Direct INSERT of a v2-looking body must still fail without the existing full
current scope, consumed exact original confirmation and atomic authority/genesis/
issuance-audit group, plus the cutover condition. UPDATE/DELETE/REPLACE protection
prevents changing any authority's policy after issuance. No general direct-write
permission is created. The threat boundary continues to trust host/DB administrators
and protected deployed code; this is not tamper-proof against arbitrary privileged
rewriting of SQLite files.

No policy table means no mutable policy values or referenced policy rows to delete.
The immutable supported enum/code/DDL defines meaning. Removing old support while
old rows remain would fail exact schema/history compatibility and is not permitted.

## 7. Application and issuance agreement

One closed immutable resolver maps the two exact IDs to 120/300, rejects unknown/
unavailable/inconsistent resolution, and never consults current default for history.
Canonical validation and `_historical_scope()` use that mapping with exact original
clipping. Preserve v1 exported/default identity for existing callers; no silent
change to tests or production selection.

Future explicit v2 selection must be fixed to the original issuance context before
source persistence, recorded in immutable authority body, and used consistently
by `_body()`, final graph checks and original consent applicability. Reject an
unsupported selection or request that would substitute policy/scope mid-ceremony.
Existing consent/credential handling remains authoritative; no synthetic artifacts
or weakened expiry checks. The old package cannot issue/persist v2: fail closed
until exact installed successor state is verified.

Attempt/entry/witness source validation keeps original expiry equality; no new
phase starts a fresh 300 seconds. Old source/genesis formats and their exact
three-field AUTHORIZED evidence do not gain new fields or lifecycle authority.

## 8. Migration owner, ordering and transactional rebuild

Use a separately explicit trusted-local control migration, consistent with existing
local inert migrations: exact expected generation, operator/reason, deployment
target/control observations, complete old graph/schema validation, integrity/FKs
and NOT_ACTIVATED binding plus independent activation-ledger prerequisite. Do not
silently upgrade on runtime access or change administration transaction semantics.
Control BEGIN IMMEDIATE precedes target BEGIN IMMEDIATE/query-only. Target remains
reserved through control commit; never commit target DML or change target schema.

The authority table CHECK requires a rebuild. Required design sequence:

1. Capture exact preupgrade main-schema object map and protected row baselines;
   verify only known installed extensions and all original v1 data.
2. Establish savepoint and narrowly scoped migration ownership. Keep foreign_keys
   ON; defer NO ACTION FK checks to transaction commit for the known authority
   rebuild using `defer_foreign_keys`. Do not disable CHECKs/FKs globally. Refuse
   unknown/cascading incoming references or triggers instead of assuming safety.
3. Stage exact authority rows in a transaction-local temporary holding table using
   explicit columns/types/values. No changes to original rows/JSON. Record exact
   known trigger/index definitions that depend on the authority table.
4. Remove only affected known triggers/indexes for the rebuild, including referring
   audit/attempt triggers needed to avoid dangling-schema references. Drop the old
   authority table, recreate it under the **same canonical name** with successor
   constraints, then copy staged original rows back under enforced table CHECKs/FKs.
   Do not rename the old parent into a backup name, which could retarget incoming FKs.
5. Recreate all exact unchanged dependent guards/indexes and the successor authority
   scope guard. Copy only the authenticated old snapshot while live insertion
   guards are absent: those guards enforce current original issuance and cannot
   be applied to historical rows whose audit already exists. No externally callable
   insertion permission or arbitrary writes are exposed during this reserved phase.
6. Remove temporary staging objects. Verify exact schema, every original authority
   value and all protected rows, full historical graph, audit prefix and FKs.
   Require no deferred violation and no cascade/unrelated changes. The known
   dependent lifecycle/attempt rows retain their original FKs and row values.
7. Append the one typed upgrade audit, validate successor/projection/current scope
   again and commit control while target reservation remains held. Only confirmed
   commit and cleanup permits publishing a migration result.

The original migration is not repurposed as this upgrade. The above temporary
rebuild ownership exists only in the explicitly authorized migration, not runtime
code. All statements remain in the same transaction/savepoint; do not use helpers
that implicitly commit DDL. R11 must prove actual deferred-FK behavior, rebuild
ordering, DELETE/WAL interruption and rollback with populated incoming references;
failure of those invariants blocks implementation, not permission to disable FKs.

## 9. Schema manifest transition and audit

Proposed upgrade migration identity:
`recognition-runtime-authority-lifetime-policies-v2`.
Proposed audit action: `runtime_authority_lifetime_policy_schema_upgraded`.
Use the existing migration audit envelope and closed subject keys:
`migration_id`, `previous_schema_sha256`, `installed_schema_sha256`,
`installation_id`, `generation`, `reason`. Actor/time/predecessor come from the
existing immutable audit chain. Exactly one confirmed matching upgrade audit is
required; partial/multiple/conflicting versions reject. No old audit is edited.

Let D0 be the exact validated preupgrade main sqlite_master map, D1 the exact
successor map. The audit binds `digest(normalized D0)` and `digest(normalized D1)`
using existing whitespace-normalized manifest rules. No fingerprint algorithm
change. Same object names alone cannot discriminate versions: require exact old
or successor definitions **and** the appropriate complete audit transition.

Before interpreting old migration manifests from D1, independently validate the
upgrade audit/scope/order and exact successor changed objects. Reconstruct D0 by
substituting only those exact known successor authority definitions with their
immutable original definitions. All unrelated objects must remain exact; no
wildcard projection or trusting a stored predecessor digest without verification.
The inverse projection validates history, never supplies live old constraints.

| Reader / historical stage | Required compatibility treatment |
| --- | --- |
| Claims `manifest()` | Raw current digest still describes D1; historical claim path must use verified projected predecessor, not treat D1 as old schema |
| Authority `check_manifest_transition()` / `historical_claim_manifest()` | Preserve original installed S1/claim predecessor audit through verified D0 projection and existing known exclusions |
| Attempt `check_manifest_transition()` / `authority_manifest()` | Reconstruct original S2/S1 relationships from verified D0, preserving existing exact attempt transition and predecessor ordering |
| Enrollment-transition `historical_manifest()` and its consumers | Reconstruct original S3/S2 projection from verified D0; old transition/source-plan schema digests retain original meaning |
| `administration_schema.check_control()` | Select exact old package without upgrade audit, or exact successor with fully verified upgrade audit; reject mixed/partial installations |
| Fresh current schema inventory/manifest checks | Observe actual D1; no historical substitution used to authorize a current write or bypass fresh observations |

Support the old package with/without known attempt/transition extensions, validating
its actual complete predecessor before upgrade. Do not require an extension to be
present by guessing; fail on unknown combinations. Existing records and all historical
schema hashes remain unchanged. In-memory observation reuse remains within its
existing ownership rules and cannot cross the migration as stale inventory.

## 10. Failure, rollback and idempotence

Incompatible rows, unknown policy, partial old schema, unexpected FK/trigger,
wrong generation/identity/state or bad manifest rejects before mutation. Any stage
copy/drop/create/index/trigger/audit/validation failure rolls back the complete
transaction or savepoint: original definitions, all data and audit prefix restored.
No new v2 row or policy activation is a migration side effect.

An interruption before commit must leave original state; confirmed commit leaves
complete D1 and its one audit. Uncertain commit/cleanup publishes no usable success;
read-only inspection distinguishes exact original/successor state. No automatic
retry, schema repair or authority issuance. Recognized complete successor may be
idempotently inspected without another audit. Concurrent local migrations serialize
and the loser revalidates exact state/generation; no duplicate transitions.

Rollback after a failed uncommitted migration is not a downgrade after successful
v2 issuance. No automatic reverse migration is authorized. Old binaries should
fail exact-schema validation on successor state, never silently treat it as v1.
Generation remains unchanged for this control-only inert package upgrade; no
target identity/enrollment or authentication changes are hidden in it. If actual
repository invariants require any such change, R11 must stop rather than invent it.

## 11. Focused implementation test plan (not run)

- Exact old/successor schema recognition; unknown, partial, mixed and audit-only
  extension rejection; all expected trigger/index/FK definitions preserved.
- Populated v1 authorities/genesis/attempts and all auth/approval/binding/audit rows
  byte-identical before/after; unchanged IDs, hashes, deadlines and manifest lineage.
- v1 remains <=120 and exact original clipping; new v2 <=300 and exact clipping;
  unknown/missing/NUL/noncanonical policy, bool/float time and overflow reject.
- UPDATE/DELETE/INSERT OR REPLACE policy/body substitution rejects; valid original
  v1 cannot become v2, expired v1 cannot revive and default changes cannot reinterpret it.
- Direct v2 INSERT without consumed original confirmation/full scope/genesis/audit,
  before cutover, or using pre-cutover consent rejects; test late source audit linkage.
- Clipped v2 credentials/consent at each shortest bound; equality at expiry rejects;
  original source deadlines inherited by attempts/entry/witness and no renewal.
- All historical readers reconstruct original claim/S1/S2/S3 manifests exactly;
  tampered upgrade/predecessor audit, foreign unrelated DDL or stale schema observation
  rejects. Raw current D1 differs without changing original historical hashes.
- Fault at each staging/drop/create/copy/trigger/index/audit/validation boundary;
  savepoint and complete rollback, populated incoming FK behavior, process termination
  in DELETE/WAL, uncertain commit inspection, idempotence and concurrent upgrade.
- No target DML/schema/commit, key-content reads, v2 issuance on migration, default
  promotion, G1/writer/readiness/activation permission or legacy record changes.

## 12. Production boundary and decision A

```text
DESIGN APPROVED != MIGRATION AUTHORIZED != MIGRATION EXECUTED
                   != V2 POLICY ACTIVATED
```

**A - MIGRATION DESIGN COMPLETE.** Existing canonical policy binding and explicit
control migration/manifest patterns support this bounded design. It introduces no
general configurable lifetime or reinterpretation of v1. Required implementation
tests must prove its concrete SQL/rollback behavior; this is not a claim those
tests already passed or that production migration is authorized.

**Next boundary: 4e-20-R11 - migration implementation and focused compatibility
validation.** Do not perform R11, issue v2, activate a policy or measure lifecycle
here. Current production/default policy remains v1/120 seconds. No G1 is required
or implemented by this design, and no target behavior changes.

## 13. Validation and explicit production blocks

Only this document is added. Read-only repository definitions/tests inspection,
document whitespace/local links and `git diff --check`. No Python/schema/validator
changes, SQL execution, migration, authority issuance, database/target writes,
lifecycle test, Z18, T, broad suite, production/hosted resource, deployment key,
permissions, commit or push.

PRODUCTION AUTHORIZATION: BLOCKED

PRODUCTION EXECUTION: BLOCKED

PRODUCTION ACTIVATION: BLOCKED
