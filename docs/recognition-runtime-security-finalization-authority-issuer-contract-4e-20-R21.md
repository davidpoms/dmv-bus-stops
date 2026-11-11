# 4e-20-R21 - authenticated finalization-authority issuer decision

## 1. R20 baseline and scope

[R20](recognition-runtime-security-integrated-finalization-primitives-design-4e-20-R20.md)
remains blocked. R19 permits design, not runtime rights, appointments or policy
changes. This decision addresses only what can authenticate and constrain the
issuer. Complete-effect proof, revocation/finalization ordering and cross-database
atomicity remain untouched and unresolved.

**Decision B - NEW ISSUER-AUTHORITY PRIMITIVE REQUIRED.** No inspected existing
principal/mechanism both authenticates the proposed issuer and authorizes this
exact new issuance action. Appointment alone would not resolve authentication,
protected issue-time action binding or compromise containment. This is a complete
requirement decision, not a claim that an executable issuer contract exists.

## 2. Actual evidence inspected

| Source | Established behavior / limit |
| --- | --- |
| [G13 mandate](recognition-runtime-g1-formal-governance-mandate-4e-20-G13.md) | Project-owner documentary authority for exact prospective G2 adoption and one constrained producer appointment. No machine issuer credential, target permission or appointment is created. |
| [G16 storage protocol](recognition-runtime-g1-adoption-producer-authoritative-storage-protocol-4e-20-G16.md) | Required immutable adoption/appointment identities, scope, approval, interval and audit lineage; no protected authenticated producer integration. |
| [G17 owner binding](recognition-runtime-g1-protected-governance-owner-binding-contract-4e-20-G17.md) | Explicitly unresolved exact-action project-owner approval bridge into a manager-owned control transaction. |
| [admin_auth](../src/review/recognition/admin_auth.py) | Primary/session ownership, credential hash, auth epoch, generation, expiry and revocation checks. Existing ACTIONS do not include governance adoption/appointment or the new issuer role. |
| [authority consent](../src/review/recognition/runtime_authority_consent.py) | Fresh exact runtime subject, original primary/session and bounded step/confirmation evidence; operation consent is not issuer appointment. |
| [authority issuer](../src/review/recognition/runtime_activation_authority_issuance.py) | Original confirmation CAS, canonical source/body, fixed five-write graph and confirmed commit/cleanup. Public duplicate issuance returns inspection DATA, not another object; private original coordinator issuance has strict ownership. No prospective G1 grant-right is added. |
| [administration audit](../src/review/recognition/administration.py) | Canonical attributed audit-chain append and control binding; an actor field/action string does not authenticate a new issuer or grant new rights. |
| R16-R20 | Design permission only, one original holder/action/D; no executable authentication root, actual appointment or operational entitlement supplied. |

Source inspection reads definitions only, not credential/key contents or databases.

## 3. Candidate issuer classes

| Candidate | Authentication and authorization | Scope / target / decision | Audit / issuer revocation linkage | Compromise impact / conclusion |
| --- | --- | --- | --- | --- |
| A - existing original authority | Genuine original holder can be proven by current protected context; no existing permission to issue the new finalization right | Current exact source/D and deployment scope; cannot broaden it into a grant-right | Existing source/genesis/audit and current source checks | Original authority possession alone cannot authorize this issue action. Not sufficient. |
| B - governance authority | Verified documentary project-owner mandate; no established runtime authentication bridge | May approve exact policy and appointment, not issue arbitrary runtime authorities | Mandate and distinct decisions; documentary revocation rules | Treating conversational identity as a machine credential would collapse roles. Not sufficient. |
| C - separately appointed issuer | Appointment is required, but no actual appointment or independently authenticating manager bridge exists | Future one constrained source role, exact adopted action and deployment; original D/holder only | Full authentic appointment/adoption/issuer/source provenance required | Closest required role, not an existing appointed principal; appointment alone leaves authentication/enforcement missing. |
| D - transaction/security service | No inspected service identity has this permission; owning a transaction does not authenticate issuer entitlement | No new service-wide action, target selector or independent executor scope permitted | Would require its own authentic appointment and attributable issuance | Introduces an unsupported trusted deputy; cannot be invented as a shortcut. |
| E - no existing safe issuer | Supported present-state conclusion | No runtime issuance is permitted by this decision | Existing evidence remains historical, not a new role | Fail closed until the new scoped issuer primitive is separately approved and specified. |

## 4. Governance-to-issuer chain

Required chain: accepted mandate -> authentic exact policy adoption -> separate
authentic constrained appointment -> independently authenticated actual issuer
context -> protected exact-action issuance to the original holder.

Governance means this issuer may hold the role. Authentication means this actual
principal/context is that issuer. Authorization means this issuer may issue this
exact authority now. No one of these implies the others. An admin session may
authenticate a different scope without satisfying governance or authorization.

The bridge must verify full canonical approved subjects, intended scope/effective
interval, expected predecessor/audit head and approval provenance, not merely
caller digests or a producer claiming it was appointed. The accepted G13 mandate
is not reopened; its existing exact G2/v1-bound scope must not be silently extended.
Runtime/source/producer self-appointment is prohibited.

The minimum new primitive is an **authenticated, exact-action issuer entitlement
binding enforced by a protected issue transaction owner**: independently verify
the actual issuer and exact authentic appointment/approval, bind it to original
holder/D/action/target/write-set references and original deadlines, prove only
the permitted issuance changes, durably exclude another issuance opportunity,
and publish nothing before confirmed commit and cleanup.

This specifies required security semantics, not a new login, signing system,
credential, callback, service account, codec, table or mutation API. Existing
evidence establishes no sufficient implementation of the authentication root.
No actual principal is selected or appointed here.

## 5. Immutable issue-time evidence

This is an evidence inventory, not additional authority fields or a new format.
References must resolve complete authoritative content under existing canonical
serialization/digest rules. Mutable current authorization must still be checked;
an original audit prefix does not prove it remains valid forever.

| Evidence | Existing support | Missing for the new issuance action |
| --- | --- | --- |
| Issuer identity and live context | Protected source context/PID/live Thread/connection patterns | Independent authentication of the appointed new issuer role; IDs or PID DATA alone are insufficient. |
| Issuer authorization / mandate | G13 stable mandate and G16 logical appointment/adoption requirements | Authentic exact approvals, protected transitions and current resolved applicability. |
| Original D | Existing canonical authority ID/body digest and source/genesis/audit | Prospective issue-time new action entitlement; no independent divergent decision identity. |
| Original holder | Existing original actor/credential/context binding | Exact authenticated issuer-to-original-holder relationship for this action; no replacement operator/session. |
| Target/family/action | Existing source/runtime operation/private manifest scope and G2 action descriptor | Issuer permission restricted to that complete exact subject, not caller target/action selection. |
| Write-set identity | Existing manifest/family definitions and references | Complete-effect contract is separately unresolved; issuer must not invent or widen it. A claimed digest is not a resolved write-set definition. |
| Issue time / validity | Actual canonical issue/expiry, version mapping and credential/consent clipping | Exact new issuance applicability under approved policy; no independent interval is selected. |
| Credential binding | Original primary/session/runtime-auth references, owner/auth/MFA scope | No reuse as a governance credential without an expressly established bridge. No plaintext credential content is evidence. |
| Audit / appointment provenance | Existing canonical hash-chain machinery | Typed authenticated action/approval/appointment-to-issuance linkage and exact protected write proof. |

No source is retrofitted: preexisting authority rows acquire no new eligibility.
No v1/v2 policy is changed, and no 600-second or separate action lifetime is approved.

## 6. Compromise boundary

The required design must prevent an issuer-facing caller or compromised issuer
credential from selecting another D, target, holder or write set, extending any
original deadline, minting a replacement, or bypassing once-only issuance.
That requires checks enforced by a trusted protected owner **outside the claimed
issuer input**, resolving independent full approval/appointment and original
source/consent, not accepting issuer-supplied self-certification.

Desired maximum for compromise confined to one exact issuance entitlement is
at most its one already-approved action for its original holder/D/scope, within
all original bounds. Even that does not authorize execution or prove its safety.
This maximum is a requirement, **not a demonstrated containment guarantee**:
the authentic bridge and independent enforcement are missing. A producer-wide
credential spanning several valid subjects cannot honestly be claimed to limit
damage to one decision unless entitlement isolation is separately established.

Compromise of the entire trusted issuer/transaction-manager interpreter or host
is a different trust-boundary breach. Existing in-process registries and hashes
do not prevent malicious trusted code from fabricating claims or bypassing code.
No repository evidence establishes independent isolation sufficient to bound
that compromise to one action. Required next design must explicitly state this
trust assumption and containment boundary; a universal compromise-proof claim
would be unsupported. Audit enables attribution, not prevention by itself.

## 7. Replay and duplicate issuance

The required rule is at most one logical issuance opportunity for the original
D/action, with permanent operation/manifest exclusions preserved. Multiple
replacement or renewed authorities for that same decision are prohibited;
same D/different body is a conflict. An identical lookup is historical DATA,
not a second executable authority or reconstructed original context.

Existing confirmation CAS, source uniqueness, fixed mutation proofs and private
coordinator checks are useful foundations. They do not automatically fence an
additional authority class. The new protected issuance primitive must prove its
durable once-only binding under authoritative transaction serialization; no new
table/field or reusable bearer token is specified here. In-memory flags alone
are insufficient. Uncertain issuance commit/cleanup publishes nothing usable
and authorizes neither retry, another source, adoption nor repair.

## 8. Issuer-side revocation linkage only

Required immutable attribution must resolve who issued, what exact authority/
action was issued, actual issue time/expiry, original D/holder/target, applicable
policy and full governance/adoption/appointment approval references. Preserve
original records and linked audit ordering; no overwrite or latest-policy
reinterpretation. These facts identify the affected issuer and scope for a
later independently authorized revocation system.

G13/G16 documentary revocation and existing credential/source checks retain
their meanings. R21 does not define in-flight cancellation, effective revocation
linearization, a new revoker, or commit-fencing behavior. Unknown current issuer
authorization rejects issuance. This is issuer eligibility checking, not a
resolution of R20's separate revocation-ordering problem.

## 9. Decision and exact next boundary

**B - NEW ISSUER-AUTHORITY PRIMITIVE REQUIRED.** Existing authority cannot supply
this grant-right/authentication bridge (A). A bare appointment cannot authenticate
the issuer or enforce exact issue-time scope (C). Evidence identifies a concrete
missing primitive rather than leaving the requirement wholly unknown (D).

The exact next boundary is explicit governance/design approval for the minimum
authenticated exact-action issuer entitlement and protected once-only issuance
primitive defined above, including its independent authentication root and
compromise-containment assumptions. No role is appointed or permissions granted
by this requirement decision. Design authorization alone must not later be
reported as evidence that a credential/bridge already exists.

Stop here. Do not advance to R22 on an A outcome that has not been established.
Complete-effect proof, full revocation ordering and cross-database atomicity
remain independent unresolved boundaries, not reopened or resolved in R21.
There is no new lifetime decision, finalization redesign or implementation slice.

## 10. Validation and production blocks

Only this document is added. Read-only inspection of actual mandate, G16/G17,
admin authentication/revocation, authority consent/issuer, administration audit,
and R16-R20 baseline. Document whitespace/local-link checks and `git diff --check`
passed. No pytest, lifecycle, Z18, T, broad suite, code/schema/permissions/policy
changes, migration, authority issuance, producer appointment, target change or
production/hosted access. No credential/key reads, commit or push.

PRODUCTION AUTHORIZATION: BLOCKED

PRODUCTION EXECUTION: BLOCKED

PRODUCTION ACTIVATION: BLOCKED
