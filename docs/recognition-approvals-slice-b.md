# Slice B: local administrative approval records

Slice B persists approval only. Production authorization, execution and activation
remain blocked. It never calls recognition writers or the execution/recovery
coordinators. Local hashes and append-only triggers protect ordinary application
use; they are not protection against trusted database/deployment administrators.

## Existing contracts inspected

Slice 3 owns operation identity in `recognition_operation_contracts`, with one
immutable envelope per frozen event. `operations.get_operation` checks canonical
JSON/hash, event/preparation hashes, rule, dependencies, population/member IDs,
accounting policy, target observation, decision/execution chains and receipts.
The existing operation generation is the frozen preparation request's
`generation_reference`; it is distinct from Slice A's integer restore generation.
Decision history begins PREPARED, execution history begins NOT_STARTED. Slice 3
decision evidence and its AUTHORIZED state are explicitly synthetic assertions.

Slice A owns confirmations, hashed primary/session/step-up references, owner
authorization and installation bindings in the separate local control database.
Its confirmation binds the operation envelope digest and state digest; these
include preparation/generation/population and current decision/execution state.
The immutable installation binding associates each restore generation with one
installation, target UUID and physical/schema observation. No browser field can
choose these bindings. Delegation is not implemented.

## Schema and state

The additive control v3 extension contains `recognition_approvals` and
`recognition_approval_history`. Existing control v2 and Slice 6 v1 definitions are
preserved. Slice A accepts either exact v2 or exact v3; the synthetic v1 checker
continues rejecting both. No redundant control database or target tables are added.

`recognition-local-approval-v1` records bind approval UUID, original operation ID
and digest, event/preparation IDs and hashes, original operation generation,
population and accounting policy hashes, installation/target identities, physical
target/schema observation, restore generation, operation contract format and
synthetic flag, checked operation state and its digest, authenticated actor,
hashed administrative session and confirmation reference, time and reason.
Canonical record hashes link every history entry to the original approval.
Neither raw session/confirmation tokens nor MFA material are stored in approvals.

PENDING is the conceptual pre-approval state: no durable pending row exists.
One atomic transaction moves PENDING to APPROVED. Append-only history permits
APPROVED to INVALIDATED or SUPERSEDED, both terminal. The original APPROVED
document never changes. Unique operation and confirmation constraints allow one
approval record per operation, even after invalidation; a revised operation is
required for a new approval. No APPROVED-to-PENDING/rebinding transition exists.
This deliberately avoids an intermediate state needing recovery.

## Atomicity and crash matrix

The lock order is control BEGIN IMMEDIATE, then target BEGIN IMMEDIATE. All
authoritative operation, owner, installation, step-up, confirmation and dependency
checks occur under these locks. The target reservation stays held THROUGH the
control commit. The target is never modified by approval and is rolled back on
exit. Operation writers therefore cannot change the checked target snapshot
between validation and approval commit, including when SQLite uses WAL.

Confirmation `used=1`, approval insertion, history insertion and administrative
audit append share ONE control-store commit. There is no cross-database write
transaction or claimed distributed atomicity. SQLite storage guarantees and
trusted host/filesystem behavior remain assumptions; disposable hosted storage
testing is required before any production execution design is activated.

| Injected failure | Durable consumption | Approval/history |
| --- | --- | --- |
| A: before confirmation validation | No | Absent |
| B: after validation, before consumption | No | Absent |
| C: after consumption, before approval insertion | No | Absent |
| D: after approval insertion, before history | No | Absent |
| E: after history/audit, before commit | No | Absent |
| F: after commit, before acknowledgement | Yes | Both present |

Tests inject deterministic exceptions at these boundaries and reopen SQLite to
check durable results. They exercise application transaction unwinding, not an
OS power failure. After a lost acknowledgement, authenticated list/get retrieves
the committed record; repeating the mutation fails rather than consuming again.
Serialized control writers plus unique constraints allow exactly one concurrent
winner for the same confirmation, different confirmations or different sessions.
The losing valid confirmation remains unused when conflict is detected.

## Validity and invalidation

Approval requires PREPARED / NOT_STARTED / READY, no receipt, exact target and
valid accounting, plus the original Slice 2 dependency recheck returning READY.
STALE and INVALID reject without consuming confirmation. Verification failures
are unavailable, not persisted invalidity. Slice C must perform the final check.

Restore/rebind appends INVALIDATED history for every effective approval in the
same control transaction that advances generation and revokes authentication.
Slice A's existing target/control rebind commits remain separate: interruption
between them fails closed on target mismatch and requires operator repair.

Authenticated get/list reconcile operation, generation and dependency bindings
under the same lock discipline, appending INVALIDATED if the subject is now
superseded/rejected/corrupt/missing/stale or otherwise mismatched. Original hashes
and records remain available in history. This is lazy reconciliation, not a new
background service or a cross-store write hook. A target/control identity mismatch
blocks access outright; it cannot report an effective approval. Raw SQL rows or a
previously returned JSON object are historical data, never executable authority.
Transient verification/storage failures fail closed without inventing invalidity.
Manual invalidation/supersession requires owner session, recent operation-scoped
step-up and reason; it cannot reinstate an approval or correct an award.

## API and explicit install

Python APIs in `approvals.py`: `create_approval` (`approve_operation` alias),
`get_approval`, `list_operation_approvals`, `invalidate_approval`, `install`.
The creation API takes operation ID, authenticated server session, step-up,
confirmation, reason and trusted server time; all operation details are loaded
server-side. There is no arbitrary-record approval interface or provider callback.

The existing owner/session/CSRF protected, no-store blueprint adds:

- POST `/api/admin/recognition-control/operations/<operation_id>/approve`
- GET `/api/admin/recognition-control/operations/<operation_id>/approvals`
- GET `/api/admin/recognition-control/approvals/<approval_id>`

POST accepts only `step_up_token`, `confirmation_token`, `reason`, `csrf_token`.
Actor, digest, approved flags and all unknown fields are rejected. The response
states `execution_pending=true`, with production authorization/execution BLOCKED.
The old Slice A consume-data endpoint still does not approve anything. Tokens
consumed there cannot later create approval. No web migration/invalidation route,
writer, recovery or activation endpoint is added.

Trusted host operators may explicitly run the EXISTING management CLI with action
`install-approvals`, explicit absolute `--target`, `--control`, `--key-file`,
`--operator`, and `--reason`, after Slice A installation. This was implemented but
NOT run against production. Installation is idempotent and uses a savepoint inside
a caller transaction; caught failures roll back its DDL. Startup and web requests
never migrate, create fallback files or grant recognition execution permissions.

## Compatibility and Slice C boundary

Existing event/operation IDs, envelope formats, synthetic decision/execution
history, authority checks and all writers are unchanged. No approval is projected
into synthetic AUTHORIZED history and no signed artifact is fabricated. The local
history references the original operation, not a parallel operation identity.
Slice 4–7 implementations stay dormant/test-only. Explorer is unchanged.

IMPORTANT: currently creatable Slice 3 operation contracts remain explicitly
synthetic and disposable. Slice B can record local administrative approval of
such an exact subject, but neither converts that contract into production data
nor provides a production preparation/operation-creation path. Its production
approval RECORD format uses real local authentication, never a synthetic provider.
Slice C must explicitly establish compatible production operation/preparation and
receipt contracts, scoped persistence permissions and final checked admission;
it must reject synthetic subjects for production execution. No removal of the
synthetic flag or reinterpretation of old records is acceptable.

Slice C must also revalidate effective approval/hash/session or policy revocation,
exact current operation and installation/restore bindings, dependency READY,
activation/readiness and idempotent claim/commit/recovery boundaries. It must not
treat detached approval JSON as authority or retry an uncertain commit blindly.
Award corrections, delegation, backup automation and deployment storage testing
remain outside Slice B.

## Validation

Focused tests cover exact independently computed hashes, actor/session/step/
confirmation denial and expiry, invalid TOTP, operation corruption/accounting,
supersession/rejection, stale/unavailable dependencies, identity/generation,
durable crash outcomes, concurrent requests, target writer exclusion, explicit
migration/rollback, immutable history, strict HTTP fields/CSRF and blocked writers.
Full-suite validation also exercises Slice A, Slices 1–7, reviewer/admin auth,
Explorer and existing recognition writers against disposable fixtures.

Validation results: focused Slice B/A: 67 passed, 54 subtests passed (26 Slice B
tests plus 41 Slice A tests). Full pytest: 955 passed, 3 skipped, 1,020 subtests
passed. The full-suite launcher prohibited external socket connections and SQLite
access beneath `src/database`. Final focused validation additionally compared the
entire target SQL dump before/after approval. Tracked diff and new-file whitespace
checks passed. No production installation, recognition execution, awards,
activation, production keys, external infrastructure, commit or push occurred.
