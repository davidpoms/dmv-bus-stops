# 4e-20-Z21: authority issuance composition and late-authority review

## 1. Z18 constraint

Decision: retain current fail-closed rejection. Existing contracts do not support
a new materially shorter issuance transaction. The current producer already
performs live verification before constructing authority; splitting that work
into another phase cannot substitute its result for required fresh validation.
No fundamental impossibility of every future design is proven, but the measured
current composition exhausted its authority budget before metadata admission.

Sources: [Z14 and Z15-C](recognition-runtime-preauthority-preparation-late-issuance-contract-4e-20-Z14.md),
[Z19](recognition-runtime-authority-bound-lifecycle-redesign-decision-4e-20-Z19.md),
[Z20-R](recognition-runtime-attempt-preparation-late-finalization-contract-4e-20-Z20-R.md),
and [Z5](recognition-runtime-admission-lifetime-contract-4e-20-Z5.md).

Z18 measured issuance/admission at 80.302s, including issuance final validation
at 35.356s. The coordinator was published with 85s authority budget remaining.
Attempt creation took 84.405s, including 35.328s final validation, and failed at
zero remaining with `AdminError: administrative_session_expired_or_revoked`.
Those nested spans must not be added. Metadata admission and subsequent stages
remain UNMEASURED. The authority lifetime was exactly 120 seconds, consent was
valid, and the 360-second external diagnostic timeout was not reached.

## 2. Current issuance decomposition

The measured path is private coordinator issuance, not a public `issue()` object
subsequently imported into a coordinator. Sources:
[`runtime_execution_coordinator.py`](../src/review/recognition/runtime_execution_coordinator.py)
and [`runtime_activation_authority_issuance.py`](../src/review/recognition/runtime_activation_authority_issuance.py).
Public issuance has its own private manager and duplicate inspection behavior;
it does not mint the original coordinator continuation.

| Issuance operation | Duration/evidence | Requires authority already? | Requires live security state? | Can occur before final issuance? |
| --- | --- | --- | --- | --- |
| Create original outer owner; acquire control then target/query-only reservations | UNMEASURED individually; `_phase` | NO | YES: actual owner/connections/transactions | Already does; reservations must persist through control commit |
| Initial scope/session validation and shared admission | UNMEASURED; phase `_evaluate` then private issuer `_evaluate` | NO before construction | YES | Already does; no reusable allow decision |
| Consent step/confirmation resolution and freshness | Individual `_fresh` calls were about 0.0003-0.0006s, not the cost of complete artifact resolution/validation | NO before construction; repeated post-write | YES | Already does; repeated validation remains required |
| Proposal/ACK/approval | UNMEASURED exclusive cost; `_collect`, `_subject_for_owner` | NO before construction | YES | Already does, then freshly revalidated |
| Readiness and claim-disposition inventory | UNMEASURED; `_subject_for_owner` | NO before construction | YES | Already does; no prepared readiness authority |
| Dependencies and whole-population manifest validation | UNMEASURED; shared admission/subject readers | NO before construction | YES | Already does; no historical manifest allow decision |
| Independent activation | UNMEASURED; current scope/subject | NO before construction | YES | Already does, must stay fresh |
| Physical identity/schema | UNMEASURED; actual observations and scope readers | NO before construction | YES, independent of SQLite locks | Already does, repeated checks remain required |
| Current history/control/claim validation and exclusions | UNMEASURED; `_history`, subject/disposition readers | NO before construction; actual new graph exists only afterward | YES | Preexisting graph already checked; changed graph cannot be validated in advance |
| Schema inventory preparation | 0.006s; actual Z15 hook | NO | Fresh continuity eligibility | YES, only original issuance scope |
| Schema/migration relationships | UNMEASURED exclusive cost | NO before construction; actual changed graph afterward | YES for relationships | Already read before; relationship results cannot be reused under Z15-C |
| Confirmation CAS | UNMEASURED; `_persist` | NO | YES | Must precede `_body`, inside same atomic issuance transaction |
| Canonical authority construction/insertion | UNMEASURED; `_body`, `_authority_row` | Construction creates it; INSERT requires exact constructed body | YES | Cannot insert before actual authority construction or postpone its timestamp to publication |
| AUTHORIZED genesis insertion | UNMEASURED; `_genesis` | YES, exact authority ID/digest | YES: actual graph | Remains after authority insertion |
| Consumption/issuance audit inserts | UNMEASURED; `_persist` | Consumption audit built with actual issue time; issuance audit binds actual authority/genesis | YES | Same transaction; not a separately committed preparation |
| Issuance final validation and control commit | 35.356s nested span; coordinator `_finish` | YES | YES | NO under current ordering; validates actual five-write result |
| Target release, connection cleanup and continuation promotion | UNMEASURED individually; `_phase`, `_promote` | YES | YES: original lineage and confirmed outcomes | NO; publication follows confirmed commit and cleanup |

The table explains what work occurs, not an exclusive attribution of the 80.302s.
There is no measured isolated 80-second pure verification function to move.

## 3. Authority-bound versus pre-issuance work

Before authority: the original owner, reservations, fresh `_evaluate`, exact
consent and exclusions, and eligible Z15 inventory already exist. `_persist`
performs the one-use confirmation CAS; `_body` then samples actual issue time.
The expiry is the minimum of issue time plus 120 seconds and the existing earlier
primary/session/consent deadlines. The exact immutable body is not restamped.

After authority construction: consumption audit, authority, genesis and issuance
audit must match their actual bodies; final `_evaluate`, `_final_mutations`,
scope/MFA/time/query-only checks and manager commit remain required. Target stays
reserved until control commit resolves, then both cleanups precede promotion.
An uncommitted authority already has its issue time; publication does not begin
a new window. This finalization consumed about 35 seconds of the measured budget.

Moving checks already performed before `_body` earlier does not remove that
post-write work. Moving final validation before construction would fail to check
the actual changed confirmation, authority population, audit chain and global
graph. Existing contracts provide no equivalent incremental-validation proof.

## 4. Fresh-validation boundary

This is an inventory of existing requirements, not a proposed new check cadence.
Immediately before construction the original owner must retain complete fresh
admission, consent resolution, exclusions, reservation identity and time checks;
the CAS and `_body` remain inside that protected transaction. Existing post-write
fresh validation before control commit is equally mandatory.

| Predicate | Immediately before construction | Post-write / before commit | Allowed earlier evidence |
| --- | --- | --- | --- |
| Authentication/consent | Current credentials, owner/auth/MFA epochs, revocation, exact artifacts, expiry and one-use CAS | Exact consumed artifact/step, current scope and all accumulated deadlines | No reusable authentication result |
| Operation/proposal/ACK/approval | Current exact pairing/digests and invalidation state | Fresh original subject equality and current eligibility | Frozen content is data only |
| Activation | Independent current incarnation/sequence/digest | Same incarnation, no upgrade/rebinding | No cached activation decision |
| Emergency stop/operation blocks | Current clear state | Fresh current state | None |
| Dependencies/population | Fresh recheck and required current manifest regeneration | Fresh as required by existing admission | None |
| Physical identity/schema/fingerprint | Actual hostname, paths/devices/inodes/schema | All required actual checks repeated | Z15 comparison baseline is not physical continuity |
| History/control/claims | Current graph/disposition, exclusions, baselines and audit head | Actual new graph, exact writes/protected baseline/audit suffix, complete validators/FKs | No reusable whole-graph result |
| Schema inventory | Eligible Z15 only within original issuance phase | Exact five-write continuity proof and live eligibility | Existing Z15 schema definitions only |
| Migration/profile/enrollment relationships | Current finalized G+2 and migration relationships | Fresh current relationships | No relationship reuse under Z15-C |
| Readiness | Fresh existing assessment/inventory | Fresh existing assessment/current subject | No prepared ready flag |
| Reservations/clock | Original PID/thread/context, connections/transactions/epochs, paired clock | Same owned reservations through manager commit, time and no target mutation | No independent lease or portable proof |

## 5. Atomic issuance write set

`_persist` performs exactly five mutations in the original control transaction:

1. CAS `recognition_admin_confirmations.used` from 0 to 1 for the exact artifact.
2. INSERT the exact consumption audit in `recognition_admin_audit`.
3. INSERT canonical authority in `recognition_runtime_execution_authorities`.
4. INSERT AUTHORIZED genesis in `recognition_runtime_execution_lifecycle`.
5. INSERT exact issuance audit in `recognition_admin_audit`.

Storage names are the authority schema's `AUTHORITIES` and `LIFECYCLE` constants;
the canonical body, row projections, linked audit suffix and protected-state
change proof all remain mandatory. These are not five independent commits.

The AUTHORIZED genesis **evidence object has exactly three fields**:
`format`, `authority_id`, `authority_sha256`. Its format is
`recognition-runtime-authorized-genesis-evidence-v1`. Do not add scope, consent,
time, receipt or later-lifecycle evidence fields. The enclosing genesis event
has its existing separate canonical fields; it is not itself the three-field
evidence object. See
[`runtime_activation_authority_schema.validate_genesis_evidence`](../src/review/recognition/runtime_activation_authority_schema.py).

The five mutations can and must remain atomic in control SQLite. Reservation
state is not another durable insert: manager memory/epochs and target reservation
release are not SQLite-atomic with those rows. Control commit is manager-owned
while target remains query-only and reserved. Publication waits for confirmed
control commit and successful connection cleanups. No cross-database atomicity
or executable continuation from a pending row is claimed.

## 6. Ceremony options A-F

| Option | Security-valid under current contracts? | 120s feasibility | New contract required? | Main risk |
| --- | --- | --- | --- | --- |
| A: current issuance unchanged | YES, with fail-closed expiry | Z18 composition failed before metadata; no completion guarantee | None to retain rejection | Issuance finalization plus attempt exhaust remaining budget |
| B: pre-issuance verification, late insertion | Already happens within current owner; a new split is not authorized | Current form failed; redesigned form UNMEASURED | YES for changed owner/phase or retained predicates | Stale admission or skipping actual post-write validation |
| C: same-ceremony protected final issuance | Current protocol already protects final issuance; shorter replacement UNRESOLVED | UNMEASURED for replacement | YES for exact changed write/validation/continuity/commit rules | Original ceremony alone does not prove freshness |
| D: separate issuance ceremony | Public issuance exists but cannot supply an adoptable coordinator continuation | UNMEASURED; not a lawful substitute for the current path | YES for any new handoff/adoption/stage policy | Reconstructing original ownership from a durable authority |
| E: longer lifetime | Rejected under current policy | UNMEASURED; a bigger number is not a guarantee | Separate security decision, not this review | Longer exposure and implicit renewal of intent |
| F: reject/rearchitect runtime design | YES to rejection; new architecture undefined | Current run failed; all alternatives UNMEASURED | YES before changed executable composition | Availability blocked; guessing a replacement compromises safety |

A fails the measured downstream path because only 85 seconds remained when its
continuation was published; attempt creation exhausted that budget before any
metadata check. This does not prove all G+2 architectures fundamentally incompatible
with every 120-second authority model. Metadata costs remain unmeasured and no
valid shorter substitute is currently defined. E remains unapproved under Z5,
Z13 and Z19. A second ceremony is not shown necessary and does not solve freshness.

## 7. TOCTOU and binding analysis

A new pre-issuance phase cannot preserve an allow decision merely by holding the
same operation digest or sharing an outer object. Required bindings are the
original registered ceremony/PID/thread/context, actual phase/connections/
transactions/reservation epochs, exact operation/manifest/proposal/ACK/approval,
G+2 profile/generation/install/owner/binding, auth/MFA scope and deadlines, consent
artifacts/reason and independent activation incarnation. Z15 already binds its
inventory to this original issuance context; it does not grant wider reuse.

Authentication/consent can expire while reserved. Physical identity can change
outside SQLite. Issuance's own writes invalidate old confirmation-use state,
audit head, authority population and global graph predicates. Auth/activation/
approval/profile/physical/dependency/claim/history/control/stop changes must be
handled by current authoritative readers, rejecting mismatches rather than
refreshing intent. Epoch, transaction, connection, owner, clock, code/schema or
unexpected-write changes invalidate any eligible inventory; no wider prepared
observation survives. No event source covers all external invalidation.

## 8. Crash and uncertain commit

Before mutation: no authority or alternate handoff; discard volatile inventory.
During the five writes: roll back known uncommitted work through the manager,
preserving existing safe denial behavior. On commit or cleanup uncertainty,
poison original ownership, publish no usable continuation and inspect durable
state read-only. Absence of a result is not proof of rollback. Confirmed authority
rows after process death are historical records, not importable live authority.
No automatic retry, reissue, timestamp renewal, adoption or recovery is permitted.

## 9. Adoption and concurrency

Control BEGIN IMMEDIATE serializes competitors. Current operation/manifest
exclusions, exact one-use confirmation CAS, schema uniqueness/collision guards
and actual graph validation remain enforced. The private coordinator rejects
existing authority instead of adopting it. Public `issue` may return exact
duplicate inspection data (`retry_authorized=False`, `execution_authority=False`),
but never manufactures another original coordinator continuation from that data.

Cleanup failure prevents `_promote`; matching hashes or a fresh login cannot
replace the missing original owner/notice/phase registration. Separating issuance
and coordinator ceremonies would require a new explicit handoff security policy;
it is not authorized for performance. No process-local lock replaces database
serialization, and no durable row alone recreates a spent continuation.

## 10. Decision

The review is complete with a negative implementation decision. Pre-issuance live
verification is already legal and already performed. No existing contract permits
dropping repeated live checks, carrying mutable results across phases, or moving
actual authority/genesis/audit verification before the writes. Consequently a
materially shorter final transaction cannot be established from current contracts
or timings. Preserve the current rejection; do not reinterpret this as approval
of a new pre-issuance cache or another lifetime decision.

## 11. Exact next boundary

**No implementation boundary is approved.** A concrete proposal for shorter
protected issuance must first specify an exact replacement for post-write
validation: every retained fresh predicate, exact five-write/trigger effect,
changed confirmation/audit/authority graph and FK proof, owner/reservation/clock
scope, permitted intervening state, invalidation and all commit/crash prefixes.
It must prove equivalent security without reusing mutable observations or moving
the authority issue-time origin. If it cannot, retain rejection and revisit the
architecture rather than implement a performance workaround. This document does
not invent that missing proof or imply one exists.

Only this document is added. Validate `git diff --check` and document whitespace/
local links. No pytest, Z18, T, broad suite, code/schema/migration, production or
hosted access, commit or push.

PRODUCTION AUTHORIZATION: BLOCKED

PRODUCTION EXECUTION: BLOCKED

PRODUCTION ACTIVATION: BLOCKED

WRITER CAPABILITY: BLOCKED
