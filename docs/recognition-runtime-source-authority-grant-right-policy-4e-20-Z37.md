# 4e-20-Z37: source-authority grant-right policy proposal

## 1. Z36 blocker and decision

[Z36](recognition-runtime-original-authority-target-action-delegation-contract-4e-20-Z36.md)
found no existing policy entitling the original runtime authority holder to
delegate the exact family-effect-plus-witness target action.

**Assessment B: one specific new grant-right policy is required.** This document
defines that proposed policy explicitly below. It is not a claim that the existing
authority model already contains it (A), nor a claim that restricted delegation is
inherently impossible (C). Its proposed name is **original-source exact-family-
witness grant-right policy, version 1**; this is a policy label, not a new codec,
schema column, capability type, configuration switch or activation mechanism.

The policy adds a deliberate prospective entitlement rule. It is not inferred
from ownership or by reinterpreting old consent/authority rows. No implementation,
policy adoption by a running deployment, authority-code change, mutation grant,
target privilege, schema/migration or executor is performed or authorized here.
The 120-second ceiling remains unchanged. No performance investigation or claim.

## 2. Exact candidate source authority

Only an activation-bound source of type
`recognition-runtime-execution-authority-v1` could be eligible. It must have been
newly originated **under this expressly adopted prospective policy**, with valid
source-policy provenance and original explicit owner consent as specified below.
No existing authority is grandfathered in by age, matching format, same IDs or
successful inspection.

| Source element | Required authoritative meaning |
| --- | --- |
| Authority ID/body digest | Exact canonical immutable source; D is `(authority_id, digest(body))`; complete confirmed source/genesis/audit and original creation provenance |
| Authority scope/operation | Exact operation UUID/digest, event/preparation, family, manifest/population, proposal reference and supported atomic historical finalize action |
| Target/scope | Exact enrolled actual target/control observations/schema/fingerprint and runtime target installation/target UUID/generation/binding/owner/auth/MFA scope |
| Authentication | Genuine current original owner primary/session and runtime-auth links, access, MFA enrollment/epochs, revocation and all expiry bounds |
| Consent | Original protected TOTP/step/one-use confirmation for the exact current execution subject, explicit reason and decision; no reused approval/activation consent or generic flag |
| Approval/ACK | Exact acknowledged proposal and effective approved state/history, with current invalidation checks |
| Activation | Exact independently verified current incarnation/sequence/digest bound to source authority |
| Profile/incarnation | Finalized G+2 profile/generation/binding and actual runtime identities, not a caller-declared host/process |
| Reservation | Genuine original manager's exact connections/transactions/modes/epochs, control before target, target retained through required control commits |
| Deadline | Actual source issue time, at most 120 seconds and clipped by original credentials/consent; current paired clock strictly before all bounds |
| Original owner | Exact private original outer/context/issuance/continuation registration, active original PID/Thread/identifier and lifetime |
| Existing delegation permission | **None currently defined for the exact replacement action.** The rule in section 4 would be the new source of entitlement, not a finding that existing code grants it |

Sources inspected:
[`runtime_activation_authority_schema.py`](../src/review/recognition/runtime_activation_authority_schema.py),
[`runtime_activation_authority_issuance.py`](../src/review/recognition/runtime_activation_authority_issuance.py),
[`runtime_execution_coordinator.py`](../src/review/recognition/runtime_execution_coordinator.py)
and [4e-11](recognition-runtime-activation-bound-authority-contract-4e-11.md).

## 3. Exact grant-right semantics

The proposed right is **one original-holder-only permission to issue one internal
action grant**, not permission to mutate directly. The action grant, if separately
implemented and admitted, may cover only:

```text
one original source authority and execution decision D
  -> one exact supported historical family finalize effect set
  -> one exact enrolled target and original runtime scope
  -> one internally derived Z31 decision/pending/effect-bound witness
  -> one atomic target mutation transaction
```

The family effect is existing First Look or Geography behavior, including its
whole-population preconditions, fixed rule/operation/supporting/family records and
complete outcome verification. No corrections/discrepancies, active capture,
Explorer/review/source mutation, changed evaluation, per-item quarantine, arbitrary
SQL or another business action is included. Existing matching shared rule records
need not be rewritten. See
[Z33 effect inventory](recognition-runtime-target-effect-witness-authorization-contract-4e-20-Z33.md).

The witness derivation is fixed, not caller-selected: unchanged Z31 shape with the
same decision and confirmed unique pending event, actual verified effect evidence
digest and recorded time inside the original authority window. Its byte digest
cannot be asserted in advance of actual effects/time. Exact result and whole write
set must be verified before commit and independently after commit.

The right permits neither arbitrary target writes nor another D/target/operation/
witness/transaction, another operator/process/ceremony, general writer access,
authority renewal, grant of the right itself, or control-journal/recovery privilege.

## 4. New delegation entitlement rule

**Normative proposed rule G1:** a newly issued eligible original source authority
may issue exactly one non-transferable internal action grant for section 3 **if
and only if all** the following conditions hold:

1. **Prospective policy authority:** this exact policy has been explicitly adopted
   for the source issuer before the source decision/consent was originated. The
   original authenticated owner is informed that the execution decision permits
   precisely the existing atomic family effect and its inseparable outcome witness.
   This is not silent compatibility with prior authority or consent.
2. **Issue-time binding:** immutable original issuance provenance binds D to this
   exact policy version and exact action restriction. A later append, runtime
   boolean, operator claim, environment setting or metadata lookup cannot add the
   right to an older source. Absence/conflict of that provenance denies entitlement.
3. **Genuine original holder:** the exercising owner is the same live registered
   original authority owner, not an imported authority, inspection object, recovered
   attempt, delegated permit, new session/ceremony or another runtime.
4. **Exact action restriction:** all D/operation/family/population/target/profile/
   activation/owner/auth/consent/approval/ACK bindings in sections 2, 3 and 6 match
   authoritative current state. No argument supplied by the applicant is a replacement.
5. **Fresh independent gates:** every condition in section 7 is satisfied at actual
   exercise. Current consent, authentication, scope and reservation validity are
   necessary prerequisites, not the source of this grant-right policy.
6. **Permanent single-exercise fence:** the logical decision/operation/manifest
   has no conflicting old/new authority, claim, attempt, entry, effect or outcome.
   The unique journal start must be confirmed under serialized control ownership
   before any action grant is usable. A second grant construction/use is denied
   even if the first construction failed or never produced target DML.
7. **No escalation:** the resulting action grant is narrower than its source,
   expires no later, authorizes no re-delegation and is bound to one actual
   original-owner target connection/transaction/reservation lifetime.
8. **Failure discipline:** unknown exercise/commit/cleanup outcome poisons live
   use, publishes no usable permission/result, retains the durable exclusion,
   and cannot be converted to a new grant by retry, recovery or fresh authentication.

**Why the source may delegate under G1:** because the explicitly adopted source
policy confers that one narrowly defined issuance entitlement on the original
source at its creation. Identity, ownership, consent, reservations and digests
restrict its exercise; they do not create the entitlement. G1 is the proposed
new security rule, not another inference from a successful validator.

This policy cannot be enforced by today's existing schema/producer/authorizers.
Exact prospective-policy provenance encoding and consent/issuer enforcement would
need separately approved representation/integration; this document neither adds
fields to existing typed source audit bodies nor invents a policy-binding event.
That is an implementation/representation limit of the proposed new policy, not
permission to treat missing provenance as true. All existing sources remain
ineligible for G1 under current code and current authority semantics.

```text
identity != ownership != consent != reservation != authority != grant right
```

## 5. Grant-of-grant prohibition

Only the original source can exercise G1, through its genuine original owner,
once. The action grant carries **zero grant-rights**. It cannot issue a successor
permit, narrow-copy itself, transfer to another connection/context, or create a
grant after rollback. No recursive delegation, subdelegation, cross-ceremony grant,
adoption or recovery reissuance is allowed. A source cannot delegate G1 itself,
even to the same actor on the same host. Matching scope does not create a new
original source.

## 6. Exact action binding at exercise

| Binding | Must be established before exercise? | Required source |
| --- | --- | --- |
| D/source policy | YES | Exact confirmed canonical source plus original issue-time G1 policy provenance |
| Operation/manifest/family/population | YES | Current durable operation, frozen event/preparation and complete manifest/reference equality |
| Target | YES | Actual enrolled target/control observations/schema and installation/target UUID |
| Runtime incarnation | YES | Exact original private owner, current G+2 profile/generation/binding/epochs and independent activation incarnation |
| Reservation/transaction | YES | Actual original manager-owned target connection/open transaction/query mode/epoch after required fresh checks |
| Approval/ACK/consent | YES | Exact current authoritative pairing/effective history and original one-use source consent |
| Witness | YES as an exact derivation constraint, not an arbitrary future digest | Same source decision/pending plus complete actual effect evidence and bounded actual recorded time |
| Deadline/single use | YES | Original clock/deadlines, unused original local exercise path and exact confirmed permanent journal start/exclusions |

Actual effects and witness must later match that constraint inside the one target
transaction. A caller cannot preselect an evidence digest to evade full verification.
Control commits never release the target reservation before required confirmation.
If phases release reservations, reacquire control before target, revalidate all
current predicates and bind the action grant to the new actual owned transaction;
never transfer a previously created action grant across that boundary.

## 7. Fresh security conditions

| Current condition at exercise/use | Required check |
| --- | --- |
| Authentication | Current owner primary/session/runtime-auth/MFA scope, access, revocation and expiry; source credentials cannot be swapped |
| Authority validity | Exact original confirmed source graph, original private owner, issue-time policy provenance, no effective invalidation or prior exercise |
| Activation/profile | Current exact independent incarnation, finalized G+2 generation/profile/binding/install/owner/auth/MFA epochs |
| Approval/ACK | Complete exact current proposal/ACK pairing and effective approval/invalidation state |
| Emergency stop | Current bound stop/block history; set-clear cannot silently revive old authority |
| Dependencies/family preconditions | Authoritative recheck and required whole-population manifest regeneration/equality |
| Physical identity | Actual strict host/resolved paths/devices/inodes/schema/fingerprint, not earlier cached observations |
| Claims/history | Current complete graph/disposition/exclusions and exact append-only source/journal/audit lineage |
| Control/schema/migrations/readiness | Protected state and required source/package/profile/migration relationships, FKs and protected readiness |
| Reservations | Actual original registrations/connections/transactions/modes/epochs; no caller lease or raw handle |
| Deadline | Existing authoritative paired clock, no rollback/anomaly, strictly before all original grant/auth/consent bounds |

The same mutable predicates remain current at action-grant use and all required
precommit/result boundaries. G1 does not authorize prepared complete admission,
cross-context schema inventory, mutable observation reuse, skipped post-write
integrity or physical continuity assumptions. Actual permitted changes require
complete actual-effect/write-set verification, not pretending source preconditions
were never changed by approved effects.

## 8. Revocation and invalidation

Effective source revocation/invalidation, auth/MFA revocation/epoch/access change,
activation change/reactivation, approval/ACK invalidation, emergency stop/block,
dependency change, physical identity/schema mismatch, profile/generation/binding/
owner change, unexpected claim/history/control/migration mutation, deadline or
source runtime termination denies G1 and invalidates pending local permissions.
Do not invent a new source-revocation table/flag; use independently authoritative
current conditions and existing invalidation rules, not a caller revocation claim.

Reservation/connection/transaction/mode/epoch loss invalidates the action grant.
Loss does not erase historical rights/decision records or reopen single-use state.
Every applicable invalidation must be checked immediately before target mutation
and at required final/use/commit boundaries. There is no universal event listener
or guarantee that a filesystem path cannot change between observations. Failure
rolls back only known uncommitted work, poisons local use and retains exclusion.

Restoring a prior apparently clear state never revives spent/expired/invalid old
authority; historical stop/activation/approval/epoch bindings must still match.
Already committed positive outcomes remain facts, not renewed permissions.

## 9. Non-transferability

The right has no standalone bearer representation. A policy ID, audit reference,
source body/digest, journal state or witness may be copied as historical DATA,
but cannot instantiate the original private live registry/issuance lineage.
Only the genuine original active holder may exercise G1 through a reviewed manager.

Another process/restart, Thread/context, runtime/profile/activation incarnation,
operator/credential/MFA linkage, ceremony, decision, target, connection or transaction
fails exact original/current checks. PID equality alone is insufficient; private
object/outer/phase lineage and actual owner resources are mandatory. No public
constructor/import/pickle/copy/provider callback can recreate a right or permit.

This is a policy requirement within the existing trusted-host/code integrity model,
not cryptographic resistance to arbitrary host compromise. No enforcement is
implemented in this slice. Current non-adoptable ownership patterns provide the
provenance foundation, but they do not make G1 already active or prove a nonexistent
grant registry is present.

## 10. Crash and uncertain-commit analysis

“Issuance” below distinguishes original source issuance from exercise issuing a
local action grant. Both must be confirmed before permission is usable.

| Point | Grant-right state under proposed G1 | Target effect | Witness | Recovery |
| --- | --- | --- | --- | --- |
| Before original issuance | No source G1 entitlement | None from this decision | None | No inferred right from consent/identity |
| After source issuance | Eligible only with exact prospective policy provenance and original live owner; not yet exercised | None known | None | A lost original lifetime cannot be reconstructed from durable source |
| After grant issuance / before mutation | Permanently exercised/spent; local permit valid only in exact original live transaction | None or not started | None | No replacement permit after crash or construction failure |
| During mutation | Spent; no other grant possible | Uncommitted whole population until actual commit | Absent or uncommitted | Roll back known uncommitted work; never infer committed outcome from process state |
| After effects before witness/commit | Spent | Effects must remain uncommitted | None/uncommitted | Commit prohibited without exact witness; unknown outcome remains blocked |
| After target commit | Spent/closed, not renewable | Positive complete effects may be durable | Must commit atomically with effects | Validate exact durable proof; no repeated execution |
| Before control outcome | Spent; no new right from missing completion | Target may be committed | May provide positive proof | Current authenticated factual recording only |
| After control outcome | No further exercise, regardless of remaining source time | Confirmed facts according to verified target evidence | Immutable outcome witness | Historical inspection; never restore original live result/permit |

Uncertain source/grant/journal/target/control commit or cleanup publishes no usable
permission/success and permits no blind retry. Keep permanent D/operation/manifest
exclusions. Current authenticated outcome-only inspection validates exact intended
identity/schema/restore lineage, source-policy/source/journal graph, witness and
complete actual effects. Positive proof can establish historical commit; only
positive original-manager no-commit evidence can establish failure. Absence of a
record/response, expired authority or process death cannot establish safe retry.
UNKNOWN may remain indefinitely. Recovery cannot acquire G1 by discovering an old
source, grant, journal or witness. New login or a new D does not bypass conflicts.

## 11. Duplicate and replay policy

G1 allows **one grant issuance attempt**, not repeated manufacture until one succeeds.
Local consumption begins before exposing or invoking the action grant. Its use
cannot be reset after no DML, known rollback, failed commit, success, uncertainty
or process restart. Durable journal unique decision/operation/manifest and pending
start fences must be confirmed before any grant is usable; a local flag alone
does not enforce cross-process single exercise.

Concurrent applications serialize through control ownership/expected head and
source/journal uniqueness. Target reservation and one unique D/operation/manifest
witness commit with whole effects as the independent target fence. Only the original
registered exercise may create its local grant; another process cannot inspect
pending and adopt the right. Target or control failure never releases exclusions.
No expiry/TTL deletion, UPDATE/DELETE/REPLACE, automatic recovery, checkpoint or
arbitrary retry loop is policy-authorized. Existing journal definitions remain
inert/not installed and do not themselves enforce live G1.

## 12. Security boundary

```text
grant right != mutation permit
grant right != writer capability
grant right != execution authority
grant right != recovery authority
grant right != target witness
grant right != journal state
```

G1 is the proposed entitlement to issue one narrow action grant. Possessing G1's
policy representation does not perform mutation. Only a separately implemented,
freshly admitted, exact original-owner action grant could exercise target writes.
G1 authorizes no journal/control repair, completion writer or resolver by itself.
Witness/outcome facts and factual recovery can never create or renew G1.

## 13. Existing-contract assessment B

No existing authority model contains this complete grant-right policy for the
exact replacement action. The necessary **new security contract is G1**, defined
in sections 3-11: prospective source-policy entitlement with explicit issue-time
provenance and informed exact owner consent, one original-holder-only grant
issuance attempt, exact fixed atomic family/witness action, all current independent
gates, no grant-of-grant/transfer/renewal/adoption and permanent no-retry fences.

This answers why delegation could be lawful after explicit policy adoption: the
source policy would confer that narrow right, rather than deriving it from a
copied ID or trusting the permit to justify its own creation. It does not declare
existing authorities eligible, silently broaden old consent or create a general
authority class. No claim of safe live enforcement follows until exact provenance,
owner permissions and target/effect/journal integration receive their own approval.

## 14. Stop and validation

Assessment B stops the architectural chain. **No next optimization or implementation
slice is proposed.** G1 is a defined prospective policy proposal, not authorization
to implement/adopt it, modify source authority, mint a permit or install a journal.
No new live entitlement is present in the repository because of this document.

Only this document is created. Validate `git diff --check` and document whitespace/
local links. No pytest, Z18, T, broad suite, code/schema/migration, policy/grant
implementation, target DML/DDL, writer capability, executor, production/hosted
access, commit or push. The original 120-second ceiling is unchanged.

## 15. Production blocks

PRODUCTION AUTHORIZATION: BLOCKED

PRODUCTION EXECUTION: BLOCKED

PRODUCTION ACTIVATION: BLOCKED

WRITER CAPABILITY: BLOCKED
