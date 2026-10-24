# Execution foundation: writer trace before implementation

Source inspection, not production database inspection. Production provisioning
remains unavailable. The following trace records the pre-Slice-6 boundaries.

| Actual writer | Callers, transactions and mutations |
| --- | --- |
| `permanent.finalize` | `scripts/active/rehearse_private_recognition.py:rehearse` through imported `finalize`, plus explicit tests/fixture helpers. No Flask/job/worker calls it. Owns `BEGIN IMMEDIATE`, all writes, final verification and commit; `schema.connection` rolls back/closes outstanding transactions. Writes private rules/operations, First Look claims, or Geography scope identities/snapshots/members/awards/witnesses. |
| `live_first_looks.seal_pending` | Explicit tests/fixture helpers only; no production dispatcher. Caller-owned transaction, `first_look_seal` savepoint/no commit, writer lock before delivery verification. Writes private rules/operations/First Look claims plus pending delivery attempts/state. Unexpected failures roll back savepoint; delivery-authorized qualification failures can record quarantine after rollback. |
| `permanent.append_discrepancy` | Tests/fixture helpers only. Owns `BEGIN IMMEDIATE`/commit; writes First Look discrepancy, never replaces a claim. Connection helper rolls back on failure. |
| `live_first_looks.enqueue` | Flask review-completion refresh transaction and tests. Caller-owned transaction and enqueue savepoint. Shared completion capture plus pending delivery only; no claim issuance. |
| `live_first_looks.record_retryable_failure` | Tests/fixture helpers only; caller transaction, exact delivery approval, attempts/error update; no claim insertion. |

`permanent._prepare` and First Look/Geography report modules are read-only eligibility
and manifest generation, not writers. `processing.finalize_job`, `qualification`,
`backfill`, and `process_live_recognition.py` are the separate Explorer pathway.
Their authorization, rules, job leases and awards are not repurposed here.

Existing duplicate/integrity constraints: private operation ID is the canonical
manifest digest/PK; First Look claim PK is physical stop, assignment is UNIQUE;
Geography scope has unique dimension/canonical identity, snapshot has UNIQUE scope,
award has UNIQUE reviewer/scope/tier, witness/member pairs are PKs. Immutable
UPDATE/DELETE/REPLACE triggers and foreign keys protect stored evidence. Historical
finalizer replay verifies the stored operation and exact result sets. Live delivery
replay verifies completed delivery/claim; it is not a general execution journal.
Discrepancy IDs are content-derived and replay checks canonical evidence.

Existing private operation manifests, immutable claims, delivery rows and discrepancy
records are audit evidence; they are not the unique Slice 3 execution operation or
an authorization-to-commit receipt. Writers have no remote side effects. The
disposable rehearsal additionally writes its own filesystem copy/receipt and checks
Explorer unchanged; that is separate from target transaction atomicity.

Slice 6 implementation details and validation are documented below after the trace.

## Supported contract and setup

`execution.admit_operation` automatically enters `execute_operation` after admission.
The only supported issuance is the historical First Look/Geography finalizer with
`atomic-historical-v1`. The owner explicitly chose atomic execution and deferred
active quarantine issuance. Quarantine-enabled policies are rejected; no items are
silently skipped. Live delivery issuance and Explorer remain outside this protocol.

Setup is explicit on disposable databases: install the existing private/operation
schemas, install `execution_schema`, install a separate control store, bind exact
target/control/status-checkpoint identities with the existing opaque administrative
approval, then enroll the target. There is no startup migration or fallback DB.
Binding precedes enrollment so the signed schema fingerprint includes the journal.

Registered `SyntheticExecutionContext` pins the operation, signed artifact, immutable
enrollment, exact stores, synthetic trust provider and separate execute/writer
permissions. Admission checks event/dependency READY status, operation/artifact
association, signature/expiry, current enrollment/physical identity, signed fresh
authority status, revocation/sequence floors, policy, accounting, stop and prior
execution. Missing/stale status and temporary dependencies wait; substantive denials
are durably blocked. A valid revoked status advances the checkpoint even when denied.

## Writer boundary and durable state

Production authorization is rejected inside each private mutation entry point,
independently of the ordinary verifier. Production provisioning still rejects.
The coordinator leases a registered, one-use capability pinned to the exact open
connection, target and manifest. `permanent.finalize` uses that caller transaction;
legacy disposable fixture/rehearsal calls retain their existing transaction behavior.
There is no production capability factory or arbitrary execution callback.

Explicit target tables are `recognition_execution_storage`,
`recognition_execution_claims`, `recognition_execution_seals`, and
`recognition_execution_audit`. Separate control tables are
`recognition_execution_stops` and `recognition_execution_blocks`. Immutable triggers,
hashes, unique operation claims and constrained state transitions prevent replacement
or a second execution of the same operation. Store identities are pinned on each
open; selecting a new checkpoint/control file cannot clear a recorded denial.

The seal binds operation, authorization, enrollment, claim, accounting and verified
actual writer evidence. Verification reruns the historical writer verifier. A Slice 3
receipt or terminal flag alone is not proof of commit. Completed replay returns
ALREADY_EXECUTED, even if authority or dependencies later change.

## Transactions and interruption behavior

1. Under the synthetic enrollment lock, acquire the control writer lock and target
   `BEGIN IMMEDIATE`; verify admission while holding the status-checkpoint transaction.
   Commit the target claim, EXECUTING audit and Slice 3 projection, then commit the
   checkpoint and release control. The target claim retains the accepted status floor
   if the independent checkpoint commit is lost.
2. Open a new target `BEGIN IMMEDIATE`, recheck physical identity/dependencies, invoke
   the historical writer with its lease, and commit all writer effects plus the
   evidence seal in the same SQLite transaction.
3. Verify the committed seal and append the terminal receipt/history/audit in a
   separate target transaction. A lost projection is recoverable without issuance.

These are not atomic cross-database transactions. Admission snapshots authority and
stop state at the durable claim; a later stop/revocation does not undo an admitted
operation. SQLite writer locking serializes concurrent claims and owner recovery.

| Interruption | Durable evidence and owner recovery |
| --- | --- |
| A: before claim | No entered execution; fresh admission remains possible. |
| B: after claim | EXECUTING claim, no effects; separate owner recovery fences FAILED. No automatic rerun. |
| C: after mutation before commit | Writer effects and seal roll back together; recovery fences FAILED. |
| D: after commit before finalization | Effects and seal survive; recovery verifies and projects COMPLETED without invoking writer. |
| E: after finalization | Replay verifies evidence and returns ALREADY_EXECUTED. |
| Commit acknowledgement lost | Return RECOVERY_REQUIRED; inspect seal under lock instead of guessing or retrying. |
| Outcomes without a valid seal | PARTIAL/UNKNOWN and RECOVERY_REQUIRED; never invent a successful receipt. |

`reconcile_operation` requires a separate exact owner recovery permission and supports
a recovery-only context after ordinary execution permissions are discarded. It never
calls a writer. Confirmed absent effects become terminal FAILED; retry requires a new
event/operation/authorization. Known rollback is recorded FAILED; uncertain evidence
remains recovery-required. Histories are append-only.

Emergency stop/clear use distinct exact administrative approvals, expected sequence,
reason and append-only control-store records. A stop works even when the target is
missing, denies entry before claim and records WAITING. Clearing does not erase stop
history or permanent failures. An operation already claimed can finish.

## Validation and remaining infrastructure

The focused suite contains 45 tests with independent expectations and 20 subtests:
historical families, accounting, concurrency, all five interruption points, lost
commit/checkpoint acknowledgements, recovery fencing, signature/status/enrollment
failures, immutable journal/store binding, stop/clear, rollback, production bypass
rejection, deferred quarantine policy and unchanged Explorer outcomes. Interruptions
are deterministic exceptions with connection cleanup, not physical host power cuts.

The enrollment lifecycle lock is synthetic and single-process. Real protected trust
and checkpoint storage, restart-durable incarnation/enrollment registry, host/process
fencing, filesystem replacement/restore detection, trusted clock, production owner
identity and production crash testing remain external prerequisites. Local path and
SQLite checks cannot prove those production properties. No production authority,
execution, live issuance, deployment or activation is enabled. Slice 7 contract work
may proceed with these prerequisites explicit; production remains blocked.

Final validation: focused execution suite **45 passed, 20 subtests passed**;
writer/authorization/status/enrollment compatibility run **95 passed, 1 skipped,
85 subtests passed**; full `tests/` pytest run **860 passed, 3 skipped,
900 subtests passed** in 203.85 seconds. The full run installed an audit hook
rejecting socket connections/DNS and SQLite access under `src/database`.
Tracked and new-file whitespace checks produced no whitespace diagnostics.
No packages were installed; no production database, key or authority was used;
no commit, push, deployment or activation was performed.
