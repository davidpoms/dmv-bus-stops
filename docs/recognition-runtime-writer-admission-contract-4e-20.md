# Slice 4e-20: runtime writer-admission contract review

**B. BLOCK 4e-20 — concrete runtime writer-admission conflict**

Design/review only. This document does not authorize an implementation around
the missing boundaries. No capability, lifecycle record, migration, target write,
execution, seal, recovery or activation is introduced. The approved
[4e-17 contract](recognition-runtime-live-attempt-storage-writer-contract-4e-17.md)
remains authoritative; this review does not replace its target-entry requirement
with a control-only permission flag.

## 1. Current source contract and exact blockers

| Source/function | Actual boundary and consequence |
| --- | --- |
| `runtime_execution_coordinator.CoordinatorContext.create_attempt`, `_create_attempt`, `_publish_attempt`, `_attempt_entry` | Only the original private issuance continuation may create an attempt. Publication follows confirmed control commit and both cleanups. `CreatedAttempt.snapshot` is historical DATA; it cannot establish current admission or be imported as a writer credential. |
| Coordinator `_phase`, `_State.authorize`, `_evaluate`, `_finish` | Control-first `BEGIN IMMEDIATE`, target `BEGIN IMMEDIATE` then query-only, manager-owned final validation/control commit before target rollback/release. Target writes are forbidden. Every pre-attempt phase rejects existing attempts; only the exact pending creation graph is accepted during its own creation transaction. No post-creation writer phase exists. |
| `runtime_execution_attempt_schema.definitions`, `validate_created`, `check_rows` | History permits exactly sequence 1, state ATTEMPT_CREATED, explicit null predecessor, one matching creation audit. Updating/deleting/replacing records is forbidden. It cannot record WRITER_ADMITTED or later facts. |
| `runtime_activation_authority_issuance._subject_for_owner`, `_current`, `_final_mutations` | Current authentication, approval/ACK, full manifest/dependencies, stop, activation and protected readiness kernels are reusable through exact registered owners. They are not a general writer admission API; the five issuance writes and AUTHORIZED genesis remain unchanged. |
| `runtime_activated_owner._State`, `_read_parts`; `runtime_proposal_transaction._State.authorize` | Exact ownership, connections and reservation epochs are enforced. Query-only changes invalidate target epochs; borrowed read views cannot survive a write-mode transition. Activated observation is not execution authority. |
| `writer_boundary._local_lease`, `verify_local`, `acquire` | The local lease requires a protected legacy admission tuple, exact legacy claim and latest EXECUTING history with no seal. Production adds exact `ProductionOperationContext`, legacy approval/activation and deployment verification. `acquire()` returns a raw connection to trusted legacy writer code; it is not the permitted public runtime mutation interface. |
| `writer_boundary._lease`, `production_guard` | The other lease is disposable-only. A production authorization cannot use that path to bypass the local lease requirements. |
| `local_execution.execute_approved_operation`, `_verify`, `_existing`, `_seal`, `reconcile_operation` | Legacy flow commits a claim/EXECUTING prefix, reacquires target, mints a legacy lease, invokes the family writer, commits effects plus a legacy seal, then projects completion. No runtime attempt-to-legacy conversion is allowed. |
| `execution.execute_operation`, `_execute_claim`, `reconcile_operation` | Disposable/trust execution also requires durable legacy claims, EXECUTING and existing authorization/status/recovery contracts. Its automatic dispatch is not an inert runtime writer-admission operation. |
| `permanent.finalize`, `_writer_connection`, `_prepare`, `_verify_operation_records` | The useful checked family DML is embedded in `finalize`; there is no independent runtime-safe apply primitive. Authorization, connection acquisition, family writes, verification and optional commit are interleaved. Pure preparation/verification helpers alone cannot apply an operation. |
| `production_receipts.evidence`, `project`, `recovery_binding`; `local_execution._seal` | Readers resolve legacy claims/seals and legacy receipt/projection histories. Existing private manifest-keyed family outcomes do not bind a runtime attempt/activation incarnation. None may be relabeled runtime evidence. |
| `runtime_validation._identity_snapshot`, enrollment schema observation, `administration.observe_target` | Actual physical identity and the complete target schema hash must match the profile/binding. Installing target tables changes that hash; no runtime-table exemption exists. |

The concrete stop is the combination of: no isolated checked mutation kernel;
no post-creation protected owner/readiness interface; no accepted admission
history state; and no implemented, exactly specified target-entry/seal schema
and generation/enrollment transition. Calling the legacy writer today would
require fabricated legacy authority or expanding its accepted authority types.
Turning off query-only in the current owner would violate its checks. Neither is
approved. These are prerequisites for a later review, not missing names that can
be supplied by an adapter callback.

## 2. Required transition and durable decision

The conditional forward contract is:

```text
ATTEMPT_CREATED
  -> original coordinator provenance + fresh admission
  -> independently committed runtime target entry verified
  -> durable control WRITER_ADMITTED decision
  -> later fresh mutation-phase admission
  -> process-local single-use writer capability
```

WRITER_ADMITTED requires durable control history. It records a decision and its
committed target-entry evidence, not the existence/use of a Python token and not
family mutation. A crash can occur before a token is minted. Process-local flags
alone cannot fence independent restoration or another process.

The target-entry metadata transaction is a distinct prerequisite, as specified
by 4e-17. It performs target INSERT/COMMIT but no award/family DML. Therefore it
cannot be hidden inside a claimed zero-target-DML admission test. The subsequent
decision phase is query-only on target. This design slice executes neither.
Removing the entry phase to make admission appear read-only is prohibited.

## 3. Fresh authoritative validation

Before entry, admission, first family mutation and the final commit decision,
require the original active unpoisoned coordinator, PID, exact thread object and
identifier, current phase, exact connections and reservation epochs. Require the
original private continuation/result registration, never snapshot JSON, a public
`issue()` result, lookup authority, another session or reconstructed context.

Resolve the immutable attempt, its digest, creation history and audit; resolve
its exact authority ID/digest and unchanged AUTHORIZED genesis/consent chain.
Compare the complete durable scope against current actual scope:

- Operation/reference/digest, whole regenerated manifest/population, target,
  installation, binding/generation, runtime profile, owner/access, auth/MFA epochs.
- Original genuine primary/session scope, nonrevocation, authentication links,
  original consent deadlines and authority/attempt expiry. Creation <= current
  UTC < original expiry; paired wall/monotonic anomalies reject. No renewal.
- Exact activation sequence/event digest from `require_activated`, not a boolean
  or binding marker; exact proposal/ACK, effective runtime v2 approval/history.
- Full frozen dependency snapshot plus current READY recheck, actual physical
  target/control observations and unchanged full schema hashes, protected
  readiness/rehearsal and the exact inactive emergency-stop head.
- Complete attempt/entry/claim/recovery inventory, including target orphans after
  independent restore. No competing attempt, selected 4d claim in any disposition,
  legacy effect/seal conflict or blocking recovery. A selected attempt can be
  handled only by an exact stage-aware graph validator, never a skip-ID filter.

Use existing authoritative kernels through a separately reviewed exact owner
adapter. The current query-only read interfaces cannot simply be declared valid
under write mode. After family effects begin, ordinary dependency/manifest
regeneration is insufficient: the fixed post-effect validator must compare the
locked pre-effect baseline and exactly enumerated permitted new rows, while
external input facts and all auth/identity/activation/deadline facts stay fixed.
The current checkout has no such protected stage-aware mutation interface.

Every failure means **NO WRITER CAPABILITY** (or immediate invalidation of an
already minted one). Historical evidence does not override a failed current check.

## 4. Exact extraction boundary, not a legacy-authority adapter

In `permanent.finalize` (currently lines 263–340), retain its public gate,
production guard, authorization checks, `_writer_connection` ownership and final
authorization/optional-commit behavior for all existing callers. `_local_lease`
and `verify_local` must keep requiring genuine legacy claim/EXECUTING evidence.

The proposed extraction is one private **checked, connection-bound fixed-family
kernel**, not `writer_boundary.acquire()` and not individual INSERT helpers:

1. Validate exact historical manifest/reference/hash and supported family/policy;
   check schema and existing-operation integrity/idempotency semantics.
2. Regenerate the entire population with `_prepare` under the existing reservation
   and require exact equality before the first write.
3. Preserve the current rule validation/insertion, private operation insertion,
   First Look claim/provenance checks, Geography scope/snapshot/member/award/
   witness inserts, timestamp checks and whole-population atomicity.
4. Preserve `_verify_operation_records` and FK verification before returning
   bounded accounting DATA. Runtime dispatch must reject a preexisting outcome,
   not mistake the legacy idempotent return for permission to adopt it.

That kernel must neither open/close a connection, control a transaction, toggle
query-only, validate a fake legacy claim, nor write runtime lifecycle/seals.
Legacy `finalize` must perform its same authorization checks around it. A future
separate runtime dispatcher resolves the genuine capability internally and calls
the checked kernel on the manager's exact connection. It accepts no caller SQL,
connection, manifest, database path or mutation callback. A raw helper is not a
new supported public runtime API. Extraction parity and legacy security tests
must pass before any runtime caller is admitted. No extraction is implemented or
approved for immediate use by this review.

## 5. Future capability and ownership

The only proposed application-visible mutation interface is the fixed
`_apply_runtime_family(runtime_capability)` dispatch described in 4e-17, returning
bounded accounting DATA. The token itself exposes no SQL, cursor, connection,
queries, target selector, schema method, commit/rollback or recovery operation.

Its private registration must bind the original outer manager, PID, exact thread,
active mutation phase, exact control/target connections and epochs, immutable
authority/attempt bodies and digests, operation/manifest/population, target and
physical/schema scope, profile/generation/install/owner/auth/MFA scope, exact
activation event, entry/admission/intent evidence and every original deadline.
It is nonconstructible/nonserializable, cannot survive context exit/restart and
is spent before the one fixed family call, including a failed call. No second
token after rollback, expiry, uncertain outcome or failed admission.

The manager owns connections, target reservation/transaction, authorizers,
commit/rollback and cleanup. The kernel and token own none of them. Existing
3a, activated observation, issuance and legacy owners must not be widened or
impersonated. A separately reviewed mutation-phase owner must preserve original
coordinator provenance while making the necessary new ownership boundary explicit.

## 6. Ordered transaction protocol and query-only transition

No cross-database atomicity is claimed. Follow 4e-17's explicit durable prefixes:

1. Creation has already committed control with target reserved, then released
   target. Its old reservation is gone; no old epoch can be revived.
2. Original coordinator acquires control then target `BEGIN IMMEDIATE`, target
   query-only. Fresh validation precedes a fixed target-entry metadata write
   phase. Only its reviewed entry DML is enabled; commit entry with control held.
   Target commit ends that reservation and invalidates its phase evidence.
3. Reacquire target/query-only while control remains held, validate the committed
   entry independently, repeat fresh checks, append typed WRITER_ADMITTED history
   plus audit, and commit control with target reserved. Release/cleanup afterward.
   No family writer token is published from this released query-only phase.
4. In another ordered fresh phase, commit conservative TARGET_MUTATION_STARTED
   intent on control with target query-only/reserved, then release. Intent proves
   possible future effects, not that any family DML occurred.
5. Reacquire both reservations in order in the same original live outer lifetime;
   freshly validate entry, admission, intent, exact work and all current facts.
   Only the new mutation owner may perform the checked query-only OFF transition.
   It invalidates old borrowed views/epochs and binds the newly checked write
   phase/token to the post-transition epoch. There must be no intervening release,
   connection substitution, target DML or caller transaction control. Current
   shared read views are not usable after this transition; a new protected
   stage-aware read/validation contract is a prerequisite, not a bypass flag.
6. Mint/spend one token only after those checks. A later slice may execute the
   fixed family plus exact runtime seal in one target transaction. Hold control
   and target reservations through final post-effect checks and target commit.
7. Reacquire target/query-only, independently verify committed seal/actual records,
   then project target-commit/completion facts on control while target remains
   reserved through control commit. Release and cleanup afterward.

Every release/commit/query-only change invalidates the appropriate old epoch and
its tokens. Unplanned epoch loss, connection replacement, schema/physical drift,
poisoned owner or another target writer rejects; no silent reacquisition resumes
a capability. Different target writers serialize on BEGIN IMMEDIATE. No control
reacquisition while holding target, permanent reservation or arbitrary retry loop.

## 7. Activation and stop linearization

| Change boundary | Required outcome |
| --- | --- |
| Before admission | Reject changed incarnation/head; no token. |
| After admission, before mutation | Admission is historical; fresh final checks must reject. No token is recovered from the admission row. |
| During uncommitted family mutation | Hold the control reservation, so a conforming activation/stop updater cannot commit concurrently. Revalidate original deadlines and unchanged facts before target commit. If validation fails and the transaction is still uncommitted, manager rollback can discard effects. No claim that expiry automatically rolls SQLite back. |
| Immediately before target commit | Final checked scope, exact expected effects/seal and fresh time are required under both reservations. A failed check forbids commit. A commit call can still have an uncertain result. |
| After target commit, before control projection | A committed target outcome cannot be undone by a later activation change. Independently verify its committed evidence. Projection cannot grant a new writer or reinterpret an old incarnation as current. If scope/connection/control evidence is unavailable or changed, require recovery; do not erase committed history. |

The linearization is the checked commit decision under reservations, not a
promise about instantaneous wall time inside the operating system's commit call.
Noncooperating host/filesystem replacement is not solved by a SQLite lock; strict
identity checks and uncertain-outcome fencing still apply. No automatic restore,
rollback-after-commit or postcommit continuation is inferred.

## 8. Storage, evidence and fingerprint prerequisites

Keep the authority table and AUTHORIZED genesis codec unchanged. Keep the six
attempt fields and existing CREATED event/audit unchanged. The minimum future
control extension is a versioned attempt-history transition beyond sequence 1,
with contiguous sequences, exact previous digest, monotone timestamps, explicit
legal edges and **typed** entry/admission/intent/commit evidence linked to append-
only audits. Existing CHECK/trigger/reader definitions cannot accept that today.
Do not loosen them to arbitrary states/JSON or mutate historical rows.

The already approved target-table *inventory* is precisely:

- `recognition_runtime_execution_entries`: attempt ID PK, operation ID UNIQUE FK
  to its exact operation, authority digest UNIQUE, manifest digest UNIQUE, integer
  entered time, canonical body and UNIQUE body digest.
- `recognition_runtime_execution_seals`: attempt ID PK/FK to entry, manifest digest
  UNIQUE, integer committed time, canonical exact runtime receipt/seal body and
  UNIQUE body digest.

Both need immutable UPDATE/DELETE/REPLACE protection, all collision keys, exact
body/index agreement, bounded canonical/UUID/SHA/time/NUL validation and complete
cross-store scope resolution under reservations. There is no cross-file SQLite
FK/ATTACH shortcut. The entry must bind the exact authority/attempt/work/current
scope; the eventual seal must bind that entry and actual complete effects.

**Not yet defined/implemented:** exact target DDL/trigger SQL, typed entry/seal
and post-CREATED evidence codecs, recognized control manifest transition and
stage-aware inventory/readiness/post-effect readers. This review does not invent
their bytes and call the prerequisite complete. These require their own review.

Required additive migration path is 4e-17 sections 6–7, not hot installation:

1. Quiesce and settle conflicting attempts/recovery; require validated NOT_ACTIVATED
   or DEACTIVATED, expected generation G and exact old deployment/profile scope.
2. Install recognized inert control prerequisites via a transactional S2-to-next
   manifest/audit transition preserving old S0/S1/S2 reconstruction. Unknown or
   partial schema must fail. No generic ignore-new-table logic.
3. Prepare one exact reviewed target DDL/hash plan on control, revoke authentication
   and invalidate pending approvals nondestructively, and commit with query-only
   target held. Pending-plan rejection must exist in all relevant admissions.
4. Apply only that inert target DDL while control remains held; independently
   verify the committed full target hash, integrity/FKs and unchanged app rows.
5. Complete the plan with binding G+1, unchanged physical identities/owner/target,
   new schema hash, null profile and NOT_ACTIVATED. Commit control before release.
6. Transition-aware trusted runtime observation/enrollment establishes a new
   profile at G+2 with exact physical continuity and new hash. Fresh authentication,
   proposals, approvals, consent, readiness and explicit activation are required.

All target schema objects are fingerprinted by the unchanged observation helper.
No exclusion, caller-supplied hash, Slice H rebind, ordinary profile replacement
or old-authority rewriting can substitute. Current T attempts are historical
after this transition and cannot be made portable. The exact pending-plan schema,
guards and transition-aware enrollment interface remain missing; consequently
the next step cannot safely be an immediate writer mint on current attempts.

## 9. Lifecycle, crash and uncertain-outcome contract

| Fact/status | Minimum evidence and failure meaning |
| --- | --- |
| ATTEMPT_CREATED | Current immutable creation graph only; no writer. |
| WRITER_ADMITTED | Typed control decision referring to an independently verified committed runtime entry; no proof of a minted/used token. |
| TARGET_MUTATION_STARTED | Durable conservative intent before possible family effects; not proof that any statement ran. Later slice. |
| TARGET_COMMIT_KNOWN | Independently verified committed runtime seal plus exact actual records and accounting, then typed control projection. Later slice. |
| COMPLETED | Verified complete outcome and projection; target commit alone is insufficient. Later slice. |
| FAILED | Terminal no-effects failure only after independently establishing rollback/no effects and fencing the dead writer. Never for uncertain commit. Later reviewed recovery/failure boundary. |
| RECOVERY_REQUIRED | Durable precise evidence when possible; no retry/resume/adoption permission. Later slice. |
| UNCERTAIN | Conservative inspection status for unresolved commit/cleanup/connection; cannot require that an uncertainty row itself successfully committed. |

Crash before entry/admission: retain CREATED or whatever exact durable prefix
exists, publish no token, no automatic retry. Crash after admission or before
mutation: token cannot survive; entry/decision do not authorize a new process.
Crash during family mutation: SQLite may roll back an uncommitted transaction,
but inspect independently; absence of a control completion record is not proof
of rollback. Committed entry remains an irreversible work fence.

Target commit succeeds/control projection is uncertain: preserve target evidence,
no re-execution; separately authorized inspection/reconciliation is required.
Control admission/intent commit succeeds/target commit is uncertain: control
intent is not a target receipt; inspect target entry/seal/actual rows. Never write
a target-commit-known/completion record before independently verifying commit.
Connection loss, restart, changed activation or cleanup failure poisons all live
tokens. Do not infer a target commit from missing control data or infer no effects
from a missing seal after independent restore. No blind retry or automatic
adoption; this review defines no recovery implementation.

## 10. Concurrency and separation

Same attempt/authority/operation: immutable attempt/authority UNIQUE keys plus
target entry keys and serialized control reservations must allow at most one
durable admission and one original live token. Same-target distinct work also
serializes; any other incomplete attempt/recovery remains a blocker. An identical
duplicate yields historical inspection only, never another token. A conflicting
duplicate rejects. A failed/uncertain call spends the original lifetime; no retry
loop, changed busy timeout, replacement claim or renewed authority. BUSY/LOCKED
is a rejection, not permission to reconstruct provenance.

Writer admission is not mutation; mutation is not commit; target commit is not
completion; completion is not activation. Legacy claims, EXECUTING, receipts and
recovery must remain unchanged. A runtime-specific fixed dispatcher and separate
target entry/seal evidence make legacy fabrication unnecessary in principle;
the current public writer does not provide that boundary today.

## 11. Required focused test contract for later slices

No new mutation test or implementation is added here. The requested existing
legacy execution tests exercise only their disposable fixtures, not production
or a new runtime writer. Future admission-only tests must use a separately
established valid entry fixture and assert zero target DML/DDL/COMMIT during the
query-only admission-decision phase; entry installation tests are separate and
must not misreport their metadata INSERT/COMMIT as zero target impact.

| Focused test | Required assertion |
| --- | --- |
| Genuine original lifecycle/valid entry | Real enrollment/auth/proposal/ACK/v2 approval/consent/coordinator/CREATED chain and exact entry; one admission decision, no family DML/completion. No provider that manufactures authority. |
| Expired attempt/authority, clock rollback/anomaly | Reject at exact deadline, no renewal, no capability. |
| Wrong attempt/authority ID, digest, state or history | Exact durable graph rejected; no token from matching operation hash alone. |
| Activation change at every phase | Changed-before-admission and pre-effect head changes reject; two-connection tests prove updater exclusion while reservations held; postcommit change never erases facts or grants another writer. |
| Profile/generation/install/target/owner/auth/MFA changes | Alter actual durable state or real observations after creation, reject without capability. Validate original credentials, revoked/expired sessions and consent too. |
| Proposal/ACK/approval/dependency/readiness/stop changes | Recheck authoritative records/manifest; exact changed stop head rejects even after clear. No mocked happy-path collector or supplied readiness boolean. |
| Each physical field and schema mismatch | Target/control hostname, canonical path, device, inode, schema and malformed/NUL/type values reject using unchanged helpers. |
| Reservation loss/epoch or connection replacement | Replace/release handles or change epochs before decision, first mutation and commit; reject, invalidate all cached views and publish no token. |
| Concurrent/duplicate admission | Separate actual DB connections/processes; at most one durable decision/token. Preserve BUSY/LOCKED. No mutex as the authority fence. |
| Wrong thread/PID/outer, restart, serialization/forgery | No import/adoption/constructor/public-issue conversion, no callbacks invoked before exact ownership validation, no capability restored from JSON. |
| Every mutation/commit/cleanup fault | Exact rollback or verified durable prefix; no token on uncertainty, no automatic retry; missing control data never proves target commit/no effects. |
| Minimal interface | No SQL/connection/cursor/query/path/transaction/schema API; spend once before fixed dispatch; invalidate at exit/epoch/expiry. |
| Legacy isolation and absent downstream authority | Symmetric populated legacy/protected snapshots and schema unchanged; no legacy claims/EXECUTING/recovery/receipt reinterpretation, no seal/completion/activation from admission. Existing legacy writer checks still reject runtime objects. |
| DELETE/WAL and zero-impact admission | Query-only target reservation retained through control decision commit, competing writer blocked, target logical dump and DML/DDL/COMMIT trace unchanged. No checkpoint/retry workarounds. |
| Later extracted-kernel parity | Separate reviewed disposable family-mutation tests must prove unchanged atomic First Look/Geography behavior and exact post-effect accounting; they are not authorized by this slice. |
| Schema/enrollment prerequisites | Partial/unknown DDL, migration rollback, pending-plan crash prefixes, source/destination hashes and generations, auth revocation/approval invalidation, no portability of old operations/A/attempts. No hot schema repair. |

## 12. Decision and required next review

Blocked for immediate minimal writer-admission implementation. First separately
review the exact checked-kernel extraction and protected mutation-owner interface,
then the typed admission/entry lifecycle storage and target schema/enrollment
transition prerequisites. Neither bypassing legacy checks nor broadening current
query-only contexts is an acceptable implementation. Only after those prerequisites
are specified, implemented and independently validated can the minimal runtime
writer-admission implementation be the next executable boundary.

Validation: the requested attempt-creation, coordinator and legacy execution
baseline passed together: **123 passed, 70 subtests passed in 5550.41 seconds**.
The guarded disposable-only run used `-B`, `-q`, `-p no:cacheprovider` and `-x`
(stop on the first failure to avoid failed-fixture patch contamination). No
failure or expiry isolation was required. `git diff --check` and the new
document's trailing-whitespace check passed. These are baseline checks, not
proof of a writer-admission implementation; none is introduced by this slice.
No full suite or recognition/deployment-family run was performed. No hosted or
production resources or real deployment keys were accessed; no commit or push
was performed. Only this document was added for Slice 4e-20; preexisting working
tree changes remain outside this slice.

PRODUCTION AUTHORIZATION: BLOCKED
PRODUCTION EXECUTION: BLOCKED
PRODUCTION ACTIVATION: BLOCKED
