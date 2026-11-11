# Slice 4e-19-T: inert coordinator-owned ATTEMPT_CREATED creation

This slice implements only the control-side creation transition authorized by
[4e-17](recognition-runtime-live-attempt-storage-writer-contract-4e-17.md),
[4e-18-R](recognition-runtime-execution-attempt-storage-slice-4e-18.md) and the
[original coordinator contract](recognition-runtime-authority-coordinator-continuation-contract-4e-19-R.md).
It uses the private original-issuance continuation implemented in
[4e-19-S](recognition-runtime-authority-coordinator-continuation-slice-4e-19-S.md).
No schema or durable codec changes are introduced.

## API and original provenance

Inside the original `runtime_execution_coordinator.coordinator(...)` lifetime,
call `owner.create_attempt()` with **no arguments**. There is no authority import,
attempt-ID override, replacement scope, public-result conversion, web route or
lookup/adoption path. The coordinator exists before private authority issuance.
Its exact registered continuation proves the original confirmed issuance and
cleanup. Public `issue()` results and historical authority/attempt data cannot
establish this provenance.

The original owner marks the continuation spent before opening the creation
phase. A failed or uncertain creation permanently poisons that owner; absence
of a durable attempt does not authorize retry. Another coordinator cannot adopt
the already-issued authority. No additional issuance or repeated consent occurs.

## Fresh authoritative checks

Creation uses the same original credentials, paired wall/monotonic clock and
original deadlines. Exact registered owner, PID, thread object/identifier,
context lifetime, phase, connection identities and reservation epochs are checked.
The existing admission collector, subject assembly, protected readiness,
authentication, current v2 approval, proposal/ACK, dependency/manifest, activation
and physical-identity kernels are reused, not replaced by supplied validators.

The complete current subject must equal the original canonical subject. The
durable authority body and digest must equal the private continuation, with its
original AUTHORIZED genesis, owner-consent artifacts and original expiry.
Validation covers installation, target, profile, generation/binding, owner/access,
auth/MFA epochs, originating primary/session records, activation incarnation/event,
approval/history, proposal/ACK, dependencies, inactive emergency-stop head,
readiness/rehearsal, physical observations and schema. Existing selected claims,
legacy conflicts and other incomplete attempts remain blockers. No TTL, consent
deadline or authentication expiry is renewed.

## Reservation and persistence sequence

1. Validate the genuine outer owner and original private continuation; mark its
   one creation invocation spent.
2. Acquire control `BEGIN IMMEDIATE`; validate exact schema/history.
3. Acquire target `BEGIN IMMEDIATE` reservation and set `PRAGMA query_only=ON`.
   This is the approved writer-excluding reservation, not a write-enabled phase.
4. Establish exact phase/connection/epoch ownership and perform fresh checks.
5. Require the existing inert attempt-storage installation. Generate a random
   canonical UUID with `uuid4()`; build and validate the exact six-field attempt
   codec against the durable authority. Creation is current canonical UTC;
   expiry equals the original authority expiry, and creation must precede it.
6. Insert exactly one immutable attempt, its sequence-1 `ATTEMPT_CREATED` event
   and `runtime_execution_attempt_created` audit, with one shared deferred audit
   sequence. The existing authority body/AUTHORIZED history remain unchanged.
7. Repeat fresh admission/subject/authority/expiry checks while **both**
   reservations remain held. Verify the entire attempt/history tables contain
   exactly this phase's expected graph, full canonical/FK/audit validity, exactly
   three control changes and unchanged protected authentication records. This is
   an exact pending-graph check, not an exclusion of a selected operation from
   inventory. No preexisting attempt is eligible for it.
8. Sample the original deadlines; manager commits control while target remains
   reserved. Invalidate phase views/epochs, release target by rollback, and close
   both connections through the existing ownership cleanup.
9. Publish a result only after confirmed commit and successful cleanup, bound
   to this exact original owner, continuation, creation phase and authority.

The creation-only SQLite authorizer admits INSERT into exactly the two attempt
tables and admin audit during the fixed private persistence function. It grants
no caller SQL API. It does not allow UPDATE, DELETE, REPLACE or later lifecycle
states. Existing Slice S authenticated-denial handling is unchanged: before any
attempt mutation, only its established independently validated control-only
denial reductions may commit. An incomplete insertion or failed final check
cannot satisfy that denial finalizer and rolls back the attempt transaction.

## Result, duplicates and uncertainty

`CreatedAttempt` has no public constructor and cannot be pickled/restored. Its
read-only `snapshot` returns deeply immutable historical inspection data with
`state=ATTEMPT_CREATED`, exact attempt/event digests,
`execution_authority=False` and `retry_authorized=False`. It contains no raw
credential, key, SQL handle, cursor, connection or writer method. Access requires
the same active unpoisoned PID/thread/original owner and its original deadlines;
context exit clears the private result registration. A fresh process cannot
recreate it from JSON or durable rows. The result is not a current-admission or
execution credential.

Only one attempt per authority is permitted by the immutable storage UNIQUE
constraints. Control reservations serialize competitors; an existing attempt
blocks before insertion. Identical existing data and different IDs are not
adopted. Repeated calls on one owner fail even when the first call failed.
Independent historical `inspect_attempt()` remains read-only DATA; it never
renews expiry or returns a live result. Established BUSY/LOCKED errors remain;
there is no new retry, busy-timeout, checkpoint or recovery workaround.

Before-commit failures roll back uncommitted creation writes and release the
target reservation. Raised/silent/unconfirmed commit, cleanup failure or failed
result publication yields no usable result. Commit may nevertheless have made
the complete graph durable; inspect durable state explicitly. Never retry,
reconstruct/adopt provenance, infer success from process memory, delete a winner
or release uniqueness. After restart only durable history remains authoritative.

## Explicit downstream stop

Only `ATTEMPT_CREATED` is stored. Authority lifecycle remains AUTHORIZED, with
attempt uniqueness fencing reuse. No WRITER_ADMITTED, TARGET_MUTATION_STARTED,
target entry/commit/seal, failure, completion or recovery transition is created.
No target INSERT/UPDATE/DELETE/DDL/COMMIT occurs. No writer capability/admission,
execution, readiness receipt, activation transition, legacy claim/history or
4d claim/handoff reinterpretation is added. All deployment/private-key behavior
remains inside existing protected readiness; this slice exposes no key material.

The exact next boundary is **runtime writer-admission contract/implementation**.
That requires separate review; the inert result is not accepted by current
writer or execution entry points.

## Validation

Tests use the real guarded disposable enrollment/authentication/proposal/ACK/
approval/consent/coordinator lifecycle with scoped synthetic activation fixtures.
No hosted resources or production database are involved. Focused creation tests
and the three requested coordinator/storage/issuance regression files are run;
the full suite and recognition/deployment family are deliberately not run.

Focused validation verified all 40 current cases across runs. The initial full
file run had 30 passes, 10 passing subtests and nine setup failures. The first
failure was a pre-creation authentication deadline in the existing nested
fixture; it passed alone (1 pass). Failed setup had left fixture patches active,
causing the following setup failures. The new test harness now registers cleanup
before setup and unwinds partially initialized nested fixtures, with a dedicated
no-database regression. The eight affected cases plus that regression passed
together (9 passes). No runtime security implementation or expiry semantics were
changed to address the setup failures. A clean single full-file rerun is not
claimed; only affected cases were rerun, as required by the validation policy.

The requested three-file regression run initially had 34 passes, 35 passing
subtests and 42 setup failures. The first was `authority_consent_expired` in the
existing coordinator fixture before its test body; subsequent setup failures
were `operation_target_mismatch` after nested fixture patches remained active.
The first case passed alone (1 pass, 5 subtests). Only affected cases were then
run in fresh guarded processes stopping on the first failure: the other three
coordinator cases passed; all 19 attempt-schema cases passed with 71 subtests;
all 19 authority-issuance cases passed with 36 subtests. Thus all 76 requested
regression cases and 147 subtests were verified across runs. No existing
regression file, production deadline, identity comparison or authentication
primitive was changed. A clean single combined regression run is not claimed.

`git diff --check`, AST parsing and final-newline/trailing-whitespace checks for
the three slice files passed. No full suite or recognition/deployment-family run,
hosted/production access, real deployment-key access, commit or push occurred.

PRODUCTION AUTHORIZATION: BLOCKED
PRODUCTION EXECUTION: BLOCKED
PRODUCTION ACTIVATION: BLOCKED
