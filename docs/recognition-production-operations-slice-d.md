# Slice D: production operation contract and admission context

Production operation DATA can now be created, approved and submitted to Slice C
without synthetic providers. Production writer provisioning, execution and
activation remain unconditionally BLOCKED. No production service/database was
accessed and no production awards, keys or external infrastructure were created.
Hashes and append-only triggers provide application-level audit protection, not
protection against trusted database/deployment administrators.

## Existing repository and callers inspected

Slice 3 already owns operation UUIDs in `recognition_operation_contracts`, one
operation per event, canonical envelope/hash, append-only decisions/executions and
receipts. Its old v1/v2 envelopes/history explicitly describe synthetic contracts.
Slice B owns approval/history in the separate Slice A local control store and
consumes exact confirmations in that same control transaction. Slice C owns the
single local coordinator, target claims/seals/audit and connection-bound one-use
writer leases. Before D its context loader accepted fresh disposable workspaces
only and its source operation getter accepted synthetic envelopes only.

Current mutation callers were traced through `permanent.finalize`, its First
Look/Geography branches, `live_first_looks.seal_pending`, Explorer
`processing.finalize_job`, private/Explorer rehearsal scripts, historical Explorer
CLI, live Explorer CLI, administrative routes and deployment entry point
`scripts/active/serve_pilot.py`. Historical writer/transaction details remain in
the Slice C report. No additional production recognition scheduler/daemon was
found. The pilot runs Waitress with four threads; deployment validates the API
and assignment database paths. D does not invent a new service/process architecture
or assume that one worker is the only reader of approvals.

## Production representation in existing tables

`recognition-local-operation-v1` is a NEW envelope format in the ORIGINAL operation
table, not a second identity system. It retains operation UUID, immutable frozen
event/preparation IDs and hashes, family/action, writer manifest hash, rule/hash,
dependency hash, population hash, exact member IDs, full accounting policy,
provenance, frozen time and creation time.

It additionally binds operation version 1, initial PREPARED state, canonical local
installation/target UUIDs, restore generation, actual physical target observation
and pinned schema hash, creation actor, request UUID and exact request digest.
The operation digest is the canonical envelope's SHA-256, stored in the existing
`body_sha256` column and returned as `operation_sha256`; it is not a self-referential
field inside the hashed envelope. Current state is derived from immutable history,
approvals and the existing execution journal, never rewritten into the envelope.

Production envelopes have NO synthetic contract flag or external enrollment
reference. New `recognition-local-operation-history-v1` entries use the existing
decision/execution tables without pretending to be synthetic assertions or signed
authorization. Original v1/v2 envelopes, hashes and history remain unchanged and
readable. The old synthetic AUTHORIZED evidence is not fabricated for local approval.

Only `first_look` and `geography_steward`, action `finalize`, exact historical
manifest and `atomic-historical-v1` accounting are supported. Active quarantine and
other accounting categories remain empty. Explorer/live First Look/discrepancy and
VOID/SUPERSEDE/REINSTATE/GRANT_MISSING issuance are rejected as current execution
families. Future corrections can have their own UUID and explicit version/action
in the existing identity system; D does not implement or silently enable them.

## Creation, frozen population and dependencies

`production_operations.create_operation` requires the current recognition-owner
administrative session. Browser/CLI input is exactly request UUID, supported
family, historical inputs, evaluation time, review reference and optional parent
operation UUID. Actor, preparer, generation, target, policy, writer, preparation,
event and operation digest are all derived server-side. Arbitrary writer/callable/
module/SQL/target/authority fields are not accepted. Invalid input fails closed.

Creation takes control BEGIN IMMEDIATE, then target BEGIN IMMEDIATE. The existing
historical preparation generator and Slice 2 dependency builder create a full
preparation. Its event, READY history, operation and initial local histories are
persisted in ONE target transaction against that snapshot. No browser-supplied
manifest/candidate population is accepted. Geography scope/membership/evaluation
and denominator stay frozen; First Look ordering, identity history, deletion
policy and non-transfer semantics still come from unchanged existing rules.

Execution's authoritative population is ALWAYS this frozen manifest. Existing
candidate regeneration in Slice C/the historical writer is a comparison-only
validation prerequisite: a difference blocks execution. It never replaces the
approved population, moves a winner or recalculates an old Geography award.
New legitimate inputs require a new preparation/event/operation.

Request UUIDs make duplicate/concurrent creation idempotent. Exact replay returns
the same operation; changed request/actor/generation conflicts. A revision creates
a new linked event/operation and appends SUPERSEDED to the unclaimed predecessor
within the same target commit. Claimed or terminal predecessors cannot be revised.
Slice B checked reads append invalidation to old approval history when they see
the supersession; final execution checks it independently.

The control creation audit is a SEPARATE commit, not distributed atomicity. An
interruption after target commit leaves the complete immutable graph and creation
actor/request identity durable. Retrying the SAME request UUID returns that graph
and repairs the missing control audit without creating a second operation.

## Slice B and Slice C compatibility

The original operation getter strictly validates the new envelope, local history,
preparation generation/actor/target and canonical hash. Slice A step-up and
confirmation therefore bind its exact digest and state without new identity APIs.
Slice B binds the original operation UUID, digest, current state and generation,
and checks the operation's local target descriptor against authoritative control.
It still commits confirmation consumption/approval/history atomically in control.

Slice C is the ONLY coordinator. The existing approval orchestrator detects a
new production-format subject server-side, loads its admission descriptor and
calls final verification automatically. No second Execute confirmation/button or
arbitrary writer endpoint is added. Final checks still verify owner/session,
operation/preparation/event, approval/hash, exact target/schema/generation,
dependency READY, supported policy/accounting, existing claim/history/seal and stop.
The unconditional production activation/deployment guard then returns WAITING,
without creating an execution claim or calling a writer. Disposable readiness
cannot satisfy or replace this guard.

## Context and writer permission stages

`load_context(config, operation_id)` reconstructs an opaque, registered,
one-use `ProductionOperationContext` from authoritative records. It binds exact
operation UUID/digest/family, installation/target/restore/schema identity and
physical control identity. Public construction is rejected. It contains no raw
session token, password, MFA seed, signing key, callable or SQL authority. Wrong
operation/approval/target binding fails. An admission attempt consumes the descriptor;
replaying the same object fails. A restart may reconstruct a descriptor, but never
erase or bypass durable claims, terminal history or seals.

An admission descriptor is NOT a writer permission. Actual Slice C writer leases
remain a separate one-use protected-final-check product, bound to the connection,
operation ID/digest/family, installation, target/generation, durable claim digest
and final-verification digest. The writer enforces exact scope/consumption and
revokes leases on scope exit. D makes these bindings explicit in the existing
lease registry. Production descriptor-to-writer provisioning STILL rejects
unconditionally, independently of the activation guard. The old production
authority provisioner and independent writer production guard also still reject.
No environment/DB flag, `production=True`, force option or synthetic fallback can
enable execution. Activation and real writer provisioning require a later slice.

## Worker lifecycle and restart

`discover_pending` reads the persisted approval/operation/journal under the same
control-then-target lock order. Discovery is advisory, bounded and grants no
capability. Only approved NEW production-format operations without a claim or
terminal execution result are selected; old synthetic subjects are excluded.
Approvals arriving after a scan snapshot are handled on a subsequent scan.

`continue_pending` loads a fresh exact descriptor for each discovered approval
and calls Slice C's same `execute_approved_operation`. Each continuation uses an
opaque server-only reference to the ORIGINAL approval's stored session hash.
The ordinary owner/primary/MFA/session epoch, expiry, revocation and generation
checks are reused. A browser cannot supply a hash as a session token or create
these references. No raw authentication secret needs to be persisted in a job.
There is no autonomous recovery or writer retry in the worker.

States are: PREPARED without approval; APPROVED_WAITING after approval and before
a claim; EXECUTING represented by a durable claim; verified seal plus COMPLETED
audit means COMPLETED; unfinished claim means UNKNOWN_RECOVERY_REQUIRED; residue
without valid seal requires PARTIALLY_EXECUTED_RECONCILIATION_REQUIRED. Terminal
FAILED_BEFORE_COMMIT cannot reenter execution. COMPLETED requires actual writer
evidence, not a flag. Inspection and existing journal validation preserve these
states across process restarts.

The worker rechecks after discovery. Stale dependencies, invalidated approval,
supersession, wrong generation, deactivation or active stop cannot execute.
Concurrent workers use the existing SQLite locks, unique claims and fences.
Restart tests include two fresh concurrent Python processes reconstructing a
pending context without the old in-memory disposable-workspace registry.
Since production mutation is globally blocked, positive committed-outcome and
uncertain-outcome restart tests exercise Slice C's real disposable writer evidence;
they do NOT claim production mutation was tested or enabled.

The minimum current continuation policy retains Slice A's approximately eight-hour
session limit. Expired/revoked source authentication blocks continuation and
preserves the approval; it never renews authority automatically. Slice E must
define deliberate renewal/reapproval/expiry policy for work delayed past that
window. No daemon or scheduled task was installed or launched.

## Flask, CLI and deployment

All web endpoints use the existing recognition-owner/session/CSRF/no-store guards:

- POST `/api/admin/recognition-control/operations`: strict creation fields, 201.
  Idempotent replay returns the same operation, with the same 201 response.
- GET `/api/admin/recognition-control/operations/<id>`: inspection, 200.
- Existing POST `.../operations/<id>/approve`: confirmation/step-up/reason only;
  persists approval then automatically enters the coordinator. Production subject
  returns 202 APPROVED/waiting while the gate is closed. Legacy approval response
  stays compatible. No context tokens or writer authority are returned.
- Existing approval get/list retain exact history and invalidation semantics.

Malformed fields are rejected; unauthorized requests use existing 401/403 rules;
state/replay conflicts use existing 403/409 rules; missing records use 404;
storage/configuration failure uses 503. The structured execution result distinguishes
WAITING, BLOCKED, COMPLETED and recovery states without undoing a persisted approval.
There is no public execution or worker-discovery endpoint.

The existing management CLI adds `install-contracts`, `create-operation`,
`inspect-operation`, `scan-approved`, using explicit target/control/key-file paths
and host ceremony operator/reason. Creation/inspection require a current owner
administrative token through a non-echoing prompt, not command arguments.
`scan-approved` is the bounded trusted deployment worker entry and can continue
ONLY durable eligible approvals through Slice C. It accepts neither arbitrary
writer selection nor force/bypass approval. No second implementation is added.
Recovery stays with the existing separate owner/session/recent-step-up protocol;
no new CLI recovery grant was introduced.

## Explicit installation and migration

The envelope/history extension reuses existing tables and immutable triggers;
there is no duplicate operation table, redundant journal or startup migration.
`install_target` explicitly installs original event/operation/private/execution
definitions, requires an existing exact Explorer schema, caller transaction/FKs,
uses a rollback savepoint and validates schema/FKs. It is idempotent. No fallback
DB is created. The CLI verifies the intended existing installation before DDL.

If installation changes a schema already pinned by Slice A, runtime becomes
blocked until the operator explicitly previews the target and advances the
restore generation using the existing ceremony. This invalidates old approvals
and authentication. DDL and rebind are not claimed atomic across files. A repeated
CLI install after changed-schema interruption requires that explicit reconciliation;
the low-level target migration itself remains idempotent/rollback-safe. No such
production migration or ceremony was run during this implementation.

## Compatibility, blockers and Slice E

Explorer and existing writer tests/rules remain unchanged. First Look's lifetime
identity and historical review rules are preserved. Geography retains frozen
scope, members, original evaluation and denominator. No correction/missed-award
issuance, active historical quarantine, backup automation or delegation is added.
Slice 4 authority/status, Slice 5 continuity and Slice 7 high-assurance activation
remain dormant/test-only; production creation/approval/continuation never
instantiates them. Original synthetic tests remain supported.

Slice E must establish reviewed local activation/deployment readiness and actual
production writer-capability provisioning, production execution receipt/projection
semantics, the delayed-approval session policy, and disposable hosted storage,
multi-worker commit/recovery, restart and backup/restore verification. The new
admission descriptor alone must never become writer authority. Current blocks
must not be replaced by a flag or by reinterpreting synthetic records.

Required answers: production operation creation without synthetic providers YES;
Slice B approval YES; Slice C final verification YES; restart duplicate execution
NO; browser arbitrary writer NO; CLI bypass approval NO; execution while activation
disabled NO; execution while stop active NO; execution after target generation
change NO. Actual production mutation remains blocked in ALL cases.

## Files and validation

Added `production_operations.py`, `test_recognition_production_operations.py` and
this report. Changed `operations.py`, `admin_auth.py`, `approvals.py`,
`local_execution.py`, `writer_boundary.py`, `admin_routes.py`, and the existing
administrative management CLI. Earlier working-tree changes were preserved.

Tests independently compute canonical operation digests and physical target
identity, assert known First Look and Geography populations, and cover exact
bindings, idempotent/concurrent creation, revisions, approval, context replay,
production gates, stale/generation/stop races, process restart, two concurrent
fresh worker processes, approval during scanning, invalidation after discovery,
browser authority rejection, CLI bypass rejection, session expiry, Explorer and
legacy writer compatibility. Full validation blocks external socket connections
and repository `src/database` access; worker subprocesses also prohibit network.

Results: full pytest 1,018 passed, 3 skipped, 1,039 subtests passed; focused
D/A/B/C/operation/authorization regressions 185 passed, 146 subtests passed;
final Slice D-only run including the target-commit/control-audit interruption
test 24 passed, 19 subtests passed. Tracked diff and all touched new/previously
untracked file whitespace checks passed. No validation was blocked.

No production recognition executed; no production award created; no production
activation; no production keys created; no external trust infrastructure created;
no production database or PythonAnywhere access; no external service contact;
no commit/push.
