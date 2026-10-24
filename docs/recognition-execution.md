# Operation contracts and durable histories (Slice 3)

This is a LOCAL/SYNTHETIC data foundation. It does not authorize or execute a
recognition mutation. Production provisioning still rejects unconditionally.
No existing writer, Explorer schema/behavior, Flask route, startup hook,
authentication, signing, enrollment, scheduler, emergency stop, recovery service,
or First Look lifecycle is changed. Only fresh disposable targets are supported
for operation-history persistence in this slice.

## Installation and transactions

`operation_schema.install(conn, authorization=..., authority=...)` adds four
tables after the Slice 1 event schema has been explicitly installed:

- `recognition_operation_contracts`
- `recognition_operation_decisions`
- `recognition_operation_executions`
- `recognition_operation_receipts`

The caller supplies an active transaction with foreign keys enabled. File-backed
installation requires the existing exact migration binding for family
`recognition_operations` and the opaque registered authority. Only disposable
authority can currently be provisioned. Installation is additive, idempotent,
savepoint-protected, and does not commit. No automatic migration is provided.

All mutation APIs require an explicit file-backed connection, caller-owned
transaction, exact persistence approval from `binding(action, subject)`, and
disposable authority. Prefer `BEGIN IMMEDIATE`. A no-row UPDATE obtains the SQLite
writer lock before reading operation state. A savepoint covers the entire API
call, with authority rechecked before return. A caught exception followed by an
outer commit cannot retain that call's partial writes. The caller owns durability.

These SQLite transactions do **not** coordinate with external authorization state
or establish the future authorization-to-target-commit linearization point.
Operation receipts here are synthetic assertions, not proof of durable target
mutation. Full execution idempotency, fencing, commit uncertainty, and recovery
remain Slice 6 responsibilities.

## Immutable operation envelope

`create_operation(conn, event_id, accounting_policy, ...)` derives all population,
target, action, rule, and event fields from the frozen event; callers cannot
override them. The current historical First Look/Geography format maps to action
`finalize`. Unsupported legacy dependency records require revision through the
existing Slice 2 policy. Creation requires retained event state READY and matching
observed target; it does not claim current dependency freshness.

The `recognition-operation-contract-v1` envelope contains:

- An independently random UUID `operation_id`, distinct from the event UUID,
  preparation UUID, and existing content-derived private writer operation ID.
- Event ID/hash, preparation ID/hash, parent event ID, and dependency-manifest hash.
- Family, exact action, and writer-manifest hash. The existing writer manifest
  remains in the immutable preparation; it is not regenerated into a new operation.
- Existing target observation and explicit unenrolled placeholder
  `{enrollment_id: null, generation: null}`. This is never an enrollment bypass.
- Existing full rule definition/hash, preserving whatever version/algorithm
  identity that rule defines without inventing a separate version convention.
- Existing candidate-population hash and ordered member IDs. Each member ID is the
  canonical SHA-256 of one exact candidate, not merely a reviewer or stop ID.
  Geography's complete scope/member snapshots remain bound through the writer
  manifest and dependency manifest.
- Immutable accounting policy: nonblank `reference`, `quarantine_categories`, and
  `other_categories` lists. Lists contain unique nonblank strings and are disjoint.
  These are synthetic policy assertions, not authenticated production rules.
- Creation and original event-freeze timestamps, plus original preparation request
  provenance. Those labels/times do not become authenticated identity or trusted time.
- `synthetic_contract_only: true`.

There is one contract per frozen event. A duplicate create with the same accounting
policy returns the existing envelope and current histories unchanged, including
after invalidation/decision changes. A conflicting policy fails. Identical
preparation requests still follow Slice 1: each new preparation has a new UUID;
re-freezing the same preparation returns the same event. New events/revisions
always receive independent operation UUIDs, even with identical writer manifests.
No creation API accepts a caller-selected operation ID.

Envelope JSON uses existing `rules.canonical`/`digest` semantics. Database triggers
block UPDATE, DELETE, and INSERT OR REPLACE, including with recursive triggers off.
Retrieval verifies schema, canonical hashes, event/preparation bindings, and linked
history. These protections are not signatures against an administrator who can
replace schema and rewrite all records/hashes.

## Decision history

`record_decision(conn, operation_id, state, reason, evidence=..., ...)` appends a
sequence-numbered, hash-linked assertion with UTC observation time. Every assertion
is explicitly `synthetic_assertion_only: true`. Initial state is PREPARED.

| Current state | Allowed next states |
| --- | --- |
| PREPARED | AUTHORIZED, REJECTED, SENT_BACK, INVALIDATED, SUPERSEDED |
| AUTHORIZED | INVALIDATED, SUPERSEDED |
| REJECTED / SENT_BACK / INVALIDATED / SUPERSEDED | None |

AUTHORIZED requires exactly `{authorization_id, artifact_sha256}` as evidence;
the digest must be lowercase SHA-256. This is an immutable reference associated
with the exact operation by its history record, **not signature verification,
executive authority, or an Authorization object**. Other decisions take no evidence.
An AUTHORIZED reference cannot be replaced. App roles are not consulted.

All decisions require a nonblank explanation/reference in `reason`. SENT_BACK also
atomically appends INVALID to the original event, using separately supplied exact
event persistence `event_authorization`/`event_authority`. A missing approval or
failure rolls back both histories. Revision then uses existing
`events.create_revision` and freeze; its new operation starts PREPARED/NOT_STARTED
without inherited authorization.

Decisions cannot be changed during EXECUTING. A terminal execution may later be
marked SUPERSEDED on the decision axis, without replacing its terminal execution
or receipt. Rejected/invalidated/sent-back decisions remain terminal historical
decisions; successor events link through the existing parent event identity.

## Execution history

`record_execution(conn, operation_id, state, reason, receipt=..., ...)` records
synthetic observations only. It does not call any recognition writer. There is no
executor or human Execute action in this slice.

| Current state | Allowed next states |
| --- | --- |
| NOT_STARTED | WAITING, EXECUTING, FAILED_BEFORE_COMMIT |
| WAITING | WAITING, EXECUTING, FAILED_BEFORE_COMMIT |
| EXECUTING | COMPLETED, COMPLETED_WITH_QUARANTINE, FAILED_BEFORE_COMMIT, PARTIALLY_EXECUTED_RECONCILIATION_REQUIRED, UNKNOWN_RECOVERY_REQUIRED |
| Any terminal result | None |

WAITING/EXECUTING/normal completion additionally require latest decision AUTHORIZED
and retained event state READY. No dependency freshness or actual production
authorization is inferred. WAITING can append a new reason; identical last
state/reason/evidence submissions return unchanged history. Conflicting terminal
results and terminal-to-executing transitions fail. No recovery transition is
introduced: uncertain/partial states remain terminal pending a future controlled
recovery/adjudication design.

Database triggers enforce initial states, contiguous sequences, legal transitions,
the authorized-decision prerequisite for active/completed execution assertions,
and receipt presence for normal completion. Focused APIs enforce full evidence,
event, receipt, and cross-history checks. Direct privileged SQL is outside the
domain API boundary and can never acquire writer authority from these tables.

## Receipt and accounting contract

A receipt has format `recognition-operation-receipt-v1`, with:

- Exact operation/event IDs and recorded authorization ID/artifact digest.
- Exact enrollment placeholder and observed target identity.
- Terminal outcome, authorized candidate count, start/finish timestamps.
- `successful`, `quarantined`, and `other` outcome lists.
- `synthetic_assertion_only: true`.

Every outcome names an exact candidate `member_id` and a nonblank
`outcome_reference`. Quarantine/other outcomes also require an allowed category and
nonblank reason. The reference is retained evidence labeling, not proof that the
result occurred. Unknown population members, duplicate members within/across
groups, mismatched bindings, malformed timestamps, and unapproved categories fail.

`validate_receipt(operation, receipt)` is pure validation returning authorized,
successful, quarantined, other, and unaccounted counts. COMPLETED and
COMPLETED_WITH_QUARANTINE require all members accounted for exactly once:

`authorized = successful + quarantined + other`, with `unaccounted = 0`.

COMPLETED has no quarantine. COMPLETED_WITH_QUARANTINE requires explicit quarantine.
An explicit policy-approved other outcome can be normally accounted for without
claiming success. FAILED_BEFORE_COMMIT cannot claim successful mutations.
Partial/unknown receipts may retain unaccounted members, which the returned counts
expose; they cannot become normal completion. System/authorization failures must
not be represented as allowed per-item quarantine in future production policy.

Normal completion requires a receipt. Other terminal observations may omit it to
represent lack of reliable evidence. A receipt and the terminal execution assertion
are inserted atomically in the caller's transaction. Only one immutable receipt
exists per operation; canonical JSON/body SHA-256 protects it, and the terminal
history evidence binds `receipt_sha256`. An operation row alone is never a receipt.

## Remaining boundaries

No contract/history/result from this module can satisfy existing recognition writer
Authorization + opaque Authority checks. The production provisioner is unchanged;
no permissive callback, application-role approval, implicit target selection,
enrollment, production key, or production capability is added.

Slice 4 can implement independent artifact/status verification against these
identities and digests. Production use requires a reviewed versioned extension:
authenticated non-null enrollment, real authority verification, and executor-owned
history/receipt recording. Synthetic assertions and null enrollment records must
never be promoted into production authority or proof of execution.

[Slice 5](recognition-enrollment.md) now adds an explicit synthetic v2 envelope
extension for non-null enrollment references. Legacy v1 records and default
creation retain the contract above. Both formats remain synthetic; the extension
does not activate production authorization or execution.

REQUIRES IMPLEMENTATION DESIGN: production wire profile, enrollment/restoration
controls, trusted status/time persistence, and the commit/recovery protocol.
REQUIRES EXTERNAL INFRASTRUCTURE: independent signing/status trust and enrollment
administration. Neither is provided or contacted in Slice 3.
