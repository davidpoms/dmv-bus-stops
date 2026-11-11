# 4e-20-Z19: authority-bound lifecycle redesign decision

## Decision

Retain the 120-second ceiling and fail closed. The measured post-Z15 composition
cannot complete under that ceiling in this run. No replacement executable path
is currently defined by the approved contracts. Recommend operational option F
(keep the runtime path blocked), followed by a narrowly scoped contract review
of B/C: non-authoritative attempt intent within the original ceremony and late
authority construction. This is a proposal for review, not authorization to move
checks, change ordering, merge owners, or implement another ceremony.

No numeric lifetime extension, new evidence continuity, recovery/adoption,
implementation or further measurement is approved by this document.

Sources: [Z14 and Z15-C](recognition-runtime-preauthority-preparation-late-issuance-contract-4e-20-Z14.md),
[Z16](recognition-runtime-remaining-preparation-inventory-review-4e-20-Z16.md),
[Z17](recognition-runtime-lifecycle-composition-decision-4e-20-Z17.md),
[Z5](recognition-runtime-admission-lifetime-contract-4e-20-Z5.md), and the single
Z18 child report at `.tmp/recognition-z18-deadline-trace.json`.

## 1. Z18 baseline and limits

All times below belong to that one run. Intervals overlap; do not sum them.

| Stage | Start/end from child start | Duration | Remaining authority | Outcome |
| --- | --- | --- | --- | --- |
| Issuance/admission | 88.831 / 169.133s | 80.302s | Not issued at entry; 85s at exit | Success |
| Z15 schema inventory, nested | 133.707 / 133.713s | 0.006s | Not issued | Success |
| Issuance final validation, nested | 133.773 / 169.129s | 35.356s | 120 to 85s | Success |
| Attempt creation | 169.133 / 253.538s | 84.405s | 85 to 0s | Failure |
| Attempt final validation, nested | 218.206 / 253.534s | 35.328s | 36 to 0s | Failure |
| Metadata-owner admission/final validation | UNMEASURED | UNMEASURED | UNMEASURED | Not reached |
| Mode transition / target-entry INSERT / target commit | UNMEASURED | UNMEASURED | UNMEASURED | Not reached |
| Reacquisition / post-commit validation / result publication | UNMEASURED | UNMEASURED | UNMEASURED | Not reached |

The exact failure was `AdminError: administrative_session_expired_or_revoked`.
The authority expiry is appended to the manager's authentication deadlines by
`runtime_activation_authority_issuance._persist()`, using that error code. The
report recorded zero authority budget; the name alone would not establish which
deadline expired. Consent validation succeeded. The authority issue/expiry were
`2099-01-01T00:18:33Z` / `2099-01-01T00:20:33Z` on the disposable clock.
Z15 ran once and reused inventory reads; it did not solve the composition budget.
The external 360-second timeout was not reached. No usable attempt result,
metadata result, writer or execution capability was published.

This demonstrates failure of the measured composition, not an exclusive lower
bound on every possible implementation or a worst-case timing guarantee. No
unexecuted metadata stage may be budgeted as zero.

## 2. Authority-bound work decomposition

The source of truth is
[`runtime_execution_coordinator.py`](../src/review/recognition/runtime_execution_coordinator.py),
[`runtime_activation_authority_issuance.py`](../src/review/recognition/runtime_activation_authority_issuance.py)
and [`runtime_target_entry_owner.py`](../src/review/recognition/runtime_target_entry_owner.py).

### Issuance/admission: what really needs an existing authority?

`coordinator()` creates the original private outer owner before authority exists.
Its issuance `_phase()` obtains control BEGIN IMMEDIATE, then target reservation
and query-only mode, current history/scope/MFA/baseline and registered read views.
It runs `_evaluate()`. `_issue_for_coordinator()` runs fresh `_evaluate()` again,
checks authority exclusions, resolves fresh confirmation, and invokes Z15 `_mint()`.
These reads establish eligibility to issue; they do not require an existing
authority. They already occur before `_body()` samples issue time. They still
require live credentials, consent, original ownership and both reservations.

`_persist()` consumes the one-use confirmation by CAS, calls `_body()`, and writes
the consumption audit, authority, AUTHORIZED genesis and issuance audit. `_body()`
must construct the exact immutable authority after CAS. Its expiry is the minimum
of issue time plus 120 seconds and the existing credential/consent deadlines.
Final `_finish()` validates the current subject and exact five-write graph,
protected state, scope, MFA, query-only target and time, commits control while
holding target reservation, then cleanup permits `_promote()` of the original
continuation. This post-construction work is inherently authority-bound under
the current protocol. An uncommitted authority is not a published continuation.

Thus the entire 80.302s is not authority exposure. The measured nested 35.356s
finalization is inside the authority window. The trace does not exclusively time
all other issuance substeps; no additional movable cost is inferred.

### Why attempt creation took 84.405 seconds

`_create_attempt()` spends the original continuation before opening its phase.
The new phase reacquires control/target reservations and builds current scope,
history, baselines and registered views. Phase entry `_evaluate()` and
`_persist_attempt()`'s `_evaluate()` use the shared admission kernel and
`issuer._subject_for_owner()`. They check live operation/ACK/approval, profile,
activation, authentication, dependencies, readiness, stop and current authority,
consent, history and claim/exclusion state. Z7 inventory is attempt-local only.

`_persist_attempt()` constructs the authority-bound body, validates binding and
expiry, then inserts attempt, ATTEMPT_CREATED history and audit. `_finish()` again
evaluates current state, validates the exact graph, protected baseline and audit
suffix, reads current history and commits control before releasing target.
`_publish_attempt()` requires confirmed commit and cleanup and the original
registered lineage. Failure poisons the owner and publishes no attempt handle.

These are the operations inside the 84.405s span; only the nested finalization's
35.328s was separately measured here. The residual is not a measured attribution
to SQL, locks, schema, pure Python, or a particular duplicated predicate. Required
repetition must not be relabeled redundant from this composite timing.

## 3. Options A-F

| Option | Security-valid under existing contracts? | 120s feasibility | New contract required? | Principal risk |
| --- | --- | --- | --- | --- |
| A: move issuance later | Only Z15's already implemented same-issuance inventory preparation; further relocation is not authorized | Existing composition measured failure; redesign UNMEASURED | Yes for moving construction past existing mutation/finalization boundaries | Backdated/rewritten authority, stale validation, incompatible audit timestamps |
| B: non-authoritative attempt preparation | Not currently defined beyond existing frozen operation intent and schema inventory | UNMEASURED | Yes: exact predicates, owner, bindings, invalidation and final recomputation | Preparation becomes an executable/adoptable attempt or cached admission |
| C: separate preparation from late authority/attempt finalization | Not currently defined; public issuance does not supply an adoptable continuation | UNMEASURED | Yes: same-owner commit protocol and exact graph/ordering proof | Circular authority/attempt digests, premature publication, unvalidated post-write state |
| D: second authenticated metadata ceremony | No: importing an old attempt outside its original owner is forbidden adoption | UNMEASURED | Yes: explicit stage authority, consent, lineage, uniqueness, storage and uncertainty policy | Renewing spent/expired authority via new credentials; multiple winners |
| E: increase lifetime | Not under Z5 or current immutable 120s policy | UNMEASURED even with a proposed larger number | Separate security/policy approval plus dependent contract review | Longer exposure to revoked/stale intent and activation changes |
| F: reject current path; review replacement | Yes to rejection; replacement not yet defined | Current run failed; replacement UNMEASURED | Yes before any replacement implementation | Availability remains blocked; guessing a redesign would undermine safety |

### A: latest issuance

Pre-authority live reads already happen before construction. Z14 explicitly
preserves CAS, body construction, post-write validation and commit ordering.
Moving the timestamp to publication, reissuing after finalization, or treating an
uncommitted body as not yet issued would alter that contract and its digests.
Schema inventory reuse does not authorize reuse of any other observation.

### B/C: proposed review, not an existing handoff

Pure prospective intent might be non-authoritative: canonical operation references
and expected record templates that confer no current validity. But Z14-Z16 do not
define an attempt preparation owner or approve migration/profile/claim/history
evidence transport. Do not create authority-dependent attempt IDs/digests/history
before the referenced authority or fabricate placeholder durable records.

A future contract must distinguish computation of intent from fresh admission.
After actual issuance all required current checks and validation of actual inserted
rows must remain authoritative. Moving expensive reads ahead of issuance and
carrying their allow decisions forward is not permitted. A short final commit is
not established: post-write history, scope, exclusions and integrity must still be
verified. No measured upper bound shows metadata could fit afterward.

### D: separate ceremony

Fresh login/MFA cannot recreate the original process/thread/lifetime registration.
An old immutable attempt is historical evidence, not an executable credential.
Under current contracts a new metadata ceremony consuming it would be adoption.
Any future multi-ceremony alternative needs explicit retirement/uniqueness and
authorization semantics, not a second 120-second clock silently attached to the
same authority. No such mechanism is specified or recommended for implementation.

### E: lifetime change requires independent approval

Review security rationale and trusted-admin threat model, maximum exposure and
credential/step-up/consent freshness, clock rollback, revocation and emergency-stop
latency, activation incarnation, reservation/concurrency behavior and partial
durable work. Review authority codec/storage lifetime policy, attempt expiry,
coordinator/metadata checks and every 4d/4e consumer. Current contracts do not
permit a larger ceiling. A new explicit approval gate and adversarial regression
coverage for boundary expiry, shorter credential deadlines, stale scope,
concurrency and uncertainty would be required. Slowness is not security approval;
a longer number also does not establish completion feasibility.

## 4. TOCTOU and exact multi-phase scope

The following predicates must remain fresh at their existing boundaries:
authentication/expiry/revocation and auth/MFA epochs; activation incarnation;
proposal/ACK/approval/invalidation; dependencies/readiness; emergency stop;
physical hostname/path/device/inode/schema/fingerprint; migration/profile
continuity; current history/audit/control and claim graph; operation exclusions;
reservation/connection/transaction identity and epochs; all accumulated deadlines.
Z10 provides no physical continuity witness. A database reservation does not stop
external filesystem replacement. Hash equality is neither provenance nor freshness.

Any future split must bind the exact original outer/ceremony and PID/thread,
operation/manifest/proposal/ACK/approval digests, finalized G+2 installation,
generation/profile/binding/owner, authentication and MFA scope, independent
activation sequence/digest, consent artifacts and original deadlines, and exact
schema/package policy. Actual reservation/connection/transaction epochs must be
validated in each phase, not declared equal by the caller. These are review
requirements, not a new schema, codec, portable token or approved binding API.

If auth, activation, approval, profile, owner, epochs, physical identity, history,
claims or stop state changes, reject at the existing authoritative boundary; do
not silently refresh, rebind or regenerate the old subject. A claimed immutable
observation is not a current allow decision. All migration relationships remain
fresh even when Z15 inventory is eligible. New phases cannot inherit inventory
permission without their separately reviewed continuity contract.

## 5. Crash, commit uncertainty and adoption

| Point | Required behavior |
| --- | --- |
| Volatile preparation failure/exit | Destroy it; no executable or durable alternate handoff |
| Issuance CAS/inserts before confirmed commit | Existing manager rollback; no published continuation |
| Issuance commit/cleanup uncertain | Poison original owner; publish nothing usable; durable read-only inspection, no automatic retry/adoption |
| Attempt before/during commit | Continuation remains spent; no reconstructed attempt capability from historical rows |
| Attempt commit confirmed but publication fails | Durable state does not confer a new live handle; no second ceremony to resume it |
| Metadata target commit/cleanup uncertain | No usable result, no automatic retry/adoption; missing lifecycle record does not prove rollback |
| Metadata commit confirmed | Reacquire exact reservation and freshly validate before publication; no cross-database atomicity claim |

Control commit must still precede release of target reservation in the existing
issuance/attempt protocol. A future combined phase must explicitly prove ownership,
write permissions, all durable prefixes and post-write validation; it cannot
masquerade as an existing owner. A second ceremony cannot resolve uncertain commit
merely by authenticating again. Duplicate exclusion must survive process restart
without turning an old durable record into a credential.

## 6. Recommendation and exact next contract boundary

No new successful lifecycle can currently be implemented under existing contracts.
Keep F's rejection. The smallest proposed review boundary is **same-original-
ceremony non-authoritative attempt-intent preparation and late authority/attempt
finalization ownership**, examining B/C together without adding another ceremony.

Before implementation that review must enumerate permissible pure intent facts,
prove no attempt or authority exists early, define exact phase/owner lifetime and
invalidation, and specify CAS/body/attempt/audit ordering with no digest cycles.
It must state which reads remain fresh, how changed post-write history/claim/control
state is verified, exact single-winner exclusions, transaction/reservation ownership,
publication conditions and every crash prefix. It must reject any design requiring
unapproved cross-phase observations or a cached admission result. If no useful
work can move under those constraints, record that result rather than inventing
a portable preparation mechanism.

This contract review is not evidence of speedup. Even an approved design would
need a separately authorized bounded same-run measurement through metadata cleanup;
all remaining metadata stages are UNMEASURED. The next boundary is not T, another
blind optimization, a lifetime increase, or implementation of B/C/D.

## 7. Scope and validation

Only this document is added. Run `git diff --check` and new-document whitespace/
local-link inspection. No pytest, Z18, T, production code, migration, schema change,
authority, attempt, target mutation, writer/execution capability, hosted/production
access, commit or push is part of this review.

PRODUCTION AUTHORIZATION: BLOCKED

PRODUCTION EXECUTION: BLOCKED

PRODUCTION ACTIVATION: BLOCKED

WRITER CAPABILITY: BLOCKED
