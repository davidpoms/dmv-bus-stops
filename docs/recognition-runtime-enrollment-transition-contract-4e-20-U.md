# Slice 4e-20-U: pending-plan and enrollment-continuity contract

**A. APPROVE 4e-20-U — enrollment-transition contract complete**

Design only. No Python, schema, migration, enrollment, writer, execution,
completion, recovery or activation implementation is introduced. This supplies
the missing transition contract identified by 4e-20-T, using the boundaries in
[4e-20-S](recognition-runtime-target-entry-contract-4e-20-S.md),
[4e-20-R](recognition-runtime-writer-phase-contract-4e-20-R.md) and
[4e-17](recognition-runtime-live-attempt-storage-writer-contract-4e-17.md).
It authorizes no production ceremony or change to the fingerprint algorithm.

## 1. Current contract and generation notation

An enrolled installation starts at **G**, target fingerprint **H0**, runtime
profile **P0**. The two advances already specified by 4e-17/S are:

```text
G:   enrolled P0, H0; plan preparation changes neither generation nor hash
     -> target DDL commit changes actual schema to H1
G+1: verified H1 binding, null runtime profile, NOT_ACTIVATED
G+2: fresh enrolled P1, H1, NOT_ACTIVATED; plan finalized atomically
```

The prompt's illustrative G+1-current/G+2-new-hash diagram must not shift these
established meanings. If an actual starting generation is numbered G+1, rename
the source to G before applying this contract; do not omit either advance.
The target hash changes physically before the first binding advance. It does
not become trusted runtime scope at that instant.

Current source findings:

| Function/module | Consequence |
| --- | --- |
| `enrollment._schema` | Hashes ordered non-sqlite_* sqlite_master type/name/table/raw SQL plus application_id/user_version. Adding entry DDL changes H0; row changes alone do not. |
| `administration.observe_target`, `_verify` | Strict actual physical observation and entire target hash must equal the binding; installation/target/owner metadata must match. H1 against an H0 binding fails. |
| `runtime_validation._history`, `_identity_snapshot` | Exact binding chain and initial-enrollment provenance; current profile must exist and equal binding/actual target hash. Null profile or H1 against P0 fails. |
| `runtime_enrollment.enroll_runtime_profile` | Initial-only from null profile; exact deployment observation, hidden nonce, challenge/private-log approval, generation + 1, atomic revocation/audit and control commit before target release. Nonnull P0 cannot be replaced by this API. |
| `runtime_profile_schema` guards | Challenge binds current source generation/digest; profile matches challenge, paths/inodes/schema and destination source + 1; current binding/profile/auth scope cross-checks. These checks must remain. |
| `administration_schema.check_control`, claim/authority/attempt manifest readers | Exact recognized schema and migration chain. Unknown/partial extension fails, including a new plan table without registered definitions/history. |
| `local_readiness._state` | Changed binding target derives NOT_ACTIVATED without rewriting the old ledger. It does not issue an activation incarnation. |
| Existing migrations and reservation owners | Savepoint-safe local migration and control-first locking conventions exist; no pending-plan/transition implementation exists. Query-only runtime/auth/coordinator owners cannot perform this DDL. |

At H1/P0, weakening `_verify`, accepting either hash, mutating P0 or skipping
enrollment would defeat the current contract. Instead only a narrowly typed
transition owner may verify an exact planned DDL delta; ordinary readers remain
denied. This is a new restricted administrative ceremony, not runtime authority.

## 2. Plan identity and prerequisites

The versioned plan body has exactly these keys:

```text
format = recognition-runtime-target-schema-transition-v1
plan_id
installation_id
target_id
owner_id
source_generation
source_binding_sha256
source_profile_sha256
source_auth_epoch
source_mfa_epoch
target_schema
control_schema_sha256
migration_id
activation_head
created_at_utc
deadline_at_utc
operator
reason
```

`target_schema` has exactly `before_sha256` (H0), `after_sha256` (H1) and
`added_definitions_sha256`. That last digest is of the repository's exact reviewed
name-to-SQL target addition manifest. `migration_id` is the registered
`recognition-runtime-target-entry-storage-v1` package, not a caller SQL selector.
Its exact definitions must be supplied by the later target-entry storage slice.
No arbitrary schema migration/SQL, seal or family change can use this plan.

H0/H1 are complete target schema identities, not table-subset hashes. H1 is
computed by the unchanged fingerprint helper on a disposable schema preview
with only the reviewed additions. Verify all old objects' exact raw SQL and
unchanged application_id/user_version. A supplied hash is only an expectation,
never evidence of actual installation. The package ID/definition digest/full
H0/H1 uniquely describe the intended schema transition; no redundant generic
"schema version" or caller-defined schema label is accepted.

`control_schema_sha256` is the existing control manifest helper's hash **after**
installation of the inert recognized plan extension, before plan creation.
No control DDL occurs between preparation and finalization. Row additions do
not change that hash. This is not the target fingerprint or an enrollment
generation. The exact migration package version is also not an activation ID.

`activation_head` has exactly `sequence`, `event_sha256`, `state`, resolving to
the actual latest validated activation ledger row. Require raw head state
NOT_ACTIVATED or DEACTIVATED and a nonactive effective state; SUSPENDED,
RECOVERY_REQUIRED or an old raw ACTIVATED head is insufficient. Pin the same
raw head throughout. Generation changes do not carry forward activation.

All source identities, profile, epochs and head are read from durable state
under reservations, never established by operator arguments. The local trusted
operator supplies plan UUID, explicit reason/operator, expected G/source digest,
reviewed package/manifest/hash expectations and an explicit deadline. Source
owner remains the verified project owner; require existing ENROLLED MFA epoch
metadata before preparation, without reading the MFA secret/key. If unavailable,
finish the existing owner/MFA setup before beginning this ceremony.

Require strict old deployment target/control identity, exact valid P0 history,
installation/target/owner, target auth epoch and MFA epoch; trusted verified
backup evidence; no pending plan, unsettled claim, attempt, target entry, orphan,
uncertain commit or blocking recovery. A CREATED attempt is unsettled: do not
delete it or reinterpret it as terminal to make migration possible. Existing
deployments with unsettled work require a separately reviewed disposition before
preparation. Never infer that an independently restored store had no prior work.

Use existing canonical JSON/digest and bounded validators: canonical UUIDs,
lowercase SHA256, exact keys/no duplicates/extras/NUL, integer-not-bool/float,
canonical UTC, explicit bounded operator/reason, source G <= 2^63-3. Body bound
is existing authority MAX_BYTES. `plan_sha256 = digest(body)` is stored outside
the body; no recursive/self digest.

Require creation < deadline within the existing UTC range, current authoritative
time >= creation and < deadline before every forward commit, with monotonic/
wall-clock anomaly rejection inside an owner. There is no default borrowed
authentication TTL: this is an operator-chosen maintenance deadline, not an
authorization credential. Challenge expiry remains exactly 600 seconds; final
enrollment must satisfy **both** deadlines. Expiry never clears the plan fence,
permits renewal or authorizes rollback/retry. An expired incomplete plan requires
manual inspection and a separate reviewed resolution policy.

## 3. Exact additive control representation

Two append-only tables, with no mutable pending boolean or new target table:

### `recognition_runtime_schema_transition_plans`

| Column | Type and constraints |
| --- | --- |
| `plan_id` | TEXT NOT NULL PRIMARY KEY, canonical UUID. |
| `installation_id` | TEXT NOT NULL, canonical UUID. |
| `source_generation` | INTEGER NOT NULL, 1 through 2^63-3. |
| `source_binding_sha256` | TEXT NOT NULL UNIQUE, canonical SHA256. |
| `source_profile_sha256` | TEXT NOT NULL, canonical SHA256. |
| `created_at`, `deadline_at` | INTEGER NOT NULL, existing UTC range; created_at < deadline_at. |
| `body_json` | TEXT NOT NULL, bounded exact canonical plan object. |
| `body_sha256` | TEXT NOT NULL UNIQUE, plan digest. |
| `audit_sequence` | INTEGER NOT NULL UNIQUE, preparation audit. |

UNIQUE `(installation_id,source_generation)`. FK source generation to admin
binding generation, source binding digest to binding body digest, source profile
digest to runtime profile digest; guard that all resolve to the **same** current
source/install/target/owner, enrolled P0 and H0. Audit FK is DEFERRABLE INITIALLY
DEFERRED. Column/body equality is mandatory. Reject a second unfinished plan for
the installation, even from another generation: this is an insertion guard over
validated histories, not a partial index on a mutable status.

### `recognition_runtime_schema_transition_history`

Columns: `plan_id TEXT NOT NULL`, `sequence INTEGER NOT NULL`, `state TEXT NOT
NULL`, `at INTEGER NOT NULL`, `previous_sha256 TEXT NULL`, `body_json TEXT NOT
NULL`, `body_sha256 TEXT NOT NULL`, `audit_sequence INTEGER NOT NULL`,
`destination_generation INTEGER NULL`, `destination_binding_sha256 TEXT NULL`,
`destination_profile_sha256 TEXT NULL`.

PK `(plan_id,sequence)`; UNIQUE `(plan_id,state)`, body digest, audit sequence.
FK plan to plan row. Deferred audit FK. Deferred destination generation and
binding-digest FKs to admin bindings, and deferred destination profile FK to
runtime profiles; exact same-row/scope guards supplement independent FKs.
Destination columns are all null for events 1/2; event 3 requires G+1/binding
digest and null profile; event 4 requires G+2/binding/profile digests.

Only the following exact sequence/state pairs are legal:

1. PREPARED
2. MIGRATION_INTENT
3. SCHEMA_BOUND
4. FINALIZED

First predecessor is explicit null; each later predecessor is the exact prior
event digest. No skipped/repeated/reversed edge, cancellation, reset, recovery or
expiry transition. Event time is nondecreasing from plan creation and each
forward producer must still meet the original deadline. Historical validation
does not reject an old finalized row simply because today's time is later.

Canonical event body keys are exactly `format`, `plan_id`, `plan_sha256`,
`sequence`, `state`, `at_utc`, `previous_sha256`, `actor_id`, `operator`, `reason`,
`evidence`; format is `recognition-runtime-schema-transition-event-v1`.
Actor is the exact plan/source owner, operator/reason are explicit bounded
ceremony inputs (preparation equals plan inputs). Exact evidence shapes:

| Event | Evidence object keys and authoritative values |
| --- | --- |
| PREPARED | `source_binding_sha256`, `source_profile_sha256`: exact plan values. |
| MIGRATION_INTENT | `prepared_event_sha256`: event 1 digest. Conservative intent only. |
| SCHEMA_BOUND | `intent_event_sha256`, `observed_schema_sha256`, `generation`, `binding_sha256`: event 2, independently observed H1, G+1 and exact disabled binding. |
| FINALIZED | `schema_bound_event_sha256`, `generation`, `binding_sha256`, `profile_sha256`, `challenge_sha256`, `observation_sha256`, `review_sha256`: event 3, G+2 and exact new enrollment graph. |

All values resolve to the complete plan and exact immutable prior scope, not
merely matching hashes in caller data. A committed target schema is checked by
the owner; SQLite cannot FK a separate file. No ATTACH or fabricated cross-file
constraint. Event/body/index time, digests and destination fields must agree.

Every plan/history UPDATE/DELETE is denied. BEFORE INSERT collision guards cover
every PK/UNIQUE key and reject OR REPLACE even with recursive triggers off.
Use current SQL canonical UUID/SHA/time/JSON/NUL constraints and Python row
validation, with immutable profile/large decimal-text behavior preserved.

Preparation inserts plan + PREPARED + one matching audit atomically, sharing
their preparation audit sequence. Other events each have a fresh audit.
Audit actions are `runtime_target_schema_transition_prepared`,
`runtime_target_schema_transition_intent_recorded`,
`runtime_target_schema_transition_completed` (SCHEMA_BOUND, **DDL** completion),
and `runtime_target_schema_transition_finalized`. Exact audit subject keys:
`plan_id`, `plan_sha256`, `event_sequence`, `event_sha256`. Audit actor is the
explicit local operator; body operator/time must match; actor_id resolves to
the owner. Creation/audit triggers, deferred FKs and whole-row readers must
require complete exact graphs; no orphan event, reused audit or half plan may
commit. The existing enrollment audit remains separately unchanged.

An installation is pending if any structurally valid plan lacks its complete
valid FINALIZED graph. Malformed/missing plan/history/audit/extension is a denial,
never NO PLAN. A final flag without its binding/profile/enrollment graph does
not clear the fence. Historical plans remain permanently inspectable.

## 4. Legal durable prefixes and manager ownership

All future writers are explicit trusted-local administrative ceremonies, not
HTTP routes, background jobs, collector self-enrollment or ordinary runtime
authentication. Reuse existing connection/reservation/savepoint conventions;
do not modify `administration.transaction`, `_verify`, target_identity, Slice H
or query-only runtime owners. A typed transition manager owns control-first
BEGIN IMMEDIATE, target reservation, permitted fixed DDL, commit/rollback and
cleanup; no raw handle/SQL/callback/transaction control is exposed to callers.

| Prefix | Authoritative storage and meaning | Fence / continuation |
| --- | --- | --- |
| NO PLAN | Exact installed schema and complete history show no unfinished plan. | Existing gates apply; no new authority. |
| PLAN RECORDED | Control plan/PREPARED/audit + auth revocation/approval invalidation committed; actual target still H0. | Durable append-only pending fence. No ordinary admission. Only original typed maintenance continuation may proceed. |
| TARGET MIGRATION STARTED | Control MIGRATION_INTENT/audit committed before any target DDL. | Durable conservative intent, not proof DDL ran. Remains blocking after crash. |
| TARGET MIGRATION COMMITTED | Independently observed exact target H1; control may still have G/INTENT. | Actual schema fact, not an invented control state. Unexpected/uncertain prefix blocks; no automatic completion. |
| SCHEMA_BOUND | One control commit appends G+1 disabled binding + event 3/audit after independent H1 verification. | Pending; null profile. Only scoped challenge/evidence/enrollment ceremony may proceed. |
| ENROLLMENT TRANSITION COMMITTED / PLAN FINALIZED | One control commit inserts P1, G+2 binding, unchanged enrollment audit, FINALIZED event/audit and revocation/invalidation. | Same durable atomic prefix. There is no permitted committed enrollment-without-finalization interval. Normal gates may then evaluate fresh scope; activation remains off. |

Preparation: validate old deployment observations/history/P0/epochs/nonactive
ledger/package/backup/no unsettled work under control then query-only target
reservations. Append plan/PREPARED, call existing authentication invalidation
and nondestructive approval invalidation, validate full graph, commit control
while target remains reserved. Release target only after control outcome resolves.
No generation advance or target DDL here.

Before target DDL, a fresh ordered phase rechecks original plan/identity/H0,
deadline/head/epochs/revocations and commits MIGRATION_INTENT on control while
target is reserved/query-only. Release afterward. This durable marker fences a
crash before the first DDL statement. No automatic repeat from INTENT is allowed.

Original live maintenance continuation then reacquires control and target in
order and repeats every check. Only manager-owned fixed reviewed DDL/savepoint
may disable query-only and advance/invalidate target reservation epochs. Check
exact H1/raw definitions, integrity/FKs, unchanged application/metadata rows and
actual physical observations; commit target with control held. No entry record,
family row, completion or execution result is created.

Reacquire target/query-only while control is still held. Independently verify
H1/package/physical continuity and all current control scope/time. In one control
transaction append the exact G+1 binding and SCHEMA_BOUND graph; verify existing
revocation/invalidation and commit control before releasing target. Confirmed
commit and cleanup are required before publishing inspection data. Any uncertain
target/control/cleanup outcome poisons the continuation; no reconnect-and-resume.

Plan installation itself is a separate inert control-only manifest migration:
savepoint-safe, explicit local, expected current generation, verified nonactive
state and strict identities, query-only target, empty plan tables, no binding/
generation/target changes or authority. Matching exact installation is a no-op;
partial/incompatible extension fails. Do not combine extension installation with
an unrecorded target DDL change or silently install it during normal access.

## 5. Exact G+1/G+2 continuity and enrollment guard

Let B0 be the complete source binding. At SCHEMA_BOUND, the **only** new B1 is:
copy B0 with generation G+1, previous digest digest(B0), fresh event time,
target schema SHA H1, runtime_profile_sha256 null, production_state NOT_ACTIVATED.
All deployment physical observations/install/target/owner remain identical.
The target auth epoch and control MFA epoch/secret remain unchanged; the plan
does not reset MFA or read its encryption key. Every old proof/session is revoked,
step-ups removed, confirmations spent; old scope is never reused because numeric
epochs happen to match. Pending approvals gain explicit invalidation/history,
not rewritten bodies. Repeat invalidation checks at B1 and B2 commits.

While SCHEMA_BOUND, allow only trusted-local plan-scoped 2a challenge issuance,
actual-runtime 2b **read-only observation**, and the typed local enrollment
ceremony. Challenge remains the existing format/600-second lifetime and must
bind exact current B1/G+1 and the unique SCHEMA_BOUND plan. This relationship is
derived and guarded from durable source generation/digest, not a browser flag.
No authentication, session or writer authority is issued by these exceptions.

The new named local API contract is
`enroll_transition_runtime_profile(config, *, plan_id, plan_sha256, ...)`, taking
the existing 2c expected-generation/source-binding/challenge/review digests,
explicit operator/reason/private-log approval and hidden nonce ceremony. No new
HTTP route or nonce argument/environment/file ingestion. Ordinary initial 2c
must not independently finalize a transition-owned B1; add a denial for that
scope rather than weakening its validation or changing its standalone format.

Require exact durable plan/event 3/B1, H1, current deployment identity/owner/
epochs/raw activation head/time. Validate genuine challenge, nonce hash, bounded
canonical review, all-worker agreement and actual WSGI observation by the
existing 2b/2c semantics. The complete runtime physical tuple (hostname, target
and control paths/device/inode) must equal P0 exactly; only target schema becomes
H1. No device drift, hostname exception, rotation, browser claim or console
impersonation is authorized. Unsigned evidence still proves content integrity,
not provenance; trusted private-log retrieval/operator approval remains required.

P1 retains the existing profile format, with challenge source B1 and generation
G+2. B2 is exactly B1 with G+2, previous digest digest(B1), enrollment time and P1
digest. This still satisfies `_history`'s null source + 1 and exact copy relation;
no general alternative-hash path or nonnull-profile replacement is needed.
H1 becomes an enrolled runtime fingerprint only through this complete graph.

Require **insertion guards**, not merely pretransaction file comparisons:

- Source B1 resolves to exactly one validated SCHEMA_BOUND plan/B0/P0/H0/H1.
- New profile matches P0's entire runtime physical tuple, H1, installation/
  target/owner, B1 challenge and G+2; it has unchanged 2c enrollment provenance.
- B1 insertion requires its same-transaction SCHEMA_BOUND event with deferred
  destination binding FK; forbid other unlinked null-profile resets from P0.
- B2/P1 insertion requires its same-transaction FINALIZED event. Insert that
  event first after computing exact digests/audit positions; its deferred binding,
  profile and audit FKs require the rest of the graph before commit. Profile and
  binding triggers can then require its presence. No ordinary 2c call can omit it.
- Finalization audit insertion checks the full profile/challenge/unchanged
  enrollment-audit/B2/plan-event graph. Whole-schema readers validate it again.

In one control transaction, with target query-only/reserved through commit,
perform revocation/invalidation and the complete enrollment/finalization graph.
Any failure rolls it all back, including P1/B2. There is no finalize-later API,
standalone fence clear or automatic completion after an uncertain result.
Once finalized, ordinary new enrollment/auth may run only its current strict
checks; no authentication is issued by this ceremony.

Raw activation history is unchanged. Its pinned nonactive head stays historical;
G+1/G+2 effectively remain NOT_ACTIVATED through existing target-scope rules.
No new activated incarnation is minted. Later activation requires the full
independent ceremony with fresh generation/profile scope. Old activation,
consent, readiness, approval and runtime objects cannot become current just
because selected fields match. This adds denial/continuity guards, not a new
activation or legacy execution semantic.

## 6. Admission fences and old-object disposition

The pending-plan check belongs in exact control schema/history readers and at
every authoritative admission/final-validation boundary, not only a route or
startup check. Fail closed before writes and repeat while reservations remain
held. Plan schema/history malformation is also blocking. Required integrations
for the future implementation:

Keep structural validation distinct from permission: `check_control` must fully
validate a legitimate pending graph as DATA so inspection and the typed
maintenance owner can read it. Ordinary admission then requires no pending plan;
maintenance uses an exact phase/scope check instead. No public boolean, arbitrary
callback or caller-selected reader mode may bypass that fence. At G+1 ordinary
runtime `_history` still rejects the null profile; the transition owner validates
the exact plan/B1/P0 provenance without pretending to be a normal runtime owner.

| Consumer | PREPARED / INTENT / uncertain | SCHEMA_BOUND | FINALIZED |
| --- | --- | --- | --- |
| Runtime validation/authentication, primary/session/step-up/confirmation | Deny admission/issuance. | Deny; challenge/evidence exception is not auth. | Existing strict fresh G+2 scope only. |
| Runtime authority issuance/coordinator/attempt creation | Deny, including an already-open original continuation at final validation. | Deny. | Fresh work only; original deadlines/epochs/generation still enforced. |
| Writer admission/execution, runtime and legacy | Deny; no claim/lease/target effects. | Deny. | Existing gates only; no new writer API or legacy conversion. |
| Readiness and activation | Report pending/not ready; deny any activating transition. | Still pending/not ready. | Recompute independently; remains NOT_ACTIVATED. |
| Challenges/collector/enrollment | No ordinary issuance/enrollment. | Only exact plan-scoped challenge, real observation and local transition enrollment. | Ordinary existing contracts; no old challenge replay. |
| Read-only inspection and existing emergency authority reduction | Allowed as inspection/reduction only, never fence clearing, resume or activation. | Same. | Existing rules. |

Control reservation serializes a conforming in-flight operation against prepare:
either its preexisting phase resolves first and preparation rechecks inventory,
or the durable plan wins and its next admission/final check denies. A new plan
cannot seize an active target writer. All conforming gates lock control first;
no control reacquisition while holding target and no Python mutex as authority.

Old authorities, approvals, operations and activation/readiness evidence remain
immutable historical records with original G/P0/H0; no wrapping or portability.
Approvals are nondestructively invalidated. Runtime claim/attempt/entry or legacy
execution that is unsettled blocks preparation. Resolved legacy claims/seals/
completion histories remain unchanged and inspectable through their own readers;
they confer no G+2 authority. Old process-local objects are never upgraded or
imported. Existing generation/profile/digest checks continue rejecting them even
after the plan is FINALIZED; the fence clearing is not authorization.

Do not retrofit generic legacy claims/recovery, fabricate EXECUTING or weaken a
writer lease. Adding a pending-plan rejection to legacy admissions is an extra
safety fence; legacy record formats, legal transitions, verification, receipt
semantics and completed historical outcomes remain unchanged.

## 7. Crash, uncertainty, replay and concurrency

No cross-database atomicity or rollback-after-commit exists.

| Observation/prefix | Safe read-only conclusion and required action |
| --- | --- |
| Crash before plan commit | Read complete durable graph. No partial plan may commit; absence is only current state evidence, not proof of no historical work after restore. |
| PREPARED with H0 | Plan exists; no durable intent yet. After termination, no original live continuation; inspection only, no automatic resume. |
| INTENT with H0 | DDL may not have started or may have rolled back. Never infer safe retry from H0 alone; manual inspection required. |
| INTENT with exact H1 | Target DDL committed but control binding may not have. Keep fence, inspect exact package/identity/application rows; no automatic B1/adoption/reapply. |
| Any intermediate/unexpected schema | Deny all authority. Preserve evidence; manual review, not repair or acceptance of either hash. |
| Target commit succeeds, control commit fails/uncertain | Target cannot be rolled back by control. Pending prefix blocks; inspect both stores under fresh trusted reservations. No automatic completion. |
| B1/SCHEMA_BOUND but target H0 | Impossible normal commit order; restore/corruption/conflicting stores. Stop, no enrollment or schema replay. |
| B1 with H1 | DDL is bound but no current runtime profile; still pending. Only fresh explicit scoped challenge/enrollment, never old authority. |
| G+2/P1 without valid FINALIZED graph, or vice versa | Not a legal committed prefix; deferred/graph checks must reject it. Report corruption/uncertainty, never clear the fence. |
| Valid G+2/P1/FINALIZED with H1 | Finalization confirmed historically; no activation/auth/writer result. Lost caller acknowledgement is handled by inspection, not replay. |
| Connection loss, failed cleanup, clock anomaly or deadline expiry | Poison live continuation; incomplete plan remains blocking. No reconnect, renewal, rollback inference or automatic retry. |

Inspection is read-only and validates exact schema/manifest/binding/audit/plan/
profile history plus actual physical/H0-or-H1/package observations. Stable paired
inspection requires the approved control-first/target reservation mechanism;
ordinary detached observations without a stable pair report UNCERTAIN, not a
cross-store atomic snapshot. No key read, enrollment, activation or authority
creation is part of inspection. Recovery mutation/resumption/cancellation is
deliberately not defined: manual inspection is necessary but does not itself
authorize a write. A separate reviewed resolution policy is needed for abandoned,
expired or uncertain plans; startup/workers must leave them blocked.

Idempotency means immutable identity, not automatic replay:

- Identical recorded plan ID/digest: return historical inspection only; no new
  time, revocation, target DDL, generation advance or continuation from lookup.
- Conflicting plan ID/digest, same source generation or unfinished installation:
  reject. Unique keys plus insertion guards and control BEGIN IMMEDIATE decide.
- Duplicate migration request at INTENT/SCHEMA_BOUND: inspect/reject, never replay
  DDL or advance G twice, even when schema already matches H1.
- Repeated enrollment/finalization: existing unique challenge/profile/generation
  and event keys reject; matching finalized graph is inspection-only.
- Stale/expired plan or wrong expected G/binding/phase: deny forward mutation.
  Deadline cannot be extended; no delete/new-plan escape for an unfinished plan.

Competing plans, transition/enrollment callers and runtime/activation admissions
use separate real DB connections and control-first reservations. At most one
plan, DDL intent, B1 and B2/finalization graph can win. Target reservations
remain held through each control commit; target DDL commit/reacquisition is an
explicit epoch change with borrowed-view invalidation. Do not reuse old views
or silently replace connections. SQLite BUSY/LOCKED remains a failure; no retries.

## 8. Manifest and implementation boundary

The future control extension migration is
`recognition-runtime-enrollment-transition-storage-v1`; its audit action is
`runtime_schema_transition_storage_installed`. Follow the existing explicit
control migration audit shape: migration_id, previous_schema_sha256,
installed_schema_sha256, installation_id, generation, reason; actor/time remain
in the existing audit envelope. Verify predecessor, exact new definitions,
single audit and scope before computing historical manifest projections.

`administration_schema.check_control` must recognize exactly both plan tables,
their guards and migration record. Extend the claim/authority/attempt historical
manifest chain only through this verified addition (S2 -> S3), excluding only
the exact recognized new definitions when reconstructing old manifests. Unknown
or altered SQL, missing audit, partial extension or unrecognized later schema
must fail. Do not weaken the exact schema inventory or let caller exclusions
silently project arbitrary tables away. Existing fingerprint helpers are unchanged.

Future implementation touchpoints: new plan schema/codec/inspection module and
explicit local migration CLI; exact schema/manifest readers; narrowly typed
transition manager; pending fences in shared validation/auth/readiness/activation
and legacy admissions; transition enrollment wrapper and stricter insertion
guards; focused tests. The standalone 2a/2b/2c formats remain unchanged. Normal
runtime access never installs schema or changes enrollment.

4e-20-V implements the inert recognized control storage/guards/migration first.
It cannot apply target DDL until the separately reviewed target-entry package
from 4e-20-T exists and exactly matches the plan manifest. Unrecognized/unavailable
package means no executable plan, not invented SQL. Target-entry storage follows;
no writer admission is implied by either migration. Business effects, seals,
completion and recovery stay outside this boundary.

## 9. Required focused contract-test matrix

No tests are implemented/run in this documentation slice. Future disposable tests:

- Clean preparation: exact canonical plan/digest/schema identity/owner/epochs/
  nonactive head, full graph/audit, one revocation/invalidation commit, unchanged
  generation/target and no authority. Invalid UUID/SHA/NUL/type/time/path/decimal,
  JSON duplication/extras/canonicality and huge lossless identities reject.
- Duplicate/conflicting plans and all UPDATE/DELETE/REPLACE collision keys,
  partial/altered schema, missing audit/half graph, source FK same-row mismatch,
  wrong predecessor/edge/sequence/time/destination reject transactionally.
- Target H0/H1/added-definition and control manifest mismatches; changed raw SQL,
  application_id/user_version or physical identity; caller-supplied preview/hash
  never substitutes for actual computation. Unregistered package denies DDL.
- Fault/termination before PREPARED, INTENT, DDL/savepoint, target commit before/
  after effect, reacquisition, B1 commit and cleanup: exact legal prefix and
  blocking inspection status; no automatic retry/adoption/repair.
- G+1: exact B0 copy except defined fields, P0 immutable, null profile, verified
  H1 and event 3; no G+1 scope accepted against H0. Target/control/application
  rows and original activation ledger otherwise unchanged.
- G+2: genuine challenge, nonce hash, real runtime evidence/private-log approval,
  all-worker agreement, P0 physical continuity/H1, exact initial profile/B2
  provenance plus FINALIZED in one control commit. Direct standalone 2c or SQL
  attempting to bypass transition guards fails, including missing finalization.
- Enrollment/control commit uncertainty, every final graph insertion failure and
  restart: all-or-nothing P1/B2/finalization; no finalized-only or enrollment-only
  graph; no automatic reacquisition/re-enrollment. Matching finalized lookup is
  inspection only, with no fresh credentials/activation/token.
- Expired/stale plan, generation/source/profile/head/owner/auth/MFA changes and
  challenge expiry/clock rollback: no forward advance, fence persists. No deadline
  extension, conflicting replacement, profile reset or epoch reuse escape.
- Concurrent plans, DDL, enrollment, runtime admission and activation via real
  connections/processes under DELETE and WAL: one winner; final checks exclude
  races, control commit precedes target release, epochs/views invalidate; no lock
  retry workaround or mutex-based authority.
- Every pending state blocks real runtime auth, authority issuance, coordinator/
  attempt creation, readiness, activation and legacy/runtime execution admission;
  permitted evidence/inspection exceptions create no authentication. Finalized
  state still rejects old authorities/attempts/operations/approvals/objects.
- Populated legacy claim/history/seal/receipt and runtime historical snapshots
  remain symmetric/unchanged; unsettled work blocks prepare; completed history is
  inspectable, never portable. No synthetic EXECUTING, writer or target effects.
- Inert extension install: success/no-op, partial rejection, savepoint/outer
  rollback and exact manifest predecessor projections; no target DDL, generation
  advance, profile/plan/authority creation, startup migration or secret reads.

## 10. Review result and validation

The transition is representable with the existing strict binding-chain and
initial-enrollment model plus explicit additive plan guards and a typed local
ceremony. No activation inheritance, alternative hash, changed fingerprint
algorithm, cross-database atomicity or legacy authority conversion is needed.
These additions are the contract for the next implementation, not existing APIs.

Only this document is added. Validation: `git diff --check` passed; no existing
cheap document-link checker was found in the inspected repository scripts.
No executable changes, tests, hosted/production access, real-key reads, commit
or push. Preexisting working-tree changes remain untouched.

Next boundary: **4e-20-V — pending-plan/enrollment-transition storage and
migration implementation**, followed by target-entry storage. Actual transition,
writer admission, execution and activation require their own subsequent gates.

PRODUCTION AUTHORIZATION: BLOCKED
PRODUCTION EXECUTION: BLOCKED
PRODUCTION ACTIVATION: BLOCKED
