# 4e-20-R17 - finalization security-authority contract design

## 1. R16 baseline and disposition

[R16](recognition-runtime-security-finalization-authority-decision-4e-20-R16.md)
authorizes design of the missing authenticated governance-to-finalization-action
entitlement only. It grants no runtime right, producer appointment or changed
lifetime. [R15](recognition-runtime-security-finalization-ownership-write-set-contract-4e-20-R15.md)
also leaves complete effect proof and cross-database atomicity unresolved.

**Recommendation D - INSUFFICIENT EVIDENCE.** The required subject, constraints
and bindings can be specified below, but the authenticated issuer bridge and
enforceable complete-action protocol cannot be established from current contracts.
This is not an implementation-ready authority. The separate atomicity gap is
real; selecting C alone would obscure that authority authenticity remains
unresolved even if split control/target outcomes were explicitly accepted.

## 2. Authority subject and exact action

The sole candidate holder is the **genuine original holder** of one confirmed
prospectively eligible source authority. A constrained producer establishes
issue-time eligibility; it is not a second holder or an executor allowed to take
over. An internal transaction owner may exercise only the same original holder's
fixed action under its live original registration. No service identity or other
operator inherits this right from governance approval or a matching database row.

Required action: one complete supported historical First Look **or** Geography
family effect for the exact approved private manifest, verified and committed
with the exact decision-bound target witness. Bind to D = original `authority_id`
and canonical authority-body digest, exact runtime operation/digest, private
manifest digest, target/installation/family, original actor/runtime incarnation,
profile/generation/owner/auth/MFA scope, activation and applicable adopted policy.
One fixed write-set contract must identify the complete action, not caller SQL.

No other target, decision, operation, population, evaluation, witness or transaction
is permitted. No arbitrary write, partial effect, transfer, re-delegation,
renewal or retry is permitted. The exact effect-proof contract remains incomplete
under [G5](recognition-runtime-original-holder-atomic-enforcer-implementation-design-4e-20-G5.md);
its identity cannot be replaced with an invented digest and declared authoritative.

## 3. Issuance authority and governance bridge

Required issue-time chain, with every link independently established:

1. Verified project-owner governance mandate within its exact scope.
2. Authenticated, separately attributable prospective adoption of exact policy/action.
3. Authenticated constrained producer appointment under that adoption.
4. That actual appointed producer's protected original issuance with fresh
   action-specific consent, original credentials and exact source eligibility.
5. Confirmed durable issuance/audit and required cleanup before original-holder
   publication; later runtime execution remains separately validated.

[G13](recognition-runtime-g1-formal-governance-mandate-4e-20-G13.md) establishes
the documentary governance basis for exact G2 policy adoption and one constrained
producer appointment. It does not appoint that producer or authenticate its
machine transaction. Its exact policy descriptor remains v1/120-bound. Existing
v2 representation is not a new G1 policy authorization.

[G17](recognition-runtime-g1-protected-governance-owner-binding-contract-4e-20-G17.md)
leaves the executable bridge unresolved: how the protected manager independently
authenticates that the actual project owner approved the exact typed transition,
complete subject, effective scope, permitted write group and expected predecessor/
audit head. Existing admin credentials and runtime consent authenticate other
scopes; no role equivalence, incoming callback, signature system, new key, service
account or login route is assumed to supply the missing proof.

Therefore no actual issuer of this new authority is established. The required
producer is a future constrained appointment, not a producer selected by R17.
Mandate, policy adoption, appointment, authority issuance and runtime execution
remain distinct. Authenticity uncertainty at any link prevents issuance/use.

## 4. Immutable issue-time bindings

This is a logical binding inventory, **not** a new JSON format, schema, codec or
additional fields in an existing authority. Canonical serialization and `digest()`
rules must be used by a future separately reviewed representation. Existing full
authoritative records must resolve every reference; caller hashes alone are not proof.

| Binding | Required source and meaning |
| --- | --- |
| Policy/version and action | Exact adopted G2 descriptor/digest, effective before original action-specific consent and source issuance; no latest-policy substitution. |
| Decision D | Original canonical source ID/body digest and validated genesis/audit graph; no independent execution identity. |
| Original holder | Original authenticated actor/credential scope plus genuine private issuance registration. PID/live Thread/context/runtime provenance is checked locally, not persisted as authentication. |
| Target/family/operation | Exact enrolled target/control identity, installation, family/rule/population and operation/private manifest references, not caller replacements. |
| Write set | Full approved effect contract plus exact manifest and witness derivation obligations; complete proof is still unresolved, so no invented write-set format is specified. |
| Producer | Exact actual appointment identity/scope and genuine source context, attributable to independently authenticated approval. |
| Issue time and expiry | Actual original issue event, immutable canonical timestamps, original source/credential/consent bounds; no publication-time restamping. |
| Credential binding | Original primary/session/runtime-auth references, owner/auth/MFA scope and original deadlines; no tokens, TOTP or key contents. |
| Governance/appointment evidence | Full resolvable mandate, adoption, appointment, consent and issue-time eligibility provenance, ordering and audit linkage. |

Current revocation, live reservation, changing history/control state and current
physical observations must be checked at use, not frozen into an evergreen allow
flag. Any digest/projection must agree with the full authoritative subject.
Existing authorities gain no rights by later adoption or matching bindings.

## 5. Lifetime semantics

No independent numerical lifetime is selected. Under the original-holder candidate,
validity cannot begin before genuine issuance or survive original source expiry,
original credentials/consent, context closure, invalidation or spending. A candidate
expiry must be no later than the minimum of all original applicable deadlines.
The authority's own policy is immutable; current defaults never reinterpret it.

v1 remains 120 seconds and v2 remains 300 seconds under their existing meanings;
ordinary/default issuance remains v1. G2/G13 eligibility is not broadened to v2.
If a separate action lifetime or a source-window extension is needed, its start,
ceiling, clipping and applicability are **UNRESOLVED future security decisions**.
No new duration, second ceremony, renewal or independent clock is authorized.
Freshness must hold at every required final validation/commit boundary; neither
preparation nor elapsed time spent validating creates an expiry exception.

## 6. Single-use, fencing and complete write set

Private original-holder registration must be process/Thread/context/runtime and
resource-bound, opaque, nonserializable and non-adoptable. A single-use in-memory
flag alone is insufficient. Durable decision/operation/manifest exclusions, one
confirmed start, target constraints and exact witness correlation must prevent
concurrent owners, a new D retrying an excluded action, replay and uncertain-outcome
re-execution. Failed or uncertain use cannot restore the spent opportunity.

The request's "R30" identity requirement is the inspected
[Z30 decision-bound journal contract](recognition-runtime-decision-bound-outcome-journal-contract-4e-20-Z30.md).
No separate R30 artifact was identified. D remains the sole decision identity;
event/pending/witness digests name correlated facts, not new executable decisions.

| Required effect | Binding and transaction status |
| --- | --- |
| Source/consent/genesis/audit | Existing complete issuance group; no hidden eligibility writes added to its fixed mutation proof. |
| Attempt/history/creation audit | Existing committed coordinator group; replacement placement is unresolved and cannot simply be omitted. |
| Target-entry metadata | Existing separate protected metadata operation; neither entitlement nor business effect. Inclusion/replacement requires explicit contract, not a performance shortcut. |
| Rule and private operation | Exact rule verification or missing-rule INSERT, private manifest operation INSERT and operation/manifest exclusion. |
| First Look effects | Every exact `recognition_first_look_claims` candidate after complete historical regeneration and competitor checks. |
| Geography effects | Complete scope identities, snapshots, members, awards and supporting geography witnesses for the approved manifest. |
| Decision-bound target witness | Derived from verified actual complete effects and exact D/pending; must commit with all family effects. Family geography witnesses do not replace it. |
| Decision/start/duplicate fence and outcome journal | Separate immutable control decision/history/audit and exact target witness under Z30. A journal row is not permission. |
| Control/audit outcome | Correlated positive target evidence or positive no-commit evidence; not inferred from missing target/control rows. |
| Reservations/epochs/modes | Live manager-owned state, not atomically persisted authority; transitions invalidate borrowed views and require checks. |

The actual family INSERT block in
[`permanent.finalize()`](../src/review/recognition/permanent.py) is coupled to its
historical authorization and transaction owner. It is not an existing runtime
mutation API. Legacy claim/EXECUTING fabrication or writer-boundary widening is
prohibited. Complete effect extraction/proof remains a prerequisite, not an
implementation detail selected here.

## 7. Fresh validation immediately before action

| Fact | Why fresh / required authoritative validation |
| --- | --- |
| Authority/credentials/consent | Current original registration, full source/eligibility/audit graph, original auth/MFA scope, revocation, action-specific consent and all deadlines. |
| D and exact write set | Resolve canonical source, operation, approved manifest/population and pending; regenerate family preconditions and compare complete actual action. |
| Target and ownership | Actual physical/schema/fingerprint identity, installation/profile/generation/owner, activation incarnation and original runtime; SQL reservations do not prove filesystem continuity. |
| Duplicate state | Current permanent exclusions, sole pending/head, absence of conflicting committed effects/witness, no prior spend or unknown outcome. |
| Concurrency/resources | Actual manager connections/transactions/reservations/epochs/query modes, control-before-target ordering and owner lifetime. Reacquisition is not continuation by assertion. |
| Target state | Full candidate/competitor/claim/scope/member preconditions under the target transaction; actual effect verification before witness/commit. |
| Policy/version and appointment | Exact prospective adoption and source applicability, authentic current policy state, appointment validity where required; unknown/revoked applicability rejects. |
| Other current eligibility | Approval/proposal/ACK, stop, dependencies/readiness, current claim/history/control integrity and migration relationships through existing authoritative kernels. |

Preparation may describe intended action; it cannot replace any required fresh
allow decision. Only existing Z15 schema inventory may be reused within its exact
approved continuity scope. The new contract establishes no broader cache or
cross-phase reuse and makes no performance claim within 120 or 300 seconds.

## 8. Crash and uncertainty protocol

| Event | Authority / result rule |
| --- | --- |
| Pre-execution crash | Original live registration is lost; durable authority or preparation cannot recreate it after restart. No automatic adoption. |
| Transaction failure | Known uncommitted work rolls back as a complete group; original opportunity is not renewed. Rollback uncertainty is unknown, not known failure. |
| Commit ambiguity | Publish no usable result; stop for independently authorized read-only durable inspection. Never infer rollback from timeout or missing control outcome. |
| Post-commit response loss | Historical D/witness/full-effects/control inspection may establish facts, but cannot recreate a capability or authorize replay. |
| Duplicate retry | Reject mutation, even after known failure or lost response; inspection returns data only. |
| Producer crash | No replacement producer/holder acquires the original right. Partial source/control prefixes must remain fail-closed under the exact future producer protocol. |

The inert
[`runtime_decision_outcome_journal_schema`](../src/review/recognition/runtime_decision_outcome_journal_schema.py)
validates canonical DATA and permitted historical transitions. It does not open
connections, install storage, authenticate producers, prove effects or issue
authority. Inspection must validate committed target evidence and exact D/pending,
not detached witness bytes. Unknown facts remain blocked; recovery is not reauthorization.

## 9. Revocation and role separation

[G16](recognition-runtime-g1-adoption-producer-authoritative-storage-protocol-4e-20-G16.md)
and G13 permit the same project-owner governance authority to revoke/supersede
within its mandate through explicit attributable immutable decisions identifying
scope, original identities and effective ordering/time. No runtime or producer
receives that power. Evidence must resolve the full authorized transition and
audit lineage; absence of a revocation record alone is insufficient under uncertainty.

Appointment revocation/expiry denies future eligibility production, not automatic
retroactive rewriting of issued sources. Mandate revocation stops new governance
decisions; effects on existing adoption/appointments must be explicit. Existing
current policy revocation and independent source/authentication/activation/scope
checks remain mandatory. No completed target effect is retroactively undone.

At every required fresh check, a currently effective applicable revocation denies
use. Exact serialization of revocation versus in-flight finalization/commit remains
**UNRESOLVED** in the executable producer/finalizer contract. No cancellation
guarantee during irreversible commit or retrospective mutation right is invented.
Stale/ambiguous revocation applicability blocks publication/use and requires inspection.

Governance authority is not producer appointment; appointment is not finalization
authority; finalization authority is not arbitrary target mutation authority.
G13 permits the same project owner to approve adoption and appointment separately
without a second person's approval. It does not permit runtime self-appointment
or collapse those decisions. No additional role overlap for producer/executor is
approved: any proposed overlap requires an explicit separation/risk decision.

## 10. Threat analysis

| Threat | Required mitigation / remaining gap |
| --- | --- |
| Confused deputy / privilege escalation | Fixed complete action, no caller SQL/target, authentic exact approvals; missing governance bridge prevents claiming enforcement. |
| Replay / authority substitution | Original private holder plus canonical source/digest and permanent exclusions; copied data cannot construct permission. |
| Producer impersonation | Independently authenticated appointment and actual protected issuance context; authenticity mechanism unresolved. |
| Target / decision substitution | Full scope/manifest/D/pending equality and fresh actual target identity, not digest-only caller claims. |
| Stale consent | Original current consent/deadlines and issue-time policy ordering; no renewal or retrospective eligibility. |
| Duplicate / concurrent execution | Durable one-start and operation/manifest fences plus target uniqueness under real reservations; in-memory flags alone insufficient. |
| Partial commit | Complete family effects and witness in one target transaction with actual-effect proof; complete proof remains unresolved. |
| Cross-database inconsistency | Z30 correlation and fail-closed uncertainty, not asserted atomicity. Combined transaction requirement remains unresolved. |
| Crash / uncertain outcome | No usable publication, retry or adoption; independently authorized factual inspection only. |

## 11. Options A-D

| Option | Authority / governance dependency | Implementation dependency | Atomicity and crash status | Unresolved assumption |
| --- | --- | --- | --- | --- |
| A - original-holder-only finalization | Narrow G2 prospective original eligibility with authentic adoption/appointment | Protected source bridge, genuine private owner and complete action proof | Target-local effects/witness possible; split control outcome, no restart adoption | Issuer authenticity and exact producer protocol not established. |
| B - constrained producer acting for holder | Would require an explicit authenticated agency/delegation right, not governance identity alone | New principal-to-original-holder binding and permitted exercise protocol | Same atomicity gap; producer crash cannot transfer original right | Existing original-holder-only rule does not authorize a separate actor to execute. |
| C - appointed transaction-owning executor | Appointment is not itself source grant-right or target entitlement | New explicitly reviewed executor/holder relationship and action proof | Transaction ownership does not fuse target/control commits; no recovery right | Independent executor permission and transfer compatibility absent. |
| D - another repository-supported model | Legacy/local writer and read-only/metadata owners have different narrow rights | Cannot forge claims, widen owner type or promote read-only capability | Existing models' own crash/fences remain unchanged | No inspected supported replacement expresses this new action entitlement. |

Only A matches the minimum original-holder constraint as a candidate. That is
not a readiness decision or a new permission grant.

## 12. Recommendation, atomicity status and stop

Minimum requirement remains one principal, one D, one action, one target/family,
one complete write set, one bounded immutable interval and at most one execution:
no transfer, re-delegation, renewal or retry authorization.

**D - INSUFFICIENT EVIDENCE.** Existing model does not supply the new right (A);
issuer authenticity, complete proof, revocation ordering and enforceable source
protocol are insufficiently specified for implementation design (B). C correctly
identifies the independent atomicity obstacle, but is not the sole reason this
authority contract is incomplete.

Target effects plus decision witness must commit atomically in the target.
Attempt/history, decision/start fences and control/audit outcome occupy separate
control transactions under Z30 and current ownership contracts. No combined
cross-database atomicity is established. Accepting a split factual outcome or
requiring a different storage/transaction model is a separate unresolved decision;
this document makes neither choice and introduces no ATTACH or storage workaround.

Stop. The next boundary is a separately authorized security decision resolving
the authenticated exact-action governance-to-producer bridge and, independently,
the required target/control atomicity semantics. A separate action lifetime, if
needed, also requires explicit approval; none is inferred. No numbered follow-on
implementation, new performance investigation, producer or G-series continuation
is authorized. R17 supplies requirements and identified gaps, not an executable
contract or evidence that any proposed ceremony will fit the existing ceiling.

## 13. Validation and production blocks

Only this document is added. Read-only R16/R15, G13/G17/G16, G5, actual authority
issuer and inert journal definitions were inspected. Document whitespace/local-link
checks and `git diff --check` passed. No pytest, lifecycle, Z18, T, broad suite,
code, schema, policy, permissions, migration, authority issuance, producer
appointment, target change or production/hosted access. No commit or push.

PRODUCTION AUTHORIZATION: BLOCKED

PRODUCTION EXECUTION: BLOCKED

PRODUCTION ACTIVATION: BLOCKED
