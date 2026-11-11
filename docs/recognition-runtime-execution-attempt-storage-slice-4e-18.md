# Slice 4e-18-R: inert runtime execution-attempt storage

This implements storage, DATA codecs/validators, read-only inspection and an
explicit local migration only. There is no attempt producer, live result,
coordinator, continuation token, authentication issuance or writer/execution
authority. No runtime code inserts an attempt or creation event. Populated
attempts in tests are direct synthetic schema-constraint fixtures only.

## Identity and canonical codecs

`runtime_execution_attempt_schema` implements the exact 4e-17 identity:

```text
format = recognition-runtime-live-attempt-v1
attempt_id
authority_id
authority_sha256
created_at_utc
expires_at_utc
```

`validate_attempt`, `parse_attempt` and `attempt_digest` validate bounded canonical
DATA (4096 UTF-8 bytes), canonical UUID/lowercase SHA, exact UTC seconds and a
positive interval. Parsing rejects duplicate/unknown/missing keys, noncanonical
JSON, malformed digests, NULs, floats and invalid time types. Digest is external
to the body, using existing `canonical()` / `digest()` rules. No physical identity
or authority fields are invented or copied into an alternative source of truth.

`validate_binding(control, body, expected_scope=...)` resolves the **durable**
authority row and verifies its full immutable authority/AUTHORIZED genesis/
consent/audit graph, ID/digest, creation >= authority issuance and expiry exactly
equal to the authority expiry. It never accepts a supplied serialized authority
as proof. Optional exact scope comparison covers complete operation reference,
runtime target, physical snapshot, activation, approval, authentication,
dependencies and stop objects, including nested proposal/ACK and epochs. All
comparison is canonical/type-sensitive and physical integers remain lossless.

These are structural and historical validators, not fresh runtime authentication
or admission. `expected_scope` is comparison DATA, not a trusted current context.
`validate_expiry(body, now=...)` checks creation <= time < original expiry; its
supplied time is also DATA. The future coordinator must obtain fresh authoritative
scope/time through its reviewed manager and protected authentication readers.
Successful validation here cannot substitute for that context.

The creation codec has the nine exact fields approved in 4e-17. Format is
`recognition-runtime-attempt-created-event-v1`, sequence is integer 1, state is
ATTEMPT_CREATED, previous digest explicitly null, actor/reason equal the durable
authority owner/producer reason, and time equals attempt creation. Its 16384-byte
bound includes the reason. `validate_created` / `parse_created` accept no later
lifecycle or evidence format. The existing AUTHORIZED genesis is unchanged.

## Control-only schema

Two new tables:

- `recognition_runtime_execution_attempts`: immutable attempt identity/body/hash,
  authority ID and digest FKs, creation/expiry and unique deferred audit link.
  Attempt ID is primary; authority ID, body digest and audit sequence are unique.
- `recognition_runtime_execution_attempt_history`: immutable sequence-1
  ATTEMPT_CREATED event/body/hash, explicit null predecessor and deferred audit
  link; primary `(attempt_id, sequence)`, unique body digest and audit sequence.

Both authority FKs must identify the same row. SQL guards check header/body,
authority interval and AUTHORIZED genesis. Attempt and history reference one
future `runtime_execution_attempt_created` audit. Audit insertion requires the
complete matching attempt/history graph; missing audit cannot commit because of
deferred FKs. Immutable UPDATE/DELETE and BEFORE INSERT collision guards reject
REPLACE even with recursive triggers disabled. All collision keys are covered.
Reader validation recomputes canonical digests, complete body/index/audit equality
and FK integrity; SQLite CHECK expressions alone do not establish content hashes.

Uniqueness supplies a single-winner **storage invariant**, not permission to
create an attempt. Duplicate insertion fails; inspection can return existing
historical DATA without renewing it. Migration creates zero attempt/history rows.
No target table, legacy claim/history or existing authority body is modified.

## Read-only inspection

```python
inspect_attempt(control_path, attempt_id=..., authority_id=None)
```

The inspector receives only an absolute control path, opens URI mode=ro through
the existing `administration.connect()` helper, enables query-only and takes a
read snapshot. It never opens the target or key file. Exact schema, migration
chain, authority graph and all attempt records are validated before publication.

It returns deeply immutable DATA with status MISSING, MALFORMED, CONFLICTING or
VALID. VALID includes historical-only status, ATTEMPT_CREATED, immutable body and
body/event digests. Every result has `execution_authority=False` and
`retry_authorized=False`. Missing is not retry/adoption permission. VALID does
not assert that current activation/profile/authentication/dependencies still
match, that an authority is unexpired now, or that a genuine outer lifetime exists.
Expired or subsequently revoked historical records remain valid history.

Results expose no SQLite connection/cursor/transaction API and no local capability.
Malformed-store errors are classified without exception text or database contents.
Invalid lookup arguments fail validation. No public route or browser interface.

## Explicit local migration

Migration ID: `recognition-runtime-execution-attempt-storage-v1`.
API: `migrate(config, expected_generation=..., operator=..., reason=...)`.
The explicit CLI action is:

```powershell
python -B scripts/active/manage_recognition_administration.py `
  migrate-runtime-execution-attempt-storage `
  --target <absolute-target-path> --control <absolute-control-path> `
  --key-file <existing-key-path> --expected-generation <current-generation> `
  --operator <explicit-operator> --reason <explicit-reason>
```

This is a local trusted-host ceremony, not browser authentication. The key path
is configuration only: migration reads no administrative key contents. It requires
the existing complete profile/claim/authority storage prerequisites, exact current
generation, strict deployment control/target observations and metadata, and a
validated nonactive ledger (NOT_ACTIVATED or DEACTIVATED; not SUSPENDED, ACTIVATED
or recovery). It never changes those existing activation preconditions elsewhere.

Ordering follows existing 4e-12 migration:

1. Control BEGIN IMMEDIATE; validate exact control schema, history, scope and audit.
2. Target BEGIN IMMEDIATE, then query_only=ON. Validate strict target observations,
   complete schema fingerprint and installation/target/owner metadata. Perform
   integrity/FK preflight using separate existing read-only connections.
3. Under a control savepoint, install only the eleven recognized control objects
   and append one migration audit. Check the exact manifest/graph, zero new
   attempt rows, unchanged binding/target/schema and fresh monotone time.
4. Commit control while target remains query-only/reserved. Confirm commit ended
   the control transaction and target is still reserved; verify committed control
   integrity/FKs using a read-only connection. Only then release/rollback target.

There is no target DML, DDL or COMMIT. Query-only BEGIN IMMEDIATE is expressly
authorized by corrected 4e-18-R; it is a reservation, not attempt production.
No new transaction primitive or change to administration.transaction/_verify.

Matching installation is a validated no-op (`installed=False`), with no duplicate
audit. Stale generation, partial extension or incompatible schema fails before
installation; no repair. Errors during installation roll back the complete new
DDL/audit. Silent commits are rejected. Commit acknowledgement/cleanup failure
may leave the whole inert extension durable; no success is returned, no automatic
retry or adoption follows. Inspect the committed schema/metadata explicitly.

Generation, owner/profile, primary/session/step-up/confirmation/approval records,
authority bodies and existing audit rows are unchanged by installation. No
enrollment, reset, recovery or target schema transition is performed.

## Manifest compatibility

Fingerprint algorithms are unchanged. The full target fingerprint includes every
non-internal schema object and application_id/user_version; it remains identical.

The control chain is explicitly S0 (4d-1) -> S1 (4e-12) -> S2 (this extension).
The new transition validates all exact added definitions and a single typed audit
binding previous/current full manifests, historical installation/generation and
the earlier S1 audit. The old authority reader reconstructs its original S1 hash
only after validating S2; the old claim reader then reconstructs S0 as before.
No audit hash is rewritten and no unknown DDL is ignored. Exact base schema
validation detects table/trigger/audit-only partial extensions. This control-only
extension requires no target fingerprint or runtime enrollment change.

## Unchanged authority boundary and next slice

No producer API, live object or continuation exists. The 4e-15 result remains
inspection-only; authority DATA plus fresh authentication is not an original
coordinator. No WRITER_ADMITTED, mutation/commit/completion evidence, legacy claim
conversion, writer capability, readiness receipt or activation is introduced.
The next reviewed implementation boundary is **runtime coordinator/attempt
creation**, preserving the original pre-issuance outer lifetime and fresh
authenticated/reserved validation specified in 4e-17. This storage does not
authorize that implementation or replace its independently reviewed gates.

## Validation

Focused tests use existing disposable enrollment/auth/approval/authority fixtures.
Attempt INSERTs exist only in synthetic test graph/constraint helpers; they are
not runtime producers or a provider that can manufacture production authority.
Coverage includes malformed/canonical codecs, every transitive scope class,
expiry, immutable and deferred graph guards, duplicate/racing direct SQL identities,
read-only/sanitized inspection, unknown/partial manifests, populated historical
authority preservation, migration idempotence/races/rollback/uncertain commit,
and DELETE/WAL target-reservation and zero-target-write probes. Key reads are
explicitly denied in migration/inspection tests. No hosted resources are used.

Validation results:

- New focused file: 19 passed, 71 subtests passed (121.02 seconds).
- Final deterministic malformed-input test: 1 passed, 20 subtests passed.
- Authority schema/issuance dependencies: 49 passed, 170 subtests passed,
  1 failed (16713.28 seconds). The duplicate-issuance test accessed the first
  process-local authority after its inspection lifetime had expired, raising
  `issued_authority_expired`. Its isolated rerun passed (57.10 seconds).
  The aggregate failure remains recorded; expiry/locking behavior and the
  existing test were not changed. No WAL/disk-I/O failure was reported.
- `git diff --check`, new-file whitespace/final-newline checks and Python AST
  parsing passed.

No recognition/deployment-family or full-suite run was performed, as requested.

PRODUCTION AUTHORIZATION: BLOCKED

PRODUCTION EXECUTION: BLOCKED

PRODUCTION ACTIVATION: BLOCKED
