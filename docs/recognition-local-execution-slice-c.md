# Slice C: local final verification and execution bridge

Production authorization, execution, provisioning and activation remain BLOCKED.
Only registered, newly created disposable workspaces can exercise this bridge.
No production target, PythonAnywhere account or external service was accessed.
Application audit/hash protection does not defend against trusted host/DB admins.

## Actual writer trace

| Writer and caller | Transaction/ownership | Mutation and idempotency |
| --- | --- | --- |
| `permanent.finalize`; private rehearsal script, Slice 6 coordinator, tests, now local bridge | Standalone owns connection and BEGIN IMMEDIATE/commit; leased execution uses coordinator connection and leaves commit/rollback to it. Connection context rolls back errors. | Private rule and immutable operation; First Look claims OR Geography scope identities/snapshots/members/awards/witnesses. Whole frozen population regenerated under writer lock. Same manifest hash verifies existing records and returns idempotently. |
| First Look branch of `permanent.finalize` | Same atomic historical transaction | Unique physical stop, unique assignment; no identity transfer or automatic correction. |
| Geography branch of `permanent.finalize` | Same atomic historical transaction | Unique scope identity, scope snapshot, reviewer/scope/tier award and witness pairs; original supplied frozen evaluation only. |
| `live_first_looks.seal_pending`; tests, no production Flask dispatch | Caller owns transaction/commit; savepoint, no independent BEGIN/commit; no-op update acquires writer lock. Unexpected error rolls back savepoint. | Shared private rules/operations/First Look claims; pending-delivery state and attempts. Requires delivery authority plus finality decision; existing stop claim integrity checked. Legacy delivery quarantine remains a separate, unsupported live adapter. |
| `processing.finalize_job` (Explorer); `process_live_recognition.py`, `issue_historical_explorer.py`, Explorer rehearsal and tests | Caller BEGIN IMMEDIATE, savepoint makes award/witness/job update atomic; caller commits; failures roll back. | Explorer awards/witnesses and job lease completion; unique reviewer/family/scope/tier and witness pair. Lease token/expiry, current ledger sequence and existing evidence checks enforce idempotency. |
| `permanent.append_discrepancy` | Own connection, writer transaction/commit | Append-only discrepancy, hash identity; records disagreement, never reverses or creates a recognition claim. Unsupported by bridge. |

The historical writers have no external side effects, capture, Explorer writes
or per-item commit. Explorer's existing offline/live processing remains separate;
its existing policies and CLI controls are unchanged. No existing writer script
was executed. Historical primitive connection ownership and uniqueness constraints
were re-read from current code, not assumed from Slice 6 documentation.

## Supported families and APIs

Only immutable family `first_look` or `geography_steward`, action `finalize`,
historical manifest format and exact `atomic-historical-v1` accounting dispatch
to `permanent.finalize`. There are no callbacks/function names/SQL dispatch fields.
Unknown families are UNSUPPORTED_OPERATION. Live issuance, Explorer, discrepancies
and recognition corrections are unsupported bridge operations.

`local_execution.py` exposes `verify_approved_operation`,
`execute_approved_operation`, `approve_and_execute`, `reconcile_operation`.
Verification preview returns no token/capability and is never cached admission.
`approve_and_execute` persists Slice B approval, then performs final admission and
automatic execution when a registered disposable context is present. It requires
no second confirmation or human Execute action. The existing approval HTTP route
calls this orchestrator with NO execution context: it returns the durable approval
and an explicit BLOCKED execution result. No execution endpoint/button or context
factory is available through HTTP, configuration flags or environment variables.

## Final admission checks

Each admission reads authoritative control/target records under writer locks:

1. Exact control schema, actual physical control identity, installation binding,
   target UUID, host/path/device/inode and target schema fingerprint.
2. Current verified owner, unchanged owner authentication epoch/key, nonrevoked
   primary/MFA/admin session, absolute session expiry and clock floor.
3. Exact append-only approval/history/hash; effective APPROVED state and approved
   actor still the authorized owner; exact original operation/preparation/event,
   operation generation and target/restore generation bindings.
4. Original operation getter verifies canonical envelope/history, frozen event,
   preparation, population, policy, member identity and accounting.
5. PREPARED decision, NOT_STARTED original operation assertion, READY frozen event,
   no original receipt, no supersession/rejection, supported policy/rule identity.
6. Target-local execution history/claim/seal checked first to prevent replay.
   COMPLETED is accepted only after validating actual writer evidence.
7. Slice 2 current dependency recheck must return READY; unavailable verification
   waits, while stale/invalid data blocks. No copied approval readiness is trusted.
8. Exact supported family/action/manifest and no quarantine/other categories.
9. Durable emergency-stop chain must be inactive and durable disposable readiness
   must match current target UUID/restore generation. Production NOT_ACTIVATED is
   never changed. Missing execution storage fails closed.
10. Actual writer whole-population regeneration must equal the frozen manifest,
    and trusted admission time must not precede operation creation.

## Exact transaction sequence

The consistent lock order is control, then target. Both use BEGIN IMMEDIATE and
FULL synchronous writes. Control remains locked throughout the execution entry,
writer transaction and final evidence projection, fencing approval invalidation,
restore/rebind, readiness/deactivation and emergency-stop updates.

1. Lock control, verify audit/schema/physical control binding.
2. Lock target; inspect existing claim/history/seal and re-read ALL admission state.
3. Insert immutable execution claim and EXECUTING audit; commit TARGET only.
   This is the protected execution-entry boundary. No writer mutation precedes it.
4. Reacquire target writer lock. Because target commit released that reservation,
   ordinary target writers could have changed data: re-read ALL final admission
   checks immediately before issuing a connection-bound writer lease.
5. Invoke only `permanent.finalize` on that same connection. It regenerates and
   validates the whole population again. Insert the actual evidence seal, then
   commit ALL writer effects and seal in ONE target transaction.
6. Reopen a target writer transaction, verify the committed seal against actual
   private operation/claims/snapshots/awards and integrity checks, append COMPLETED
   to existing execution audit and commit. Release control lock afterward.

No distributed atomicity is claimed. Slice B approval/confirmation commit is an
earlier control transaction. A crash between approval and claim leaves a durable
approval without a claim. Once a claim exists, ordinary execution never resumes a
writer. Missing acknowledgements, storage failure or interruption after claim
require separate owner recovery. Target-local locks and terminal fences protect
against delayed/competing workers. Busy/unavailable storage cannot admit mutation.

## Claims, capabilities and evidence

Reuses Slice 6 `recognition_execution_claims`, `recognition_execution_seals`,
`recognition_execution_audit`, existing stop chain and transition triggers. No
redundant journal or execution-control store was created. The new versioned local
claim binds operation envelope/digest, writer manifest hash, original approval ID
and hash, actor, installation/target/restore binding, unique claim ID and time.

`writer_boundary.LocalExecutionCapability` cannot be publicly constructed. An
internal lease requires a registered fresh disposable context, the same target
connection in a transaction, exact durable claim and EXECUTING journal state, and
no seal. It additionally consumes one-use registry admission produced immediately
after the protected final verification; possession of a context/claim alone is
insufficient. The writer validates the registered target/manifest/claim/connection and
consumes the lease once. Scope exit revokes it. A changed manifest, another
connection, direct invocation without authorization/context, replayed/expired
lease, or a production authorization object is rejected. The existing independent
production guard remains in force. No signed authorization or synthetic provider
is used by local admission, lease issuance, writer verification or recovery.

The local receipt is a NEW explicit version: `recognition-local-execution-receipt-v1`,
marked `execution_mode=disposable-local-bridge`. It carries operation/digest,
approval ID/hash, actor, installation, target observation/UUID/generation, claim
hash, writer family/result, exact full-population successful member references,
authorized total, empty quarantine/other groups, start/finish times and actual
writer-evidence digest. The seal links claim, writer hash, receipt and evidence.
Verification recomputes actual stored writer integrity/accounting; a COMPLETED
flag alone is insufficient. Hashing is not administrator-proof.

Original Slice 3 synthetic authorization/receipt assertions are NOT forged or
rewritten. The existing execution audit and target seal are authoritative for
these disposable bridge executions. Slice B checked reads recognize a verified
local outcome instead of invalidating the historical approval merely because its
own legitimate writer effects changed the original dependency snapshot.

## Crash/failure matrix

| Point | Durable state | Next ordinary request / owner recovery |
| --- | --- | --- |
| A before verification | No claim or effects | Fresh admission permitted |
| B after verification before claim | No claim or effects | ALL checks repeated |
| C after claim before writer | EXECUTING claim, no writer effects | RECOVERY_REQUIRED; writer lock plus absence of all outcome rows permits terminal FAILED_BEFORE_COMMIT fence |
| D writer mutation before commit | Writer transaction rolls back; claim remains | Same recovery; never automatic retry |
| E after writer+seal commit before finalization | Actual effects and seal, EXECUTING projection | RECOVERY_REQUIRED; owner verifies seal and appends COMPLETED, never calls writer |
| F after evidence finalization | Verified seal and COMPLETED | ALREADY_EXECUTED |
| G lost acknowledgement | Same as F | ALREADY_EXECUTED |

Tests inject deterministic BaseException interruptions at A–G and inspect reopened
SQLite state. This exercises transactional unwinding, not OS power-loss behavior.
Another test commits the writer transaction and then raises an OperationalError:
the caller reports uncertainty, retry never invokes the writer, and owner recovery
finds the seal. Residual outcome rows without a valid seal require explicit
reconciliation; absent effects are proven only under the target writer lock with
all known outcome tables inspected. Neither case permits resuming this operation.

## Concurrency, races, stop and activation

Two executor threads serialize via database locks, produce one mutation and one
ALREADY_EXECUTED. Two approved operations competing for the same historical writer
cannot duplicate a claim: the first changes protected dependencies, blocking the
second. Two competing HTTP approvals consume one confirmation once; their
production execution remains BLOCKED. Tests use barriers/hooks, not sleep races.

Dependency stale/invalid/unavailable state, supersession, operation digest,
target generation/installation/schema/physical-file replacement, policy change,
deactivation and approval invalidation after approval all prevent mutation.
The target-commit gap is explicitly tested: a normal target writer changes a
dependency after the durable claim, the second verification catches it, and
recovery proves no effects and fences the operation. Preview success is followed
by a fresh final check; it cannot bypass a later stop.

An inactive stop is required immediately before entry. A stop/deactivation request
after protected entry cannot acquire the retained control writer lock until this
operation finishes. It does not forcibly interrupt a writer; it governs subsequent
entries. Tests verify stop updates contend after claim, completion is preserved,
and the subsequently durable stop does not rerun an already completed writer.

Disposable readiness is an audited, generation-bound fixture observation created
ONLY by the registered workspace. It is NOT a production activation provider and
does not change production NOT_ACTIVATED. Production accepts no such context.
Production activation/provisioning still unconditionally rejects execution.

## Explicit install and preserved behavior

The fresh disposable workspace exposes explicit `install_target_storage` before
Slice A pins the target schema. It installs the original private/execution table
definitions, validates schema/FKs and commits; savepoint rollback and idempotency
are tested. It cannot install an arbitrary production target. No new target DDL,
startup migration, fallback database, production install command or activation is
introduced. Existing Slice A/B ceremonies and legacy Slice 1–7 tests remain.

Explorer tables are compared unchanged across real disposable historical
execution. Live First Look, discrepancy records, correction policy and existing
writer semantics are preserved. Active historical quarantine is explicitly
rejected. No VOID/SUPERSEDE correction system, backup automation or broad
delegation is introduced.

## Current limitation and next slice

This is a real local approval-to-writer execution bridge exercised ONLY on fresh
disposable targets. Production has no context factory, compatible production
operation/preparation creation/state-projection path, or activated local readiness
ceremony. Existing source operation contracts retain their synthetic flag. They
are never converted into production subjects. Consequently this slice does NOT
make production execution available, even if a browser or trusted code supplies
flags. The production HTTP path always stops after approval with BLOCKED execution.

The disposable context registry is process-local. Windows spawned workers cannot
reconstruct an executable context against an existing target. Multiple-process
execution provisioning is therefore intentionally unsupported; thread/database
lock tests are not claimed as production multi-worker validation. Deployment
storage/locking, commit/power-loss and backup/restore testing remain outstanding.

Slice D must resolve these explicit production-format/provisioning/readiness and
worker-lifecycle boundaries through a reviewed contract before any activation,
and define the controlled handling of approvals left waiting after a process
dies before claim. It must retain current receipt/claim fencing and final checks;
it must not reinterpret synthetic records, accept detached approval JSON as
authority, enable high-assurance providers by accident, or add a blind retry.

Required safety answers: execution after stale dependencies NO; after changed
target generation NO; after deactivation NO; while stop active NO; two concurrent
executors both mutating this operation NO; uncertain outcome causing blind retry
NO. These apply to supported disposable bridge execution. Production is BLOCKED
in all cases, including the unsupported multi-worker deployment case.

## Files and validation

Added `local_execution.py`, `test_recognition_local_execution.py` and this report.
Changed `writer_boundary.py`, the three authority-check sites in
`permanent.finalize`, the approval HTTP orchestration in `admin_routes.py`, and
Slice B's historical outcome reconciliation in `approvals.py`. Earlier edits in
the working tree belong to earlier slices and were preserved.

Validation includes focused local bridge, A/B, legacy execution, authorization
and historical writer tests; full pytest; tracked/new-file whitespace checks.
The full launcher prohibits external socket connections and SQLite access under
the repository's `src/database` directory. All execution fixtures are newly
created disposable databases and test identities.

Final results: full suite 995 passed, 3 skipped, 1,020 subtests passed; focused
bridge/A/B/legacy execution/writer/authorization regression run 205 passed and
121 subtests passed; final Slice C-only run 40 passed. Final focused coverage
includes the latest response-state and existing-claim error-classification fixes.
Tracked diff and new/previously-untracked touched-file whitespace checks passed.

No production recognition executed; no production award created; no production
activation; no production keys created; no external trust infrastructure created;
no production/ PythonAnywhere access; no external service contact; no commit/push.
