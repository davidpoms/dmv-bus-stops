# Slice 4e-19-S: coordinator-owned admission and private issuance

Implements the original private continuation defined by
[4e-19-R](recognition-runtime-authority-coordinator-continuation-contract-4e-19-R.md).
It does not create ATTEMPT_CREATED or grant writer/execution authority.

## Original owner and entry

`runtime_execution_coordinator.coordinator(config, session_token,
confirmation_token, approval_id, *, primary_token, approval_sha256, reference,
activation_sha256, reason)` is a trusted in-process context manager. No route,
CLI, callback/provider, authority loader or adoption API is added. Lookup fields
are expectations checked against authoritative storage, not replacement scope.

The opaque `CoordinatorContext` is registered before fresh issuance. Its private
outer state retains exact PID, Thread object/identifier, original paired clock,
originating credentials/deadlines, immutable canonical subject, activation and
scope. A separate `CoordinatorAdmissionContext` owns each reserved phase and
binds exact connections, private phase identity and both reservation epochs.
It never registers as a 3a, proposal, claim, consent, activated or issuer context.
No SQL handle, cursor, lifecycle or writer method is exposed.

## Reused validation and protected readiness

The exact coordinator adapters in `runtime_scope_validation` and
`runtime_admission_validation` reuse current authentication/runtime-auth scope,
v2 approval/history, proposal/ACK, dependencies, fixed-policy whole-manifest
regeneration, emergency-stop and physical observation readers. The issuer's
`_subject_for_owner()` is a fixed exact-owner shared kernel, not a supplied
validator or provider. The original issuer `_subject()` remains its own wrapper.

Existing identity/history helpers and `require_activated()` validate the enrolled
profile, installation/target UUIDs, generation, binding, owner, auth/MFA epochs,
strict hostname/path/device/inode/schema and exact activation incarnation and
consumed confirmation. No boolean substitutes for activation. Complete existing
claim/recovery and runtime proposal inventory still applies; when attempt storage
is installed, any existing incomplete attempt blocks this pre-attempt boundary.
No selected-attempt exception or target-schema transition is implemented.

`local_readiness._assess_coordinator()` resolves only the exact coordinator phase
and invokes the existing protected inventory/key verification internally. The
cipher/seed/ciphertext does not cross that interface. It returns nonserializable
immutable readiness evidence whose canonical DATA accessor checks its original
owner, phase, connections, reservation epochs, scope and deadlines. The issuer
copies those canonical DATA internally. Evidence is invalid after phase exit.
Every finalization/reacquisition recomputes protected readiness; a stored hash or
old evidence object is never permission to skip verification.

Successful validation/inspection performs zero writes. Established authentication
denial/revocation reductions use the existing private denial facade and
`_denial_safe()` rules. They may commit only their existing safe control-only
changes after independent final checks while target stays reserved. Rejection
is not swallowed and produces no continuation. Unsafe scope/history failure
does not authorize arbitrary denial writes.
Owner-access loss detected by the existing strict `_identity_snapshot()` gate
before authentication remains a zero-write rejection; it does not force new
revocation effects or move that established boundary.

## Private issuance and transaction ordering

```text
original outer owner
  -> control BEGIN IMMEDIATE / exact history
  -> target BEGIN IMMEDIATE / query_only=ON
  -> exact coordinator phase/view registration
  -> fresh admission / auth / protected readiness
  -> issuer._issue_for_coordinator(exact_phase, confirmation_token)
  -> fixed consent CAS, consumption audit, authority, genesis, issuance audit
  -> fresh final validation / graph / protected-state checks / paired time
  -> manager control COMMIT, target still reserved
  -> invalidate phase views; target rollback/release and connection cleanups
  -> one private continuation retained by original outer owner
```

The target BEGIN IMMEDIATE is the approved query-only reservation from 4e-17,
not a write-enabled target phase. Target query-only is never disabled; target
DML/DDL/COMMIT is absent. No schema or fingerprint algorithm changes.

The private issuer receives the already-registered coordinator admission context
and borrows its reservations. It does not invoke public `issue()`, open another
issuer transaction or manufacture an `IssuedAuthority` inspection object.
It validates original consent and rejects any preexisting authority for the
operation/manifest. The existing fixed `_persist()`/`_final_mutations()` kernels,
approved authority/AUTHORIZED formats and five-write protocol remain unchanged.

A pending immutable notice binds the actual issuing state, phase identity,
connections/epochs and authority digest. It is not a continuation. `_promote()`
requires confirmed control commit and both successful cleanups, exact notice
identity and original active outer lifetime. The private `_Continuation` is
stored only in the original owner's registry. No public authority result, JSON,
lookup ID, forged object, new process or later login can reconstruct it.

## Inspection and lifetime

The yielded owner has an immutable `snapshot` inspection property. It reopens
a fresh control-first/query-only-target phase, reloads the exact durable authority
and original consent artifacts, revalidates all current facts and compares the
complete canonical subject. Only historical safe DATA is returned, explicitly
`execution_authority=False` and `retry_authorized=False`. It is not a serialized
continuation. The internal continuation itself is not exposed or consumed here.

Expected manager commit/cleanup destroys borrowed phase views. It does not
pretend a transaction remains held after cleanup. In the reservation gap the
outer continuation is inert provenance; every use requires fresh authoritative
validation. No permanent reservation or validation-gap exception is introduced.

Original authority/primary/session/consent deadlines accumulate on the outer
owner and never renew. The original paired clock detects rollback/anomaly;
`now >= earliest deadline` rejects. PID/thread mismatch, phase/connection/epoch
replacement, rollback, stale authentication, changed activation/profile/
generation/installation/target/owner/auth/MFA scope, changed proposal/ACK,
approval/dependencies/stop or invalid readiness rejects and poisons use.
Outer exit clears credentials and removes the continuation and registrations.
Restart cannot recreate the original process-local lifetime.

## Duplicate, crash and uncertainty behavior

The control reservation, existing authority UNIQUE keys and confirmation CAS
select at most one fresh issuer for an operation/manifest. Repeated private
issuance in the same phase rejects; another coordinator cannot adopt an existing
authority. Established bounded BUSY/LOCKED rejection is preserved without retries.
Public `issue()` remains unchanged and inspection-only, including duplicates.

Before confirmed commit, failure rolls back pending control effects. If commit
is uncertain or silent, no continuation is published. Confirmed commit followed
by either cleanup failure or partial continuation-publication failure also
publishes no live result. A durable authority can remain and is inspection-only.
Use the existing trusted `inspect_issuance()` read-only ceremony; exact/absent/
conflict/unknown inspection does not authorize retry, adoption or renewal.
No new recovery behavior, audit action or durable uncertainty record is invented.

## Validation and boundary

Focused tests use real disposable enrollment/authentication/ACK/v2 approval/
consent/issuance fixtures and synthetic scoped activation ledger DATA. Inert
attempt storage is installed before fixture activation solely to verify zero
attempt creation. Tests do not create any attempt graph or provider that can
manufacture production authority. Fault/observation wrappers preserve the real
validators rather than substituting unconditional success.

Validation in the guarded disposable environment:

- Targeted identity, readiness, WAL, commit/cleanup and publication probes:
  8 passed, 14 subtests passed.
- Standalone no-provider owner fence: 1 passed, 2 subtests passed. The full
  coordinator run also covers this fence, including continuation lookup.
- Final implementation's coordinator-file run: 37 passed, 40 subtests passed,
  1 failed new test expectation. That test incorrectly expected revocation after
  owner-role loss, although the existing strict identity gate rejects before
  authentication. The new test was corrected to require that exact rejection
  and unchanged control/target state, then rerun alone: 1 passed. No implementation
  change followed that full-file run. All 38 coordinator cases are therefore
  verified across the full and corrected isolated runs; a separate wholly green
  full-file rerun after the test-only correction was not performed.
- Requested existing authority issuance, owner consent and activated-owner
  regression files: 65 passed, 111 subtests passed.
- `git diff --check`, new-file whitespace/final-newline checks and Python AST
  parsing passed. No full or recognition/deployment-family suite was run.

Earlier development test-data errors (an identity value equal to the fixture's
real UUID, an incorrect target field name and an incorrect legacy audit table
name) were corrected in the new tests, without loosening existing checks.
One pre-hardening in-flight test run was interrupted and is not a milestone
result. No SQLite retries, clock grace or authority expiry changes were added.
No hosted/production resources or real deployment keys were accessed. Existing
tests use disposable fixture databases/keys. No commit or push was performed.

No writer admission/capability, target entry, execution, target mutation,
completion/seal/receipt, legacy claim/EXECUTING/recovery, readiness enablement or
activation is implemented. Existing gates and legacy formats are unchanged.

The next independent boundary is **4e-19-T: inert ATTEMPT_CREATED creation using
the coordinator continuation**. This implementation does not authorize it.

PRODUCTION AUTHORIZATION: BLOCKED

PRODUCTION EXECUTION: BLOCKED

PRODUCTION ACTIVATION: BLOCKED
