# R11-A — SQLite migration staging/control-state design amendment

## 1. R11 blocker and amendment scope

[R11](recognition-runtime-security-versioned-lifetime-compatibility-migration-implementation-4e-20-R11.md)
identified a conflict in [R10 section 8](recognition-runtime-security-versioned-lifetime-compatibility-migration-design-4e-20-R10.md):
TEMP staging initializes SQLite's connection-local TEMP database, which survives
dropping the staging table. Mandatory control validation then rejects the connection.

This amendment replaces only the staging mechanism and clarifies its validation
boundaries. All other R10 requirements remain: immutable original v1 rows and
120-second meaning, closed prospective v2/300-second representation, v1 default,
credential clipping, exact schema/history verification, one upgrade audit,
transactional rollback, unchanged generation and no target writes. This is design
only; no migration or v2 activation is performed or implemented here.

## 2. Actual administrative-control rule

Source: [administration_schema.py](../src/review/recognition/administration_schema.py),
`check_control()`.

The validator first compares the complete current main-schema object names and
normalized SQL against the exact expected packages. Extra objects fail with
`administration_schema_mismatch`. It then requires
`len(conn.execute('PRAGMA database_list').fetchall()) == 1`, otherwise raising
`isolated_admin_control_required`. It subsequently validates extension rows.

The isolation check counts database-list entries, not active TEMP objects. It
does not distinguish an empty TEMP schema from one containing a table. It is not
an explicit test for the word `temp`; the observed TEMP attachment violates the
one-database condition. Arbitrary attached databases also violate that condition.
These are SQLite-specific catalog/connection semantics.

[administration.connect()](../src/review/recognition/administration.py) opens one
explicit existing control file, enables foreign keys, rolls back an outstanding
transaction on exit and closes the connection. Existing migration owners use
explicit transactions/savepoints and execute individual DDL statements. The
authority migration validates control before mutation and after installing its
package/audit, before committing while the query-only target reservation is held.

## 3. TEMP-schema interaction

R11's in-memory observations establish that creating TEMP initializes a second
database-list entry. Dropping its final object, rolling back a savepoint or rolling
back the full transaction does not remove that entry; detaching TEMP fails.
Moving the final check later on the same connection therefore cannot resolve it.

The existing authority migration already accounts for another TEMP initializer:
its comment explains why integrity checks that may initialize TEMP use separate
preflight/committed read-only connections. That pattern does not permit substituting
a separate reader for final validation of an uncommitted successor transaction.
Keep potentially TEMP-initializing integrity work off the reserved manager
connection, as in the existing owner; do not relax its isolation requirement.

## 4. R10 staging trace

R10 selects a transaction-local holding table to retain exact authority columns
while rebuilding the parent under its canonical name. This avoids renaming the
parent and accidentally rewriting incoming foreign keys. It does not require TEMP
for authority or authentication; TEMP was a proposed row-preservation mechanism.

R10's ordering is control `BEGIN IMMEDIATE`, target reservation/query-only,
complete prerequisite checks, savepoint, deferred NO ACTION foreign keys, staging,
parent rebuild/copy, guard restoration, staging removal, schema/row verification,
upgrade audit and final validation, control commit, then target release. The
original design placed staging creation at step 3 and removal at step 6.
Historical manifests must describe stable predecessor/successor packages, never
the transient staging/rebuild state.

## 5. Candidate amendments

| Candidate | Assessment |
| --- | --- |
| A — Main-schema staging inside the controlled transaction | Selected. Uses the same CREATE/INSERT/DROP, transaction and savepoint mechanisms already used by repository migrations. Removal restores the exact main object set without initializing TEMP. |
| B — Existing non-TEMP staging helper | No dedicated reusable row-staging helper is established by the inspected migration owners. Do not invent or claim one. |
| C — Ordering change alone | Insufficient for TEMP: the attachment survives cleanup. Stable-boundary validation ordering is required with A, but does not replace it. |
| D — Close/reopen or another connection | Reopening loses transaction/reservation continuity. A separate reader cannot verify uncommitted successor state. In-memory application snapshots would be a different preservation design, not needed here. |
| E — No safe amendment | Not selected: A satisfies the observed isolation and transactional-DDL requirements, subject to implementation tests. |

## 6. Selected amendment: transaction-scoped main staging

Replace R10's TEMP holding table with a regular table explicitly qualified in
`main`. Its storage class is persistent, but its lifetime is confined to this one
uncommitted migration transaction. It must never appear in a committed schema.
Use the fixed migration-only name
`recognition_authority_lifetime_upgrade_staging`; no caller supplies a name or SQL.

The implementation contract is:

1. On the original reserved connection, validate the exact old package, complete
   graph, binding, prerequisites and audit head before mutation. Capture D0 and
   protected rows. Any pre-existing staging object rejects; do not adopt or delete it.
2. Under R10's savepoint and unchanged target reservation, create the main staging
   table using explicit authority columns/types and copy exact stored values.
   Include no authority-issuing guards, outgoing FKs, lifecycle hooks or public
   insertion interface on staging. Independently compare its complete row values
   against the validated original snapshot before dropping the original parent.
3. Perform R10's same-name parent rebuild, deferred foreign-key checks and exact
   restoration of dependent guards/indexes. Copy explicit columns back without
   parsing/reserializing JSON, changing IDs, timestamps, policy or audit references.
4. Compare all copied values and protected rows, and drop the main staging table
   before producing the successor manifest or running final control validation.
   Confirm its absence and the exact intended successor object set. No manifest
   exclusion or schema-validator allowlist for staging is permitted.
5. At this clean schema boundary compute raw D1, append R10's one typed upgrade
   audit and validate the complete successor schema/history/projections/current
   scope on the same reserved connection. Historical checks requiring the upgrade
   audit run after that audit exists; preceding structural/row checks do not claim
   that the incomplete upgrade is a valid committed package. All original and
   final required checks remain in place.
6. Require clean foreign-key checks, exact preservation, `check_control()` success
   including the unmodified isolation predicate, and R10's final target/scope
   checks before releasing the savepoint and committing control. Keep target
   reserved through control commit. Publish success only after confirmed commit
   and cleanup. Never commit an intermediate state containing staging.

While staging/replacement is in progress the main schema is deliberately not a
valid administrative package. No runtime reader, issuance, authority creation or
callback may consume that intermediate state. The private migration owner alone
performs the bounded statements. A call to `check_control()` at that point must
reject; no flag, bypass, special connection or weakened object check is introduced.

## 7. Transaction, visibility and rollback evidence

Repository evidence is the individual transactional DDL/savepoint pattern in
`administration_schema.install_runtime_extension()`, authority/attempt/transition
migration owners, and rollback-on-close in `administration.connect()`. This amendment
uses those mechanisms rather than a new migration framework. No `executescript`,
implicit DDL commit, ATTACH, TEMP, foreign-key disabling or permission change is allowed.

In-memory SQLite 3.50.4 probes performed for this review:

| Probe | Observed result |
| --- | --- |
| Existing base definitions and actual `check_control()`, before staging | Passed |
| Main staging table present | Actual validator rejected with `TrustError: administration_schema_mismatch` |
| Drop main staging, validate and commit | Exact original object map restored; actual validator passed; database list only `main` |
| Roll back staging savepoint, validate and roll back outer transaction | Same exact map, passing validator and main-only connection |
| Synthetic parent rebuild with populated child references to two parent unique keys | Confirmed commit preserved exact original row bytes and child references; foreign-key check empty; staging absent |
| Injected failure after staging, parent drop, parent recreation, copy, index creation, guard creation or final staging removal | Each savepoint/full rollback restored original schema and exact rows; staging absent; connection remained main-only |

All probe writes were confined to `:memory:` databases. No repository database or
persistent migration was opened/executed. These probes demonstrate connection-local
DDL/rollback behavior, not a disk crash guarantee or a complete authority migration.

Within the transaction, the owner sees the staging DDL immediately. Existing
transaction isolation keeps uncommitted changes from ordinary independent readers;
rollback-journal readers/commit may block and WAL readers may hold older snapshots.
No reader is entitled to use incomplete state. Cross-connection file-backed
visibility, DELETE/WAL interruption and uncertain-commit handling still require
R11-B's focused tests; they were not exercised by these in-memory probes.

## 8. Failure handling and security preservation

| Failure point | Required handling |
| --- | --- |
| Before staging | Reject without mutation; preserve original package. |
| Staging creation/copy/comparison | Roll back complete migration; never continue with a partial copy. |
| Parent drop/replacement/copy | Roll back DDL and rows, preserving original v1 package and incoming references. |
| Constraint, trigger or index creation | Roll back; no incomplete or unguarded package may commit. |
| Schema, history, audit, FK or final control validation | Roll back; no fallback to old interpretation of an incomplete successor. |
| Staging cleanup | Failure prevents commit; roll back, not a best-effort commit with artifacts. |
| Connection closes before commit | Existing owner rolls back outstanding transaction; reopening is a new read-only inspection, not continuation. |
| Commit/cleanup uncertain | Publish no usable result; no automatic retry, repair, adoption or reverse migration. Inspect durable exact old/successor state. |

Successful commit must contain D1 plus the single migration audit, no staging,
and unchanged original rows. A failed transaction must restore D0 without staging.
Unexpected committed staging is corruption/incomplete state and must fail exact
validation; do not turn it into a supported recovery format. Disk-crash/commit
proof remains an implementation-validation obligation, not a result of this design.

Neither `check_control()` nor `isolated_admin_control_required` may be disabled,
bypassed or weakened. No final validation is moved after commit as a substitute
for precommit validation. Target reservation ordering, current authority checks,
historical v1 interpretation, policy immutability and all R10 production gates remain.

## 9. Decision A and exact next boundary

**A — R11-A AMENDMENT COMPLETE.** Main-schema staging confined to the reserved
transaction resolves the demonstrated TEMP/control conflict using existing
transactional migration mechanisms, without changing administrative isolation.
This authorizes the design only, not execution of a production migration.

**Next boundary: 4e-20-R11-B — amended migration implementation and focused
validation.** That slice must prove the complete R10 preservation, manifest,
rollback, FK, interruption and policy compatibility requirements with this staging
amendment. Do not issue v2, change the v1 default or perform lifecycle measurement here.

## 10. Validation and explicit production blocks

Only this document is added. In-memory probes, AST parsing of inspected migration
surfaces, document whitespace/local-link checks and `git diff --check` were run.
No pytest, lifecycle, Z18, T or broad suite was run. No production Python/schema,
migration, permissions, current/default policy or authority behavior was changed.
No target DML/DDL, G1, v2 issuance/activation, hosted/production access, commit or push.

PRODUCTION AUTHORIZATION: BLOCKED

PRODUCTION EXECUTION: BLOCKED

PRODUCTION ACTIVATION: BLOCKED
