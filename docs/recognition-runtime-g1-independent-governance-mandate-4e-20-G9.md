# 4e-20-G9: independent G1 governance mandate specification

## 1. G8 option B baseline

[G8](recognition-runtime-g1-governance-adoption-decision-4e-20-G8.md) selected the
prerequisite disposition B: independent governance authority/mandate must be
established before adoption. G1 remains unadopted, no producer is appointed, no
permissions have changed and the architectural implementation chain is stopped.

This document specifies minimum requirements for a mandate, not an actual
mandate. **Assessment and decision B: a new independent governance mandate is
required outside the current runtime authority model.** Completing this
specification neither identifies a lawful appointee nor establishes its authority.

## 2. Mandate purpose

The mandate must expressly empower identified governance actors to decide whether
to adopt the exact proposed G1 policy and to appoint, constrain and revoke its
producer. It must bind the project/installation scope, policy descriptor/version/
digest, permitted action, effective ordering and limits of those governance rights.
It must identify who can revoke policy, appointment and the mandate itself.

The right is limited to governance actions. Adoption remains a separate explicit
accept/reject decision; appointment remains another attributable scoped decision.
The mandate must not itself issue source authorities, establish an individual
source's eligibility, permit target mutation or create a producer capability.

## 3. Independence and authoritative origin

Minimum independence means that the mandate's authority comes from a recognized
project governance decision external to the rights it is authorizing. Evidence
must establish the authorizer's identity, legitimate project mandate and power to
make this appointment; the producer cannot certify those facts about itself.

| Role from which independence is required | Required distinction |
| --- | --- |
| Source issuer | Its source authority, consent or audit access cannot confer governance adoption/appointment rights |
| Prospective G1 producer | It cannot appoint itself or define its own scope, policy, lifetime or delegation rights |
| Target mutation owner | Transaction ownership, reservations and enforcer permission cannot authorize policy adoption |
| Executing runtime | Host/process identity, runtime profile, credentials or control-database possession cannot authenticate a governance mandate |

Separate identifiers, functions or contexts in the same runtime do not establish
independence. Conversely, this specification does not assume a distinct machine,
new cryptographic key or fixed number of people is sufficient or required.
Governance must establish actual permission and separation, not technical labels.

No existing inspected actor is established as satisfying this mandate. G7's
authority inventory remains applicable. `administration.py` explicitly confines
trusted operators to installation control, and the
[maintainer reference](TECHNICAL_HANDOFF.md) describes narrow reviewer/owner roles,
not a general G1 policy-adoption right. Repository maintenance, host administration,
owner identity, MFA, activation consent and prior design approvals do not supply
the missing project governance authorization. This is a finding about available
repository evidence, not proof no legitimate external authority can exist.

## 4. Mandate scope and exclusions

The mandate must authorize only prospective adoption of exact G1 and appointment
of the constrained original source producer under that policy. Its action scope
is the existing supported historical family-effect-plus-decision-witness action,
not an extensible permission list. Unknown versions/actions are outside scope.

It must exclude retroactive eligibility, arbitrary target writes, general writer
capability, transfer/re-delegation of the producer role or action grant, renewal
of execution authority, retry and recovery-based authorization. It cannot override
original-holder, exact-decision/target/action, atomic effect/witness, single-use,
fresh-validation or existing readiness/activation requirements. It cannot change
the 120-second authority ceiling or grant exceptions to it.

## 5. Approval and separation of duties

| Decision | Minimum independent approval requirement |
| --- | --- |
| Create mandate | Recognized project authorizer with demonstrated legitimacy and explicit right to establish the limited governance role; not authority inferred from this specification |
| Adopt G1 | Mandated policy approver, authenticated and explicitly consenting to exact policy/version/action/effective time |
| Appoint producer | Mandated appointing authority, independently approving exact producer and constrained scope under confirmed adopted policy |
| Authorize future target-mutation capability | Separately authorized security/implementation approval plus all actual runtime action gates; governance mandate/adoption/appointment alone is insufficient |

One governance authority may perform multiple approval functions only if its
independently established mandate explicitly permits the combination and evidence
shows separate scoped decisions, authentication, conflict handling and required
review. No permission for such overlap is established here. Overlap with producer,
mutation-owner or runtime roles must also be explicitly addressed; it cannot be
assumed safe because the person is an owner or uses another context.

The governing decision must specify allowed/prohibited role combinations, approval
or quorum requirements, authentication and consent evidence, and treatment of
conflicts. A mandatory two-person rule is not invented, and single-person control
is not approved by default. Until these choices are established, no adoption or
appointment may rely on unresolved role overlap.

## 6. Mandate lifecycle

| Stage/property | Minimum required rule |
| --- | --- |
| Creation | Attributable explicit project authorization naming the mandated actor/body, source of legitimacy, permissions and limits. A draft or unsigned runtime assertion is not creation |
| Effective time | Explicit confirmed start, no earlier than actual authorization; corroborated by authoritative ordering, not a backdated timestamp |
| Policy/version and scope | Exact descriptor/version/digest and project/install/action boundaries; no implicit latest version or broader successor scope |
| Expiration | Explicit finite authorization interval with start/end chosen by legitimate governance; no numeric duration is selected here. Expiry denies new governance actions under this mandate |
| Revocation | Explicit named revoker with independently established permission; attributable scope/effective ordering; no deletion or retrospective rewriting |
| Supersession | New independently authorized mandate/version and explicit relationship to the prior mandate. No silent inheritance, scope expansion or authority renewal |
| Auditability | Retain complete immutable evidence of authorization, decisions, predecessors, intervals and revocation/supersession; resolvable after role changes |

Governance must expressly decide the effect of mandate expiration/revocation or
supersession on already-adopted policy and existing appointments. Do not infer
automatic survival, cascade revocation, grace periods or retroactive invalidation.
Unclear current applicability cannot authorize new producer use. Existing G2
policy-revocation and all independent source/runtime invalidation checks remain.
Historical facts/committed effects are never erased by a governance transition.

## 7. Prospective effect

Authorities issued before G1 adoption remain unchanged. Authorities missing exact
original G2 eligibility cannot acquire it through a later mandate, appointment,
audit append, matching date or new policy. Future sources must satisfy confirmed
effective policy/appointment plus original protected G1 consent/source provenance
and all current checks; issue time alone is insufficient.

Policy revisions cannot silently broaden existing sources. Uncertain adoption
does not constitute adoption. No governance event restarts an issued source's
deadline, reconstructs original ownership, releases duplicate fences or converts
recovered evidence into a new action right.

## 8. Producer appointment relationship

```text
independently established mandate
  -> explicit exact G1 policy adoption
  -> separate constrained producer appointment
  -> new original source issuance with prospective G2 eligibility
```

Each arrow requires its own independently authorized, confirmed evidence; none is
automatic. Appointment must bind exact producer identity/role and protected context,
policy/version, installation/target/family/action, runtime/profile/generation/owner
and authentication constraints, interval and revocation. It must not preassign or
adopt a historical execution decision. The appointed producer can only establish
eligibility within original protected issuance, not establish its own mandate.

The producer must not appoint itself. Its role carries no appointment or
re-delegation right. Any separately proposed right to appoint another producer
would need independent authorization outside this specification; it is not an
implicit exception here. An appointment is evidence of a role decision, not a
serializable runtime capability or replacement authentication.

## 9. Minimum audit/evidence requirements

Required evidence must allow independent verification of:

- Who authorized the mandate, their identity and legitimate project authority,
  authenticated approval, exact scope/interval and role/conflict rules.
- Who adopted G1, exact P/version/digest and action, mandate reference, decision
  and actual effective time/order.
- Who appointed the producer, their appointing permission, exact producer scope,
  runtime/context constraints, interval, policy and mandate references.
- Who revoked or superseded which authorization, their permission and effective
  order, with explicit treatment of existing policy/appointments/sources.
- How subsequent eligible sources resolve that confirmed graph through original
  G2 consent and immutable issuance prefix; source identifiers alone are insufficient.

Records must be attributable, immutable and retained with full references and
ordering. Authentication/approval proof must be verifiable under an independently
established governance method; no method, signer, key, audit codec or schema is
invented here. No credentials or secrets belong in the evidence. Generic runtime
audit text, repository file ownership or an assistant-written document cannot
serve as their own root of legitimacy.

## 10. Crash and uncertain governance state

| Event | Required behavior |
| --- | --- |
| Mandate creation uncertain | No governance action under it; resolve authoritative complete authorization evidence, not process state |
| Policy adoption uncertain | No appointment/use inferred from a proposed or partially published adoption |
| Producer appointment uncertain | No eligibility production; policy adoption alone is insufficient |
| Publication fails after confirmed decision | Authorized factual inspection can establish the committed decision; no automatic repeat, source issuance or producer activation |
| Revocation uncertain | Do not assume continued authorization or silently erase confirmed history; block dependent new use until exact effective applicability is resolved |

No uncertain governance state is interpreted as permission. Resolution establishes
facts only; it cannot manufacture missing approvals, recreate original runtime
ownership or retry a spent target action. The implementation chain stays stopped
until legitimate governance evidence and separately required authorizations exist.

## 11. Security boundary

```text
mandate != G1 authority
mandate != target mutation authority
mandate != producer capability
mandate != execution authority
mandate != recovery authority
```

The mandate permits governance decisions only. It supplies no target connection,
SQL, transaction, grant, executor or capability. Existing authorities gain no new
rights; original source, producer, enforcer, witness and journal separation remains.
Neither mandate publication nor specification completion activates recognition.

## 12. Existing-model assessment and decision

| Assessment | Finding |
| --- | --- |
| A - Existing authority can satisfy the mandate | Not established by inspected repository evidence. Existing scoped roles do not establish the missing independent mandate |
| B - New governance authority/mandate outside the runtime model is required | Supported and selected. Legitimate project governance must explicitly establish the role and its limits; this document does not do so |
| C - No safe governance structure can be established from current model | Not demonstrated. Missing evidence is not proof external legitimate governance is impossible |

**Decision B - New independent governance mandate required.** This specification
is complete as a statement of minimum requirements, not as an actual authorization.
Identity of the legitimate authorizer, actual approvers, intervals and explicit
role/revocation choices must come from that governance decision, not guessed code.

## 13. Architectural stop and validation

Stop the architectural chain. No next implementation path, performance slice or
adoption step under a purported existing authority is proposed. G1 stays unadopted;
no producer is appointed and no permissions change.

Only this document is added. Run document whitespace/local-link checks and
`git diff --check` only. No pytest, Z18, T, broad suites, Python/schema/migration,
permission/authority/grant/enforcer, target DML/DDL, hosted/production resources,
key reads, commit or push. The 120-second ceiling is unchanged.

## 14. Explicit production blocks

PRODUCTION AUTHORIZATION: BLOCKED

PRODUCTION EXECUTION: BLOCKED

PRODUCTION ACTIVATION: BLOCKED
