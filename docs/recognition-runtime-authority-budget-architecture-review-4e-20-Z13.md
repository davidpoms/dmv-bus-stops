# 4e-20-Z13: authority-budget architecture/security review

## Decision and limits

**APPROVE the architecture review, not an implementation or runtime admission.**
Retain the 120-second ceiling and fail-closed behavior. The current G+2 lifecycle
did not complete within that ceiling in Z12's measured fixture. No feasible
replacement architecture or longer lifetime is approved here. Z and T remain
blocked. The defensible next boundary is a separately reviewed pre-authority
preparation/late-issuance ownership contract, with explicit acceptance or rejection
of each proposed reservation crossing. Implementation must wait for that decision.

This document changes no code, schema, migration, lifetime, authentication,
activation, physical-identity, writer or execution semantics. It authorizes no
production access, target mutation, cache, retry, adoption or new capability.

## 1. Z12 measured baseline

The source is the single `.tmp/recognition-z12-deadline-trace.json` run, not a
combination of historical benchmarks. The requested command reported two passing
diagnostic/setup tests and one failing lifecycle test in 257.61s. The lifecycle
itself ended at 246.898s overall. Preparation before authority issuance is part of
overall elapsed time, not authority age.

| Recorded span | Overall elapsed start/end | Duration | Remaining authority at end |
| --- | --- | --- | --- |
| Authority issuance / coordinator admission | 87.750–150.123s | 62.373s | 97s |
| Issuance final validation, nested in that span | 127.085–150.120s | 23.035s | 97s |
| Attempt creation, including its finalization | 150.123–244.265s | 94.141s | 3s |
| Attempt final validation, nested in creation | 197.285–244.261s | 46.976s | 3s |
| Metadata-owner admission, failed | 245.070–246.895s | 1.825s | 0s |
| Metadata call/result-publication span, failed | 244.265–246.898s | 2.633s | 0s |

The two issuance/admission labels cover the same manager-entry call; they are
not two independent costs. Final validation spans are nested. The last span
contains initial metadata validation, not demonstrated completed cleanup or
publication. No final metadata validation, target mode transition, target-entry
INSERT, target commit, reservation reacquisition or post-commit validation was
reached. Their durations remain **UNMEASURED**, not zero.

Z12 reached the live deadline during metadata-owner admission and published no
usable metadata result. No target metadata DML, business/family mutation, writer
or execution capability followed. The raw classifier says C because it recognizes
only two expiry names. The accepted Z12 review result is deadline failure under
this fixture. The code registers authority expiry using
`administrative_session_expired_or_revoked`; the diagnostic retained `AdminError`
and zero remaining lifetime, but not the exact thrown code. This review follows
the accepted result without claiming the artifact retained more evidence than it
does. No rerun or classifier correction is needed for this review.

This measurement demonstrates failure of this run, not a universal lower bound
for all hosts, a cost estimate for unexecuted stages, or proof that a longer
lifetime is necessary.

## 2. Authority-budget decomposition and actual ownership

Authoritative sources:

- [`runtime_activation_authority_issuance.py`](../src/review/recognition/runtime_activation_authority_issuance.py):
  `_body()`, `_persist()`, `_final_mutations()` and `_issue_for_coordinator()`;
- [`runtime_execution_coordinator.py`](../src/review/recognition/runtime_execution_coordinator.py):
  `_Outer.check()`, `_phase()`, `_evaluate()`, `_persist_attempt()`, `_finish()`,
  `_promote()` and `_create_attempt()`;
- [`runtime_target_entry_owner.py`](../src/review/recognition/runtime_target_entry_owner.py):
  `create_target_entry()`, `_evaluate()`, `_mode()`, `_commit_target()` and `_reacquire()`;
- [Z5 lifetime policy](recognition-runtime-admission-lifetime-contract-4e-20-Z5.md),
  [Z6 observation scope](recognition-runtime-final-validation-observation-continuity-contract-4e-20-Z6.md),
  [Z7 implementation](recognition-runtime-attempt-schema-manifest-observation-slice-4e-20-Z7.md),
  [Z9 consumption review](recognition-runtime-schema-manifest-observation-consumption-contract-4e-20-Z9.md),
  [Z10 physical continuity](recognition-runtime-physical-identity-continuity-contract-4e-20-Z10.md)
  and [Z11 feasibility review](recognition-runtime-lifecycle-feasibility-contract-4e-20-Z11.md).

The original outer coordinator exists before issuance. Its issuance phase obtains
control BEGIN IMMEDIATE, validates history, then obtains target BEGIN IMMEDIATE
and query-only mode. Current scope/MFA, protected baselines and registered views
precede admission. The private issuer consumes the one-use confirmation by CAS,
constructs the authority body and writes its exact five-mutation protocol. Issue
time is sampled in `_body()` after successful consumption. Expiry is the minimum
of issue time plus 120 seconds and the existing credential/ceremony deadlines.

The authority is not usable merely because its body exists: fresh final validation,
exact mutation/audit checks and control commit while target remains reserved must
succeed. Only confirmed commit and both connection cleanups allow original-owner
continuation promotion. Consequently part of issuance necessarily spends the
authority's lifetime before publication. Z12 measured about 23s here. It is wrong
to charge the entire 62.373s to that lifetime or reset expiry at publication.

Attempt creation opens a new phase with different connections/reservations. It
freshly validates current authority and admission, performs pre-insert validation,
then inserts the attempt, its genesis and the exact audit suffix. Finalization
revalidates current scope and the changed graph, protected state and target
query-only/zero-write conditions. Control commit occurs with target held; cleanup
invalidates phase views/epochs. Z12 measured 94.141s across this phase, including
46.976s final validation. Its remaining roughly 47.166s is merely the non-final
remainder: no exclusive component profile proves how much is preparable.

Metadata uses the same genuine original attempt/outer lineage but another reserved
phase, not the same transaction. It marks the attempt spent and binds its own
control/target connections and epochs, then validates current state. The intended
later mode changes, INSERT, target commit, reacquisition and post-commit validation
each have their own checks and invalidation rules. Z12 expired before those steps.

## 3. Fresh-versus-preparable observation matrix

"Preparable" below means non-authoritative data or an explicitly bounded static
predicate. A digest proves content binding, not who observed it or its currency.
No preparable observation is a credential, admission result, continuation,
durable execution permit or restart/adoption token.

| Component | What could be prepared | Required current/fresh part | Existing scope / missing contract |
| --- | --- | --- | --- |
| Schema/manifest | Exact immutable expected definitions, canonical encodings/digests; verified installed static facts within approved M scope | Actual expected package/schema, migration relationships, scope/owner eligibility and physical/schema kernels wherever required; changed row/FK predicates | ZR/Z2/Z3 same-call reuse and Z7 attempt-local M only. Pre-issuance to attempt/metadata transfer is **UNRESOLVED**: needs exact owner, connection, transaction, reservation and mutation invalidation contract. |
| Runtime profile | Immutable binding/challenge/profile/enrollment relationships scoped to exact installation, target, owner, generation and digest | Current binding/profile selection, pending-transition fence, authentication/epochs, actual identity/schema and activation | Z6 P permits only exact same-attempt I1/I2/I3 continuity. No implemented pre-issuance or cross-phase P authority. A future wider contract is **UNRESOLVED**. |
| Historical claim-local integrity | Canonical immutable claim bodies, their own predecessor histories and referenced historical rows under Z6 C | Current disposition/consumption, expiry, operation exclusions, authority/attempt relationships and global FK/current graph | Z6 C is original attempt-transaction scope, not pre-issue transfer. A broader preparation protocol is **UNRESOLVED**. |
| Authentication/expiry | Identifiers/digests can describe intended scope only | Current genuine proof/session, revocation, owner, auth/MFA epochs, ceremony freshness and live deadlines | Cannot move the authoritative decision earlier. No prepared authentication substitute. |
| Activation | Expected incarnation identity can be bound into intent | Current valid incarnation/ledger, suspension and exact authority relationship | Later activation cannot upgrade preactivation intent or stale authority. Fresh check mandatory. |
| Approval/proposal/ACK | Canonical immutable bodies and exact operation/reference digests | Current exact pairing, approval validity/invalidation, current scope and authority binding | Earlier integrity checks do not replace live approval/ACK admission. No host portability or automatic reapproval. |
| Dependencies/readiness | Describe expected dependency snapshot and static policy | Current dependency state, readiness inventory and current exclusions | Cannot freeze the live decision before issuance. Current readers remain authoritative. |
| Emergency stop | Expected operation scope only | Current stop state at every existing boundary | No prepared allow decision. |
| Physical identity | Historical expected tuple/schema may be recorded as data | Actual hostname, paths, devices, inodes and schema as existing kernels require | Z10 found no authoritative continuity/invalidation for external physical changes. Z7 does not remove these checks. |
| History/audit | An immutable predecessor prefix may be described | Current audit head/population/time, new suffix, full applicable relationships and integrity | Complete H cannot cross I1/I2/I3. No approved generic history-delta certificate. Cross-phase reuse is **UNRESOLVED**. |
| Control state | Independently covered static subfacts may be described | Current complete graph, FKs, generations, scope, denial effects and exact write set | Complete V cannot cross the inserts; whole-control "already checked" flags are prohibited. |
| Reservations/epochs | Nothing transferable as authority | Exact registered owner, PID/thread, both connection/transaction identities, phase and epochs | Commit, release, mode change, replacement or reacquisition invalidates the old scope. A lineage is not an unchanged reservation. |

Any future preparatory object must be immutable, source/provenance bound to the
genuine manager, scoped to the exact future operation and subject digests, and
non-executable/non-adoptable. It must be unusable after every relevant change.
Existing registries supply provenance only within their approved lifetimes; a
caller-supplied hash, witness or signed file cannot invent currency. For the
proposed earlier phase, full invalidation coverage is not yet established.

## 4. Security and TOCTOU analysis

Moving a computation is safe only if its predicate remains true until use or is
re-established before use. SQL reservations do not prove filesystem continuity.
Holding the same owner does not prove the same transaction, and holding the same
connection does not prove the same reservation epoch. A longer-held lock also
needs a reviewed contention/cancellation model; it is not an automatic solution.

Z6 creates observations only after complete successful pre-insert validation in
the original attempt phase. It permits continuity across the exact I1/I2/I3
inserts, not across issuance commit, attempt commit or entry into the metadata
phase. Those three inserts do not change M/C/P's covered static facts but do
change attempt existence, global graph/FKs, audit head and complete-control
predicates. Finalization must validate those changes. Current implementations
cannot replace that work with a prior complete-history/control result.

The metadata mode switch invalidates query-only views; target commit ends its
reservation; reacquisition has a new connection/epoch and needs fresh checks.
Nothing in Z6 allows a pre-issue observation to survive those boundaries. Any
proposal to reduce metadata admission must account for each of them separately.
No operation can become portable, approved or executable from static data alone.

## 5. Crash and uncertain-commit analysis

Keep the existing original-ceremony rule: the manager accepts current credentials,
confirmation and exact lookup expectations, not an old authority/attempt ID or
serialized continuation as a resume credential. Issuance promotion requires its
own confirmed commit and cleanups. An authority or attempt from another ceremony,
thread, process, restart or exited owner cannot be adopted even if every field
matches. A genuinely new request must pass existing uniqueness/exclusion gates;
changing identifiers cannot bypass an incomplete or uncertain prior attempt.

A future non-authoritative preparation failure must publish no live authority.
If it wrote any durable preparation state, that would require a separate reviewed
storage/lifecycle contract; none is supplied here. Do not casually add such state.
After confirmation consumption or authority/attempt writes, original transaction
rollback/uncertainty and spent-continuation rules remain authoritative. Silence
does not prove rollback. No automatic retry, refresh, adoption or recovery follows.

Preserve control commit with the target reservation held in issuance/attempt
phases. Metadata target commit, subsequent reacquisition and cleanup have separate
uncertainty: publish no usable result if commit or cleanup is uncertain, inspect
durable state read-only, and do not retry/adopt. There is no cross-database atomic
commit. Splitting phases or moving issuance must not hide a new crash prefix or
publish an object before confirmed commit and cleanup.

## 6. Architectural options

| Option | Security-preserving possibility | Present decision |
| --- | --- | --- |
| A: move issuance later | Do more non-authoritative work before consuming consent and constructing the immutable authority; retain fresh final scope checks, original ceremony and all deadlines | **UNRESOLVED.** Current body is already created after initial admission. Moving issue time after its own finalization would invalidate canonical bodies/digests/audits; moving it after attempt creation violates the attempt's required authority relationship. A new phase/ordering contract is required, not a timestamp adjustment. |
| B: prepare non-executable observations | Prepare exact-operation static facts, then re-establish every changed/live predicate under the proper owner before minting authority | Preferred contract-review candidate, not implementation approval. Z6 supplies useful predicate decomposition but no cross-issuance/attempt/metadata transport. No speedup or sufficiency is established. |
| C: restructure attempt/metadata admission | Separate non-authoritative calculation from a short final authority-bound commit, while preserving every predicate and original continuation | **UNRESOLVED.** Must define transaction/epoch boundaries, original-provenance ownership, exact mutations, changed graph verification, view invalidation and all crash prefixes. Cannot just merge owners or widen 3a, or call final checks "bounded" without evidence. |
| D: extend lifetime | Only a separately approved exposure/freshness policy with an explicit maximum, earliest credential bounds and full codec/schema/reader compatibility review | Not approved and not proven necessary. Slowness alone is not a security rationale. No numeric replacement is selected. |
| E: redesign or reject lifecycle | Retain safe denial; reconsider whether issuance, attempt persistence and metadata validation can be composed as a useful bounded service | Required if no acceptable preparation/reordering contract or lifetime policy exists. Reject deployment of this runtime path rather than weaken mandatory checks. |

## 7. Answers to required decision questions

| Question | Answer |
| --- | --- |
| 1. Can issuance move later safely? | Potentially, only after a new preparation/late-issuance contract. Not as an authorized reorder of current mutations or a reset after publication. |
| 2. Can schema/manifest work precede issuance? | Expected definitions/canonical static data can be computed without authority; transferring verified installed facts requires the missing continuity/invalidation contract. No earlier installed-schema pass grants later admission. |
| 3. Can static/profile observations precede issuance? | Historical data can. Current profile eligibility and physical identity cannot be replaced by it. Wider P observation scope is **UNRESOLVED**. |
| 4. Can claim-local historical integrity precede issuance under Z6? | Not under Z6's existing scope: creation is after genuine attempt pre-insert validation. Extending C earlier requires a new contract, while current claim/global checks stay fresh. |
| 5. What must be revalidated afterward? | All live predicates in the matrix, all uncovered static predicates, exact write proof and changed graph/audit/FK relationships, at each existing boundary. |
| 6. Can attempt creation split into preparation and short commit? | A non-authoritative preparation is conceivable; safe transfer into current commit is **UNRESOLVED**. Attempt durability still requires exact original authority, original continuation and final validation. No pre-authority durable attempt is permitted by current storage. |
| 7. Can metadata admission use Z6 across its boundary? | No. Z6 explicitly excludes the later metadata phase. A separate metadata-phase scope/transition contract is necessary; live physical/auth/activation/stop checks cannot be dropped. |
| 8. Is there TOCTOU risk? | Yes: stale profile, history head, claim disposition, schema, physical tuple, approval, dependencies or reservation state. Content hashes alone do not close any mutable-state interval. |
| 9. Can another ceremony's authority/attempt be adopted? | Must remain impossible. Preparation data cannot create a continuation or authorize loading an existing one. |
| 10. Can crash handling weaken? | No. Every new boundary needs rollback/commit-unknown/cleanup proof before approval. No automatic recovery or inference from missing records. |
| 11. Is longer lifetime necessary? | **UNRESOLVED.** Z12 proves current measured composition failed, not that safely movable work would suffice or that every composition requires more time. |
| 12. What contract would a longer lifetime need? | The separate Z5 policy review described below; a numeric increase is neither recommended nor authorized here. |
| 13. What if neither route is acceptable? | Reconsider the original authority-to-attempt-to-metadata phase decomposition and its bounded-service viability. Keep the runtime path rejected until a reviewed replacement meets the policy; do not start T/writer work. |

For option D, the required new security contract must justify a maximum exposure
window under the trusted-admin threat model; bound stolen/stale authority and
paused-worker risk; retain earliest primary/session/MFA/consent constraints and
paired-clock anomaly rejection; specify live revocation/activation/stop observation
and concurrency/lock implications; and prohibit renewal, replay and adoption.
It must review the lifetime policy identifier, canonical authority validation,
SQL guards, historical readers, attempt/metadata deadline copies, migrations and
legacy compatibility. Current 4d/4e contracts do not silently permit extension.
Required adversarial coverage includes equality/overrun, earlier credential
expiry, rollback clocks, suspension, concurrent revocation, generation/profile/
activation/owner changes, stale approval/dependencies, commit uncertainty and
restart. An explicit separate security approval gate is mandatory before any
policy or schema implementation. No signing infrastructure is invented here.

## 8. Recommendation and exact next boundary

Retain 120 seconds and stop blind performance iterations. Review options A/B/C
together as a **pre-authority preparation and late-issuance ownership contract**.
This is the exact next boundary; no runtime implementation is presently authorized.
The contract must identify the exact existing owner and source read for each
preparable predicate, its future operation/subject binding, its creation point,
every proposed connection/transaction/epoch crossing and authoritative invalidation
for that predicate. Any unsupported crossing must be rejected or reread fresh.
It must specify original consent freshness/consumption, immutable issuance and
attempt ordering, exact mutation sets, final checks and crash/cleanup outcomes.

Only if that contract establishes a complete safe predicate mapping may the next
implementation slice be scoped to one named internal, non-executable preparation
observation and its invalidation tests. There is no approved name/API, transport,
schema, fresh-check omission, durable preparation record or cross-phase token yet.
If the contract cannot establish useful safe preparation, return to the explicit
Z5 lifetime-policy/rejection decision; do not invent a continuity witness.

Before claiming an improvement, future separately authorized tests must prove
unchanged decisions under stale/mutated scope, extra writes, changed audit/claim
graph, physical replacement, reservation loss, expiry, foreign ceremony, process/
thread mismatch, serialization, commit uncertainty and cleanup failure. A later
bounded same-run measurement must include all remaining metadata stages. No
measurement or implementation is performed by this review, and no speedup is
assumed from historical call counts.

## 9. Validation and explicit authority fences

Only this document is added. Run `git diff --check` and the established explicit
new-file whitespace check. Do not run pytest, Z12, Z, T or broad suites. No hosted
or production resource, production database or deployment key is accessed. No
code/schema changes, migration, commit or push occurs.

This review grants no production authorization, execution, activation, writer
authority or target mutation. It creates no authority, attempt, target entry,
completion, seal, readiness receipt, recovery or adoption mechanism.

PRODUCTION AUTHORIZATION: BLOCKED

PRODUCTION EXECUTION: BLOCKED

PRODUCTION ACTIVATION: BLOCKED
