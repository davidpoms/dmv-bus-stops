# 4e-20-Z25: fresh finalization ceremony and owner contract review

## 1. Z24 blocker

[Z24](recognition-runtime-evidence-boundary-final-admission-contract-4e-20-Z24.md)
authorizes no retained preparation payload or cross-context observation. Schema
inventory is phase-local. This review assumes no preparation object exists.
It adds no new authentication, authority, transaction owner, schema or executable
transition.

**Decision C: the only supported fresh-ceremony composition reproduces the
already-blocked lifecycle.** A different single atomic finalization owner/write
set remains **UNRESOLVED**, rather than being invented to imply feasibility.
The review is complete as a negative architecture determination; no replacement
implementation is authorized.

## 2. Fresh-finalization definition

A genuinely fresh request must derive current scope and independently validate
authentication, exact consent and complete admission. It cannot import an old
preparation token, authority object/JSON, continuation, attempt handle or previous
allow decision. Existing durable operation/approval/audit records remain historical
source data, looked up and validated under their current readers. A caller's
reference selects intent only; it does not replace authoritative scope.

Fresh validation of existing genuine credentials and fresh issuance of credentials
are different operations. The existing activated owners validate primary/session
scope and expiry; they do not issue replacement authentication. Current
`runtime_auth` producers use `runtime_validation.authentication_transaction()`;
the preactivation identity gate requires non-activated state. A new authenticated
login/session producer for an already activated installation is **UNRESOLVED**
within this replacement design. Do not widen that gate or treat a new login as
recreation of an expired original coordinator.

Thus this review can enumerate the supported fresh validation of genuine eligible
credentials and consent, but cannot manufacture an activated reauthentication
path, a replacement final owner or an executable result.

## 3. Owner

The only existing owner that can originate coordinator authority and an attempt
is the registered outer `CoordinatorContext` in
[`runtime_execution_coordinator.py`](../src/review/recognition/runtime_execution_coordinator.py).
It is one original outer lifetime with separate reservation-local phases, not one
atomic finalization transaction. Current consent has its own protected manager.

| Responsibility | Existing owner/rule | Replacement limitation |
| --- | --- | --- |
| Process/thread/context | Outer PID, exact Thread/identifier, private registry; each admission phase resolves that outer | No cross-process/thread/context adoption or supplied owner callback |
| Authentication | Existing genuine primary/session supplied as references; shared kernels validate current owner/profile/epochs/expiry | Outer cannot issue fresh credentials; activated issuance remains UNRESOLVED |
| Consent | Existing authority consent manager performs protected TOTP/step/confirmation; issuer freshly resolves and consumes exact confirmation | Consent manager is not a coordinator or replacement final owner |
| Authority | Original coordinator invokes private `_issue_for_coordinator`; manager commits and promotes original notice | Existing public issuance DATA cannot be imported to create a continuation |
| Scope/operation | Shared admission, current proposal/ACK/approval and `_subject_for_owner`; canonical exact subject comparison | Caller cannot supply a new operation/target/profile/approval body |
| Activation | Current independent incarnation via activated/current/readiness readers | Binding marker alone is not activation; mismatches reject |
| Reservations/transactions | Each phase owns actual control and target connections, transactions and epochs; control before query-only target | No borrowed handles or merging of consent/issuance/attempt/metadata owners |
| Target | Issuance/attempt owners reserve target query-only, with zero target DML/DDL/commit | Target-entry mode/commit belongs to a separate metadata owner |
| Result | Original-owner private continuation, then inert `CreatedAttempt` only after confirmed commits and cleanup | No executable/writer capability; no result reconstruction from durable rows |

If “one finalization owner” means one new protected transaction combining fresh
consent, authority, attempt and target entry, existing ownership contracts do not
supply it. Its exact type, registrations, authorizer, mutation proof and publication
rules are **UNRESOLVED**. Do not simply name or relabel an existing context.

## 4. Fresh-validation matrix

Owner abbreviations: consent manager = current protected `ConsentContext`;
coordinator = original outer plus its exact current admission phase. All reads
resolve genuine private registrations and current reserved state.

| Item | Why fresh | Source of truth | Validation owner | Before or inside transaction? |
| --- | --- | --- | --- | --- |
| Authentication | Expiry, revocation, owner or auth/MFA scope may change | Existing primary/session/runtime-auth/MFA records and target owner/epochs | Shared auth kernels under consent manager and coordinator | Caller supplies references before entry; actual validation inside each protected transaction and final checks |
| Consent/TOTP | Replay counters, one-use status, subject and expiry are current | Existing MFA replay/throttle, step/confirmation artifacts and linked audit | Consent manager; issuer consumes confirmation under coordinator | TOTP/step and confirmation in existing consent transactions; fresh artifact checks inside issuance |
| Exact operation | Prevent substitution or stale manifest | Durable operation/preparation/event graph and writer manifest | Shared admission `_collect` and subject readers | Inside reservations; repeated at required final checks |
| Runtime scope | Generation/profile/binding/install/target/owner/epochs may change | Current finalized G+2 binding/profile and runtime scope | `_current`, shared scope and history readers | Inside each phase; actual scope comparison before commit |
| Proposal/ACK/approval | Exact pairing and effective approval can become invalid | Current proposal/ACK, v2 approval and invalidation/history | Current approval and proposal readers | Inside consent/issuance/attempt and final checks |
| Activation incarnation | Activation head can change | Independent current ledger and validated activation scope | Activated/current/readiness adapters | Inside each protected phase, fresh before finalization |
| Emergency stop | Clear state can change | Current stop and operation blocks | Admission and subject kernels | Inside each phase and required final checks |
| Dependencies | Current source records/population can change | Dependency graph/recheck and required regenerated whole-population manifest | Shared admission and subject readers | Inside reserved transactions; no historical ready flag |
| Physical identity | Filesystem changes are independent of SQL reservations | Actual hostname/paths/devices/inodes/schema/fingerprint | Strict identity and runtime snapshot kernels | Actual observations inside each phase at all required uses; never cached across contexts |
| History/audit | Prior and own writes change current graph | Full canonical binding/profile/authority/claim graph and audit linkage | `_history`, schema readers and manager finalizers | Entry/prewrite and actual post-write checks inside transaction |
| Claim state | Expiry/disposition/conflicts are current | Current full inventory and selected/global exclusions | Disposition, subject and admission readers | Inside each phase; historical claims do not become credentials |
| Control state | Protected baseline/FKs/write set must remain exact | Current installed schema, protected rows, counters and actual audit suffix | Owner finalization and schema readers | Baseline and post-write proof inside transaction |
| Schema inventory | Definitions/code/connection scope can differ | Actual current control definitions | Current readers; eligible Z15/Z7 only in their original phases | Acquire afresh in new phase; no earlier-auth inventory import |
| Migration relationships | Inventory alone cannot prove current transition validity | Migration audits, predecessor order, binding/profile/G+2 continuity | Existing manifest/transition readers | Fresh inside current phase and existing final validators |
| Readiness | Complete inventory, policy and activation must be current | Protected readiness assessment and genuine rehearsal/config checks | Existing exact consent/coordinator/private readiness adapters | Inside each corresponding reserved transaction; not a caller flag |
| Reservation identity/epoch | Connection/transaction/mode or owner can change | Actual registered state, paired connections/transactions/epochs | Owning manager only | At entry, every borrowed use, finalization and cleanup/publication |
| Deadlines | Auth/consent/authority can expire while locked | Paired authoritative clock and accumulated expiry bounds | Each owner `_time` and outer lifetime | Fresh during operation and before commit/use; equality expired |

All fresh checks stay mandatory. Fresh final consent cannot discard shorter
deadlines or change authentication semantics to make the final transaction pass.

## 5. Exact supported write sets

Sources:
[`runtime_authority_consent.py`](../src/review/recognition/runtime_authority_consent.py),
[`runtime_activation_authority_issuance.py`](../src/review/recognition/runtime_activation_authority_issuance.py)
and [Z20-R](recognition-runtime-attempt-preparation-late-finalization-contract-4e-20-Z20-R.md).

| Order/phase | Write | Owner and atomic transaction | Fence and outcome |
| --- | --- | --- | --- |
| Consent step, earlier phase | Existing TOTP replay-counter update and step-artifact audit; existing denial/throttle rules on failure | Existing consent manager and its fixed mutation proof | Existing code replay/throttle and artifact scope/expiry; no authority |
| Consent confirmation, earlier phase | Exact `recognition_admin_confirmations` row and confirmation-artifact audit | Existing separate consent transaction | Existing step-use and exact scope guards; no authority |
| Issuance 1 | CAS exact confirmation `used=0 -> used=1` | Original coordinator issuance transaction | Exactly one changed expected row; replay rejects |
| Issuance 2 | Consumption audit INSERT in `recognition_admin_audit` | Same issuance transaction | Current predecessor and exact artifact/subject/time |
| Issuance 3 | Canonical `recognition_runtime_execution_authorities` row INSERT | Same issuance transaction, after actual `_body` construction | Operation/manifest/confirmation uniqueness and exact scope/digest/expiry guards |
| Issuance 4 | AUTHORIZED `recognition_runtime_execution_lifecycle` INSERT | Same issuance transaction | Exact authority ID/digest and genesis sequence/state/time |
| Issuance 5 | Issuance audit INSERT | Same issuance transaction | Exact authority/genesis and predecessor linkage |
| Attempt 1-3, later phase | Attempt row; ATTEMPT_CREATED history row; linked creation audit | Separate original coordinator attempt transaction | UNIQUE authority/attempt and immutable guards, exact three-row graph/audit proof |
| Target-entry marker | Not part of either write set above | Separate existing protected metadata target owner/transaction | Requires genuine original created attempt, current authority, fresh metadata admission and its own mode/commit/reacquisition checks |
| Reservation transition | No new durable row | Actual manager transaction calls and memory epoch invalidation | Not atomically committed memory or target cleanup with control rows |
| Replacement combined write set | **UNRESOLVED** | No existing combined authorizer/owner/proof | Must not combine these merely by running them on one connection |

The canonical authority is the authority row's body, not an additional sixth
write. AUTHORIZED evidence has exactly `format`, `authority_id`,
`authority_sha256`; the enclosing lifecycle event has its separate unchanged
fields. ATTEMPT_CREATED remains inert. No execution claim, writer, seal, completion
or readiness receipt belongs to finalization.

## 6. Transaction and atomicity boundary

Each supported transaction independently takes control BEGIN IMMEDIATE before
target BEGIN IMMEDIATE/query-only. Final current validation and actual write
proof precede manager-owned control commit while target remains reserved.
Only then release target and clean up both connections; publish no usable result
before confirmed commit and cleanup. No caller transaction control is exposed.

The five issuance mutations are atomic together. The three attempt mutations
are atomic together in a later phase. They are not one eight-write transaction;
consent writes and target-entry insertion are not part of either atomic set.
Current contracts do not permit merging them or skipping the intermediate
commit/cleanup/original-continuation promotion. All replacement combining
boundaries are **UNRESOLVED**. There is no cross-database atomicity and no
SQLite-atomic guarantee for memory epochs or publication.

## 7. Verified ceremony ordering

The suggested linear sequence needs these qualifications under existing contracts:

1. Supply genuine eligible primary/session references; validate them freshly in
   the consent transaction. Creating fresh activated credentials is not supplied
   by that reader and is not assumed here.
2. Resolve exact current scope/operation, activation, proposal/ACK/approval and
   security subject **before** accepting TOTP consent for that subject. Unbound
   consent cannot precede the authoritative subject it authorizes.
3. Issue the protected fresh step and then explicit exact-subject confirmation
   through the existing consent phases, preserving their final checks/commit and
   earlier expiry. Neither result is execution authority.
4. Establish the genuine original coordinator owner and reservations. Perform
   full current admission, exact subject/consent checks and durable exclusions.
   Optional existing Z15 inventory stays local; no Z24 evidence is imported.
5. CAS the confirmation, then construct the authority with actual issue time.
   Perform the remaining exact five-write issuance protocol, including canonical
   authority, genesis and audits. Do not move the issue time to publication.
6. Perform fresh post-write admission and integrity/time checks; commit control
   with target held, clean up, then promote the original continuation.
7. Spend that continuation once, obtain fresh attempt-phase reservations, validate
   again, write the exact attempt/history/audit graph, and freshly finalize/commit/
   clean up before publishing an inert CreatedAttempt.
8. Any target-entry metadata phase has its separate genuine owner and complete
   validation/commit/reacquisition protocol. It grants no writer capability.
9. **No existing ceremony step here establishes the requested executable
   transition.** Execution/writer admission is a separate blocked boundary, not
   the meaning of ATTEMPT_CREATED or successful read-only admission.

This ordering repeats the current composition. A new single final owner with a
different order or combined transaction is **UNRESOLVED** and not silently added.

## 8. Crash and uncertain commit

Before consent/issuance: no preparation handoff exists. Failed consent publishes
no successful live result; preserve existing safe denial/throttle behavior.
During known uncommitted issuance/attempt work, rollback through its manager;
do not promise rollback of earlier consent/authority commits.

During commit or cleanup uncertainty, poison the live owner and publish nothing
usable. Stop for durable read-only inspection; no automatic retry, replacement
authority, adoption or inference that missing publication means rollback. After
confirmed commit but before publication, historical rows may remain without a
usable process-local result. A new process cannot recreate it. If publication or
cleanup fails, the original continuation is not reissued. Unknown outcome is an
explicit stop condition, not a probable success state.

## 9. Concurrency, stale state and adoption

Control reservations serialize competing finalizations. Confirmation CAS, current
operation/manifest/authority exclusions, exact schema uniqueness/immutable guards,
and one-use original continuation fence duplicates; no Python-only lock substitutes
for durable serialization. Exact duplicate public issuance returns historical
inspection DATA only. It cannot enter the private coordinator as new authority.

Stale auth, activation, physical identity, approval/ACK, stop, dependencies or
claim/history/control state rejects through current readers and final comparisons.
Reservation loss or epoch/connection replacement invalidates borrowed views.
No arbitrary retry repairs a reservation race. Process/thread/context changes,
matching hashes, fresh login or a newer activation cannot adopt the old scope,
continuation, attempt or uncertain result. Caller-supplied authority substitution
is rejected; authority is originated by the same registered coordinator only.

## 10. Security validity versus 120-second feasibility

Fresh validation without retained evidence is security-compatible with existing
readers. It does not establish availability or introduce a new fast path.
Fresh credential/consent validation and initial scope/admission precede authority
construction, while their own deadlines already run. The authority clock starts
at actual immutable `_body()` issue time after confirmation CAS.

Issuance post-write final validation/commit/cleanup, continuation promotion,
attempt admission/construction/finalization/commit/cleanup and every later
metadata check spend the same remaining authority window. Earlier credential/
consent expiry may shorten it; no fresh ceremony grants a longer window to old
authority. If it expires, fail closed and publish no usable result.

Z18 already measured that very composition failing before metadata entry. No
retained evidence or changed owner/write set is now available to remove required
work. Therefore this fresh ceremony necessarily reproduces the **structure** of
the blocked path; it is not a demonstrated performance solution. It need not
reproduce the exact wall-clock duration under every host/load. New alternative
feasibility and later metadata timings are UNMEASURED; no universal impossibility
or 120-second completion guarantee is inferred.

## 11. Decision C

The only supported fresh finalization route repeats the already-blocked lifecycle.
It offers current security checks, not a new executable transition or a shortened
authority window. A different combined final owner/write set, activated fresh
authentication producer if required, and executable transition policy are
**UNRESOLVED**. These gaps cannot be resolved by relabeling existing contexts or
declaring a new ceremony fresh. No replacement code should be implemented.

## 12. Exact next boundary

Stop this preparation/fresh-ceremony direction as an established performance
solution. Before further implementation, require an explicit architecture decision
that changes a specifically named security contract and proves its replacement
guarantees, or retain runtime execution unavailability. There is no new supported
payload/owner to implement from Z25. Do not run the lifecycle again, merge owners,
extend expiry, relax fresh checks or start T based on this review.

## 13. Validation and production status

Only this document is created. Validation: `git diff --check`, document whitespace
and local links. No pytest, Z18, T, broad suite, code/schema/migration, authority,
attempt, target state, writer/execution capability, hosted/production access,
commit or push.

PRODUCTION AUTHORIZATION: BLOCKED

PRODUCTION EXECUTION: BLOCKED

PRODUCTION ACTIVATION: BLOCKED

WRITER CAPABILITY: BLOCKED
