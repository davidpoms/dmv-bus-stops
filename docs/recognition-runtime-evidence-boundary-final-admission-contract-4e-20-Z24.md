# 4e-20-Z24: evidence boundary and fresh final admission

## 1. Z23 decision and result

[Z23](recognition-runtime-replacement-security-contract-4e-20-Z23.md) recommends
evidence-only preparation followed by fresh final consent/admission as a design
direction, not an approved replacement owner or reusable payload. This review
concludes **B. New security rule required**. The exact useful retained payload
and replacement finalization ownership cannot be derived from current contracts.
No implementation, authority, attempt or executable transition is approved.

**NO ADDITIONAL CROSS-BOUNDARY EVIDENCE IS AUTHORIZED.**

This does not authorize existing schema inventory to cross the proposed boundary
either. Z15 inventory is usable only within its original issuance phase; Z7 is
attempt-local. A later fresh-authentication/final-admission context must obtain
its own current observations. A common outer ceremony or unchanged content digest
does not preserve a prior reservation, connection, transaction or epoch.

## 2. Preparation payload, field by field

There is no approved new retained payload/format. The exact current Z15 `_Facts`
fields below are inspected to establish the limit, not repurposed as an exported
envelope. Source:
[`runtime_issuance_schema_inventory.py`](../src/review/recognition/runtime_issuance_schema_inventory.py).

| Field/evidence | Source | Immutable? | Scope binding | Lifetime | Invalidation | Safe across proposed boundary? |
| --- | --- | --- | --- | --- | --- | --- |
| `preparation` | Private `_mint` token | Opaque identity | Exact original registered state | Issuance phase only | Owner/phase termination or discard | NO |
| `owner`, `context`, `phase` | PID, exact thread/ident, outer/context/phase | Captured references, not immutable live validity | Original ceremony | Same phase | Any ownership/lifetime change | NO |
| `connections`, `epochs` | Bound actual connections/reservations | Captured tuple only | Original paired transactions | Same phase | Commit/rollback/replacement/epoch change | NO |
| `snapshot_json`, `subject_json` | Canonical original authoritative scope/subject | Captured content immutable | Exact operation/install/profile/generation/owner/activation scope | Same phase | Changed current scope or phase | NO current eligibility may survive |
| `credential_scope` | Existing private credential/scope digest | Captured digest immutable | Original credentials, approval/reference/activation/MFA | Same phase | Credential/scope/epoch change or expiry | NO; not authentication |
| `consent_json` | Validated original consent artifact | Captured canonical content | Original subject and artifact | Original phase and all earlier deadlines | Changed/used/expired artifact, phase exit | NO; not renewed consent |
| `objects` | Control `sqlite_master` names and SQL definitions | Captured inventory immutable | Exact original owner/schema/code/transactions | Same phase only | Failed continuity, DDL/unexpected writes/phase change | NO across boundary; YES only existing Z15-local use |
| `physical` | Actual control/target identity observations | Captured baseline only | Exact original paths/host/devices/inodes | Comparison baseline within phase | Actual mismatch or phase change | NO; must reobserve even within reuse |
| `definition_code` | Existing schema definition function/code identities | Captured tuple | Original code/schema policy | Same phase | Definition/code policy mismatch | NO approved transport |
| `control_changes`, `target_changes` | Original connection counters | Captured integers | Same exact connections/write baseline | Same phase | Unclassified mutation or transaction/phase change | NO; not a complete mutation proof |

Migration audit/relationships, predecessor ordering, transition/profile continuity,
readiness, history/claim/control validity, dependency validity and physical
continuity are not part of reusable schema evidence. Observing them during
preparation does not authorize retaining their allow decisions.

Existing frozen operations and audit records remain durable historical data under
their current reader contracts. They may be independently looked up and freshly
validated later; they are not a newly trusted preparation payload. A caller's
lookup reference is only an expectation. It cannot convey provenance, authorization
or permission to select a replacement operation/profile. No additional fields,
portable digest, preparation ID, lifetime, schema or provenance mechanism is
invented here. A useful exact retained intent payload remains **UNRESOLVED**.

## 3. Phase-boundary semantics

End the old phase's observation eligibility; invalidate views and discard volatile
preparation. Do not preserve a valid flag, credential, reservation identity,
continuation, attempt handle or executable entitlement. Source historical records
are not deleted or rewritten by discarding live observation eligibility.

A hypothetical later final request must establish new genuine authentication and
current admission independently. It cannot adopt the original preparation owner
or restore the original continuation from IDs or historical rows. Current
contracts do not define this replacement request or authorize a second executable
ceremony. No state-machine transition to it is approved by this document.

## 4. Invalidation matrix

The matrix distinguishes the volatile observation from unchanged historical
source rows. Historical retention is never retention of current eligibility.

| Event | Volatile evidence decision | At hypothetical final admission | Historical data |
| --- | --- | --- | --- |
| Authentication changes/revokes/expires | Invalidate/discard old credential-bound observation | Fresh genuine primary/session/MFA/epochs and fresh consent; reject old scope | Retain history, not credentials as authority |
| Activation changes | Invalidate scope-bound observation | Fresh exact incarnation; reject substitution | Retain prior event as history |
| Approval/ACK changes | Invalidate eligibility | Fresh pairing/effective approval/invalidation; reject mismatch | Existing immutable records remain |
| Emergency stop changes | Invalidate prior clear-state decision | Fresh authoritative stop/block check | Prior clear event does not override current stop |
| Physical identity changes | Invalidate observation eligibility | Recompute actual strict identities/schema/fingerprint; reject mismatch | Prior observation is historical only |
| Dependencies/population change | Invalidate dependency/manifest validity | Fresh recheck/required manifest regeneration | Frozen evaluation stays historical |
| Claims change | Invalidate claim/exclusion decision | Fresh full graph/disposition and operation exclusions | Keep append-only claim/history |
| History/control changes | Invalidate complete validation result; only existing exact Z15 write proof permits local inventory reuse | Fresh graph/audit/protected state/FKs | Never repair or rewrite to revive authority |
| Reservation/connection/epoch/transaction changes | Discard phase-local preparation/views | Prove actual new manager ownership; reread | No reservation entitlement retained |
| Schema/migration state changes | Invalidate inventory on continuity failure; relationship results are never reusable | Fresh schema/package and all migration relationships | Retain migration audit, not validity certificate |
| Process/thread/context changes | Discard live objects; reject cross-owner use | New request cannot recreate/adopt old live owner | Existing durable records inspectable only |
| Preparation process crash | Lose all live eligibility; no preparation recovery | No resumption/adoption; independent request is currently UNRESOLVED | No new prepared executable record exists |

Even without a detected change, the proposed boundary itself discards eligibility.
No universal event listener guarantees that a path or device remained unchanged;
fresh checks remain required. Z15's fixed local writes do not authorize a new
cross-phase exception.

## 5. Fresh-final-consent and admission matrix

The following are non-negotiable predicates for any later replacement contract,
drawn from existing kernels. This is not a new callable final admission owner.
Freshness includes existing post-write validation before commit, not just an
initial check followed by unchecked inserts.

| Predicate | Required fresh establishment | Existing source |
| --- | --- | --- |
| Authentication | Current owner primary/session, generation/profile scope, auth/MFA epochs, revocation, expiry and existing MFA replay/throttle rules | Shared runtime scope/auth readers and genuine owner adapters |
| Authority consent | Current exact subject, explicit decision/reason, fresh TOTP step and unused one-use confirmation bound to those credentials; existing strict expiry, no extension | `runtime_authority_consent`, consent manager and issuer |
| Operation/scope | Durable exact operation/manifest/install/target/generation/G+2 profile/binding/owner; no caller replacement | Runtime contract, proposal/ACK/approval readers, `_current` |
| Activation | Current independently verified incarnation/ledger/scope | Activated/current/readiness kernels |
| Approval/ACK | Exact acknowledged proposal, effective runtime approval and invalidation history | Shared admission `_collect` and current approval readers |
| Emergency stop | Current clear stop and no operation block | Execution stop/block readers |
| Dependencies | Fresh dependency state and required read-only whole-population preparation equality | `dependencies.recheck`, shared admission and `permanent._prepare` |
| Physical identity | Actual hostname, resolved control/target paths/devices/inodes, schema/fingerprint and enrolled observation match | `target_identity`, `observe_target`, runtime identity kernel |
| Current history/control | Full current binding/migration/profile/audit graph, protected baseline, exact actual writes and FK checks | `_history`, exact manager finalization and schema readers |
| Claims | Complete current inventory/disposition and selected-operation/global exclusions, legacy conflicts | Authority subject/disposition/admission readers |
| Reservation state | Exact PID/thread/context, connections/transactions/epochs/query-only mode; target retained through required control commit | Genuine manager registrations and lifecycle checks |
| Migration relationships | Current definitions/package, audits, predecessor order, binding and finalized G+2 continuity | Manifest/transition readers; never a prepared migration certificate |
| Readiness | Protected fresh assessment, actual inventory/rehearsal/activation policy | Existing private readiness interfaces |
| Deadlines | Original authoritative clock, no rollback/anomaly, current time strictly before all auth/step/confirmation/authority expiries | Existing paired clock and owner `_time` checks |

Consent's 600-second maximum is clipped by credential expiry; confirmation does
not renew the step deadline. The authority's maximum remains 120 seconds from
actual issue time and is also shortened by earlier deadlines. Neither fresh
authentication nor a new reservation extends an existing authority.

## 6. Exactly one finalization owner: unresolved replacement boundary

Required owner: one genuine registered manager, bound to actual PID/exact thread/
context, owning the original final authority and all transaction lifecycle calls.
It must receive no old preparation capability or imported authority/attempt.
Only independently validated durable lookup data can select the intended scope.
It exposes no SQL/connection/cursor/commit/rollback or writer interface.

**The exact replacement owner is UNRESOLVED.** Naming an existing class would
not resolve it: current `CoordinatorContext` spans separate issuance and attempt
transactions; `CoordinatorAdmissionContext` is reservation-local; consent,
read-only activated and metadata owners have different fixed authorizers and
registrations. None can be widened or relabeled to implement the replacement.
The existing public issuance result is inspection, not an adoptable continuation.

The only existing authority/attempt producer remains the unchanged coordinator:
private issuance, confirmed commit/cleanup, original continuation promotion,
fresh attempt phase, confirmed attempt commit/cleanup, opaque inert result.
It is the stopped composition, not a newly sufficient finalization owner.

## 7. Exact known write sets and unresolved replacement atomicity

| Current phase | Exact successful writes | Atomicity and limitations |
| --- | --- | --- |
| Authority issuance | CAS confirmation `used=0` to `used=1`; consumption audit INSERT; `recognition_runtime_execution_authorities` INSERT; AUTHORIZED `recognition_runtime_execution_lifecycle` INSERT; issuance audit INSERT | Five mutations in one manager-owned control transaction; final actual graph/protected state checks; no publication before confirmed commit and cleanup |
| Attempt creation | `recognition_runtime_execution_attempts` INSERT; `recognition_runtime_execution_attempt_history` ATTEMPT_CREATED INSERT; linked `recognition_admin_audit` INSERT | Three inserts in a separate manager-owned control transaction, authority-bound; exact graph/history/audit and exclusions required |
| Fresh consent | Existing protected MFA/step/confirmation and audit writes under their existing consent owners | Not another attempt write and not automatically part of either transaction above |
| Replacement finalization | **UNRESOLVED** | No approved combined write set, authorizer, graph proof, commit ordering or publication contract |

Authority genesis evidence retains exactly `format`, `authority_id`,
`authority_sha256`; do not add boundary/evidence fields. Do not combine the five
and three writes or move timestamps/CAS for performance. Uniqueness and immutable
guards are enforced with the existing row writes, not a new fence row.

Each current manager retains target reservation through control commit; target
is query-only in issuance/attempt phases. Memory epochs, connection cleanup and
opaque result publication are not SQLite-atomic with control row insertion.
Metadata target commit/reacquisition is a separate approved protocol, not implied
by a final admission snapshot. No cross-database atomicity or target write access
is introduced. Exact replacement rollback/uncertainty/publication rules must be
reviewed before an owner can be implemented.

## 8. Crash and uncertain-commit behavior

| Crash/failure point | Required fail-closed outcome |
| --- | --- |
| During preparation | Publish no usable evidence token; discard eligibility; no authority/attempt/target state |
| After preparation | Live phase evidence cannot be restored; historical data does not resume a ceremony |
| During fresh consent | Existing consent manager resolves known writes; no final authority inferred; committed consent is not execution permission |
| During final admission before commit | Owning manager rolls back known uncommitted writes; publishes nothing usable; spent continuation is not revived |
| During commit or cleanup | Outcome UNKNOWN until durable inspection; poison live owner, no result, automatic retry or adoption |
| After commit before publication | Durable history may exist without a usable process-local result; do not reconstruct one from rows |

UNKNOWN is an explicit stop state, not “probably succeeded.” Read-only inspection
does not itself authorize recovery. Earlier confirmed commits are not undone by
a later rollback. Exact new durable crash prefixes remain **UNRESOLVED** until
the replacement owner/write set is defined.

## 9. Concurrency and adoption

Duplicate preparation data creates no winner, reservation or permission. Competing
current admission requests serialize with control BEGIN IMMEDIATE and current
durable operation/manifest/authority exclusions. Existing attempt uniqueness and
one-use original continuation remain mandatory. Exact duplicate inspection data
cannot be promoted to a capability.

Reservation races or loss reject actual ownership checks; no arbitrary retries.
Stale evidence is discarded/recomputed within a genuine new owner, never refreshed
into authority. Cross-process/thread/context attempts cannot share registries or
revive old results. Finalization replay must fail through durable confirmation/
uniqueness fences plus original-owner lifetime, not a Python-only flag. An actual
new final-request protocol and its global race rule remain **UNRESOLVED**; the
current fences do not automatically define a replacement transaction.

## 10. Evidence, consent, admission and execution

| Category | Meaning | Does not imply |
| --- | --- | --- |
| Evidence | Bounded observations/data under exact reader/phase rules | Freshness, consent, admission or a live capability |
| Consent | Explicit current owner authorization with current genuine credentials/MFA and one-use exact subject | A committed authority, readiness or permission to skip fresh admission |
| Admission | Current authority-bound decision under an exact registered owner and protected transaction | Writer permission solely by possessing a snapshot or historical row |
| Execution | Separately reviewed writer capability and controlled mutation/commit protocol | Automatic creation from evidence, consent, admission, attempt or target metadata |

The requested replacement executable transition has no defined new owner yet.
Existing ATTEMPT_CREATED is inert, not an executable state, and cannot be used
to imply a missing execution contract. Production gates stay blocked.

## 11. Decision B: new security rule required

No exact useful cross-boundary preparation payload is supported. Schema inventory
is local only. The missing rule must define **which exact non-authoritative intent
may be retained, by what source/binding/selection/lifetime, without transferring
any current allow decision, and how one exact fresh final owner originates its
authority and commits its exact write set without adopting an older ceremony**.

That rule must explicitly resolve independent fresh consent versus original-owner
continuity, reader registration, new phase epochs, durable exclusions and actual
post-write verification. It cannot be inferred from calling something evidence,
relogging in, using the same outer context, or matching hashes. The information
currently available does not supply it; inventing fields or an owner here would
create the shortcut this review is required to prevent.

## 12. Exact next implementation boundary

**No implementation is authorized.** First explicitly decide whether any useful
retained intent is needed and define the exact rule in section 11; otherwise
reject this replacement direction as an unproven solution to the lifetime problem.
Do not repeat the stopped lifecycle, implement a hollow preparation phase, create
another authority ceremony, merge transaction owners or change the 120-second
ceiling on this document's authority. No performance feasibility is claimed.

## 13. Validation and production blocks

Only this document is created. Run `git diff --check` and document whitespace/
local-link checks. No pytest, Z18, T, broad suite, code/schema/migration,
authority/attempt/target state, writer/execution capability, production/hosted
access, commit or push.

PRODUCTION AUTHORIZATION: BLOCKED

PRODUCTION EXECUTION: BLOCKED

PRODUCTION ACTIVATION: BLOCKED

WRITER CAPABILITY: BLOCKED
