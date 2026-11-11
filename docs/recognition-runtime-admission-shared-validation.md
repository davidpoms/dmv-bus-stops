# Reservation-bound shared admission validation

This slice extracts validation authority only. It does not create or consume execution claims and does not grant execution, writer, readiness or activation authority.

## Why extraction was needed

The original 4d-0 collector resolved only a proposal transaction context. Its public
`revalidate()` opens and releases its own reservations, so its returned snapshot
cannot establish validation for a later control write. A claim context must not
be registered as a proposal context, and the checks must not be copied into a
second validator.

`runtime_admission_validation` contains the original collector and complete
snapshot comparison. `runtime_execution_admission` delegates to this kernel
inside its existing proposal reservation. Its public `assess()` and `revalidate()`
retain their historical, point-in-time DATA behavior, output format and digest.
Neither API is a live validation or execution capability. Future claim code must
use the reservation-bound kernel instead of either detached API.

## Opaque read contract

`proposal_read_view(context)` accepts only the existing registered proposal owner.
`claim_read_view(context)` accepts only the distinct registered
`runtime_claim_validation.ClaimValidationContext`. Neither accepts an arbitrary
connection, cursor, provider, callback, scope dictionary or 3a/approval context.
The resulting immutable `AdmissionReadView` exposes no SQL, handles, transaction
methods or writer interface. Existing authoritative readers use owner-private
connections internally; no raw connection is an input to the shared validator.

`validate(view, admission_snapshot, session_token, primary_token=...)` independently
repeats the complete validation and compares it with the original opaque 4d-0
snapshot. It returns `BoundAdmission`, whose data/digest accessors require the
same live reservation. There is no import, restore, pickle or detached factory.
Copied/exported JSON remains observation data and cannot be imported as authority.

## Separate owners and reservations

The claim-side scaffold is registration and read-only validation infrastructure
only. `validation_transaction(config)` has no claim insertion/consumption phase,
no target write phase, no caller-supplied authorization provider and no credential
issuance. It uses the existing ownership utilities with its own exact context
type and registry. The 3a, proposal and approval registries retain their types and
permissions. The shared scope reader dispatches claim views explicitly, including
authentication deadline registration, without registering them as another owner.

Both paths reserve control first with `BEGIN IMMEDIATE`, then reserve target with
`BEGIN IMMEDIATE` and enable `query_only`. Owner PID, Thread object and identifier,
active lifetime, phase, denial/poison state, exact connection objects and both
transactions must remain valid. A borrowed admission view additionally pins the
target change count, control and target reservation epochs, and checks query-only
remains enabled. Epochs are observation metadata on the existing owner: an authorized
transaction release/reacquisition or query-only protection change invalidates earlier admission views even
if the same connection is again in a transaction. It changes no SQL permission
or persistence sequence. Unauthorized lifecycle/SQL attempts still poison the
owner through its existing authorizer.

The kernel never commits, rolls back, opens another transaction or releases a
reservation. Control finalization remains manager-owned, with target held through
control commit and target rollback/release afterward. No claim write is added.
Future acquisition must invoke this kernel before its bounded insertion and again
before its manager commits; this slice does not implement that future protocol.

## Checks retained

The extracted collector preserves the original ordered checks:

- Current runtime profile, installation, generation, target, owner, authentication
  epoch and MFA epoch through the existing runtime/scope readers.
- Existing primary/session validation and profile links, with unchanged expiry,
  revocation, throttling and verified-denial behavior.
- Exact current versioned approval, approval digest/history and proposal reference;
  the original confirmation and step-up provenance/consumption remain historical
  approval evidence, with unchanged approval semantics.
- Exact durable proposal graph and acknowledgement, operation format/digest,
  execution storage prerequisites, frozen preparation and dependencies.
- Existing dependency recheck (`READY` with no reasons), supported family,
  `finalize` action, atomic accounting policy and whole-population manifest
  regeneration/equality using the existing read-only preparation helper.
- Authoritative emergency-stop reader and operation execution-block lookup.
- Actual target schema and hostname/path/device/inode, actual control physical
  identity, fresh session/current operation-target scope and trusted UTC time.

The comparison includes every original snapshot field. Only `checked_at_utc`
may advance, and it must not move backward; this is the existing 4d-0 rule.
There is no normalization, scope refresh, regenerated approval/ACK or dependency
replacement. The original admission object is not replaced by the bound result.

Existing authentication deadlines accumulate on the owner and are checked again
before manager commit. Bound-result access also checks those recorded deadlines;
it cannot extend their lifetime. Authentication rejection may perform only the
existing verified denial reductions/audit under the owner's unchanged rules.
Successful validation performs zero control and target writes.

## Tests and authority fences

The focused tests exercise the real 2c → 3a/3b → 4a/4b → 4c → 4d-0 lifecycle
through both owner registrations. They compare complete canonical output/digests,
inject changed fields only after the real collector runs, and independently test
durable approval invalidation, stop, dependency, physical/schema and proof changes.
They also test owner separation, opaque interfaces, PID/thread/lifetime, connection
replacement, transaction release/reacquisition, query-only/lifecycle violations,
authentication deadlines, final commit ordering and read failures.

DELETE and WAL are covered for read-only successful validation and reservation
loss/lifecycle failure. Disposable claim-schema installation is used only to prove
both new claim tables remain empty; this slice changes no schema. Whole-store
before/after snapshots and connection change counts verify successful validation
does not modify populated authentication, approval, operation or target records.

No routes, CLI changes, key-content reads, target DML, legacy execution changes,
claim acquisition, writer capability, readiness receipt or activation are added.
Production remains `NOT_ACTIVATED`; ordinary v3 administration remains blocked by
`runtime_profile_contract_not_enabled` and existing downstream gates remain intact.
