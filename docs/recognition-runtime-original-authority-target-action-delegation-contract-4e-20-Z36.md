# 4e-20-Z36: original-authority-to-target-action delegation review

## 1. Z35 blocker and disposition

[Z35](recognition-runtime-original-mutation-grant-contract-4e-20-Z35.md)
identified missing creation authority for the exact family-effect-plus-witness
mutation permit. This review concludes **B: one specific primitive remains
missing — a source-authority grant-right policy for that exact target action**.
No existing rule establishes that entitlement for the original runtime owner.

This document specifies the necessary conditions and safety restrictions without
declaring them sufficient to create a permission absent from the source contract.
It grants no target action, changes no authority semantics and creates no
delegation, permit, executor, schema, migration or target mutation. The authority
ceiling remains 120 seconds. No performance investigation or feasibility claim.

## 2. Delegation source

The only relevant candidate source is the original activation-bound runtime
execution authority, format `recognition-runtime-execution-authority-v1`, under
its genuine original private coordinator lifetime. Neither a journal row, detached
codec result, preactivation claim/handoff, approval, metadata entry, activated
read-only observer nor legacy writer lease is an alternative source.

| Source dimension | Required existing authoritative binding |
| --- | --- |
| Identity | Canonical authority ID and body digest; exact immutable durable source/genesis/audit and original issuance provenance |
| Scope | Exact operation UUID/digest, source event/preparation, family, writer manifest/population and runtime target/install/generation/profile/binding/owner/auth/MFA epochs |
| Authentication | Current genuine original owner primary/session, profile/session scope, access, revocation, auth/MFA epochs and expiry |
| Consent | Exact subject, protected TOTP/one-use step and confirmation; original `authorize_runtime_execution` decision/reason and consumption provenance |
| Approval/ACK | Exact acknowledged proposal, effective current runtime approval and invalidation history |
| Activation | Independent current incarnation/sequence/digest exactly matching original authority |
| Runtime identity | Actual enrolled hostname/paths/devices/inodes/schema/fingerprint and finalized G+2 profile continuity |
| Reservation | Actual original manager connections/transactions/modes/reservation epochs; control before target; no caller-supplied lease |
| Deadline | Original authoritative paired clock, strictly before all auth/consent/authority deadlines; at most 120 seconds from actual authority issue |
| Owner | Exact original private outer/context/issuance notice/continuation registration, PID, Thread/identifier and active unpoisoned lifetime |

Sources:
[`runtime_activation_authority_issuance._body`](../src/review/recognition/runtime_activation_authority_issuance.py),
[`runtime_execution_coordinator`](../src/review/recognition/runtime_execution_coordinator.py),
and [4e-11](recognition-runtime-activation-bound-authority-contract-4e-11.md).
The source policy anticipates a future distinct writer under fresh execution-phase
reservations. That future requirement is not a complete grant-right rule for the
new exact atomic family-effect-plus-journal-witness action. The producer itself
forbids target DML and writer lease issuance; current coordinator/metadata and
writer contracts remain narrower.

**Necessary source grant-right: UNRESOLVED.** A copied authority ID, valid body,
unexpired record or genuine holder cannot bootstrap a privilege not yet defined.

## 3. Exact delegated action required for any future rule

The only candidate action is one internal invocation of the existing supported
atomic historical family mutation plus its one Z31 witness, in one exact target
transaction. It must bind:

- the one original authority and D = authority ID/body digest;
- exact runtime operation and frozen private manifest, including family,
  population, source event/preparation and proposal/ACK/effective approval;
- the actual enrolled target and control scope, installation/target UUID,
  G+2 generation/profile/binding/owner/auth/MFA epochs and activation incarnation;
- actual original PID/Thread/context, target connection/open transaction,
  reservation identity/epoch and controlled mode;
- exact confirmed journal decision and sole TARGET_PENDING event, plus intact
  logical-operation/manifest and old-runtime/legacy exclusions;
- exact existing First Look or Geography effect set, including required
  rule/operation/supporting rows, full precondition and post-effect verification;
- exactly one canonical Z31 witness derived internally from the same D/decision/
  pending, verified actual effect evidence and valid recorded time;
- original authority expiry and all earlier credentials/consent deadlines,
  one-shot consumption and no re-delegation.

The witness cannot be an arbitrary precomputed byte string: its actual effect
digest/time follow mutation and verification. The allowed derivation must be fixed
and source-bound, with actual resulting witness and entire write set validated.
This grants no caller choice over witness, manifest, alternate target/transaction,
another decision, another operator or a broader writer action. No arbitrary SQL,
cursor/connection access, DDL, commit/rollback, lifecycle repair or recovery method
can be exposed by the delegation.

## 4. Entitlement rule: necessary conditions versus missing permission

| Concept | What it establishes | What it cannot establish |
| --- | --- | --- |
| Identity | Which actor/runtime/decision is referenced | Permission to delegate target mutation |
| Authority | Exact originating owner consent and intended execution scope | Any new grant-right not defined by that authority's policy |
| Ownership | Genuine original process/thread/context and reserved resources | Broader action set than its authorizer/contract |
| Permission | An independently defined allowed target action for that source/owner | Cannot be inferred merely from successful checks or journal state |
| Delegation | A constrained derivation of an already-held target-action right | Cannot create the creator's missing permission, transfer ownership or extend scope/time |
| Execution | Actual use of a consumed local right under fresh current checks | Cannot be implied by an authority ID, journal append or witness |

Let C denote all current source/ownership/scope/security/deadline conditions in
sections 2 and 7. A valid rule would need **C AND an existing source-policy
grant-right for this exact action**. C alone is insufficient. The second operand
is not supplied by current contracts, so no positive entitlement can currently
be established. This is an absence of an authorization rule, not a new stored
`can_delegate` flag or a condition the caller may assert.

In particular `producer_ceremony.decision=authorize_runtime_execution` is necessary
original intent, not an automatic delegation API. Current code permits exact
issuance/attempt control writes, not this target mutation. Existing writer leases
bind distinct legacy/local/disposable claim semantics. Neither can be extended
by treating a future design aspiration as already approved action entitlement.

## 5. Non-transferability requirements and proof boundary

| Transfer attempt | Required rejection |
| --- | --- |
| Another process/restart | Original private registry, outer, issuance/continuation and live object identities are absent; matching IDs/PID/profile cannot recreate them |
| Another thread | Exact original Thread/identifier and current owner lifetime mismatch |
| Another runtime/activation incarnation | Fresh exact enrolled profile/generation/binding and independent activation comparison rejects |
| Another connection/transaction/reservation | Exact object/open transaction/mode/epoch differs; old delegation invalidated, not rebound |
| Another ceremony/operator | Original actor, credentials/MFA/consent and private owner binding differ; fresh login does not adopt old permission |
| Another decision or copied authority identifier | Exact D, operation/manifest/target/consent binding and original source registry fail; body lookup does not issue a local object |

An eventual delegation must be opaque/nonserializable and privately registered,
with no public construction/import/copy/restore or portable material. These
mechanisms can enforce locality under the existing trusted-code/host model;
PID/thread equality alone cannot. They are not cryptographic protection against
arbitrary host/code compromise. No actual delegation registry currently exists,
and non-transferability requirements do not themselves supply creation permission.

## 6. Single-use and duplicate fencing

First use must consume the private local right before its only fixed mutation
invocation. Consumption cannot be undone if the invocation fails before DML,
rolls back, commits, loses connection or becomes uncertain. Concurrent local use
must have one winner under genuine manager ownership; a Python-only flag is not
the cross-process duplicate fence.

Durable logical fencing is Z30/Z31's exact D/body digest plus installation/target/
operation and manifest exclusion, one confirmed pending start and one unique
target witness atomic with effects. Current source authority/attempt/entry/legacy
and business-family conflicts remain exclusions. Journal schema is inert/not
installed; its definitions supply no live permit or proof a producer enforced it.

Competing processes/ceremonies serialize control before target and revalidate
current scope after waiting. Pending start is never reissued. Confirmed failure,
success, uncertainty, new session/request/profile/generation IDs and process
restart cannot release the same logical-operation/manifest fence. Retries of a
consumed action reject; exact terminal state may be inspected as historical facts
only. No expiry-driven deletion, update/replace, retry loop or automatic recovery.

## 7. Atomic effect/witness action and immediate invalidation checks

Before any mutation, a future already-entitled creator/consumer must independently
validate all current source credentials/consent, exact operation/manifest and
proposal/ACK/effective approval, enrolled profile/generation/owner/auth/MFA scope,
activation, physical identity/schema/fingerprint, emergency stop/blocks, dependencies/
whole-population preconditions, current claim/history/control/migration integrity,
protected readiness, original owner/reservations and all deadlines. No reusable
cross-context evidence or generic validation callback supplies those decisions.

Inside one target transaction, preserve the existing whole-population family
semantics: prewrite manifest regeneration/equality; exact historical rule/operation/
family effects; complete actual-record/accounting checks; one internally derived
D/pending/effect witness; actual complete write-set and required fresh precommit
checks; manager commit. Existing matching shared rule rows need not be rewritten.
Target effect and witness cannot be separately committed or repaired afterward.

Existing family correctness is defined in `permanent.py`; unleased `finalize()`
owns commit, and its existing lease path accepts different authority. Neither
can be invoked through a fabricated context to supply this transaction. SQLite
local atomicity is possible, but the **source-policy entitlement to originate
this target-action delegation remains UNRESOLVED**. No new SQL/mutation mechanism
or privilege is invented. Later corresponding control outcome remains a separate
transaction, not cross-database atomicity.

| Invalidation | Required check/action at grant/use and required final boundaries |
| --- | --- |
| Authority expiry or any earlier deadline | Current paired clock; equality expired, no reissue/restamp/renewal |
| Authentication revocation/owner/auth/MFA change | Fresh genuine current reader/scope; reject and invalidate local right |
| Activation change/reactivation | Exact current incarnation/sequence/digest; reject even if other values match |
| Emergency stop/set-clear history or block | Current authoritative state/exact bound history; no stale clear flag |
| Approval/ACK revocation or mismatch | Current effective approval and complete exact pairing; no regeneration |
| Reservation/connection/mode/epoch loss | Original manager ownership fails; no transfer/rebinding to another transaction |
| Dependency/population change | Current required recheck and whole-manifest equality before effects; exact actual effects verified after |
| Physical identity/schema change | Actual strict observations at every required boundary; SQL locks do not provide filesystem continuity |
| Claim/history/control/migration change | Current graph/exclusions/baselines and actual permitted write proof; no cached allow decision |
| Transaction completion, failure, uncertainty or owner exit | Local right ends permanently; known uncommitted rollback only; retain durable exclusions |

No universal revocation event source is assumed. Mutable conditions must be freshly
checked by the original owner at execution-time/use/precommit boundaries, not
only at delegation construction. Actual committed facts are not erased by later
expiry/revocation; they require non-executable outcome inspection. No guarantee
of canceling an in-flight SQLite commit exactly at a deadline is invented.

## 8. Crash and uncertain-commit matrix

| Point | Delegation | Target effect | Witness | Recovery |
| --- | --- | --- | --- | --- |
| Before delegation | No mutation right created | None from this action | None | Existing source history inspectable; no implicit grant |
| After delegation | Hypothetical original local right lost on crash; cannot be recreated | None or not yet started | None | Original private identity cannot be adopted |
| Before mutation | Consumed/start may already be spent | No known committed effects | None | Keep durable exclusion; no retry from lost output |
| During mutation | Permanently consumed/lost | Uncommitted effects in original transaction unless commit actually occurs | Absent or uncommitted | Known rollback only; inspect durable outcome, never guess |
| After effect before witness | Consumed/lost | Must remain uncommitted | Absent | Commit forbidden; rollback known work; unknown status stays excluded |
| After target commit | Consumed/closed | Complete effects may be durable | Must be durable in same transaction for a valid positive outcome | Verify exact target witness/full effects/D/lineage; never repeat action |
| Before control outcome | No reusable right survives | Target may be committed despite control pending | Positive durable proof may exist | Authenticated factual recording only; missing control result is not retry permission |

On uncertain commit publish no usable execution result. A separately authenticated
outcome-only inspector may validate exact target/control identity/restore lineage,
D/source/pending, durable witness and complete actual records. Positive proof
can support factual control completion; only positive original-manager no-commit
evidence can support failure. Missing row, no response, expired source or process
exit is not that proof. Retain UNKNOWN indefinitely when evidence conflicts or is
unavailable. Recovery can never issue a fresh mutation right from old delegation,
state, witness or copied identifiers. No new same-operation/manifest D bypass.

## 9. Security separation

```text
delegation != original authority
delegation != general writer capability
delegation != reusable execution authority
delegation != target witness
delegation != journal state
recovery != reauthorization
```

Any valid future delegation would only narrow an already-held action; it cannot
broaden the original source, create a new general authority class, mint a successor
grant or extend time. A journal/witness records history or excludes duplicates;
it does not originate permission. Recovered positive attestation remains an
outcome fact, not a callable action. No browser/CLI flag, fixture or provider
callback is accepted as the missing policy entitlement.

## 10. Minimum auditability relationship

An auditor must be able to resolve the original source authority ID/body digest,
exact original consent and source audit; exact logical operation/manifest and
approval/ACK/current-at-authorization scope; exact journal decision/pending event;
actual target witness and verified effect digest; and matching control outcome/
audit references. Z31's witness already embeds the decision and pending data;
do not duplicate whole approvals/profiles/credentials or create another durable
delegation UUID merely for correlation.

The prospective delegation is local and nonserializable. Audit linkage must
describe the exact exercised action through D and journal/witness/event digests,
not serialize its live object, secret credentials, PID or connection handle.
General audit is append-only and must be atomically linked with the relevant
control transition, without pretending to share target's commit.

Current source audit can show owner intent and issuance. It **cannot currently
answer the stronger question “which approved source-policy grant-right entitled
this exact family-effect-plus-witness delegation?”** because that rule is absent.
No invented audit action, boolean or self-issued grant record can fill it. Until
that entitlement exists, an auditor must reject a claim of delegated target
authorization even if all source IDs and effect hashes are internally consistent.

## 11. Existing-model assessment B

**B: one specific missing primitive is the source-authority grant-right policy
for the exact original-runtime target action.** It must establish entitlement
without deriving it from identity, successful checks, reservation ownership or
journal/witness correlation. Existing authority describes scoped runtime execution
intent and future writer constraints, but does not fully define this delegation
entitlement for the replacement action under unchanged producer/owner contracts.

This is not a claim that restricted internal delegation is inherently impossible
(C), nor that it requires another general authority class. It is the specific
absence of an approved grant-right from the existing model. The necessary safety
conditions above cannot turn that absent right into an existing one (A).

## 12. Stop and validation

**Stop the architectural chain.** No next optimization, implementation slice,
permit, delegator/executor, schema/migration, writer change or lifecycle measurement
is proposed. No delegation or target privilege is approved by this document.

Only this document is created. Validate `git diff --check` and document whitespace/
local links. No pytest, Z18, T, broad suite, code/schema/migration, target DML/DDL,
delegation/mutation grant, executor, production/hosted access, commit or push.
Existing authority semantics and the 120-second ceiling remain unchanged.

## 13. Production blocks

PRODUCTION AUTHORIZATION: BLOCKED

PRODUCTION EXECUTION: BLOCKED

PRODUCTION ACTIVATION: BLOCKED

WRITER CAPABILITY: BLOCKED
