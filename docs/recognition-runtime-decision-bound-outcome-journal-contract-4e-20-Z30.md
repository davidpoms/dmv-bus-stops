# 4e-20-Z30: decision-bound outcome journal contract

## 1. Z29 blocker and decision

[Z29](recognition-runtime-execution-decision-identity-contract-4e-20-Z29.md)
found that existing IDs can name intent, but existing runtime records cannot
couple that intent to committed business effects and the corresponding control
outcome. **Existing-storage assessment B: one new durable journal structure is
required.** This document defines its minimum logical semantics, not SQL, codecs,
migration, executable producer, writer authority or a new execution architecture.

The journal is **one logical primitive with two mandatory durable placements**:
control-side decision/fence history and a target-local commit witness. It cannot
be implemented as a control-only table or a target marker written after business
commit. Physical table/codec design is reserved for the exact inert schema review.
No current table gains new state meanings or mutation permissions here.

The 120-second ceiling and all current authority/owner checks remain unchanged.
Outcome recording never extends execution permission. This contract does not
establish lifecycle performance, complete the replacement executor contract,
or authorize T, a writer or a live journal migration.

## 2. Canonical identity

No new random identity is needed. The canonical decision key is the existing
`authority_id`, with mandatory immutable `authority_sha256 = digest(authority body)`.
Together these are Z29's execution-decision identity D. The journal's identity
is D; the journal is not another authority or independent grant. Sequence/event
digests identify history facts, not new decisions.

An existing genuine producer creates the authority ID/body only after its exact
consent CAS and fresh admission. A journal initializer may bind D only to a
confirmed durable canonical authority and its complete validated genesis/audit
scope. It cannot accept a caller-supplied replacement body or import a historical
authority as a new live execution owner. No preparation creates D or an executable
journal entry. Old-runtime decisions are not automatically enrolled in this new
journal; future version/eligibility rules must explicitly reject unsupported
lineage rather than retrofit it.

Same ID with a different digest is a hard conflict. Same D is historical lookup,
not permission to repeat execution or recreate an original local capability.

## 3. Minimum immutable bindings and conceptual fields

The exact physical representation must be reviewed next; these are minimum
conceptual contents, not a new JSON field set or table definition.

| Content | Source / minimum purpose |
| --- | --- |
| D: authority ID and exact body digest | Existing canonical authority; primary decision correlation |
| Installation ID, target ID, operation ID and operation digest | Authority's exact current scope and operation reference; indexed exclusion and subject integrity |
| Writer-manifest digest | Authority operation reference; reject the same business intent under another operation/decision |
| Scope anchor | Exact authority body/digest and its enrolled binding/profile/generation, owner/auth/MFA epochs, activation incarnation, approval/ACK/proposal and physical target/control snapshot; resolve and validate complete source, not digest equality alone |
| Control event sequence, predecessor digest, event digest, factual kind, actor/time and evidence reference | Append-only authoritative history and exact audit linkage; classify source/provenance of facts |
| Pending-event digest reference | Target witness binds the exact once-only control start declaration, not only an operation UUID |
| Target outcome evidence and digest | D, scope anchor, exact pending event, whole-population manifest/effect accounting and verifiable complete actual family-record evidence; persistence is atomic with those effects |
| Terminal control outcome's target-witness or positive-failure evidence reference | Immutable correlation to the fact being recorded, never an executable credential |

No duplicate full profile/approval/credential copies are needed when their exact
canonical authoritative sources remain available and validated. Indexed projections
must agree with those sources. Never persist plaintext nonce, token, TOTP, keys,
connection/cursor, PID or thread as journal authentication.

**Reservation binding remains live, not durable permission.** The executor must
prove the exact original registered owner, actual connections/transactions, modes
and reservation epochs on each transition. A pending event and target witness bind
the exact intended decision and observed target scope, but do not make an old
epoch adoptable. Reacquisition requires a new current reservation check. There
is no portable reservation token or invented filesystem continuity witness.

Journal events are immutable individually. New factual events append; they never
UPDATE/DELETE/REPLACE earlier facts or rewrite original authority bodies. Body
and event digests follow existing canonical serialization principles; exact size,
key sets, SQL constraints and trigger definitions belong to the inert codec review.

## 4. Minimum outcome state machine

These are new conceptual journal terms, not new states in existing AUTHORIZED
or ATTEMPT_CREATED tables. Two histories are related, not transactionally fused.

| Proposed state/fact | Placement and meaning | Execution eligibility |
| --- | --- | --- |
| DECISION_CREATED | Control: D and permanent operation/manifest exclusion registered against valid durable authority | None from this fact |
| TARGET_PENDING | Control: one original live owner has spent the decision's sole execution-start opportunity | Never authorizes adoption or another start |
| TARGET_UNCERTAIN | Control: durable factual report of commit/connection/cleanup uncertainty, or conservative reader classification when pending has no confirmed outcome | Blocked; never a retry grant |
| TARGET_COMMITTED | Target: validated witness, committed in the exact same target transaction as all business effects | Historical target fact only |
| TARGET_FAILED | Control: positive evidence of known no-target-commit outcome from the original manager, not an inference from absent rows | Terminal no-retry outcome |
| COMPLETED | Control: confirmed record correlating D/pending and validated committed target witness/effects | Terminal historical success; no further execution |

`CONTROL_COMMITTED` is not an additional state: every durable control event is
locally committed; successful correlated control recording is COMPLETED. A separate
control TARGET_COMMITTED event is unnecessary: the target witness is the source
of that fact. Do not add speculative business lifecycle states merely to mirror
both databases. TARGET_UNCERTAIN records preserve prior sequence and can be resolved
only by positive evidence; existing uncertain events are never erased.

| Transition | Owner / prerequisite and predecessor | Atomicity | Retry and terminality |
| --- | --- | --- | --- |
| Absent to DECISION_CREATED | Original eligible decision owner; validated durable D, exact scope, no conflicting operation/manifest/journal | Control registration, permanent exclusion and audit linkage resolve together | At most one; duplicate creation is inspection/conflict, not another grant |
| DECISION_CREATED to TARGET_PENDING | Genuine original live executor only, current authority/auth/consent and every required fresh check | One append-only start event and audit under control reservation; sequence/CAS predicate enforces single start | Irreversibly spent for execution; never a second pending start |
| TARGET_PENDING to TARGET_COMMITTED witness | Same original executor, exact validated pending fact and current required prewrite/precommit authority/scope/reservations | Witness and complete family effects in one target transaction | One target witness per decision/operation/manifest; irreversible on confirmed commit |
| Pending to TARGET_FAILED | Original manager only with positive confirmed no-commit/rollback evidence and current permission to record that fact; if recording cannot be confirmed, remain unresolved | Control factual failure append and audit, conditional on expected head and no contradictory proof | Terminal; no automatic or manual execution retry authorized here |
| Pending to TARGET_UNCERTAIN | Original manager reporting error, or explicitly authorized authenticated factual resolver; never an execution owner restored from rows | Control append if available; otherwise durable pending is conservatively unresolved | Non-terminal for factual resolution, permanently no-retry for execution |
| Pending/uncertain to COMPLETED | Original manager or explicitly authorized authenticated outcome-only resolver; positively verified target witness and complete actual records for exact D | Conditional control outcome append and audit resolve together, referencing target proof | Terminal success; exact duplicate resolution returns history only |
| Uncertain to TARGET_FAILED | Only original manager's positive already-established no-commit evidence, not an inspector's absent-witness inference | Conditional factual control append and audit | Terminal; if evidence missing, UNKNOWN indefinitely |

Outcome-only resolver permission is a **new narrowly scoped journal-recording
role**, not current code or business execution authority. Its permitted actions
are inspecting and appending verified facts, never writer admission, reauthorization,
retirement, fence release or target mutation. Exact authenticated owner-only scope,
records/codecs and authorizer must be reviewed with inert schema/producer boundaries
before implementation. No existing generic admin/audit function gains that role.

DECISION_CREATED may remain permanently unused. Closing or expiring its grant
does not delete its exclusion. A cancellation state is not needed for safety and
is not defined. Terminal facts cannot contradict each other; conflict poisons
inspection and blocks success instead of choosing whichever row is newer.

## 5. Target/control coupling protocol

The following is the required journal protocol for a future separately approved
executor. Journal state itself cannot authorize any of these actions.

1. Confirm control DECISION_CREATED and then sole TARGET_PENDING with exact D,
   expected sequence/predecessor and operation/manifest exclusions. Target cannot
   begin business mutation without positively reading this confirmed pending fact.
   Both control commits retain their actual target reservations until resolution
   as required by the owning managers. No caller controls commit.
2. If a phase releases reservations, reacquire **control before target**, validate
   all current state and original owner/deadlines again. Never hold target and
   wait to acquire control in an inverted lock order. No previous allow decision
   or schema inventory crosses phase boundaries.
3. The original executor takes the final control reservation, then exact target
   writer reservation. It verifies D/pending and all required current authority,
   identity, activation, approval/ACK, stop, dependency, history/claim/control,
   migration/profile, readiness, expiry and reservation predicates. No other
   process can adopt pending. Any deadline/identity/scope failure denies execution.
4. Under a separately approved exact-action writer, mutate the entire permitted
   family population and construct the target witness **inside that same target
   transaction**, after verifying the exact effects/accounting. Validate the exact
   whole write set and all required fresh precommit conditions, then commit target
   while the control reservation remains held. Failure rolls back all known
   uncommitted effects and witness together. There is no witness-only successful
   transaction or later post-commit witness INSERT.
5. Confirm target commit and reacquire/inspect as required without losing required
   control fencing. Validate witness, D/pending, enrolled target identity/lineage
   and complete effects. The witness proves commit because it is observed durable
   outside the mutation transaction, not because its precommit timestamp says so.
6. Append control COMPLETED only on that positive proof and expected predecessor,
   committing its audit linkage. Publish usable success only after confirmed target
   outcome, confirmed control completion and required cleanup/current result checks.
   If grant/auth/cleanup/publication fails, publish no usable execution result;
   historical factual resolution can still be reported without renewing authority.

Target commit before **control completion** is allowed and has a deliberate
incomplete-recording window. Target commit before its **target witness** is
forbidden: they must share one local transaction. A witness inserted but uncommitted
is not target success. Control decision/pending commit before target commit is
allowed but says only reserved/spent, not completed. Control COMPLETED before
validated durable target proof is forbidden.

Every crash prefix retains permanent exclusion and permits only factual diagnosis.
There is no cross-database atomicity. Target and control are not attached into a
single assumed transaction. A transient target-committed/control-pending mismatch
is explicitly unresolved recording, never safe retry or falsely completed success.

The witness's recorded time is a validation/event time, not an asserted exact
wall-clock instant of SQLite commit. All existing authority deadlines still apply
at required use/precommit/result checks. This journal does not make an in-flight
commit interruptible at a clock tick or move the authority's issue-time origin.

## 6. Durable duplicate fence

Required immutable identities, enforced in both journal placements as appropriate:

- One D per authority ID, with exactly one body digest; conflicting digest rejects.
- At most one decision exclusion per authoritative installation/target/operation.
- At most one corresponding manifest exclusion per installation/target, even if
  a different operation/decision ID is supplied.
- One pending-start event per D and one target committed witness per D, logical
  operation and manifest; append-only unique event sequence and predecessor.
- One terminal factual outcome per D; a COMPLETED outcome must reference the exact
  target witness and pending event, not merely an operation digest.

Generation/profile/session/request ID changes do not create a fresh duplicate
domain. Scope changes fail closed and never rebind old D. Existing authority,
attempt, entry and legacy conflicts remain blocking rather than being converted.

| Request | Required behavior |
| --- | --- |
| Same process retry after start | Reject: pending spent the execution start; no loop/reuse |
| Process restart or another ceremony | May inspect history with current authentication; cannot recover the original live permit or start D |
| Competing process for same D | Control serialized expected-head/unique start rejects second start; target unique witness is an independent final duplicate fence |
| Duplicate authority or operation under new D | Reject conflicting authority/operation/manifest identity; do not allocate a new journal winner |
| Duplicate target request/entry | Reject business DML on existing witness or conflicting original metadata; exact existing outcome may be returned as historical inspection only |
| Retry after success | Reject execution; terminal history remains authoritative |
| Retry after confirmed failure | Reject execution; failure is not permission to release or reuse the fence |
| Retry after uncertain target outcome | Reject; UNKNOWN never permits a fresh request that evades the old logical exclusion |

This aims at at-most-one committed business effect under the trusted-code/database
model, not guaranteed delivery or exactly-once success publication. Ambiguity is
explicit and blocking, not resolved probabilistically. Arbitrary host/database
tampering is not solved by UUIDs, hashes or journal rows.

## 7. TARGET_UNCERTAIN and factual resolution

1. A confirmed TARGET_PENDING plus no positively confirmed terminal outcome is
   durably unresolved. A caught commit/connection/cleanup error may add an immutable
   TARGET_UNCERTAIN event with sanitized classification and original references.
   No event claims the error proves target rollback or success. A crash need not
   leave an explicit uncertainty event: pending without terminal proof is sufficient
   to forbid replay. A stale reader reports the durable prefix, not a definitive
   claim that a still-running executor has died.
2. A currently authenticated owner with the separately reviewed **outcome-only**
   resolver permission may inspect. It takes control reservation before target
   inspection/reservation, validates exact enrolled identities/schema/restore
   lineage and D/source graph, and observes a stable committed target snapshot.
   It does not receive writer capability or the original grant.
3. Authoritative positive target evidence is the complete validated durable target
   witness, exact D/pending binding and full corresponding actual family-record
   accounting. Metadata entries, request logs, exceptions, process memory, expired
   grants and absence of control completion are not substitute proofs.
4. Exact positive proof may resolve pending/uncertain to factual COMPLETED through
   the conditional control append. Expired or changed current activation/auth state
   does not rewrite historical commit; it bars new execution. Resolver authentication
   must be current and cannot be borrowed from the old executor. Historical scope
   and validated original grant/evidence must still be exact.
5. Only positive original-manager no-commit evidence can produce TARGET_FAILED.
   Absence of a witness alone never resolves an uncertain decision to failure,
   even if one snapshot is readable. If such positive evidence cannot be validated
   and durably recorded, remain indeterminate indefinitely.
6. If either store is unavailable, identity/restore lineage is uncertain, actual
   effects mismatch, proofs conflict, reservation fails or inspection is itself
   uncertain, record/return UNKNOWN without target writes or usable success.
   A failed control resolution commit is reread by identity; never blindly appended
   or executed again.
7. No new D for the same logical operation/manifest is permitted while unresolved,
   after completion, or after failure. No original execution retry is authorized.
   A genuinely new business operation must independently satisfy all existing
   conflicts and cannot be used as a renamed retry. Retirement/correction requires
   a separate explicit policy, not a resolver privilege defined here.

While unresolved, expose only pending/uncertain facts with `retry_authorized=False`
and no executable success/capability. An outcome resolver records history, not
authorization. Exact repeated positive resolution returns the existing history;
conflicting resolution rejects.

## 8. Crash matrix

The matrix concerns confirmed durable facts, never in-memory row construction.
“UNKNOWN” is a deterministic fail-closed classification, not a guessed outcome.

| Crash point | Journal state | Target state | Control state | Allowed recovery |
| --- | --- | --- | --- | --- |
| Before target attempt | DECISION_CREATED or confirmed TARGET_PENDING, depending on prefix | No known committed effects from this attempt; reader cannot infer solely from process exit | Decision excluded, start unused or spent as actually recorded | Inspect; no restored owner/retry |
| During target operation | Pending; explicit uncertainty may be absent | Known uncommitted transaction rolls back through SQLite; external observer still validates actual durable proof | Pending/uncertain, never completed without proof | Positive witness resolution only; missing witness remains UNKNOWN |
| After target commit | Target witness durable with exact effects | Whole committed population or conflict requiring UNKNOWN | Pending/uncertain until correlated recording | Validate witness/effects, append factual completion; no repeat mutation |
| Before journal target outcome | If target witness not yet written, target transaction cannot yet validly commit | Effects/witness uncommitted, or no target attempt | Pending | No guess from absent witness; exact durable inspection |
| After journal target outcome | Witness may be uncommitted or durable; distinguish by validated independent committed read | Same target transaction contains effects and witness | Pending or completed only if positive proof already recorded | Read actual committed facts; do not trust inserted-but-uncommitted memory |
| Before control commit | Initial decision/start or final completion append is unconfirmed | Before start: no authorized mutation; before completion: target may already be committed | Last confirmed control prefix only | Inspect by D; a failed completion append cannot undo target commit |
| After control commit | Decision/start commits mean no success; COMPLETED commit means correlated target proof recorded | None/pending for early prefix; confirmed witness/effects required for completion | Exact committed sequence | Historical inspection or positive resolution; no adoption |
| Before result publication | Confirmed history may exist despite missing response; cleanup can fail | May be committed | May be completed or unresolved recording | Publish no usable result on uncertainty; inspect history, never re-execute |

No automatic recovery infers failure from absent output. Duplicate fencing stays
effective in every row, including a decision that is never executed or resolved.

## 9. Corresponding control outcome

The new journal's **control placement** carries D, immutable binding/exclusions,
pending/uncertainty/failure/completion events and exact audit linkage. COMPLETED
references the target witness digest and pending-event digest, and its source
authority/operation scope must be resolvable and canonical. Missing source history
or target proof prevents completion, never authorizes audit reconstruction.

Existing runtime attempt/history cannot represent this: they permit only inert
ATTEMPT_CREATED and exact old three-insert proof. Existing authority lifecycle
permits only AUTHORIZED genesis. Existing general audits alone do not enforce a
new outcome state machine or target-atomic proof. Legacy completion/claim/seal and
production receipt readers cannot be imported as replacement authority/evidence.

The extra relationship is therefore exactly **control D/start/outcome -> target
D/start/committed-effect witness**, with global operation/manifest exclusion and
immutable references in both placements. No other durable bridge or grant is
required by the journal. Existing AUTHORIZED evidence remains its exact original
three fields; no later-lifecycle codec is added here.

## 10. Authorization separation

```text
journal existence != authorization
journal state != writer capability
journal state != execution capability
journal recovery != reauthorization
```

All ordinary execution gates stay independent: fresh genuine owner auth/MFA,
exact operation/runtime scope, independent current activation, effective approval/
proposal/ACK, stop/block, dependencies/current whole-population preconditions,
actual strict physical identity/schema, current history/claim/control/migration
integrity, readiness, genuine reservations and original authority deadlines.
No row lookup, digest, pending state, witness or resolver result bypasses any gate.
Journal failures can deny execution; journal success cannot manufacture permission.

This fact-recording contract does not grant the current writer boundary a new
accepted type, widen any owner authorizer, permit target mutation, change legacy
claims or let a fresh ceremony adopt old executable state. A future inert schema
may contain synthetic records in constraint tests without conferring authority.

## 11. Concurrency and exact fencing invariant

Two owners for D serialize control updates using expected sequence/predecessor
and unique pending-start identity. Only the genuine original execution owner may
start; an outcome-only resolver cannot. At most one target witness may commit for
the logical operation/manifest, regardless of process/request/decision ID.

Different nonconflicting decisions on one target still serialize target writers;
each freshly validates dependencies/claim/history/stop/identity after waiting.
Conflicting operation/manifest or family constraints reject, not skip validation.
Preserve BUSY/LOCKED semantics; no arbitrary retries or stolen reservation claims.

Stale readers observe a prefix only. They cannot grant execution, assert final
failure from absence or overwrite a later outcome. Concurrent resolvers hold the
control reservation, validate the same target proof, and append conditionally to
the expected head. One factual completion wins; an exact duplicate is inspection;
conflicting evidence is a hard integrity stop. Concurrent recovery never executes
business DML. No Python mutex substitutes for these durable fences.

## 12. Retention and terminality

COMPLETED and TARGET_FAILED are terminal control outcomes. TARGET_COMMITTED is
an immutable terminal target effect fact even while control recording is pending.
Uncertain is non-terminal only for factual resolution; it never regains execution
eligibility. All earlier events and exclusion identities are permanently retained.

No UPDATE/DELETE/REPLACE, purge-on-expiry, TTL reuse, partial history compaction or
deletion of terminal records is permitted. The logical operation/manifest fence
must remain effective for as long as any copy/request can reference the operation.
This contract selects indefinite operational retention, not deletion after a backup
retention period. Backup retention and live duplicate-fence retention are different.

Restores/copies are trusted administrative events that must preserve verified
decision/witness history or block all affected execution until existing installation/
generation/restore controls resolve lineage. Journal absence on a restored or
different target is not proof of no earlier commit. This journal supplies no
anti-rollback oracle or new restore/adoption policy; uncertain lineage fails closed.
Administrative destruction of both histories is outside the trusted-code/database
integrity model and must not be claimed prevented by a hash or unique constraint.

## 13. Existing-storage assessment B

**One new durable journal structure is required**, with the two mandatory placements
and minimum contents/invariants specified above. Existing storage is not sufficient:

| Current storage | Why it cannot be reused unchanged |
| --- | --- |
| Runtime authority/lifecycle | Exact AUTHORIZED-only schema/codec/graph; no correlated target outcome states |
| Runtime attempt/history | ATTEMPT_CREATED-only, original continuation and exact three-write producer proof |
| Runtime target entry | Immutable metadata reservation state, not effects committed atomically with a journal witness |
| Private operation/family records | Business-manifest evidence, not replacement D/start/control outcome provenance |
| Legacy seals/claims/receipts | Different exact authority and execution contract; fabricating legacy scope is prohibited |
| General control audit | Audit facts alone do not enforce the new cross-store decision/outcome/fence relationship |

Sources inspected:
[`runtime_activation_authority_schema.py`](../src/review/recognition/runtime_activation_authority_schema.py),
[`runtime_execution_attempt_schema.py`](../src/review/recognition/runtime_execution_attempt_schema.py),
[`runtime_target_entry_storage.py`](../src/review/recognition/runtime_target_entry_storage.py),
[`permanent.py`](../src/review/recognition/permanent.py).

This is not assessment A and not a proof that safe coupling is impossible (C).
The new logical journal can specify conservative crash-safe semantics by allowing
UNKNOWN indefinitely and rejecting all retries. No claim of automatic liveness,
existing target support or executable implementation is made.

## 14. Exact next boundary and validation

The next boundary is **review of the exact inert journal schema/codec**, including
both durable placements, canonical event/witness content, exact constraints,
immutability, expected-head/uniqueness guards, source relationships and malformed/
partial/conflicting graph rejection. It is not a live migration or a producer,
resolver, executor, writer or target-DML implementation. No new authority can be
created from that review. Later integration must separately prove the actual
business-effects/witness atomicity and exact owner permissions under this contract.

Only this document is created. Validate `git diff --check` and document whitespace/
local links. No pytest, Z18, T, broad suite, code/schema/migration, journal creation,
authority or target state, target DML/DDL, writer/execution capability, production/
hosted access, commit or push. No lifetime change or performance investigation.

## 15. Production blocks

PRODUCTION AUTHORIZATION: BLOCKED

PRODUCTION EXECUTION: BLOCKED

PRODUCTION ACTIVATION: BLOCKED

WRITER CAPABILITY: BLOCKED
