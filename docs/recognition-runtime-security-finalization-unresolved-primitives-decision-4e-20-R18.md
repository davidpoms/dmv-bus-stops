# 4e-20-R18 - finalization unresolved-primitives decision

## 1. R17 baseline and scope

[R17](recognition-runtime-security-finalization-authority-contract-4e-20-R17.md)
identified three incomplete security boundaries: issuer authentication, complete
effect attestation and in-flight revocation ordering. Target/control atomicity is
a separate blocker. This review makes an explicit requirement decision for each;
it neither supplies missing operational evidence nor authorizes implementation.
Current default remains v1/120 seconds; existing v2/300 meaning is unchanged.

| Boundary | Decision |
| --- | --- |
| Authenticated issuer bridge | **B - a new governance/issuer primitive is required.** |
| Complete-effect proof | **B - a new witness/attestation primitive is required.** |
| Revocation ordering | **B - a new revocation/fencing primitive is required.** |
| Cross-database atomicity | **B - atomicity remains a separate required primitive.** |

Overall: **B - ONE OR MORE NEW SECURITY PRIMITIVES REQUIRE EXPLICIT GOVERNANCE
APPROVAL.** These are decisions about required security semantics, not adoption
of a mechanism or a claim that these primitives are already approved/deployed.

## 2. Authenticated issuer bridge

### Evidence and minimum requirement

[G13](recognition-runtime-g1-formal-governance-mandate-4e-20-G13.md) establishes
the verified documentary project-owner mandate for prospective adoption of exact
G2 policy and appointment of one constrained producer. It does not issue runtime
authority. [G17](recognition-runtime-g1-protected-governance-owner-binding-contract-4e-20-G17.md)
expressly leaves the exact-action approval-to-protected-transaction authentication
bridge unresolved. Actual
[`admin_auth`](../src/review/recognition/admin_auth.py) authenticates existing
installation/runtime scopes; those scopes do not silently become governance
adoption/appointment permission.

The required chain is governance mandate -> exact prospective policy adoption ->
explicit producer appointment -> original source/action issuance -> independently
validated runtime exercise. None of these arrows follows from identity alone.

The protected governance transaction owner must independently verify the actual
project owner's exact attributable approval, full canonical transition subject,
scope, effective ordering, expected predecessor/audit head and permitted write
group. The source issuance owner must then authenticate the actual appointed
producer/context and resolve its exact effective appointment and adopted policy.
No implementation of either verification bridge is established by current evidence.
R18 does not choose a credential scheme, signing key, service account, callback
or new login route; these cannot be presumed sufficient.

The producer may establish only one original-holder-only entitlement to the exact
supported historical First Look or Geography action plus decision-bound witness.
It must bind original D (authority ID/body digest), target/installation/family,
operation/private manifest/population, original actor/runtime/context, profile/
generation/owner/auth/MFA scope, activation, exact policy/action and original
consent/deadlines. Producer identity alone cannot select a different action.

Minimum durable attribution is the verified governance decision, exact adopted
policy/action, distinct appointment and scope, original consent/eligibility,
producer identity, protected issuance provenance and confirmed source/genesis/
audit relationship. Full authoritative records must resolve references. No token,
TOTP, key material or persistent PID/Thread field is an authentication substitute.
Unauthorized, unknown, revoked, stale or ambiguous issuer provenance denies
issuance/use without a usable result; no fallback to a generic audit append.

**Decision B.** Existing ownership and authentication provide foundations but
not the missing grant-right bridge. Required explicit security approval: an
authenticated exact-action governance-to-producer transition/issuance contract
within the accepted mandate, preserving separate adoption and appointment. No
additional human approver or new mandate is presumed necessary; no runtime right
is granted by this requirement decision.

## 3. Complete-effect proof

### Canonical complete effect from actual writer definitions

The inspected
[`permanent.finalize()` and `_verify_operation_records()`](../src/review/recognition/permanent.py)
require a canonical reviewed private manifest, regenerate historical `_prepare`
under reservation, compare the full manifest, verify rule consistency, write the
fixed family records, check actual records and foreign keys, then authorize/commit
under that writer's existing separate permissions. These validators do not
themselves confer runtime mutation/attestation authority.

| Required effect | Complete evidence, not a subset |
| --- | --- |
| Rule | Exact `recognition_private_rules` canonical definition/digest, whether already identical or inserted; conflicting rule denies. |
| Private operation | `recognition_private_operations` exact manifest, manifest-derived operation identity, authorization reference and actual recorded time. |
| First Look | Exact full `recognition_first_look_claims` candidate set; every claim's canonical data/integrity and regenerated qualifiers/competitors; existing conflicting claim denies. |
| Geography scopes | Exact `recognition_geography_scope_identities`, scope snapshots and complete `recognition_geography_members`; previously sealed scopes deny. |
| Geography awards/support | Exact full `recognition_geography_awards` and `recognition_geography_witnesses`, with canonical candidate data, numerators/denominators and actual supporting facts checked through integrity readers. |
| Decision witness | Exact original D, sole pending/start event, authoritative source/scope and digest of complete actual-effect evidence in the same target transaction. Geography support witnesses are not this outcome witness. |
| Whole transaction | Exact permitted mutations and absence of extra/partial/unrelated writes, full actual-record checks and foreign-key integrity; confirmed commit plus committed-snapshot inspection. |

The canonical effect is determined by the exact frozen manifest and existing
family rules, not an arbitrary caller evidence digest. This table defines proof
obligations, not a new evidence field set or a complete implemented effect encoder.
[G5](recognition-runtime-original-holder-atomic-enforcer-implementation-design-4e-20-G5.md)
still leaves the privileged complete-effect evidence/write proof incomplete.

The required proof producer/attester is only the prospectively entitled original-
holder transaction owner. It must derive evidence from actual rows after all
effects, create the exact witness inseparably with those effects, confirm commit,
then independently inspect the committed target before asserting a durable fact.
No currently appointed component is authorized to do that runtime attestation.
[Z34](recognition-runtime-target-mutation-commit-attestation-contract-4e-20-Z34.md)
already distinguishes attempted mutation, verified uncommitted rows, confirmed
target commit, and separate control recording; those meanings must be preserved.

[`runtime_decision_outcome_journal_schema`](../src/review/recognition/runtime_decision_outcome_journal_schema.py)
validates inert decision/event/witness DATA. Its witness's effect digest cannot
prove business rows existed, that the producer was entitled, or that commit
occurred. An audit record, witness bytes or successful INSERT alone is not proof.

Partial/missing/extra/conflicting effects reject pre-commit and require rollback
of the complete target group. Uncertain commit or later unavailable/inconsistent
inspection yields unknown, never assumed success or retryable failure. Correlate
target and control using D and the exact pending reference under
[Z30](recognition-runtime-decision-bound-outcome-journal-contract-4e-20-Z30.md),
not a second independent identity. Later factual outcome recording is not execution.

**Decision B.** Existing family integrity readers and inert witness representation
are necessary but insufficient. The required new primitive is the authorized
same-transaction complete-family-effect/witness attester with exact write proof
and committed-target verification. Approving that privileged boundary and its
full proof obligations is required before implementation; no new witness format
or attestation permission is created here.

## 4. Revocation ordering

### Existing evidence and required order

Existing admin revocation persists primary/session revocation in control; current
readers check revoked flags, ownership, epochs and expiry. Existing managers use
control `BEGIN IMMEDIATE` before target reservation. This serializes cooperating
control writers while held, but does not establish a new policy revocation
producer or a universal in-flight cancellation rule.

[G16](recognition-runtime-g1-adoption-producer-authoritative-storage-protocol-4e-20-G16.md)
preserves project-owner mandate revocation/supersession, appointment revocation
for future eligibility production and independent current policy/source checks.
It does not retroactively rewrite authorities or guarantee cancellation during
irreversible commit. R18 preserves those distinctions.

The required logical order, subject to separately approved enforcement, is:

1. Resolve authentic current adoption/appointment/revocation before source
   issuance; any effective disqualifier denies issuance. Confirm exact original
   issuance/audit before publishing holder eligibility.
2. At finalization acquire actual control-first/target reservations and begin
   the owned transactions before authoritative final validation; validation
   does not by itself grant permission to enter another transaction later.
3. Validate original authority and current applicable revocation under the
   authenticated durable state/order. Reject already effective disqualifiers.
4. Stage only the exact permitted action, verify complete effects/witness and
   immediately before commit perform every required current check, including
   applicable revocation and original deadlines. No cached clear decision.
5. Confirm target commit, inspect committed outcome and perform required fresh
   post-commit checks before result publication. Revocation or uncertainty then
   cannot erase commit, release exclusions or authorize re-execution.

This is a required order, not a newly implemented fence. The missing contract
must define the **linearization point for revocation versus finalization** and
prove that all relevant revocation producers participate in its authoritative
ordering. A durable revocation request, a committed effective revocation and a
request blocked behind a reservation must not be conflated. A pending request
cannot be promised immediate cancellation merely because it exists externally.

Required decision for that contract: revocation already effective before the
finalizer's protected authorization/commit decision must deny the in-flight use.
Revocation ordered after confirmed commit cannot retroactively undo the effect.
What happens between those points must be explicitly serialized/fenced; existing
repository evidence does not establish its complete mechanism or effective point.
No choice of epoch field, interrupt flag, lease, new table or cancellation API is
invented here. Unknown ordering denies usable publication and mutation where
still preventable; an uncertain irreversible outcome requires inspection.

**Decision B.** A new explicit revocation/finalization ordering and fencing
contract requires security approval. Current database serialization is a useful
foundation, not a demonstrated cancellation or revocation linearization primitive.
Revocation is forward enforcement, not retroactive effect reversal or retry
authorization. Appointment revocation alone does not rewrite issued rights.

## 5. Cross-database atomicity remains separate

| Domain | Required effects |
| --- | --- |
| Control SQLite database | Consent/source/genesis/audits; current attempt/history/audit; journal decision/start, durable exclusions and final factual outcome/audit; applicable authentication/governance state. |
| Target SQLite database | Metadata entry under current protocol; full rule/private operation/family effects; target-local uniqueness; exact decision witness in the same business transaction. |
| Process/resources | Original registration, reservation connections/epochs, phase/mode and publication; not durable rows atomically committed with both databases. |

The request's R30 identity requirement is represented by the inspected Z30
contract: original authority ID/body digest D couples exclusions, committed target
witness and correlated control outcome. History hashes name facts, not new decisions.

**Decision B - atomicity remains a separate required primitive.** Separate local
commits and held reservations do not yield a combined atomic transaction. The
issuer bridge, attester and revocation fence cannot make them atomic. The explicit
security/product decision must either accept Z30's split factual-outcome protocol
with uncertainty handling or require a separately authorized storage/transaction
model. Neither choice is made here. No ATTACH, storage move, migration or invented
cross-database rollback is authorized. Absence of control outcome is not proof
of target rollback; missing target evidence is not a retry permission.

## 6. Combined minimum-authority model and rejection criteria

The constrained model can be stated as requirements: one authenticated appointed
issuer -> one original holder -> one original D -> one exact target/family/action
and complete write set -> one immutable bounded interval -> at most one exercise.
No current evidence establishes it as an enforceable combined contract.

Fresh validation, durable duplicate fencing, complete-effect attestation,
authoritative revocation order and crash-stable D are jointly necessary. None
can substitute for another. Existing v1/v2 meanings and original credential/
consent clipping remain unchanged. No separate lifespan or broader observation
reuse follows from this review, and no feasibility claim is made.

Reject any model permitting general-purpose producer permission, arbitrary SQL
or audit/control writes, another target/action/decision, transferable rights,
re-delegation, renewal, retry, recreated original ownership after restart or
recovery-based reauthorization. Reject a model that hides an incomplete family
effect behind an audit/witness hash, assumes physical continuity from a lock,
or treats uncertain revocation/commit as authorization.

## 7. Overall decision and exact next boundary

**B - ONE OR MORE NEW SECURITY PRIMITIVES REQUIRE EXPLICIT GOVERNANCE APPROVAL.**
All three boundaries require explicit security contracts; they have not become
resolved merely because their evidence obligations are listed. Cross-database
atomicity is not the only remaining blocker, so overall C is not justified.
Evidence is sufficient to identify these concrete missing primitives, rather
than leaving the entire assessment unclassified under D.

Stop. The exact required governance/security decisions are approval of:

- The authenticated exact-action governance/appointment-to-source issuer bridge,
  within the existing accepted mandate and without runtime self-appointment.
- The privileged original-holder complete-effect/witness attestation boundary,
  including complete mutation proof and confirmed committed inspection.
- An authoritative durable revocation/finalization order and explicit in-flight
  effective semantics, without retroactive effect rewriting or retry rights.

Independently decide the target/control atomicity requirement as stated above.
No approving actor is invented beyond established mandate scope. A departure
from its scope requires explicit authorization, not an assumed extension.
No R19 consolidated contract, implementation, performance slice or producer work
is authorized by this result. It authorizes no new rights or operational policy.

## 8. Validation and production blocks

Only this document is added. Read-only inspection of R17, G13/G17/G16, G5/Z34,
actual admin revocation and coordinator reservation definitions, family writer/
integrity readers, and inert journal definitions. Document whitespace/local-link
checks and `git diff --check` passed. No pytest, lifecycle, Z18, T, broad suite,
code/schema/policy/permission changes, migration, authority issuance, producer
appointment, target mutation or production/hosted access. No commit or push.

PRODUCTION AUTHORIZATION: BLOCKED

PRODUCTION EXECUTION: BLOCKED

PRODUCTION ACTIVATION: BLOCKED
