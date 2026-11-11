# Slice 4e-11: activation-bound runtime authority producer contract

Design/review only. No producer, ceremony, schema, migration, authentication,
writer, recovery or activation implementation is added. This contract proposes
the new lineage that was missing in 4e-10; it does not make the current runtime
executable. Existing production gates remain in force.

## 1. Repository findings and deliberate design decision

An "activated runtime profile" is not a new profile type or mutable profile
flag. It means the exact current enrolled profile and installation binding pass
`runtime_validation._identity_snapshot()` and the current activation passes
`local_readiness.require_activated()`. The binding's `production_state` marker
remains `NOT_ACTIVATED`; the independent activation ledger is authoritative.
That marker alone neither proves nor disproves a valid activated incarnation.

Initial enrollment in `runtime_enrollment.enroll_runtime_profile()` requires a
null current profile, a deployment-issued challenge, independently reviewed
runtime observations, explicit operator consent and a hidden nonce. It inserts
an immutable runtime profile at source generation + 1, preserves deployment
observations, invalidates authentication and pending approvals, and commits
control while the query-only target reservation remains held. It does not
rotate a profile or activate anything. `runtime_validation._history()` verifies
the complete binding/challenge/profile/review/audit graph. `_identity_snapshot()`
then checks actual runtime observations, schema, owner access and epochs.

`runtime_auth` issues existing primary/session primitives under the preactivation
owner. The shared activated reader can validate existing genuine profile-scoped
credentials; it does not issue activated logins. `runtime_activated_owner` is a
read-only observer, explicitly `execution_authority=False`. Its live context
cannot be reused as a control-writing producer or target-writing owner.

The existing proposal, ACK and v2 approval are exact, immutable, profile-scoped
prerequisites. None contains activation consent or execution authority. The
4d-1 claim schema and 4d-2 consumption remain permanently preactivation.

**New design decision:** use a fresh activation-bound owner ceremony and a new
authority record, not another consumed-claim version or a conversion of 4d-1.
An unchanged runtime v2 approval can be a prerequisite, but a new explicit owner
decision must authorize its exact operation for the exact current incarnation.
This is the explicit compatibility policy requested in this review: it replaces
the earlier *proposed* requirement in 4e-3 for an entirely new operation/ACK/
approval/claim family. It does not alter those existing formats or confer new
meaning on their historical decisions. No callable compatibility rule exists
until this contract and its later implementation receive review.

To prevent adoption, an operation with **any** current 4d-1 claim row, regardless
of expiry or disposition, is ineligible for this new producer. Also reject any
legacy execution claim, entry/seal/effects conflict, operation revision or prior
runtime authority for that operation. Such operations require a separate future
retirement policy, not an automatic replacement claim or copied manifest.

The intended lineage is:

```text
current enrolled runtime profile + current validated activation
  -> fresh owner/MFA activation-bound producer ceremony
  -> durable runtime execution authority + AUTHORIZED history
  -> future distinct one-use runtime writer capability
  -> future fixed family transaction and independent completion evidence
```

4d-1 claim != activated authority. 4d-2 handoff != activated authority.
Neither is accepted as an input, source credential, predecessor or FK domain.

## 2. Producer and trust boundary

Only a separately registered, manager-owned activated producer may issue this
authority. It runs in the enrolled runtime, requiring genuine current primary
and session references, owner role/access, current MFA enrollment/epochs and
fresh TOTP using the existing `admin_auth._code()` verification, replay counter
and throttle semantics. Host/database administrators and deployed code remain
trusted. A digest is not remote attestation. Browser identity fields, imported
scope objects, console hostname overrides, environment booleans and CLI
confirmation flags cannot establish any prerequisite.

The caller may supply lookup references, credentials, explicit decision/reason
and one-use ceremony tokens. The producer derives all binding values from
durable state and actual observations under reservations. No caller-supplied
operation body, target, manifest, dependency list, activation body or clock is
authoritative. No route or CLI is implemented by this slice.

The future producer must independently repeat the protected readiness policy,
exact proposal/ACK and effective v2 approval readers, strict identity/schema,
dependency checks and complete 4e-7 claim inventory. Global blocking claim
disposition still rejects issuance; the selected operation's any-4d-1-claim
exclusion is an additional stronger rule. Empty inventory is not assumed on
reader failure. Existing read-only owner registries and 3a/3b meanings must not
be widened or impersonated.

## 3. Exact authority identity and scope

Proposed format: `recognition-runtime-execution-authority-v1`.
The producer generates `authority_id` with a cryptographically random canonical
UUID. `authority_sha256 = digest(body)` using existing canonical serialization;
the digest is stored outside the body, avoiding self-reference. Exact body keys:

```text
format authority_id operation_reference runtime_target physical_snapshot
activation approval authentication producer_ceremony dependencies
emergency_stop readiness issued_at_utc expires_at_utc lifetime_policy
```

The nested exact sets are:

| Object | Exact fields |
| --- | --- |
| `operation_reference` | `operation_id`, `operation_sha256`, `event_id`, `event_sha256`, `preparation_id`, `preparation_sha256`, `writer_family`, `writer_manifest_sha256`, `population_sha256`, `proposal_reference` |
| `runtime_target` | Unchanged validated `recognition-runtime-operation-target-v1`: `format`, `installation_id`, `target_id`, `generation`, `owner_id`, `binding_sha256`, `runtime_profile_sha256`, `auth_epoch`, `mfa_epoch` |
| `physical_snapshot` | `target`, `control_identity`; target is the existing `observe_target()` result, control identity the existing strict physical identity |
| `activation` | `sequence`, `event_sha256`; resolve the entire event/ceremony from the ledger, never trust this pair alone |
| `approval` | `approval_id`, `approval_sha256`, `effective_history_sha256`; require format `recognition-runtime-approval-v2` and APPROVED current state |
| `authentication` | `actor_id`, `primary_sha256`, `session_sha256`; actor must equal current owner |
| `producer_ceremony` | `step_artifact_sha256`, `confirmation_artifact_sha256`, `confirmation_token_sha256`, `decision`, `reason`; decision exactly `authorize_runtime_execution` |
| `dependencies` | `snapshot`, `snapshot_sha256`; full existing dependency snapshot, not merely event IDs |
| `emergency_stop` | `snapshot`, `snapshot_sha256`; complete validated stop/block observation for this operation |
| `readiness` | `assessment_sha256`, `assessed_at_utc`, `policy`; policy exactly `recognition-runtime-readiness-recompute-v1` |

`proposal_reference` retains the exact existing 4b-1 reference fields. Readiness
hashes the exact protected assessment binding; it does not hash or expose key
contents. Preserve integer physical observations in their existing JSON format;
where indexed as SQL text, use canonical lossless unsigned decimal, never SQLite
numeric casts. Python executable/version are historical metadata only, not an
authorization comparison; PID/thread exist only in a live local capability.

All objects use bounded canonical JSON, reject extra/missing/duplicate keys,
NULs, floats, booleans in integer positions, noncanonical UUID/SHA/path/time,
and recompute every digest. Proposed authority body limit is 1 MiB, nesting 64;
dependency and operation codecs retain their stricter existing limits. Receipt
outcomes are not embedded in the authority. No plaintext tokens, TOTP, reviewer
keys, seeds, ciphertext, connection handles or PID are persisted in it.

Every captured field is immutable historical evidence. Its *current validity*
is not immutable: reread effective approval history, auth/owner/epochs,
profile/binding/generation, actual physical observations/schema, current
activation head, dependency state, stop/block state and readiness at issuance,
finalization and future execution. Equality of an old digest is insufficient
without authoritative current-state validation.

## 4. New versioned consent ceremony

Existing approval and activation confirmations are insufficient and must never
be reused. New formats are `recognition-runtime-authority-step-up-v1` and
`recognition-runtime-authority-confirmation-v1`. They are consent DATA, not login,
runtime authentication, writer capability or durable authority by themselves.

The fixed ceremony subject consists of the authority body's exact operation,
runtime target, physical snapshot, activation, approval, authentication,
dependencies and stop objects, plus the exact current readiness assessment
binding and reason. It excludes the future authority UUID/digest, which do not
exist yet. Its digest is `subject_sha256`. The displayed review must identify
the operation, frozen population/manifest, activation sequence/digest and current
installation/profile/generation. No silent worker or target selection.

Use `local_readiness._assessment_binding()` to remove only the fresh
`assessment_at_utc` from the consent subject; compare its remaining exact facts
on every recomputation. Never drop deadline, prerequisite, disposition or scope
fields to obtain equality. The authority separately records the latest actual
`assessed_at_utc`. A merely later observation time cannot renew consent.

Exact step artifact fields: `format`, `token_sha256`, `subject`,
`subject_sha256`, `actor_id`, `primary_sha256`, `session_sha256`,
`issued_at_utc`, `expires_at_utc`. Exact confirmation artifact fields are the
same plus `step_artifact_sha256` and `decision`. Validate subject digest,
actor/credential agreement and exact decision; the explicit reason is carried
inside the subject, not inferred. All artifact digests cover the complete
canonical artifact; each has a 1 MiB bound and strict field/type validation.

1. Under a dedicated producer owner (control first; target reserved/query-only),
   validate all prerequisites and fresh TOTP. Append a typed step artifact to
   the existing audit and advance only existing TOTP replay state. Return one
   opaque random step token; persist only its SHA. The artifact binds actor,
   primary/session hashes, subject digest, issue/expiry times and current scope.
2. A matching authenticated owner explicitly chooses
   `authorize_runtime_execution` and reason. Revalidate current facts; insert a
   one-use row in `recognition_admin_confirmations` and append the full typed
   confirmation artifact to the audit. Its scope is
   `runtime-authority:<operation UUID>`; `operation_sha256` is the exact envelope
   digest, `state_sha256` the exact subject digest, generation and actor/session
   must match. Existing confirmation columns suffice; do not misuse action
   `approve`, re-use approval artifacts or expand the old ACTIONS semantics.
3. Issuance revalidates the typed audit/artifact chain, unexpired step and unused
   confirmation, current credentials/scope and exact subject. A compare-and-set
   changes `used=0` to `used=1` and inserts authority, AUTHORIZED genesis and audit
   in the same control transaction. Rollback restores all issuance mutations.

Audit action names are `runtime_authority_step_up_issued`,
`runtime_authority_confirmation_issued`,
`runtime_authority_confirmation_consumed`, `runtime_execution_authority_issued`
and later `runtime_execution_lifecycle_recorded`. Step/confirmation subjects
are their complete typed artifacts. Consumption subject has exactly `format`
(`recognition-runtime-authority-confirmation-consumption-v1`), `token_sha256`,
`artifact_sha256`, `subject_sha256`. In issuance order, spend the confirmation,
append its consumption audit, insert authority and AUTHORIZED genesis, then
append issuance audit. Issuance subject is exactly `authority_id`,
`authority_sha256`, `event_sequence`, `event_sha256`. Both authority and genesis
reference that last audit sequence. Event and authority digests exclude audit
row digests, preventing a circular dependency. Final graph checks require both
audit records and exactly one consume/issue for that confirmation.

Generate each raw step/confirmation token with `secrets.token_urlsafe(32)`;
never put it or the TOTP into audit, CLI arguments, files or diagnostic logs.
Immutable consumption-audit lookup also rejects a confirmation whose mutable
`used` flag was accidentally reset. A row flag alone is insufficient.

Step/confirmation deadlines are server-chosen, at most `RECENT_SECONDS` and
bounded by primary/session expiry, with unchanged epoch/profile/activation and
subject. Only one confirmation may be issued per step token (audit history must
enforce this under the control reservation). One TOTP cannot issue another step
because the existing replay counter applies. On any failure, existing verified
denial/throttle/revocation persistence remains manager-owned and must not commit
partial authority state. No code reads a real MFA key during this design slice;
a future authorized MFA ceremony necessarily uses existing protected decryption.

## 5. Lifetime and invalidation

New explicit policy proposal: `recognition-runtime-authority-lifetime-120s-v1`.
It is independent of the 4d-1 300-second claim rule. Set

```text
expires = min(issued + 120,
              primary expiry, session expiry,
              producer step expiry, producer confirmation expiry)
```

Require integer UTC seconds, `issued < expires <= issued + 120`, canonical UTC
strings matching those columns, and current time strictly less than expiry.
No minimum remaining window is guaranteed; reject if already expired. This is
a proposed bounded safety limit, not a claim that deployed jobs fit 120 seconds.
Future fixed-writer rehearsal must prove it can finish inside the deadline;
otherwise review a new policy version, never renew an issued authority.

Sample fresh wall/monotonic time after locks, on finalization and immediately
before future effect commit. Use the reviewed paired-clock anomaly rules.
Never accept caller time, forward/rollback anomalies or a retry that changes
issue time/deadline. The authority cannot renew itself by a different token,
new process, activation, approval, profile or reason.

| Change | Effect on previously issued authority |
| --- | --- |
| Normal expiry | Reject future admission/write; preserve historical row and outcomes |
| Activation suspended/deactivated/recovery-required | Reject immediately at next fresh check |
| Reactivation | New ledger sequence/digest; reject even if all other scope matches |
| Repeated ACTIVATED request | Existing same-state transition rejection remains; no second counter |
| Profile or generation | Exact binding/profile mismatch; reject; do not transfer |
| Owner/access/verified status | Reject; no identity reassignment |
| Auth epoch/key or session/primary revocation | Reject using existing readers |
| MFA epoch/enrollment/session linkage | Reject; a fresh TOTP cannot repair an old authority |
| Target UUID/path/host/device/inode/schema | Strict mismatch rejection; no allowlist or profile override |
| Dependency mutation or generation/state change | Reject; no refreshed snapshot |
| Stop set/clear or operation block | Reject; set-then-clear changes history and cannot revive authority |

Historical authority rows are not deleted or overwritten to invalidate them.
Fresh predicates and append-only lifecycle/recovery events establish effective
state. A later expiry/change never erases independently verified committed effects.

## 6. Issuance transaction and concurrency

The new producer is not 3a, 4d-2 or the read-only 4e-6 owner. Future integration
must use a separate exact-type registration and restricted authorizer, reusing
shared read validators without manufacturing a registered old context.

Ordering: control BEGIN IMMEDIATE; full schema/history validation; target BEGIN
IMMEDIATE/query-only; genuine runtime/profile/auth/activation/operation/approval/
ACK/dependency/stop/readiness/ceremony checks; verify no claim/authority conflict;
spend confirmation and insert authority/genesis/audit on control only; repeat
all mutable checks and sample deadlines last; manager commits control while
target reservation remains held; only then release/rollback target. No target
DML, target commit, writer lease or completion record in the producer.

A future coordinator may retain one opaque attempt identity in its outer
manager-owned lifetime after confirmed issuance. Database reservation contexts
remain separate phase owners: do not keep a permanent target reservation or
rebind a retired 3a/4e-6 context. Any later writer capability binds the *new*
execution phase's exact connections/epochs plus the same genuine attempt and
authority; it must freshly validate everything again. Returning an inspection
record to a caller, losing the outer lifetime, or restarting cannot recreate
that continuation. Producer-only code must not publish a callable execution API.

Enforce PID, exact thread and connection ownership, reservation epochs, context
lifetime, raw-handle protection, authorizer integrity, manager-only commit and
rollback. Uncertain commit/cleanup publishes no live capability. Return only a
sanitized inspection reference and stop, never automatically repeat issuance.

SQLite control serialization plus unique operation/confirmation keys gives one
winner across workers; no process-local mutex supplies durability. A second
producer inspects the immutable record/history and returns duplicate/ineligible
DATA, not a replacement authority or reconstructed local object.

## 7. Minimal additive storage: exact control requirements

Existing runtime profiles describe enrollment and physical scope, not issuance
or execution. Existing activation records can be referenced immutably by their
existing sequence/digest; do not add another activation counter or authority
columns to those records. Existing audit/confirmation storage represents typed
ceremony DATA, but cannot by itself enforce operation-level execution uniqueness
and lifecycle relationships. Add two control tables only for the producer slice.

All columns below are NOT NULL unless marked nullable. Exact named types:

### `recognition_runtime_execution_authorities`

| Column | Type/constraint |
| --- | --- |
| `authority_id` | TEXT canonical UUID PRIMARY KEY |
| `operation_id` | TEXT canonical UUID UNIQUE |
| `operation_sha256` | TEXT lowercase SHA256 |
| `writer_manifest_sha256` | TEXT lowercase SHA256 UNIQUE |
| `installation_id` | TEXT canonical UUID |
| `target_id` | TEXT canonical UUID |
| `generation` | INTEGER, 1..signed-64 maximum, exact integer |
| `profile_sha256` | TEXT lowercase SHA256 |
| `owner_id` | INTEGER, positive signed-64 |
| `auth_epoch` | INTEGER, positive signed-64 |
| `mfa_epoch` | INTEGER, positive signed-64 |
| `activation_sequence` | INTEGER, positive signed-64 |
| `activation_sha256` | TEXT lowercase SHA256 |
| `approval_id` | TEXT canonical UUID |
| `approval_sha256` | TEXT lowercase SHA256 |
| `confirmation_sha256` | TEXT lowercase SHA256 UNIQUE |
| `issued_at` | INTEGER UTC, 0..MAX_TIME-120 |
| `expires_at` | INTEGER UTC, issued_at < expires_at <= issued_at+120 |
| `body_json` | TEXT bounded canonical authority body |
| `body_sha256` | TEXT lowercase SHA256 UNIQUE |
| `audit_sequence` | INTEGER positive signed-64 UNIQUE |

Local FKs: generation to `recognition_admin_bindings(generation)`;
profile to `recognition_runtime_profiles(profile_sha256)`; activation sequence
to `recognition_local_activation(sequence)`; approval ID to
`recognition_approvals(approval_id)`; confirmation SHA to
`recognition_admin_confirmations(token_hash)`; audit sequence to
`recognition_admin_audit(sequence)` DEFERRABLE INITIALLY DEFERRED. No FK to any
preactivation or legacy claim. No target operation FK crosses databases.

Named index `recognition_runtime_execution_authorities_scope_idx` on
`(installation_id,target_id,generation,profile_sha256,activation_sequence)`.
PK/UNIQUE autoindexes enforce the other lookup/idempotency keys.

### `recognition_runtime_execution_lifecycle`

| Column | Type/constraint |
| --- | --- |
| `authority_id` | TEXT canonical UUID, FK to authorities(authority_id) |
| `sequence` | INTEGER positive signed-64 |
| `state` | TEXT, enumerated below |
| `kind` | TEXT, AUTHORIZE / EXECUTION / RECOVERY |
| `at` | INTEGER UTC, 0..MAX_TIME |
| `previous_sha256` | TEXT nullable; null only at sequence 1, otherwise lowercase SHA256 |
| `entry_sha256` | TEXT nullable lowercase SHA256 |
| `seal_sha256` | TEXT nullable lowercase SHA256 |
| `receipt_sha256` | TEXT nullable lowercase SHA256 |
| `body_json` | TEXT bounded canonical lifecycle object |
| `body_sha256` | TEXT lowercase SHA256 UNIQUE |
| `audit_sequence` | INTEGER positive signed-64 UNIQUE, deferred FK to admin audit(sequence) |

PRIMARY KEY `(authority_id,sequence)`; named index
`recognition_runtime_execution_lifecycle_state_idx` on `(state,authority_id)`.
No mutable current-state table. Exact event body keys: `format`, `authority_id`,
`authority_sha256`, `operation_id`, `operation_sha256`, `sequence`, `state`,
`kind`, `at_utc`, `previous_sha256`, `entry_sha256`, `seal_sha256`,
`receipt_sha256`, `actor_id`, `reason`, `evidence`.
Format is `recognition-runtime-execution-lifecycle-event-v1`. Evidence must be
a validated typed object for the transition, not arbitrary proof-by-dictionary.

The AUTHORIZED genesis evidence format, exact fields and authority/event/audit
bindings are specified by the normative
[4e-11-1 clarification](recognition-runtime-activation-authorized-genesis-evidence-slice-4e-11-1.md).
Only that genesis evidence is defined for the initial 4e-12 implementation;
all later lifecycle evidence types must be rejected until separately specified.

Required triggers/read guards, all named with their table prefix:

- `_immutable_update`, `_immutable_delete`: abort all changes.
- `_immutable_replace`: BEFORE INSERT rejects collisions on **every** PK and
  UNIQUE key, including operation/confirmation/audit keys, even when recursive
  triggers are off. Never rely on DELETE triggers for REPLACE safety.
- Authority `_scope_guard`: exact body/index agreement; current binding/profile/
  install/target/owner and epoch scope; activation row's exact digest and current
  valid activated head; matching v2 approval/history; matching used confirmation
  and typed consumed-ceremony audit; no old runtime claim for operation; no
  previous authority; correct genesis/audit relationship. SQL guards enforce
  local relationships; manager readers enforce target/auth/readiness/time facts.
- Lifecycle `_sequence_guard`: contiguous sequence, exact predecessor, monotone
  time, same immutable authority/operation and legal transitions/kind/evidence.
  Genesis is AUTHORIZED/AUTHORIZE, timestamp equals issue time, null entry/seal/
  receipt/predecessor, exact issuance audit. All later edges require versioned
  execution/recovery readers; producer implementation must reject them.
- Audit/body/read guards: exact canonical fields/types, recomputed digests,
  indexed equality, action/actor/time/subject references, genesis required for
  each authority, FK check. Complete graph validation at transaction end rejects
  authority without genesis or audit; defer local relationships where insertion
  order requires it, never temporarily disable FKs.

Separate historical integrity from current admission. Historical row validation
checks its immutable generation/profile, original activation/ceremony/audit and
legal lifecycle at the recorded times; it must not fail merely because that
session is now revoked, the record expired or the current generation changed.
Insertion guards and current authority readers enforce current scope/expiry.
An old valid history is not current permission, and stale permission must not
make historical evidence unreadable or require rewriting it.

UUID/SHA/decimal/path helpers retain explicit NUL rejection. UTC limits use the
existing runtime profile MAX_TIME. Integer SQL CHECKs use `typeof(...)='integer'`
and bounds; Python rejects bool and float before binding. Physical device/inode
values are never converted to SQLite INTEGER/REAL for comparison. Enforce body
byte limits, not SQLite's NUL-truncated character length. Canonical JSON/digest
verification is application-side as well as SQL shape constraints.

## 8. Lifecycle, effects storage and completion

The runtime states are AUTHORIZED, EXECUTING, COMMITTED, COMPLETED,
FAILED_BEFORE_COMMIT and RECOVERY_REQUIRED. ADMITTED remains a transient
observation, not a redundant durable state. Uncertain commit is an inspection
outcome requiring recovery, not another alleged successful state.

Allowed edges: AUTHORIZED -> EXECUTING / FAILED_BEFORE_COMMIT /
RECOVERY_REQUIRED; EXECUTING -> COMMITTED / FAILED_BEFORE_COMMIT /
RECOVERY_REQUIRED; COMMITTED -> COMPLETED / RECOVERY_REQUIRED;
RECOVERY_REQUIRED -> COMMITTED or FAILED_BEFORE_COMMIT only through explicit
owner recovery with independent evidence. Terminal states do not reopen.

EXECUTING requires a confirmed committed runtime target entry and records its
digest. COMMITTED requires that entry plus an independently observed committed
seal and full actual outcomes; COMPLETED requires complete accounting and a
consistent projection referencing the same entry/seal/receipt. A target commit
can precede its control COMMITTED event. Control history alone proves no effects.
Unknown commit status must block even when history still says AUTHORIZED.

Future readiness must inventory these runtime authority/history records through
a separately reviewed version-aware reader. Any unknown, malformed or unresolved
foreign attempt blocks. A genuine current attempt may exclude only its own
exact validated lifecycle from the pending-work scan, under its manager's
reservations and phase-specific checks; no caller-selected operation exclusion
is permitted. Before effects, regenerate the whole frozen manifest. After
effects, validate historical accounting rather than requiring the pre-write
pending manifest to remain newly eligible. The present readiness implementation
does not provide this new lifecycle reader; the producer/DDL work must not
advertise writer readiness before that later boundary is reviewed.

Future target tables are the separate
`recognition_runtime_execution_entries` (authority UUID PK, unique operation,
authority digest and manifest, canonical exact entry) and
`recognition_runtime_execution_seals` (authority UUID PK/FK to runtime entry,
unique manifest and seal digest, canonical independent receipt/accounting).
They must never FK to legacy claims. **Their exact DDL/codecs belong to a later
effects-storage review, not the first producer migration.** Until then the
producer tables/owner, even if implemented later, cannot authorize a writer.

A future fixed writer commits all atomic family effects and the matching seal
in one target transaction, then verifies both from a fresh post-commit read.
The receipt binds the complete authority scope, entry, operation/manifest/frozen
population, actual rows, exact successful member references and zero active
quarantine/other/unaccounted members. Mutation evidence and application COMPLETED
are distinct. Do not regenerate pending eligibility against one's own effects.
The existing `production_receipts` formats/readers and legacy seals are unchanged.

## 9. Schema/profile transition and installation protocol

The producer-only extension is **control-only**. It changes no target schema or
profile observation and need not advance generation merely to install inert
storage. It nevertheless requires an explicit local migration with expected
generation/binding/schema digests, correct deployment observations, owner and
target verification, NOT_ACTIVATED effective ledger state and operator/reason.
Ordinary runtime access never auto-installs. No migration code is written here.

Its exact schema checker must reject partial/foreign extensions and all malformed
graphs. The old claim migration manifest is historical evidence: a new explicit
manifest-transition audit records exact predecessor schema and new schema,
migration/version, install/generation, actor/reason/time. Version-aware validation
must verify each old manifest against the schema at its original transition,
then prove the current schema through the complete transition chain. Do not edit
old migration audits or merely ignore a current manifest mismatch. Upgrade
schema readers and their expected definitions together while authority remains
disabled. All control DDL/audit is savepoint-safe and rolls back on any failure.

For an additive transition, the historical manifest can be reconstructed by
excluding only the exact later definitions named by validated transition
records from the current schema. Check the remaining exact DDL against that
earlier version and its recorded manifest; then check the full new object set
against the latest manifest. Never exclude an unrecognized object, tolerate an
altered old definition, or treat a version string alone as proof. A partial
transition, extra table/trigger, missing audit or mismatched predecessor rejects.

For eventual target entry/seal installation, two options are deliberately
distinguished:

1. Fresh installation: install the complete approved target schema **before**
   initial deployment binding and 2c enrollment, so both observe its final SHA.
2. Existing installation: requires a separately reviewed explicit maintenance
   transition, not Slice H or initial-enrollment replacement. Stop issuance,
   deactivate through the valid administrative path, resolve all uncertain/live
   execution, verify a coherent backup and exact old identities/schema/history.
   Under deployment-controlled reservations install only the approved additive
   target schema; then append a new generation/binding with its exact new schema,
   null runtime profile and NOT_ACTIVATED marker, revoke authentication and
   invalidate pending approvals without rewriting history. Independently collect
   and approve the new runtime observation using a fresh challenge and initial
   enrollment at the next generation. Rehearsal/activation must be fresh.

The narrow initial maintenance case must have **no 4d-1 claim rows**. The current
4e-7 reserved inventory requires each inspected claim to match the current
profile/generation; retaining old-generation claims after a profile transition
will correctly reject, not silently classify them as safe. Installations with
such history need a separately reviewed historical-scope disposition/retirement
contract before that upgrade. Do not delete claims, bypass the inventory, or
relax its current comparisons. Likewise unresolved new runtime authorities must
be terminally resolved before any future transition; preserving old receipts
requires explicitly versioned historical readers. This restriction does not
affect the control-only inert storage migration, which changes no profile or
generation.

That maintenance protocol spans separate databases and is not atomic. Partial
upgrade, lost commit acknowledgement or a target-schema/binding disagreement
must remain disabled and inspectable; no automatic retry, adoption or code that
relaxes the old schema check. A dedicated maintenance journal/codec and exact
resumable *inspection*, before implementation, require their own review.

Do not append a second NOT_ACTIVATED activation genesis: `_state()` permits only
the first genesis and already reports effective NOT_ACTIVATED when the binding
target/generation no longer matches the last event. Preserve old activation
history; subsequent activation uses a fresh ceremony/event sequence/digest.
Every old operation, ACK, approval and authority remains frozen to its old scope.
New generation means new preparation/operation IDs under normal reviewed flows,
not copied portable operations. Owner transfer and profile rotation/recovery are
not implemented by this design; until separately reviewed, they fail closed.

Answers to the seven schema questions: profiles do not store authority; existing
activation rows provide immutable incarnation references; a new UUID/digest and
unique operation key represent authority; new lifecycle is append-only; stale
scope is rejected nondestructively; entry/seal plus control history distinguishes
effects/uncertainty; separate runtime tables/readers preserve legacy semantics.

## 10. Writer, restart, recovery and idempotency

Authority issuance creates no writer. A future private runtime capability must
be a different exact type/registry, bound to the live execution owner, PID,
thread, connection/reservation, exact authority/operation/target/manifest and
deadline, one-use and nonserializable. It exposes no SQL, cursor, connection,
commit/rollback, mutation, completion or recovery API to callers.

The lowest fixed family writer remains `permanent.finalize()`'s regeneration,
fixed inserts and integrity checks. Its present dispatch depends on legacy
writer acquisition. A later reviewed runtime-specific adapter must preserve
those checks and existing legacy dispatch; never create a fake legacy claim or
legacy EXECUTING row to satisfy `writer_boundary._local_lease()`. No unrestricted
connection/manifest callback is acceptable. No writer code changes in this slice.

| Duplicate/change | Producer outcome |
| --- | --- |
| Same operation + same activation | Inspect existing authority; no second issuance or live handle |
| Same operation + changed activation/profile/approval | Reject; unique operation fence is permanent |
| Stale or expired authority | Inspect-only; no renewal, transfer or replacement |
| Executing | Reject producer; current genuine attempt only, otherwise recovery |
| Completed | Historical evidence only; no writer/idempotent replay |
| Uncertain | Block; require explicit owner inspection/recovery, never adoption |
| Any 4d-1 claim for operation | Permanently ineligible for this producer |

Before issuance commit, failures roll back authority/genesis/confirmation spend.
At/after uncertain commit, publish no authority capability; inspect exact durable
row/genesis/audit/confirmation state. A confirmed issuance followed by publication
failure still cannot mint a replacement local object. Restart never reconstructs
authority from UUID/JSON/digest alone. Future recovery may repair a projection
from a verified committed seal or terminally fence a proven no-effect attempt;
it must exclude delayed original writers under reservations. Absence of a seal
alone proves neither rollback nor safe retry. Recovery does not invoke a writer.

Revoke or change scope before future effect commit: reject and roll back pending
effects. Independently verified historical commit remains evidence after later
scope change; repair projection with current owner/MFA without treating stale
authority as current write permission. Keep the original effect scope intact.

Legacy `recognition_execution_claims`, `recognition_execution_audit`, their
EXECUTING semantics, `production_receipts`, seals, local execution and recovery
remain unchanged. Runtime authority never implements their context/capability
interfaces. No completion is inferred from issuance or 4d-2 consumption.

## 11. Required implementation tests and next boundary

First implementation boundary: **producer storage and canonical codecs only**.
Add the two control tables, explicit local control-only migration/manifest-chain
validation, exact authority/event/ceremony codecs and permanent issuance/writer
denial fences. No producer, TOTP ceremony, runtime owner registration, target
schema, target DML, authority publication, activation, writer or recovery.

Proposed files for that next slice: new
`runtime_execution_authority_contract.py`,
`runtime_execution_authority_schema.py` and their focused tests/documentation;
necessary integration only in `administration_schema.py` and the historical
manifest-validation portion of `runtime_execution_claim_schema.py`. Preserve
the existing 4d-1 body, eligibility, transitions and readers' authority meaning.
An explicit local migration CLI may install inert storage with expected scope,
operator/reason and confirmation, never issue an authority. Review that exact
diff before implementing the separate producer ceremony.

Required tests: exact/partial schema; savepoint rollback at every DDL/audit step;
canonical UUID/SHA/NUL/path/time and large lossless physical values; every
PK/UNIQUE REPLACE collision; immutable UPDATE/DELETE; deferred audit/genesis/FK
relationships; all body/index/activation/profile/approval/confirmation mismatch;
old manifest transition verification; stale/concurrent migration; no target
change; unchanged legacy schema/rows/readers; ordinary v3 gate unchanged.

Subsequent separate reviews/commits: new bounded consent owner and artifacts;
producer issuance and duplicate/uncertain-publication tests; target effect schema
and maintenance/profile transition; execution owner/runtime writer adapter;
independent receipt/seal/accounting; current-owner manual projection/recovery.

Producer tests must use real enrollment/auth/ACK/v2 approval and new consent;
assert rejection of every scope/epoch/activation/dependency/stop change, all old
claims/handoffs, expired/replayed tokens, contradictory worker observations,
clock anomalies, concurrent confirmations/issuance, all commit/cleanup failures,
restart reconstruction, and any target/writer/activation/completion side effect.
No test provider/callback may manufacture production authority. A positive
production activation path and hosted verification remain separate missing
deployment gates; this design does not assert they currently work for v3.

## 12. WAL fixture investigation and validation

The requested consumption file passed: **19 tests, 83 subtests, 678.96 seconds**.
The actual recorded 4e-10 failure was in the acquisition file, not consumption:
`RuntimeExecutionClaimTests.test_crashes_connection_loss_restart_wal`. Its isolated
rerun also passed: **1 test, 70.22 seconds**, without any fixture correction.

Inspection: both crash fixtures invoke the acquisition fixture's `_stop()`;
it kills a still-running child and `communicate(timeout=30)` waits for termination
before the parent reopens the disposable store. Each stage cleans up and creates
a fresh disposable fixture. Database contexts close their handles. No explicit
sidecar deletion, journal reset, checkpoint, production recovery or reopen retry
is involved. No demonstrated fixture cleanup/reopen ordering defect was found.

The previous `PRAGMA synchronous=FULL` disk I/O failure is therefore **not
reproduced in these initial runs; its root cause remains unestablished**. A
passing rerun does not prove it fixed or the WAL baseline consistently clean.
Do not label it a Windows/SQLite bug or silently patch production connection
behavior. No fixture/source changes are justified by the evidence so far.
Environment observed: Python 3.14.6, SQLite 3.50.4. The requested five-file
regression ran once, with results below. No full suite or broader
recognition/deployment family ran.

Final five-file run: **119 passed, 236 subtests passed in 1155.06 seconds**.
Files: activated owner, claim disposition, execution claims, claim consumption
and existing execution tests, exactly as requested. The recorded WAL failure
did not recur in isolation or this regression. No test lifecycle correction was
made, and the earlier intermittent failure's underlying cause remains unknown.
These passing runs verify the existing disposable baseline for this invocation,
not the future authority schema/producer or hosted deployment reliability.

`git diff --check` and new-document whitespace checks pass. All Python source
bytes match the start-of-task fingerprint; only this document was added.
Existing working-tree changes were preserved. Tests use their existing guarded
disposable migrations/legacy writers; no new migration, runtime execution,
hosted/production resource, real deployment key, commit or push was involved.

**A. APPROVE 4e-11 — activation-bound runtime authority producer contract complete.**

This classification is for this proposed design boundary only. It does not
approve production activation or implement an authority producer. The exact
next implementation boundary is the control-only storage/codecs/manifest-aware
local migration in section 11, with issuance and all downstream authority still
disabled. New ceremony/producer and target schema/profile-transition work remain
separate reviewed slices.

PRODUCTION AUTHORIZATION: BLOCKED

PRODUCTION EXECUTION: BLOCKED

PRODUCTION ACTIVATION: BLOCKED
