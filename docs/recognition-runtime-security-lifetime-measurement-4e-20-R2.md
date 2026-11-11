# 4e-20-R2: bounded lifecycle measurements for lifetime selection

## 1. R1 baseline and outcome

[R1](recognition-runtime-security-lifetime-reassessment-4e-20-R1.md) found no
quantitative justification uniquely requiring 120 seconds and no complete workload
distribution supporting another number. This slice attempted new measurements
without changing product code, lifetime, policy or validation.

**Recommendation E - evidence remains insufficient.** Two children ran: one valid
fail-closed expiration trace and one external-timeout/infrastructure failure.
There are zero complete successful lifecycle samples. Sampling stopped rather
than retrying after the harness failed to enforce its configured wall-time bound
promptly. R2's measurement objective is incomplete; no new lifetime is recommended.

## 2. Methodology and safety verification

Used the existing `tests.runtime_deadline_harness.run_child()` with its unchanged
360-second timeout. Each sequential child invoked only:

```text
python -B -m pytest tests/test_recognition_runtime_lifecycle_deadline_trace.py::LifecycleDeadlineTraceTests::test_one_g2_lifecycle -q -s -p no:cacheprovider
```

The parent set the existing child-selector flag, preventing a nested parent launch.
No separate Z18 invocation outside the external harness occurred. A temporary
in-memory parent script targeted five samples, capped below eight children, and
stopped on the first infrastructure/invalid measurement. No runner/test/production
Python file was changed. The script saved each result before starting another.

Pre-run inspection verified the configured finite `communicate(timeout=360)`,
timeout kill attempt, final kill-if-needed/wait/reap/pipe cleanup, and parsing of
sanitized structured reports from captured stdout, including after timeout. The
disposable G+2 fixture and writable repository-root adapter were reused unchanged.
All databases, fixture keys and activation state were disposable. No actual
production/hosted database, resource or deployment key was accessed. Source `_body()`
retained its original lifetime; the diagnostic asserted exactly 120 seconds in
both reports. Actual UTC fixture progression was anchored to monotonic time.

These were inspected mechanisms, not an assumption that timeout responsiveness
is guaranteed. Run 2 demonstrated that its actual elapsed bound was not met in
this environment. It returned through the timeout path after 510.753 seconds.
No timeout was increased. The cause of delayed enforcement is **unknown**; no
claim of a SQLite lock, host suspension, GIL cause or production defect is made.

Raw new reports are preserved separately from historical R1 measurements in
`.tmp/recognition-r2-lifetime-samples.json`. They contain each parent's status,
exit/reaping, complete sanitized child report, stages and remaining authority.
The reused child also writes its established `.tmp/recognition-z18-deadline-trace.json`
diagnostic output; the R2 collection preserves both distinct new runs. Historical
measurements are not combined into the sample or distribution.

## 3. Run table and classification

| Run | Parent elapsed s | Child elapsed s | Parent result | Exit / reaped | R2 class | Exact child failure |
| --- | ---: | ---: | --- | --- | --- | --- |
| 1 | 255.878 | 251.840 | Child exited within parent bound | 0 / yes | B: fail-closed authority expiration | `AdminError: administrative_session_expired_or_revoked`, attempt final validation |
| 2 | 510.753 | 504.663 | `subprocess_timeout`; configured 360-second bound exceeded | 0 / yes | C: measurement/infrastructure failure | Preserved child reports the same error during issuance final validation; not a successful sample |

Run 2's child independently labeled itself B, but R2 classifies the run C because
the external bound failed operationally. Parent timeout is **not authority expiry**.
Exit zero does not mean successful lifecycle: this diagnostic accepts a properly
reported fail-closed expiry as a completed test. Run 2 exit zero also does not
prove the kill caused termination; the child may have exited before that attempt.
The authoritative observation is that the parent reports timeout and reaping.

Only **2 of at most 8** children were run. No repeat was attempted after run 2.

## 4. Complete stage observations

Durations below are seconds. Issuance and coordinator admission overlap; final
validation is nested. Do not sum these spans. Remaining budget is the original
120-second product lifetime, not the parent timeout. `N/A` means authority not
yet issued; `UNMEASURED` never means zero.

| Stage | Run 1 duration / status / remaining s | Run 2 duration / status / remaining s |
| --- | --- | --- |
| Setup before coordinator admission | 88.950 elapsed / completed / N/A | 88.005 elapsed / completed / N/A |
| Authority construction budget | Observed 120, issue age 0 | Observed 120, issue age 0 |
| Authority issuance | 80.821 / success / 83 | 416.534 / failure / -253 |
| Coordinator admission, overlapping issuance | 80.821 / success / 83 | 416.534 / failure / -253 |
| Pre-authority schema inventory preparation, nested | 0.005611 / success / N/A | 0.003276 / success / N/A |
| Issuance final validation, nested | 37.121 / success / 83 | 372.641 / failure / -252 |
| Attempt creation | 82.067 / failure / 0 | UNMEASURED |
| Attempt final validation, nested | 32.412 / failure / 0 | UNMEASURED |
| Metadata-owner admission | UNMEASURED | UNMEASURED |
| Metadata-owner final validation | UNMEASURED | UNMEASURED |
| Target mode transition | UNMEASURED | UNMEASURED |
| Target-entry INSERT | UNMEASURED | UNMEASURED |
| Target commit | UNMEASURED | UNMEASURED |
| Reservation reacquisition | UNMEASURED | UNMEASURED |
| Postcommit validation | UNMEASURED | UNMEASURED |
| Cleanup/result publication | UNMEASURED | UNMEASURED |

Run 1 issuance final validation began at child elapsed 132.645 seconds, with
120 seconds remaining. Attempt creation failed at 251.838 seconds, reported
remaining zero: about 119.193 seconds of monotonic elapsed across that observed
authority-bound prefix. Integer UTC sampling can report zero while this interval
is slightly below 120; do not interpret it as spare usable product budget.

Run 2 final validation began at 131.751 seconds and ended at 504.391, with negative
remaining budget. This proves late fail-closed detection in the preserved trace,
not a positive execution or a successful 372-second legitimate validation workload.
No metadata/target mutation was reached in either run. Neither result identifies
which specific inner operation consumed run 2's additional elapsed time.

## 5. Valid-sample distribution and headroom

Classification counts: **A = 0, B = 1, C = 1, D = 0**. Fewer than three A samples
were obtained; the successful-runtime sample is insufficient. Minimum, median,
maximum, spread and completion probability for successful lifecycles are all
**NOT ESTABLISHED**. No percentile or worst-case estimate is reported.

Run 1 establishes a legitimate partial prefix reaching its expiry check. It cannot
establish complete duration because metadata, target and cleanup remain unmeasured.
Run 2 is excluded from successful-runtime calculations and cannot be treated as a
slow successful workload. Across neither run may unmeasured stages be assigned
zero cost or durations from older traces. Major observed costs in run 1 are issuance
and attempt validation; run 2's dominant recorded span is issuance final validation,
but its internal cause is not isolated. No optimization or additional profiling
is performed.

## 6. Candidate lifetime comparison

| Candidate | Measured successful runs fitting / complete headroom | Exposure relative to 120 | Evidence interpretation |
| --- | --- | --- | --- |
| 120 s | No A samples; complete headroom unknown | Baseline | Run 1 expired before metadata; insufficient to call this operationally appropriate |
| 180 s | Unknown; no successful-run distribution | +60 s maximum age, 1.5x ceiling | No evidence that remaining metadata/target/cleanup fits; not a measured defensible minimum |
| 300 s | Unknown; no successful-run distribution | +180 s, 2.5x ceiling | More nominal budget is not proof of completion or acceptable consent exposure |
| 600 s | Unknown; no successful-run distribution | +480 s, 5x ceiling | Cannot use run 2's infrastructure anomaly as justification; earlier consent/credential expiry can clip available time |

These are ceilings, not guaranteed lifetimes: original primary/session/step/
confirmation deadlines still clip authority. No extrapolated complete-runtime
headroom is given from a truncated prefix. The current policy was not changed
to test any candidate, and no small-sample statistical guarantee is claimed.

## 7. Security interpretation

Completion probability depends on full workload and environment, neither measured
adequately here. Authority freshness limits age of original intent; longer lifetime
increases that exposure even with current mutable-state checks. Replay protection,
durable duplicate fencing, control/target reservation concurrency and crash/
uncertain-commit inspection are separate mechanisms; a larger lifetime replaces
none of them. Existing exact scope, original-owner registration, one-use constraints
and fresh auth/profile/approval/ACK/activation/stop/dependency/physical/history/
claim/control/readiness checks mitigate additional exposure but do not erase it.

A security expiry is checked at protected boundaries, not a guarantee that a blocked
process exits at the clock tick. An external diagnostic timeout is another boundary
and its failure must be investigated as such, not repaired by increasing runtime
authority. No successful result or target action was published from these failures.

## 8. Recommendation E and G-series disposition

**E - evidence remains insufficient.** Unknowns are complete successful lifecycle
duration/variability, remaining metadata/target/cleanup costs, acceptable owner-intent
exposure and why the existing external harness returned 150.753 seconds beyond
its configured bound. There is no measured basis to select A-D.

The replacement G1 architecture's necessity remains **unresolved**. No modest
increase was shown to make the existing path viable, so it cannot be declared
unnecessary on these data. Nor do these partial failures prove the existing path
cannot fit any defensible lifetime. No G-series continuation or replacement design
is proposed automatically.

## 9. Stop, next evidence boundary and validation

Stop sampling. Before another lifecycle measurement can be trusted, the specific
parent-bound failure must be resolved in a separately authorized diagnostic scope;
R2 does not modify the harness, schedule another run or weaken security checks.
Even a repaired bound would not by itself justify a lifetime change or provide
the missing complete workload samples.

Validation performed: two sequential lifecycle diagnostic children through the
existing external harness only; saved structured results inspected; document
whitespace/local links and `git diff --check`. No broad suite, T, separate
unbounded Z18, production/hosted validation or lifetime change. No Python/schema/
migration/permission changes, production database/key access, commit or push.
Only this documentation is added to the source tree; disposable fixture and
diagnostic-output writes are test-only. No G1 adoption, producer, enforcer,
business/family mutation or production activation was performed.

PRODUCTION AUTHORIZATION: BLOCKED

PRODUCTION EXECUTION: BLOCKED

PRODUCTION ACTIVATION: BLOCKED
