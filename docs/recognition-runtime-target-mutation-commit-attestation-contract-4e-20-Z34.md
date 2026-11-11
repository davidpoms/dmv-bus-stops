# 4e-20-Z34: decision-scoped target mutation and commit attestation

## 1. Z33 blocker and result

[Z33](recognition-runtime-target-effect-witness-authorization-contract-4e-20-Z33.md)
identified the absent decision-scoped target mutation-and-commit attestation
boundary. This review defines its required evidence/lifecycle/atomicity semantics,
but concludes **B: one specific primitive remains missing — a non-adoptable
original-runtime mutation grant for the exact family effects plus witness**.
No existing authority contract grants that target action to a runtime owner.

An approved source authority can bind intended execution without making an
arbitrary owner eligible for the current writer. Read-only checks and inert witness
codecs do not supply the missing grant. No permit, new accepted capability,
transaction owner, target behavior, schema, migration or producer is created here.

## 2. Exact authorized-original-owner definition

The existing original identity/provenance source is the private registered
`CoordinatorContext` and its exact original outer lifetime, issuance notice,
committed authority and original continuation in
[`runtime_execution_coordinator.py`](../src/review/recognition/runtime_execution_coordinator.py).
This identifies origin, **not an existing family mutation entitlement**.

For any later attestation owner all of these must be actual authoritative bindings:

| Dimension | Required original-owner binding |
| --- | --- |
| Authentication | Genuine current owner primary/session; exact runtime profile/generation, auth/MFA epochs, revocation/expiry and current ownership/access |
| Consent | Exact current owner decision/reason and protected one-use step/confirmation, existing TOTP replay/throttle rules; no generic CLI/browser flag |
| Operation | Exact runtime operation UUID/digest and source event/preparation/proposal/ACK/effective approval; exact frozen family manifest/population |
| Scope | Installation, target UUID, binding/generation, owner, enrolled runtime profile and auth/MFA epochs; no caller replacement scope |
| Authority and D | Exact canonical authority ID/body digest from genuine durable issuance plus original live registration; D identifies the decision but is not itself the grant |
| Profile/incarnation/activation | Current finalized G+2 and runtime observation match; current independent activation sequence/digest exactly matching original authority |
| Reservation | Actual control then target owned connections/transactions, query mode and reservation epochs; no inherited or caller-supplied lease |
| Process/thread/context | Exact registered original outer/context/PID/Thread/identifier and paired clock; no imported/reconstructed continuation or attempt |
| Target ownership | Exact actual target path/host/device/inode/schema/fingerprint and existing installed packages; manager owns lifecycle exclusively |

Existing coordinator issuance/attempt contexts keep the target query-only and
permit only their fixed control writes. The metadata owner enables only its
approved metadata marker. `writer_boundary._local_lease/verify_local/acquire`
requires its distinct accepted local/legacy claim/EXECUTING path; disposable
capabilities have their own restrictions. **The grant allowing the original
runtime owner to perform family effects plus the journal witness is UNRESOLVED.**
Do not widen a context or synthesize legacy records to satisfy these checks.

## 3. Attestation semantics: what can actually be asserted

| Fact | Required evidence | What it cannot assert |
| --- | --- | --- |
| Validation completed | Current exact admission/source checks under original reservations | No mutation has thereby occurred or become permitted |
| Mutation attempted | Original owner entered the authorized fixed write operation | Neither accepted DML nor return value proves commit |
| Business effects verified before commit | Existing exact manifest/record/accounting/FK checks on actual rows in the owned target transaction | Rows visible to that same transaction may still roll back |
| Witness created before commit | Z31 witness encodes exact D/decision/pending/effect digest and time | Detached/inserted witness is not durable target outcome |
| Mutation and witness committed | Confirmed target transaction plus independent validated committed read of complete effects and exact witness | Does not prove control recording or renewed authority |
| Control outcome recorded | Confirmed conditional journal terminal/audit correlated to validated target proof | Cannot substitute for target proof or restore original capability |
| Outcome uncertain | Missing/conflicting/unavailable/unknown-commit or wrong-lineage evidence | Neither success nor retryable failure |

There is no new cryptographic signature or SQLite global commit ID. The proposed
attestation is a verified durable outcome relationship under trusted code/database
ownership: effects and witness committed in the same local transaction, then
independently verified on the intended target. A witness timestamp is not the
exact wall-clock commit instant and no observation claims filesystem continuity.

## 4. Complete existing family verification

Before mutation the owner verifies **preconditions and the intended complete
effect set**, not nonexistent resulting business rows. After writes it verifies
the complete actual effect set, and after commit it independently verifies durable
effects/witness. Do not move post-write checks earlier as if they proved actual
effects. No family policy or qualifier is added.

| Existing effect/precondition | Authoritative source | Freshness and owner | Relationship to D / target transaction |
| --- | --- | --- | --- |
| Exact rule/manifest and explicit authorization reference | Stored/current reviewed private manifest, `permanent._validate_manifest`, source operation and authority references | Original owner before DML, actual matching rule/operation checks after DML | Runtime manifest digest must equal private manifest-derived operation key; full checks inside reserved target transaction |
| Qualifying completions, competitors and identity history | `permanent._prepare`, existing First Look report, immutable completion ledger and qualification rules | Regenerate whole manifest and compare before writes; no missing-completion capture | D's exact frozen inputs/evaluation/population, not caller replacement inputs |
| First Look claims | `check_claim_integrity`, `_verify_operation_records` and `recognition_first_look_claims` | Check no conflicting claims before writes; exact actual candidate/evidence/reviewer/assignment/time/set afterward | One exact claim per candidate, all in same T; historical credit is not reassigned |
| Geography current preconditions | Existing `_prepare` geography report, certified frozen scope snapshot and current-active membership checks | Full frozen evaluation/input/rule equality before writes; no later denominator shrink or threshold override | Exact manifest and independently reviewed scope; inside T |
| Geography scope/snapshot/membership | Existing scope identities, snapshots, members and `_verify_operation_records` | Exact snapshot set, canonical scope/digests, member sets and identities after writes | Immutable complete frozen scope population bound to D's manifest |
| Geography awards/assignment witnesses | `check_geography_integrity`, `_check_facts`, `_verify_operation_records` | Exact award set/candidate fields, snapshot/denominator, qualifying assignments, distinct-stop numerator and reviewer identity after writes | Whole existing population in T; no partial award/quarantine outcome |
| FK/actual record accounting | Existing `PRAGMA foreign_key_check`, full family integrity and deterministic `production_receipts._records` extraction | Actual effects verified inside T and again from committed target after commit | Exact permitted record set; digest is evidence reference, not authority |

Source:
[`permanent.py`](../src/review/recognition/permanent.py),
[`permanent_schema.py`](../src/review/recognition/permanent_schema.py)
and [`production_receipts.py`](../src/review/recognition/production_receipts.py).
Supported effects remain First Look and Geography `finalize`, atomic historical
policy, no active per-item quarantine, no Explorer/review/source mutation and no
discrepancy correction inserted into finalize. Existing read-only extraction may
inform evidence, but legacy receipt construction/authority cannot be fabricated.

The target record family itself is defined. The unresolved issue is who may
legally perform its writes and bind the result to a new runtime witness, not
permission to invent another family effect or change old idempotency semantics.

## 5. Smallest decision-scoped mutation grant

A sufficient future grant must be an internal one-shot exact-action permit, not a
general writer or durable bearer token. It must bind D, exact runtime operation/
manifest/population, target/installation/G+2 profile/generation/binding/owner/auth/
MFA epochs, exact activation incarnation, current proposal/ACK/approval and original
context/PID/thread/target connection/transaction/reservation epoch. It exposes no
SQL, cursor, connection, alternate manifest/target, commit/rollback or schema change.

Only an independently authorized original runtime execution owner could originate
it, **after** complete current authentication/consent/admission and positive exact
journal decision/pending/exclusion validation. No existing function currently
grants this permit. Its actual grant/source contract is **UNRESOLVED**; the
requirements here are not a new accepted writer capability or constructor.

The permit would be consumed before its sole fixed mutation invocation. Failure
or uncertain use cannot reset it. Its lifetime is no longer than the original
120-second authority window and all earlier credential/consent bounds. Owner exit,
thread/process/context change, connection/reservation loss or epoch/mode transition
invalidates old views/permits and requires the separately reviewed current owner
rules; no caller recreates one. Auth/profile/generation/activation/approval/stop/
dependency/identity/claim/control changes must fail fresh required checks rather
than silently rebind or refresh intent. Expiry/revocation permits no additional
mutation and never releases the durable duplicate fence.

## 6. Atomic business-effect/witness boundary

The smallest valid target atomic unit is all permitted new rule/operation/family
records for one exact frozen manifest **and one exact Z31 target witness**.
Existing matching shared rule rows need not be reinserted. Same target database,
same original owned connection, same target transaction; no intermediate commit.
This is possible as a SQLite local transaction in principle, but no current
runtime owner is authorized to execute that combined unit.

The required order is: fresh actual authorization and precondition verification;
consume exact local permit; existing fixed family mutation; complete actual-record
verification and evidence digest; exact D/pending witness encoding/insertion;
actual entire write-set and fresh final identity/scope/time/stop/control checks;
then target commit. Witness failure rolls back all known uncommitted effects.
No writer result or effect count can skip record verification.

Before effect there is no result. During/after effect but before witness, all
effects must still be uncommitted. After witness before commit, both remain
uncommitted. After confirmed commit, verify independently under required target
reacquisition/reservations and actual identity. A commit error produces UNKNOWN
unless positive durable proof resolves it. Witness repair after a prior family
commit is forbidden; it would falsely attest same-transaction coupling.

Current unleased `permanent.finalize()` owns its own commit. Its existing leased
path accepts different exact authority. Neither may be used as an undocumented
replacement adapter to obtain this atomic unit. No new DML/extraction/permit is
invented here and no legacy check is weakened.

## 7. Control-outcome coupling

Use unchanged journal D and exact confirmed DECISION_CREATED/TARGET_PENDING source
events. Their durable control exclusion must precede target business mutation,
but those events grant no permission. Each control commit retains its target
reservation as required by its manager. Between phases reacquire control before
target and revalidate current ownership/security state; never transfer old views.

After positive target commit/witness/effect verification, control COMPLETED must
reference that exact pending/witness digest and commit atomically with its exact
source-audit linkage. This is a factual outcome transition, not new execution
authority. No success before confirmed target proof, confirmed corresponding
control record and required cleanup/current result checks.

Target-first relative to **control completion** leaves target committed/control
pending after a crash: keep exclusion and permit factual inspection only.
Control-first relative to target may record only decision/start, never completion.
Control success before target proof is forbidden. Both databases do not share
one atomic commit. No intermediate durable decision or witness is adoptable;
missing control completion never makes target effect retryable.

Source authority/consent/audit answers original permission; witness plus actual
records answers target outcome; control journal/audit answers its recording.
No domain overrides conflicting proof in another. A disagreement is an integrity
stop, not permission to choose a newer row or repair history. The future fixed
source-audit producer must link D and exact journal event/witness references
without duplicating all family records into general audit.

## 8. Crash and uncertain-commit protocol

| Failure point | Deterministic required interpretation and action |
| --- | --- |
| Before verification | No target mutation grant; no artifact or prior preparation is executable |
| After verification | Validation is not durable permission or outcome; process loss destroys local eligibility |
| Before mutation | Durable decision/pending may be spent, but no new owner can adopt its start |
| During mutation | Known uncommitted family transaction rolls back as a whole; observer still requires durable proof |
| After business effect, before witness | DML is not commit; known rollback removes effects; unknown connection outcome cannot be declared success or failure from memory |
| After witness, before target commit | Witness and effects both uncommitted; inserted witness cannot establish target outcome |
| After target commit | Verified positive effects/witness may survive lost owner; keep duplicate exclusion and do not repeat effects |
| Before control outcome | Pending/uncertain control and positive target evidence may coexist; no usable success publication |
| After control outcome | Confirmed terminal/audit still requires exact target proof; no live owner or permit reconstructed from those records |
| Before result publication | Cleanup/response may fail despite committed effects; do not re-execute to reproduce response |

Authoritative inspection must use current authenticated outcome-only permission,
validated intended target/control identity/schema/lineage, exact D/source/pending
and complete target witness/effect evidence from a committed snapshot. Only exact
positive proof can resolve target committed and permit factual control recording.
Positive original-manager no-commit evidence is required for failure; missing row,
no response, dead process, elapsed timeout, absent marker or expired grant is not
that evidence.

If commit, identity/restore lineage, inspection or source/audit graph remains
uncertain, the decision is **terminally blocked for execution**. Its facts may be
resolved later, but no retry/adoption/renewal is authorized. It may remain UNKNOWN
indefinitely. Failure/uncertainty recording cannot commit through expired old
authentication: if original recording permission is gone, leave facts unresolved
for a separately authenticated factual inspector. That inspector cannot mutate
target or reauthorize execution.

## 9. Conceptual attestation lifecycle

These labels are not new database enums or changes to Z31/legacy schemas.
The attestation is a relationship of facts, not a new reusable token.

| Transition | Owner / prerequisite / authority | Durable evidence and atomicity | Failure/rollback |
| --- | --- | --- | --- |
| BOUND to PRECONDITIONS_VERIFIED | Genuine original owner, complete fresh source/target admission; read authority only | Existing exact D/scope and pending may exist; no committed effects inferred | Reject changed/expired scope; no permit from verification alone |
| PRECONDITIONS_VERIFIED to MUTATION_PERMITTED | Only the original authorized target-grant issuer, currently UNRESOLVED | One-shot private registration, not durable executable evidence | No existing issuer means STOP, not a generic lease |
| MUTATION_PERMITTED to EFFECTS_VERIFIED_UNCOMMITTED | Same owner/connection/transaction and consumed permit; all family preconditions/fixed writes | Exact complete actual effect evidence inside T | Whole known uncommitted rollback; no partial family acceptance |
| EFFECTS_VERIFIED_UNCOMMITTED to WITNESS_BOUND_UNCOMMITTED | Same owner, canonical Z31 D/pending/effect witness and current final checks | Effects plus witness in same T, not yet durable | Any mismatch/encoding/insert failure rolls back both |
| WITNESS_BOUND_UNCOMMITTED to TARGET_ATTESTED | Same original owner commits; independently validates durable target effects/witness | Target commit is the irreversible effect/witness atomic point | Unknown commit publishes no usable result; no repeat effect |
| TARGET_ATTESTED to CONTROL_RECORDED | Original recorder or separately permitted authenticated factual resolver; exact positive target proof | Conditional COMPLETED and audit atomically in control | Unknown recording leaves target fact/exclusion intact, never retry |
| CONTROL_RECORDED to RESULT_PUBLISHED | Original owner only, confirmed facts, clean lifecycle/deadline/result checks | No new authority; historical records may outlive lost response | Publication failure cannot restore a permit or generate another mutation |

No factual terminal resolution transitions backward to MUTATION_PERMITTED.
Original source authority and live ownership are prerequisites of mutation;
positive outcome evidence is not an alternative predecessor grant.

## 10. Security separation

```text
attestation != authorization
attestation != writer capability
attestation != execution capability
witness != authorization
journal != authorization
recovery != reauthorization
```

A recovered attestation can establish historical outcome only. It cannot bypass
fresh auth/MFA, activation, effective approval/ACK, emergency stop, dependencies,
strict physical identity, current profile/generation/history/claim/control/schema,
readiness, deadlines or actual reservation/owner checks. Journal DATA cannot be
passed to the writer boundary as a newly accepted type. No public/browser supplied
scope/digest or synthetic fixture authority may manufacture production permission.

## 11. Duplicate, replay and adoption

Durable journal fences remain exact D/body digest and installation/target/operation
and manifest exclusions, with one pending start and one target witness. Existing
authority/attempt/metadata/legacy/family conflicts remain exclusions, not data to
adopt. Control-first writer reservation serializes competing owners; target
reservation and unique witness plus business-record constraints independently
fence target effects. Preserve BUSY/LOCKED behavior without arbitrary retry loops.

Duplicate owner, replayed permit or lost original registration rejects before
mutation. Replayed witness/attestation yields only validated historical inspection,
never a new grant. Process restart/cross-process recovery cannot recreate the
original PID/thread/context/transaction or reset consumption. A new decision for
the same operation/manifest remains blocked; a truly different nonconflicting
operation requires its own fresh complete decision and family preconditions.

The logical uniqueness constraints are defined in Z30/Z31 but not installed into
runtime databases. Their inert presence cannot prove a producer enforced them
or substitute for the missing target mutation grant. No TTL, deletion, terminal
failure or new session releases historical duplicate exclusion.

## 12. 120-second distinction

Security validity requires an actual original grant and exact effects/witness
commit proof. This review specifies those obligations but cannot complete that
validity proof without the missing grant boundary. Expected performance is not
established. Measured performance of this new boundary is **UNMEASURED**.

All authority-bound work still spends the original at-most-120-second window,
clipped by earlier auth/consent deadlines. Actual authority construction starts
time; journal creation, witness insertion, commit or publication cannot restart
it. A required deadline failure denies further mutation and usable result, while
possible already committed outcomes remain excluded and subject to inspection.
No guarantee of interrupting a SQLite commit at the exact clock tick is invented.
Nothing here solves or authorizes rerunning the blocked Z18 composition.

## 13. Decision B

**One specific primitive remains missing: the non-adoptable original-runtime
mutation grant for the exact atomic family-effect-plus-witness target transaction.**
Its grantor/source authorization, live registration, fixed write permission and
commit/outcome attestation responsibility are not supplied by existing coordinator,
metadata, observer, journal or legacy writer contracts. Codec correctness and
family integrity readers cannot grant that privilege.

This identifies a missing authority boundary, not an impossibility of SQLite
atomic effects/witness or a license to remove legacy checks. No replacement permit
or privileged owner is invented merely to reach decision A.

## 14. Stop and validation

**Stop. No next performance investigation or implementation slice is proposed.**
There is no approved target writer, attestation producer, new mutation permit or
executable transition to implement from this document. Existing code, schema,
authority semantics, identity checks and lifetime remain unchanged.

Only this document is created. Validate `git diff --check` and document whitespace/
local links. No pytest, Z18, T, broad suite, code/schema/migration, target DML/DDL,
attestation boundary, mutation grant, writer/execution authority, production/hosted
access, commit or push.

## 15. Production blocks

PRODUCTION AUTHORIZATION: BLOCKED

PRODUCTION EXECUTION: BLOCKED

PRODUCTION ACTIVATION: BLOCKED

WRITER CAPABILITY: BLOCKED
