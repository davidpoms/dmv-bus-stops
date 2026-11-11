# 4e-20-R19 - governance decision on new finalization security primitives

## 1. R18 baseline and decision scope

[R18](recognition-runtime-security-finalization-unresolved-primitives-decision-4e-20-R18.md)
identifies three missing primitives: authenticated issuer bridge, authorized
complete-effect attestation, and revocation/finalization fencing. Cross-database
atomicity remains separately unresolved. None is operationally authorized.

**Decision A - AUTHORIZE ALL THREE NEW SECURITY PRIMITIVES, FOR DESIGN ONLY.**
This records the decision within the R19 request's explicit decision-making
scope: permit bounded investigation/design of all three related requirements,
not their operational introduction. It does not manufacture an approving actor,
authenticate a governance transaction or expand the G13 runtime mandate. No
implementation, permission change, appointment, issuance, activation or execution
is authorized. If a design cannot stay within these limits, it must stop.

## 2. Primitive A - authenticated issuer bridge

The design authority covers a protected bridge that independently verifies exact
project-owner approval of prospective policy adoption and a separate constrained
producer appointment, then permits only that appointed producer's protected
original issuance. The lawful documentary governance basis is
[G13](recognition-runtime-g1-formal-governance-mandate-4e-20-G13.md), verified under
G14; its exact G2 policy/action scope is controlling. No new human mandate or
additional approver is presumed necessary, and no runtime self-appointment is allowed.

| Term | Required design constraint; no operational grant is made |
| --- | --- |
| Issuer | One explicitly appointed constrained original source producer, independently authenticated in its exact protected context; no issuer is appointed here. |
| Recipient | Only the genuine original source holder, with original actor, credentials, runtime/process/Thread/context and resource ownership. No imported historical authority or separate service/executor. |
| Action | One supported historical First Look or Geography complete family-effect-plus-decision-witness action; no arbitrary SQL, other family or partial population. |
| Binding | Original D = authority ID/body digest; exact operation/private manifest/write-set contract, target/installation/family, profile/generation/owner/auth/MFA scope, activation and applicable adopted policy. |
| Validity | One immutable finite interval within all original source, credential and consent deadlines; no new numerical interval, renewed source or second ceremony is selected. |
| Evidence | Authentic full governance approval subject, mandate, exact adoption and distinct appointment, expected predecessor/audit head, original action-specific consent/eligibility, actual producer provenance, confirmed source/genesis/audit commit and cleanup. |
| Revocation | Applicable authoritative policy/source checks and appointment restrictions, separately ordered under primitive C; uncertain applicability denies. Appointment revocation does not silently rewrite issued sources. |
| Prohibitions | No transfer, re-delegation, renewal, retry authorization, producer self-appointment or automatic recovery-based eligibility. |

Project governance authority is not issuer authority, and issuer authority is
not runtime execution authority. Identity or possession of a source ID does
not establish any arrow between them. The design must resolve
[G17's authentication gap](recognition-runtime-g1-protected-governance-owner-binding-contract-4e-20-G17.md)
without assuming a new signing key, login, callback, service role or existing
admin session automatically authenticates the required governance action.

## 3. Primitive B - complete-effect/witness attestation

Design authority covers only an original-holder fixed-action transaction owner
that can attest actual complete effects, not an auditor that merely accepts a
supplied effect hash. Its actual entitlement depends on primitive A. No current
component is newly authorized to attest or mutate by this record.

Complete effect is the exact reviewed historical manifest regenerated under
target reservation and verified against actual records using the family rules
and integrity readers in
[`permanent.py`](../src/review/recognition/permanent.py):

- Exact rule verification or missing-rule insertion and canonical private operation.
- For First Look, the entire candidate claim set and its qualifier/competitor integrity.
- For Geography, full scope identities, snapshots, members, awards and supporting witnesses.
- Exact decision-bound outcome witness, distinct from family geography witnesses,
  derived from the complete actual-effect evidence and original D/pending.
- Proof that the transaction performed only the complete permitted write set,
  with no missing, extra, substituted or unrelated effects and valid foreign keys.

The full target family effect and decision witness must commit in one target
transaction. Exact before/after allowed-write proof and independent committed-
snapshot verification are mandatory. Existing integrity readers are foundations,
not a complete privileged producer/proof. No evidence codec or extra fields are
invented in this decision.

Target and control correlate through the same original D and sole pending/start
reference under [Z30](recognition-runtime-decision-bound-outcome-journal-contract-4e-20-Z30.md).
Event/witness hashes are facts under D, not independent execution identities.
An audit record, detached witness, staged INSERT or successful function return
does not prove business commit. Incomplete/contradictory effects deny and require
known-uncommitted rollback; unknown commit or unavailable inspection stays
uncertain. Later inspection may establish durable facts but cannot reauthorize
execution. No outcome-only recovery implementation is authorized.

## 4. Primitive C - revocation/finalization fencing

Design authority covers authoritative ordering of applicable revocation against
issuance, final validation, transaction mutation, commit and publication. It must
define effective/linearization points and prove all relevant producers participate.
Existing control reservations are a possible foundation, not proof of a universal
revocation protocol or immediate cancellation of irreversible commit.

Only the existing project-owner governance authority may revoke/supersede within
its mandate through explicit attributable immutable decisions. Runtime producers
gain no governance revocation power. Existing independently authorized credential,
source, activation and scope revocation mechanisms retain their scopes. Any new
revoker identity or broader revocation power needs separate explicit approval.

Revocation is forward enforcement, not undoing committed effects. Appointment
revocation denies future eligibility production; consequences for prior sources
cannot be inferred. Mandate revocation does not silently rewrite prior adoption
or appointment. Current effective policy/source disqualifiers must be observed
at every required fresh boundary, including immediately before commit.

Final validation must observe authoritative durable revocation state under the
approved fence/order. Effective revocation ordered before the protected action
must deny in-flight use; after confirmed commit it cannot roll back history or
release duplicate exclusions. The design must resolve the intervening race,
including committed revocation versus blocked/pending request, without promising
unsupported cancellation. Unknown ordering fails closed; it is not continued permission.

Concurrent finalization requires durable once-only decision/start and permanent
operation/manifest fences plus genuine reservation/transaction ownership. A
process-local flag or a bounded lifetime alone is insufficient. Post-commit
revocation/uncertainty may block usable publication; it does not imply no commit,
restore a spent opportunity or permit retry.

## 5. Cross-database atomicity: not authorized or solved here

Control holds original consent/authority/genesis/audit, attempt/history, decision/
start/exclusions, governance/authentication state and factual outcome/audit.
Target holds entry metadata, complete family business records and decision
witness. Original-holder registration/reservation state and response publication
also have process-local lifetimes rather than database atomicity.

Existing transactions provide local atomicity, not one commit across all those
domains. Holding both reservations does not fuse commits, and none of A/B/C does
so. A target commit followed by control uncertainty remains a possible durable
prefix under Z30, never proof of rollback or permission for another execution.

An additional explicit security/product decision is required: accept the split
factual-outcome protocol and its uncertainty semantics as satisfying the actual
requirement, or require a separately authorized atomic storage/transaction
boundary. This decision supplies neither an atomicity mechanism nor approval
to relax that requirement. Any such new primitive or changed storage semantics
requires its own governance/security authorization. No ATTACH, migration,
storage relocation or distributed commit design is approved here.

## 6. Security and operational cost

The objective remains "make the recognition system work appropriately with
reasonable security." More mechanisms are not automatically better, and design
approval is not a conclusion that their deployment cost is justified.

| Cost / risk | A - issuer bridge | B - effect attester | C - revocation fence |
| --- | --- | --- | --- |
| Privilege expansion | Introduces exact issue-time eligibility production, not general issuance | Adds privileged fixed family/witness mutation and attestation | Defines ordering authority, not arbitrary cancellation or mutation |
| Attack surface | Governance authentication and protected producer integration | Trusted mutation/proof/commit path | All participating revocation and finalization transitions |
| Confused deputy | Full authentic approval/action/holder binding required | Reject caller SQL, substituted manifest/target/evidence | Reject false revoker, stale state and ambiguous effective order |
| Delegation | Original holder only; no transfer or subdelegation | Internal fixed action is not an independent executor | No runtime/producer governance self-revocation authority |
| Replay | Exact one-use approval and prospective source provenance | D/start/permanent exclusions and complete transaction proof | Durable ordered transitions, never restored spent rights |
| Audit | Separate adoption/appointment and exact issuer/source linkage | Actual effects, witness and committed verification | Attributable scope, predecessor, effective order and result |
| Revocation complexity | Must resolve applicability without retroactive broadening | Must check current disqualifiers at required boundaries | Must explicitly resolve races and commit/publication semantics |
| Operational complexity | New protected integration and failure surfaces | Full population/evidence accounting and inspection | Serialization and ordering across producer paths |
| Failure / uncertainty | No usable partial issuance or automatic adoption | No inferred commit, witness-only proof or retry | Unknown state blocks; cannot erase irreversible commit |

Design all three together only to determine whether they form a simpler coherent
minimum than the current blocked composition. Do not add optional machinery or
general roles, and do not declare performance improvement without separate
authorized evidence. The measured expiration is not proof that this design fits
120 or 300 seconds. If costs outweigh the original objective, return that result
rather than expanding privileges to make implementation convenient.

## 7. Alternative: reject and accept limitation

Rejecting the primitives is a safe available terminal choice: retain current
v1/120 default, fail-closed recognition lifecycle under the measured workload,
no production activation and no further G-series/finalization-authority chain.
It avoids all new privileged surfaces but does not meet the desired complete
runtime objective that R14 declined to abandon.

That alternative is not selected here. Limited design of all three requirements
is justified to test whether the requested objective can be met without broad
authority or a lifetime escalation. No operational rollout is justified merely
by that willingness to investigate. Terminal acceptance remains an explicit
future product choice if the bounded design cannot satisfy its obligations.

## 8. Decision, lifetime and exact next boundary

**A - AUTHORIZE ALL THREE NEW SECURITY PRIMITIVES, DESIGN AUTHORITY ONLY.**
Authorize design of A's authenticated exact-action issuer bridge, B's original-
holder complete-effect/witness attester and C's durable revocation/finalization
ordering. No specific producer, credential mechanism, schema, API or runtime
permission is selected. Existing authorities gain no new rights.

v1 = 120 seconds and v2 = 300 seconds retain their existing meanings; ordinary
default remains v1. No 600-second policy, separate action lifetime, renewal or
retroactive source extension is authorized. Lifetime is a separate decision.

The exact next boundary is a **design-only integrated specification of these
three primitives**, resolving authentic approval/producer provenance, complete
effect evidence and allowed-write proof, and revocation/commit linearization.
It must preserve the separate atomicity blocker and must not claim implementation
readiness until that requirement is explicitly resolved. R19 does not execute
that next design or assign an invented follow-on slice number.

G-series work may continue only within this constrained design boundary, not as
an automatic implementation chain. No G1 adoption, appointment, issuance, mutation
permit, writer/execution capability, readiness or activation follows from R19.

## 9. Validation and production blocks

Only this document is added. R18 and its cited mandate, producer, effect and
journal requirements are the decision baseline. Document whitespace/local-link
checks and `git diff --check` passed. No pytest, lifecycle, Z18, T or broad suite;
no code/schema/policy/permission changes, migration, authority issuance, producer
appointment, target change or production/hosted resources. No commit or push.

PRODUCTION AUTHORIZATION: BLOCKED

PRODUCTION EXECUTION: BLOCKED

PRODUCTION ACTIVATION: BLOCKED
