# Slice 4d-1 execution-claim contract review

Status: control-side schema migration implemented for local validation only.
Claim acquisition, claim transaction ownership and all execution authority remain unimplemented.
The approved lifetime is fixed at five minutes, nonrenewable and not caller-selected.
The design sections below record the approved contract. The final implementation
section identifies the storage-only migration now present; it adds no claim issuer,
transaction owner, writer admission, recovery behavior or production authority.

## Decision and exact missing invariant

Recommend Candidate A: a dedicated durable runtime claim in the existing control
database, with immutable issuance and append-only consumption/fencing history.
The existing schema cannot support this contract. It has no control-side record
that enforces one claim per operation, exact runtime scope, bounded expiry and
one-use consumption atomically with audit. Control audit alone is not such a
record: it lacks the required unique operation key and guarded state transitions.

`execution_schema.TABLES` defines `recognition_execution_claims`, seals and
execution audit in the TARGET. `CONTROL_TABLES` defines only execution stops and
blocks. Reusing the target claim requires target DML and commit, contrary to the
claim-acquisition boundary. Reusing primary/session, approval, acknowledgement,
stop or block records as claims would change their security meaning.

The original design review stopped here. The storage-only migration has since
been separately approved and implemented as described in the final section.
Claim acquisition still stops here. Existing transaction
owners must not be widened or relabelled to issue claims. A separately reviewed
claim owner/adapter with bounded control writes is also required. If that cannot
be added without changing approved ownership, implementation must stop again.

Proposed storage names for that later review are
recognition_runtime_execution_claims and recognition_runtime_execution_claim_history.
The required minimal relationships are a unique operation_id and claim_id on the
issuance table; history foreign key to claim_id; unique (claim_id, sequence);
immutable UPDATE/DELETE/REPLACE protection; and transition guards matching the
body/digest, sequence and prior digest. There can be no cross-database SQLite
foreign key to the target operation: its existence and exact digest must be
verified under the target reservation on every authority boundary. Migration
atomicity, exact-schema validation and rollback must follow existing control-store
conventions. The final implementation section records the authorized storage-only change.

There is also an explicit downstream incompatibility to preserve:
runtime_validation._binding requires binding production_state NOT_ACTIVATED,
and _snapshot requires local activation state NOT_ACTIVATED when present.
production_operations.activation_guard and the real local writer require activated
state. Thus the current runtime validation path cannot be treated as an activated
execution path. The future claim design cannot resolve this by accepting the
admission snapshot as activation or relaxing either check. A separately reviewed
runtime activation/execution contract is required before an actual handoff can
reach the writer. No such change is proposed or implemented in this slice.

## Existing lifecycle: source of truth

* `execution_schema.py`: the target claim key is operation_id, a primary key
  referencing recognition_operation_contracts. Immutable update/delete/replace
  guards protect claim bodies. Seals reference claims; execution audit records
  state transitions. The primary key prevents two durable claims for one operation.
* `local_execution.execute_approved_operation`: consumes an opaque process-local
  production context; reserves control with BEGIN IMMEDIATE, then target with
  BEGIN IMMEDIATE. It validates binding, owner/session, approval, operation,
  dependencies and writer manifest; production additionally requires activation.
  It inserts the target claim and EXECUTING audit and commits TARGET, then reserves
  target again and revalidates before entering the writer lease. Claim creation
  is not a separate read-only acquisition API. The claim includes operation,
  approval binding/digest, manifest digest, actor and claimed_at_utc, but no expiry.
* `execution.execute_operation`: the older synthetic coordinator similarly
  commits a target claim/checkpoint before execution. `admit_operation` invokes
  execution; it must not be reused as a claim-only entry point.
* `local_execution._existing`: a completed, verified seal is ALREADY_EXECUTED;
  an unfinished claim is UNKNOWN_RECOVERY_REQUIRED with
  unfinished_claim_never_retry_writer. Terminal failure requires a new operation.
  Process death does not erase durable claims. `production_operations.consume_context`
  is only an in-memory one-use flag, not claim expiry or durable consumption.
* `local_execution.reconcile_operation`: current owner authentication plus a
  recovery-scoped step-up are required. A valid seal permits projection repair;
  absent a seal, residue/integrity determine reconciliation or failure fencing.
  It never retries the writer. `production_operations.load_recovery_context`
  checks the claim, approval and current deployment target; it grants no writer
  permission itself. The synthetic recovery path in execution.py is separate.
* `writer_boundary._local_lease` and `verify_local`: require the coordinator's
  protected final-verification handoff, exact live connection/transaction and
  manifest, durable matching claim, EXECUTING audit and no existing seal. Real
  production additionally verifies activation, binding and approval. Claim
  possession alone is insufficient. Leases disappear with their context/process.
* `production_receipts` and `local_execution._seal`: receipts/seals bind claim,
  operation, approval and writer evidence; projection is distinct from committed
  writer effects. Completion cannot be inferred from claim existence.
* `administration.advance_restore_generation`, filesystem rebind and v3 migration
  append bindings and revoke authentication/invalidate approvals. Old claims are
  not rewritten. Ordinary v3 administration remains denied. Legacy claims bind
  deployment/restore generation and do not acquire runtime-profile semantics;
  runtime enrollment does not make them portable. Changed owner/authentication
  and activation are rechecked at protected boundaries, not encoded as an expiry.
* Emergency stop is checked in local_execution._verify and the synthetic
  coordinator. A stop does not erase claims or prove absence of writer effects.

Runtime admission is different: `runtime_execution_admission.assess/revalidate`
produces process/thread-local immutable eligibility data, under the proposal
owner's reservations, and releases those reservations before returning. It
validates the real enrolled runtime, authentication, exact proposal/ACK/approval,
dependencies, whole-population manifest, stop and block state. It creates no
claim. Calling revalidate and subsequently writing a claim outside those locks
would introduce a TOCTOU gap.

`runtime_scope_validation` exposes live read views, not transferable authority.
`runtime_proposals` deliberately commits target before control ACK, with explicit
orphan/uncertain-commit semantics. That protocol is not cross-database atomicity
and must not be reused to promote an orphan into execution. `runtime_approvals`
uses a distinct bounded control-write owner, retaining a query-only target
reservation through control commit. None of these owners permits arbitrary claim
insertion.

## Candidate comparison

| Property | A: existing control DB, new claim records | B: separate claim DB | C: existing target claim |
| --- | --- | --- | --- |
| Atomicity | Claim, consumption and control audit can share one transaction; target validation is a separate reservation | Adds a third store; no atomic claim/control audit or stop update without a new protocol | Claim/audit share target transaction; control remains separate |
| Zero target DML | Yes, with target query_only ON | Possible, but needs new owner and ordering | No; incompatible |
| Single winner | BEGIN IMMEDIATE plus unique operation key and guarded consumption | Same only within third DB; scope races require reservations across all stores | Existing target PK already enforces uniqueness |
| Crash/uncertain commit | Inspect exact durable claim/history; never blind retry | Must reconcile claim DB and control audit divergence | Existing durable claim and recovery rules |
| Restart | Claim survives; live handoff does not | Same, plus third-store availability | Claim survives, requires existing recovery |
| Generation/profile fencing | Exact current binding/profile checked under control lock | Must lock/control-check across stores | Legacy binding only; runtime profile contract absent |
| Owner/auth/MFA fencing | Current authoritative records plus target owner/auth state checked under both locks | Cross-store check/commit protocol needed | Existing legacy checks; not runtime-profile authority |
| Dependencies | Exact target snapshot under target reservation; repeat at consumption/execution | Same plus extra lock ordering | Existing target verification; future runtime scope absent |
| Emergency stop | Stop and claim serialized in same control DB | Stop/claim in different stores | Existing check under control reservation |
| Recovery | New reviewed runtime inspection/fencing contract required | New multi-store reconciliation required | Existing legacy recovery; cannot reinterpret |
| Compatibility | New version/tables; no change to legacy readers | New database/configuration/backup contract | Requires forbidden target writes or changed legacy meaning |

Candidate A minimizes stores and permits control-local uniqueness, consumption,
audit and stop serialization. It does not make target and control atomic. Candidate
B is rejected absent a demonstrated need; Candidate C is rejected for this boundary.

## Proposed versioned immutable issuance body

Proposed format: `recognition-runtime-execution-claim-v1`. These are exact body
fields for review, not an implemented codec. No field establishes authentication
merely because it appears in JSON.

* format; claim_id (canonical random UUID); operation_id; operation_sha256.
* proposal_sha256: digest of the complete 4a operation envelope, equal to
  operation_sha256 under the current contract. proposal_reference: the complete
  existing 4b-1 five-field reference, including acknowledgement sequence/digest.
* acknowledgement_sha256: exact durable 4b-1 audit-body digest; approval_id;
  approval_sha256; approval_history_sha256: exact current effective history head.
* runtime_scope: the exact existing 4a target object, including installation_id,
  target_id, generation, owner_id, binding_sha256, runtime_profile_sha256,
  auth_epoch and mfa_epoch. No renamed or relaxed legacy target interpretation.
* authentication: actor_id, primary_sha256, session_sha256, matching the current
  validated owner and the explicit approved execution/session scope.
* dependency_snapshot_sha256: digest of the entire frozen preparation dependency
  object (not merely its internal sha256 field).
* target_snapshot: the complete 4d-0 target observation and control_identity;
  target_snapshot_sha256: digest of that object. This covers schema and strict
  hostname, resolved paths, device and inode for both files. Reuse those exact
  observation formats; never convert lossless decimal strings through SQLite
  integer/float casts. UUID/owner relationships must match runtime_scope.
* admission_sha256: original 4d-0 immutable snapshot digest, historical linkage
  only; all security-relevant fields must match freshly validated T2 state.
* emergency_stop_snapshot_sha256: digest of the complete validated stop snapshot
  from 4d-0, including its sequence. Consumption must require the same inactive
  stop snapshot, so an intervening activation/clearing cannot revive this claim.
* issued_at_utc; expires_at_utc; state exactly ISSUED.

Persist body_json and body_sha256=digest(body), with indexed scope columns checked
against the body. The digest is outside the body, avoiding self-reference. Require
exact field sets, duplicate-key rejection, canonical JSON equal to rules.canonical
(sorted keys, compact separators, ASCII escapes), and rules.digest SHA256 over its
UTF-8 bytes. Reject floats, integer booleans, NULs, noncanonical UUIDs/lowercase hex
SHA256, noncanonical paths and timestamps. Use existing profile canonical decimal
checks without signed-integer conversion; use exact positive integer guards for
generation, actor and audit sequence. Nested formats retain their existing codecs.

Consumption/fencing history is separate and append-only, not an UPDATE to this
body. Proposed event fields: format=recognition-runtime-execution-claim-event-v1,
claim_id, claim_sha256, sequence, previous_sha256 (explicit null at genesis),
state, reason, at_utc. A future schema must enforce one issuance per operation,
unique claim IDs, contiguous guarded history, and at most one CONSUMED transition.
No alternative profile/generation/session may acquire a second claim for the same
operation. Exact request replay is inspection only, never a second acquisition.

## Acquisition and one-use consumption

Future acquisition must take control BEGIN IMMEDIATE before target BEGIN IMMEDIATE,
set target query_only ON, and validate current scope/authentication using the
approved read interface. Revalidate the complete 4d-0 subject, current graph,
approval/history, dependencies, manifest, physical/schema observations, stop,
blocks, activation/readiness prerequisites for the eventual handoff, and fresh
clock under BOTH reservations. A new claim must not make those gates optional.

Insert immutable claim, genesis event and control audit in one control transaction
only after checks pass. Final validation must run before control COMMIT with target
reservation still held. Release target by rollback only after control commit.
Acquisition target DML and target total_changes must remain zero. No target commit.

Control BEGIN IMMEDIATE serializes contenders; a unique operation_id constraint is
the durable single-winner invariant, not a read-then-insert timing assumption.
Given valid contenders and successful storage, exactly one wins; others fail
closed. Storage failure may yield no winner or an unknown outcome, never a claim
of guaranteed success. Different sessions/profiles do not bypass uniqueness.

Later consumption is a separate, reviewed, single-winner control transition from
ISSUED to CONSUMED, after fresh checks under both reservations. Consumption must
be durable before any future writer handoff. A lost response or process death
after consumption must never permit a second handoff. No detached JSON, hostname,
PID, token digest or claim ID is a bearer writer capability. A future live handoff
must use an opaque manager-registered exact connection/process/thread context;
restart loses that registration. PID alone cannot identify a worker incarnation
and is not proposed as a persisted identity or reusable credential.

## Lifetime, invalidation and restart

The approved duration is exactly 300 seconds, with no extension or renewal.
Require expires_at = issued_at + 300 and issued_at < expires_at, using trusted server UTC from the existing runtime
clock, canonical whole-second UTC values. Both are constructed by the coordinator,
never supplied by browser/operation input. Recheck a fresh clock after lock waits;
reject clock rollback and times before issuance. Client clocks grant no lifetime.

| Event | Required behavior |
| --- | --- |
| issued_at <= now < expires_at | Only potentially consumable; all live checks still mandatory |
| now == expires_at or now > expires_at | Fail closed; no consumption, extension, second claim or retry |
| Process restart/worker replacement | Durable evidence remains; opaque handoff lost; no automatic resume or reassignment |
| Connection loss or commit error | Outcome UNKNOWN until explicit exact durable inspection; no blind retry |
| Generation/profile/install/target/owner/auth/MFA change | Claim ineligible immediately by comparison; no historical rewrite or portability |
| Approval invalidation/history change | Ineligible, even if original approval body remains immutable |
| Dependency/schema/physical identity mutation | Ineligible; do not refresh snapshot or regenerate authority |
| Emergency stop | Blocks acquisition, consumption and future writer entry; clearing stop must not revive a fenced claim |

Expiry is an eligibility deadline, not proof that a writer has stopped or that no
effects exist. Effective ineligibility must not depend on a cleanup job appending
EXPIRED/REVOKED. Proposed terminal history states are EXPIRED, REVOKED and
RECOVERY_REQUIRED; none transitions back to ISSUED. CONSUMED cannot be consumed
again. Any ambiguity after consumption requires explicit recovery assessment.
History timestamps cannot precede the previous event or issuance. The dedicated
schema section below specifies fail-closed clock checks. Transaction ownership,
consumption and future worker-ownership recovery still require implementation review.

Proposed history transitions are genesis -> ISSUED; ISSUED -> CONSUMED, EXPIRED,
REVOKED or RECOVERY_REQUIRED; and CONSUMED -> RECOVERY_REQUIRED when the handoff
outcome is uncertain. No EXPIRED, REVOKED or RECOVERY_REQUIRED transition restores
eligibility. Completion/sealing transitions are deliberately absent from this
contract: they require the future target-effect and receipt contract. Claim
uniqueness survives all these states; a different claim ID, renewed session or
new generation does not reset it. New-operation handling needs explicit later
review and cannot be inferred from expiry.

## Failure and recovery boundaries

* Claim commit succeeds but response is lost: inspect claim, exact body/hash and
  history under control reservation. Report existing state, not fresh authority.
* Death before commit: rollback gives no claim; establish durable outcome first.
* Death after acquisition but before execution: no automatic reassignment. Fence
  or inspect explicitly; expiry cannot clear uniqueness or authorize a new claim.
* Death after consumption: mark/interpret as recovery-required; never reissue a
  handoff, even when no target mutation is visible.
* Expiry, profile generation change, approval invalidation or stop: deny further
  handoff and preserve history. No automatic retry, approval refresh or recovery.

Actual execution will necessarily write TARGET after a later independently
reviewed gate. There is no atomic commit spanning claim consumption in CONTROL
and writer effects/seal in TARGET. That future slice must define uncertain gaps,
final revalidation, fixed writer ownership and reconciliation. This design does
not bridge that gap, project completion, or authorize a legacy writer to accept
the new claim. An expired claim must never become a reason to retry a writer.

Restore is not restart: rolling control history back can remove the uniqueness
evidence while target effects remain. A SQLite unique key alone cannot detect
that rollback. Restored/copied stores require deliberate recovery and generation
fencing before any authority is considered; do not automatically resume claims
or infer absence of effects from missing restored control records. Existing
restore/rebind helpers and their legacy scope remain unchanged. A compatible
runtime restore/backup-pair policy is another prerequisite for eventual execution,
not a recovery mechanism implemented by this design slice.

## Required review and validation gates

Before any implementation: review the implementation of new control storage/constraints,
explicit transaction owner, approved five-minute clock policy, consumption and stop-incarnation fencing,
worker replacement/recovery policy, and later target-effect correlation. Keep
legacy claim/schema/readers and Slice H semantics unchanged.

Future tests must cover every field mismatch; exact proposal/ACK/approval/history
binding; generation/profile/owner/auth/MFA change; stale dependencies/schema and
physical identity; emergency-stop activation and clearing; unique operation claims
across processes/sessions/profiles; expiry boundary and rollback of clock; one-use
consumption; process death and lost commit responses; rollback of claim/event/audit;
zero target writes; inability to mint writer capability or enter readiness or
activation; and legacy behavior unchanged. DELETE and WAL must both be exercised
with real processes, not timing-only mocks or assumed cross-database atomicity.

Existing regression anchors are test_recognition_execution (including interrupted
claim recovery), test_recognition_local_execution, writer/receipt tests,
test_recognition_runtime_execution_admission, runtime approval tests, and
test_recognition_deployment_rehearsal. Its process tests cover committed survival,
uncommitted rollback, reader visibility, writer timeout and restart in DELETE/WAL;
they establish local filesystem behavior only, not hosted deployment readiness.

No new tests are added merely to assert this prose or manufacture a claim. Run the
existing execution/admission/approval/deployment and recognition regressions for
this documentation-only slice. Production authorization, execution and activation
remain BLOCKED. Execution claim != writer capability != completion != readiness
!= activation. Existing NOT_ACTIVATED behavior is unchanged.

## Follow-up review: storage, lifetime and ownership decisions

This section resolves the structural design questions, not authority to implement.
The approved numeric lifetime is now fixed at 300 seconds. The final schema classification is
**SCHEMA CHANGE REQUIRED**. No existing claim or control record is changed.

### Minimum additive storage specification

Use an immutable issuance row plus immutable state/history, rather than a mutable
claim row. The following are proposed columns and constraints for a later explicit
migration review. All columns are NOT NULL unless explicitly marked nullable.

recognition_runtime_execution_claims:

| Column | SQLite type | Constraint/meaning |
| --- | --- | --- |
| claim_id | TEXT | Canonical UUID, PRIMARY KEY |
| operation_id | TEXT | Canonical UUID, UNIQUE for the lifetime of the control history |
| body_json | TEXT | Exact canonical issuance body specified above |
| body_sha256 | TEXT | Canonical lowercase SHA256, UNIQUE; recomputed digest of body_json's parsed object |
| generation | INTEGER | Positive exact integer, FK recognition_admin_bindings(generation) |
| profile_sha256 | TEXT | Canonical SHA256, FK recognition_runtime_profiles(profile_sha256) |
| issued_at | INTEGER | UTC epoch seconds, 0..runtime_profile_schema.MAX_TIME |
| expires_at | INTEGER | Same integer range, strictly greater than issued_at |
| audit_sequence | INTEGER | Positive exact integer, UNIQUE; deferred FK recognition_admin_audit(sequence) |

recognition_runtime_execution_claim_history:

| Column | SQLite type | Constraint/meaning |
| --- | --- | --- |
| claim_id | TEXT | Canonical UUID, FK issuance claim_id |
| sequence | INTEGER | Positive exact integer; PRIMARY KEY(claim_id,sequence) |
| state | TEXT | ISSUED, CONSUMED, EXPIRED, REVOKED or RECOVERY_REQUIRED only |
| at | INTEGER | UTC epoch seconds, 0..runtime_profile_schema.MAX_TIME; exact conversion of event at_utc |
| body_json | TEXT | Canonical claim-event object specified above |
| body_sha256 | TEXT | Canonical SHA256, UNIQUE; recomputed event digest |
| audit_sequence | INTEGER | Positive exact integer, UNIQUE; deferred FK recognition_admin_audit(sequence) |

Issuance generation/profile FKs are immediate: both already exist. History's
claim FK is immediate: insert issuance before genesis. Audit FKs are DEFERRABLE
INITIALLY DEFERRED, matching the existing profile/audit installation convention.
Genesis history and issuance share ONE creation audit_sequence, recorded in
separate tables; later history events each reference a new distinct control audit.
The creation audit subject binds claim ID/digest and genesis event digest. Each
later audit subject binds claim ID/digest, event sequence and event digest.

All remaining required scope fields live in canonical body_json rather than being
duplicated into dozens of index columns. They are immutable, with exact typed
reader validation against live durable state. No SQL JSON-number cast is used for
device/inode. The indexed generation/profile/times must exactly match the body;
issued_at/expires_at are lossless epoch conversions of the canonical UTC strings.
Use existing NUL-safe SHA/UUID/integer helpers and canonical path/decimal Python
validation. SQLite affinity is not proof of the caller's original integer type:
the codec must reject booleans/floats before SQL, and row validation must recheck
the complete parsed body. Digest verification runs in trusted Python validation,
not a nonexistent SQLite SHA function.

Required indexes beyond primary/unique indexes: an issuance index on
(generation,profile_sha256). History's primary-key prefix supports claim lookup;
no expiry scheduler/index is needed for correctness. No FK to target-side operation,
proposal or preparation is possible across these isolated databases. Their exact
presence/scope/digests must instead be validated under the target reservation.

Required guards: immutable UPDATE/DELETE and BEFORE INSERT collision protection
for EVERY unique identity (including INSERT OR REPLACE with recursive_triggers
disabled); exact indexed/body equality; issuance references the latest binding,
its installation/target/owner/profile/generation and matching enrolled runtime;
body authentication refers to existing matching primary/session runtime scope;
audit actor/time/subject and profile scope match issuance; genesis sequence=1,
explicit null previous_sha256, state ISSUED and exact claim digest; later sequences
are contiguous, previous_sha256 is explicit and equals the prior event digest;
event time never decreases; only the listed state transitions are legal. A second
CONSUMED transition is impossible because no transition returns to ISSUED.
Cross-table audit relationship validation may be deferred until the audit exists,
but must be checked before commit and by exact-schema/row validation afterward.
Static constraints/triggers are defense in depth, not substitutes for live checks.

The latest-generation/current-auth guards above are INSERT/admission guards,
not requirements that all historical claims remain current forever. Historical
row validation checks the referenced immutable binding/profile, original proof
scope and audit linkage; it must tolerate subsequent legitimate revocation or
generation changes without rewriting old rows or declaring the entire store
malformed. Consumption separately requires equality to CURRENT scope and active
proofs. Historical validity and present authority are different predicates.

Only effective state and consumption status transition: derive them from validated
history, never mutate issuance.state. No event means malformed storage, not an
unconsumed claim. CONSUMED, or RECOVERY_REQUIRED following CONSUMED, means the
one-use acquisition was spent. EXPIRED/REVOKED never restore consumption rights.
Generation/profile changes do not rewrite issuance/history; live scope mismatches
deny use even if a terminal event has not yet been appended.

The uniqueness identity is operation_id ALONE within the bound control history.
Adding generation, approval or profile to that key would permit another claim for
the same immutable operation after scope change, undermining one-use fencing.
A different operation digest under the same operation ID is corruption/conflict,
not a new claim. A lost acknowledgement never permits another claim ID. Exact
replay returns inspection data only, not acquisition authority. This guarantees at
most one durable issuance; exactly one valid contender succeeds only if storage
commits successfully. Rollback/uncertainty cannot be advertised as guaranteed success.

### Explicit lifetime policy proposal

Use the explicitly approved FIXED, nonrenewable duration D=300 seconds,
not caller-selected, not inferred from session lifetime and not extendible by
retry. The permitted minimum and maximum issuance duration are both 300 seconds;
issued_at_utc and expires_at_utc must be whole-second canonical UTC and satisfy
expires_at = issued_at + D within the supported timestamp range. Issuance also
requires expires_at no later than the validated primary/session deadlines; if
insufficient authentication lifetime remains, reject rather than silently shorten
the fixed duration or issue fresh authentication.

The trusted clock is runtime_validation._utc_now(), re-read after lock waits and
at final validation/consumption. No request timestamp sets issuance or expiry.
Reject clock rollback before the transaction's trusted start, issuance, admission
time or preceding audit/history timestamp. Across-process clock correctness is a
trusted host assumption; this code cannot prove real elapsed time after an
undetected host-clock rollback. No expiry grace or background job may bypass it.

The five-minute value comes from explicit operator approval, not existing
SESSION_SECONDS=8 hours, RECENT_SECONDS=10 minutes or challenge expiry=600 seconds.
Those policies concern different authority. No duration decision remains open.
Renewal is prohibited: there is no renewed digest, updated expiry, replacement
claim or automatic new operation. Any future renewal policy is a new review.

Usability is strictly issued_at <= now < expires_at with every live scope check
passing. At equality or after expiry, fail closed. Changed generation/profile,
owner/auth/MFA epoch, invalidated approval/history, changed dependencies, schema or
physical identity deny use. An emergency stop blocks use, and its changed sequence
also prevents revival after clearing. Existing stop authorization/history is unchanged.

Proposed restart policy: durable claim/history survive, but worker restart or
replacement INVALIDATES the in-memory right to consume. Only the exact issuing
process/thread's opaque manager-registered object can request consumption while
live and unexpired; no durable secret, PID, hostname or JSON object reconstructs
it. PID/thread values are registry checks only, not persisted identity or
authentication. A new authenticated worker may inspect but cannot adopt that
claim. Lost responses, lost live handles and restart therefore require deliberate
fencing/recovery review; no reassignment is implemented or implied.

### Smallest manager-owned transaction proposal

Proposed separate RuntimeClaimContext and claim_transaction(config), with exact
type/private registry and fixed claim kernel. Do not register it as a 3a, proposal
or approval context. Add a separate explicit shared-read-view adapter only in a
future implementation review. Existing owners/registries/authorizers retain their
semantics and write scopes. No generic callback, supplied connection, scope dict,
public writer facade or authorization provider may mint claims.

Comparison: administration.transaction uses deployment identity and rejects v3;
3a owns runtime validation/authentication, not claim writes; 4b owns graph/ACK
persistence including a deliberate target commit; 4c owns bounded approval writes
with query-only target. The 4c control-before-target reservation and finalization
ordering is the model, but its issuance permissions cannot be reused for claims.
runtime_execution_admission._collect is hardwired to the proposal owner, so a new
context must not be passed to it by widening its type check. The future claim
kernel must use the same approved read contracts via its separately registered
view, compare all admission data, and independently repeat final checks. A pure
shared validation extraction, if needed, requires separate review proving equal
checks; it cannot accept detached identity data as authority.

Proposed order, with no target/control cross-database atomicity claim:

1. Manager opens configured control, BEGIN IMMEDIATE; exact schema, binding,
   profile and history validation. Read existing binding/profile/scope records;
   administrative encryption and deployment private-key contents are unnecessary.
2. Manager opens configured target, BEGIN IMMEDIATE then query_only ON. Bind
   exact connection objects to PID, Thread object/identifier and active context.
3. Validate actual runtime, installation/target/owner, auth/MFA and registered
   session scope; check exact live graph/ACK/approval/history, dependencies,
   manifest, stop/block and original 4d-0 snapshot comparison at T2. Preserve
   NOT_ACTIVATED; this issues no actual writer handoff. Later activated execution
   remains incompatible with the present runtime gate and separately blocked.
4. Fixed internal phase inserts claim, genesis and creation audit on CONTROL only.
   Authorizer permits only these bounded INSERTs, plus necessary trigger reads.
   No target DML/DDL, ATTACH, transaction replacement or caller lifecycle actions.
5. Final validation while BOTH reservations remain held: exact scope, identities,
   fresh time and expiry, authentication deadlines, proposal/ACK/approval/dependency
   equality, protected-state snapshots and exact inserted rows/audit sequence.
   Require target total_changes delta=0 and query_only still ON; control delta and
   affected records must equal the fixed intended writes, not merely a count.
6. Manager commits control; target reservation remains held through commit.
   Only after successful commit, roll back/release target. Never commit target.
7. Publish an opaque live claim handle only after successful finalization and
   cleanup. Poisoned, replaced, expired, wrong-process/thread or closed contexts
   cannot publish. No raw handle/lifecycle method escapes the manager.

This ordering requires no release gap and no deviation from 3a's security order.
The new owner is an additive, separately reviewed bounded-write owner, not a
modification of 3a or a proposal context masquerading as authentication. Normal
claim issuance cannot mutate proofs, sessions, step-ups, confirmations or approvals.
Existing authentication-denial reductions may occur only through the existing
verified-denial kernel, with exact baseline/integrity checks, never mixed with a
committed claim. Such a denial-only commit is permitted only before the first
claim write; after insertion any denial rolls back the entire transaction,
including claim/history/audit and any pending denial effects. Catching an inner
error cannot unpoison the context or permit caller commit. Manager rollback must
resolve/close control before releasing target even when cleanup fails.

### Approved migration and validation ordering

After separate migration/owner implementation approval, use an explicit trusted local ceremony, exact current
generation and existing strict deployment/history validation; ordinary access
must never install/repair the extension. Under control then target reservations,
validate the old exact schema and NOT_ACTIVATED, use an enclosing savepoint,
create the complete additive tables/indexes/triggers, and validate exact schema,
body/history consistency and foreign keys before committing control with target
still held. No target DML; no claims are created by migration. Partial/malformed
extensions must fail closed rather than be silently repaired.

Deploy extension-aware exact validators/readers before the explicit ceremony,
retaining support for the existing complete schema without automatically upgrading
it. Once the extension exists, old binaries must fail closed. An installation
error may roll back uncommitted DDL; a later binary rollback must not drop committed
claim/history records or bypass schema validation to make old code run.

The versioned extension marker should be the COMPLETE exact object set, detected
by the control schema validator, following the existing runtime-extension model;
do not change the v3 binding format or schema hash meaning silently. Installing this
extension is proposed as a schema-only, expected-generation-bound ceremony: retain
the exact binding, generation, profile and authentication/approval records, and
append only the explicit schema-install audit in the same control transaction.
Installing empty claim storage grants no authority and does not justify a binding
transition. This differs from Slice 1's v2-to-v3 semantic transition, which advanced
generation and revoked authentication. Do not copy that transition blindly:
current runtime enrollment supports initial enrollment, not profile rotation.
If future implementation proves a generation advance is necessary, STOP for a
separate profile-transition design; do not carry a stale profile forward or add
rotation/recovery to this migration. Schema installation is not claim issuance.

Any DDL, row validation, protected-state validation, audit or deferred-FK failure rolls back the
entire savepoint and outer transaction. A rollback is not permission to continue
partial migration. A stale/concurrent ceremony fails expected-generation checks.
Idempotence means inspecting a fully matching installed extension, not silently
advancing generation again. Uncertain migration commit requires read-only durable
inspection; no blind rerun, automatic downgrade or destructive rollback. Backups
and deliberate restore-generation fencing remain required; old binaries must
reject the unfamiliar extension, not ignore it.

### Commit, crash and connection-loss outcomes

| Boundary | Classification and action |
| --- | --- |
| Before insert, or after insert before commit, rollback positively acknowledged | Confirmed rolled back: no claim/genesis/audit persists |
| Process killed before attempting commit | SQLite transaction recovery should roll back; surviving process must inspect integrity and durable absence before classifying it confirmed |
| During COMMIT or connection loss with unknown commit outcome | Uncertain: stop, no returned handle, no create retry |
| COMMIT positively acknowledged | Confirmed committed; later cleanup failure must retain that classification |
| Commit succeeds but response lost/worker dies | Caller outcome uncertain; durable claim remains if commit persisted; inspect rather than create again |
| Target release/connection cleanup fails after control commit | Confirmed committed with cleanup error; never pretend claim rolled back |
| Rollback or storage inspection fails | Uncertain; close unresolved handles and require deliberate inspection |

Inspection uses trusted tooling with read-only/query-only SQLite, validating exact
control identity/schema/binding and all claim/history/audit digests. After readers
can establish SQLite recovery and integrity, lookup BOTH expected claim_id and
operation_id and compare the complete expected body/digest, scope and history.
Report exact committed state, confirmed absence, conflict or unknown; never turn
inspection into authentication or a fresh acquisition. A different row under the
same operation is a conflict. Recovery/checkpoint needs on damaged/unclean storage
are not solved by disabling read-only mode in the inspector; inability to inspect
is UNKNOWN and requires a separately authorized recovery procedure.

Confirmed absence after uncertain commit still does not trigger automatic retry:
the trusted operator must decide the next action under current scope. Confirmed
presence cannot reconstruct the lost opaque process handle. Generation/profile,
approval, expiry or stop changes remain authoritative even for a committed claim.
Future consumption and target-effect commits must have their own reviewed crash
matrix; this documentation does not alter legacy recovery or authorize execution.

Runtime authentication != execution admission != execution claim != writer
capability != execution completion != readiness != activation. All legacy
target-side claims, formats, recovery, seals, receipts and gates remain unchanged.

Follow-up validation completed on 2026-11-01: the complete recognition test family
plus pilot deployment/readiness tests passed with 1012 passed, 3 skipped and
1725 subtests passed. This includes the existing execution, admission, approval
and deployment/rehearsal tests. No tests or implementation files were changed for
this follow-up design. At that review the numeric lifetime was unresolved; the
subsequent approved five-minute policy supersedes that earlier blocker.

## Control-side execution claim schema design

This section is the normative schema/migration design for the approved five-minute
policy. It refines the preceding review without authorizing implementation.
**SCHEMA CHANGE REQUIRED**: the existing exact control schema has no runtime claim
issuance/history objects and will reject them until a separately approved validator
extension is deployed. No legacy table changes or target DML are necessary.

### Versioned object manifest and columns

Proposed migration identifier: recognition-runtime-execution-claims-v1.
It installs exactly the two tables specified in the column tables above:

* recognition_runtime_execution_claims: claim_id TEXT PRIMARY KEY,
  operation_id TEXT UNIQUE, body_json TEXT, body_sha256 TEXT UNIQUE,
  generation INTEGER, profile_sha256 TEXT, issued_at INTEGER,
  expires_at INTEGER, audit_sequence INTEGER UNIQUE.
* recognition_runtime_execution_claim_history: claim_id TEXT, sequence INTEGER,
  state TEXT, at INTEGER, body_json TEXT, body_sha256 TEXT UNIQUE,
  audit_sequence INTEGER UNIQUE; PRIMARY KEY(claim_id,sequence).

All columns are explicitly NOT NULL, including TEXT primary keys. The only null
in the document formats is genesis event previous_sha256, which must be PRESENT
and null; subsequent events require the exact previous digest. Issuance fields
and every history row are immutable. Current state/consumption are derived from
validated history plus current scope/time, never updated in place.

The issuance body uses recognition-runtime-execution-claim-v1 and the exact body
field list above: claim/operation IDs and digests; proposal/reference/ACK; approval
ID/digest/history head; complete runtime_scope; authentication hashes; dependency
digest; complete target_snapshot and its digest; admission digest; stop snapshot
digest; issued/expires UTC; initial ISSUED state. Installation, target, owner,
generation, binding/profile digests and auth/MFA epochs are mandatory typed fields
of runtime_scope. Schema SHA and both files' actual host/path/device/inode are
mandatory within target_snapshot. No observation is inferred from an imported
hostname or caller-supplied path. This stores the full required scope without
duplicating every body field into separately indexed columns.

Canonical JSON and digests use rules.canonical/digest, duplicate-key rejection and
exact field sets; the digest is stored outside the object it hashes. Reject NULs,
floats, boolean-as-integer fields, extra/missing fields, noncanonical UUID/SHA/path
and decimal representations. SHA values are exactly 64 lowercase hexadecimal
characters; UUIDs are canonical lowercase hyphenated UUID strings. Times are
exactly YYYY-MM-DDTHH:MM:SSZ accepted by trust.utc, with no offset variants,
fractions, leap-second normalization or whitespace. Preserve existing observation
types: lossless canonical decimal text in profile fields, exact Python integers
where the existing target observation uses them; never SQL-cast device/inode
values through REAL or signed INTEGER. Reject invalid historical observations.

### Exact constraints, keys and indexes

Required scalar CHECKs for each table:

* TEXT columns: typeof='text', no char(0); UUID and SHA checks use the existing
  runtime_profile_schema NUL-safe canonical predicates. body_json additionally
  requires json_valid and an object root; its complete canonical form, digest and
  typed nested fields are authoritatively verified in Python before any commit
  and by every trusted reader. SQL JSON validity alone is insufficient.
* generation, sequence and audit_sequence: typeof='integer' and 1..2^63-1.
* issued_at: typeof='integer' and 0..MAX_TIME-300; expires_at: typeof='integer'
  and 0..MAX_TIME; CHECK(expires_at=issued_at+300 AND expires_at>issued_at).
  Bounded arithmetic stays exactly within signed integer range. These redundant
  checks do not replace canonical UTC parsing and application arithmetic.
* history at: typeof='integer' and 0..MAX_TIME; state is exactly one of ISSUED,
  CONSUMED, EXPIRED, REVOKED, RECOVERY_REQUIRED. Application input type guards run
  before SQLite affinity conversion, which otherwise can normalize bad inputs.

FKs are exactly issuance.generation -> recognition_admin_bindings.generation,
issuance.profile_sha256 -> recognition_runtime_profiles.profile_sha256,
history.claim_id -> issuance.claim_id, and both audit_sequence columns ->
recognition_admin_audit.sequence. The first three are immediate; the two audit FKs
are DEFERRABLE INITIALLY DEFERRED. No cascades. Set foreign_keys ON before BEGIN.
Composite profile/generation/install/target/owner equality is required by guards
and full row validation, not assumed merely from these separate FKs.

Explicit non-unique index name: recognition_runtime_execution_claims_scope_idx
on issuance(generation,profile_sha256). Primary/UNIQUE constraints provide all
other indexes: claim ID, operation ID, issuance digest/audit, history(claim,sequence)
and history digest/audit. No UNIQUE(operation_id,generation/approval/profile):
UNIQUE(operation_id) deliberately forbids renewed ownership of the same operation.
Storage errors may produce zero successful contenders, never two committed winners.

Each table has immutable_update, immutable_delete and immutable_replace triggers,
named by appending those suffixes to its table name. Collision checks cover EVERY
primary/unique key before INSERT, so REPLACE cannot delete/reinsert history even
with recursive_triggers OFF. Additional proposed trigger names are:

* recognition_runtime_execution_claims_scope_guard: exact indexed/body equality,
  latest valid binding/profile scope and matching proof references at INSERT.
* recognition_runtime_execution_claim_history_transition: contiguous sequence,
  explicit prior hash, matching claim ID/digest, legal state and nondecreasing time;
  genesis is ISSUED at issuance time; CONSUMED requires at < expires_at and
  at >= issued_at; EXPIRED requires at >= expires_at. No transition permits renewal.
* recognition_runtime_execution_claims_audit_guard, attached to INSERT on the
  control audit table: when an audit is linked to these tables, require exact
  actor/time/action/subject and corresponding issuance/history scope. A linked
  audit must not preexist before its claim/event: fixed insertion is claim,
  genesis, then audit, or later event then audit. Deferred FKs prevent committing
  missing audits; final validation verifies their hashes and complete linkage.

The exact validator must recognize all objects together, validate canonical rows,
FKs, cross-table scope, genesis and audit links, and reject partial/modified/extra
objects. Historical claims validate against their original immutable generation;
only fresh admission/consumption requires CURRENT generation and active proofs.
No SQL FK can cross into the target database. Approval ID/digest and the target
proposal/operation relationship are checked against durable records under both
reservations at T2 and final validation, not trusted from JSON or an ID alone.

### Lifecycle, five-minute expiry and clock checks

Persisted lifecycle: absent -> ISSUED -> CONSUMED, EXPIRED, REVOKED or
RECOVERY_REQUIRED. CONSUMED may transition only to RECOVERY_REQUIRED for uncertain
handoff; EXPIRED/REVOKED/RECOVERY_REQUIRED never restore eligibility. No completion
state or writer receipt is introduced. No row/history pair means either absent
or malformed: absence can be classified as never committed only after trusted
inspection establishes transaction recovery/integrity and exact nonexistence.

Current means: immutable rows valid, history ISSUED, exact live scope/approval/
dependencies/stop unchanged, issuing live context valid, and issued_at <= now <
expires_at. Consumed means validated CONSUMED history exists, even after subsequent
RECOVERY_REQUIRED. Expired means now >= expires_at, regardless of whether an
EXPIRED event has been appended. Invalidated means a relevant scope/approval/
dependency/stop change or terminal fence; a stale ISSUED history cannot override it.

Expiry is EXACTLY issued_at_utc + 300 seconds. Minimum=maximum=300; not selected
by callers, not shortened for stale credentials, and never renewed or extended.
Fresh primary/session validity must cover issuance and all subsequent checks;
the earlier proposed deadline rule requires enough remaining proof lifetime for
the full 300 seconds or denies issuance. At equality with expiry, deny. There is
no grace period, background expiry dependency, clock-reset extension or retry.
Consumption before expiry cannot turn the claim into enduring writer authority:
every future execution entry must independently check the same deadline before
any target mutation and reject now >= expires_at. Existing writers do not accept
this new claim format and remain unchanged. Mid-execution time/finality handling
belongs to the separately blocked execution contract, never to claim renewal.

Application-level final validation is authoritative: parse both UTC strings,
recompute +300 with integer datetime arithmetic, compare indexed epoch seconds,
and re-read the trusted runtime UTC clock after lock waits and before control
commit. Reject malformed, overflowed, future-issued, backdated or already-expired
data. The kernel creates issuance time from its fresh clock, not an input file;
final time must be at least issuance/admission/preceding audit time and strictly
before expiry. Historical expired rows remain valid historical data, not authority.

Clock rollback or anomalous time movement fails closed. Future live ownership must
retain a monotonic-clock observation alongside the trusted UTC samples in private
process memory. Require nondecreasing UTC and monotonic readings and consistency
of elapsed time, accounting only for whole-second UTC quantization and the measured
sampling interval; no configurable skew allowance or expiry grace. An elapsed
monotonic duration of 300 seconds also denies use even if UTC stalls. A forward
jump inconsistent with elapsed monotonic time denies use; it never moves expiry.
If consistency cannot be established, deny rather than invent a tolerance.

No database CHECK can detect a system-clock anomaly. Only supported, health-checked
trusted host clocks and same-process live sampling support this design; it does
not claim detection of undetectable privileged clock tampering. Restart loses the
live context and monotonic baseline, so another worker cannot adopt a durable
claim or reset its clock window. A detected rollback does not justify an earlier
history timestamp; deny without writing a false event until trusted time is restored.

### Transaction, crash and uncertain outcome

The future manager takes control BEGIN IMMEDIATE, validates schema/history,
takes target BEGIN IMMEDIATE and sets query_only ON, validates T2 actual runtime,
auth/profile/proposal/ACK/approval/dependencies and admission comparison, inserts
claim/genesis/audit on control, then performs final exact record/scope/time checks.
Commit CONTROL while TARGET reservation remains held; only afterward roll back
and release TARGET. Target total_changes must not change. No ATTACH, target DML,
target commit, cross-database atomicity assumption or public raw writer handle.
Immediate FKs refer to already existing binding/profile/claim rows; audit FKs
allow the creation audit to be inserted last and validated at control commit.

Before insert or after insert/precommit death: pending claim/history/audit should
roll back together under ordinary SQLite recovery. A positive commit preserves
all three; postcommit process termination does not erase them. Death during commit
or a lost response is uncertain to the caller. These rules apply to DELETE and
WAL without forced checkpoints, retry loops or journal-mode changes. Read-only
inspection that cannot establish recovery/integrity must report UNKNOWN rather
than perform unauthorized repair. Successful commit followed by cleanup failure
is committed-with-cleanup-error, not permission to retry.

Exact inspection identity: query issuance WHERE claim_id=:expected_claim_id OR
operation_id=:expected_operation_id, then read history by claim_id ORDER BY
sequence and linked audits by audit_sequence. Bind query parameters, never SQL
string interpolation. No rows plus verified integrity/recovery = confirmed absent;
one row with BOTH IDs and every expected body/digest/scope/link = present and exact;
different identity/digest/scope or multiple matches = conflict; unreadable or
unresolved storage = UNKNOWN. Row counts alone cannot prove exactness. Inspection
does not grant a fresh opaque handle, consume anything, or automatically retry.

### Explicit additive migration and deployment preflight

The proposed migration identifier is recognition-runtime-execution-claims-v1,
tracked by its complete exact object manifest and an immutable control audit action
runtime_execution_claim_schema_installed. No new migration-marker table or binding
format is needed. The audit subject records migration ID, previous schema-manifest
digest, installed schema-manifest digest, current installation/generation, operator
and reason; it creates no claim or authority. The manifest digest is rules.digest
over a name-to-whitespace-normalized-definition mapping, following existing exact
schema comparison. It is not a replacement for checking definitions individually.

Proposed ordering, not executable migration code:

1. Deploy exact extension-aware validators first, supporting both the complete old
   schema and complete new schema without implicit install. Require explicit trusted
   local operator/reason and exact expected generation and deployment identity.
   Ordinary administration.transaction still rejects v3; do not change it. The
   future local migration manager must use the existing deployment-history reader
   pattern in runtime_challenges._deployment_binding and strict administration._verify,
   with additional full profile/history validation. Do not invoke enrollment or
   mislabel the deployment console as an enrolled runtime to install schema.
2. Verify coherent backup(s), hashes, schema and existing data inventories as below.
   Acquire control then query-only target reservations; recheck actual identity,
   current binding/profile, NOT_ACTIVATED, schema, integrity and foreign keys.
3. If no extension objects exist, establish savepoint and create issuance table,
   history table, explicit index, six immutability triggers and three guards above.
   Validate exact schema and empty new tables; append the one migration audit.
4. Verify unchanged binding/generation/profile and protected auth/approval/legacy
   inventories, full integrity/FKs, manifest and audit; release savepoint and commit
   control with target still reserved; release target by rollback only.
5. On any failure, roll back all DDL/audit and outer transaction. A caller catching
   an error cannot commit a partial extension. Commit uncertainty requires inspection.

Idempotence: a complete exact installation with the one valid migration audit is
an inspected no-op after current preconditions, NOT a second audit or generation
advance. Existing valid runtime claim/history rows are preserved and validated,
never rewritten by a rerun. Any partial object set, incorrect definition, missing
audit, malformed row or preexisting conflicting object fails closed; no repair,
DROP/recreate or rewrite. The old-to-new schema-only ceremony leaves installation,
binding/profile/generation, primary/session records, approval histories and legacy
claims unchanged. Old binaries must reject the extension after migration; binary
rollback cannot silently drop claim evidence. No automatic downgrade or recovery.

Before deployment applies the eventual migration, verify:

* A coherent verified control backup, plus the intended target backup/paired
  recovery reference; backup SHA256, size, location, timestamp and installation/
  generation manifest. A file copied without journal-aware coherence is insufficient.
* Target backup verification uses read-only access; migration preflight does not
  write the target or perform a production backup in this design slice.
* Exact old/new schema preflight, extension object inventory and schema-manifest
  digest; canonical binding/profile/audit history and identity checks.
* integrity_check='ok' and empty foreign_key_check on applicable isolated stores;
  check foreign_keys=ON on the future migration connection before BEGIN.
* Existing target legacy claims, seals, execution audit, approvals and proposal
  inventory, and any existing new control claim/history inventory. Compare exact
  IDs/digests/counts and unresolved states before/after; do not migrate legacy rows.
* Current DELETE/WAL mode, required sidecars, permissions, SQLite version/features,
  durability settings and no competing administrative migration. Do not change
  journal mode, checkpoint forcibly, or retry away uncertainty.
* Deliberate restore procedure and generation fencing: a backup rollback must not
  erase evidence and make an old immutable operation claimable/executable again.
  Verify backups before any eventual mutation; retention/restore policy is unchanged.

### Test plan and implementation boundary

Future isolated migration tests must cover empty install/no-op rerun, populated
valid extension rerun, exact/partial/modified schema rejection, every unique-key
REPLACE collision, UPDATE/DELETE denial, FK ordering and missing audits, bad scope/
audit/history linkage, every canonical/NUL/type/large-decimal case, five-minute
arithmetic and overflow, equality-at-expiry, past/future/rollback/stalled/jumped
clock denial, terminal/duplicate consumption, same-operation concurrent inserts,
savepoint and outer rollback at each stage, uncertain commit inspection, unchanged
legacy/auth/profile/binding records, and real process termination in DELETE/WAL.
No schema-only test can establish future writer or claim-consumption authority.

No new tests or SQLite objects were added in the original design-only slice. The earlier
recognition/deployment results recorded above describe existing behavior, not
validation of an implemented claim schema. This section specifies future tests;
it does not claim they have run. Current documentation/whitespace checks are the
only new checks performed for that documentation-only change. The later storage
implementation and its tests are recorded below. Claim acquisition,
transaction implementation, writer handoff, readiness and activation remain
independently blocked. Legacy recognition_execution_claims and recovery are untouched.

## Storage-only migration implementation

Implemented migration identifier: recognition-runtime-execution-claims-v1.
The explicit local API is runtime_execution_claim_schema.migrate(config,
expected_generation=..., operator=..., reason=...). It is not called by startup,
ordinary control access or any HTTP route; there is no new CLI or claim API.

Objects: the two control tables and columns listed in the dedicated schema section,
six immutable UPDATE/DELETE/REPLACE triggers, the scope index, issuance scope guard,
history transition guard and linked-audit guard (12 named objects total). State is
immutable issuance plus append-only history; schema installation inserts no claim
or history rows. UNIQUE(operation_id) enforces the single-winner storage invariant.
Canonical UUID/SHA/NUL checks reuse the existing profile schema predicates; nested
scope/proof/physical observations have INSERT guards and historical Python row
validation. Device/inode comparisons use raw JSON decimal representations, never
SQLite numeric casts. UTC strings must agree with typed integer epoch columns;
CHECK and historical Python validation both require exactly 300 seconds. No live
clock/consumption/execution authority is implemented by these storage validators.

Immediate FKs: claim generation to immutable binding; profile digest to enrolled
profile; history to claim. Deferred audit FKs allow claim, genesis, then audit in
one control transaction. Initial/later audit actions are respectively
runtime_execution_claim_issued and runtime_execution_claim_state_changed; the
subject is exactly claim_id, claim_sha256, event_sequence, event_sha256. These are
storage conventions, not implemented issuance endpoints. History never updates
the original claim. Missing/extra objects, malformed rows/audits, broken FKs,
illegal state transitions and incompatible preexisting definitions fail closed.

administration_schema.check_control recognizes only the COMPLETE exact extension;
ordinary access never installs it. The immutable install-audit marker also
requires the complete extension: deleting
all new objects cannot masquerade as the pre-migration schema. Installation uses
existing control connection, savepoint and append-only administrative audit
conventions. It validates durable
v3 history and any enrolled profile, exact expected generation, strict deployment
control identity and target identity/schema/installation, plus NOT_ACTIVATED.
Binding, generation, profile, primary/session/step-up/confirmation and approval
records remain unchanged. Legacy target tables, indexes, rows, readers and recovery
code remain unchanged. No target DML or target commit occurs.

Preflight reserves control then target, sets target query_only, and runs integrity
and FK checks through separate read-only handles while BOTH reservations stay
held. This matters because SQLite integrity_check can initialize a temp schema:
the existing strict single-database migration/control connection invariant is
preserved, not relaxed. The migration then creates all objects and its one schema
audit atomically, validates exact schema/rows/manifest/identity/fresh time, commits
control while target remains reserved, and releases target by rollback only.
Mid-DDL, audit or final-validation failure rolls back the entire migration. A
fully matching installation plus migration audit is an inspected no-op, including
with valid synthetic historical rows; it neither appends a second audit nor
advances generation. Incompatible/partial installation is never repaired.

The schema-install audit links migration ID, prior/installed normalized schema
manifest digests, installation, generation and reason, with the explicit operator
as actor. This version fences the complete installed control manifest: a later
additive control-schema migration needs its own reviewed historical-manifest
compatibility handling, not a rewrite of this immutable audit. Commit or cleanup
uncertainty requires trusted durable inspection; the API does not retry.

Deployment still requires a verified coherent backup and SHA256, schema/identity
preflight, integrity/FK checks, claim/seal/audit inventory, DELETE/WAL and sidecar
verification, permissions/durability checks and deliberate restore-generation
fencing. Existing verified-backup tooling is not invoked automatically, and no
production backup/preflight/migration was performed. The migration deliberately
does not claim to verify a backup that an operator has not supplied/reviewed.

The migration creates no execution claims and grants no execution authority.
Synthetic claim/history rows in disposable tests exist only to exercise constraints;
the migration itself creates storage and its installation audit only. There is no
production claim issuer, lease, writer capability, receipt, readiness or activation.

### Implementation validation results

* Focused migration tests: 17 passed, 32 subtests passed. Covers fresh DELETE/WAL
  installs, exact sqlite_master/table_info/index_list/foreign_key_list inspection,
  populated-record preservation, idempotence, incompatible/partial/missing objects,
  scalar/canonical/NUL/scope/physical constraints, deferred audit FK, immutability,
  duplicate operation rejection, legacy storage preservation, no key-helper access,
  target DML denial and mid-DDL/audit/final-validation rollback.
* Complete recognition/deployment suite: 1029 passed, 3 skipped, 1757 subtests passed.
* Guarded full suite: 1469 passed, 3 skipped, 2046 subtests passed. The runner disabled
  deployment defaults, restricted SQLite opens to disposable locations and blocked
  non-local network access. An initial guard incorrectly excluded the existing
  UUID-named Falls Church fixtures in the repository root; only that exact fixture
  filename pattern was added, its ten tests passed, then the full suite passed.
  No test assertions or product security gates were changed for the guard issue.
* git diff --check and new-file trailing-whitespace/final-newline checks passed.

All migration runs were against disposable fixtures. The migration created no
claim/history rows and performed no target DML. Constraint tests manually insert
synthetic rows solely to exercise storage guards; they grant no authority. No
hosted/production resource or deployment private key was accessed. No production
migration, backup, commit or push occurred. Production authorization, execution
and activation remain BLOCKED.

Validation on 2026-10-31: the complete test_recognition*.py family plus
test_pilot_deployment.py and test_pilot_readiness.py passed with 1012 passed,
3 skipped and 1725 subtests passed. This includes execution, runtime admission,
runtime approval and deployment/rehearsal coverage. git diff --check and the new
document's trailing-whitespace/final-newline checks passed. No hosted resources,
production database or deployment keys were accessed; no commit or push occurred.
