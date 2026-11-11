# 4e-20-G17: protected governance transaction-owner binding

## 1. G16 blocker and result

[G16](recognition-runtime-g1-adoption-producer-authoritative-storage-protocol-4e-20-G16.md)
requires a protected governance transaction owner that binds verified project-owner
approval to exact typed transitions and permitted control writes. The verified
G13/G14 governance mandate is accepted; no new mandate is requested here.

**Assessment B - GOVERNANCE OWNER-BINDING CONTRACT INCOMPLETE.** The fundamental
missing primitive is the **authenticated, exact-action approval bridge between
the project-owner governance identity and a manager-owned control transaction**.
The mandate identifies the lawful approver; current code authenticates different,
narrow application/runtime scopes. It does not establish that bridge. Transaction
ownership and mutation proof can restrict a verified approval but cannot originate
its authenticity. No credential scheme or trusted callback is invented here.

## 2. Governance owner identity and authentication

The governing identity is the project owner under
[G13](recognition-runtime-g1-formal-governance-mandate-4e-20-G13.md), verified for
documentary governance by G14. The same owner may separately approve adoption
and appointment without another person's governance approval. This does not
authorize runtime/source/producer self-appointment.

Distinguish that approver from the future transaction manager, which is trusted
code acting only on exact authenticated approval. The manager must bind actual
PID, live Thread/context, connection/transaction/phase lifetime and reservation
epochs; it cannot let an incoming object certify its own ownership or expose SQL,
connection, commit or rollback. No opaque identifier alone authenticates the owner.

`admin_auth._owner()`/`_primary()` verify installation owner/access, key/epoch,
generation, revocation and expiry. `admin_auth.ACTIONS` contains existing scoped
actions, not governance adoption/appointment. `runtime_authority_consent._fresh()`
binds exact execution subject, actor, original primary/session and expiry; its
confirmation binds a runtime operation. These cannot be reinterpreted as governance
approval. G13 supplies no separate machine-authentication credential or mapping
between the conversational project owner and an installation owner/session.

Required authentication is therefore **unresolved at the executable boundary**:
how a manager independently verifies that this exact project owner approved this
exact typed action. The prior human governance verification remains valid; it is
not an implementation of a transaction authentication interface. No additional
human approver, signing key, encryption-key read, browser flag or new login route
is assumed necessary or sufficient without an explicit contract.

## 3. Exact approval binding

A future authenticated approval must resolve complete immutable values, not merely
accept claimant-supplied hashes. Its approved subject must include:

- Exact G13 mandate identity/revision and applicable owner approval provenance.
- Exact full G2 P/version/digest and installation/target/family/action scope.
- One transition kind, exact logical record identity, predecessor and successor.
- Exact adoption event for adoption; exact producer identity/context/scope and
  start/end for appointment; exact affected appointment/policy for revocation/
  authorized supersession. Approval of adoption is not approval of appointment.
- Expected relevant governance state and complete control audit head, approved
  effective time/interval and explicit current authorization conditions.
- Exact permitted logical write group and its audit relationship, with an original
  approval identity whose prior consumption can be determined durably.

Approve only immutable canonical subjects under existing canonical/digest rules.
The same approval must not authorize another policy, producer, target, transition,
effective interval or write set. Alteration or stale predecessor rejects; the
manager must not repair the subject, extend its period or reinterpret consent.
This defines required semantics, not a new approval codec or credential issuer.

## 4. Legal typed transitions

Only these four requested transition classes are within this contract. No restore,
reappointment, unrevocation, renewal, replacement or activation transition is added.

| Transition | Required owner / predecessor | Required approval / successor | Permitted logical group | Failure behavior |
| --- | --- | --- | --- | --- |
| Policy unadopted -> adopted | Authenticated mandated project-owner approval; exact scope unadopted, mandate currently applicable | Exact P/scope/effective point; adopted historical fact | One immutable adoption fact, approval-consumption linkage and exact audit evidence | Reject duplicate/conflict/stale approval; whole known uncommitted group rollback |
| Appointment absent -> appointed | Same independently approved governance role; exact adoption effective, no existing conflicting producer | Exact one producer/context/scope/P and start/end; appointed fact | One immutable appointment fact, approval-consumption linkage and exact audit evidence | Reject self-appointment, second producer or wrong policy/interval; rollback group |
| Appointment appointed -> revoked | Same governance owner; exact current appointment/predecessor | Exact affected appointment/scope/effective disposition; revoked fact | One immutable revocation fact, approval-consumption linkage and exact audit evidence | Reject stale/already-revoked/conflicting scope; rollback group |
| Policy adopted -> superseded, if authorized | Same governance owner; exact current policy and explicit separately authorized supersession decision | Exact prior/successor relationship, policy scope and effective disposition; old policy historical superseded fact | One immutable authorized supersession fact, approval-consumption linkage and exact audit evidence | Deny without actual successor authorization; no automatic latest-policy or broader rights |

All groups forbid target writes, source/eligibility/authority creation, authentication
issuance, unrelated control writes, UPDATE/DELETE/REPLACE of governance history,
schema changes, writer/executor capability and arbitrary audit append. Supersession
does not implicitly adopt a successor or appoint a replacement producer.

## 5. Permitted control writes and representation limit

For an audit-backed representation, a single closed typed audit event could carry
the transition and original approval-consumption reference; its one append would
be the logical fact plus audit, not permission for additional generic inserts.
If separate records are used, exact record and corresponding approval-consumption/
audit writes must commit as one fixed group. These are alternatives, not permission
to choose a new schema or authorize variable writes during implementation.

Existing `recognition_admin_audit` supports canonical chained immutable events
and serialized sequence assignment. No exact governance action/subject codec,
approval-consumption representation or permitted physical SQL write set exists.
Thus the exact executable write permit is **not established** merely by listing
logical groups. The future bridge/owner must make authenticated approval inseparable
from an exact typed event and final mutation proof. Until then permit zero writes.

```text
governance mandate != owner approval != adoption state != producer appointment
producer appointment != G1 eligibility != mutation authority != execution authority
```

## 6. Atomic owner binding and transaction ordering

Approval may be obtained before the transaction; a human decision is not a SQLite
atomic operation. Its verification, durable one-use consumption reference, typed
transition, fixed control writes and complete audit linkage must be checked and
committed atomically in the actual control transaction. A detached prevalidated
allow object is not sufficient.

The manager must reserve control first with BEGIN IMMEDIATE, validate exact
schema/history/current governance state, authenticate/resolve scope-exact approval,
reserve and validate target as existing identity rules require, enforce expected
predecessor and unused approval, perform only the approved group, then repeat
current owner/scope/time/identity checks and exact protected-state/write proof.
Manager commits control while retaining required target reservation; only afterward
release target. Target remains query-only; no target DML/DDL or target commit.

Unexpected control mutation, raw-handle/lifecycle access, connection replacement,
epoch/thread/process/context loss or invalidation poisons the manager. No current
administration, 3a, source or consent transaction is widened or impersonated.

Record-before-audit separate commits are forbidden. Publication occurs only after
confirmed control commit and cleanup; publication itself cannot be database-atomic.
If existing storage cannot represent approval consumption and typed linkage in
one group, stop before writes rather than claim sequencing solves atomicity.

## 7. No self-authorization

The source issuer has no governance bridge credential or approved action merely
because it issued an authority. The producer cannot create its own appointment,
change its scope or appoint another producer. Target executor/connection ownership
cannot manufacture project-owner approval. Generic audit records may reference
verified approval but cannot create the independent identity it relies on.

Recovery cannot reconstruct a live owner context, issue fresh approval or reinterpret
an old source-consent token. The same human may act in separately authorized
governance and operational roles under G13, but runtime code does not inherit that
human's governance power. These are required interface exclusions, not proof an
unimplemented credential isolation mechanism already exists.

## 8. Replay, duplicates and concurrency

Actual control writer serialization plus full typed current-state replay must
check expected head/predecessor and original approval's unused identity. Atomic
transition/consumption recording ensures the approval cannot authorize multiple
transitions. Existing audit sequence uniqueness is not by itself a unique approval
constraint; the typed manager must enforce that domain invariant under the lock.

Duplicate adoption, duplicate/conflicting producer appointment, stale approval,
wrong P/version or changed audit/state head rejects before writes. Exact already
committed facts may be inspected after lost publication, not appended again.
Concurrent governance managers serialize; the loser revalidates and rejects stale
scope instead of updating its approval or retrying automatically. Preserve existing
BUSY/LOCKED semantics. No invented SQL index, retry loop or process-local mutex
is substituted for durable authoritative validation.

## 9. Crash and uncertain governance transaction

| Point | Required behavior |
| --- | --- |
| Before owner approval | No approval, writes or usable transition |
| After approval, before transition | Approval is exact subject evidence only; no resulting current state or recoverable manager |
| During transition | Known rollback removes entire record/consumption/audit group; unknown outcome denies publication |
| After control record, before audit linkage | No commit allowed; partial durable group is malformed, not adopted/appointed state |
| After linkage, before commit | All remains uncommitted; INSERT return is not success |
| After commit, before publication | Complete durable facts may be inspected under read authority; no repeated transition to reproduce response |
| Uncertain commit/cleanup | No usable result, no automatic retry; inspect exact durable group/current state |
| Recovery | Factual inspection only; no manufactured approval, live context or newly authorized transition |

This contract grants no automatic reuse even after a known rollback. Any later
write requires valid exact approval and current checks under its separately
defined ceremony. Unknown state never becomes authorization by elapsed time.

## 10. Current-state validation

Future readers must validate intended actual control identity/schema/history and
complete canonical audit/typed governance graph in an authoritative current
snapshot. Resolve exact mandate and owner provenance, policy descriptor/version,
adoption, appointment, original approval-consumption relationships and all relevant
revocation/supersession/interval facts. Reject unknown versions, missing references,
illegal transitions, reused approvals, conflicting scope or inconsistent order.

Return not-adopted, adopted, appointed, revoked, superseded, expired, uncertain or
malformed/incomplete as factual DATA appropriate to the record type. Never return
execution permission from a historical audit event. Each issuance/final boundary
needs fresh applicable state; no cached complete allow or broader latest policy.
Unclear restore lineage or unknown approval authenticity fails closed, not an
absence proof permitting another adoption or producer.

## 11. Revocation and supersession

Project-owner-controlled appointment revocation requires its own exact approval
and expected predecessor, and denies future eligibility production. No automatic
rewriting of already-issued source rights or committed effects is implied.
Current independent source/auth/policy/activation/scope invalidation still applies.

Policy supersession requires explicit authorized old/new policy disposition; it
cannot retroactively broaden source rights, adopt a successor implicitly or reset
exclusions. Current G2 policy-revocation checks remain unchanged, even though this
four-transition contract does not add a separate policy-revocation producer.

Mandate supersession remains an external explicit project-owner governance decision
under G13. It is not a fifth automatic transition or authority created by this
manager. The manager/readers must verify that actual attributable decision and
its consequences for prior adoption/appointments; uncertainty denies dependent
use. Indefinite mandate duration does not mean perpetual source/appointment rights.

## 12. Audit linkage

Required chain: verified exact owner approval -> typed transition -> fixed control
group -> derived current state -> validated audit evidence. Audit must resolve
owner identity/provenance, mandate revision, exact P/version/digest, transition,
predecessor/successor, effective point, scope and consumed approval. Full references
must resolve; a syntactically correct digest is not independent authentication.

Actual writes and expected audit suffix must match exactly, protected unrelated
state must be unchanged, and the authoritative reader must validate the resulting
whole graph. Audit proves attribution/ordering only under that verified producer;
it cannot be the source of the owner's mandate or substitute for current state.
No redundant authority token or execution witness is added.

## 13. Non-escalation and implementation boundary

```text
owner binding != G1 eligibility
owner binding != producer capability
owner binding != mutation authority
owner binding != execution authority
owner binding != recovery authority
```

**Contractually established:** lawful documentary governance owner and its limited
mandate; exact approval subject requirements; four legal transition classes;
logical write groups; manager ownership/lock/commit discipline; atomic approval
consumption and audit obligation; replay/current-state/crash/non-adoption rules.

**Requires another security contract:** the single authenticated exact-action
governance approval bridge. It must establish how the verified human/project-owner
decision is authenticated to the manager and durably bound to the exact subject,
one-use transition and physical write proof. Current runtime/installation sessions
and execution consent artifacts do not already provide it. This is a technical
approval-enforcement gap, not a finding the approved human mandate is absent.

**Prohibited:** governance power inferred from database access or runtime ID,
reusing execution confirmation as governance approval, trusted provider callbacks,
context impersonation, generic audit permission, new schema or credential mechanism
invented in code, stale/cross-context approval reuse, producer self-appointment,
target mutation, broader execution, retries/adoption, lifetime changes or weakened
fresh checks.

## 14. Decision B and architectural stop

**B - GOVERNANCE OWNER-BINDING CONTRACT INCOMPLETE.** Transaction identity and
write/state constraints can be stated, but the missing authenticated exact-action
approval bridge prevents proving that an actual governance owner controls those
writes. Selecting an existing runtime credential or arbitrary operator assertion
would invent unsupported authority. No evidence proves the model inherently
incompatible (C), and A is not justified without that bridge.

Stop the architectural chain. No implementation, optimization or performance
slice is proposed. G1 remains unadopted and no producer is appointed. All existing
authority semantics, identity checks and the 120-second ceiling remain unchanged.

## 15. Validation and explicit production blocks

Only this document is added. Document whitespace/local-link checks and
`git diff --check` only. No pytest, Z18, T, broad suites, Python/schema/migration,
database writes, permissions, authorities, producer appointment, enforcer,
target DML/DDL, hosted/production access, key reads, commit or push.

PRODUCTION AUTHORIZATION: BLOCKED

PRODUCTION EXECUTION: BLOCKED

PRODUCTION ACTIVATION: BLOCKED
