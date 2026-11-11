# 4e-20-G8: G1 governance adoption decision

## 1. G7 blocker and decision status

[G7](recognition-runtime-g1-policy-adoption-producer-appointment-gate-4e-20-G7.md)
found no existing inspected independent mandate to adopt G1 and appoint its
constrained producer. Authentication, approvals, role overlap and appointment
revocation therefore require an explicit governance decision.

**Selected option B: a new governance authority/mandate must be established before
G1 can be adopted.** This is the supported prerequisite decision, not establishment
of that mandate. G1 is **not adopted**, no producer is appointed, and no mutation
capability is authorized. Completion of this decision document does not complete
G7's authorization gate.

The evidence is G7's scoped authority inventory, the explicit installation-only
boundary in `administration.py`, enrollment's non-authority boundary, and the
existing consent/approval/activation contracts. The
[maintainer reference](TECHNICAL_HANDOFF.md) documents operational/data boundaries
and narrow application roles; it does not establish a G1 governance mandate.
Maintainer reference status, repository access or owner identity is not such a
mandate. This conclusion is limited to inspected repository evidence, not a claim
that legitimate external project governance cannot exist.

## 2. G1 policy adoption decision required

| Choice requiring authorized governance | Required decision / current status |
| --- | --- |
| Whether G1 should exist | Explicit accept or reject of the new original-holder single-action grant-right. **Not decided by this documentation instruction** |
| Effective policy version | If accepted, identify exact proposed G2 P/version/digest and action restrictions; never infer the latest policy. Proposed version 1 is not an effective adopted version |
| Scope | Only prospective new eligible original sources for the exact supported historical family-effect-plus-witness action, exact target/runtime/decision and all existing gates; no general writer or expanded family |
| Effective point | Confirmed attributable adoption and explicit effective time, no earlier than adoption record, before original G1 consent/source issuance; no backdating |
| Adopting authority | Named independently empowered actor/body, mandate and scope. **UNESTABLISHED**; no operator, owner, runtime issuer or assistant is appointed here |
| Authentication and approval | Define how that actor proves its mandate and identity, exact policy-bound approval, approval/quorum and conflict rules. MFA/owner status alone is insufficient; no mechanism is selected here |
| Revocation authority | Name who may revoke the exact policy, effective ordering and evidence. Preserve G2 live policy-revocation checks without rewriting historical facts or undoing committed effects |

This review records these choices; it does not answer them on behalf of an
unidentified approving authority. A generic approval of architecture or permission
to write this file is not deployment policy adoption.

## 3. Producer appointment decision required

Appointment is a separate explicit authorization after applicable policy adoption.
It must identify the independent appointing mandate; exact trusted source-producer
identity/role and protected original issuance context; adopted P/version/digest;
permitted installation/target/family/action scope; runtime/profile/generation/owner/
authentication constraints; start/end; and authorized revocation rules.

Only the G6 prospective original source producer is within the proposed boundary.
It could establish exact issue-time eligibility, not adopt policy, appoint itself,
appoint another producer, broaden actions, grant arbitrary writes or re-delegate
its role. Durable appointment cannot recreate a lost original runtime context.
No identity, implementation allowlist, appointment interval or appointer is
selected in G8. In particular, appointment lifetime is not the execution authority
lifetime, and supplies no extension of the unchanged 120-second ceiling.

Governance must explicitly decide whether appointment revocation affects only
future production or also currently unexercised issued sources. G7 leaves that
question unresolved; no retroactive invalidation or grace period is inferred.
Existing authentication, source, policy, activation and scope invalidations remain
mandatory independently of that future decision.

## 4. Separation of duties and required approvals

| Decision | Independent approval that must be established | What cannot substitute |
| --- | --- | --- |
| G1 adoption | Actor/body with explicit mandate to approve this new source grant-right policy | Runtime source issuance, installation access, existing operation approval or architecture-review completion |
| Producer appointment | Actor/body independently empowered to appoint/restrict/revoke the producer under adopted P | Producer self-appointment or its own consent/authority/audit append |
| Target mutation capability | Explicit capability-security and implementation authorization, followed by all independent runtime action gates | Policy adoption or producer appointment alone; G4 approves implementation design only |

No same-actor combination is presumed legal. Governance must record allowed and
forbidden role combinations, conflicts, independent review and any quorum before
adoption/appointment is usable. This gate neither invents a mandatory two-person
system nor permits one person to perform all roles. Logical independence requires
authorization external to the source issuer's own rights, not merely another
function/context or a copied actor identifier.

## 5. Existing-authority impact

- No retroactive eligibility: pre-policy sources and old immutable issuance
  prefixes cannot acquire G1 through later documentation, audit append or dates.
- Existing authorities gain no new rights. Adoption alone would not make every
  later source eligible; exact original G2 consent/prefix and current gates remain.
- No broader writer authority: enrollment, approval, activation, metadata ownership,
  journal rows or witness evidence cannot become a general target-write capability.
- Existing authority formats, semantics, strict identity checks, legacy execution,
  transaction ownership, readiness and activation gates remain unchanged.

Policy revisions must not rebind older sources to a broader latest version.
Historical outcomes remain facts; revocation is not permission to erase fences,
retry effects or reconstruct original ownership.

## 6. Non-negotiable security properties of any future adoption

Future governance acceptance must preserve all of the following, without treating
acceptance itself as execution permission:

- Original-holder-only execution with actual private runtime/process/Thread/context
  and reservation ownership; no transferable or adoptable identifier.
- Exact original source/decision, target, operation/private manifest, complete
  family-effect set, runtime/activation/profile and witness binding.
- One atomic target transaction for complete family verification, business effects
  and decision-bound witness; no cross-database atomicity claim.
- Permanent single-use and duplicate fencing, including crash/uncertain commit.
- No transfer, re-delegation, renewal, retry or recovery-based reauthorization.
- Mandatory fresh authentication/expiry, approval/proposal/ACK, activation, stop,
  dependencies, physical identity/schema, claims/history/control/migrations,
  readiness, reservation identity/epoch and deadline checks.
- Original at-most-120-second authority lifetime, clipped by earlier bounds; no
  reset through preparation, appointment, journal, grant or phase change.
- Fail-closed uncertainty: no usable result or permission inferred from incomplete
  adoption, appointment, source issuance or target/control outcome evidence.

## 7. Evaluation of exactly options A/B/C

| Option | Evaluation |
| --- | --- |
| A - Existing governance authority is identified and explicitly approves G1 | **Unsupported.** No inspected mandate or attributable actual adoption/appointment approval establishes this. Existing operator/owner/authentication roles and prior design approvals cannot fill the gap |
| B - A new governance authority/mandate must be established before adoption | **Supported and selected.** It records the missing prerequisite without assigning an actor or granting rights |
| C - G1 is rejected and replacement architecture remains blocked | **Not selected.** No authorized rejection decision has been provided; missing authorization is not evidence of rejection or architectural impossibility |

## 8. Selected decision and architectural stop

**B is the governance prerequisite disposition.** The actual accept/reject policy
decision, actor/mandate, approval/authentication rules, role combinations and
revocation choices remain unmade. G8 records them explicitly rather than fabricating
an approving authority. The architectural chain stops at that governance boundary.

There is no next implementation-authorization gate selected: the conditional A
path has not been established. No further technical implementation or performance
slice is proposed. Nothing here creates the governance mandate it says is missing.

## 9. Implementation status and validation

Regardless of option, G8 itself authorizes no implementation. No producer is
appointed by documentation; no permissions change; no authority/grant is issued;
no target mutation is permitted. No timing feasibility claim is made.

Only this document is added. Validate document whitespace/local links and
`git diff --check`. No pytest, Z18, T, broad suites, Python/schema/migration,
permissions, hosted/production resources, key reads, target DML/DDL, commit or push.

## 10. Explicit production blocks

PRODUCTION AUTHORIZATION: BLOCKED

PRODUCTION EXECUTION: BLOCKED

PRODUCTION ACTIVATION: BLOCKED
