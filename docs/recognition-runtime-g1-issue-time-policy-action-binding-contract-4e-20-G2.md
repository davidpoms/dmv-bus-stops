# 4e-20-G2: authoritative issue-time G1 eligibility and action binding

## 1. G1 gate blocker and result

[The G1 gate](recognition-runtime-g1-implementation-authorization-gate-4e-20-G1.md)
blocked implementation because original issuance did not establish prospective
G1 policy/action applicability; source-audit and target-attestation integration
also remained incomplete. This document defines a **prospective audit-bound
eligibility proposal**, not a live policy or change to existing authority formats.

**Decision B: one specific primitive remains missing — authorized enforcement of
the exact source-bound action as an atomic verified family-effect/witness target
transaction.** The proposed issuance binding below can distinguish new eligible
sources from old ones, but cannot supply that target attestation/permission path.
No implementation or further implementation/performance slice is proposed.

## 2. Exact issue-time eligibility predicate

Let S be a newly constructed existing-format source authority; D its authority ID
and canonical body digest; P the exact proposed G1 policy; C the exact action
constraint; Q original G1-specific consent; and E original issuance eligibility
evidence. Source S is historically G1-eligible at issue **if and only if**:

1. S passes its existing complete canonical authority/source scope rules and is
   originated by the genuine original private runtime issuer/holder, not imported
   historical DATA. Its one-use source consent and canonical source/genesis/audit
   resolve in the confirmed original issuance transaction.
2. P was expressly adopted by the trusted installation's recognition owner through
   an independently authorized protected administrative decision, before Q and S.
   Adoption is an immutable control audit fact, not an environment switch, browser
   field or inferred consequence of owning the host. This proposal does not grant
   a new administrative adoption API or existing ceremony permissions.
3. P's exact version/digest was effective and not revoked at issuance, with its
   adoption audit preceding Q and E. Canonical adoption/effective time is no later
   than Q and S issue time; effective time cannot precede the actual adoption
   audit's recorded time. Time comparisons and audit ordering are both required.
4. Q is fresh authenticated owner consent explicitly authorizing one G1 action
   grant under that exact P and C, alongside the exact existing protected source
   consent. No old approval/activation/source confirmation is reinterpreted alone.
5. C is recomputed from the same canonical source consent subject used for S,
   binding exact operation/manifest/population, target/runtime profile/epochs,
   activation, proposal/ACK/approval, dependencies/stop/readiness and reason.
6. E binds D, P, adoption, C and Q and occupies the exact original source-audit
   prefix position described in section 8. It commits atomically with source
   confirmation consumption, authority, AUTHORIZED genesis and both existing
   consumption/issuance audits. Missing/conflicting evidence denies eligibility.
7. At actual issue, authentication/access/MFA/consent, exact source subject,
   approval/ACK, independent activation, enrolled G+2 runtime/physical scope,
   reservations, current history/claim/control/migrations/readiness/dependencies/
   stop and all deadlines pass their authoritative current kernels.
8. Source action/family/accounting is the supported atomic historical finalize
   policy. S has original issue time and an expiry no greater than issue plus
   120 seconds and all shorter credentials/consent bounds; no journal or policy
   timestamp starts a fresh window.

Inputs come from current durable source/adoption/consent/audit graphs and actual
registered owner/connection/transaction/epoch/identity observations, not applicant
assertions. Eligibility is established only on confirmed source commit. Partial
or uncertain source issuance never yields usable G1 entitlement.

## 3. Policy version binding

Define a proposed canonical policy descriptor P with exactly these conceptual
keys; this is an audit DATA design, not a new SQL column or implemented codec:

| Key | Fixed meaning |
| --- | --- |
| `format` | `recognition-g1-source-policy-v1` |
| `policy_id` | `original-source-exact-family-witness` |
| `version` | Exact integer 1 |
| `action` | `atomic_historical_family_effect_and_outcome_witness` |
| `max_grants` | Exact integer 1 |
| `lifetime_policy` | Existing `recognition-runtime-authority-lifetime-120s-v1` |

`policy_sha256 = digest(P)` under existing canonical rules. The format/version's
normative semantics are Z37 G1: original-holder-only, no transfer, grant-of-grant,
re-delegation, renewal, retry, general writer, target selection or recovery right.
The descriptor cannot be read as a generic extensible permission list.

The proposed adoption fact must bind complete P/digest, installation, trusted
owner actor and effective time in append-only authenticated control audit.
No secret or raw token is recorded. It is the explicit policy adoption required
by G1, not authority issued to a browser. A revocation fact binds the same P/digest
and installation and takes effect through the authoritative audit order/current
time checks. No update/delete/unrevoke of the old P is permitted. A later policy
revision has a distinct version/digest and applies only to newly originated
consent/authority; no source gains broader actions by resolving “latest policy.”

These are new prospective policy facts. Exact codecs/owner authorizers/storage
integration are not implemented or silently assigned to current administration
transactions. Existing exact audit bodies and SQL/schema are unchanged.

## 4. Exact action constraint

Define canonical C with exactly:

```text
format = recognition-g1-source-action-v1
policy_sha256 = digest(P)
subject_sha256 = digest(exact original source consent subject)
```

The canonical source subject already includes exact operation/reference/manifest/
population, runtime target/profile/generation/install/owner/auth/MFA scope,
physical snapshots/schema, approval and full proposal reference resolving ACK,
independent activation, authentication, dependencies/stop/readiness and reason.
The action format additionally fixes the following non-expandable constraints:

- Exactly one decision D, supplied by E after actual S construction; no preexisting
  D is adopted and no second operation is selected.
- Only supported whole-population First Look or Geography finalize effects with
  their unchanged rule/operation/family verification; no Explorer/source/review
  mutation, discrepancy correction, changed evaluation or per-item quarantine.
- Exactly one unchanged Z31 witness, derived internally from this decision's
  unique pending event and complete actual verified effect evidence, in the same
  target transaction as those effects.
- Exactly the original live runtime holder, subject's profile/activation incarnation,
  actual final manager-owned target connection/transaction/reservation epoch and
  original deadlines. Those actual live resources must be freshly bound when the
  grant is exercised; the issue-time subject does not transport a future epoch.
- No arbitrary witness/target/write/transaction or grant-of-grant; one grant
  construction attempt, no retry after failure/uncertainty, no renewed window.

The future witness's actual effect digest/time cannot be frozen before mutation;
C fixes the derivation and exact source/pending/action, not arbitrary future bytes.
Actual effects/witness must later be verified against that rule.

The existing authority body cannot directly encode P/C: its exact field set and
existing reason/readiness/decision meanings leave no legitimate policy slot.
Do not overload `reason`, readiness policy, operation provenance or consent text.
Its digest can bind the complete unchanged S to E, providing an **indirect immutable
audit relationship** without inventing an extra authority schema field or changing
old codecs. This still requires a new prospective issuance protocol, not acceptance
by the current unchanged issuer.

## 5. Eligibility versus the source grant-right

Only a source satisfying section 2 may possess proposed G1 eligibility. Under
Z37, that eligibility entitles only its genuine original holder to originate one
internally bound action grant when all grant-time conditions and single-exercise
fences hold. The action grant has zero grant-rights and no transfer/redelegation.

```text
authority eligibility != grant issuance != mutation permit != execution authority
```

Historical eligibility remains a fact even after expiry/revocation; **current
usability** becomes false and never broadens. E/P/C/Q, their hashes, general audit,
journal state or a valid detached authority cannot create a live grant registration,
target-write permit or executor. This document creates none.

## 6. No-retroactive-broadening proof

| Case | Required result |
| --- | --- |
| Source issued before adopted G1 | Ineligible; no original E/Q/P chain. Later append or deployment cannot insert evidence into original immutable source prefix |
| Source issued after adoption | Not automatically eligible: exact original E/Q/C and all section 2 predicates must hold |
| Unknown policy/version | Deny eligibility/use; never infer latest compatible version |
| Incomplete/conflicting action binding | Deny; no caller repair or recomputed broader C |
| Policy revision after issuance | Original source stays bound to original P/C; no broader actions; new revision requires new independently eligible source, subject to all exclusions |
| Policy revocation after issuance | Historical eligibility fact is preserved; future exercise/use rejects. Revocation never restores consumed rights or erases committed outcomes |

The old source authority format alone conveys no G1 right. “Issued after date X”
is insufficient. Existing sources retain their exact prior rights, not a new G1
interpretation. No claim is made that every future source can be issued without
changing the source producer protocol; such changes are expressly not made here.

## 7. Minimum target-attestation relationship and exact remaining gap

The required chain is:

```text
original confirmed S + prospective P/C/Q/E eligibility binding
  -> genuine original holder, current grant-time checks and sole journal start
  -> one exact original-owner transaction action grant
  -> complete actual family effects + exact D/pending witness in one target commit
  -> verified durable witness/effects + corresponding control journal/audit outcome
```

Every comparison is exact: D, source subject/action, operation/manifest/population,
target/profile/generation/owner/epochs and activation incarnation. Journal identity
and witness cannot be rebound to another eligible source. Evidence is not authority.
Target/control completion is not one atomic cross-database commit; a target-committed/
control-pending prefix remains excluded/uncertain and can only be resolved factually.

**The missing primitive is authorized exact-action enforcement through the atomic
target mutation-and-commit attestation boundary.** Z33/Z34 supply existing family
integrity foundations and required coupling but no legal runtime grant consumer,
fixed permitted actual write set/producer proof and complete business-effect/witness
verification under that grant. A G1-eligible source does not fill this gap merely
by acquiring eligibility. Neither current legacy writer lease nor metadata owner
accepts it as target-mutation authority. No target behavior is invented here.

## 8. Exact prospective source-audit relationship

Use immutable audit relationships rather than inserting policy fields into the
old authority body or modifying exact old consumption/issuance subjects.

**Q, proposed G1-specific original consent evidence**, must durably bind complete
P/adoption reference and C/digest, the exact original source step and confirmation
artifact digests/subject, actor and consent time, and explicit decision
`authorize_one_g1_action_grant`. It is produced only through fresh protected owner
consent before source issuance; an old source confirmation without Q is insufficient.
Q is not a bearer credential, mutation permit or a later operator assertion.

**E, proposed issue-time eligibility evidence**, binds exactly the conceptual
source/action relationship: format/version, authority ID/body digest, P digest,
policy-adoption audit digest, C digest and Q digest. Actor/time/predecessor remain
in the normal audit envelope. Its source references must resolve full validated
P/C/Q, not rely on a syntactically valid digest. No live PID/thread/token or copy
of every business row is persisted.

Let N be the exact source issuance audit sequence referenced by S's stored source
authority and AUTHORIZED genesis. Prospective eligible issuance must place:

```text
N-2: E, the original eligibility audit
N-1: unchanged-format source confirmation consumption audit
N:   unchanged-format source issuance audit
```

The new eligible-source transaction's proposed ordering is: exact source confirmation
CAS; actual `_body()` construction/time; append E; append consumption audit; insert
source authority and exact AUTHORIZED genesis referencing N; append issuance audit.
These **six mutations** must commit atomically with complete fresh source/final
and exact audit/protected write verification. Target reservation remains held
through control commit. E's body digest does not depend on audit-row digests,
avoiding a circular dependency; audit predecessors link the actual sequence.

This is a deliberate prospective protocol difference from the current five-write
issuer. No current authorizer, mutation proof, codec or transaction is modified
or presumed to accept it. Q/adoption also require explicit future exact typed
audit/consent enforcement, not a generic unvalidated audit append.

For a source already issued at N, the required N-2 slot is already immutable or
does not exist. A later policy/consent/E append cannot occupy it or change N.
Exact source ID/body/action/policy/consent/time comparisons prevent using an unrelated
older event. This structural rule, not timestamps alone, prevents retroactive rights.

Later action grant/outcome auditing must reference D and the original E/C plus
exact journal event/witness digests. There is no need for a second delegation UUID
or full duplicate profile/approval/record dump. The original source supplies intended
permission, target proof supplies actual outcome, control journal/audit records
that fact. Conflicts stop integrity inspection; no domain overrides another by
being newer. Current source audit does not already provide these new Q/E facts.

## 9. Issue-time facts versus fresh grant-use conditions

| Condition | Captured immutably at issue | Must remain fresh at exercise/use/precommit |
| --- | --- | --- |
| Policy/action | Original P/C/Q/E and effective adoption/revocation state | Exact original version/action, no revocation; never resolve latest broader policy |
| Authentication/consent | Original actor, credential/epoch/artifact/subject and deadline bindings | Genuine current original scope/access/revocation/MFA/expiry and live owner; no new login repair |
| Approval/ACK | Exact original pairing/digests/effective history | Current pairing/approval/invalidation must still authorize the same operation |
| Activation/profile | Original independent incarnation, G+2 generation/profile/binding/install/owner/epochs | Current exact match; no reactivation/profile upgrade |
| Physical identity | Actual original host/paths/devices/inodes/schema/fingerprint | Actual strict observations at all required boundaries; no filesystem continuity assumption |
| Stop/dependencies | Exact original bound snapshots/history and manifest | Current authoritative stop/block/history, dependency and whole-population preconditions |
| Claim/history/control/migrations/readiness | Original complete validated source state/assessment | Current graph/exclusions/protected state/FKs, migration/profile continuity and protected readiness |
| Reservation | Original issuance provenance | Actual current original-holder connections/transactions/query mode/epochs; reobserve after reacquisition |
| Time | Actual immutable issue/expiry, clipped by source credentials/consent | Current paired clock strictly before every bound; no restamping/renewal |

Captured facts establish the original decision, never an evergreen allow result.
Actual approved mutation changes require exact post-write/effect proof; earlier
preconditions are not a substitute for resulting record integrity.

## 10. Crash and uncertain commit

| Event | Required policy interpretation |
| --- | --- |
| Source issuance committed, publication failed | Exact P/C/Q/E/source graph may establish historical eligibility, but no new process may reconstruct original holder/continuation or exercise the right |
| Source/eligibility issuance commit unknown | No usable eligibility/grant; validate actual atomic source audit/authority prefix by D. Partial/missing/conflicting prefix denies, never manufactures E |
| Action-grant issuance uncertain | Right remains spent/excluded under single-exercise policy; no alternate grant from new authentication or same D |
| Target execution/commit uncertain | Keep permanent operation/manifest exclusion; positive witness/full effect proof only for factual resolution; no retry |
| Policy revised/revoked later | Original binding immutable; revision adds no rights, revocation denies future use; historical effects remain facts |
| Process/thread/context restart/loss | Original local right/permit unusable; source/policy audit remains historical DATA only |

Authenticated outcome inspection may describe exact facts with no execution/retry
authority. Absence of publication, valid copied identifiers, expired grant, missing
target row on unclear restore lineage or generic audit text cannot establish
eligibility, failure or safe re-execution. No rollback of earlier confirmed commits
is promised and no cross-database atomicity is assumed.

## 11. Decision B

The proposed **issue-time policy/action binding is defined** as prospective P/C/Q/E
plus immutable original source-prefix placement and atomic source issuance. It
requires a new explicit prospective producer/consent protocol rather than widening
old authority semantics or adding a convenient authority field. This slice does
not implement or approve deploying that protocol.

**One specific remaining primitive is the authorized source-bound target-action
enforcement/attestation boundary in section 7.** It must realize the exact grant
in a fixed verified atomic family-effect-plus-witness transaction and provide
positive durable proof for the corresponding outcome. The existing inert journal
and historical/legacy writer contracts do not supply it. Therefore the combined
eligibility/attestation/source-audit readiness criterion for decision A is not met.
This is B, not a claim that a prospective audit-bound eligibility model is inherently
unrepresentable (C). No target authority is inferred to make the answer A.

## 12. Stop and validation

Assessment B stops the architectural chain. No next optimization, implementation
slice, grant, executor, source-format change, migration, target-attestation writer
or lifecycle run is proposed or authorized. No current authority gains G1 rights.

Only this document is created. Validate `git diff --check` and document whitespace/
local links. No Python/schema/migration changes, pytest, Z18, T, broad suite,
grant/permit, target DML/DDL, production/hosted access, commit or push. The original
120-second ceiling and current authority behavior are unchanged.

## 13. Production blocks

PRODUCTION AUTHORIZATION: BLOCKED

PRODUCTION EXECUTION: BLOCKED

PRODUCTION ACTIVATION: BLOCKED

WRITER CAPABILITY: BLOCKED
