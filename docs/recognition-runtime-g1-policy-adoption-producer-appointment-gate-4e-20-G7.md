# 4e-20-G7: independent G1 policy adoption and producer appointment gate

## 1. G6 blocker and assessment

[G6](recognition-runtime-g2-producer-complete-effect-evidence-contract-4e-20-G6.md)
requires independently authorized prospective G1 policy adoption and constrained
producer appointment. The prospective source issuer cannot authorize itself.
Its conditional issuance/effect/verification contracts are not reopened here.

**Assessment B: an independent project governance authority with the explicit
right to adopt this new G1 policy and appoint/revoke its constrained producer is
not established by the inspected repository contracts.** No actor receives that
right through this document. The architectural chain stops.

## 2. Existing authority inventory and policy-adoption boundary

Inspected sources are under `src/review/recognition/`, plus the local management
CLI. Finding no grant is not a claim that the project cannot establish governance
externally; it means no such authoritative decision can be assumed from these
existing permissions or this documentation task.

| Candidate | Existing authority | Why it does not establish G1 adoption authority |
| --- | --- | --- |
| Trusted host/database operator and `administration.py` | Explicit local installation, generation, filesystem rebind and administrative recovery ceremonies | Module expressly says local installation control never authorizes recognition. File access/trusted-host status is not an adopted grant-right policy |
| Runtime-profile enrollment operator | Approval of independently reviewed runtime evidence, generation-bound profile and revocation | `runtime_enrollment.py` expressly does not grant runtime authority; identity enrollment is not policy adoption |
| Verified project owner / authenticated admin | Existing actor/access checks, MFA, scoped approvals and confirmations | Identity/authentication establish who acts, not a new power to change source delegation rights |
| Activation owner | `local_readiness.begin_activation_confirmation`, `_transition`, `require_activated`: exact readiness, activation confirmation and incarnation | Explicit activation permission is not permission to appoint a new authority producer or reinterpret source consent |
| Protected source-consent owner | `runtime_authority_consent_transaction`: registered activated context, narrowly permitted MFA/confirmation/audit writes | Existing artifact subjects and exact mutation proof do not authorize G1 policy adoption/appointment |
| Original runtime source issuer | Confirmed original source issuance/continuation, exact source scope and five-write protocol | The actor being authorized cannot bootstrap its prospective policy entitlement |
| Generic audit append / repository contract approval | Evidence recording / design review | An audit row or approval to design a capability is not independently authenticated deployment policy adoption |

Required governance authority is external to the source-issuer permission chain:
it must expressly be empowered to decide this new policy's adoption and to bind
the producer's limited role. **Authority identity/type, its root of legitimacy,
authentication, approval/quorum requirements and governance revocation rights are
UNRESOLVED.** No existing project-owner, console, key-holder or developer role is
silently promoted to that position.

Conditional adoption requirements already established by G2 remain: exact policy
descriptor P/version/digest; installation and adopting actor; independently
authorized protected consent; immutable audit evidence; recorded adoption before
source consent/issuance; effective time no earlier than actual adoption; no
retroactive source rights; and explicit version-bound revocation. Authentication
and approval mechanics cannot be specified as authoritative until the governance
actor and its permission are established. No arbitrary second approver, quorum,
new key or signing infrastructure is invented to conceal that gap.

## 3. Producer appointment authority and constraints

Only that independently empowered governance authority could appoint the sole
prospective original source issuer described by G6. This is a conditional role
boundary, not a grant from this gate. Policy adoption authorizes the policy;
appointment selects its permitted producer. Neither substitutes for the other.

| Appointment binding | Required constraint; not an implemented record |
| --- | --- |
| Producer identity | Exact trusted source-producer role/implementation and permitted original issuer context, not a caller-chosen function, hostname or bearer ID |
| Producer authority | Establish prospective G2 eligibility through original protected source issuance only; zero adoption, appointment or target-write rights |
| Policy | Exact adopted P/version/digest and adoption reference; never latest-policy lookup |
| Action / decision scope | Only G1 original-holder exact supported family-effect-plus-witness action, bound to one new original D per genuine issuance under all existing exclusions |
| Runtime / context | Original private registered producer, actual authenticated owner/runtime incarnation, current enrolled profile/generation/install/target/epochs and reservation lineage |
| Target / family | Exact authorized installation/target and supported historical family scope; no arbitrary target selection, new family or scope expansion |
| Start / end | Canonical recorded authorization interval; start cannot precede confirmed appointment/adoption or applicable policy effective time; current issuance strictly within interval |
| Revocation | Append-only exact appointment reference and authorized revoking actor/time/order; no reset, replacement or extension inferred |

The exact appointed identity, interval/end, permission evidence and appointing
actor are **UNRESOLVED** until governance authorizes them. No numeric appointment
lifetime is selected. Appointment is not an execution decision and cannot preassign
or adopt an old D. Its scope only constrains future independently consented source
issuance. The producer cannot appoint itself or another producer, broaden its
scope, change P, create arbitrary actions, bypass validation or grant its role.

## 4. Separation of duties

```text
policy adoption != producer appointment
producer appointment != G1 eligibility
G1 eligibility != mutation authority
mutation authority != target witness
target witness != authorization
```

These are separate decisions/permissions even if future governance permits one
human to perform more than one role. Existing contracts do not establish whether
one human may adopt and appoint, or may also operate the appointed issuer. Do not
invent a mandatory two-person rule or assume same-actor legality. **Role
co-occupancy and approval requirements remain governance questions.**

What is fixed: the producer's own runtime/consent/authority cannot authorize its
adoption or appointment. A copied actor ID, matching owner status or separate
context in the same interpreter is not independent authorization. Even if a future
governance decision permits the same person, separately authorized and attributable
adoption/appointment must precede producer use; no self-certifying producer API.

## 5. Prospective-effect rules

| Source case | Required interpretation |
| --- | --- |
| Issued before adoption | No G1 rights; immutable old source prefix cannot receive later eligibility |
| Issued after adoption | Not automatically eligible: confirmed effective appointment, original G1-specific consent and exact G2 source prefix/current checks are required |
| Issued while adoption/appointment is uncommitted or uncertain | No eligibility from pending facts; issuance must observe confirmed applicable authorization under authoritative order |
| Original source under older policy | Stays bound to original exact version/action. Later versions never broaden it; only separately authorized new sources may use a new version |
| Issued after effective revocation | Deny prospective production/use under the revoked policy or appointment; no grace or latest replacement inferred |

Adoption and appointment time must be corroborated by immutable audit order,
not timestamps alone. G2's original E/source prefix supplies source attribution.
No authority gains rights merely because its fields, host or issue date match.

## 6. Minimum authoritative audit and durability

Required evidence is policy P and exact adoption decision/actor/authentication/
approval provenance/effective time; exact appointment scope/actor/authorization
interval; immutable references linking appointment to adoption; and separately
authorized revocation facts resolving each referenced decision. Ordinary audit
actor/time/predecessor/order must be validated. No secret, credential or raw token
belongs in the evidence. No database schema or new typed codec is defined here.

Producer source issuance must resolve full confirmed adoption and appointment,
not trust a supplied digest or generic audit text. Later Q/E/source evidence must
be attributable to that exact independently authorized graph. Missing, ambiguous,
conflicting, partial or unknown authorization denies eligibility.

Adoption and appointment are distinct logical facts. If governance later permits
them in one local transaction, both must satisfy their own permission checks and
commit atomically; this gate does not prescribe such a transaction. If separate,
appointment cannot become usable before confirmed adoption. Publication is not
atomic with durable commit. Lost publication allows authorized inspection of facts,
never automatic repeated adoption, appointment or runtime authority creation.

## 7. Revocation semantics and limits

Separate historical truth, prospective production permission and live source use.
Do not assume deleting an appointment or revoking a role erases old effects.

| Revoked / changed scope | Established effect or unresolved boundary |
| --- | --- |
| G1 policy | G2 already requires current applicable policy not revoked at exercise/use. Deny later production/use; preserve original historical eligibility and committed effects. This is live invalidation, not retroactive grant broadening or rewriting |
| Producer appointment | Must deny future eligibility production once effective. Whether revocation independently invalidates already-issued sources is **UNRESOLVED**; do not infer that from appointment revocation alone. Existing policy/source live checks still apply |
| Source authority/authentication | Existing expiry/revocation/current scope rules invalidate live use; no renewal/adoption. Historical audit/outcomes remain facts |
| Producer runtime/context | Original-owner loss, restart or incarnation mismatch prevents producing/using live rights; durable appointment does not recreate private ownership |
| Target/profile/generation scope | Existing exact physical/enrollment/binding checks fail closed on mismatch; appointment cannot override or rebind them |
| Execution scope | Existing approval/ACK, stop, dependencies, activation, history/claim/control/readiness or deadline invalidation denies current action; no restored allow through governance DATA |

Who can revoke adoption/appointment, how the effective point is established and
the permitted co-occupancy/conflict rules belong to the missing governance
authority. No new retroactive revocation power is created by this review.
No invalidation promises to undo already committed target effects; uncertainty
retains exclusion and permits only separately authorized factual inspection.

## 8. Crash / uncertain authorization

| Event | Required handling |
| --- | --- |
| Adoption committed, publication failed | Exact authorized durable adoption may be inspected; no inferred appointment/eligibility or automatic repeat ceremony |
| Appointment committed, publication failed | Inspect exact independently authorized appointment and current effective state; do not manufacture original runtime ownership from it |
| Adoption commit uncertain | No producer use; confirm authoritative complete adoption graph, not process memory or timeout |
| Appointment commit uncertain | No eligibility production; do not infer appointment from adoption, audit text or identifier |
| Producer uses stale policy/appointment observation | Deny; resolve current effective exact authorization at production, with required ordering and original source binding |
| Policy revoked during producer use | Fresh current checks must deny if effective revocation is observed before authorization commit/use; no cached allow. Existing target/control commit and uncertainty rules remain, not an instantaneous cancellation promise |

No uncertain authorization is interpreted as permission. Resolving a confirmed
historical fact does not itself issue a source, grant or enforcer. Unknown state
stays blocked, without retries, adoption or a second authority ceremony inferred.
No authorization rollback across independent databases is claimed.

## 9. Decision B and architectural stop

**B - One specific governance/security authority is missing:** an independently
recognized project policy-adoption/producer-appointment authority whose explicit
mandate covers prospective G1, its constrained issuer, authentication/approval,
role co-occupancy and revocation. Existing operator/owner/activation/consent
permissions do not establish that mandate.

This is not evidence that independent adoption is incompatible (C), but existing
independent authorization (A) has not been established. The unresolved appointment
revocation and role-overlap rules are parts of that same governance boundary,
not permission to select convenient technical defaults.

**The architectural chain stops.** No next technical implementation, optimization
or performance slice is proposed. This gate does not appoint an actor, adopt P,
create permissions or reopen G6's effect-evidence design.

## 10. Validation and production blocks

Only this document is added. Document whitespace/local-link checks and
`git diff --check` only. No pytest, Z18, T, broad suites, Python/schema/migration,
permission/authority/grant/enforcer, target DML/DDL, hosted/production access,
key reads, commit or push. The 120-second ceiling and fresh validation are unchanged.

PRODUCTION AUTHORIZATION: BLOCKED

PRODUCTION EXECUTION: BLOCKED

PRODUCTION ACTIVATION: BLOCKED
