# Slice 4e-19-R: private authority-to-coordinator continuation

**APPROVE 4e-19-R: design contract complete; implementation remains blocked.**

This document defines the missing boundary identified by the blocked 4e-19
inspection. It adds no executable interface, schema, authority, continuation,
attempt or capability. Public `issue()` remains inspection-only. The proposed
names below are implementation contracts, not claims that these APIs exist.

The governing original-continuation and transaction rules remain those in
[4e-17](recognition-runtime-live-attempt-storage-writer-contract-4e-17.md).
[4e-18-R](recognition-runtime-execution-attempt-storage-slice-4e-18.md) supplies
inert attempt DATA/storage only. Its presence cannot authorize adoption.

## 1. Current ownership and missing interfaces

| Existing implementation | Creation, registration and release contract |
| --- | --- |
| `runtime_activation_authority_issuance._transaction()` | Creates its own `_State`, paired clock and exact `IssuanceContext`. Opens control with `BEGIN IMMEDIATE`, validates history, opens target with `BEGIN IMMEDIATE` and `query_only=ON`, binds actual observations/MFA epoch, then registers in its private `_contexts` and shared `_issuance_views`. `_finish()` revalidates before control commit while target remains reserved. Finally unregisters the context/view and clears credentials; nested `_owned_connection()` exits roll back/release target and close both connections. |
| `runtime_activation_authority_issuance.issue()` | Validates existing authority or consumes consent and calls the fixed `_persist()` protocol. Only after confirmed commit and both cleanups does a new issuance return `IssuedAuthority`. Its `_issued` registration is PID/thread/deadline-bound inspection, not an original execution lifetime. Duplicates return inspection DATA instead. There is no coordinator parameter or private original-issuance notice. |
| `runtime_authority_consent_transaction.consent_transaction()` | Separate exact `ConsentContext` and `_consent_views` registration. Same control-first/query-only-target ordering. Allows only bounded consent writes and established denial effects. Final validation/commit precedes target release. Registration is removed and credentials cleared on exit. It is neither an issuer nor an execution owner. |
| `runtime_activated_owner.validation_transaction()` | Separate exact `ActivatedAdmission`/`_activated_views` registration, snapshots actual identity and activation incarnation, validates existing authentication/approval/readiness and commits successful zero-write observation or validated denial reductions. Own connections/reservation epochs are invalid after exit. It cannot be promoted to a coordinator. |
| `runtime_scope_validation.RuntimeReadView` | Exact private owner registrations, not duck typing. `_view_parts()` resolves the original owner and MFA epoch. `_primary()`/`_session()` call existing auth kernels, runtime scope links and owner deadline adapter. No raw handle escapes. There is no coordinator registration. |
| `runtime_admission_validation` | `AdmissionReadView` currently resolves only proposal and claim owners. `_resolve()` checks exact state/connections/reservation epochs/query-only status; `_collect()` performs current v2 approval, proposal/ACK, dependency, manifest, physical observation, stop and auth validation. Its results are reservation-bound DATA. There is no activated coordinator adapter. |
| `local_readiness` | Exact activated, consent and issuance adapters call `_assess_inventory()` internally. That kernel performs protected `_cipher(config)` verification, owner/MFA/activation/rehearsal checks and version-aware runtime inventory. No coordinator adapter exists; raw `_assess_inventory()` is not an acceptable new public interface. |
| `runtime_execution_attempt_schema` | Canonical six-field attempt and nine-field CREATED codecs, exact immutable control graph and migration chain. `validate_binding()` resolves historical authority DATA; `inspect_attempt()` returns historical read-only DATA. Neither checks current authentication nor provides a continuation. |

`runtime_execution_coordinator.py` is absent. The shared validation is reusable
but is not a complete composition for a new owner: exact registrations, protected
readiness and original private issuance must be implemented together later.

Existing `runtime_validation` 3a ownership, consent/issuance ownership, ordinary
v3 denial, Slice H, `target_identity()` and legacy execution remain unchanged.

## 2. Exact future owner and private entry points

Proposed module: `runtime_execution_coordinator.py`. Define an opaque outer
`CoordinatorContext`, a distinct opaque reservation-local admission context,
and private registries. No public constructors, import/load, pickle/copy-based
restoration, connection properties, cursor, SQL, commit/rollback, writer or
activation method. Private Python reflection/host compromise remains outside
the existing in-process integrity model; a Python underscore is not a new
cryptographic trust mechanism.

Exact proposed types/registrations are `CoordinatorContext` in `_coordinators`
(outer lifetime), `CoordinatorAdmissionContext` in `_admission_contexts` (one
reserved phase, retaining its exact outer reference), and private `_Continuation`
in `_continuations` (one committed original issuance). Opaque objects have no
caller-writable fields or `__dict__`; private registry entries carry state.
`_state(context)` and `_read_parts(context)` accept only the exact registered
`CoordinatorAdmissionContext`, and validate its original outer registration too.
`_require_auth_expiry(context, expires, code)` validates that same phase and
appends deadlines to the outer lifetime as well as the phase. This prevents a
new phase from discarding an earlier constraint. Closing or poisoning the outer
owner invalidates/removes all its phase, pending-notice and continuation entries.

The future owner is established before any authority issuance. It accepts
existing originating runtime primary/session credentials and exact lookup data
for the approved operation, approval digest, activation digest and ceremony
reason. Those arguments are expectations, not authoritative scope. Resolve all
scope through current durable readers under reservations. It accepts no existing
`IssuedAuthority`, authority JSON/ID/digest, continuation or callback/provider as
an issuance input. No browser endpoint or CLI adoption mode is introduced.

Proposed fixed private issuer entry:

```text
runtime_activation_authority_issuance._issue_for_coordinator(
    coordinator_admission_context, confirmation_token)
```

The issuer resolves that exact context through the new coordinator's private
registration, verifies that it belongs to the original active outer lifetime
and is in its one allowed issuance phase, and uses its already-held connections.
It does not open a second issuance transaction or relabel the context as an
`IssuanceContext`. No caller-supplied state, connection, scope dictionary,
factory, callable or selected provider can substitute for registration.

The private call stages issuance only. It returns no public authority credential
or live continuation. The coordinator manager finalizes the control transaction
and cleanup and only then retains a private continuation in its original registry.
The public `issue()` signature, return types, duplicate semantics, `_issued`
registry and standalone owner remain unchanged in meaning.

## 3. Binding inventory: live references versus immutable values

| Binding | Private representation and required check |
| --- | --- |
| Original outer owner | Exact object reference in private registry; PID, exact `Thread` object and identifier, active/poisoned state, paired clock and allowed phase. No durable PID/thread/coordinator token. |
| Connections and transaction | Exact connection references plus fresh manager-created phase identity, control/target reservation epochs and query-only state. Transaction presence alone is insufficient: rollback/re-BEGIN invalidates the old phase even on the same connection. |
| Operation/proposal/ACK | Canonical immutable copies/digests of the full durable operation reference and proposal reference, including operation/manifest/population/event/preparation and ACK sequence/digest. Reload and compare; never compare operation digest alone. |
| Target/runtime scope | Immutable canonical runtime target and actual physical snapshot: paths, hostname, lossless device/inode values, target schema, installation/target UUIDs, deployment binding digest, profile digest, generation, owner and auth/MFA epochs. Values come from enrolled/current readers. No host exemptions or caller-selected physical identity. |
| Activation | Current `require_activated()` event sequence and whole event digest, including its existing consumed-confirmation validation. Never a boolean or binding marker. |
| Authentication | Private originating raw credentials only as needed by existing validators, plus immutable primary/session hashes and actor. Never replace them with another login or expose them in evidence/logs. Clear credentials on exit/failure. Current proofs/runtime-auth links must remain valid. |
| Approval/consent | Exact current runtime v2 approval and effective history digest; immutable original authority consent step/confirmation artifact digests, one-use consumption chain and original deadlines. No new TOTP or confirmation ceremony inside this continuation. |
| Dependencies/stop/readiness | Full immutable frozen dependency and exact inactive stop snapshots/digests, plus normalized protected readiness evidence. Recheck live facts and regenerated whole manifest/population before each effect boundary. A set-then-clear stop has a different head. |
| Authority | After fresh issuance only: exact durable authority ID, canonical body/digest, AUTHORIZED genesis/audit linkage, original expiry and private issuance provenance bound to this outer owner and issuance phase. A copied body/digest is not provenance. |

Canonical copies use existing bounded JSON/UUID/SHA/decimal/NUL/integer/time rules.
No fields are added to the approved authority, AUTHORIZED evidence, attempt or
CREATED codecs. Ephemeral owner/phase provenance is not a new durable record.
Clear phase-local credential references when the phase exits. Only the original
outer owner may retain the originating credentials privately until outer exit,
expiry or poisoning, solely for fresh validation in its later reserved phase.
It cannot request or substitute newly issued authentication.

## 4. Smallest shared validation extraction and adapters

Implementation must first provide the following fixed adapters; none exists yet.
Each accepts only an exact registered coordinator admission context/view. No
`allow_activated`, skip-validation, exclusion, override or provider parameter is
added to old public interfaces.

| Required interface | Reuse and boundary |
| --- | --- |
| Coordinator scope view | Add a separate `_coordinator_views` registry and fixed `_register_coordinator_view()` in `runtime_scope_validation`. `_view_parts()` dispatches to the coordinator's exact `_state()`/`_read_parts()`, not 3a, claim, consent, activated or issuance registration. Preserve all existing cases and rejection behavior. |
| Identity/activation | Coordinator `_read_parts()` uses `runtime_validation._history()`/`_identity_snapshot()`, shared `_mfa()`, actual observations and `local_readiness.require_activated()`. Compare exact recorded scope and activation head. Do not call preactivation-only `_snapshot()` as an activated bypass. |
| Authentication/deadlines | Existing shared `_primary()`/`_session()`, `admin_auth._primary()`/`_session()`, `runtime_auth._scope()` remain authoritative. `_require_expiry()` gains an exact coordinator dispatch. Its manager appends original constraints; it never replaces or extends an earlier deadline. No auth issuance or MFA seed decryption/TOTP duplication. |
| Admission | Add a fixed coordinator owner case/read-view factory to `runtime_admission_validation`. Keep `_resolve()`'s original exact owner/connection/epoch and zero-target-change tests. Reuse `_collect()` for current v2 approval/proposal/ACK, dependency snapshot/READY recheck, fixed-policy whole-manifest regeneration, stop and physical observations. Existing proposal/claim adapters are unchanged. |
| Approval/ACK | Continue `runtime_approval_contract.read_current()` and `runtime_proposal_records.read_approved_proposal()` through that genuine shared view. Do not use historical approval or detached ACK data as current authority. No legacy wrapping or operation portability. |
| Protected readiness | Add fixed `local_readiness._assess_coordinator(view, session_token, primary_token)` resolving only the coordinator owner. It validates current credentials and calls existing `_assess_inventory()` internally with the same runtime inventory, policy and protected key verification. No target/control handle or cipher escapes. |
| Attempt/recovery inventory | Keep `runtime_claim_disposition._inspect_reserved()` and existing legacy/runtime proposal inventory checks. Additionally use exact control schema/attempt row validation and a complete read-only attempt inventory. In this pre-attempt boundary any existing incomplete attempt blocks the new continuation; a selected-authority attempt is also a duplicate/adoption fence. No selected-attempt exclusion or stage-aware writer exception exists yet. |
| Producer subject | Extract the minimum subject-assembly kernel from the issuer's `_subject()` so its durable readers and scope comparisons can be reused under the two exact owners. Subject construction maps the already validated full operation/admission facts to existing `SUBJECT_FIELDS`. It must retain the current readiness normalization, original consent subject comparison, claim/recovery blockers and final identity/deadline checks. No alternate caller-selected reader or readiness implementation. |
| Fixed issuance mutations | Reuse/extract the existing `_body()`, `_persist()` and `_final_mutations()` fixed protocol behind exact public-issuer/coordinator entry adapters. Keep CAS confirmation consumption, the five writes, original body/genesis format, audits, complete graph checks and original expiry calculation. No caller-supplied mutation or finalizer callback. |

An extraction is acceptable only with before/after regression equivalence for
the existing public issuer, consent and activated owners. Consent's preissuance
"authority must not already exist" fence remains its own prerequisite. Public
issuer duplicate inspection remains its own behavior. Do not unify either into
a permissive generic mode. The coordinator private path rejects any preexisting
authority rather than interpreting it as successful issuance by this owner.

Keep the common subject and fixed mutation kernels private to
`runtime_activation_authority_issuance.py`; proposed `_subject_for_owner(context)`
resolves only the exact original issuer or coordinator registration through fixed
code branches. It is not passed a state object or validation callback by a caller.
The old `_subject()` remains the issuer's owner-specific entry wrapper. Factor
shared data assembly and existing reader calls, not independent copies of auth,
approval, readiness or dependency validators. Any adapter dispatch must reject an
unrecognized context before reading a connection or performing a mutation.

Fresh checks resolve every complete authority scope object, not a collection of
selected hashes. Current authority/history readers must verify immutable rows,
AUTHORIZED genesis, consent artifacts/consumption and typed audit chain. Fresh
admission must also compare originating proof hashes, original consent subject,
whole activation event, physical snapshot, effective approval history, full
dependencies, exact stop head and readiness. Current readiness uses its present
full normalized binding, excluding only `assessment_at_utc` as `_assessment_binding()`
already does. An assessment hash from another phase is not fresh validation.

### Protected readiness and denial effects

`_assess_inventory()` calls `admin_auth._cipher(config)` internally today. The
future adapter preserves key-file checks and that verification. The returned
cipher and stored MFA ciphertext/seed are never returned, logged, copied into
the coordinator subject or put into a continuation. Tests may use disposable
fixture keys; this design task reads no deployment key.

Wrap only safe immutable readiness DATA in a phase-bound private evidence view:
exact outer owner, reservation phase/epochs, canonical normalized assessment,
digest and assessed time. Never add these private wrapper fields to authority
or consent formats. Reject after phase exit, changed activation or owner scope;
regenerate readiness on reacquisition. Readiness is a prerequisite, not a token
granting writer access or proof that PythonAnywhere has been verified.

Successful shared validation is zero-write. Private issuance alone performs
its existing bounded control writes. Preserve `admin_auth._deny()` and
`runtime_auth._scope()`'s established control-only denial/revocation behavior:
the private denial facade defers physical COMMIT to the manager. Only the existing
`runtime_validation._denial_safe()` reduction/audit shape may commit, after the
same independent final scope/identity/ownership checks while target is reserved.
No continuation is produced. An identity/history failure must not be converted
into permission to commit arbitrary denial changes. Do not swallow the rejection
or weaken a final check to guarantee persistence when the boundary is unsafe.

## 5. One original issuance phase: exact ordering

Proposed outer phases:

```text
CREATED -> RESERVED -> VALIDATED -> ISSUING -> PENDING_COMMIT
        -> COMMITTED_UNPUBLISHED -> CLEANED -> CONTINUABLE
any failure -> POISONED -> CLOSED
normal outer exit -> CLOSED
```

1. Register the exact outer owner and paired wall/monotonic clock before issuance.
   Reserve one issuance invocation in its private state; no second invocation.
2. Create a fresh reservation-local context/phase identity. Acquire control
   `BEGIN IMMEDIATE`, validate exact control schema/history, then acquire target
   `BEGIN IMMEDIATE` and set `query_only=ON` before any shared validation.
3. Bind exact connections and both reservation epochs. Register only the new
   coordinator view; capture protected baselines and audit sequence. Perform
   current auth, identity, activation, approval/ACK, dependency, stop, complete
   claim/recovery inventory and protected readiness checks.
4. The fixed private issuer receives this exact admission context. Reject any
   existing authority for the selected operation/manifest, any selected 4d-1
   claim, conflicting attempt or prohibited legacy effects. Validate original
   consent/one-use confirmation. Stage only existing issuance control writes.
5. Construct a private pending issuance notice from that successful invocation,
   bound to the original owner, phase, exact connections/epochs, authority
   ID/body/digest and original scope/deadlines. It is not yet a continuation and
   cannot be observed/spent by a caller or future attempt producer.
6. Under the same uninterrupted control and query-only target reservations,
   repeat fresh shared validation, exact subject/graph/audit/protected-mutation
   checks and original consent deadlines. Sample paired time last. Manager alone
   commits control. Require confirmed transaction end and target still reserved.
7. Mark the private notice committed but unpublished. Invalidate all borrowed
   phase views. Only now roll back/release the target reservation and close its
   connection; finish control cleanup/close. No target COMMIT is permitted.
8. After both cleanups succeed, verify original outer PID/thread/lifetime,
   monotonic/wall time, no poisoning and the exact pending notice. Consume that
   notice once and retain the private continuation in the same outer registry.
   Allocation/registration/publication failure poisons the outer owner and
   publishes no continuation. It cannot be repaired by reinserting registry DATA.

No release/reacquisition occurs between validation, issuance writes and control
commit. No ATTEMPT_CREATED insertion occurs in this contract's next admission/
continuation implementation. Attempt production is the following separate gate.

### Reservation epochs and the interval after cleanup

A phase records both exact connections, a unique private phase identity and
control/target reservation epochs. Manager-owned BEGIN, COMMIT, ROLLBACK,
query-only changes and release advance the corresponding epoch/invalidate views;
unauthorized lifecycle calls poison the owner. A new transaction on the same
connection never validates an old view. Connection replacement is equally fatal.
Capture epochs at registration; do not accept caller-provided epoch numbers.
Manager invalidation must be explicit even when SQLite reuses a prepared
statement; authorizer callback invocation alone is not a transaction identity.

The outer continuation deliberately survives only the manager's expected confirmed
issuance commit and cleanup. It does not keep a transaction/read-view alive or
claim that authentication/activation cannot change afterward. There is a real
interval without reservations after cleanup. In that interval the continuation
is inert provenance, not current eligibility. Before any future attempt creation
or other use of authority, the same original outer manager must acquire a fresh
control-first/query-only-target phase and repeat every current scope, auth,
activation, consent/deadline and readiness check. It may not reuse phase evidence.
This is the 4e-17 phase rule, not a validation-gap exemption or permanent lock.

Unexpected rollback/replacement/cleanup or a failed transition poisons the whole
outer lifetime. Intended manager cleanup invalidates phase handles, not permission
to reconstruct a new outer owner. No API grants admission based only on an outer
object being present or its old snapshot matching a supplied dictionary.

## 6. Continuation, deadline and current validation

The private continuation is exact-type/registry-owned, process-local,
thread-bound, immutable to callers, nonserializable and lifetime-bound. It has no
SQL, writer, executor, completion, activation, resume or adoption method. It is
not returned by public `issue()`, stored in its `_issued` registry, or constructible
from the public inspection result. Any exposed inspection copy is DATA only and
cannot recreate this registration. Only the original manager can spend the
private provenance once for the later separately reviewed attempt transition.

Provenance proves one fresh issuance by this exact original owner after confirmed
commit/cleanup. Current validity additionally requires fresh authoritative
validation under its own new phase. Never claim provenance alone proves current
authentication, activation or readiness. Changed scope, owner/access, profile,
installation/target, generation, auth/MFA epochs, originating proof revocation or
expiry, activation incarnation, proposal/ACK, approval, dependency, stop or
readiness invalidates use and poisons the continuation. Renewed login/MFA cannot
transfer or extend the originating scope.

Inherit the minimum of the authority's original expiry, originating primary and
session deadlines, original consent step/confirmation deadlines and any earlier
existing validation constraint. Authority expiry remains the existing minimum
including its 120-second ceiling; no new TTL/grace/renewal. Use the original
paired `_Clock` across phases; reject rollback, elapsed-time inconsistency and
`now >= deadline`. No lifetime begins anew at cleanup, publication or future use.
No PID, thread, raw token, key or session credential is persisted in a new record.

## 7. Duplicates, concurrency and failure outcomes

| Case | Required result |
| --- | --- |
| Public identical duplicate | Existing inspection-only DATA with no new `_issued` object; no private continuation. Existing public contract unchanged. |
| Second private invocation, same owner/authority | Reject; cannot publish/spend a second continuation. Existing continuation must not be reissued. Treat an invalid transition as terminal for that outer lifetime. |
| Same owner, conflicting authority/scope | Reject and poison. No scope update, replacement ID or second notice. |
| New coordinator, authority already exists | Reject even if unexpired, identical and authenticated. Historical authority is not original issuance. Durable inspection only. |
| Concurrent coordinators, same operation/manifest | Control BEGIN IMMEDIATE serializes; existing authority UNIQUE keys and one-use confirmation CAS fence the winner. At most one fresh authority/private original continuation. Loser rejects or receives established BUSY/LOCKED; no retries/new busy timeout/adoption. |
| Prior failed issuance before commit | Roll back uncommitted writes, poison original lifetime, no continuation. Absence does not authorize replay of that owner. Any later independent ceremony is subject to unchanged unused-consent/current-scope checks, never automatic recovery. |
| Commit raises or does not confirm transaction end | Outcome unknown; no continuation, no auto retry/adoption. Resolve/close control before releasing target per existing ownership rules; cleanup failure cannot be success. |
| Confirmed commit, target rollback/close or control close fails | Authority may be durable but remains inspection-only; no continuation. No target effects or attempt are claimed. |
| Both cleanups succeed but notice promotion fails | Same inspection-only authority; poison owner, no fallback construction or retry. |
| PID/thread mismatch, timeout, rollback or scope mutation | Invalidate current use; destroy original continuation. A new process/login cannot reconstruct it. |

Use existing `inspect_issuance()` for trusted deployment-side read-only durable
inspection. Its exact/conflict/unknown/absent statuses never authorize retry or
adoption. Matching durable authority after uncertainty cannot prove the original
manager survived. A missing result is not evidence of rollback. A missing row in
one snapshot is not permission to reenter the poisoned lifetime. No new recovery
state, lifecycle codec, audit action or schema is needed to represent loss of a
process-local continuation; absence is deliberate fail-closed behavior.

Error reporting may identify sanitized commit/cleanup classification and safe
inspection references, never raw session/confirmation tokens, key/ciphertext,
seed, SQL contents or a serialized continuation. No HTTP exposure is added.

## 8. Focused implementation test contract

These are future tests, not executed new functionality. Use real disposable
enrollment/auth/proposal/ACK/v2 approval, authority consent and synthetic scoped
activation fixtures; never a provider/callback that manufactures production
authority. Do not insert attempt rows in these tests. Snapshot attempts/history
when installed and prove counts/bytes unchanged. Cover DELETE and WAL where
reservation/process behavior is tested, without checkpoint/retry workarounds.

| Proposed focused test(s) | Required assertions |
| --- | --- |
| `test_owner_precedes_private_issuance` | Original registry exists before validation/issuance; private issuer receives its exact already-reserved context; no nested issuance manager/transaction or post-issue owner reconstruction. |
| `test_private_issuance_commit_cleanup_then_continuation` | Real five-write durable authority/genesis/consumption/audits; no notice promotion before confirmed control commit and both cleanups. Same owner/phase/scope/digest; no attempt. |
| `test_public_issuance_cannot_promote` | Public new and duplicate results remain inspection-only, rejected by private path; lookup ID/JSON/copy/pickle/`object.__new__`/unregistered context cannot manufacture provenance. |
| `test_scope_fields_and_digest_binding` | Alter each complete operation/target/install/profile/generation/owner/auth/MFA/physical/activation/proposal/ACK/approval/history/dependency/stop object independently; reject before commit/promotion. Do not compare only hashes supplied by test callers. |
| `test_wrong_owner_pid_thread_and_registry` | Wrong exact coordinator, PID, thread object/identifier and forged registration fail. Use subprocess restart to prove durable authority/public inspection cannot restore continuation. |
| `test_connection_transaction_and_epoch_replacement` | Swap either handle; rollback/re-BEGIN on same handle; change phase or either reservation epoch; unauthorized COMMIT/ROLLBACK/SAVEPOINT/query_only changes; reject and poison even if transaction is active again. |
| `test_original_deadlines_and_clock` | Earliest primary/session/consent/authority deadline, equality-at-expiry, wall rollback/monotonic anomaly and expiry during cleanup/publication fail. No new lifetime, auth refresh or renewal. |
| `test_current_authentication_and_denial_effects` | Valid credentials cause zero validation writes. Invalid/revoked/missing primary or session/runtime-auth link and changed epoch produce exact established rejection and permitted control-only reduction/audit where safely committable. Compare symmetric populated protected-table snapshots; unrelated state and target unchanged. |
| `test_activation_profile_owner_changes` | Actual changed activation event/consumed confirmation, hostname/path/device/inode/schema, owner/access, installation/target UUID, binding/profile/generation or MFA/auth epoch rejects. Changed-then-restored stop/activation cannot reuse old incarnation. |
| `test_approval_ack_dependencies_and_inventory` | Tampered or missing ACK/proposal, invalidated/effective-history-changed approval, dependency/manifest/population change, selected 4d-1 claim, legacy effects/recovery conflict or other incomplete attempt blocks; no generic selected-operation exclusion. |
| `test_protected_readiness` | Real existing internal key verification; invalid/missing key, unenrolled MFA, stale rehearsal/recovery/readiness or stop fails. Immutable evidence contains no secret and is exact-owner/phase/activation-bound. Old adapters still reject new/foreign types. |
| `test_duplicate_and_existing_authority` | Same owner repeated/conflicting private call, standalone existing authority and new coordinator for same work never obtain a continuation. Public idempotence remains unchanged. |
| `test_concurrent_private_issuance` | Independent DB connections/processes, not a Python mutex. At most one durable authority and original continuation; loser cleanly rejects or bounded BUSY/LOCKED. No duplicated audits/consumption and no retries. |
| `test_faults_at_every_issuance_boundary` | Before CAS, after consumption audit, after authority/genesis/audit INSERT, final validation, before/silent/during/after actual commit, each cleanup and notice registration. Assert exact rollback or durable inspection-only prefix; no publication and no attempts. |
| `test_process_termination_and_restart` | Kill before commit and after commit-before-publication under DELETE/WAL; inspect durable state independently. Restart cannot adopt, reuse notice or infer success from in-memory object absence. |
| `test_target_reservation_and_no_effects` | Competing target writer blocked through final validation/control commit; target remains query-only; trace/authorizer rejects all INSERT/UPDATE/DELETE/DDL/COMMIT and query_only=OFF. Target dump unchanged, locks released after confirmed cleanup. |
| `test_no_downstream_authority_or_legacy_records` | Writer/production/execution entry points reject all owner/readiness/public/private inspection objects; no lease, target effect/seal/receipt, legacy claim/EXECUTING/recovery/completion or activation transition. Existing schema/legacy rows byte-for-byte unchanged. |
| `test_expected_release_and_fresh_phase` | Intentional manager commit/cleanup invalidates old views yet retains original outer provenance; subsequent authoritative use must reacquire control-first/target-second and freshly validate. Mutations during the gap reject; no stale evidence grants eligibility. |

Faults and private-registry probes may instrument lifecycle boundaries, but must
not mock authentication/admission/readiness into unconditional success. Existing
public issuance, consent and activated-owner suites are required regression gates
for any extraction. Tests of future continuation never need target writer mode.

## 9. Ordered implementation boundaries

1. Implement distinct coordinator outer/phase ownership, exact shared scope and
   admission registrations, and protected readiness adapter. Extract only the
   fixed common subject/issuance kernels needed to avoid copying validators.
   Prove public and legacy behavior unchanged and zero-write validation/denials.
2. Implement the fixed private issuer path using that same reserved admission
   context, original preissuance outer lifetime, one pending notice, manager-only
   commit/cleanup and one private promotion. Test failure/concurrency/deadlines
   and no public-result conversion. Still zero attempts and no new schema.
3. After independent approval of the above, implement inert ATTEMPT_CREATED
   creation using 4e-18-R storage/codecs and 4e-17 uniqueness/phase rules.
   No writer admission, target metadata schema or later lifecycle is authorized.

The exact next boundary is **coordinator-owned admission/continuation
implementation, followed by inert `ATTEMPT_CREATED` creation.** Runtime writer
admission remains a later independent review. No production deployment, readiness
enablement, activation or target fingerprint/enrollment transition is authorized.

## 10. Validation of current implementation

Only this document is added in 4e-19-R. No adapters are implemented because the
current exact-owner interfaces cannot compose this new continuation unchanged.
Existing tests are regression observations, not proof that the proposed private
path exists or that production is ready.

Requested existing regression run in the guarded disposable environment:

```text
tests/test_recognition_runtime_activation_authority_issuance.py
tests/test_recognition_runtime_authority_owner_consent.py
tests/test_recognition_runtime_activated_owner.py
65 passed, 111 subtests passed
```

`git diff --check` and new-document whitespace/final-newline checks passed.
No full or recognition/deployment-family run was made. No hosted/production
resources or real deployment keys were accessed; existing tests use disposable
fixture databases and keys. No commit or push was performed.

PRODUCTION AUTHORIZATION: BLOCKED

PRODUCTION EXECUTION: BLOCKED

PRODUCTION ACTIVATION: BLOCKED
