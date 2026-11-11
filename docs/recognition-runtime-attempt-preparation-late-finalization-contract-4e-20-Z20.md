# 4e-20-Z20: attempt preparation and late-finalization ownership contract review

## 1. Z19 measured constraint

[Z19](recognition-runtime-authority-bound-lifecycle-redesign-decision-4e-20-Z19.md)
retains the 120-second ceiling and rejection of the measured composition. Z18
measured issuance/admission at 80.302s, including 35.356s issuance finalization.
Attempt creation then took 84.405s, including 35.328s attempt finalization, and
failed with `administrative_session_expired_or_revoked` at zero authority budget.
Metadata entry was not reached. Nested durations are not additive. No exclusive
measurement identifies a large pure-construction cost that could simply move.

**Decision: the requested replacement late-finalization contract is incomplete.**
A safe non-authoritative intent boundary can be described, but no existing
contract authorizes moving the expensive mutable validation results into it.
All proposed restructuring below is review material, not an implementation grant.
Do not implement a new owner, codec, schema, state or reusable predicate from it.

## 2. Definitions

**Preparation is evidence, not authority.** Attempt preparation would mean pure
prospective intent computation in the original live issuance ceremony, before
authority construction. It is not an attempt, permission decision, readiness
receipt, reservation lease, validation certificate or continuation.

An already-frozen operation reference may describe intent; it cannot establish
that operation's current eligibility. Z15's schema inventory remains the only
approved reusable observation, and only inside its exact issuance phase.
No additional prepared field set, record template or codec is approved here.

No durable preparation is selected. It creates no attempt ID, authority-dependent
digest, creation timestamp, expiry, history/audit record, claim, target entry or
executable state. In particular, it cannot create `ATTEMPT_CREATED`.

The existing `ATTEMPT_CREATED` result itself is inert, not an executable attempt.
There is no approved operation that converts preparation into an executable
attempt or grants writer/execution authority.

## 3. Ownership

The only candidate owner is a private subordinate of the original coordinator's
issuance-phase admission context, while its original control and target
reservations remain held. It must not be another transaction primitive or a
compatible-looking adapter. Its creation point, API and exact new representation
remain UNRESOLVED; Z14 defines only the implemented inventory preparation owner.

Required constraints for any future design: opaque, no public constructor,
nonserializable/noncopyable/non-adoptable, original PID/exact Thread/context/phase
identity, exact paired clock, original connections/transactions/reservation epochs,
and no exposed SQL, cursor, connection or commit/rollback capability.
Process, thread or context change must invalidate it, not transfer ownership.

## 4. Binding

Any proposed intent must originate from authoritative readers inside the original
ceremony, never replacement caller scope. The review must bind the exact operation
and manifest, proposal/ACK, approval, original credentials' scope and auth/MFA
epochs, finalized G+2 installation/generation/profile/binding/owner, independent
activation incarnation, consent artifacts/reason, code/schema policy, original
owner and reservation lineage, and applicable deadlines.

These are required comparison dimensions, not a newly approved record format.
The exact minimal field/predicate set and validation rules for a new preparation
object are **UNRESOLVED**. A digest alone neither proves origin nor closes TOCTOU.
No preparation contains the later authority digest: that body does not yet exist.

## 5. Preparation lifecycle

If eventually approved, construction must publish internally only after complete
success. It has no independent TTL, durable checkpoint or cleanup exemption.
It expires with its original phase and earlier credential/consent deadlines.
It cannot survive commit, rollback, connection replacement, reservation loss,
epoch/mode change, owner exit, poison, clock anomaly, process/thread change or
uncertain cleanup. Destroy eligibility on success, failure and uncertainty;
dropping an object does not promise physical erasure of Python memory.

Auth, activation, approval/ACK, stop, physical identity, dependencies or current
history/control/claim changes must reject stale intent through fresh readers.
There is no universal change notification or continuity witness to invent here.
No automatic retry is authorized. Failure cannot revive the object. Starting an
entirely new explicit ceremony, where existing durable exclusions permit it, is
not adoption or a retry of the spent original continuation.

## 6. Fresh-validation matrix

| Work/predicate | Permitted before authority? | Reusable in finalization? | Required final behavior |
| --- | --- | --- | --- |
| Existing frozen operation intent | May inspect as data | Not a current eligibility result | Exact current operation/manifest and scope checks |
| Schema inventory | Yes through Z15 | Only exact original issuance-phase continuity; not into attempt/metadata | Fresh eligibility/physical checks; existing attempt-local Z7 only in its own phase |
| Migration validation/relationships | May inspect under existing readers | NO | Fresh migration rows, ordering, binding and transition validation |
| Runtime profile/enrollment | May inspect | NO additional reuse approved | Fresh finalized G+2/profile/generation/install/owner continuity |
| Claim-local integrity/current claim graph | May inspect | NO additional reuse approved | Fresh current graph, disposition and exclusions |
| Authentication/consent | Required live during preparation | NO | Fresh scope, revocation, epochs, time and all earlier expiries |
| Activation | May inspect | NO | Fresh exact independent incarnation |
| Proposal/ACK/approval | May inspect | NO | Fresh exact pairing, digest and invalidation |
| Dependencies/readiness/stop | May inspect through existing read interfaces | NO | Fresh decisions at every currently required boundary |
| Physical identity/schema/fingerprint | Required actual observations | NO physical continuity guarantee | Repeat actual checks; SQL reservation is insufficient |
| History/audit/control | May inspect | NO complete reuse | Fresh current state and actual post-write graph/audit/FK checks |
| Target reservation | Existing original issuance owner may hold it | Not transferable | Each phase proves actual connections/transactions/epochs |
| Target write mode/DML/DDL/commit | NO | N/A | Preparation remains query-only and nonmutating |
| Unspecified construction or observation | UNRESOLVED | NO | Do not move it |

Preparation may perform schema reads, migration validation and readiness
inspection, but permission to read is not permission to reuse the result.
Schema inventory preparation does not establish migration validity.

## 7. Finalization ownership

Current authoritative producer:
[`runtime_execution_coordinator._create_attempt()`](../src/review/recognition/runtime_execution_coordinator.py)
spends the genuine original continuation, opens its fresh attempt `_phase()`,
calls `_persist_attempt()`, completes `_finish()`, then `_publish_attempt()` only
after confirmed control commit and both connection cleanups.

`_persist_attempt()` requires the existing durable authority and current admission.
[`runtime_execution_attempt_schema`](../src/review/recognition/runtime_execution_attempt_schema.py)
binds the attempt to authority ID/digest, timestamps and scope. Its immutable
body/history cannot be prepared with invented placeholders or retroactively bound.

Under current contracts this owner alone creates the inert attempt after issuance.
No new conversion operation is specified. A proposed late finalization owner or
combined issuance/attempt transaction is **UNRESOLVED**, not silently delegated
to the preparation object. Fresh checks cannot be replaced with its `valid` flag.

## 8. Atomic boundary

Current attempt/history/audit insertion is atomic within its manager-owned control
transaction. Control reservation precedes target reservation; target stays
query-only and reserved through control commit. Preparation has no commit.
The existing issuance CAS/five-write transaction and subsequent attempt
three-insert transaction are separate. There is no cross-database atomicity.

Moving attempt insertion into issuance, moving authority issue time past existing
finalization, or eliminating the fresh attempt phase requires a new explicit
owner/write-set/post-write-predicate contract. Neither an original outer context
nor identical hashes proves equivalent transaction ownership. No such change is
approved here.

## 9. Crash and uncertain commit

Before authority: discard volatile preparation on death/failure; no durable state
or live handoff remains. During issuance: preserve existing CAS/rollback and
confirmed-commit/cleanup requirements. After issuance: the original authority's
clock continues; it is never restarted by preparation or publication.

If authority expires before finalization, reject and publish no usable result.
If attempt commit is uncertain, poison the original owner, discard preparation,
and permit only existing durable read-only inspection. Do not infer rollback from
an absent result, reconstruct capability from rows, automatically retry, or adopt.
A hypothetical new combined transaction needs every durable crash prefix
specified before implementation; current finalizers cannot be assumed to cover it.

## 10. Duplicate and concurrency handling

Do not introduce durable preparation uniqueness or a new logical-attempt lock.
Pure intent cannot exclude another actor by itself. Original manager reservation
ordering and fresh durable authority/operation/manifest exclusions remain required.
Existing attempt uniqueness includes authority ID; `_create_attempt()` spends its
original continuation even if creation fails. Two prospective preparations cannot
grant two winners or allow a failed winner to regain a continuation.

An exact duplicate is not permission to reuse an old live handle. New construction
must check existing durable exclusions; uncertainty requires inspection, not a
loop. Any proposed new durable preparation race policy remains UNRESOLVED.

## 11. Adoption prohibition

No JSON, pickle, ID lookup, browser claim, file, signed digest, reauthentication,
matching scope, provider callback or process restart can recreate a preparation
owner or original continuation. New credentials cannot extend an old authority.
No second ceremony is selected. Inspection of historical data stays inspection.

## 12. Options A-D

| Option | Security validity / existing permission | TOCTOU and adoption risk | Crash/uncertainty | Duplicate/concurrency | New contract needed |
| --- | --- | --- | --- | --- | --- |
| A: in-memory | Existing Z15 inventory only; new intent object UNRESOLVED | Must not carry current allow decisions; same outer does not preserve a phase | Discard, no durable resume | Reservations and durable exclusions, not object identity | Exact additional payload, owner, invalidation and consumption predicates |
| B: durable non-authoritative record | Not defined or selected | Durability encourages adoption; a label does not prevent it | Surviving record must remain historical and non-resumable; cleanup/retirement undefined | Durable uniqueness/write policy undefined | Schema, reader fences, retention, audit, crash prefixes and explicit non-adoption policy |
| C: preparation then late ATTEMPT_CREATED | Pure intent can conceptually precede authority; no approved useful expensive predicate movement | Authority-linked body must be constructed afterward; actual row checks remain fresh | Existing finalization retained unless separately reviewed | Existing single-winner constraints remain mandatory | Exact movable work and proof that later insertion preserves every predicate |
| D: separate short finalization transaction | Current attempt phase exists but is not insertion-only or demonstrated short | Reacquisition invalidates prior observations; cannot import a cached allow decision | Preserve original continuation and unknown-commit fences | Original continuation spent once; no reconstruction | Any changed owner/order/continuity and exact post-write proof |

B is not justified: no need for durable preparation has been established and it
would require new schema and adoption policy. A is the preferred representation
only if a later review identifies a permissible payload. C/D are not permission
to reduce finalization to INSERT plus COMMIT. Feasibility of every replacement is
UNMEASURED.

## 13. Security and TOCTOU

The original ceremony is necessary but not sufficient for continuity. Time can
expire under both reservations. Physical identity can change outside SQLite.
Issuance changes confirmation use, authority population and audit history; attempt
insertion changes the current graph again. Those facts must be freshly validated.
Readiness inspection is not readiness authority. A prospective record template
cannot authenticate actual rows, global exclusions, audit suffix or trigger effects.

No automatic invalidation authority covers all mutable predicates. Any future
reuse proposal must enumerate exact source/predicate, binding, permitted intervening
writes, invalidation and use boundary. If any is unspecified, do not move it.
This review supplies no wider continuity mechanism than Z15.

## 14. Minimum authority-bound work

The authority window begins at actual immutable `_body()` issue time after CAS.
It still includes issuance post-write fresh validation, exact five-write graph,
confirmed control commit and cleanup, original continuation promotion, fresh
attempt admission/binding/expiry, actual attempt/history/audit construction and
validation, confirmed attempt commit/cleanup, and every metadata admission, mode,
target-commit, reacquisition and post-commit validation required by the current
path. Earlier credential/consent deadlines may shorten the window.

No measured exclusive lower bound shows that only pure construction dominates.
No contract makes those live checks preparable. The 35.356s and 35.328s measured
finalization spans are observations, not guaranteed minimums. Metadata remains
UNMEASURED. A short final commit and complete 120-second lifecycle cannot be promised.

## 15. Exact implementation boundary

**No replacement implementation is authorized.** The missing contract is an exact
predicate-level decomposition of proposed attempt intent versus live admission,
with a useful movable payload, and a late-finalization ownership/write-set proof
compatible with authority-linked immutable attempt fields and current phase
commit/publication rules. In particular, moving claim/profile/history or migration
validation would require its own explicit continuity contract; Z15 does not supply it.

Before a new owner could be implemented, that review must resolve the payload,
creation/consumption points, no-authority proof, actual post-write verification,
phase/transaction ordering and all uncertainty/race outcomes. If no expensive
predicate can move without weakening freshness, retain rejection and return to an
explicit architecture decision. Do not fill the gap with another cache, ceremony,
timestamp shift, lifetime extension or blind optimization.

## 16. Non-authorization and validation

This document neither creates nor authorizes creation of preparation objects,
authorities, attempts, target entries, writer admission or execution capability.
It changes no ownership, schema, authentication, activation or lifetime policy.
No runnable replacement satisfying the requested expensive-work relocation is
currently contractually defined. The safe inventory-only boundary already exists;
it is not a newly sufficient solution.

Validation is `git diff --check` and this document's whitespace/local links only.
No pytest, Z18, T, broad suite, code/schema/migration, hosted/production access,
commit or push.

PRODUCTION AUTHORIZATION: BLOCKED

PRODUCTION EXECUTION: BLOCKED

PRODUCTION ACTIVATION: BLOCKED

WRITER CAPABILITY: BLOCKED
