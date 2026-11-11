# 4e-20-R21-B - consolidated finalization contract and implementation boundary

## 1. Process and approved baseline

This contract follows the project owner's consolidation directive: one contract,
one separately authorized implementation tranche, one isolated end-to-end
validation campaign, one production-readiness review, then explicit production
authorization. Routine implementation defects are fixed within that tranche;
they do not require another numbered architecture document.

[R16](recognition-runtime-security-finalization-authority-decision-4e-20-R16.md),
[R19](recognition-runtime-security-finalization-new-primitives-governance-decision-4e-20-R19.md)
and [R21-A](recognition-runtime-security-issuer-authority-governance-decision-4e-20-R21-A.md)
authorize design of the narrowly scoped authority and its three enforcement
boundaries. Their permission to design is settled. They are not operational
appointments or evidence that the mechanisms already exist. This document
specifies those mechanisms as prospective implementation obligations, rather
than treating their current absence as a reason for another design stage.

v1 remains 120 seconds and ordinary/default; v2 remains 300 seconds and
prospective/test-only. No 600-second policy, lifetime extension, historical
authority broadening, independent G1 runtime adoption or production execution
is authorized. Prior timing evidence is not reopened and no feasibility claim
is made.

**Decision A - CONSOLIDATED CONTRACT READY FOR IMPLEMENTATION.** This means ready
for one separately authorized non-production tranche, not permission to execute
that tranche now or to activate its results. The trust assumptions, installation
inputs, transaction protocol and acceptance conditions below are mandatory.

## 2. Trust assumptions and authority chain

The trusted boundary is the local application/transaction-owner implementation,
its protected installation configuration and OS/database access controls.
Untrusted callers, request data and issuer credentials are not trusted to choose
their own scope. Arbitrary malicious trusted Python, host compromise or direct
database rewriting is outside the capability model; hashes/private registries
do not isolate against that adversary.

| Transition | Principal, authentication and authorization | Shared binding | Lifetime, audit, revocation and failure |
| --- | --- | --- | --- |
| Mandate -> installation governance binding | Project owner explicitly binds the accepted mandate to one actual enrolled installation-owner identity; no inferred equivalence of conversational owner and runtime account | Exact mandate/revision, installation/target and approving actor/credential scope | Protected deployment input and attributable owner approval; unknown/missing binding disables new governance actions |
| Binding -> issuer entitlement | New protected governance owner verifies that bound identity using existing primary/session/MFA kernels, plus a new exact-action approval scope, and separate explicit adoption/appointment/entitlement decisions | Full approved subjects, exact policy/action, constrained issuer implementation role, original holder/action intent and target/write-set scope | One-use confirmation, immutable bounded interval and linked audit; stale predecessor/current disqualifier rejects |
| Entitlement -> finalization authority | Only actual registered appointed issuer context, independently constrained by governance owner and exact approved subject | Original D, holder, exact operation/private manifest, target/family/write set and issuer-entitlement reference | Original clipped deadlines, one issuance, confirmed commit/cleanup; no retry on uncertainty |
| Authority -> fresh ceremony | Same genuine original holder through private process/Thread/context/runtime registration | Same D and all scope fields, actual connections/reservations/epochs | Current auth/consent/policy/activation/approval/stop/state checks; closure or mismatch denies |
| Ceremony -> verified target outcome | Same fixed-action transaction owner performs complete family effects and derives witness from actual rows | Same D, sole confirmed pending and exact effect inventory | Target effects/witness atomic; precommit deadline/revocation checks; unknown commit denies publication |
| Target -> control outcome/publication | Original manager records factual outcome under exact predecessor and validated committed proof | Same D/pending/witness; no new execution identity | Confirmed control outcome and cleanup required for usable success; otherwise pending/uncertain and no re-execution |

No new principal is appointed by this table. Installation governance binding is
an explicit deployment prerequisite, not a bearer credential or a file the runtime
may create to authorize itself. The installer must not infer it from possession
of a reviewer key, database access, project ownership text or a runtime session.
Disposable tests may provision a synthetic binding to a synthetic owner; production
binding requires actual attributable owner approval at the readiness/authorization
gate. If that input cannot be independently established, the feature stays disabled.

## 3. Authenticated issuer-authority primitive

The new governance owner is a distinct protected context/action scope. It reuses
actual authentication, current ownership, primary/session validity, MFA/replay/
throttle and canonical audit kernels; it does not reinterpret existing admin
actions or operation consent. A fresh exact-action approval must bind the full
canonical transition subject, installation governance binding, expected governance
predecessor/audit head, exact policy/adoption, appointment, intended holder/action
scope, interval and approved permitted write group. Adoption and appointment are
separate approvals even when the same bound person approves both, as G13 permits.

Issuer authentication is actual protected implementation-role registration plus
the original bound actor's current authenticated context. A caller-supplied issuer
name, callback, object, hash or historical record is insufficient. Registry entries
must bind actual PID/live Thread/context, phase, owned connections and transaction
epochs. No raw connection, SQL, commit/rollback or generic factory is exposed.

The governance owner, not issuer input, resolves the independently approved full
subject and creates the one exact issuer entitlement. Its immutable logical body
contains only: format/version; authentic governance-binding/adoption/appointment
references; issuer role; original holder/scope; exact action intent (operation,
manifest/write-set contract, target/family); approved policy; actual issue/expiry;
original credential/consent references; and source decision binding once D exists.
Exact codec/storage projections are implementation details that must have closed
keys and deterministic canonical/digest semantics, not additional permissions.
No token/TOTP/key content or persisted PID/Thread authenticates the body.

Before source construction, the action intent is fixed but no D exists. The
actual authority ID is generated only by the genuine original source constructor.
The entitlement-to-D relation must be committed once with the new source's
eligibility evidence and audits in the new protected producer protocol. It cannot
be appended later to an old authority, accept a caller D, or remain reboundable.
An entitlement identity names approval evidence, never another execution decision.

The entitlement permits one issuer -> one original source/finalization action ->
one D only. No general issuance, target mutation, appointment, transfer,
re-delegation, renewal or retry. A durable unique entitlement consumption and
operation/manifest exclusion must resolve atomically with issuance; in-memory
flags are supplemental. Identical duplicate inspection returns historical DATA,
not another capability. Unknown issuance commit/cleanup publishes nothing usable.

## 4. Constrained finalization authority and lifetime

Finalization permission is a new prospectively issued action binding to the
original canonical source, not an edit to its existing format or permissions.
Its logical subject binds D/source digest, exact consumed issuer entitlement,
original holder and same authorized private finalizer, exact target/installation/
family, operation/private manifest and complete write-set descriptor, policy/
version, original authentication/MFA/profile/generation/owner and activation scope,
actual issue/expiry and original consent/credential references. No caller may
replace any resolved value. Audit presence alone confers no permission.

The new registration is nonconstructible by public callers, opaque, nonserializable,
non-adoptable, process/Thread/context/resource-bound and usable only in its original
ceremony. Neither separate executor nor producer process may inherit the right.
One credential compromise cannot alter a subject enforced by an uncompromised
governance/transaction owner. Full trusted-owner/host compromise is not claimed
to be contained by the same interpreter.

Its validity is the intersection of original source policy, issuer-entitlement/
appointment interval, original primary/session, exact original consent and all
applicable earlier bounds. It never restarts the source clock. No independent
longer lifetime is introduced. Current G2/G13 v1 scope remains v1; a test-only v2
source does not silently receive G1 eligibility or new production permission.
Expired/spent/closed/revoked/unknown scope denies use; existing authorities gain
no rights. Actual time must be monotonic-consistent and checked at required use,
precommit and result boundaries. A blocking commit is not made interruptible by
declaring a deadline; uncertain/late return publishes no usable execution result.

## 5. Complete effect and witness proof

Use actual historical family semantics in
[`permanent.py`](../src/review/recognition/permanent.py), not a synthetic legacy
claim/EXECUTING or a call through widened legacy authorization. Extract only a
private fixed mutation kernel while preserving legacy checks and caller behavior
in its existing compatibility layer. The new finalizer supplies its own explicit
entitlement and owns its transaction; existing writer boundaries remain unchanged.

Canonical expected effects are derived by regenerating `_prepare` against actual
target state inside the writer reservation and comparing the entire reviewed
manifest. Compute a deterministic evidence object from the exact actual records:
fixed table names and primary-key-ordered canonical full rows for the required
rule, private operation, and family rows below, together with D, pending digest,
manifest digest and target scope. No caller supplies future witness/effect bytes.
Hash this evidence using existing canonical serialization and `digest()`.

Exact write proof combines a pre-write protected-state snapshot, private allowed
INSERT authorizer and expected row-level delta. Compare every table's actual
delta to regenerated expected inserts, including rule insertion only when absent;
reject UPDATE/DELETE/REPLACE, DDL, unexpected trigger effects, extra tables, missing/
extra rows or changed unrelated data. Retain full foreign-key/integrity checks
and existing family integrity readers. A table allowlist alone is insufficient.

The witness retains existing Z31 contents exactly: `format`, `decision`, `pending`,
`recorded_at_utc`, `outcome`, `effect_evidence_sha256`. Decision embeds the original
source; pending is the exact complete validated start event; no new witness fields
or independent decision UUID are added. Witness time is event time, not SQLite's
exact commit instant. Its `TARGET_COMMITTED` label is not proof while uncommitted.

All effects and that witness commit in the same target transaction. After confirmed
commit, independently inspect a committed target snapshot, re-resolve actual
identity/schema, validate full witness/source/pending, recompute complete row
evidence and compare its digest. Only that positive durable observation establishes
target success. Contradictory, missing or unavailable evidence is unknown, not
assumed rollback or success. An audit row or detached codec-valid witness is never
complete-effect proof. The control COMPLETED event binds the same pending/witness.

## 6. Complete write set and unchanged boundaries

| Domain / category | Required exact effect |
| --- | --- |
| Governance control | Explicit installation binding references, separate adopted policy/appointment/entitlement records, exact approval consumption and immutable audit relationships; no generic control writes. |
| Source control | Existing consent CAS, consumption audit, canonical authority, exact AUTHORIZED genesis and issuance audit remain the full original group; new entitlement/eligibility relations belong to an explicitly new producer proof, never hidden in the old five-write helper. |
| Attempt/history control | Retain exact attempt, ATTEMPT_CREATED history and creation audit with original authority and genuine continuation; no speculative states or omitted records. |
| Metadata target | Retain required target-entry marker and its immutable scope; it remains metadata, not writer permission. Do not silently remove its established ownership/validation boundaries. |
| Rule/operation target | Verify identical rule or insert missing exact rule; insert canonical private operation under manifest-derived identity and original authorization reference. Existing operation is a conflict for new mutation, not adoptable success. |
| First Look target | Every exact candidate claim and full qualifier/competitor/claim integrity. |
| Geography target | Complete scope identities, snapshots, members, awards and supporting geography witness rows, with all historical population/fact checks. |
| Journal control | Decision creation and permanent operation/manifest exclusions; sole TARGET_PENDING start and linked audit; conditional factual COMPLETED, TARGET_FAILED or TARGET_UNCERTAIN and linked audit. |
| Outcome witness target | Exactly one original-D/pending complete-effect witness in the same transaction as business effects. |
| Live resources | Private owner, connection/transaction identity, reservations/epochs/modes and cleanup/publication. These are not portable durable rights. |

Source, attempt and metadata owners remain separate protected phases in this
tranche; no authority timestamp is moved after a write or refreshed at publication.
The objective is a correct integrated execution boundary, not a promise that
retaining all required validation makes the measured lifecycle fast enough.

Use inert journal definitions in
[`runtime_decision_outcome_journal_schema.py`](../src/review/recognition/runtime_decision_outcome_journal_schema.py)
and existing schema-package/migration/enrollment machinery. Any additive storage
needed by the new logical issuer/action/fence/evidence bindings must preserve
existing formats, manifests and historical semantics. Its exact DDL and fixed
mutation proof are reviewable deliverables within the one tranche; no production
migration, reinterpretation of legacy records or invented parallel migration
framework is permitted. Existing readers deny unrecognized/incomplete new state.

## 7. Revocation and finalization ordering

This contract selects **commit-ordered revocation**, not request-arrival cancellation.
For the new policy/appointment/entitlement, every authorized revocation writer and
finalizer must use the same authoritative control database and protected control
`BEGIN IMMEDIATE` ordering. Record immutable attributable revocation referencing
exact identity/scope, effective order and audit predecessor. Runtime/producer
self-revocation powers are not added. Governance revocation uses the explicitly
bound governance identity; existing credential/logout mechanisms retain their scope.

Before any target business mutation, acquire final control reservation, then target
reservation, freshly read complete effective revocation/authorization state and
the sole confirmed pending. Retain control reservation throughout target mutation,
last validation, target commit, committed inspection and control outcome commit.
Keep target reserved through every required control commit; any permitted release
reacquires control before target and repeats required validation. No lock inversion.

A revocation committed before that control reservation must be observed and denies
the affected use. A competing revocation writer blocked behind it has not taken
effect: the finalizer may linearize first if every other check holds. Immediately
before target commit recheck current applicable state/order and deadlines under
the same reservation. This serializes a cooperating revoker versus commit; it
does not promise to cancel irreversible commit when a human request arrives.

After finalizer releases control, a later committed revocation affects future
applicable use, not already committed target effects. Appointment revocation denies
future eligibility issuance; no automatic retrospective rewriting of sources.
Policy/entitlement revocation denies their still-unused action at the ordered
checks. No revocation releases permanent exclusions or renews use. Any mechanism
claiming an externally immediate effect outside this order is unsupported by this
contract and must disable new finalization rather than pretend this fence covers it.

Database/schema/physical identity and independently mutable target facts still
receive actual fresh checks; a control lock supplies no filesystem continuity.
Unknown effective order, missing audit/credential state or reservation loss fails
closed. If a revoker or finalizer crashes while holding a transaction, SQLite
rollback/commit evidence determines durable state, not request timestamps.

## 8. Fresh preparation and final ceremony

Non-authoritative preparation may collect candidate manifests/populations, decode
canonical references and construct expected effect plans before authority exists.
Those outputs confer no permission and must be regenerated/compared where security
requires fresh source state. Only Z15 schema inventory is reusable under its exact
approved continuity. No current auth, approval, physical, history, migration,
claim/control or readiness allow decision becomes a cross-phase cache.

The ceremony must freshly validate genuine original holder and issuer entitlement;
all original policy/credential/consent deadlines and auth/MFA/owner epochs; exact
source/operation/proposal/ACK/effective approval; finalized profile/generation/
installation and independent activation; stop, dependencies/readiness; actual
physical/schema/fingerprint identities; current complete history/claim/control/
migration graph; durable exclusions/pending; and actual resources/epochs/modes.
Use authoritative shared kernels through explicit new narrow adapters, never
forged old context types or caller verifiers.

Sequence: confirmed prospective issuance -> original attempt/entry prerequisites ->
confirmed journal decision and sole start -> final control/target reservation and
fresh validation -> complete target effects and witness -> final checks and target
commit -> committed inspection -> conditional control outcome/audit commit ->
required cleanup/current result checks -> historical success publication.

No target business write precedes full current authorization. Regeneration,
actual-row proof, witness generation and final transaction validation remain inside
the writer reservation. No timing target justifies shortening them. Expiry before
required completion fails closed even if some durable historical prerequisites
exist. No automatic new ceremony or adoptable continuation is created.

## 9. Cross-database outcome decision

For this new contract, the required atomic unit is **complete target family
effects plus their decision witness**. Control records intent/start and later
verified facts; it does not participate in one simultaneous business commit.
This explicitly selects the existing
[Z30 fail-closed coupling protocol](recognition-runtime-decision-bound-outcome-journal-contract-4e-20-Z30.md)
as the implementation requirement, rather than promising combined database atomicity.
It does not rewrite existing transaction helpers or relax target effect atomicity.

Before mutation, DECISION_CREATED/permanent exclusion and sole TARGET_PENDING
must be durably confirmed. Pending spends the sole execution opportunity.
Target commit is allowed before control COMPLETED, but never before its own
witness. COMPLETED is forbidden without positive committed target verification.
Missing/uncertain control outcome remains pending/uncertain and permanently
non-retryable. Thus an incomplete recording window can reduce availability but
cannot produce partial target effects, falsely completed success or another action.

This protocol provides crash-stable evidence, not cross-database atomicity. If the
product later requires all-or-nothing simultaneous control/target visibility,
this contract is inapplicable and implementation must stop for that genuinely
different storage requirement. No distributed transaction or ATTACH is invented.
Deployment must explicitly review and accept the recorded incomplete-window
semantics, rather than describing them as atomic across databases.

## 10. Crash, uncertainty and identity

One D spans entitlement consumption, finalization binding, exclusions, pending,
target witness and control outcome. A different source D cannot retry an excluded
operation/manifest. Historical lookup cannot restore private ownership.

| Failure boundary | Required outcome |
| --- | --- |
| Preparation/issuance failure | No usable preparation/authority on failed or uncertain publication; no automatic retry or adoption. |
| Before pending | Already committed source/exclusions remain historical; no right is recreated after crash. |
| After pending, before/during target work | Permanently spent; known rollback may produce positive no-commit evidence, unknown outcome remains unresolved. |
| Effect before witness / witness failure | Known uncommitted transaction rolls back all effects and witness together; no partial success. |
| Commit ambiguity / connection loss | Publish nothing usable; durable pending blocks another execution. Missing witness alone is not proof of rollback. |
| Target committed, control recording fails | Target fact remains; pending/uncertain remains blocked. No effect re-execution or automatic journal repair. |
| Response lost / cleanup fails / expiry after commit | No recreated credential, repeated effect or inferred rollback. Only exact durable factual inspection is allowed. |
| Contradictory witness/control/effects or unknown revocation | Stop and report inconsistency/unknown, never select a convenient newer row or release a fence. |

This tranche includes original-owner factual recording and read-only inspection,
not a new recovery executor or autonomous outcome resolver. If the original owner
cannot safely finish recording, indefinite pending/unknown is acceptable for
safety. A later independently authorized factual resolver is not necessary for
safe operation and is not silently introduced.

## 11. Security invariants and performance

Required invariants: least privilege; actual original-holder proof; finite immutable
policy/deadlines clipped by original credentials/consent; fresh current validation;
durable once-only issue/start and permanent duplicate exclusions; no transfer,
re-delegation, renewal or retry; exact whole target transaction/evidence; control-
ordered revocation; crash-stable D; attributable confirmed audit/outcome; no usable
publication on uncertainty. Existing writer/readiness/activation/legacy boundaries
are not weakened or made to accept new objects as old capabilities.

Expensive candidate enumeration/evidence construction may occur in preparation
but is not an allow decision. Mutable state must remain fresh; actual regeneration,
effect accounting, witness and integrity checks stay under the target transaction.
No promise is made about completion in 120 or 300 seconds. One successful test
would establish feasibility for that run, not a latency guarantee or permission
to increase lifetime. Failure on time is a failed acceptance gate, not a reason
for another security-design chain or skipped checks.

## 12. One implementation tranche and validation campaign

The next separately authorized non-production tranche shall deliver together:

- Explicit installation governance binding validation, new exact-action approval
  scope, protected entitlement/issuer/finalizer registrations and closed codecs.
- Necessary additive isolated storage/migrations through existing machinery,
  prospective source/entitlement binding, fixed mutation proofs and historical readers.
- Durable once-only issue/start/exclusion enforcement and commit-ordered revocation.
- Private fixed family mutation kernel with unchanged legacy wrapper behavior,
  exact complete-effect evidence/delta proof, existing witness and Z30 protocol.
- Fresh authoritative adapters, original-owner factual outcome recording and
  read-only inspection; uncertainty and cleanup publication fences.
- Focused unit/integration/security/crash tests and required documentation.

Do not enable production permissions, migrate production, issue production
authorities, appoint production producers or activate runtime in that tranche.
Old formats and ordinary v1 issuance remain unchanged. Migration/codec detail
is reviewed within the tranche; only a genuinely new security authority/property
outside this contract warrants another decision stage.

Streamlined validation: focused ownership/codec/transaction tests -> one isolated
end-to-end campaign with a genuinely configured synthetic governance binding and
original credentials -> duplicate/concurrent/replay tests -> original expiry and
ordered revocation races -> crash/uncertain commit at every durable boundary ->
complete actual effect/witness/control verification -> production-readiness review.
Fix ordinary failures within the same tranche and rerun only affected tests; do
not create a new architecture document for each failure. Use bounded external
harnesses, preserve DELETE/WAL semantics and no automatic retry/adoption.

## 13. Single future production-readiness gate and decision

**A - CONSOLIDATED CONTRACT READY FOR IMPLEMENTATION**, conditional on the explicit
inputs and trusted enforcement assumptions above. The authorized primitives are
integrated here; no fourth runtime authority or speculative follow-on primitive
is required. No code, role or permission is created by this decision.

One future review must see the complete implementation and migration/format
compatibility; passing focused/security checks; a complete isolated lifecycle;
actual complete business effects and durable proof; duplicate/expiry/revocation/
crash results; demonstrated pending/unknown behavior and permanent exclusion;
and no unresolved authority ambiguity. It must verify the actual deployment's
explicit governance identity binding, prospective adoption/appointment approvals,
target scope and policy, not transplant synthetic test evidence into production.
It must expressly accept the split factual control-outcome semantics in section 9.

Only after that review may the project owner make a **separate explicit production
authorization** decision identifying deployment, policy, migrations, appointments
and permitted operations. Current v1/default and v2/test-only restrictions remain
until separately approved changes; this contract is not that authorization.

Exact next boundary: **one separately authorized consolidated non-production
implementation tranche under this contract**, followed by the single isolated
validation campaign and production-readiness review. Do not issue R22/R23-style
micro-contracts or execute the tranche in this documentation-only task.

## 14. Validation and production blocks

Only this document is added. Read-only inspection of R15-R21-A, actual authority/
consent/coordinator/revocation and inert journal definitions, family writer and
G17/Z30 ownership/protocol requirements. Document whitespace/local-link checks
and `git diff --check` passed. No pytest, lifecycle, Z18, T, broad suite, code,
schema, permissions, migration, authority issuance, appointment, target change,
production/hosted access, commit or push.

PRODUCTION AUTHORIZATION: BLOCKED

PRODUCTION EXECUTION: BLOCKED

PRODUCTION ACTIVATION: BLOCKED
