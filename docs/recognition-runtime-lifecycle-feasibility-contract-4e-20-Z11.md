# 4e-20-Z11: runtime lifecycle feasibility under the 120-second ceiling

## Decision

**B — Not demonstrated but potentially feasible.** The approved lifecycle has
not demonstrated sufficient remaining authority lifetime to complete the protected
metadata path. The measurements also do not establish that mandatory stages have
an irreducible combined duration exceeding 120 seconds. Z remains BLOCKED; T has
not started. This review approves no execution, measurement run or implementation.

The [Z5 lifetime policy](recognition-runtime-admission-lifetime-contract-4e-20-Z5.md)
remains authoritative: expiry is the minimum of issue time plus 120 seconds and
the applicable primary/session/producer-step/confirmation deadlines. Equality is
expired. Paired clock/anomaly checks remain mandatory. Setup before issuance is
not authority age; issuance finalization, publication, attempt creation and all
subsequent permitted uses spend the same remaining window. No phase renews it.

## Bounded lifecycle budget

This is an evidence budget, not an estimated completion schedule. **UNMEASURED**
means no complete, separately attributable duration is established for that stage
on the current approved G+2 path. Partial timings and older fixture measurements
below are evidence, not substituted durations. Nested timings overlap; results
from different runs must not be added or subtracted to predict remaining time.

| Stage | Measured evidence | Complete current-path budget |
| --- | --- | --- |
| 1. Authority issuance | Z4 recorded entry to issuance final validation at overall elapsed 129.650s. This is a boundary timestamp, not an issuance duration. Pre-issue setup does not spend authority lifetime. | **UNMEASURED**: issue-time sampling through confirmed issuance cleanup/publication |
| 2. Coordinator admission | Z4 recorded initial evaluation boundaries at overall elapsed 88.494s and 109.043s, and attempt admission at 152.706s. These are separate phase boundaries, not exclusive costs. | **UNMEASURED** as a separate current-path duration |
| 3. Attempt creation | Post-ZR genuine creation phase took 73.699s; confirmed creation occurred at authority age 93s, leaving 27s in that run. This includes validation/finalization and must not be added to stage 4. | **UNMEASURED** for the complete currently approved configuration |
| 4. Coordinator final validation | Z3 comparison: 28.604s to 20.561s. Z7 comparison: 18.147s to 30.732s. Z8 instrumented comparison: 19.302s disabled versus 35.339s reuse enabled. These comparisons are disposable coordinator benchmarks, not complete G+2 metadata lifecycles. G+2 Z4 finalization remained incomplete after 37.53s; another bounded Z run remained incomplete after 32.06s. | **UNMEASURED** complete current G+2 finalization |
| 5. Metadata-owner admission | An older post-ZR run began the first metadata evaluation at overall elapsed 218.016s; it remained incomplete after 21.291s. At interruption, authority age was 117s, leaving 3s. Later bounded runs did not reach this phase. | **UNMEASURED** completed admission |
| 6. Metadata-owner final validation | No completed measured metadata-owner validation sequence exists. The owner has several fresh validation boundaries, not one transferable admission result. | **UNMEASURED** |
| 7. Target mode transition | No successful measured protected transition is established. | **UNMEASURED** |
| 8. Target-entry INSERT | No successful measured protected insertion is established. No insertion is performed by this review. | **UNMEASURED** |
| 9. Target commit | No measured protected metadata commit is established. | **UNMEASURED** |
| 10. Reservation reacquisition | No measured protected post-commit reacquisition is established. | **UNMEASURED** |
| 11. Post-commit validation | No measured complete validation, confirmed cleanup and opaque-result publication is established. | **UNMEASURED** |

The numbered budget follows the requested categories, not a claim that all
validation precedes the mode switch. In
[`runtime_target_entry_owner.create_target_entry()`](../src/review/recognition/runtime_target_entry_owner.py),
the actual sequence includes initial admission, mode switch, fresh post-transition
validation, the fixed INSERT, fresh row/scope validation, return to query-only,
another fresh validation, integrity/FK/time checks, target commit, reservation
reacquisition and fresh post-commit validation. Required cleanup precedes result
publication. Stage 6 covers those pre-commit validation boundaries without charging
them again to stages 7–9; no separate timing for any is available.

Historical partial metadata evaluation is not completed metadata-owner admission.
It does not contradict the current blocked position before demonstrated entry
through the protected path. It supplies neither a successful mode transition nor
any timing for the remaining stages.

## What the efficiency evidence does and does not establish

- [ZR](recognition-runtime-validation-efficiency-review-4e-20-ZR.md) reduced schema
  reads from 80 to 20 over its 20-call reader comparison; elapsed time fell from
  0.047506s to 0.031171s. Its separate creation run left 27s, not a measured budget
  for metadata completion.
- [Z2](recognition-runtime-readiness-claim-efficiency-review-4e-20-Z2.md) reduced
  one readiness inventory measurement from 3.4095s to 3.1060s, manifest calls from
  1,378 to 1,234 and SELECTs from 12,434 to 11,474. All 656 PRAGMAs remained.
  This was not an end-to-end coordinator/metadata measurement.
- [Z3](recognition-runtime-coordinator-final-validation-efficiency-review-4e-20-Z3.md)
  retained required validation counts and 20,288 PRAGMAs in its comparison. Its
  finalization improvement is not an additive saving guaranteed on another fixture.
- [Z7](recognition-runtime-attempt-schema-manifest-observation-slice-4e-20-Z7.md)
  reduced schema reads from 18,274 to 2,124 but did not demonstrate latency or
  lifecycle feasibility improvement.
- [Z8](recognition-runtime-z7-latency-diagnosis-slice-4e-20-Z8.md) measured 12.052008s
  exclusive physical-observation work inside its 35.339s enabled finalization.
  It is included in that total, not another 12 seconds to add. The measurement
  localizes cost; it is neither a universal lower bound nor permission to omit it.
- [Z9](recognition-runtime-schema-manifest-observation-consumption-contract-4e-20-Z9.md)
  and [Z10](recognition-runtime-physical-identity-continuity-contract-4e-20-Z10.md)
  establish no mechanism authorizing removal of the repeated physical checks.
  They add no measured duration or available-time credit.

The Z4 artifact `.tmp/recognition-z4-final-profile.json` stopped at 240.005s overall
with approximately 9.645s estimated remaining and final validation incomplete.
The later reported 242.40s bounded run stopped at authority age 115s, with 5s left
and zero metadata evaluations. Overall fixture elapsed time must not be compared
directly with the post-issuance 120-second ceiling. Neither interruption is proof
of unavoidable expiry. None of these independent remaining-time observations can
be combined into a complete lifecycle trace.

## Mandatory fresh validation versus scoped observations

Fresh live authentication/expiry, approval/proposal/ACK, activation incarnation,
emergency stop, dependencies, readiness and physical identity/schema checks remain
mandatory at their existing boundaries. Current history/audit, claim graph and
control validation remain fresh where mutations invalidate earlier observations.
The three attempt inserts change the current graph; earlier complete validation
cannot simply be carried across them.

[Z6](recognition-runtime-final-validation-observation-continuity-contract-4e-20-Z6.md)
permits narrowly specified continuity for static facts. Z7 implements only the
coordinator-owned schema/manifest inventory observation, bound to the original
attempt phase, owner, connection, transaction, reservation epochs and exact three
inserts. Its existing invalidation and per-consumption eligibility checks remain.
ZR/Z2/Z3 retain their separately approved same-call reuse. No observation crosses
issuance/attempt reservations or becomes a metadata-owner authorization result.
Z6's separately bounded possible profile and historical claim observations are
not implemented reuse permission for this review.

In particular, schema-fact continuity does not establish physical continuity.
Z10 found no authoritative unchanged-physical-identity guarantee or comprehensive
external-change invalidation source. Hostname, resolved paths, devices, inodes and
schema must continue to be checked as required. Synthetic witnesses, SQL locks
and writer leases cannot supply the missing filesystem authority. No saved-time
budget assumes that these checks disappear.

## Feasibility test and single missing measurement

**Does measured data demonstrate sufficient remaining lifetime for all required
stages? No.** A is unsupported: there is no complete measured protected path or
measured remaining-stage budget. C is also unsupported: partial runs, overlapping
timings and a regression do not establish an irreducible mandatory duration above
120 seconds. The defensible classification is B.

The single missing measurement is **one bounded, coherent current-configuration
G+2 end-to-end deadline trace**, sampling the actual authority issue/expiry and
elapsed time at the eleven boundaries through successful protected post-commit
validation and cleanup. It must use genuine independent activation, the original
coordinator/attempt continuation, all approved fresh checks and the existing live
clock. A partial entry-only measurement cannot establish feasibility while later
stages remain unmeasured. This is one lifecycle dataset, not a sum of independent
benchmarks or a new production optimization.

That future measurement requires separate authorization; it is not run here and
does not authorize T, target DML or hosted access. Existing test-only timing and
an external hard bound can observe the disposable path without production-code
changes. It must stop before exhausting the applicable live deadline, preserve
fail-closed cleanup/uncertainty semantics and publish no usable result on failure.
If it cannot finish, record the last boundary and remaining lifetime rather than
retrying automatically or claiming all later stages cost zero. One successful
sample would demonstrate feasibility under those conditions, not a worst-case
completion guarantee under arbitrary scheduling or contention.

No specific redundant security operation with an approved unused continuity
contract is established here. No further micro-optimization is proposed. The next
boundary is the single bounded measurement decision, not T or a lifetime change.
If later evidence establishes C, stop the runtime path for an explicit security
contract decision; do not silently increase the lifetime.

## Scope and validation

This slice creates only this document. Validation is `git diff --check`. No pytest,
Z, T or broad suite is run. No code/schema/migration, deadline, authentication,
readiness, history, claim, physical-identity or activation semantics change. No
target DML, hosted/production access, key read, commit or push occurs.

PRODUCTION AUTHORIZATION: BLOCKED

PRODUCTION EXECUTION: BLOCKED

PRODUCTION ACTIVATION: BLOCKED
