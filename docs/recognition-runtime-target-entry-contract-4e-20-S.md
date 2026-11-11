# Slice 4e-20-S: runtime target-entry metadata contract

**A. APPROVE 4e-20-S — runtime target-entry metadata contract complete**

Design approval only. No INSERT, migration, runtime owner, admission, token,
family mutation, execution, seal, completion, recovery or activation is implemented.
The classification below resolves the metadata-entry question raised by
[4e-20-R](recognition-runtime-writer-phase-contract-4e-20-R.md); it does not
approve the remaining runtime writer prerequisites in
[4e-20](recognition-runtime-writer-admission-contract-4e-20.md).

## 1. What the required INSERT actually is

[4e-17 section 4](recognition-runtime-live-attempt-storage-writer-contract-4e-17.md)
names **target `recognition_runtime_execution_entries`**. That table is a
proposed contract, not an existing implementation. Its required operation is one
immutable entry INSERT followed by an independent target commit before a control
WRITER_ADMITTED decision. Its primary classification is **reservation/entry
marker**, stored as immutable execution metadata. It records that one exact
attempt entered this target's runtime protocol; it does not assert execution.

The marker reserves operation/authority/manifest identity in the target store,
including across an independent control restore. It is not a permanent SQLite
lock and does not reserve a physical connection across commits. It carries
identifiers, digests and historical scope, not candidates, awards, witnesses,
review reassignment, claim winners or family outcomes.

Actual family mutation is the fixed SQL in `permanent.finalize`: private rule
and operation insertion, First Look claim insertion, or Geography scope,
snapshot, member, award and witness insertion. `_prepare` regenerates that work;
`_verify_operation_records` verifies it. None of these is called to apply family
effects by the metadata phase. The metadata producer must not call `finalize`,
acquire its lease, or insert legacy claims/EXECUTING.

```text
metadata INSERT != business/family mutation
target-entry commit != family-effect commit != execution completion
metadata-entry authority != family-writer authority
```

The metadata INSERT is nevertheless real target DML requiring write mode and a
target commit. Only the subsequent query-only admission-decision phase can claim
zero target DML. This contract approves that explicit separation at design level;
it does not redefine a target write as read-only.

## 2. Exact target-entry record contract for future migration

Use the 4e-17 table name and seven columns; no new authority table, mutable
status flag or target copy of administrative secrets:

| Column | Type/constraints and meaning |
| --- | --- |
| `attempt_id` | TEXT NOT NULL PRIMARY KEY; canonical UUID of durable runtime attempt. |
| `operation_id` | TEXT NOT NULL UNIQUE; canonical UUID; FK to `recognition_operation_contracts(operation_id)`. |
| `authority_sha256` | TEXT NOT NULL UNIQUE; lowercase 64-hex digest of exact durable runtime authority. No cross-file FK. |
| `writer_manifest_sha256` | TEXT NOT NULL UNIQUE; exact frozen writer-manifest digest, not a writer permission. |
| `entered_at` | INTEGER NOT NULL; UTC seconds in existing `runtime_profile_schema` timestamp range. |
| `body_json` | TEXT NOT NULL; bounded exact canonical object below. |
| `body_sha256` | TEXT NOT NULL UNIQUE; existing `digest(body)`. |

Proposed versioned canonical body has exactly these keys:

```text
format = recognition-runtime-target-entry-v1
state = TARGET_ENTRY_CREATED
attempt_id
attempt_sha256
creation_event_sha256
authority_id
authority_sha256
operation_reference
runtime_target
physical_snapshot
activation
approval
authentication
entered_at_utc
expires_at_utc
```

`operation_reference`, `runtime_target`, `physical_snapshot`, `activation`,
`approval` and `authentication` are exact copies of those existing authority
members, using their current validators and complete nested field sets. Do not
invent reduced target/approval/authentication formats. Their canonical bytes
must match the resolved durable authority. `attempt_sha256` resolves to the
unchanged six-field attempt; `creation_event_sha256` to its genuine nine-field
CREATED event and creation audit. `authority_id`/digest must resolve to the same
authority row referenced by that attempt. The authority digest also binds the
unchanged dependency, emergency-stop, readiness and producer-consent evidence.

The top-level and nested operation IDs/digests, proposal reference, manifest,
target/installation/generation/profile/binding/owner, auth/MFA scope and activation
incarnation/event must agree in every representation. Columns must equal body
values, including `operation_reference.operation_id`, manifest digest and
`entered_at == timestamp(entered_at_utc)`. Never compare only operation/manifest
digest. Target/control physical observations are runtime observations; original
deployment bindings remain unchanged and are not made portable.

Use existing `rules.canonical`/`digest`, strict duplicate-key rejection and exact
serialization equality. Limit serialized bytes to the existing authority
`MAX_BYTES`, not an unbounded JSON blob. Reject extra/missing keys, NULs, malformed
UUID/SHA/path/decimal values, noncanonical UTC, booleans/floats as integers and
noncanonical JSON. Device/inode fields retain existing lossless representations
and validators, never SQLite floating-point/signed-integer coercion.

`expires_at_utc` equals the original authority and attempt expiry. Require
authority issue <= attempt creation <= entry time < original expiry and
nondecreasing current audit/clock observations. No renewed lifetime or caller
time. Recheck fresh time before target commit. Row presence remains historical
after expiry; it is not an expiring row that can be deleted and retried.

Future exact SQL must enforce canonical indexed scalar CHECKs, valid bounded
object JSON, indexed/body equality and fixed format/state, operation FK and all
unique keys. UPDATE/DELETE are prohibited; BEFORE INSERT collision guards must
prohibit OR REPLACE on **each** PK/unique key even with recursive triggers off.
Readers must independently recompute digests, validate full canonical/nested
scope and resolve cross-store relationships under reservations. Exact schema
validation must reject altered/unknown triggers, partial tables and extra
business-writing triggers. A target-only schema cannot verify control FKs;
do not use ATTACH or pretend those relationships are SQLite-enforced.

## 3. Minimal lifecycle and audit linkage

TARGET_ENTRY_CREATED is the derived historical fact of a valid committed target
row, not a new control history edge. Preserve existing ATTEMPT_CREATED genesis
and the 4e-20-R proposed direct WRITER_ADMITTED decision; do not insert a speculative
pending state or broaden the current genesis-only history CHECKs.

```text
ATTEMPT_CREATED       control attempt + creation event/audit
TARGET_ENTRY_CREATED independently verified committed target marker
WRITER_ADMITTED      future separate control decision referencing entry digest
TARGET_MUTATION_STARTED future conservative intent, not proof of effects
TARGET_COMMITTED     future independent committed-effects evidence
COMPLETED            future verified full accounting/projection
```

The entry's creation-event digest links back to existing owner/reason/time audit
provenance without a cross-store FK. A future WRITER_ADMITTED event/audit must
link back to this exact entry body digest and authority/attempt. No target audit
table or extra control TARGET_ENTRY_CREATED event is needed to prove entry:
the target row is the witness. Entry-only completion performs no control DML.
An entry without a later control decision is visible blocking inventory, not
an invisible success to be automatically promoted.

No secret/token, PID, process-local epoch, raw connection identity or future
completion codec is persisted. A row/digest is DATA, never a bearer credential.

## 4. Metadata-only ownership and exact transaction order

Current coordinator `_phase`/`_finish` forbids target changes and `_evaluate`
rejects preexisting attempts except its own pending creation graph. Do not
toggle query_only through it or impersonate 3a. A separately reviewed private
post-creation metadata owner is required, tied to the genuine original live
coordinator/continuation/CreatedAttempt registration and its original deadline.

The manager owns both connections, authorizers, all BEGIN/COMMIT/ROLLBACK and
cleanup. Callers supply no SQL, path, connection, replacement attempt/scope,
callback or transaction operation. There is no general metadata-write token or
public capability. The only authorized target write is one bound entry INSERT.
The authorizer must reject all UPDATE/DELETE/DDL/ATTACH and all INSERTs to other
tables, including trigger-induced writes. No family writer exists in this phase.

Required ordering for that future owner:

1. Confirm original coordinator lifetime/PID/exact thread and registration.
   Acquire control BEGIN IMMEDIATE, validate exact schema/manifest/history/audit,
   immutable attempt/authority and no competing/incomplete inventory.
2. Acquire target BEGIN IMMEDIATE, set query_only ON. Validate current auth,
   profile/physical/schema/owner/epochs, proposal/ACK/approval/dependencies,
   protected readiness, exact activated incarnation/stop head and all original
   deadlines. Validate target operation graph and absence of entry/outcomes.
3. Build the exact entry only from those resolved records and actual observations.
   Manager changes query_only OFF solely for the fixed entry statement. Advance
   target epoch and invalidate every borrowed read view/cached statement scope.
   Verify post-transition connection, transaction and epoch, physical/schema,
   fresh time, activation/stop and complete current scope with a separately
   registered metadata-phase validation interface. No caller code or reservation
   release occurs between final validation and INSERT.
4. INSERT exactly one entry, validate body/index/relationships, quick/integrity
   and FK checks, exactly one target row change and no other target-table change.
   Recheck unchanged authoritative scope and fresh deadlines before commit.
   Metadata phase cannot excuse an unrelated change as its own write.
5. Commit target with control still reserved. A raised/unconfirmed commit or
   failed cleanup produces no success result and no automatic repeat.
6. Restore query_only ON and reacquire target BEGIN IMMEDIATE in manager-owned
   order while control remains held. The old target transaction/epoch is gone.
   Independently read/validate the committed exact entry and scope, schema,
   identity, activation/stop/auth and time. No cached precommit evidence survives.
7. Entry-only owner releases target and rolls back/releases its read-only control
   reservation; no control state was changed. Publish bounded historical DATA
   only after confirmed commit, independent verification and both cleanups.
   A future integrated admission owner may instead keep both reservations for
   its explicit control WRITER_ADMITTED insert/audit and commit control before
   target release. That integration is not implemented or implicitly granted.

The target commit ends the original writer reservation even if the connection
object is reused. Eventual admission binds a **new** epoch/reservation after
reacquisition and full fresh checks, never the old one. The held control lock
serializes conforming coordinators/activation/stop writers; target uniqueness
survives the reservation gap and independent control restoration. No permanent
lock or claim that the target reservation survives COMMIT.

Query-only ON/OFF, transaction release/reacquisition, connection replacement and
cleanup each invalidate relevant views/epochs. Unexpected loss poisons the owner;
no transparent reconnect/resume. Planned changes must have private explicit
stage-aware ownership; widening current read/auth contexts is prohibited.

## 5. Entry evidence received by later writer admission

Only confirmed entry digest plus the complete validated historical body is
evidence. Any process-local result is original-owner/PID/thread/lifetime-bound,
opaque and nonserializable if it is used as a continuation; detached inspection
data cannot recreate it. Later admission must independently resolve the actual
target row, exact control attempt/authority and all current scope under new
ordered reservations. It may not trust a caller's entry body or success flag.

Entry grants no writer lease, arbitrary SQL/target selection, lifecycle method,
execution/completion/readiness/activation or right to retry. Future writer
admission still requires its own durable decision, fresh final validation and
approved narrowly scoped mutation owner/kernel. The metadata owner never calls
`writer_boundary.acquire`, `_local_lease`, `permanent.finalize`, execution or
completion code. Existing legacy authorization paths remain unchanged.

## 6. Idempotency, concurrency and read-only inspection

Idempotency means a stable immutable historical entry, **not** repeatable
authority. PK attempt and unique operation/authority/manifest fences prevent
two logical entries for the same work. Do not UPSERT, ignore a collision, refresh
time or adopt a matching old row. Two separate coordinators/connections serialize
on control/target reservations; one original insertion can succeed. The loser
must inspect/reject, with existing BUSY/LOCKED semantics and no arbitrary retries.

Same-attempt repeat, matching entry from another process, competing attempt or
concurrent admission cannot mint a token or continuation. Stale/expired scope,
changed activation/profile/generation/install/owner/auth/MFA/approval/ACK,
reservation loss or contradictory inventory rejects. An expired historical entry
continues fencing work. No delete/reissue after expiry or rollback.

Read-only inspection opens files mode=ro/query_only, checks exact schemas,
canonical rows, collisions and whole cross-store scope, without enrollment,
key reads, writes or live authority. For authoritative classification require
stable paired observations under the approved reservations; otherwise report
UNCERTAIN, not a jointly atomic snapshot. Historical categories:

| Status | Evidence and allowed consequence |
| --- | --- |
| ABSENT | No row across attempt/operation/authority/manifest collision keys in a verified stable snapshot. Not proof of no past effects after restore; no automatic retry. |
| VALID | Exactly one structurally valid committed entry, exact durable control linkage and unchanged current scope. Historical metadata only, not admission. |
| DUPLICATE | Repeated identical request resolves to that same valid immutable row; reject recreation and return inspection only. More than one colliding row is corruption/CONFLICTING. |
| CONFLICTING | Different body under any collision key, malformed graph/schema, unrelated target/control, missing/contradictory durable linkage. Block. |
| UNCERTAIN | Commit acknowledgement, cleanup, connection or coherent paired-state evidence unavailable; no absence/success inference. Stop for later reviewed inspection/recovery policy. |
| STALE | Structurally valid entry but original expiry or current binding/profile/auth/activation/approval scope no longer qualifies. Retain row, no new authority. |

An uncertain call may later reveal a valid committed entry. That does not restore
its original process continuation or authorize admission/adoption. Current
protocol has no recovery/resumption operation.

## 7. Crash, activation and commit prefixes

No cross-database atomicity is claimed. Target entry commits first. There is no
control entry update to pretend both stores committed together.

| Prefix/failure | Required outcome |
| --- | --- |
| Before INSERT | No new marker. Existing attempt remains; failure is not restart/adoption permission. |
| During INSERT/precommit | Roll back if definitely uncommitted. Termination/connection loss requires independent inspection; never infer outcome from exception alone. |
| Target entry commits; control admission fails/uncertain | Retain orphan entry and attempt. No automatic WRITER_ADMITTED, no writer token, no retry/adoption. |
| Claimed control admission succeeds but metadata commit fails | Not a legal normal prefix: admission must follow confirmed target commit and independent verification. If observed after restore/corruption, block as conflicting/uncertain. |
| Entry-only control cleanup fails | No successful result publication. Target may already contain the marker; inspect, do not repeat. |
| Process restart | No continuation/token survives; historical row remains. No automatic adoption. |
| Activation/stop changes before entry | Reject exact head/incarnation change. No conversion of preactivation authority. |
| Change during uncommitted entry | Conforming updater cannot commit while control reservation held. Fresh final checks/deadlines may forbid target commit; only uncommitted work can be rolled back. |
| Change after entry commit, before admission | Marker remains historical. Fresh admission must reject mismatched incarnation/head, even after stop is cleared. |
| Physical/schema change or reservation/connection loss | Poison/stop, no result or new authority. Do not weaken identity checks, auto-rebind or reinstall schema. |

The commit decision is validated under both reservations; wall time can advance
inside SQLite/OS commit. Expiry does not automatically roll back SQLite, and a
successful marker commit after a checked decision does not extend future
authority. Nothing in this phase can prove target family effects/completion.

## 8. Additive storage/fingerprint/enrollment boundary

The target entry table does not currently exist in source schema definitions.
Legacy operation metadata can provide its operation FK, but legacy claims,
EXECUTING, receipts/seals and family outcomes cannot replace a runtime entry.
`production_receipts.evidence`/`recovery_binding` and `local_execution._seal`
resolve legacy claims; they must not reinterpret this marker.

`enrollment._schema` hashes all non-sqlite_* objects' ordered type/name/table/raw
SQL plus application_id/user_version. Adding this table/indexes/triggers changes
that full hash. `runtime_validation._identity_snapshot` requires actual hash ==
profile hash == binding hash. Physical identity remains actual hostname/resolved
path/device/inode. No hosted schema/path/hash was verified by this review; prior
deployment observations are historical, not current inspection evidence.

The next migration boundary is **inert target-entry storage plus its recognized
control migration/transition guards**, not writer admission or execution:

1. Turn section 2 into exact reviewed SQL/codec definitions and schema tests;
   register the exact additive control manifest chain, read-only entry inventory
   checks and pending-plan fences in every runtime auth/authority/readiness/
   activation admission. No unknown-table acceptance or startup migration.
2. Use 4e-17's explicit `recognition-runtime-target-schema-transition-v1` ceremony:
   local operator/reason/plan UUID, exact G/source binding/profile, reviewed old/
   new full hash/added-definition manifest, verified backups, nonactive ledger,
   strict old deployment identities, no unsettled attempts/claims/recovery.
3. Prepare a unique append-only control plan under control-first/query-only target
   reservations; revoke authentication/step-ups/confirmations and invalidate
   pending approvals nondestructively. Commit control before target release.
   Pending plan machine-fences all authority, not just an operator promise.
4. Under ordered reservations apply only reviewed additive entry DDL, verify
   exact resulting schema/hash/integrity/FKs and unchanged application rows;
   commit target with control held. No entry execution row is created by migration.
5. Reacquire target/query-only and independently verify. Append G+1 binding with
   unchanged deployment physical/install/target/owner identity, new full hash,
   null profile, NOT_ACTIVATED and plan-completion audit. Commit control before
   target release. On uncertainty retain prepared fence; no auto-DDL replay,
   completion, repair, profile reset or enrollment.
6. Explicit transition-aware challenge/actual runtime observation/private-log
   approval and enrollment establish a new profile at G+2. Recognized insertion
   guards must tie this to the unique completed plan and exact old runtime
   physical continuity/new schema hash. Existing initial-only 2c alone is not
   a schema-upgrade/profile-rotation API. No old operation/authority/attempt is
   portable; all later work must be freshly authorized under the new scope.

Exact migration SQL, pending-plan storage/guards and transition-specific
enrollment API require their own implementation review and tests; this defines
their required boundary and does not claim they exist. All additions are
explicit and fail closed. A fresh installation can instead install reviewed
storage before its first binding/profile, without cloning old authority.

Control WRITER_ADMITTED history storage remains a separate prerequisite from
4e-20-R; entry alone creates none. No completion/recovery/seal codec or migration
is approved here. If later seal DDL changes the full target hash, it likewise
requires a reviewed schema/enrollment transition before use; do not install
unreviewed seal storage now or add a fingerprint exemption. Family execution
remains blocked until its own storage/owner/kernel contracts are complete.

## 9. Focused non-executing test contract

Future tests must use the real original runtime lifecycle and disposable files,
with no provider/callback manufacturing authority. Stop at metadata evidence:

- Valid entry: exact seven columns/body/digest/FK/scope/creation-audit linkage;
  exactly one target INSERT and commit, no business/legacy/control-state change,
  no writer/admission/completion/seal/readiness/activation output.
- Every wrong attempt/authority/operation/target/install/generation/profile/
  owner/auth/MFA/activation/proposal/ACK/approval/dependency/readiness/stop field,
  stale/expired/clock-rollback value, physical/schema field and malformed/NUL/
  noncanonical/type value: reject with no new entry/result/authority.
- Duplicate/same attempt/competing work/concurrent separate connections or
  processes: durable uniqueness, one insertion, rejected replay; preserve BUSY/
  LOCKED. Every UPDATE/DELETE/REPLACE collision and trigger side effect denied.
- Wrong PID/thread/outer/lifetime, forged/serialized result, replaced connection,
  reservation loss/epoch mismatch and cached pre-transition reader: poison,
  no INSERT/result/token; no raw SQL/transaction/target selector API.
- Fault before/during INSERT, final checks, target commit before/after actual
  effect, reacquisition, independent verification and control/target cleanup:
  exact verified prefix, no result on uncertainty, no automatic replay/adoption.
- Restart, independent control/target restore, changed activation/schema and
  absent/valid/duplicate/conflicting/uncertain/stale inspection cases: historical
  classification only, no execution inference or continuation restoration.
- DELETE and WAL: control held across target commit/reacquisition; new target
  epoch, fresh validation, no old view reuse. Symmetric populated table snapshots
  and SQL traces prove all target tables except the entry are unchanged; forbid
  `permanent.finalize`, writer lease/acquire, legacy execution and seal calls.
- Separately test future query-only writer-admission decision with an established
  entry fixture: zero target INSERT/UPDATE/DELETE/DDL/COMMIT during **that** phase.
  Never misreport the preceding metadata INSERT as zero DML.
- Exact additive migration/manifest/partial-install/rollback/plan crash prefixes,
  revocation/approval invalidation, Hnew and G+1/G+2 continuity guards, no old-work
  portability or automatic startup repair. No real deployment migration.

These tests authorize no family mutation, execution or completion. Existing
legacy baseline tests write only disposable fixtures and are not new runtime
execution tests.

## 10. Validation and next boundary

Requested attempt-creation/coordinator/legacy-execution baseline:
**123 passed, 70 subtests passed in 4630.59 seconds**. The disposable-only guarded
run used `-B`, `-q`, `-p no:cacheprovider` and `-x` (stop on first failure to avoid
failed-setup contamination). No failure/isolation run was needed. `git diff
--check` and new-document whitespace/final-newline checks passed. These baseline
results do not test a metadata producer; none is implemented in this slice.
Only this document was added; preexisting working changes are preserved. No
full suite or recognition/deployment family, hosted/production access, real
deployment-key reads, commit or push.

The metadata classification and distinct one-row phase are approved as a
contract. Next: target-entry storage/migration and its schema/enrollment guards,
then minimal writer admission only after the remaining owner/lifecycle/extraction
prerequisites are approved. None of those implementations is authorized here.

PRODUCTION AUTHORIZATION: BLOCKED
PRODUCTION EXECUTION: BLOCKED
PRODUCTION ACTIVATION: BLOCKED
