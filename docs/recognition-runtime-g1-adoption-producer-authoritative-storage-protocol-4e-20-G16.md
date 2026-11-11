# 4e-20-G16: authoritative G1 adoption/producer storage protocol

## 1. G15 blocker and result

[G15](recognition-runtime-g1-policy-adoption-producer-appointment-4e-20-G15.md)
accepts the verified governance mandate but finds no typed protected adoption/
appointment storage integration. G1 remains unadopted and no producer is appointed.
The question here is durable enforcement, not another governance mandate.

**Assessment B - STORAGE PROTOCOL INCOMPLETE.** Logical immutable records and
state/ordering requirements can be specified below using existing audit/storage
foundations. The single fundamental missing enforcement primitive is a **protected
governance transaction owner that binds verified project-owner approval to an
exact typed state transition and proves its permitted control writes**. Existing
generic audit access does not supply it; no authentication/owner adapter is
invented or an existing runtime context widened to make it appear available.

## 2. Typed adoption logical record

The following is a logical record contract, not a new SQL table, implemented
codec or adopted policy fact. Its authoritative governance owner is the project
owner under verified G13/G14; the runtime source issuer is not its writer.

| Logical field | Required meaning |
| --- | --- |
| Stable adoption identity | Exact original immutable canonical adoption record digest, resolvable in its control audit position; no ambiguous latest-policy identity |
| Mandate reference | Exact `dmv-bus-stops-g1-governance-mandate-4e-20-G13-v1`, revision and complete verified approval/provenance reference |
| Policy | Exact G2 P descriptor/version and existing canonical digest; no extra authority fields or overloaded reason/readiness |
| Scope | Actual installation/target, exact supported historical family/action and prospective-only restrictions |
| Approval | Exact project-owner decision approving this adoption, referenced full evidence, actor and decision ordering |
| Record/effective time | Actual recorded time plus approved prospective effective time no earlier than authorization/recording; canonical existing UTC rules |
| Original state | Adoption fact only; it is not an evergreen current authorization flag |
| Expected predecessor | Exact relevant prior governance state and control audit head against which approval/transition was authorized |

All original fields and canonical bytes/digest are immutable. Revocation and
supersession are separate immutable events referencing the exact original record
and expected predecessor, effective point, authorized actor/evidence and disposition.
Current state is derived from the complete validated ordered graph; no UPDATE of
an `active` field or rewriting of adoption. G13's indefinite mandate is not a
policy adoption time or automatic policy state. No G1 source eligibility follows
solely from an adopted record.

## 3. Typed producer-appointment logical record

| Logical field | Required meaning |
| --- | --- |
| Stable appointment identity | Exact original canonical appointment digest and durable audit reference |
| Producer identity | One exact constrained original source-producer role/implementation identity, not a caller-selected function or runtime self-assertion |
| Mandate/adoption/policy | Exact confirmed adoption and G13 references, full P/version/digest and current applicability |
| Action/decision scope | G1 original-holder-only, one new original D per qualifying source, exact complete permitted family-effect/witness action; no adoption of historical D |
| Deployment/runtime scope | Exact installation/target/family, enrolled runtime incarnation/profile/generation/binding/owner/auth/MFA constraints and genuine original process/Thread/context/reservation requirements |
| Approval | Exact independent project-owner appointment decision and complete attributable evidence, not source consent reused as appointment |
| Interval | Explicit approved start/end; start no earlier than confirmed applicable adoption/appointment. Indefinite mandate does not imply indefinite appointment |
| Original state/predecessor | Appointment fact and exact expected current governance predecessor/audit head; no mutable active-row overwrite |
| Restrictions | No self-appointment, appointment of another producer, scope expansion, transfer/re-delegation, renewal, retry, recovery or target-write right |

Original fields are immutable. Revocation/supersession is an append-only linked
decision, not DELETE/REPLACE. G13 does not authorize replacement/rotation/recovery
or additional concurrent producers; a record claiming those powers must reject
under this mandate, even if structurally valid. A future separately authorized
mandate would need its own explicit scope and review, not reinterpretation here.

## 4. Protected-write authority and exact missing primitive

Only the governance project owner identified by G13/G14 may authorize adoption,
appointment, revocation or supersession within that mandate. No actor may modify
original records. The future trusted writer must consume approval for exactly
one typed action, scope, interval and expected predecessor and bind it to current
verified owner/mandate evidence. It must deny runtime/source/producer attempts
to manufacture those facts or replay a broader/older approval.

```text
governance mandate != adoption record != producer appointment
producer appointment != G1 eligibility != mutation authority != execution authority
```

Evidence inspected: `administration._audit()` and `_audit_head()`,
`administration_schema.definitions()`/`check_control()`,
`runtime_authority_consent_transaction._State.authorize()`/`_finish()`, and the
current source issuer `_persist()`/`_final_mutations()`. These provide generic
append-only audit, schema/history checks and examples of manager-owned exact
mutation proofs. They do not provide the proposed governance writer's approved
identity/approval binding or a typed governance state-machine authorizer.

**Unresolved:** how actual verified owner approval becomes a non-forgeable,
scope-exact, replay-fenced permission in a dedicated manager-owned governance
transaction, with fixed allowed audit/record writes and final protected-state
proof. The original mandate exists; this is its technical enforcement boundary.
No new login scheme, browser flag, operator string, trusted callback, key-content
read or disguised runtime context is selected to fill it. Merely adding a typed
JSON subject to generic `_audit()` would leave this gap open.

## 5. Audit linkage and representation limits

Required graph: verified mandate/provenance -> exact adoption/P -> exact one
appointment -> applicable revocation/supersession, with each transition's original
owner approval, scope, time/order and expected predecessor. References must resolve
full validated objects, not just syntactically valid hashes. Future G2 original
consent/eligibility/source audit must resolve the applicable original graph.

Existing `recognition_admin_audit` has sequence primary key, immutable UPDATE/
DELETE guards, collision INSERT/REPLACE rejection and contiguous-sequence trigger.
`_audit_head()` checks digest, predecessor, sequence and nondecreasing time.
`_audit()` supplies canonical audit envelopes with action/actor/time/subject.
Those foundations could hold typed logical events without inventing another
table, but do not currently verify their authorized producer or typed transition.
They therefore cannot already establish this authority relationship.

An audit-backed future implementation would need closed typed action/subject
validation, full current-state replay and the protected writer in section 4.
Exact new action strings, schema constraints, SQL implementation, storage format
or migration are not invented here. A record and its required audit must never
be independently committed; if an audit event itself is the sole logical record,
its validated envelope is that single atomic fact, not an additional shadow row.

## 6. Current-state interpretation

| State | Authoritative meaning / admission result |
| --- | --- |
| Not adopted | No valid applicable adoption in a complete valid history; deny eligibility |
| Adopted | Confirmed effective exact adoption, unrevoked policy and required active appointment; necessary, never sufficient for source eligibility |
| Revoked | Valid effective authorized revocation; deny applicable new adoption/appointment/eligibility use under the affected scope |
| Superseded | Exact old fact remains historical; new version cannot silently authorize old sources. Validate successor independently under its own permitted governance scope |
| Expired | Current time reaches appointment end or another explicit bound; deny future production under it. G13 mandate itself has no scheduled expiry |
| Uncertain | Commit/publication/lineage/approval/status cannot be resolved; deny, do not choose a convenient older allow |
| Malformed/incomplete | Bad canonical data, missing reference, conflicting heads, illegal transition, unknown action/version or absent provenance; integrity failure and deny |

An absence result is safe only after verifying the intended complete control
history/identity. Missing data on an uncertain restored lineage is not proof that
an action never occurred or is safe to repeat. A historical adoption event alone
cannot be treated as current authorization.

## 7. Atomic state transitions and crash handling

Each authorized transition must occur under serialized control `BEGIN IMMEDIATE`,
validate exact current schema/history/mandate/approval/predecessor and applicability,
write only its fixed logical event and audit group, prove all protected state
otherwise unchanged, and manager-commit. Existing required target reservation
ordering remains: control before target and target retained through control commit;
no target changes/commit. No current transaction helper is modified or assumed
to accept new governance permissions.

| Crash point | Required state interpretation |
| --- | --- |
| Before write | No new transition; no usable publication |
| During record/audit group writes | Known rollback removes the whole uncommitted group; partial durable group is invalid |
| After record write, before required audit linkage | Commit forbidden; no valid adopted/appointed state from the partial record |
| After audit linkage, before commit | Still uncommitted; successful INSERT is not authorization |
| After durable commit, before publication | Actual complete fact may be established by read-only inspection; no automatic repeated mutation |
| After publication | Result is historical evidence; subsequent use still validates current state freshly |
| Unknown commit/publication | No usable success; inspect exact durable state, never retry automatically or fabricate missing linkage |

Adoption and appointment remain distinct approvals. If separate transactions,
appointment requires confirmed applicable adoption; adoption-only prefix grants
no producer use. A combined transaction would require both approvals and complete
group rollback, not one approval implicitly covering both. No particular combined
owner/protocol is claimed to exist. Revocation/supersession and their audit links
require the same atomic-group discipline. Publication itself is not database-atomic.

## 8. Concurrency and duplicate fencing

Existing SQLite single control-writer reservation and audit sequence/immutability
constraints support serialization; they are not a SQL unique-policy/producer
constraint. Do not claim a nonexistent index or trigger provides that guarantee.

The required typed writer must replay/validate current scope under that reservation
and condition its transition on exact expected head/state. Duplicate approval/event
or adoption of the already-adopted same scope returns inspection or rejects, never
another authorization. Conflicting policy versions and second concurrent producer
appointment reject under the current mandate. A stale expected head, appointment
interval or approval rejects. Concurrent revoke versus appoint/use must observe
authoritative serialization and effective time; revocation cannot be overwritten
by replaying an older allow. An exact committed event may be inspected after lost
publication, but inspection is not retry permission.

Without the protected writer/full typed replay contract, generic audit sequence
uniqueness alone cannot enforce these domain constraints. No arbitrary retry loop
or new database constraint is proposed to hide that distinction.

## 9. Prospective-authority proof

Adoption/appointment history is necessary context for new original source issuance,
not an assignment of rights to existing sources. Require original G2 P/C/Q/E
consent/eligibility evidence and original source-audit prefix at issuance. A later
governance event cannot enter an old immutable prefix or change its policy/action.
Never resolve an old source against a broader latest version or new appointment.

An appointed producer may establish only exactly authorized prospective eligibility,
not new target permission, another producer, grant-of-grant or executable witness.
History/audit/appointment DATA does not reconstruct original process/context
ownership. Existing formats, source semantics and permanent execution exclusions
remain unchanged.

## 10. Authoritative read protocol

For each future eligibility decision, read the intended actual control database
under its genuine owner/reservation; validate exact schema, full binding/profile/
identity/history and audit chain, then the complete typed governance graph and
owner approval references. Resolve exact mandate/adoption/P/appointment and current
revocation/supersession. Check actual clock, approved interval and exact scope,
including current installation/target/profile/generation/owner/authentication,
runtime/context and producer identity. Compare original source policy/action, never
accept caller replacements or a detached allow result.

Return current-state DATA only, not authority. Require fresh read at protected
issuance/final boundaries; stale observations and cross-ceremony caches are not
authorized. Every uncertainty, malformed relationship or unknown version denies.
The current generic `_audit_head()` is insufficient without full typed governance
replay and the protected-writer/approval binding. No reader is implemented here.

## 11. Revocation and supersession semantics

G13's project-owner governance authority may explicitly revoke/supersede within
the mandate, evidenced by attributable decisions naming original identities,
affected scope and effective order/time. No runtime/source/producer may do so.
Append immutable transitions only; no deletion, hidden overwrite or automatic
latest-version substitution.

Appointment revocation/expiry denies future eligibility production. It does not
automatically rewrite already-issued source rights or committed effects. Mandate
revocation stops new governance decisions under it; consequences for already
adopted policy/appointments must be explicit in the decision. Unknown applicability
denies dependent use. Existing G2 current policy-revocation checks and independent
source/authentication/activation/scope checks remain mandatory. No cancellation
guarantee during an irreversible commit, retroactive grant, fence release, retry
or recovery right is invented. Supersession cannot authorize replacement/rotation
that the current mandate excludes.

## 12. Implementation boundary

**Contractually established:** verified governance owner and mandate; immutable
logical adoption/appointment/reference requirements; distinct policy versus source
eligibility; audit-order/serialization foundations; fresh complete current-state
replay requirements; atomic record/audit groups and fail-closed crash rules; no
retroactive broadening; existing revocation and reservation boundaries.

**Requires another security contract:** the protected governance transaction owner
binding actual project-owner approval to exact typed transition and permitted
control write proof. Its approval-authentication/context binding, replay-fenced
entry and final mutation proof are not supplied by existing generic audit access
or source/consent transactions. This is the single fundamental enforcement gap;
typed record spelling alone cannot repair it.

**Prohibited:** runtime self-adoption/appointment, arbitrary audit subjects as
permission, context impersonation or approval callbacks, undocumented schema,
overwriting history, stale allow reuse, broader policy lookup, grandfathering old
sources, target writes/witness/enforcer implementation, lifetime extension,
transfer/delegation/renewal/retry/recovery-based authority.

## 13. Decision B and architectural stop

**B - STORAGE PROTOCOL INCOMPLETE.** The logical protocol above specifies required
state and ordering, but cannot establish who/what may perform its protected writes
without the missing exact governance-owner approval/transaction binding. Governance
authorization is already verified; no additional independent mandate is requested.
No evidence establishes that existing SQLite/audit storage inherently cannot
represent the facts, so C is not justified. A would falsely treat the existing
generic audit writer as an authorized typed state-machine producer.

Stop the architectural chain. No implementation, optimization or performance
slice is proposed. G1 remains unadopted; no producer is appointed. The original
120-second ceiling and all mandatory live validation remain unchanged.

## 14. Validation and explicit production blocks

Only this document is added. Document whitespace/local-link checks and
`git diff --check` only. No pytest, Z18, T, broad suites, Python/schema/migration,
database writes, permission/authority/grant/producer appointment/enforcer,
target DML/DDL, hosted/production access, key reads, commit or push.

PRODUCTION AUTHORIZATION: BLOCKED

PRODUCTION EXECUTION: BLOCKED

PRODUCTION ACTIVATION: BLOCKED
