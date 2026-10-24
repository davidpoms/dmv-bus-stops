# Immutable preparation/event foundation (Slice 1)

This module is an on-demand data foundation, not production authorization or
execution. Production provisioning and activation remain blocked. No CLI,
startup hook, dashboard, scheduler, executor, or recovery service is added.

`event_schema.install(conn, authorization=..., authority=...)` explicitly adds
three tables: `recognition_preparations`, `recognition_frozen_events`, and
`recognition_event_history`. The caller must supply a transaction and enable
foreign keys. Installation is additive, idempotent, savepoint-protected, and
does not commit. File installation requires the existing exact migration
authorization and registered opaque authority. Only disposable authority can
currently be provisioned. No database is selected or created implicitly.

## API

All mutations in `events.py` use an explicit file-backed connection and a
caller-owned transaction. Prefer `BEGIN IMMEDIATE`. The APIs take the existing
`authorization` and `authority` keyword arguments for permission to persist
preparation data. `binding(action, subject)` describes that persistence request;
it grants nothing and is not an executive approval. The caller commits only
after success. Savepoints roll back a failed API call even if its exception is
caught. Authorization is rechecked before returning; a future production
transaction coordinator and commit linearization are **not** implemented.

- `create_preparation(conn, request, ...)` accepts exactly `family`, `inputs`,
  `evaluation_at_utc`, `review_reference`, `preparer_id`, `generation_reference`,
  and `parent_event_id` (null for an initial preparation). Its binding subject
  is the whole request. It calls existing `permanent._prepare()` under the writer
  lock, preserving First Look and Geography eligibility and reconciliation
  requirements. There is no candidate/population/manifest override argument.
- `freeze_preparation(conn, preparation_id, ...)` binds that preparation ID,
  regenerates and compares the whole manifest under the lock, and atomically
  creates an event and its initial READY history. A changed snapshot fails closed.
  Replaying a freeze returns the existing event and its current history; it does
  not reassert freshness or change state.
- `create_revision(conn, parent_event_id, request, ...)` requires the request's
  parent to match an existing event in the same family. Its approval is the
  ordinary create-preparation binding. Freeze the returned preparation to obtain
  a new event identity. The original preparation, event, and history remain.
- `get_event(conn, event_id)` returns detached data after schema, canonical hash,
  manifest, linkage, and history checks. It does not grant writer authority.
- `record_event_state(conn, event_id, state, reason, ...)` binds a dictionary
  containing exactly those three values. It appends READY → STALE or INVALID,
  or STALE → INVALID. INVALID is terminal. Replaying the last state and reason
  is idempotent. No transition restores READY.

Preparation and event identities are independent random UUIDs; identical content
can produce distinct revisions. The content-derived `manifest_sha256` remains
separate and is not an executed operation ID. Preparation timestamps and freeze
timestamps are system UTC observations, not trusted-clock attestations.
Preparer and generation references are retained labels, not authenticated human
identities or deployment attestations. The existing manifest's
`authorization_reference` field contains the review reference for compatibility;
it does not constitute an authorization.

Preparations retain the full generated manifest, exact candidates, manifest and
candidate-population hashes, rule definition/hash, inputs, source report, identity
history, and completion ledger. Dependency hashes conservatively cover these
whole structures; scoped invalidation and automatic dependency monitoring are
deferred. Geography retains the existing reviewed scope inputs; this slice does
not independently authenticate scope completeness or certification.

The target observation retains the existing hostname/path/device/inode identity.
It is **not** independently controlled target enrollment. READY means the stored
snapshot matched at freeze, not that it is currently executable, fresh, approved,
or safe for production. State changes are descriptive invalidations, not future
executive decisions. First Look remains historical; no account lifecycle hook
reassigns or erases it.

## Immutability and limits

UPDATE, DELETE, and replacement triggers protect all three tables, including
`INSERT OR REPLACE` with recursive triggers disabled. Unique preparation linkage
and SQLite writer serialization prevent conflicting freezes. Canonical hashes
and a linked state history detect inconsistent stored data; they are not
signatures or protection against an administrator replacing schema and rewriting
all hashes. Each API checks the expected schema. Direct privileged SQL is outside
the domain API boundary.

Slice 2 adds [declared dependency validation](recognition-dependencies-slice2.md)
in the existing preparation field; new preparations use its versioned manifest.
The whole-structure hashes described above remain a description of Slice 1
records, which are retained without rewriting. Authenticated preparer/deployment
provenance, independent target enrollment, and the future exact-event
approval/transaction boundary remain deferred. Do not wire events or synthetic
artifacts into existing recognition writers as authority. Explorer tables, jobs,
rules, witnesses and behavior are unchanged.
