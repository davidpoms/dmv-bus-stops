# 4e-20-Z22: runtime architecture exit/replacement decision

## 1. Executive conclusion

**Stop further implementation of the current runtime execution composition. A new
security contract is required before any further runtime-path implementation.**
Keep the 120-second ceiling, mandatory fresh checks, immutable history and existing
fail-closed production gates. Do not proceed to T or treat accumulated approved
interfaces as a deployment-ready execution system.

The current measured implementation cannot fit its approved lifetime. That is
different from asserting that no possible implementation can fit. Z18 and the
subsequent reviews establish the former, not a universal impossibility theorem.
They do not justify discarding useful codecs, strict identity checks, audit or
correctness mechanisms. Exit the stalled executable composition, retaining those
mechanisms as blocked infrastructure pending an explicit replacement decision.

No replacement architecture or implementation is approved here. Select D,
reject/rearchitect, as the current operational decision. B (a new multi-phase
model) and C (a different lifetime policy) remain distinct future security choices,
not workarounds authorized by this document.

## 2. Established evidence

Sources:
[Z5 lifetime policy](recognition-runtime-admission-lifetime-contract-4e-20-Z5.md),
[Z19 architecture review](recognition-runtime-authority-bound-lifecycle-redesign-decision-4e-20-Z19.md),
[Z20-R payload/write set](recognition-runtime-attempt-preparation-late-finalization-contract-4e-20-Z20-R.md),
and [Z21 issuance composition](recognition-runtime-authority-issuance-composition-contract-4e-20-Z21.md).

| Z18 single-run fact | Measurement / consequence |
| --- | --- |
| Issuance/admission | 80.302s; includes pre-authority work and nested finalization |
| Issuance final validation | 35.356s, nested; coordinator publication left 85s authority lifetime |
| Attempt creation | 84.405s, including nested 35.328s final validation |
| Failure | `AdminError: administrative_session_expired_or_revoked`; authority budget 0s during attempt final validation |
| Z15 preparation | Executed successfully; inventory construction 0.006s |
| Metadata admission, mode transition, entry INSERT, target commit, reacquisition, post-commit validation | UNMEASURED; not reached |
| Consent / external watchdog | Consent valid; external 360-second timeout not reached |
| Usable outcome | No usable attempt/metadata result or writer/execution capability |

Do not add nested durations or combine earlier runs to manufacture a complete
budget. The 80.302s is not all authority age: much of it already precedes authority
construction. Neither a successful test command nor a complete diagnostic report
is a successful protected lifecycle.

## 3. Current lifecycle constraint

There is an existing security-valid path of code that fails closed, but **no
existing contractually supported, demonstrated path to successful completion
within 120 seconds**. Current contracts allow no additional useful preparation
payload beyond phase-local schema inventory and no supported reduced attempt or
issuance finalization. A faster host or another noisy run is not a new contract
or a validated deployment plan.

The irreducible *logical obligations* under current contracts are:

- After authority construction: actual confirmation consumption, canonical
  authority, exact three-field AUTHORIZED genesis evidence, linked audits,
  fresh current admission and actual post-write integrity checks, confirmed
  control commit with target reserved, cleanup and original continuation publication.
- During attempt creation: fresh actual reservation/authentication/scope,
  authority/approval/ACK/profile/activation, dependencies/readiness/stop,
  physical/schema and current claim/history/control validation; the atomic
  attempt/history/audit inserts and their actual post-write validation; confirmed
  commit and original-owner publication.
- During metadata entry: all approved owner, identity, deadline, mode-transition,
  target-entry transaction, reservation reacquisition and post-commit validation
  requirements. Their costs remain UNMEASURED.

These are required operations, **not measured irreducible durations**. No exclusive
lower bound establishes that every equivalent algorithm needs the observed times.

Already before authority construction: original owner/reservation establishment,
initial current admission/scope/subject, exact consent/exclusion checks and Z15
inventory construction. They are not newly movable post-issuance work. Actual
authority-dependent graph, body/digest/time and changed audit/confirmation state
cannot be verified before they exist. Z20-R keeps the three attempt inserts
authority-bound; Z21 requires actual issuance post-write validation. Current
contracts do not authorize a different proof in their place.

## 4. Architecture alternatives

### A: continue unchanged

Retain the code and its denial behavior, but reject continuation as a deployment
strategy. There is no approved change that makes the measured downstream path
fit. No further blind performance slice or repeated timing attempt is selected.

### B: new multi-phase lifecycle

This would require a fundamentally explicit stage-authorization model rather
than extending one original authority by new login. A future review must define:

1. Which actions each stage may authorize, each stage's original consent,
   authentication/MFA freshness, absolute expiry and clock-anomaly behavior.
   A phase is not automatically entitled to another 120 seconds.
2. Immutable lineage binding exact operation/manifest/proposal/ACK/approval,
   installation/generation/G+2 profile/owner/epochs and activation incarnation.
   No authority or operation substitution, portable identity claim or silent rebind.
3. Fresh authentication/revocation, activation, physical identity/schema/fingerprint,
   approval/invalidation, dependencies/readiness, emergency stop, current claim,
   history/control state and actual reservation checks at every authorization use.
   Earlier rows can be historical intent, never inherited allow decisions.
4. The distinction between non-authoritative durable intent and a live capability.
   If stage linkage is durable, it must not permit importing the old process-local
   continuation. Any successor authority requires its own explicitly defined
   authorization policy; naming it a stage does not resolve forbidden adoption.
5. Atomic single-winner consumption/retirement, immutable stage history, exact
   idempotency and global operation exclusion across stages, processes and restarts.
   Competing or abandoned phases cannot create multiple executable winners.
6. Complete crash-prefix and uncertain-commit rules, authenticated durable
   inspection, explicit stop/retirement behavior and no automatic retry/adoption.
   Absence of publication is not proof of rollback. Separate databases remain
   non-atomic, and a second ceremony does not resolve an uncertain first commit.
7. Precise manager ownership, connection/transaction/reservation epochs, target
   held through required control commits, capability lifetime and publication.
   No speculative writer/execution authority during preparation.

This list is a required review agenda, not a newly defined usable contract,
schema, handoff, credential or successor-authority API. Under today's model,
continuing an old attempt through a second ceremony is unsafe forbidden adoption.
A separately designed model is **undefined**, not proven inherently unsafe in
all possible forms. Fresh login alone does not make it safe.

### C: new authority-lifetime contract

A longer ceiling changes exposure policy even if its implementation looks local.
Before approval, establish a threat-model justification for maximum credential
exposure, intended owner intent and revocation/stop latency; define authentication,
MFA/consent freshness, activation changes, concurrent authority use and long-lived
reservations; preserve shorter underlying credential deadlines and clock checks.

Review canonical lifetime policy, codecs, SQL guards, historical validation,
producer, coordinator, attempt/metadata consumers and old-format compatibility.
No silent rewriting or extension of issued immutable bodies is acceptable. Require
explicit security approval, expiry/revocation/concurrency/uncertainty regression
coverage and separate bounded end-to-end evidence before implementation/deployment
claims. No new numeric value is selected. The separate 4d claim lifetime provides
no authority to alter 4e's ceiling. Slowness alone justifies none of these changes.

### D: reject/rearchitect

Retain the current production block and require an explicit new architecture
before continuing implementation. The measured current combination fails; its
full metadata path is not established. Do not claim all possible 120-second
architectures incompatible. A full replacement would need a complete equivalence
or threat-model review of identity, authorization, operation correctness, immutable
audit, concurrency, uncertainty and deployment, not just a faster happy path.
No need to replace every validated subsystem is established.

## 5. Security-model implications

Continuing to reject makes **zero security-model change** and preserves the
strongest existing guarantees, at the cost of unavailable runtime execution.
There is no evidence-based total ordering of B and C as acceptable replacements.
A justified lifetime-policy change might alter fewer ownership concepts than a
multi-phase model, but enlarges authority exposure and contradicts the currently
mandatory ceiling; it is not approved or recommended for speed. B can seek to
retain short per-authority windows but introduces successor authorization,
lineage/consumption and abandonment semantics that do not currently exist.

Thus D's stop-and-review is the smallest approved change now. Any replacement
must be judged against explicit threat-model requirements; document count,
implementation size or likely speed is not a security comparison. Retaining
freshness, exact bindings, original ownership and uncertainty denial remains
mandatory unless a future security decision explicitly and precisely supersedes
a contract. This document supersedes none of them.

## 6. Decision matrix

| Architecture | Existing-contract support | 120s compatibility | Security-model change | Recommendation |
| --- | --- | --- | --- | --- |
| Current lifecycle | Existing fail-closed owners and formats; no supported shorter finalization | Measured failure; metadata UNMEASURED | None to preserve rejection | Do not continue as a deployable execution path |
| New multi-phase lifecycle | Not defined; current second-ceremony adoption prohibited | UNMEASURED; multiple clocks are not proof | New stage consent/authority lineage, freshness, single-winner and uncertainty semantics | Only an explicit future architecture/security review; no implementation |
| Longer authority lifetime | Contradicts retained Z5/Z13/Z19 ceiling | Not compatible with current policy; replacement feasibility UNMEASURED | Larger permission exposure and reviewed versioned lifetime/consumer policy | Not selected; independent threat-model justification required |
| Full runtime redesign | No replacement defined; operational rejection supported | UNMEASURED | Potentially broad; retain proven correctness/security mechanisms | Stop current executable composition; choose scope only through explicit replacement review |

## 7. Further-work determination

No further performance investigation is justified **as the automatic next step**.
Z15 already applied the only newly permitted preparation reuse. Z20-R and Z21
identified no additional useful payload or shorter supported finalization. Do not
repeat Z18, run T, weaken physical checks, introduce cached mutable observations,
or manufacture another micro-optimization from a slow composite span.

Future investigation could be separately justified by a concrete equivalent
validation algorithm or contract-supported redundant operation, with exact
predicate/ownership/invalidation proof and bounded tests. Nothing here identifies
or authorizes such a candidate. Neither this review nor one timing run establishes
a worst-case completion guarantee under arbitrary scheduling or host load.

## 8. Exact next boundary and stopping point

**Stop before any further runtime implementation, target-entry producer, writer
admission, schema change, authority-path change or lifecycle measurement.** Existing
historical/inert state and read-only inspection retain their current meanings.
No new ceremony may reactivate a spent or uncertain original continuation.

The next boundary is an explicit owner-approved replacement security-model choice:
either commission a multi-phase stage-authorization contract addressing section 4B,
independently reconsider the lifetime policy with section 4C's threat-model case,
or keep runtime execution unavailable. Until one is explicitly chosen, no further
implementation contract exists. A design review is not permission to implement
any successor authority or lengthen a deadline. Do not choose automatically on
the basis of elapsed time alone.

## 9. Scope, validation and production block

Only this document is created. Validate `git diff --check` and document whitespace/
local links. No pytest, Z18, T, broad suite, production code, schema, migration,
target state, caching, second ceremony, writer/execution capability, hosted or
production access, commit or push is part of this decision.

PRODUCTION AUTHORIZATION: BLOCKED

PRODUCTION EXECUTION: BLOCKED

PRODUCTION ACTIVATION: BLOCKED

WRITER CAPABILITY: BLOCKED
