# 4e-20-R21-A - issuer-authority governance/design decision

## 1. R21 baseline

[R21](recognition-runtime-security-finalization-authority-issuer-contract-4e-20-R21.md)
identifies a missing exact-action issuance entitlement. Authentication and
appointment are necessary but are not that entitlement. Existing authentication
can prove identities in its approved scopes; existing governance defines role/
appointment requirements. Neither establishes that an actual issuer is currently
authenticated and entitled to the new action. No issuer is appointed by this record.

**A - AUTHORIZE ISSUER-AUTHORITY PRIMITIVE FOR DESIGN.** This decision permits
specifying the minimum entitlement below, not its operational introduction.
It grants no permission, appoints no producer, issues no authority and does not
assert that its authentication or enforcement mechanism already exists.

## 2. Missing primitive and minimum scope

The proposed entitlement means: **authenticated issuer X may issue finalization
authority Y only for exact governed action Z, original decision D and holder H,
target/family T and complete write-set contract W, under exact policy P during
one immutable bounded interval.** X/Y/Z/D/H/T/W/P are explanatory names, not
new fields, identities, principals, formats or records created here.

The entitlement must identify one issuer and one exact issuance opportunity;
it is not a general role allowing arbitrary authorities for future decisions.
No transfer, re-delegation, renewal, retry authorization, target mutation,
arbitrary writes, producer appointment or general producer privilege is included.
Any need for multiple decisions, another issuer, broader scope or rotation is a
separate security decision, not an inferred feature.

## 3. Issuer bindings

| Binding | Required meaning |
| --- | --- |
| Authenticated issuer | Exact independently authenticated principal and protected live context, not a supplied identifier or self-certified callback. |
| Governance mandate / authorization | Full resolvable accepted mandate and separately attributable exact entitlement approval; no mandate-to-runtime promotion. |
| Appointment / role | Authentic applicable constrained appointment, scope and original interval; appointment alone grants no issue action. |
| Issuance action | One exact finalization-authority issue action for the specified subject, not an authority factory. |
| Decision and holder | Original D = source authority ID/body digest and genuine original holder/actor/runtime; no replacement D, session, operator or historical adoption. |
| Target / family / write set | Exact enrolled target/installation, supported family, approved operation/private manifest and complete write-set contract. Unresolved proof cannot be hidden behind a caller digest. |
| Policy/version | Exact prospectively approved policy/action identity and canonical digest, not today's default or a caller override. |
| Validity | One finite approved entitlement interval, further clipped by appointment, original credentials/consent/source and applicable policy bounds; no new numeric policy is selected. |

All substantive bindings must be fixed by the authoritative approved subject and
freshly checked, not chosen or broadened by X at issue time. Actual issue time,
derived expiry and canonical generated values may only follow the reviewed
producer rules. This decision approves no additional mutable field or new
authority identity scheme. The issuance must preserve D rather than authorize
an independent divergent execution decision.

## 4. Governance basis

The accepted documentary basis is the project-owner mandate in
[G13](recognition-runtime-g1-formal-governance-mandate-4e-20-G13.md), verified under
G14, for the exact G2 policy and one constrained producer appointment. Its
indefinite governance duration implies no indefinite entitlement or runtime right.
Its exact v1-bound policy scope is not silently broadened by v2 support.

Before operational entitlement exists, evidence must establish authentic exact
project-owner approval of its full scope, applicable adoption and distinct
appointment, approved interval and restrictions. Existing mandate scope must
actually cover the proposed subject; any departure requires explicit separate
approval. No new approver or organizational mandate is invented.

The chain is governance mandate -> separately approved issuer entitlement ->
protected finalization-authority issuance -> separately validated runtime
exercise. Authentication proves X; governance permits X to hold the exact role;
the entitlement permits this exact issue action. None substitutes for the others.
[G17's executable approval bridge](recognition-runtime-g1-protected-governance-owner-binding-contract-4e-20-G17.md)
remains an obligation for the design; no existing admin action is reinterpreted
or credential mechanism selected here. No runtime or issuer may appoint itself.

## 5. Issuance safety

The future protected owner must independently resolve and check current issuer
identity, applicable governance/appointment/entitlement, full D/source and original
holder, exact target/family/action/write-set subject, policy version and all
original credential/consent/source deadlines. Unknown or inconsistent state denies.
Use full canonical authoritative content, not caller-selected hash equality alone.

One logical issuance must be durably excluded from repetition under authoritative
transaction serialization. Existing confirmation CAS/source exclusions are
foundations, not automatic protection for an additional entitlement. Same-D
historical lookup may return DATA but cannot recreate a live capability. No
replacement/renewed authority, another D evading permanent operation/manifest
exclusion, uncertain-commit retry or recovery adoption is permitted. Failure must
publish no usable authority before confirmed commit and cleanup.

This is an issuance requirement only. Complete-effect attestation, actual target
permission and revocation/commit ordering are not resolved or implemented here.

## 6. Durable audit and revocation linkage

Minimum attributable evidence must resolve issuer identity, exact issuer-
entitlement identity/reference, full governance approval and appointment, original
D and holder, issued authority's exact canonical identity/body digest, action,
target/family/write-set reference, actual issue time/expiry and exact policy/version.
Preserve audit predecessor/ordering and confirmed issuance provenance. No new
record layout is specified and an audit append is not itself runtime authority.

These immutable relationships must let a later separately authorized revocation
system identify the exact entitlement and its issued subjects. Original evidence
cannot be overwritten or silently reinterpreted. Unknown current entitlement
applicability denies issuance. This does not choose a new revoker, cancellation
point, fence mechanism or retrospective effect on already-issued authorities.

## 7. Compromise boundary

With an uncompromised independent protected enforcement owner, compromise of X's
identity credential or issuer-facing input must not allow changing D/holder/
target/action/write set/policy or original bounds. The protected owner must resolve
the exact independently approved subject and enforce durable once-only issuance;
it cannot trust X to attest its own scope or unused status. Maximum intended
damage of one isolated exact entitlement is its one already-approved issuance,
never arbitrary finalization or another execution opportunity.

That is an enforcement requirement for R21-B, not a demonstrated security proof.
No actual independent isolation or authentication mechanism is established here.
If X and its enforcement boundary are both compromised, or arbitrary trusted
interpreter/host execution is compromised, current in-process checks/hashes do
not prove one-action containment. A producer-wide credential is not automatically
isolated to one decision. R21-B must state and justify that trust/compromise
boundary; it must stop if independent constraint cannot be specified. No claim
of universal compromise resistance is made merely to approve further design.

## 8. Separate atomicity and other blockers

The issuer primitive cannot make separate target business-effect/witness and
control decision/history/outcome/audit commits atomic. Cross-database atomicity
remains unresolved, along with complete-effect proof and full revocation ordering.
This decision neither accepts split outcomes nor authorizes a new storage model.
No target witness, permission or issuance record substitutes for those decisions.

## 9. Decision and exact next boundary

**A - AUTHORIZE ISSUER-AUTHORITY PRIMITIVE FOR DESIGN**, only within the minimum
scope above. Continued design is warranted to assess the identified exact-action
gap; it is not evidence that deployment of the added privilege is justified.
Rejecting the primitive and accepting the limitation remains a possible later
explicit product decision, but is not selected as the terminal outcome here.
No different governance model is presumed necessary without that assessment.

The exact next boundary is **4e-20-R21-B - issuer-authority primitive contract
design**. It must specify authentic entitlement provenance, actual issuer proof,
independent exact-subject enforcement and once-only issuance/uncertainty semantics,
without inventing unsupported credentials or broadening existing rights. If a
necessary mechanism cannot be established, record the gap and stop. Do not
advance to R22 or implement the producer/primitive under this authorization.

v1 remains 120 seconds; v2 remains 300 seconds; ordinary/default remains v1.
No separate lifetime or 600-second policy is approved. No existing source gains
retroactive eligibility, and no runtime activation or execution is authorized.

## 10. Validation and production blocks

Only this document is added. R21 and its cited governance/issuer definitions are
the baseline. Document whitespace/local-link checks and `git diff --check`
passed. No pytest, lifecycle, Z18, T, broad suite, code/schema/permissions/policy
changes, authority issuance, appointment, migration, target mutation or production/
hosted access. No commit or push.

PRODUCTION AUTHORIZATION: BLOCKED

PRODUCTION EXECUTION: BLOCKED

PRODUCTION ACTIVATION: BLOCKED
