# Slice 4e-17: live-attempt storage, transition and fixed writer interface

**APPROVE 4e-17: design contract complete; runtime execution remains blocked.**

Design only. No runtime coordinator, attempt producer, writer capability,
execution, schema installer, target migration, seal or recovery is implemented.
The only executable change in this slice is the disposable consent-concurrency
test correction described in section 16. Existing production gates remain shut.

This contract makes the future bridge explicit. It does not make an already
returned 4e-15 inspection object executable or authorize adopting existing
standalone authorities. Implementation boundaries below require separate review.

## 1. Authority to attempt: original continuation only

Transition domain: `recognition-runtime-authority-to-live-attempt-v1`.

Only the trusted runtime owner, authenticated by the **same originating** current
primary/session scope, may start an attempt. The owner must be the current
verified installation owner, with unchanged auth/MFA epochs and exact enrolled
runtime observations. The authority must be a genuine newly issued 4e-15 record
for the current validated activation incarnation, with its exact owner-consent
and confirmation-consumption chain. Nonce possession or lookup data is not
authentication. Browser identity claims establish nothing.

The future coordinator must establish an opaque outer lifetime **before** fresh
issuance. A private, separately reviewed issuer integration may notify that
original manager of one newly committed authority only after control commit and
both issuance cleanups are confirmed. It must not expose a callback/provider
that can manufacture authority. Public `issue()` and duplicate/inspection APIs
retain their present inspection-only meaning. No passing an `IssuedAuthority`
back into a loader, creating an outer manager after issuance, or installing an
object into an old registry is permitted.

The manager then opens its own control-first/query-only-target reservation and
performs section 3 checks. It creates one attempt, its CREATED genesis and audit
atomically on control; target remains reserved through control commit and is
released afterward. Only confirmed commit and cleanup permit the original outer
manager to retain a process-local continuation. An exception publishes none.
The private original-issuance notice is single-use. A failed or uncertain
authority-to-attempt transition permanently poisons that outer lifetime; absence
of an attempt row is not permission to reconstruct or retry the continuation.

Fresh consent is **not repeated** within this one original continuation: the
specific 4e-14 decision remains mandatory and must still meet its original
deadline. Fresh authentication validation is required at every phase; another
login/session cannot substitute for or renew the originating scope. 4e-15 data
alone is insufficient. Existing standalone issued authorities remain historical
and cannot be retroactively supplied with a live continuation.

The authority body and its AUTHORIZED genesis never change. Existence of a
unique attempt is the irreversible single-winner fence; AUTHORIZED no longer
means eligible to create another attempt. Even failed attempts cannot release
that uniqueness. Expiry, revocation or later completion changes effective
eligibility, not immutable history. No repeated consent creates a replacement
authority for the same operation/manifest; normal future work requires a genuinely
new reviewed preparation/proposal/approval, not a portable copy of old work.

## 2. Exact immutable attempt identity

Canonical body, exactly:

```text
format = recognition-runtime-live-attempt-v1
attempt_id
authority_id
authority_sha256
created_at_utc
expires_at_utc
```

IDs are server-generated random canonical UUIDs (the authority ID is copied).
Use existing bounded canonical JSON/digest rules; digest is external to the body:
`attempt_sha256 = digest(body)`. Creation is UTC whole-second canonical text,
authority issue <= creation < expiry, and expiry equals the authority's original
expiry exactly. No new 120-second window or configurable grace.

Resolve the exact authority ID/digest; do not trust an unresolved hash. It binds:

| Required scope | Existing authority source, unchanged |
| --- | --- |
| Operation, digest, event/preparation, family, manifest and population | Entire `operation_reference` |
| Target, installation, profile, generation, binding, owner and auth/MFA epochs | Entire `runtime_target` |
| Proposal and ACK | Entire `operation_reference.proposal_reference`, resolved through durable readers |
| Approval and effective APPROVED history | Entire `approval` |
| Activation incarnation | `activation.sequence` and `activation.event_sha256`, resolved against current validated ledger |
| Physical target/control identity and target schema | Entire `physical_snapshot` |
| Originating authentication, consent, dependencies, stop and readiness | Corresponding complete authority objects |

No duplicated operation/target/profile fields are needed in the attempt body.
Any SQL index or cached scope is compared to the resolved authority, never a
second source of truth. PID, exact thread object, manager identity, active/poisoned
phase, exact connections and reservation epochs exist only in the private live
registry. No SQL handles, public constructors, serialization or restart import.

## 3. Fresh admission and unchanged readers

At attempt creation, each pre-effect reservation reacquisition, immediately
before granting a writer and before first mutation, validate all pre-effect facts below. Before
target commit repeat the unchanged scope/deadline facts and the exact post-effect
comparison specified after the list:

- Current exact control schema/history/audit and authority/attempt graph.
- Actual hostname/path/device/inode/schema against the enrolled profile and
  authority; unchanged installation, target UUID, binding/generation, owner/access,
  auth epoch and MFA epoch. Preserve lossless physical values and all NUL rules.
- Current genuine originating primary/session records, runtime-auth scope links,
  nonrevocation, original expiry and original owner-consent evidence/deadlines.
- Exact current activation ledger incarnation/consumed confirmation; no boolean
  or `production_state` marker substitutes for `require_activated()`.
- Exact proposal/ACK, effective v2 approval/history, full frozen dependencies plus
  current READY recheck, regenerated whole manifest/population and supported policy.
- Exact inactive emergency-stop head and no operation block; set-then-clear is a
  changed head. Complete claim/recovery inventory, not merely the selected row.
- No selected 4d-1 claim in any disposition, legacy claim/history/seal/effects
  conflict, other attempt, target entry conflict or preexisting family outcomes.
- Current protected readiness under a new exact execution-owner interface,
  manager/PID/thread/connection/reservation epochs, phase and one-use state.
- Fresh paired wall/monotonic time, original authority/proof/ceremony deadlines;
  rollback/anomaly rejects. Sample time last before each effect commit decision.

The current 3a, activated-read-only and issuance owners are not widened. A new
owner registers a distinct protected read interface; it may reuse pure identity,
auth and canonical readers, not impersonate another context. Stage-aware readers
must validate the selected genuine attempt's exact entry/effects rather than
blindly requiring a pristine proposal forever or skipping the selected operation.
Other incomplete attempts always block. Existing preactivation readers keep
their current fences. Failed checks grant no writer and roll back pending effects.
Enumerate all runtime target entries/seals, including orphans whose control
authority/attempt is absent after independent restore; missing control provenance
is a recovery blocker, not a reason to omit the target from inventory. Keep 4e-7's
historical claim-only disposition separate from this new runtime target inventory.

Post-effect validation must not require an ordinary dependency recheck to call
newly inserted permanent records unchanged. Under the same uninterrupted control
and target reservations, retain the exact pre-effect dependency/manifest baseline;
verify that external input facts remain identical and that the only changes are
the fixed, fully enumerated family outcome rows for this exact manifest and its
runtime seal. Existing rows are not updated/deleted; compare actual new row sets,
provenance/membership/witnesses and full accounting to the approved manifest.
Recheck schema, actual physical observations, all current auth/owner/epoch/
activation/stop facts and original deadlines. Any extra/missing/changed row rejects
and rolls back. This is a separately reviewed stage-aware validation interface,
not a skip-dependencies flag or a blanket exclusion for the selected operation.

## 4. Minimum durable storage

Process-local state alone cannot fence a concurrent coordinator or restored
control snapshot. Use four separate runtime tables; no mutable authority row or
generic current-state flag. Names are new contracts, not existing callable APIs.

| Store/table | Columns and required keys |
| --- | --- |
| Control `recognition_runtime_execution_attempts` | `attempt_id TEXT PRIMARY KEY`, `authority_id TEXT NOT NULL UNIQUE` FK to authorities, `authority_sha256 TEXT NOT NULL` FK to authority body digest, `created_at INTEGER NOT NULL`, `expires_at INTEGER NOT NULL`, `body_json TEXT NOT NULL`, `body_sha256 TEXT NOT NULL UNIQUE`, `audit_sequence INTEGER NOT NULL UNIQUE` deferred FK to admin audit. |
| Control `recognition_runtime_execution_attempt_history` | `attempt_id TEXT NOT NULL` FK to attempts, `sequence INTEGER NOT NULL`, `state TEXT NOT NULL`, `at INTEGER NOT NULL`, `previous_sha256 TEXT NULL`, `body_json TEXT NOT NULL`, `body_sha256 TEXT NOT NULL UNIQUE`, `audit_sequence INTEGER NOT NULL UNIQUE` deferred audit FK; PK `(attempt_id,sequence)`. |
| Target `recognition_runtime_execution_entries` | `attempt_id TEXT PRIMARY KEY`, `operation_id TEXT NOT NULL UNIQUE` FK to existing operation contract, `authority_sha256 TEXT NOT NULL UNIQUE`, `writer_manifest_sha256 TEXT NOT NULL UNIQUE`, `entered_at INTEGER NOT NULL`, canonical `body_json TEXT NOT NULL`, `body_sha256 TEXT NOT NULL UNIQUE`. |
| Target `recognition_runtime_execution_seals` | `attempt_id TEXT PRIMARY KEY` FK to entry, `writer_manifest_sha256 TEXT NOT NULL UNIQUE`, `committed_at INTEGER NOT NULL`, canonical runtime receipt/seal `body_json TEXT NOT NULL`, `body_sha256 TEXT NOT NULL UNIQUE`. |

Authority UUID and digest FKs must resolve to **the same** authority row.
Creation/expiry equal decoded body, satisfy the authority interval and cannot be
renewed. Attempt creation requires one matching CREATED genesis and typed audit
with deferred graph completeness, following the existing 4e-12 insert/genesis/
audit pattern. Creation audit insertion checks the complete graph; neither an
orphan attempt nor a reused earlier audit can commit successfully.

All four tables require immutable UPDATE/DELETE/REPLACE guards for every unique
collision key, exact schema validation, canonical UUID/lowercase SHA/JSON checks,
integer-not-boolean UTC limits and complete body/index agreement in readers.
No float/numeric cast for physical device/inode observations. History requires
contiguous sequence, explicit null genesis predecessor, exact prior digest,
monotone time, allowed forward edges and typed evidence. No cross-store SQLite
FK or ATTACH: resolve control references under both reservations.

Attempt-to-authority uniqueness inherits operation/manifest single-winner keys
from the immutable authority table. Target entry duplicates those work fences
in the store that survives independent control restore. The seal's manifest and
scope must match its entry. These are required final schema constraints, not
permission to install DDL or define later evidence codecs in this slice.

## 5. Lifecycle: facts versus intent

Keep `recognition_runtime_execution_lifecycle` unchanged: AUTHORIZED genesis only.
Attempt history is a different stream, not an extension of 4d-1 claim history.

| Meaning | Representation and what it does not prove |
| --- | --- |
| ATTEMPT_CREATED | Durable attempt + matching creation event/audit, once. Does not grant writer authority. |
| WRITER_ADMITTED | Durable decision only after independently verified committed target entry and fresh checks. Actual local token existence/use is process-local; a crash can follow the decision before token creation. |
| TARGET_MUTATION_STARTED | Durable conservative intent before possible effects. Actual first target statement is observable only in the running process until effects/seal commit. The label alone must never claim DML occurred. |
| TARGET_COMMIT_KNOWN | Durable control projection only from a verified committed runtime seal and actual records. |
| COMPLETED | Durable projection after exact full-population accounting/evidence verification. No new target writer call. |
| FAILED | Durable terminal `FAILED_BEFORE_COMMIT` only with independently established rollback/no effects and fenced dead writer. Never use it for uncertain commit or postcommit projection failure. |
| RECOVERY_REQUIRED | Durable when possible, with precise reason/evidence references. No resume authority. |
| UNCERTAIN | Conservative inspection status whenever commit/cleanup/connection outcome is unresolved; may remain process-local or derivable from an incomplete durable prefix if control is unavailable. It cannot be required to have committed its own row. |

Normal forward edges: ATTEMPT_CREATED -> WRITER_ADMITTED ->
TARGET_MUTATION_STARTED -> TARGET_COMMIT_KNOWN -> COMPLETED. Any precommit stage
may become verified FAILED_BEFORE_COMMIT or RECOVERY_REQUIRED. A known-commit
stage may require recovery but cannot become a no-effects failure. COMPLETED and
FAILED_BEFORE_COMMIT are terminal. Recovery may project verified commit/completion
or verified no-effects failure only through a separately reviewed owner ceremony;
no edge authorizes another writer. Unknown/malformed history rejects.

For the first storage-only implementation, support only immutable attempt
identity and ATTEMPT_CREATED genesis; reject later state/evidence writes. Later
history expansion needs an explicit reviewed schema/codec transition, not a
permissive evidence dictionary. The existing AUTHORIZED three-field object is
never extended. No redundant ADMITTED, readiness TTL or mutable uncertainty table.

Exact creation event fields are `format`, `attempt_id`, `attempt_sha256`,
`sequence`, `state`, `at_utc`, `previous_sha256`, `actor_id`, `reason`.
Format is `recognition-runtime-attempt-created-event-v1`, sequence is integer 1,
state is ATTEMPT_CREATED, predecessor is explicitly null, time equals the attempt
creation time, actor equals the authority owner, and reason copies the exact
authority producer-ceremony reason. Its digest is external. Creation audit action
is `runtime_execution_attempt_created`; its exact subject fields are `attempt_id`,
`attempt_sha256`, `event_sequence`, `event_sha256`, with that actor/time. Both new
rows reference that one deferred audit. Body limit is 4096 UTF-8 bytes for attempt
identity and 16384 for the creation event (including the existing bounded reason).
Use existing UUID/SHA/time, duplicate-key, canonical JSON, NUL and integer rules.
No later lifecycle evidence format is defined by these genesis-only codecs.

## 6. Exact fingerprint inventory

| Function / reader | Objects included and consequence |
| --- | --- |
| `enrollment._schema(conn)` | Requires exactly one named on-disk `main`. Hashes ordered `[type,name,tbl_name,sql]` rows for **all** `sqlite_master` names not `sqlite_%`, plus PRAGMA application_id and user_version. Includes unrelated application tables/indexes/views/triggers; raw SQL text is significant. Excludes internal `sqlite_%` objects and all row contents. |
| `administration.observe_target()` | Uses that full schema hash plus actual strict target identity. |
| `runtime_validation._identity_snapshot()` | Requires observed target hash == immutable current profile hash == binding target hash, plus actual strict physical observations. No extension-table exception. |
| `runtime_execution_claim_schema.manifest()` | Hashes name -> whitespace-normalized SQL for all non-`sqlite_%` control objects, excluding only an explicitly supplied, verified historical set. Does not include data, application_id or user_version. |
| `administration_schema.check_control()` | Compares the exact complete set of recognized control definitions and normalized SQL; unknown/partial extension fails. Then validates profile/claim/authority graphs. |
| `runtime_activation_authority_schema.check_manifest_transition()` | Verifies the exact 4e-12 additive definitions and one migration audit linking prior/current control manifests. Present reader expects its installed hash to equal current full manifest. |
| `historical_claim_manifest()` | Reconstructs the 4d-1 manifest only after verifying that recognized 4e-12 transition. Not a generic ignore-new-tables mechanism. |

Therefore control-only attempt installation leaves target fingerprint unchanged
but still needs a recognized **control** manifest transition. Target entry/seal
installation necessarily changes the target fingerprint even with zero award
DML. Do not change any hash algorithm, normalize target SQL differently, exclude
runtime tables or replace observations with a caller's expected hash.

Control migration chain must explicitly verify S0 (4d-1) -> S1 (4e-12) -> S2
(attempt extension): exact definitions, one typed installation audit per step,
strict audit order/scope, previous/installed digests, no unknown DDL. Historical
readers reconstruct S1/S0 by subtracting only the already validated extension
sets. Old audit records and authority bodies are never rewritten. Partial
extension, altered trigger, missing audit or unrecognized later manifest rejects.
The later schema-transition guards in section 7 require their own recognized
S2->S3 extension/migration audit before preparation; S3 is not automatically
accepted by an S2 reader. No generic suffix subtraction or accept-future flag.

## 7. Target storage decision and versioned enrollment transition

Independent target entry and effect-commit evidence are necessary for this
protocol. A control intent cannot prove a target commit or fence an independently
restored control file. Existing private manifest-keyed outcomes do not bind a
runtime authority/attempt/incarnation. Existing legacy seals FK to legacy claims.
`recognition_operation_receipts` is a derived legacy receipt/history contract;
its readers validate legacy completion, and current runtime proposal readers
explicitly reject any such row. Reusing it as authoritative runtime storage would
change its meaning and affected-reader contract, not demonstrate zero change.
This design chooses separate runtime target storage, not that shortcut.

Versioned future ceremony: `recognition-runtime-target-schema-transition-v1`.
It is a proposed narrowly scoped DDL/enrollment transition, **not** Slice H,
arbitrary profile rotation or recovery. Exact target definitions and evidence
codecs must
receive their own review before its implementation. Required ordering:

1. Quiesce deployment and settle all existing claim/entry/recovery states. Require
   a validated nonactive ledger (`NOT_ACTIVATED` or explicit `DEACTIVATED`, not
   merely SUSPENDED), strict old deployment identities, source binding/profile,
   installation/target/owner and exact expected generation G. No executing/uncertain
   attempt may be transformed by this ceremony. Preserve existing history.
2. Install recognized inert control prerequisites first through an explicit local
   transactional manifest transition. This changes no target schema or generation
   and creates no authority/attempt. Verify backup/restore and exact DDL plan.
3. Trusted local operator supplies explicit reason, plan UUID, source binding and
   profile digests, old/new full target schema hashes and exact added-definition
   manifest digest. A preview computes the new hash using the unchanged target
   fingerprint function over the reviewed schema; a submitted SHA is never proof.
   No unrelated table/trigger alteration or application_id/user_version change.
4. Control-first/query-only-target prepare transaction validates old scope and
   appends `runtime_target_schema_transition_prepared` with exact source/plan,
   revokes existing auth/step-ups/confirmations and invalidates pending approvals
   nondestructively. Commit control while target remains reserved. A recognized
   pending plan is an additional fail-closed fence in all runtime authority,
   authentication, readiness and activation admissions; quiescence alone is not
   the machine-enforced fence. Only trusted explicit inspection/completion of
   this exact plan is allowed. No worker/startup automatic completion.
5. Control BEGIN IMMEDIATE, then target BEGIN IMMEDIATE. Revalidate the exact
   prepared plan/G/old scope and identities; apply **only** reviewed entry/seal
   DDL in a target savepoint/transaction, validate exact resulting schema/Hnew,
   integrity/FKs and unchanged application rows; commit target with control held.
   Reacquire target/query-only and independently verify the committed schema and
   identity. No awards or entry/seal execution rows are created by installation.
6. While both reservations remain held, append binding G+1 with exact prior
   digest, same deployment physical observations/installation/target/owner,
   Hnew and `runtime_profile_sha256=NULL`, `production_state=NOT_ACTIVATED`.
   Append `runtime_target_schema_transition_completed` binding source G/profile,
   prepared-plan audit digest, installed DDL/hash, destination G+1/binding digest
   and operator/reason. Recheck auth revocation and approval invalidation, commit
   control, then release target. New generation invalidates old authority scope;
   no authority body, old profile row or operation body is modified.
7. Current runtime remains blocked because no profile is enrolled. Explicit new
   challenge issuance at G+1, real runtime observation and private-log operator
   review, hidden nonce and one-use approval establish a new profile at G+2
   through a transition-aware initial-enrollment ceremony. Require exact same
   runtime physical tuple as source profile and exact Hnew; this ceremony does
   not authorize host/device/inode/path changes. The collector never enrolls
   itself. Preserve existing 2a/2b/2c formats and their standalone semantics.
8. New transition-specific profile insertion guards/history validation must tie
   this null-profile source binding to the unique completed plan/old profile and
   enforce that exact physical continuity. Do not expose a generic null-profile
   reset API or rely only on pretransaction review-file comparison. These stricter
   recognized guards are part of the separately reviewed transition migration.
   Enrollment and its revocation/audit remain atomic, target query-only, control
   committed before target release, as in 2c.
9. Re-enroll/currently authenticate through approved primitives, prepare genuinely
   new operations and obtain their approvals, deployment verification and explicit
   activation under the new generation/profile. No old operation, approval,
   authority or attempt becomes portable. Reusing old consent is forbidden.

This deliberately costs two generation advances: G+1 is the disabled schema
transition binding; G+2 is normal profile enrollment from a null-profile source.
It matches the existing `_history()` requirement that a profile's source binding
has a null profile and destination generation is source + 1. Existing initial
enrollment refuses nonnull-profile replacement. Current code has no step 4-8
ceremony; directly calling 2c or Slice H is not an upgrade implementation.

If target commit is uncertain or succeeds before control completion, retain the
prepared fence and report recovery-required. Inspect exact plan and actual
schema under fresh reservations; do not automatically reapply DDL, infer no
commit, clear the plan or activate. A dedicated manually reviewed completion
policy is needed before resuming that installation. Cross-store atomicity is
not claimed. A new installation may instead install all reviewed target storage
before its first deployment binding/profile; it must not clone old authority
metadata and label itself fresh.

Consequently every pre-transition 4e-15 authority remains historical and cannot
be the first executable authority after this target upgrade. Future execution
starts with newly prepared/consented scope after the transition, not conversion.

## 8. Concurrency and idempotency of the transition

Control BEGIN IMMEDIATE serializes contenders. UNIQUE authority_id in attempts
selects one durable winner; authorities already enforce unique operation and
manifest. Entry keys independently fence target work. A loser may receive a
verified duplicate/conflict or bounded SQLite BUSY/LOCKED rejection; neither
creates a capability. No retry loop or changed busy timeout is part of the
contract. Different operations on one target serialize on target reservation.

Same authority/attempt: inspection only, no new token or second writer call.
Completed: independently verified receipt data only. Failed: terminal fence.
Uncertain: owner inspection, never replay. Expired/stale activation/profile/
generation/auth: reject; no renewal or scope transfer. The schema transition
plan is likewise unique per source generation/pending plan under reservations;
stale/concurrent callers cannot complete another plan or advance generation twice.

## 9. Target reservation and phase ownership

Future execution uses a new exact registered manager, not a widened 3a/4d/4e-6
or issuance context. Each phase acquires control then target BEGIN IMMEDIATE;
target starts query-only. Manager alone owns SQL authorizers, phases, commits,
rollbacks and connection cleanup. Each commit/release/query-only change advances
the relevant reservation epoch and destroys borrowed phase views/tokens.

After ATTEMPT_CREATED control commit, release and reacquire control-first/target-
second, perform fresh checks, and enter only the fixed target-entry metadata
phase. Commit exact entry with control held. Reacquire target/query-only, verify
committed entry and scope; record WRITER_ADMITTED on control while target stays
reserved. Release after confirmed control commit. Persist conservative mutation
intent in a later freshly checked phase, also control-first/query-only-target
through control commit, then release and reacquire both in order. Never reacquire
control while holding target: no lock inversion or permanent reservation.

Only final fresh admission for the same genuine outer lifetime may enable the
fixed family-plus-runtime-seal DML phase, remove target query-only and spend one
runtime writer capability. Hold both reservations through target effect/seal
commit; reacquire target/query-only, verify durable outcomes, then control
projections commit before target release. Commit/cleanup uncertainty invalidates
continuation. Target reservation gaps are fenced by entry/attempt uniqueness
and full fresh validation, not an old eligibility snapshot.

## 10. Fixed writer interface and minimal extraction

`permanent.finalize()` is the lowest useful checked family transaction. It
currently calls `production_guard`, `verify_local`/`verify`, acquires a connection
through `writer_boundary.acquire`, regenerates the whole manifest with `_prepare`,
executes fixed First Look/Geography inserts, checks actual records/FKs and repeats
authorization. No independent runtime-safe mutation function exists today.

Proposed private interface: `_apply_runtime_family(runtime_capability)` with no
caller-supplied database, manifest, operation, connection, SQL or callback. An
exact private registry resolves the original live manager, authority/attempt,
operation and approved manifest. The internal dispatcher spends the token once
and invokes a factored checked fixed-family kernel on the manager's exact target
connection. The public result is bounded accounting data, never a handle.

Minimal extraction preserves the algorithm and all legacy pre/postconditions;
legacy `finalize()` retains its existing authorization/connection ownership and
performs its same checks around the common kernel. A separate runtime dispatcher
performs section 3 checks and current-entry/phase/epoch validation before entry
and after family work. The shared kernel must enforce schema/manifest/reference,
full frozen regeneration, conflict/idempotency behavior, supported family/policy,
First Look provenance, Geography scope/member/witness integrity and FK checks.
It cannot commit, toggle query-only, insert lifecycle/seals or accept arbitrary
SQL. A raw `(connection, manifest)` helper is not exposed as a runtime API.

The genuine runtime capability is nonconstructible/nonserializable, PID/exact-
thread/outer-lifetime/phase/connection/reservation-bound, exact target/operation/
authority/attempt/manifest/incarnation/deadline-bound and single-use. No minting
from JSON, consumed claim, immutable authority lookup or old registry insertion.
No writer_boundary.py change or legacy accepted-type expansion is required by
this design. Kernel extraction/dispatch still needs its own focused security
review and real disposable lifecycle tests before implementation approval.

## 11. Activation fencing

Any changed activation incarnation, profile, generation, installation, owner,
auth/MFA epoch or stop head rejects new admission and invalidates an unspent
token. Recheck actual physical identity/schema too. Expiry is nonrenewable.

Compliant control/target state writers serialize behind reservations held
through final validation and target commit. A queued stop request is not yet a
committed stop. If a change commits in a released-reservation gap, fresh checks
reject continuation. Before effect commit, an observed mismatch causes rollback
of uncommitted effects; no independent thread forcibly rolls back another
transaction. After verified target commit, a later activation change cannot
erase historical completion and cannot authorize further writes. No unsupported
asynchronous kill/adopt/cancel behavior or borrowed legacy no-cancellation rule.
Trusted out-of-band filesystem administration must quiesce processes; SQLite
locks do not prevent a host administrator replacing files.

## 12. Completion, seal and distinct commit facts

Target entry proves entry/identity, not effects. Control mutation intent proves
possible start, not the first DML. Runtime target seal and **all** family effects
share one target transaction/commit. Verify the committed entry, exact seal and
actual historical records under a fresh reservation before projecting known
target commit on control. COMPLETED additionally requires exact full accounting:
authorized == successful, zero active quarantine/other/unaccounted outcomes.

Original deadlines gate permission to commit effects. Postcommit historical
verification must not ask pre-effect dependency/READY readers to erase those
effects or require authority to remain unexpired forever. The original manager
may finish exact fact-only control projection while retaining its original
control reservation/lifetime; postcommit target access stays query-only and
cannot mint another lease. If it loses that reservation/lifetime or cannot
complete verification/cleanup, stop and leave a recovery-required projection
gap. A later process needs fresh owner authentication and the separately reviewed
manual projection/recovery contract; it cannot adopt execution. Later expiry or
revocation neither erases a valid target seal nor authorizes further effects.

The future distinct runtime seal/receipt binds authority ID/digest, attempt ID/
digest, entry digest, exact operation/manifest/population, target/install/profile/
generation/binding, actual physical/schema snapshot, activation sequence/event
digest, approval/effective history, proposal/ACK, original auth/consent scope,
dependency/stop/admission comparisons, timestamps and actual outcomes/evidence.
No secrets or durable PID. Exact later evidence codecs are a later slice, not
invented by extending AUTHORIZED genesis or reinterpreting production receipts.

## 13. Crash, uncertainty and recovery

| Boundary | Required behavior |
| --- | --- |
| Before confirmed attempt commit | Publish no continuation if uncertain. Inspect durable control state; absence in one snapshot does not authorize retry. |
| Attempt committed, before entry | Unique attempt fences restart/duplicates. No adoption even if authority is still unexpired. |
| Entry committed, control admission uncertain | Orphan entry requires inspection; no automatic promotion. |
| Admission or mutation intent committed, no effects yet | Incomplete prefix remains a fence. A missing seal does not establish that a writer cannot still run. |
| Crash during uncommitted effects | SQLite rollback is expected, but known failure requires independent inspection and fenced/dead original writer. |
| Target commit known, control projection uncertain | Target evidence may establish effects; control remains uncertain until independently inspected/projected. No rerun. |
| Control intent known, target commit uncertain | Control proves no target outcome. Verify entry/seal/outcomes; never infer from return/exception alone. |
| Connection loss, cleanup failure or restart | Invalidate all local objects. Fresh owner authentication permits inspection, not recreation of continuation. |
| Schema transition interrupted | Keep pending plan/recovery fence; no startup migration, profile reset, auto completion or adoption. |

Manual recovery is a future separate authenticated owner ceremony with fresh
reservations, explicit reason, independent writer fencing and exact evidence.
It may project verified historical commit/completion or verified no-effects
failure, never execute the family, renew authority or reconstruct a local token.
Conflicting outcomes, effects without seal or inconsistent stores remain blocked.
No automatic restore/replay policy is introduced here.

## 14. Legacy isolation proof and reader changes

The future runtime route resolves control authority/attempt, runtime entry and
runtime seal, then uses its own capability dispatcher. No step requires a legacy
claim FK, legacy EXECUTING decision/audit, legacy operation wrapper or legacy
recovery call. Existing `recognition_execution_claims`, execution audit/seals,
production receipts, writer leases and synthetic/local execution entry points
remain unchanged. Historical private family awards are actual fixed writer
effects, not fabricated legacy execution credentials.

Required future readers are separate stage-aware runtime admission/readiness,
target entry/seal inspection and runtime completion/recovery. Keep the initial
4b proposal reader's no-downstream-record fence; do not add permissive flags to
it. Once the new storage is recognized, extend that initial-only denial fence
to runtime entry/seal presence too; do not let their absence from old tables make
an executed operation look pristine. Shared pure immutable graph validation may
be extracted only with equivalent strict tests. Ordinary v3 administration,
global target_identity, Slice H and
all old authentication/approval formats retain their meaning.

## 15. Ordered next implementation boundary

The exact next implementation slice is **inert control-side live-attempt
identity/ATTEMPT_CREATED storage and explicit local migration only**:

1. Add `runtime_live_attempt_schema.py`, focused schema tests and documentation.
   Define the six-field attempt codec, external digest, two control tables with
   genesis-only history, immutable/canonical/deferred-graph guards and exact
   recognized S1->S2 manifest transition. No target tables or writer adapter.
2. Explicit CLI migration requires expected current generation, trusted local
   operator/reason, exact deployment observations and a validated nonactive
   effective ledger (NOT_ACTIVATED or DEACTIVATED; never ACTIVATED, SUSPENDED or
   RECOVERY_REQUIRED).
   The binding marker remains NOT_ACTIVATED. This new installer does not relax
   the existing 4e-12 installer's stricter preconditions. Target remains
   query-only/reserved through control commit.
   Transaction/savepoint rollback and idempotent install inspection follow 4e-12.
   No generation change, auth grant/revocation, attempt creation or authority
   mutation merely from installing control-only inert storage.
3. Reject partial/malformed extension, missing audit, stale generation, unknown
   manifest, altered authority/schema history, all canonical/NUL/large-integer
   violations and UPDATE/DELETE/REPLACE. Test populated historical authorities
   remain valid history but acquire no execution permission. Test no target DML
   or schema/fingerprint change, no capability, readiness or activation grant.

Necessary existing integration points are `administration_schema.check_control()`
for exact extension/row validation, the authority schema's
`check_manifest_transition()` / `historical_claim_manifest()` for verified
historical reconstruction, and the existing local administration CLI for an
explicit migration action. Do not route through ordinary v3 administration or
change `administration.transaction()` / `_verify()`. The configured key path may
be validated as configuration; the installer must not read key contents.

Subsequent independent reviews: exact target entry/seal schemas/codecs; the
versioned pending-plan/schema/enrollment transition and stricter readers/guards
in section 7; original outer-manager issuer integration; fixed kernel extraction;
then actual entry/admission/effect-plus-seal ownership and finally owner recovery.
Do not combine those into the inert migration slice. Existing installations and
standalone authorities remain nonexecutable throughout these prerequisites.

Future adversarial tests must cover every authority/attempt binding, stale/
expired/renewed consent, forged/cross-process/thread/phase/connection/epoch token,
all release-gap mutations, duplicate operation/manifest/authority races, target
and control manifest tampering/partial install, unchanged old profile history,
new generation invalidation, contradictory runtime observations, set/clear stop,
activation change, writer arbitrary-SQL denial, full atomic family accounting,
DELETE/WAL interruptions at every distinct commit, restart, orphan entry, missing/
conflicting seal and no automatic adoption. Existing green tests are regression
evidence, not tests of these not-yet-implemented runtime execution contracts.

## 16. Isolated consent concurrency diagnostic

The original exact test reproduced independently: **1 failed in 21.36 seconds**,
`sqlite3.OperationalError: database is locked` at consent control BEGIN IMMEDIATE.
Both contenders intentionally start the same real transaction. The existing
connection uses SQLite's default bounded busy handling; the test only caught
ValueError/AdminError and assumed the loser would reach the replay check.
Expensive real validation can hold the winner's reservation past that bound.
No evidence establishes a Windows-only or filesystem fault from this exception.

`_owned_connection()` closes even on cleanup failure; `administration.connect()`
rolls back an active transaction and closes on exit. Fixture SQL helpers close
their handles. The minimal test correction adds real independent control-first/
target-second reservation probes after step setup and after both contenders, so
a leaked fixture/contender lock fails. It accepts only SQLite BUSY or LOCKED as a
loser rejection and still asserts **one success and exactly one durable confirmation
audit**. Unexpected SQLite errors propagate; two failures or two winners fail.
No retry, sleep, busy timeout, isolation, production or transaction code changes.
The corrected exact test passes: **1 passed in 26.54 seconds**.

The requested four-file direct regression passed using the existing
disposable-database/network guard: **110 passed, 131 subtests passed** in
2158.50 seconds. Files: authority issuance, authority owner consent, activated
owner and execution. This includes the corrected concurrency test and existing
DELETE/WAL interruption checks. No broader regression rerun,
recognition/deployment-family or full-suite run was performed.

`git diff --check`, explicit whitespace checks on both changed files and consent
test syntax validation passed. Only this document and the test-only correction
are changed by this slice; prior dirty files are preserved. No runtime source,
schema, migration, writer or authorization behavior is changed.
The existing legacy execution tests exercise disposable fixture writers. No
runtime execution is performed. No hosted resource, production database or real
deployment key is accessed. No commit or push.

PRODUCTION AUTHORIZATION: BLOCKED

PRODUCTION EXECUTION: BLOCKED

PRODUCTION ACTIVATION: BLOCKED
