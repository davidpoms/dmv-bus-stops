# Slice 4e-20-R: post-creation writer-phase contract review

**B. BLOCK 4e-20-R — concrete runtime writer-phase/schema conflict**

Contract review only. This document introduces no implementation, authority,
schema, migration, target write, enrollment change, completion or recovery.
The [4e-20 review](recognition-runtime-writer-admission-contract-4e-20.md) and
[4e-17 storage contract](recognition-runtime-live-attempt-storage-writer-contract-4e-17.md)
remain the source contracts. Proposed interfaces below require separate approval.

## 1. Decision that cannot be silently resolved

4e-17 section 6 requires an independently committed runtime target entry before
durable control `WRITER_ADMITTED`. That entry requires target INSERT and COMMIT.
4e-20-R requires stopping if target mutation must occur merely to establish
writer admission, and requires zero target DML during admission. The existing
storage cannot supply this entry without a new target write. Calling it metadata
does not make it read-only.

The narrow decision needed is whether a **separate, fixed target-entry metadata
transaction**, with no family effects and no family-writer capability, is allowed
before the query-only admission-decision transaction. If yes, the decision phase
can have zero target DML; the whole entry/admission protocol cannot. If no, the
4e-17 target witness requirement must receive a separately reviewed replacement.
This document neither removes that requirement nor assumes an exception to the
new stop condition. No writer-admission implementation is authorized.

There is a second prerequisite: exact target definitions, typed entry evidence,
and the pending schema-transition/enrollment guards are not implemented. The
current exact-schema readers cannot accept an ad hoc table or a changed profile
fingerprint. A proposed transition is described below, not executed or claimed
compatible with unchanged readers.

## 2. Inspected implementation and extraction boundary

| Source | Enforced contract |
| --- | --- |
| `runtime_execution_coordinator._create_attempt`, `_persist_attempt`, `_publish_attempt` | Original private continuation only; three control inserts, target query-only; result published after confirmed control commit and cleanup. Result is historical data. |
| Coordinator `_evaluate`, `_phase`, `_finish` | Existing attempts block ordinary phases; only its exact pending creation graph is accepted during creation. Control-first reservation, target query-only, final checks and control commit before target release. No post-creation writer phase. |
| `runtime_execution_attempt_schema.validate_created`, `definitions`, `check_rows`, `inspect_attempt` | Six-field immutable attempt and nine-field sequence-1 CREATED event. History CHECKs/triggers/readers accept no later state. Inspection grants no authority. |
| `writer_boundary._local_lease`, `verify_local`, `acquire` | Genuine legacy claim, protected final-verification tuple, latest legacy EXECUTING, exact connection/manifest/target and no seal. Production additionally requires its existing context, approval and activation checks. Disposable lease is separately fenced. |
| `permanent._writer_connection`, `finalize` | Authorization and connection/transaction ownership surround a block of concrete fixed-family SQL. No existing standalone runtime apply kernel. |
| `local_execution.execute_approved_operation` | Commits legacy claim/EXECUTING, reacquires target, performs final verification, leases writer, commits family effects and legacy seal, projects control state. Not a runtime adapter. |
| `execution_schema`, `production_receipts.evidence`, `recovery_binding`, `local_execution._seal` | Existing target seals/receipts/history resolve legacy claims. Runtime attempts cannot be inserted into or interpreted through them. |
| `authorization.target_identity`, `administration.observe_target`, `enrollment._schema` | Actual hostname/resolved path/device/inode and full target schema fingerprint; no runtime-table exclusion. |
| `runtime_validation._identity_snapshot`, `runtime_enrollment.enroll_runtime_profile` | Profile/binding/actual schema equality; installation/target/owner and auth epoch. Enrollment is initial-only from null profile, with strict deployment observations and generation + 1. |
| `administration_schema.check_control`, attempt/authority manifest readers | Exact recognized complete schema and recognized migration chain; partial/unknown extensions fail. |
| `local_readiness.require_activated`, activated-owner/authority checks | Exact current ledger/ceremony and incarnation scope, not a state boolean. Stop and protected readiness are independently rechecked. |

The lowest-level family mutation is the SQL inside `permanent.finalize`, not its
public call boundary: `recognition_private_rules`, `recognition_private_operations`,
then either `recognition_first_look_claims`, or geography scope identities,
snapshots, members, awards and witnesses. `_prepare` is read-only regeneration;
`_verify_operation_records` checks outcomes. Neither performs the family writes.

The smallest proposed extraction is one private, connection-bound checked apply
kernel containing the following existing sequence without semantic changes:

1. Exact private schema/manifest/reference/digest validation and existing-outcome
   verification before the current legacy idempotent return.
2. `_prepare` under the held writer reservation and equality of the entire
   frozen manifest, including competitors, identities, members and candidates.
3. Existing exact rule checks, timestamp check, fixed INSERTs and all existing
   First Look conflict/Geography catch-up rules. No per-item quarantine.
4. `_verify_operation_records` and `PRAGMA foreign_key_check`; bounded accounting
   result only. No transaction management, connection acquisition or schema DDL.

The legacy wrapper must retain `gate`, `production_guard`, capture prohibition,
authorization/reference checks, `verify`/`verify_local` before and inside the
reservation and after effects, original lease consumption, existing idempotent
behavior and optional commit ownership. Extraction is not permission to remove
apparently duplicate legacy verification. A later runtime adapter must reject
preexisting outcomes rather than adopt the legacy idempotent result.

Runtime admission owns current credentials, exact approval/ACK/dependencies,
activation/stop/readiness, authority/attempt and physical/profile scope. The
shared kernel owns fixed-family data correctness. The legacy wrapper owns legacy
authorization and legacy transaction behavior. No runtime call to `finalize`,
synthetic claim, EXECUTING insertion or new accepted legacy lease type is allowed.
Extraction appears possible as a separately tested refactor; it does not exist
today and is not implemented here.

## 3. Minimal post-creation lifecycle

Choose the direct **WRITER_ADMITTED** decision, not a speculative
WRITER_ADMISSION_PENDING state. The immutable attempt already fences work; the
separate target entry, if approved, provides the independent target witness.
Any uncertain prefix blocks progress without requiring an invented pending state.

```text
ATTEMPT_CREATED
  -> separately established committed target entry [unresolved permission]
  -> WRITER_ADMITTED [historical durable decision, not a token]
  -> TARGET_MUTATION_STARTED [conservative durable intent, not proof of DML]
  -> STOP at this contract's boundary
```

TARGET_COMMITTED and COMPLETED are different later facts, not aliases for any
of these states. Their codecs/producers/storage are not defined here. In
particular, target commit requires independent exact target evidence; completion
requires verified full effects and an explicit later projection contract.

The new phase must belong to the original live coordinator and original genuine
CreatedAttempt registration. Historical inspection, JSON, public issuance,
another coordinator, another session, restart or a lookup result cannot open it.
Do not widen the current `_phase` or masquerade as a 3a/activated read owner.
A separately reviewed post-creation owner must validate its exact own pending
entry/admission/intent while continuing to reject every conflicting graph.

## 4. Fresh validation and future capability

Before entry, durable admission, mutation intent, token creation and the final
target-commit decision, resolve authoritative state under both reservations:

- Exact immutable attempt/body/digest/creation event/audit, genuine authority,
  unchanged AUTHORIZED genesis/consent and original nonrenewable deadlines.
- Exact operation/reference/digest/full regenerated family manifest and population,
  proposal and ACK, current effective runtime v2 approval and invalidations,
  complete dependency snapshot and current READY results.
- Current genuine primary/session scope, owner/access, auth/MFA epochs and
  expiry/revocation; installation/target/generation/binding/profile.
- Actual target/control hostname/path/device/inode, complete schema hash,
  metadata and exact expected supported schema; unchanged enrollment identity.
- Exact activated ledger incarnation/event/ceremony, protected readiness and
  exact inactive emergency-stop head; no preactivation authority conversion.
- Original active unpoisoned coordinator, PID/thread object and identifier,
  phase, exact connections, transaction/reservation identities and epochs;
  no conflicting attempt, orphan entry, legacy/runtime claim or recovery state.

Wall/monotonic rollback anomalies, expired authority/attempt/credentials/consent
or any mismatch mean no capability. No renewal, reselection, transferred scope,
caller-supplied readiness boolean or cached admission survives a phase change.
Post-effect validation must be stage-aware and check exact expected effects;
regenerating a pre-effect manifest after writing cannot be an exemption flag.

The future token has no public constructor or serialization and only a private
registry entry. Bind it to every scope above, exact entry/admission/intent
digests, exact operation manifest, target connection and active transaction,
reservation epochs and original outer lifetime/deadlines. Bind activation by
incarnation/event digest. No PID is added to durable attempt records.

The only future mutation interface is a fixed family dispatch on that token;
no caller connection, cursor, SQL, query, target path, manifest replacement,
callback, DDL, commit/rollback or lifecycle method. Spend before dispatch,
including failure. No second token, replay, reissue after rollback or import on
restart. Context exit, ownership/epoch loss or uncertain outcome invalidates it.
The manager alone writes lifecycle records and owns all transaction cleanup.

## 5. Reservation and query-only transition

Conditional on the unresolved entry permission and separately approved storage:

1. Original coordinator reserves control, then target with BEGIN IMMEDIATE and
   query_only ON. Perform full fresh checks. Entry is a **separate metadata-only
   write phase**, not the family writer or the zero-DML admission decision.
2. Its manager alone may enable the exact entry INSERT, with a new target epoch
   and invalidation of all borrowed read views. Commit that entry with control
   held. Reacquire target/query-only and independently verify the committed row.
3. Revalidate current scope, append control WRITER_ADMITTED plus audit, commit
   control while target is still reserved; then release. This phase has zero
   target DML/DDL/COMMIT. It publishes no family writer token.
4. A fresh ordered phase records TARGET_MUTATION_STARTED intent on control with
   target query-only/reserved through control commit. Release afterward. The
   intent is deliberately conservative; it proves no target effect.
5. The original live owner reserves control then target again, query-only, and
   validates the exact admission/intent and all current scope. The new mutation
   manager performs its explicit query_only OFF/epoch transition, invalidates
   all old views and validates the post-transition owner/connection/transaction,
   actual identity/schema, activation, stop and fresh time. Only then mint the
   single-use token, without releasing either reservation or invoking user code.

No interval between final post-transition validation and token creation releases
the reservation. The capability binds the new epoch; it never retains a stale
query-only epoch or treats old cached readers as valid. Unexpected epoch change,
reservation/connection loss, other writer or identity/schema change poisons the
owner and forbids publication. Later mutation must keep both reservations through
final checks and target commit. None of these write phases is implemented here.

## 6. Minimum proposed additive control storage

Preserve the immutable attempt and existing CREATED table/event bytes. Prefer a
separate extension, proposed `recognition_runtime_writer_phase_history`, instead
of rewriting existing genesis records. Its exact DDL/manifest migration must be
reviewed before implementation; current readers do not recognize it.

Proposed columns: `attempt_id TEXT NOT NULL`, `sequence INTEGER NOT NULL`,
`state TEXT NOT NULL`, `at INTEGER NOT NULL`, `previous_sha256 TEXT NOT NULL`,
`body_json TEXT NOT NULL`, `body_sha256 TEXT NOT NULL`,
`audit_sequence INTEGER NOT NULL`. PK `(attempt_id,sequence)`, UNIQUE
`(attempt_id,state)`, `body_sha256`, `audit_sequence`; FK attempt ID to immutable
attempt and deferred audit sequence to admin audit. Sequence 2/state
WRITER_ADMITTED and sequence 3/state TARGET_MUTATION_STARTED are the only edges.
Sequence 2 links the original CREATED digest; sequence 3 links sequence 2.
Require strict integer types (no bool/float), canonical UUID/lowercase SHA/UTC,
NUL rejection, bounded canonical JSON, exact indexed/body equality and immutable
UPDATE/DELETE/REPLACE guards for every unique collision key.

Proposed exact canonical body keys:

```text
format = recognition-runtime-writer-phase-event-v1
attempt_id, attempt_sha256, sequence, state, at_utc,
previous_sha256, actor_id, reason, evidence
```

For sequence 2, exact evidence keys:
`authority_id`, `authority_sha256`, `target_entry_sha256`.
For sequence 3, exact evidence keys:
`authority_id`, `authority_sha256`, `target_entry_sha256`,
`writer_admission_sha256`. All are exact durable identifiers/digests; the
authority and target entry must resolve to the complete same operation, manifest,
installation/generation/profile/owner/activation/auth/physical scope. Comparing
only the manifest hash is forbidden. This is a proposed **new** event format;
it neither changes the approved CREATED codec nor defines later evidence codecs.

Actor is the current exact owner; reason is bounded canonical explicit text.
Require original attempt creation <= nondecreasing event time < original expiry,
fresh authoritative UTC under reservations, valid original authority/auth scope
and audit monotonicity. Event digest uses existing `digest(body)`; storage is
exact `canonical(body)`, no duplicate keys/extras/noncanonical representation.

Insert event and its matching append-only audit atomically on control. Proposed
audit actions are `runtime_writer_admitted` and `runtime_target_mutation_started`;
exact subject: `attempt_id`, `attempt_sha256`, `event_sequence`, `event_sha256`.
Audit actor/time must match event; triggers/deferred relationships and row readers
must prohibit a committed half graph. Original authority/attempt are unchanged.
All cross-table relationships must be checked before commit and on later reads.
Cross-file entry linkage requires independent target validation, not a fake FK.

No invalidation deletes/rewrites these facts. Later revocation, generation/profile,
activation or stop changes prevent further use. One event per state/attempt and
existing unique authority/operation/manifest fences give a single winner under
control-first DB reservations, not process locks. No new attempt after failure
or uncertainty. A missing token is not permission to repeat a durable admission.

This minimal extension does not solve target-commit/completion/recovery storage;
future producers remain blocked until their exact evidence contract exists.

## 7. Target schema and enrollment migration prerequisite

No current hosted schema or physical identity was inspected. The known earlier
deployment hash is historical evidence, not proof of today's schema. Current
authoritative schema identity is computed by `enrollment._schema`: ordered
non-sqlite_* sqlite_master type/name/table/raw SQL plus application_id/user_version.
`target_identity` observes actual hostname/resolved path/st_dev/st_ino; runtime
devices/inodes retain lossless canonical decimal text in profile validation.

The existing legacy claim/seal/receipt schema is insufficient for a runtime
attempt/activation-bound entry and must remain unchanged. 4e-17 selects additive
`recognition_runtime_execution_entries` and `recognition_runtime_execution_seals`.
An entry needs the existing inventory's attempt PK, operation UNIQUE FK, unique
authority/manifest digests, entered time and exact canonical body/digest, with
immutable collision guards. Its typed body and resulting complete DDL/hash still
require a separate target-storage review. Seal codecs/storage are not expanded
in this slice. No target table is added now and no fingerprint exemption is allowed.

The exact next **migration-design boundary**, before any migration execution:

1. Review inert control history definitions above, exact target-entry definitions,
   and the pending-plan/transition-specific enrollment schema/guards together.
   Recognize the complete additive control manifest chain and partial rejection.
2. Require explicit local operator/reason, exact expected G/source binding/profile,
   nonactive ledger, backups, no unsettled attempts/claims/recovery, unchanged
   deployment identities and exact old/new full schema/definition manifests.
3. Commit a durable prepared plan with revocation/approval invalidation and
   machine-enforced denial in every runtime auth/authority/readiness/activation
   admission before any target DDL. These guards do not exist today.
4. Under ordered reservations, install only exact reviewed additive DDL, verify
   complete Hnew/integrity/unchanged application rows, commit target; reacquire
   query-only and independently verify, with control held. No execution entry rows.
5. Append binding G+1 preserving physical observations/installation/target/owner,
   Hnew, null profile and NOT_ACTIVATED, with exact plan-completion audit and
   revocation. Control commit before target release. Retain pending fence on any
   uncertainty; no startup repair, DDL replay or automatic completion.
6. A separately transition-aware challenge/observation/operator enrollment at
   G+2 must require exact old runtime physical continuity and Hnew, linked by
   insertion guards to the unique completed plan. Existing initial-only 2c is
   not a profile-reset/rotation API. No production enrollment change here.

The manifest machinery can represent an explicitly recognized additive
extension; it cannot recognize this safely merely by creating tables. The
pending-plan schema, typed entry and transition-aware guards must first be
reviewed. Until then this prerequisite is unresolved, not an approved migration.
Old frozen operations/approvals/authority/attempts are never portable across
the transition. Fresh authentication/work/consent/activation would be required.

## 8. Activation, crash and uncertainty contract

| Boundary/failure | Required handling |
| --- | --- |
| Validation, entry or admission failure | No token; roll back uncommitted control changes and any uncommitted target transaction. Preserve durable prefixes. |
| Activation/stop change before admission | Reject exact head/incarnation mismatch, even if other fields still match. No preactivation promotion. |
| After admission, before mutation | Historical decision is not current authority. Fresh checks reject changes/expiry; never remint from rows. |
| After mutation starts, before commit | Hold control and target reservations; conforming activation/stop updaters serialize. Failed final checks forbid target commit; manager may roll back only an uncommitted transaction. Expiry does not automatically roll SQLite back. |
| During target commit | Linearization is the fresh checked commit decision under both reservations, not an instantaneous wall-clock guarantee inside OS commit. An exception may be uncertain, not proof of rollback. |
| Target commit success, control uncertainty | Control cannot undo effects. Stop, retain exact evidence/prefix, require independent target inspection by a later reviewed recovery contract. No adoption or retry. |
| Control admission/intent committed, target uncertain | Intent/admission prove no target outcome. Never infer commit, rollback or no effects from missing later lifecycle records. |
| Target reservation/connection loss | Poison owner and invalidate token/views; no transparent reacquisition or continuation. Cleanup failure also prevents publication. |
| Termination before/during mutation, restart | Token disappears; durable prefixes remain. No import, replay, automatic adoption or inference from in-memory state. Unknown target outcome blocks progress. |
| Activation changes after target commit, before recording | Committed historical facts persist. New incarnation cannot inherit writer permission; projection/recovery needs its own reviewed evidence contract. |

No cross-database atomicity, arbitrary SQLite BUSY/LOCKED retries, automatic
recovery or automatic rollback-after-commit. Concurrency on same attempt,
authority, operation or target is fenced by durable unique work inventory and
ordered reservations. Target entry must also fence independently restored control;
absence of a control row is never sufficient proof that no target work occurred.

## 9. Focused non-executing test contract

Later admission tests must invoke the real lifecycle with disposable fixtures,
not a callback that manufactures runtime authority. All tests in the admission
slice stop before family dispatch; target-entry fixture installation, if approved,
is a separately measured setup/metadata phase, not a zero-DML claim for entry.

- Valid genuine CREATED/entry/current scope: one historical admission; no family
  DML, completion, legacy record, readiness grant or activation from admission.
- Every authority/attempt/digest/history, expiry/rollback, activation/profile/
  generation/install/owner/auth/MFA, proposal/ACK/approval/dependency/readiness/
  stop and physical/schema mismatch: no token and no partial event/audit graph.
- Actual reservation loss, epoch mismatch, connection substitution, cross-thread/
  PID/outer/lifetime, restart, forgery/serialization: poison and no capability;
  stale query-only views cannot be reused after a write-mode transition.
- Concurrent/duplicate admission with distinct DB connections/processes: one
  durable event/token at most, immutable original rows, no arbitrary lock retries.
- History UPDATE/DELETE/REPLACE, skipped edge, wrong predecessor/actor/entry/
  authority/audit, timestamp/type/NUL/canonical/extra-key failures: fail closed.
- Faults before/after each event/audit insert, final validation, commit and
  cleanup: exact rollback or known/uncertain durable prefix; never retry/adopt.
- Admission decision under DELETE and WAL: query-only held through control
  commit, zero target INSERT/UPDATE/DELETE/DDL/COMMIT; symmetric logical dumps
  and populated legacy/protected snapshots unchanged. No synthetic EXECUTING.
- Exact additive migration/manifest validation, partial install and rollback,
  interrupted prepared plan, Hnew mismatch and enrollment continuity: blocked
  until reviewed guards exist, no fingerprint bypass or old-work portability.

Later extraction parity/family-write/commit/seal tests require a separate slice;
they are not new tests or execution authorized by this contract review.

## 10. Validation and disposition

The requested attempt-creation/coordinator/legacy-execution baseline passed:
**123 passed, 70 subtests passed in 4742.69 seconds**. It used the guarded
disposable-only environment, `-B`, `-q`, `-p no:cacheprovider` and `-x` (stop on
first failure to avoid failed-setup contamination). No failure/isolation run was
needed. `git diff --check` and the new document's whitespace/final-newline checks
passed. No full suite or recognition/deployment family was run for this slice.
Only this document was added; existing dirty work is preserved. No hosted or
production resources or real deployment keys were accessed. Existing execution
baseline tests use disposable fixtures; no new runtime mutation test was added.

Blocked pending the explicit target-entry permission decision and the exact
storage/schema/enrollment prerequisite review. No implementation around these
conflicts. No commit or push.

PRODUCTION AUTHORIZATION: BLOCKED
PRODUCTION EXECUTION: BLOCKED
PRODUCTION ACTIVATION: BLOCKED
