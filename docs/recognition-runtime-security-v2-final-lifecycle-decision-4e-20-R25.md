# 4e-20-R25 - prospective v2 final-lifecycle decision

## 1. R24 baseline and decision scope

[R24](recognition-runtime-security-validation-path-redesign-4e-20-R24.md)
remains blocked on successful end-to-end completion. This document records the
explicit product/security decision requested after that result. It supersedes
R24's instruction to stop for that decision only; it does not rewrite the result
or authorize an architecture change.

**Decision B - AUTHORIZE ONE ISOLATED v2/300-SECOND LIFECYCLE VALIDATION.**

This authorizes the next separately scoped R26 validation, not execution during
R25, production use, a default-policy change or permission changes. The
[R21-B contract](recognition-runtime-security-consolidated-finalization-contract-4e-20-R21-B.md)
remains unchanged. The existing prospective ceiling assessed in
[R8](recognition-runtime-security-lifetime-v2-300-second-policy-decision-4e-20-R8.md)
is used as already approved by the R25 request; no new lifetime is adopted here.

## 2. Measured improvement

R24's final focused validation passed **49 tests and 42 subtests**, including the
prior R22 security coverage. Its final hardened local comparison returned the
same history DATA with **344 -> 86 control statements** and
**0.1147282s -> 0.0317862s** for four history requests. The first request still
performed full validation; later requests shared work only within the exact
registered synchronous evaluation. Mutation, scope and reservation invalidation,
fresh physical identity and historical-path resolution remained enforced.

The isolated R24 run observed:

| Boundary | Earlier R22 result | R24 result |
| --- | --- | --- |
| Issuance final validation | 50.1470s | 6.4246s |
| Attempt admission | 52.8792s | 13.4798s |
| Protected metadata processing | Not reached | 84.9641s; completed with 1s remaining |
| Finalization reservation setup | Not reached | Expired before first finalizer action evaluation |

Cross-run timings are observations, not controlled causal estimates or completion
guarantees. The local equivalence and query-count test establish the specific
redundant-work reduction. R24's full lifecycle preceded its final historical-path
hardening; that hardening passed focused tests but has not had an end-to-end run.
R26 must use the final hardened implementation, not the earlier measured revision.

## 3. Remaining finalization gap

The measured original authority was v1, with exactly 120 seconds between its own
issue and expiry. Attempt creation and the complete protected metadata path
finished before that expiry, including target mode transition, metadata INSERT,
commit, reservation reacquisition and fresh post-commit validation.

Finalization entered with approximately **1 second remaining** and failed closed
at reservation setup with **AdminError: administrative_session_expired_or_revoked**.
Business mutation, witness commit, durable completed outcome and control completion
were not reached. Their timing remains **UNMEASURED**. The remaining untested
suffix is localized to finalization; its correctness or duration is not proved
by reaching its entry.

The child elapsed 297.8813s and the parent returned in 301.8268s, normally reaping
the child within its bound. Those totals include pre-authority preparation and
must not be treated as authority age. Nested spans must not be summed. The
diagnostic pytest pass recorded a valid fail-closed expiry, not business success.

## 4. Option A - accept the v1/120-second limitation

This is a safe available product choice: preserve v1 unchanged, accept that the
observed workload cannot complete under its current schedule, authorize no more
lifecycle work and leave production blocked. It requires no new permission or
security semantics. However, it leaves the optimized finalization suffix untested
despite an existing bounded prospective test policy.

**Not selected.** One constrained feasibility test is justified by the measured
progress and passing focused security regressions. Accepting the limitation
remains possible after that test; this decision does not require eventual release.

## 5. Option B - validate existing v2/300 seconds once

**Selected.** Authorize exactly one fresh, isolated, disposable end-to-end R26
lifecycle under the existing immutable v2 policy, with a maximum of 300 seconds
from actual authority issuance, clipped by the original credentials and consent.
Use one original holder, authority, decision and reservation lineage. Do not
extend, convert or adopt R24's expired authority, attempt or metadata record.

An unclipped 300-second ceiling offers up to 180 additional authority seconds
relative to v1. This is arithmetic policy headroom, not measured finalization
headroom: clipping, runtime variability and the unmeasured suffix can consume it.
**There is no evidence that complete finalization will fit within 300 seconds.**

R26 must exercise the actual version-bound issuer, canonical validation, persisted
constraints and historical readers. Do not simulate v2 by changing v1 timestamps,
relaxing checks or overriding an existing authority's policy. An interface or
fixture failure must be reported accurately, not bypassed to obtain success.

Capture issuance, attempt and metadata boundaries, protected finalization, actual
target effects and witness, independent durable outcome inspection, control
outcome, cleanup and result publication. Keep child elapsed, authority age,
remaining authority budget and parent harness timing separate. Preserve exact
sanitized errors and the corrected bounded harness. A parent timeout is a
measurement failure, not proof of authority expiry.

No automatic retry, renewal, adoption or second run is authorized. Expiry,
uncertain commit or cleanup must fail closed and publish no usable execution
result. Durable inspection may establish facts; it cannot reauthorize mutation.

## 6. Mandatory security invariants

- Bounded immutable policy and original deadlines, credential/consent expiry
  clipping, original-holder binding and fresh final validation remain required.
- Exact execution decision, target, operation, family, action and complete write
  set remain bound; no replacement inputs or arbitrary target SQL are permitted.
- Authentication, activation, approval/proposal/ACK, emergency stop, dependencies,
  physical identity/path, current history/control/claims and reservation checks
  remain fresh at their approved boundaries. No broader observation reuse.
- Duplicate fencing, concurrency protection, revocation and control-before-target
  ordering retain their original semantics. No cross-database atomicity claim.
- Complete-effect verification, atomic target effect plus decision-bound witness,
  independent committed inspection and durable outcome identity remain required.
- Fail-closed uncertainty and no retry after uncertain commit are preserved.

R24's focused results are sufficient evidence to authorize this controlled test,
not a blanket correctness certificate. No unresolved concrete implementation
defect was identified in the reviewed R24 result. Finalization's untested suffix
is precisely what R26 must validate. A concrete defect found there stays within
the implementation process; it does not automatically justify a new architecture.

## 7. Lifetime disposition

v1 remains authoritative/default at **120 seconds**, with all existing v1 bodies,
digests, expiries and historical interpretation unchanged. v2 remains the existing
**300-second prospective test/measurement policy**, not a production default.
R25 changes no policy, schema, validator, issuance code or runtime permission.
Unknown policies fail closed. No v3, intermediate lifetime or 600-second ceiling
is proposed or authorized. A failed R26 run cannot escalate its own deadline.

## 8. G-series and authority-model disposition

Do not reopen G1 or appoint a producer. Do not change issuer/finalizer permissions,
introduce another authority, redesign R21-B or launch another security-architecture
chain. Existing bounded v2 feasibility is the sole question authorized here.

## 9. Decision A-D

**B - AUTHORIZE ONE ISOLATED v2/300-SECOND LIFECYCLE VALIDATION.**

A was evaluated and not selected. C is not selected because R24 identified no
remaining concrete defect requiring correction before this test. D is not
selected because the evidence suffices for one bounded experiment, although it
does not establish operational sufficiency or production readiness.

## 10. Exact next boundary

**4e-20-R26 - one isolated v2/300-second end-to-end lifecycle validation.**

R26 is execution/validation only: no architecture redesign, lifetime increase,
permission change or production access. It must use the final hardened R24 code.
If the complete lifecycle succeeds, proceed directly to **4e-20-R27 - consolidated
production-readiness review**, without architecture stages for individual passing
properties. Success authorizes that review, not production. On failure, report
the actual outcome and stop; this document supplies no further run or escalation.

## 11. Validation and production blocks

Documentation/read-only decision only. Document whitespace/local-link checks and
`git diff --check` passed. No pytest, lifecycle, T, broad suite, code/schema/policy
change, database write, production/hosted access, commit or push occurred in R25.

PRODUCTION AUTHORIZATION: BLOCKED

PRODUCTION EXECUTION: BLOCKED

PRODUCTION ACTIVATION: BLOCKED
