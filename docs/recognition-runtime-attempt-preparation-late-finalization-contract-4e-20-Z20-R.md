# 4e-20-Z20-R: exact preparation payload and late-finalization write set

## 1. Z20 blocker and scope

This resolves the two inventory questions in
[Z20](recognition-runtime-attempt-preparation-late-finalization-contract-4e-20-Z20.md),
without defining a replacement owner or reusable observation contract.
**Decision B: only schema inventory is currently safe within its approved local
scope; no additional useful payload or reduced finalization is contractually
supported.** This is a completed negative boundary determination, not approval
to implement a split or a claim that the current runtime lifecycle is feasible.

The authority ceiling remains 120 seconds. Z18 observed attempt creation at
84.405s, including 35.328s final validation, exhausting the remaining authority
budget before metadata entry. These are overlapping composite durations, not
exclusive costs or proof that pure record construction is expensive.

## 2. Current attempt mutation/write set

Source: [`runtime_execution_coordinator.py`](../src/review/recognition/runtime_execution_coordinator.py),
especially `_create_attempt`, `_phase`, `_persist_attempt`, `_finish_reserved`,
`_final_attempt`, `_publish_attempt`, and `_State.authorize`.

| Mutation | Storage | Owner | Transaction | Security meaning | Must remain authority-bound? |
| --- | --- | --- | --- | --- | --- |
| INSERT exact attempt row | `recognition_runtime_execution_attempts` | `_persist_attempt` through private fixed insert permit | Original coordinator attempt-phase control BEGIN IMMEDIATE | Immutable authority-linked attempt identity/expiry | YES |
| INSERT genesis history | `recognition_runtime_execution_attempt_history` | Same owner | Same control transaction | Exact attempt digest, sequence 1, ATTEMPT_CREATED, actor/reason/time | YES |
| INSERT creation audit | `recognition_admin_audit` | Same owner via `administration._audit` | Same control transaction | Exact attempt/event digests and audit predecessor | YES |
| Uniqueness and insertion guards | Existing indexes/constraints/triggers; no separate fence row | Installed attempt schema and control manager | Enforced during the three inserts; deferred FKs checked at commit | One attempt per authority, immutable collisions, exact body/history/audit linkage | YES for successful insertion |
| Spend original continuation | `outer.attempt_started=True` in process memory | `_create_attempt`, before opening attempt phase | Not a durable SQLite write | Failure/uncertainty cannot retry the same live continuation | YES; not transferable to preparation |
| Reservation/phase state | Manager memory, registries, actual control/target transactions | `_phase`, `_finish_reserved`, connection owners | Control reservation before target BEGIN IMMEDIATE; target query-only | Original PID/thread/context/connections/epochs; commit ownership | YES for attempt phase; preparation has only its existing issuance reservation |
| Pending graph/result bookkeeping | `attempt_pending`, registered views, `_attempt_results`, outer result | Coordinator only | Pending before commit; result only after confirmed commit and cleanup | Publication is original-owner proof, not a new durable permission | YES |
| Rollback, epoch increments, cleanup, poisoning | Manager state and transaction control | Manager finalizers | Control COMMIT or ROLLBACK; target reservation release afterward | Invalidates borrowed views and failed/uncertain owners | YES; cannot be caller-selected |

The successful path performs exactly three control row mutations and no target
DML/DDL/commit. It does not consume another confirmation, insert an authority,
issue authentication, change binding/profile/generation/activation, create legacy
claims, or mark execution started/completed. Those are not hidden fourth writes.

Failure paths are distinct: shared authentication readers retain existing safe
revocation/denial behavior. `_session` in
[`runtime_scope_validation.py`](../src/review/recognition/runtime_scope_validation.py)
can invoke existing authentication denial reductions. Relevant existing kernels
may UPDATE primary/session revocation and append an `administration_denied` audit.
Those are not preparation or successful attempt writes. `_phase` commits only
an eligible existing safe denial through its manager and otherwise rolls back;
the wrapped kernels do not acquire independent transaction ownership. Denial
invalidates schema observation continuity. No new denial or throttle is proposed.

## 3. Current validation set

Phase entry reads current history, scope/MFA, protected baseline, audit head and
reservation state. `_evaluate` calls shared admission `_collect`, then issuer
`_subject_for_owner`, current continuation/authority and consent validation.
It runs at phase entry, again before insertion, and during finalization.
After insertion `_final_attempt` validates actual rows, complete graph, exact
protected baseline, three-change count, audit suffix and fresh history.
This cadence is existing semantics, not a reusable admission result.

| Validation | Current source | Mutable? | Existing approved reusable evidence? | Candidate preparation? | Must remain fresh? |
| --- | --- | --- | --- | --- | --- |
| Control schema inventory | Z15 / attempt Z7 `_objects`, manifest readers | Installed state can change; observed tuple immutable | YES, exact phase-local inventory continuity only | Existing inventory only; no issuance-to-attempt transfer | Fresh eligibility, physical checks and exact-write proof |
| Migration relationships | `historical_manifest`, `check_manifest_transition`, `_history` | Relationship/current binding predicates | NO under Z15-C/Z16 | NO | YES |
| Runtime profile/G+2 continuity | `_current`, `_history`, shared scope and subject readers | Current selection/generation/owner | No issuance-to-attempt reuse; Z6 discussion alone grants none | NO additional payload | YES |
| Claim graph/disposition | Subject reader, disposition, schema row readers | Current graph/expiry/exclusions | No approved pre-authority transport | NO additional payload | YES |
| Audit/history and actual attempt graph | `_history`, `_check_attempt_graph`, `_final_attempt` | Changed by issuance and attempt inserts | NO complete result reuse | NO | YES, including post-write graph |
| Proposal/ACK/approval | Admission `_collect`, approved proposal/current approval readers | Eligibility/invalidation/current scope | NO | NO | YES |
| Authentication and consent | Session/primary scope readers, consent `_fresh`, `_time` | Expiry/revocation/epochs/confirmation state | NO | NO | YES |
| Independent activation | Subject/activated owner readers | Current incarnation/sequence | NO | NO | YES |
| Emergency stop/operation block | Admission and subject readers | Current state | NO | NO | YES |
| Dependencies | Event/dependency readers and recheck | Current state | NO | NO | YES |
| Whole-population writer preconditions | Admission `_collect` calls read-only `permanent._prepare` and compares manifest | Target population/current validity | NO | NO | YES; this is not family mutation |
| Physical identity/schema/fingerprint | `observe_target`, `target_identity`, current scope and package checks | Independently mutable outside SQLite | NO physical continuity guarantee | NO | YES |
| Protected control state/FKs | Baselines, schema/graph validators and final mutation proof | Changed by expected writes or denial | NO full result reuse | NO | YES |
| Readiness inventory/assessment | `_subject_for_owner` and existing readiness kernels | Current eligibility | NO prepared allow decision | Inspection is permitted, reuse is not | YES |
| Reservation ownership | `_state`, `_continuation_entry`, `_read_parts`, `_finish_reserved` | Context/transaction/epoch/lifetime | NO across phase boundaries | Existing issuance ownership only | YES for actual current phase |
| Actual body/event canonicalization, digest and binding | Attempt validators, authority validators | Actual newly constructed values and durable references | No approved prospective attempt template | NO new payload | Validate actual resulting records |

Sources include
[`runtime_admission_validation._collect`](../src/review/recognition/runtime_admission_validation.py)
and [`runtime_activation_authority_issuance._subject_for_owner`](../src/review/recognition/runtime_activation_authority_issuance.py).
No exclusive timing is inferred for any row from Z18's composite spans.

## 4. Exact preparation-payload analysis

**NO ADDITIONAL PREPARATION PAYLOAD IS CURRENTLY AUTHORIZED.**

The only pre-authority reusable payload is the implemented Z15 `_Facts` in
[`runtime_issuance_schema_inventory.py`](../src/review/recognition/runtime_issuance_schema_inventory.py).
It originates in `_mint(context, artifact)` after fresh issuer evaluation.
The following is an inventory of existing internal fields, not a new transport
format or permission to copy them into a new preparation owner.

| Exact field(s) | Source/producer | Binding and invalidation purpose |
| --- | --- | --- |
| `preparation` | Private opaque `_Preparation` created by `_mint` | Internal object identity; cannot construct/import it |
| `owner`, `context`, `phase` | Genuine registered state: PID, exact thread/ident, outer, original context/phase | Reject ownership, phase or lifetime changes |
| `connections`, `epochs` | Original connections/reservation epochs | Reject transaction/connection/reservation transitions |
| `snapshot_json`, `subject_json` | Canonical current scope/subject from original state | Exact equality only; not reusable current admission |
| `credential_scope` | Existing private credential-scope digest | Exact credential/approval/activation/MFA binding, not credential validity |
| `consent_json` | Canonical validated source artifact | Exact source binding, not fresh consent validity |
| `objects` | Tuple of `(name, sql)` from existing control `sqlite_master` inventory query | Sole reusable schema-content observation |
| `physical` | Actual control and target identities at construction | Comparison baseline; actual physical identity is checked again on use |
| `definition_code` | Existing definition-function/code identity tuple | Reject definition policy changes |
| `control_changes`, `target_changes` | Original connection counters | Continuity accounting; insufficient without exact-write proof |

Every field is in the existing frozen `_Facts` container, lifetime-bound to the
original issuance phase and invalidated by the owner's rejection/discard rules.
Immutable captured values do not imply immutable source state. All fields are
non-executable and have no supported serialization/adoption API; the private
preparation token explicitly rejects serialization. Nothing is exported as SQL,
writer capability, standalone authentication or a resumable handoff.

Reuse is allowed only during Z15's exact five-write issuance finalization,
subject to `_check`, `_write_proof`, fresh physical checks and final discard.
All migration rows/relationships and current allow decisions remain fresh.
It cannot cross issuance commit into a new attempt transaction.

Attempt-local Z7 has a separately minted observation after the attempt's complete
pre-insert evaluation, with authority/manifest/credential bindings and exact
three-insert proof. It is already authority-bound, not pre-authority preparation.
Z6's other proposed observation classes do not authorize moving their production
or consumption earlier. Existing inventory facts therefore yield no new useful
pre-authority attempt payload or measured reduction of finalization.

## 5. Exact late-finalization write-set analysis

The smallest supported successful durable set is the existing three inserts:

| Storage / operation | Owner and transaction | Fresh prerequisites | Fence | Rollback / uncertainty |
| --- | --- | --- | --- | --- |
| `recognition_runtime_execution_attempts` INSERT | Coordinator `_persist_attempt`, original attempt control transaction | Genuine committed authority/continuation; fresh admission/scope/expiry; actual body validation | PK attempt_id; UNIQUE authority_id, body_sha256, audit_sequence; immutable replacement/binding guards | Roll back known uncommitted set; uncertain commit poisons owner and publishes nothing usable |
| `recognition_runtime_execution_attempt_history` INSERT | Same | Exact attempt body/digest, authority owner/reason/time, sequence 1 and null predecessor | PK attempt_id/sequence; UNIQUE body_sha256/audit_sequence; genesis guard | Same transaction outcome as attempt |
| `recognition_admin_audit` INSERT | Same, through `_audit` | Current audit predecessor, exact attempt/event digests and creation action | Existing audit sequencing plus attempt audit guard | Same transaction outcome as attempt/history |

The attempt and history share the next audit sequence. Their audit FKs are
deferred until commit; the audit insertion guard checks the exact linked rows.
Successful finalization checks the three actual changes, exact single audit
suffix, graph and unchanged protected baseline. Constraints and trigger definitions
are validated; no new fence table or reservation record is required.

These three inserts and uniqueness enforcement already remain together atomically
in control SQLite. Reservation transition does **not** mean a fourth durable row:
control commit and memory epoch invalidation belong to the manager; target remains
reserved through that commit. Later target release/connection cleanup and handle
publication are not SQLite-atomic with the inserts. A process crash can leave
durable historical rows without a usable process-local result. Do not claim that
memory transition or cross-database cleanup is part of the atomic row commit.

All three writes remain authority-bound. An attempt body requires exact
`authority_id`, `authority_sha256`, actual `created_at_utc`, and authority
`expires_at_utc`; event/audit require its resulting digest. No field placeholder,
digest rebinding, early ATTEMPT_CREATED or retrospective timestamp is valid.
There is no insertion-only finalizer authorized by the current owner contract.

## 6. Security and TOCTOU proof boundary

| Change or hazard | Required existing response |
| --- | --- |
| Stale preparation or auth/consent change | Fresh authentication/scope/expiry rejects; never refresh an old allow decision |
| Activation change | Fresh exact incarnation must match original authority; no upgrade or rebinding |
| Physical identity change | Reobserve hostname, paths/devices/inodes/schema; reservation does not prove filesystem continuity |
| Emergency stop | Fresh stop check rejects; inventory never overrides it |
| Proposal/ACK/approval change | Fresh exact matching/invalidation readers reject |
| Dependency/population change | Fresh recheck and manifest regeneration reject |
| History/control/claim change | Fresh graph, exclusions and actual mutation/audit proof reject; no cached full result |
| Reservation/connection/epoch change | Original phase eligibility ends; a new phase requires fresh ownership and reads |
| Process/thread/context change | Registry/PID/thread/original-owner checks reject; no token recreation |

This proves the existing separation's safety conditions, not a new optimization.
Moving only record templates would not eliminate any fresh predicate above, and
no approved template contract or measured useful construction cost is present.

## 7. Crash and uncertain-commit behavior

Before authority there is no durable preparation; loss destroys eligibility.
Before successful attempt commit the manager rolls back known uncommitted work.
The original continuation is spent even on failure. On uncertain commit or cleanup,
poison the owner, publish no usable result and inspect durable state read-only.
Neither absent publication nor an in-memory pending row proves rollback. Confirmed
commit still needs successful cleanup and original-owner publication checks.
Do not reconstruct a capability from historical rows, retry automatically, adopt,
or change expiry. No target commit is introduced by attempt finalization.

## 8. Concurrency and adoption

Duplicate prospective data grants no exclusion or authority. Competing finalizers
must serialize through control BEGIN IMMEDIATE and current durable exclusions.
Attempt UNIQUE(authority_id), immutable collision guards, current authority/operation
exclusions and the spent original continuation prevent a second successful live
attempt. Existing coordinator checks also reject incomplete attempt state rather
than adopting it. Database rows alone cannot restore the original continuation.

Issuance/attempt inventory observations do not cross contexts, ceremonies,
processes, threads or transactions. New login, matching identifiers, hashes or
JSON cannot repair those ownership transitions. No new adoption/recovery policy
is defined by this review.

## 9. Decision B

Only the existing phase-local schema inventories are reusable. The exact smallest
authority-bound write set already exists and is atomic for its three durable
inserts; it does not make all final validation preparable or short.
No additional useful payload or reduced finalization is contractually supported.
This negative decision completes the requested payload/write-set determination;
it does not resolve Z20 into an implementable replacement lifecycle.

## 10. Exact next boundary and validation

Do not implement another preparation owner or repeat timing runs on this result.
Any proposal to move a particular expensive predicate must first identify its
exact source, allowable intervening mutations, owner/phase scope, complete
invalidation and actual post-write proof, and explicitly authorize that new
continuity contract. Any change to the phase composition also requires exact
manager/write permissions, commit ordering and crash-prefix rules. This review
does not manufacture either contract. If no such proposal is justified, retain
runtime rejection and return to the architecture decision, not another blind
performance slice or a lifetime increase.

Only this document is added. Validation: `git diff --check`, document whitespace
and local links. No pytest, Z18, T, code, schema, migration, target state,
hosted/production access, commit or push.

PRODUCTION AUTHORIZATION: BLOCKED

PRODUCTION EXECUTION: BLOCKED

PRODUCTION ACTIVATION: BLOCKED

WRITER CAPABILITY: BLOCKED
