# 4e-20-R20 - integrated finalization security-primitives design

## 1. Baseline and status

[R19](recognition-runtime-security-finalization-new-primitives-governance-decision-4e-20-R19.md)
authorizes design of the issuer bridge, complete-effect attestation and revocation
fence, not their implementation or operational adoption. R15-R18 identify their
missing enforcement contracts. No issuer or producer is appointed; v1/120 and
v2/300 retain their meanings. Cross-database atomicity remains separate.

**C - SECURITY CONTRACT STILL INCOMPLETE.** The integrated requirements below
share one decision and fail-closed protocol, but do not establish the missing
authentication/producer mechanism, complete effect-proof representation or
revocation linearization contract. Design authorization does not authenticate
an issuer or prove those obligations. Atomicity is not the only missing boundary.

## 2. Integrated trust chain

Each row specifies the required transition, not a newly available producer.
For all rows, unresolved authenticity, scope, time, state or commit denies the
transition and usable publication. No failure restores a spent opportunity.

| Arrow | Issuer / subject | Required authenticated evidence and binding | Lifetime / revocation | Failure |
| --- | --- | --- | --- | --- |
| Mandate -> issuer authorization | Project-owner governance authority / exact policy adoption and distinct appointment | Verified G13 mandate, authentic exact-action approval, full subject, predecessor and audit head; G17 executable bridge unresolved | Within exact mandate/scope and effective appointment; current applicable revocation | No appointment or issuance on absent/uncertain approval |
| Issuer -> constrained authority | Actual appointed source producer / original holder | Exact adopted policy/action, original credentials/action-specific consent, source/genesis/eligibility/audit; protected source protocol unresolved | Original immutable policy and clipped deadlines; no renewal | No usable source until confirmed commit/cleanup |
| Authority -> original-holder binding | Protected original issuer / genuine private original context | Original D and actual process/Thread/runtime, actor, resources and scope; IDs alone insufficient | Same original lifetime; closure/spend invalidates | No import, transfer or restart adoption |
| Holder -> fresh final validation | Entitled original transaction owner / exact action | Current source/policy/consent/target/approval/ACK/readiness/dependencies/stop/history/claims/control, actual ownership/resources | Check all deadlines and effective revocation | Reject without new effect permission |
| Validation -> atomic family effects | Same owner / complete fixed family action | Exact manifest regenerated inside target transaction, current duplicate fence and allowed-write proof | Fresh pre-mutation checks; fence must remain applicable | Known uncommitted work rolls back; uncertainty blocks |
| Effects -> complete-effect witness | Same authorized attester / actual staged rows under D | Full actual-record proof, exact D/pending and existing witness definition; proof producer unresolved | Required current deadlines, no future/restamped witness | No witness-only or partial-effect success |
| Witness -> fenced target commit | Same transaction owner / complete effects plus witness | Final current checks, verified exact changes, authoritative revocation order | Revocation checked before action and immediately before commit; ordering unresolved | No assertion of commit from staged rows |
| Target fact -> durable control outcome | Separately entitled original factual recorder / same D and pending | Confirmed target commit plus independently verified committed effects/witness, or positive no-commit evidence | Recording never renews execution; recorder permissions remain separately required | Pending/uncertain is not retryable |
| Outcomes -> result publication | Original manager / historical result only | Confirmed required commits, exact correlation, post-commit validation and cleanup | No new execution interval; required current checks preserved | No usable result on uncertainty |

The requested chain's fence is not an authorization step first introduced after
the witness: it must govern pre-action validation, the transaction and pre-commit
decision. Target and control facts remain separate, not implicitly fused by arrows.

## 3. Primitive A - issuer bridge

The only candidate issuer is an actually appointed constrained original source
producer. It may establish prospective eligibility for one original-holder-only
historical First Look or Geography complete-family-effect/witness action. It may
not adopt policy, appoint itself, execute arbitrary target writes, select another
recipient/target/action, delegate, renew or authorize retry.

The recipient is the genuine original holder, not an independent executor acting
on its behalf. Bind original actor and credential scope, original private process/
Thread/context/runtime incarnation and actual manager resources. No persisted
PID or caller callback establishes that ownership.

Issue-time subject must resolve full authoritative policy/version/action, D,
operation/private manifest and complete write-set contract, target/installation/
family, profile/generation/owner/auth/MFA scope, activation, producer/appointment,
original credential/consent evidence, actual issue time and immutable expiry.
Use existing canonical serialization/digest rules; this is not a new field set
or codec. D cannot be a caller-supplied replacement authority or independent grant.

Required audit attribution is separate authentic policy adoption and appointment,
their exact scope/effective ordering, protected original consent/eligibility,
actual producer identity and confirmed source/genesis/audit graph. Unknown policy,
stale predecessor, altered subject, revoked applicability or uncertain commit
rejects. Original existing authorities receive no later-added rights.

[G17](recognition-runtime-g1-protected-governance-owner-binding-contract-4e-20-G17.md)
does not establish how exact project-owner approval is authenticated by the
manager. Existing runtime/admin authentication authenticates different scopes.
That is still unresolved: R19 authorizes designing the bridge, not inventing
its credential root, trusted callback or appointment. A generic audit writer
cannot authenticate itself into this role.

## 4. Primitive B - complete-effect/witness attestation

The proposed authorized attester is the same original-holder fixed-action
transaction owner, entitled through A. Its canonical effect is the complete
reviewed private manifest regenerated under target reservation and the exact
actual records, including all required supporting facts, not a chosen subset.

Existing witness contents in
[`runtime_decision_outcome_journal_schema.validate_witness`](../src/review/recognition/runtime_decision_outcome_journal_schema.py)
are exactly `format`, `decision`, `pending`, `recorded_at_utc`, `outcome`,
`effect_evidence_sha256`. Outcome is `TARGET_COMMITTED`; the decision embeds
the canonical original authority, whose scope binds the target/action. Pending
must be the exact validated start graph, not an asserted digest. Canonical body
digests and exact relationships provide integrity under the trusted producer/
database boundary, not a new cryptographic signature or global SQLite commit ID.

The attester must derive effect evidence from actual rows after all effects,
verify the whole permitted mutation set and foreign keys, create that witness
inside the same target transaction, confirm commit, and independently inspect
the committed target before asserting durable success. A staged witness using
the existing outcome label is not yet proof of commit. A detached encoded
witness can never by itself prove the actual committed effect.

Partial/missing/extra/conflicting records reject and roll back known uncommitted
work; uncertainty remains unknown. Control outcome must reference the same D,
sole pending and verified target witness/effects. An audit append alone is not
business evidence. Existing parsers validate DATA, not attester privilege or
actual persistence.

The full privileged effect evidence and exact allowed-write proof remain
unresolved under [G5](recognition-runtime-original-holder-atomic-enforcer-implementation-design-4e-20-G5.md).
Existing integrity readers are necessary foundations, not a complete runtime
attester protocol. No new evidence fields or proof algorithm are silently selected.

## 5. Primitive C - revocation/finalization fencing

Existing project-owner governance may explicitly revoke/supersede within G13's
mandate through attributable immutable decisions naming affected identities,
scope and effective order/time. Runtime/source producers gain no such power.
Existing separately authorized credential/scope revocation retains its own scope.
Appointment revocation stops future eligibility production, not automatic
rewriting of issued rights or committed effects. Policy/source current checks
remain independent; unknown applicability denies.

The required ordering is issuance -> durable original provenance -> transaction
reservation/start -> fresh final validation -> exact action/witness -> fresh
pre-commit validation -> confirmed target commit -> committed observation/control
correlation -> cleanup/publication. Applicable revocation must be observed both
at initial current validation before business effects and immediately before
commit; acquisition of an empty reservation transaction may precede those reads.
If any transaction/resource/epoch changes, required checks are repeated.

The final-validation and transaction fence must establish authoritative durable
state and ordering, not a local unrevoked flag. Durable decision/start exclusions
and permanent operation/manifest fences must exclude a second concurrent winner,
including another source D for the same excluded action. No in-memory lock alone
suffices. Control must be reserved before target, with target retained through
required control commit; existing ownership rules are not widened.

However, a precise effective revocation versus target-commit linearization point
and proof that all relevant revocation producers participate remain unresolved.
Actual `admin_auth.invalidate_primary()` serializes its control updates with
`BEGIN IMMEDIATE`; this does not define the future governance fence or promise
that a revocation request blocked behind finalization has already taken effect.
No request-arrival cancellation, new epoch field or universal lease is invented.
Effective disqualification before the protected action must deny; confirmed
commit cannot be retroactively undone. Unknown intervening order blocks usable
publication and mutation where still preventable, then requires inspection.
Crash or uncertain fence state never restores use or permits retry.

## 6. Shared decision identity and complete write set

D is original `authority_id` plus exact canonical authority-body digest under
[Z30](recognition-runtime-decision-bound-outcome-journal-contract-4e-20-Z30.md).
All three primitives must resolve this same D: A originates its prospective
eligibility, B verifies its exact action/outcome, and C fences its sole exercise.
Global policy/appointment/revocation events may have their own factual identities
but confer no independent execution decision. Pending/witness/audit hashes are
facts under D, never replacement grants or permission to diverge.

| Complete required category | Source / placement / constraint |
| --- | --- |
| Original consent/source/genesis/audit | Existing issuer fixed five-write control group: consent CAS, consumption audit, authority, genesis, issuance audit. No hidden eligibility additions to existing proof. |
| Attempt/history/audit | Existing coordinator separate three-write control group. Replacement placement/necessity must be explicitly settled, not dropped for performance. |
| Target-entry metadata | Existing protected owner and separate target transaction; no writer right. Folding/removing its effect requires an explicit contract. |
| Rule/private operation | Target rule consistency or missing exact rule INSERT; canonical private operation with manifest-derived identity and reference. |
| First Look | Entire `recognition_first_look_claims` candidate set and integrity/precondition verification, including competitors. |
| Geography | Complete scope identities, snapshots, members, awards and geography supporting witnesses with full historical population checks. |
| Outcome witness | Exact Z31 decision/pending/actual-effect evidence, in the same target transaction as all family effects. |
| Duplicate/start fences | Permanent operation/manifest exclusion, exact control decision and sole pending/start, target uniqueness; no new D escapes exclusions. |
| Outcome journal/control audit | Immutable decision/history and factual correlated outcome/audit; no general audit write right or automatic recovery recording. |
| Resource/publication state | Genuine connections, transactions, reservation identities/epochs, modes, context lifetime and cleanup; process-local state, not another durable atomic row. |

Actual family effects and verification are in
[`permanent.py`](../src/review/recognition/permanent.py). That SQL block belongs
to its historical authorization/transaction owner; it is not a separately
authorized runtime primitive. Legacy claim/EXECUTING fabrication, discrepancy
paths, capture, arbitrary SQL, execution seals, readiness or activation are excluded.

## 7. Separate cross-database atomicity gap

Control owns source/attempt/history, governance/auth state, decision/start fences
and final outcome/audit. Target owns metadata entry and business effects/witness.
Process-local ownership/publication has still another lifetime. Current local
transactions cannot commit all these effects atomically. Holding both locks or
adding an application witness does not create cross-database atomicity.

Z30 orders confirmed control decision/start, one atomic target effect/witness
transaction, then correlated factual control outcome. Target committed/control
unknown is therefore possible. Existing source/attempt/entry commits are not
retroactively merged by the new authority.

An explicit decision must accept that split factual protocol as the requirement,
or authorize a different atomic storage/transaction primitive. R20 does neither;
no ATTACH, distributed commit, relocation or schema change is assumed. This gap
prevents a complete finalization contract independently of A/B/C's missing details.

## 8. Fresh ceremony and preparation boundary

Before fresh authorization, candidate manifest/source descriptions may be
assembled as non-authoritative evidence. Only Z15 schema inventory may be reused
under its exact same-issuance continuity contract. No prepared migration validity,
approval, readiness, auth, activation, physical identity, dependency, history,
claim, control or reservation allow decision crosses a new boundary.

Required candidate ceremony, not an authorized executable procedure:

1. Resolve genuine original holder/source and authentic prospective issuer scope;
   acquire actual protected reservations and exact original deadlines.
2. Freshly validate full authority/policy/consent/credentials/epochs, operation/
   proposal/ACK/approval, independent activation, stop, readiness/dependencies,
   profile/generation/owner, actual physical/schema identity, current control/
   migration/history/claims, duplicates and authoritative revocation state.
3. Establish the once-only durable start/fence under the separately approved
   producer protocol; resolve its commit before target action. Existing exact
   source/attempt/write baselines cannot be impersonated or silently combined.
4. In the owned target transaction regenerate the full family manifest, recheck
   action/reservation/duplicate/fresh scope, perform only complete fixed effects,
   verify actual records, derive and insert the exact witness. No caller SQL.
5. Verify actual allowed mutations, integrity, current deadlines and effective
   revocation immediately before target commit; confirm commit and required cleanup.
6. Reacquire/inspect committed target evidence with fresh actual identity and scope,
   record the same D's factual control outcome through an entitled recorder,
   confirm its commit and perform required final checks/cleanup before publication.

These steps identify required relationships, not a resolved new phase order or
combined write protocol. Exact producer/owner placement, revocation fence and
complete evidence remain open. Fresh checks cannot be removed to shorten the
ceremony. The effects and witness must be inside the target transaction; current
checks and post-write integrity cannot be prepared before the rows exist.

## 9. Crash and uncertainty protocol

| Event | Required fail-closed treatment |
| --- | --- |
| Crash before finalization / during validation | No recreated original local authority; previously committed source facts are historical only. No adoption after restart. |
| Crash during transaction | Known uncommitted group rolls back; uncertainty stays unknown, not positive proof of no commit. |
| Commit succeeds / response lost | Read-only inspection of exact D/pending/witness/full effects and control history; never repeat the action. |
| Witness failure | Before commit abort complete target group; missing/conflicting committed evidence is uncertainty, not inferred rollback. |
| Control publication failure | Preserve pending/unknown classification; target fact is not erased and no second execution is permitted. |
| Revocation race | Apply authoritative effective order if proved; unknown order denies use/publication, with no fictitious cancellation of committed effects. |
| Duplicate retry | Reject mutation even after known failure, timeout, unknown commit or lost response; historical lookup conveys no right. |
| Database inconsistency / cross-database uncertainty | Stop, publish no usable success, require independently authorized factual inspection; no automatic audit repair or recovery-based reauthorization. |

## 10. Security properties and threat model

The proposed composition requires least privilege (one holder/D/action/target/
complete write set), bounded immutable lifetime clipped by original credentials
and consent, fresh target/scope binding, durable duplicate/concurrency fences,
non-adoptable ownership, exact audit lineage and fail-closed uncertainty. These
are preservation obligations, not claims that the missing mechanisms enforce them.

| Threat | Required defense / residual boundary |
| --- | --- |
| Issuer compromise / producer compromise | Exact appointment/action scope, protected write proof and independent governance provenance reduce deputy powers; compromise of trusted producer/host is not defeated by a digest. Trusted-code boundary and privilege isolation require explicit review. |
| Authority theft / replay | Private original process/Thread/context binding plus original deadlines and durable exclusions; copied DATA is not bearer execution authority. |
| Confused deputy | Resolve full authoritative subjects; reject caller target, manifest, SQL, witness and replacement credentials. |
| Target / decision substitution | Exact D/source digest, actual target identity, full scope and pending/action equality. No new request identity evades permanent exclusion. |
| Stale consent / revoked authority | Current exact consent/credentials and authoritative effective revocation at required pre-action/pre-commit boundaries; unresolved fence prevents readiness claims. |
| Duplicate / concurrent execution | Durable sole start, permanent operation/manifest exclusion and target uniqueness under actual reservations, not Python flags or timeout alone. |
| Partial commit / false or forged witness | Complete actual-effect proof and inseparable target transaction, followed by committed inspection; inert codec/digest alone proves neither entitlement nor effect. |
| Cross-database divergence / crash after commit | Separate correlated facts and no retry/adoption; combined atomicity remains unproved and unapproved. |

## 11. Performance and lifetime disposition

Candidate descriptions and permitted schema inventory may precede authority
construction; no additional reusable observation is authorized. Mutable security
checks necessarily remain fresh. Actual family regeneration/effects/proof/witness
must occur under target transaction; final integrity and commit/post-commit checks
cannot be replaced by intended-action evidence. No claim of completing within
120 or 300 seconds follows. Feasibility remains unmeasured.

v1 = 120 and v2 = 300 remain immutable version meanings; ordinary issuance remains
v1. No 600-second policy or independent action lifetime is approved. Candidate
permission must expire no later than every original source/credential/consent
bound; a separate lifetime or policy applicability would require explicit future
decision. The G13/G2 v1-bound descriptor is not broadened by v2 support.

## 12. Design completeness and exact stop boundary

**C - SECURITY CONTRACT STILL INCOMPLETE.** A coherent shared-decision requirement
model is stated, but the following cannot be silently completed from evidence:

- Authentic exact-action project-owner-to-protected-producer approval bridge,
  without repurposing current runtime authentication or inventing a trust root.
- Privileged exact complete-effect evidence/allowed-write proof and changed owner/
  producer integration, beyond inert witness validation and legacy family checks.
- Effective revocation/finalization linearization and enforcement covering every
  relevant producer, including blocked requests and irreversible commit races.

Atomicity is independently unresolved, so B is not a claim that the three
primitives are otherwise fully defined. A is not justified. No implementation-
design review, new producer or runtime right is authorized.

Stop at an explicit contract decision on those exact missing mechanisms; keep
the separate target/control atomicity requirement decision distinct. Merely
authorizing design again would not supply their missing trust/effect/ordering
definitions. No new follow-on implementation slice, measurement or lifetime
increase is proposed. This review records incomplete design rather than inventing
behavior to make it appear complete.

## 13. Validation and production blocks

Only this document is added. Actual R15-R19 records and authority issuer,
coordinator finalization, admin revocation, family writer/integrity and inert
journal definitions were inspected. Document whitespace/local-link checks and
`git diff --check` passed. No pytest, lifecycle, Z18, T, broad suite, code/schema/
policy/permission change, migration, appointment, authority issuance, target
change, production/hosted resources, commit or push.

PRODUCTION AUTHORIZATION: BLOCKED

PRODUCTION EXECUTION: BLOCKED

PRODUCTION ACTIVATION: BLOCKED
