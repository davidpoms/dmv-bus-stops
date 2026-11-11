# 4e-20-Z6: final-validation observation continuity contract

## Outcome and limits

**Outcome A: exact control-schema/migration-manifest facts, static runtime-profile
relationships and historical claim-local integrity can have continuity across the
fixed three attempt-creation INSERTs, within the same original reserved attempt
transaction.** Their predicates do not depend on the newly inserted attempt graph.
The complete history/control-validation result cannot have that continuity.

This is a design contract, not an implementation or a cache. The minimum next
implementation boundary is the coordinator attempt-phase **schema/manifest
observation only**, with the ownership and invalidation conditions below. Profile
and historical claim observations are separately bounded possible components of
this contract, not permission to implement all components at once. No observation
is an admission decision, credential, readiness result, writer or continuation.

Z5's 120-second ceiling, earlier credential/ceremony bounds and fail-closed policy
remain unchanged. No timing, implementation, migration or complete-Z validation
is established by this document. Z remains BLOCKED. No pytest, Z or broad suite
is run; only `git diff --check` validates this documentation change.

## Source contracts and exact current boundary

This document preserves:

- [Z5 admission-lifetime decision](recognition-runtime-admission-lifetime-contract-4e-20-Z5.md);
- [Z4 diagnostic](../tests/test_recognition_runtime_coordinator_final_validation_profile.py)
  and its bounded diagnostic artifact `.tmp/recognition-z4-final-profile.json`;
- [ZR](recognition-runtime-validation-efficiency-review-4e-20-ZR.md),
  [Z2](recognition-runtime-readiness-claim-efficiency-review-4e-20-Z2.md) and
  [Z3](recognition-runtime-coordinator-final-validation-efficiency-review-4e-20-Z3.md);
- [original coordinator continuation](recognition-runtime-authority-coordinator-continuation-contract-4e-19-R.md),
  [attempt creation](recognition-runtime-execution-attempt-creation-slice-4e-19-T.md)
  and [reservation-bound shared admission](recognition-runtime-admission-shared-validation.md);
- [4d claim contract](recognition-runtime-execution-claim-contract-4d-1.md),
  [4e authority contract](recognition-runtime-activation-bound-authority-contract-4e-11.md)
  and [authority storage](recognition-runtime-activation-authority-storage-slice-4e-12.md);
- [U enrollment transition](recognition-runtime-enrollment-transition-contract-4e-20-U.md),
  [V storage](recognition-runtime-enrollment-transition-slice-4e-20-V.md) and
  [Y G+2 finalization](recognition-runtime-enrollment-runtime-profile-slice-4e-20-Y.md).

The authoritative implementation is
[`runtime_execution_coordinator.py`](../src/review/recognition/runtime_execution_coordinator.py):
`_phase()`, `_persist_attempt()`, `_check_attempt_graph()`, `_final_attempt()` and
`_finish()`. The exact SQL package/guards are in
[`runtime_execution_attempt_schema.py`](../src/review/recognition/runtime_execution_attempt_schema.py).

The original coordinator issuance and attempt phases acquire **different** control
and target connections/reservations. No observation crosses that boundary. In the
attempt phase, control BEGIN IMMEDIATE precedes target BEGIN IMMEDIATE/query-only.
Entry admission and pre-insert `_evaluate()` run before the fixed inserts. The
original `_finish()` then repeats admission/subject validation, checks the new
attempt graph, protected baseline and audit, samples fresh scope/time and commits
control while target remains held. Target is rolled back/released afterward.

ZR/Z2/Z3 retain only their approved per-call reuse. Their existing public/private
reader interfaces do not gain cross-insert reuse, optional checked flags or caller
supplied proofs through Z6. Any later implementation must use a distinct,
coordinator-owned internal observation boundary. Ordinary 3a/3b, legacy, issuance,
metadata-owner and standalone inspection behavior remain unchanged.

## Exact three INSERTs

`_persist_attempt()` establishes source scope through its fresh `_evaluate()`,
constructs and validates the attempt/genesis, then performs these logical writes:

| Insert | Durable record if committed | Changed predicates | Predicates not changed by this insert |
| --- | --- | --- | --- |
| I1 | `recognition_runtime_execution_attempts`: attempt ID, exact authority ID/digest, creation/expiry, canonical body/digest and future audit position | Attempt population; absence of attempts; one-attempt-per-authority uniqueness; complete graph/FK integrity until its audit exists; authority's relationship to an existing attempt | Schema/migration definitions; existing binding/profile/claim rows and their referenced preexisting audit rows; credentials, activation, stop and target rows |
| I2 | `recognition_runtime_execution_attempt_history`: sequence 1, `ATTEMPT_CREATED`, canonical genesis/digest and the same audit position | Attempt-history population and genesis predicates; complete graph/FK integrity until audit exists | Schema, preexisting histories and records outside the new attempt graph; current binding/profile, claims, credentials, activation, stop and target rows |
| I3 | `recognition_admin_audit`: next sequence, action `runtime_execution_attempt_created`, owner actor, creation time, previous audit digest and exact attempt/event references | Global audit head/population; latest-audit time; current complete audit predicate; resolution of the new deferred audit references | Predecessor audit rows/digests; binding/profile/enrollment histories; claim and authority lifecycle rows; schema; credentials, activation, stop and target rows |

I1's body is `recognition-runtime-live-attempt-v1` with exactly `format`,
`attempt_id`, `authority_id`, `authority_sha256`, `created_at_utc`, `expires_at_utc`.
I2 is `recognition-runtime-attempt-created-event-v1`; its actor/reason/time and
attempt digest are bound by `validate_created()` and the genesis trigger. I3's
subject is exactly `attempt_id`, `attempt_sha256`, `event_sequence=1`,
`event_sha256`, bound by the audit guard and the manager's expected audit body.
The original authority expiry is copied, never renewed.

All three writes are visible immediately on the same control transaction. Until
commit, they are not a published durable outcome for another connection. Their
exact installed triggers perform SELECT/RAISE guards, not secondary DML. Automatic
indexes and repeated SQLite trace events do not constitute extra logical writes.

For **each** of I1/I2/I3:

| Property | Effect |
| --- | --- |
| Reservation identity/epoch | Same manager, connections, transactions and reservation epochs; DML does not itself advance an epoch |
| SQL mode | Only the manager's existing narrow `attempt_writing` permit is enabled; target stays query-only. This is not a target mode transition |
| Generation/installation/owner/profile | No binding, profile or installation/owner write |
| Authentication/MFA | No proof, session, enrollment, epoch, counter, step-up or confirmation write |
| Activation | No activation ledger, incarnation or activation-confirmation write |
| Schema/manifest | No DDL, migration, attachment or schema-policy change |
| History | New attempt/history population for I1/I2; new global audit head for I3; no rewrite of predecessors |
| Claims | No runtime/legacy claim row, lifecycle or claim audit-reference change |
| Authority | No authority body, lifecycle, approval, expiry or revocation update; its **attempt-existence** relationship changes at I1 |

The absence-of-attempt predicate and the complete authority/admission decision
cannot be carried forward just because the authority row remains unchanged.

## Common observation scope and invalidation contract

Every continuity class below has the same owner envelope **E**. E is not a new
transaction primitive or a schema/table. It is a condition on a future opaque,
immutable, nonserializable internal observation belonging to the genuine exact
`CoordinatorAdmissionContext` / `_State` in its original `CoordinatorContext`.
It exposes no SQL, cursor, connection, credentials, callbacks or lifecycle methods.
No public constructor, browser/CLI import, detached digest, provider or forged
object may establish it. Original-owner registration must remain authoritative.

E binds all of:

- original PID and exact Thread object/identifier, unpoisoned active owner and
  live outer continuation;
- exact control **and** target connection objects in `state.connections`;
- the original attempt-phase `state.phase_id` and that phase's manager-owned
  control/target transactions begun by `_phase()`;
- exact control/target reservation identities and both reservation epochs;
- exact installation, target, owner, G+2 generation, binding/profile digests,
  enrolled target schema and expected schema/migration authority;
- original primary/session scope, authentication/MFA epochs, selected operation,
  proposal/ACK and approval references, and activation sequence/digest;
- the already-validated coverage of the particular class, not an assertion that
  all control/history is valid; mutation-accounting position at creation;
- original authority and all applicable authentication/ceremony deadlines.

**Creation point:** only as a byproduct of the complete successful pre-insert
`_evaluate()` in the genuine attempt phase, before I1, after authoritative schema,
history, claim/profile checks and current scope have succeeded. Selecting a row,
holding BEGIN IMMEDIATE or receiving an opaque object is not sufficient evidence.

**Allowed continuity:** only the exact fixed I1 -> I2 -> I3 protocol on this
same owner and reserved transaction. Intermediate facts may remain true, but a
complete post-insert validation result may be accepted only after all three writes
and fresh validation of the changed graph/global invariants. Nothing is published
between inserts. A partially constructed attempt is never an approved outcome.

**Invalidation:** destroy eligibility on any unclassified/extra DML, auth denial
or audit write, INSERT/REPLACE conflict, UPDATE/DELETE, profile/binding/enrollment
change, activation/stop/approval change, code/schema-policy change, DDL/ATTACH,
mode change other than the exact existing attempt INSERT permit, transaction or
savepoint/rollback boundary, connection replacement, reservation/epoch change,
scope change, PID/thread change, exception, poison/denial, expiry/clock anomaly,
commit/cleanup/publication uncertainty or owner/context exit. A subsequent fresh
read does not revive the invalidated observation or spent continuation.

COMMIT/ROLLBACK advances epochs under the existing manager. `_finish()` additionally
invalidates control's reservation epoch before its commit. E is therefore unusable
after commit even if a connection object happens to remain alive. It cannot enter
the later metadata phase, including query-only/write-ready transitions or target
reservation reacquisition. Those require their own original fresh validation.

The implementation must prove the writes were **exactly** the fixed protocol,
not merely notice `total_changes==old+3`. Preserve table/operation authorization,
exact expected rows/bodies and canonical digests, full new attempt/history
cardinality, exactly one expected audit suffix row and protected authentication
baseline equality. Preserve schema/trigger authority and zero target changes.
The existing broad table-level authorizer is not, alone, a proof of exact values.
No new generic mutation journal or trusted caller callback is specified here.
If the exact-write proof cannot be established, stop and reject continuity.

## Observation classes and insert-by-insert continuity

All rows below incorporate **every field of E**, including owner, connection,
transaction, reservation/epochs, generation, activation and authentication scope,
creation point and invalidation events. Each additionally has the listed coverage.

| Class/component | Source observation and exact coverage | I1 | I2 | I3 | Fresh final requirement |
| --- | --- | --- | --- | --- | --- |
| M: manifest/schema | Authoritative exact control sqlite_master definitions, isolation, recognized package set, expected-definition identity and verified installed/predecessor migration-manifest relationships to their preexisting audit/binding rows | Can cross | Can cross | Can cross | Fresh E/write-proof checks; all changed row/FK/head predicates remain outside M. Any schema/migration/code/attachment change invalidates M |
| H: complete history | `runtime_validation._history()` including `check_control()`, current complete graph, `a._audit_head()` and latest-audit time | Cannot cross as a complete result | Cannot cross | Cannot cross | Fresh new attempt/history/audit, current audit head, complete-chain integrity and time relationship are mandatory |
| C: historical claim-local integrity | All preexisting runtime claim bodies/indexed columns, fixed 300-second lifetime, own history/transitions and linked existing audit rows, immutable binding/profile and historical authentication relationships; associated already-verified migration facts | Can cross for this bounded predicate only | Same | Same | Fresh global FK check and current claim disposition/time, current auth/activation/stop and operation exclusion checks. No execution/consumption eligibility follows from C |
| P: durable G+2 profile relationships | Exact binding/challenge/profile/review/enrollment audit relationships, immutable runtime auth-link relationships, and completed U/V/Y transition records supporting the current G+2 profile and no pending enrollment plan | Can cross | Can cross | Can cross | Current auth, owner/epochs, actual physical identity, path resolution/schema, activation and deadlines remain fresh. Any enrollment/generation/profile/link/auth change invalidates P |
| V: complete control validation | `administration_schema.check_control()` including schema, profile, claim, authority, attempt and transition row checks and their global FK predicates | Cannot cross as a complete result | Cannot cross | Cannot cross | Re-establish changed/current predicates; only independently covered M/C/P subfacts may have continuity |

This does not authorize treating an old H or V as true after three writes. It
allows a future explicitly decomposed validator to combine a still-valid covered
subpredicate with fresh predicates; no predicate from the original validator may
disappear. The initial implementation boundary is M, not wholesale H/V substitution.

### History: no invented delta mechanism

The new history is precisely I2's attempt genesis plus I3's linked admin audit;
I1 changes the attempt population they certify. Predecessor binding/enrollment,
claim and authority lifecycle histories are unchanged, but the statement
"the current complete graph/audit chain is valid and has this head" is changed.
An earlier prefix cannot answer that current-head predicate.

`_check_attempt_graph()` already reads the exact pending row/genesis/audit and
checks authority binding/expiry. `_final_attempt()` already compares protected
baseline, total changes and the exact one-row audit suffix. These support proving
the fixed write set; they do **not** establish a general reusable prefix-plus-delta
history validator. Z6 introduces no compact history delta, altered `_audit_head()`
or shortcut for canonical sequence/digest/previous-link/time validation. Keep a
fresh complete audit read. The new head's timestamp must be compared with fresh
time, not the predecessor head's time.

Migration-audit selections within M remain unchanged because I3's exact action
is attempt creation, not any migration/enrollment action; old referenced sequences
cannot equal the new suffix position. This narrower fact does not certify the
new event. A wrong action, extra row, collision, malformed body or mismatch with
the expected pending audit fails the write proof and invalidates continuity.

### Claims: historical integrity is not current authority

The claim validator reads its own tables, migration audits, binding/profile/auth
references and claim-specific histories/audits. I1/I2/I3 change none of those
records. They do not update operation/authority references, immutable claim
expiry, lifecycle/revocation, generation/profile, activation or existing audit
linkage. New attempt authority binding must still be checked separately.

The global `PRAGMA foreign_key_check` at the end of claim validation is different:
I1/I2 introduce deferred references to the not-yet-inserted audit. A prior global
FK result is invalid immediately, even when claim-local integrity remains true.
After I3, validate global foreign keys afresh; successful insertion alone is not
a substitute. This distinction also applies to profile/authority/attempt/transition
validators that finish with global FK checks.

Current LIVE_ISSUED/EXPIRED disposition, authentication revocation/expiry, current
authority/activation permission, selected-operation exclusions and emergency stop
remain fresh decisions. C does not reinterpret a 4d claim as activated 4e authority,
replace `_inspect_reserved()`'s fresh clock or authorize a new claim/attempt.

### Schema and runtime profile: durable facts versus actual observations

M includes exact definitions and migration relationships already independently
verified by existing readers. DML and the installed SELECT/RAISE-only guards
cannot change those facts. The existing ZR/Z2/Z3 digest algorithm, exclusions,
schema identity and fingerprint algorithm remain unchanged. M has no cross-request,
TTL, process-wide or standalone-reader scope; it is a new separate contract for
the exact coordinator transaction, not a broader interpretation of those helpers.

The U/V/Y G+2 records cannot change during this fixed write protocol: no profile,
binding, challenge, auth link, transition plan/history or referenced enrollment
audit is written. P can preserve their **durable relationships**, not a prior
observation of the worker. Canonical path resolution can depend on the filesystem,
so it is not a timeless P assertion: actual resolved paths, hostname, device/inode,
target fingerprint/schema, owner access and epochs must still be checked using
the original strict observation semantics. `target_identity()` remains unchanged.

### Control validation: no same-transaction shortcut

`check_control()` observes the exact object set/SQL and isolated database, then
validates profile/auth-link relationships, runtime claims, authorities/lifecycles,
attempts/genesis, enrollment transitions and global foreign keys. Authority
validation also reads the complete audit head. I1/I2/I3 leave some inputs stable
and change others within the very same transaction. Its single complete result
therefore cannot be carried forward unchanged.

Authority's original body/lifecycle being unchanged does not establish unchanged
attempt eligibility. Fresh `_check_attempt_graph()`, exact authority linkage,
approval/proposal/ACK binding and `_final_attempt()` remain required. Z6 grants
no separate reusable authority-permission observation.

## Fresh security decisions that continuity must not replace

Before the original manager's final control commit, continue to establish:

- current primary/session validity, expiry, owner/authentication/MFA scope and all
  original consent/deadline constraints, sampled against fresh paired-clock time;
- current activation incarnation and independently verified activation ceremony;
- current emergency stop and operation blocks;
- actual hostname/resolved paths/device/inode, current target schema/fingerprint,
  owner access and authentication epoch using existing kernels;
- exact current proposal/ACK/effective approval, dependency state, writer
  preconditions and protected readiness assessment;
- exact live owner/connection/transaction/reservation epochs, query-only target,
  unchanged target data and exact post-insert attempt/audit/control graph;
- unchanged original authority deadline, with equality/rollback/anomaly rejection.

These remain fresh even if a nested durable-subpredicate uses M/C/P. Authentication
or activation changes cannot be papered over by a still-equal schema digest. No
later deadline, renewed login, preserved field values or new process can restore E.

## Minimum implementation boundary and acceptance conditions

Next, if this contract is approved, implement only a **coordinator attempt-phase
schema/manifest observation**: minted from authoritative pre-insert validation,
private to the exact owner/reserved transaction, usable only for M's exact facts,
and invalidated by the rules above. Do not add global cache state, schema, a new
transaction primitive, a public observation API or broad checked flags. Unknown
adapters/callers retain full existing readers. No effect on 3a transaction ownership,
3b authentication, legacy execution or the metadata owner is implied.

Before approval of that implementation, focused tests must establish exact
predicate equivalence; no omitted validation; unchanged final decision; exact
I1/I2/I3 positive continuity and intermediate FK caveats; rejection/invalidation
for extra/altered writes, auth denial, wrong row/digest/action and trigger/schema
change; epoch/connection/transaction/mode/thread/process/scope mismatch; rollback,
commit uncertainty and cleanup; nonconstruction/nonserialization and lifetime
expiry; fresh physical/auth/activation/stop/approval/dependency checks; fresh new
attempt/audit/FK checks; and no target DML, writer or execution authority. Material
read-count/cost reduction must be measured before claiming a performance result.
If the implementation cannot prove the exact write set or preserve every predicate,
stop rather than weakening validation or silently broadening coverage.

The opportunity is material structurally: Z4 attributed 17.597 exclusive seconds
to repeated manifest/schema work during an incomplete final stage. M permits
avoiding reconstruction of the same verified schema/migration facts after DML
that cannot change them. This does not promise elimination of the whole category,
an exact speedup or that the complete Z path will fit within 120 seconds. Current
head/graph/FK work and all live checks remain. H/V freshness is not traded away
to make a benchmark pass.

**Outcome A is confined to these dependency-proven static observations.** No
history delta, authority reinterpretation or authentication/activation crossing is
needed for the initial M boundary. Consequently the stop conditions do not require
inventing a history-continuity contract. Outcome B's claim that no component can
cross is not supported: exact schema facts do survive the three fixed DML inserts.

The 120-second ceiling remains in force. Any future lifetime change still requires
Z5's separate approval; this contract neither recommends nor authorizes one. Z
remains BLOCKED and T has not been entered. No hosted/production resources, tests,
code changes, commit or push.

PRODUCTION AUTHORIZATION: BLOCKED

PRODUCTION EXECUTION: BLOCKED

PRODUCTION ACTIVATION: BLOCKED
