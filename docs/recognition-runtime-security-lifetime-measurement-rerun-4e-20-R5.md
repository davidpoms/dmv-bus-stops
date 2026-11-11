# 4e-20-R5: bounded recognition lifecycle measurement rerun

## 1. R4 baseline and outcome

[R4](recognition-runtime-security-lifetime-harness-boundary-correction-4e-20-R4.md)
removed unbounded pipe draining and passed focused descendant-handle tests. R5
uses that corrected harness without changing production behavior or lifetime.

**BLOCK: no complete successful lifecycle sample obtained.** Two sequential runs
both failed closed at the original authority deadline during attempt final
validation. Both children exited normally from the diagnostic and were reaped
within the corrected parent bound. No harness/environment failure was observed.
The sample stopped after repeated equivalent expiration failures rather than
spending the remaining child allowance on the same truncated path.

## 2. Harness configuration and method

Used `tests.runtime_deadline_harness.run_child()` unchanged, with **360-second
child timeout**, **5-second cleanup budget** and **365-second final parent bound**.
Relative phase deadlines were termination confirmation 362, reap 363 and output
collection 364 seconds. Output used bounded temporary-file snapshot collection,
not pipes/EOF draining. The runner retained all parent timing/cleanup/status data.

Each child ran only the existing dedicated lifecycle method, under that harness:

```text
python -B -m pytest tests/test_recognition_runtime_lifecycle_deadline_trace.py::LifecycleDeadlineTraceTests::test_one_g2_lifecycle -q -s -p no:cacheprovider
```

The existing child-selector flag prevented nested parent invocation. A temporary
in-memory sampling script targeted up to five A traces and capped children at
eight, with early stop on a harness/environment failure or two consecutive B
results. It preserved each new result before starting another child. **Two children
ran, not eight.** No lifecycle was run separately outside the external harness.

Raw complete new reports are in `.tmp/recognition-r5-lifetime-samples.json`, with
stop reason `repeated_fail_closed_expiration`. They are not combined with R2 or
historical Z12/Z18 samples. Existing writable disposable-workspace/G+2 fixture,
original fresh authentication/approval/consent and actual Z15 preparation were
reused unchanged. Only disposable fixture databases/keys/activation were involved.
No production/hosted resource or deployment key was accessed.

## 3. Run-by-run results and classification

| Run | Child diagnostic elapsed s | Parent elapsed s | Parent status / exit | Reaped / cleanup / exceeded bound | Class |
| --- | ---: | ---: | --- | --- | --- |
| 1 | 250.680923 | 254.633737 | `child_exited` / 0 | Yes / complete / no | B: fail-closed authority expiration |
| 2 | 248.271822 | 251.027517 | `child_exited` / 0 | Yes / complete / no | B: fail-closed authority expiration |

Both exact failures are `AdminError: administrative_session_expired_or_revoked`,
interrupted at `coordinator final validation` in the attempt phase. The child
diagnostic permits exit zero after a recorded fail-closed result, so exit zero
is not evidence of a successful recognition lifecycle. Output status was `snapshot`
and no parent timeout/overrun occurred.

Classification totals: **A = 0, B = 2, C = 0, D = 0**. These are interpretable valid
failure traces, not valid successful completion samples. R2's 510.753-second cause
remains unresolved; these results neither reproduce nor retrospectively explain it.

## 4. Stage timings

All stage start/end offsets and durations are child-monotonic seconds. Issuance
and coordinator admission overlap, and final validation/preparation are nested.
**Do not sum nested spans.** Remaining budgets are product-observed integer UTC
seconds; N/A means authority not yet constructed, and UNMEASURED does not mean zero.

| Stage | Run 1 start -> end / duration / remaining | Run 2 start -> end / duration / remaining |
| --- | --- | --- |
| Setup elapsed before admission | 0 -> 89.155690 / 89.155690 / N/A | 0 -> 87.243161 / 87.243161 / N/A |
| Authority issuance | 89.155690 -> 167.329425 / 78.173735 / 84 | 87.243161 -> 163.813532 / 76.570371 / 85 |
| Coordinator admission, overlapping | 89.155700 -> 167.329355 / 78.173655 / 84 | 87.243168 -> 163.813475 / 76.570307 / 85 |
| Z15 schema-inventory preparation, nested pre-authority | 131.646036 -> 131.649395 / 0.003358 / N/A | 129.233670 -> 129.237618 / 0.003947 / N/A |
| Issuance final validation, nested | 131.688876 -> 167.325390 / 35.636514 / 119 -> 84 | 129.264187 -> 163.809899 / 34.545713 / 120 -> 85 |
| Attempt creation, failed | 167.329479 -> 250.680537 / 83.351058 / 84 -> 0 | 163.813577 -> 248.271127 / 84.457549 / 85 -> 0 |
| Attempt final validation, nested, failed | 216.077236 -> 250.677048 / 34.599812 / 35 -> 0 | 212.402449 -> 248.267916 / 35.865468 / 36 -> 0 |
| Metadata-owner admission | UNMEASURED | UNMEASURED |
| Metadata-owner final validation | UNMEASURED | UNMEASURED |
| Target mode transition | UNMEASURED | UNMEASURED |
| Target-entry INSERT | UNMEASURED | UNMEASURED |
| Target commit | UNMEASURED | UNMEASURED |
| Reservation reacquisition | UNMEASURED | UNMEASURED |
| Postcommit validation | UNMEASURED | UNMEASURED |
| Successful cleanup/result publication | UNMEASURED | UNMEASURED |

Both actual preparation hooks ran; the reports capture original authority issue
age zero and unchanged 120-second lifetime. Diagnostic failure handling produced
reports; that is not successful protected lifecycle cleanup/publication. No metadata
or target-entry stage was reached; no runtime target-entry or business mutation
occurred in the measured authority path. Fixture setup performs its established
disposable enrollment/migration/proposal writes and is not a zero-write fixture.

## 5. Authority-budget measurements, separate from elapsed lifecycle

The fixture uses an advancing monotonic-anchored synthetic UTC clock, not current
calendar time. These source timestamps prove the measured lifetime, not deployment
time or credential validity outside the fixture:

| Run | Source issue -> expiry | Lifetime / issue age | Remaining after issuance | At attempt final-validation start / failure |
| --- | --- | --- | ---: | --- |
| 1 | `2099-01-01T00:18:29Z` -> `2099-01-01T00:20:29Z` | 120 s / 0 | 84 s | 35 s / 0 |
| 2 | `2099-01-01T00:18:28Z` -> `2099-01-01T00:20:28Z` | 120 s / 0 | 85 s | 36 s / 0 |

From issuance final-validation entry to attempt failure, observed monotonic spans
were 118.991661 and 119.006940 seconds. These begin after actual source construction,
not precisely at its issue timestamp. Integer UTC sampling explains why these
spans are not exactly 120. The authoritative product result in both is expiration,
not approximately one second of usable remaining authority.

The full child elapsed 250.681/248.272 seconds includes preparation before issue.
It must not be treated as required authority age or evidence that 300 seconds
would finish. Likewise, total parent elapsed is not child lifecycle duration.

## 6. Harness timing and deadline integrity

| Parent observation, seconds from harness entry | Run 1 | Run 2 |
| --- | ---: | ---: |
| Launch completes | 0.010765 | 0.008195 |
| Child wait starts | 0.010769 | 0.008197 |
| Child wait ends | 254.632072 | 251.026412 |
| Reap starts -> ends | 254.632083 -> 254.632109 | 251.026421 -> 251.026439 |
| Exit observed | 254.632113 | 251.026443 |
| Output collection starts -> ends | 254.632113 -> 254.632868 | 251.026443 -> 251.026792 |
| Cleanup completes | 254.633735 | 251.027516 |
| Parent return elapsed | 254.633737 | 251.027517 |
| Child timeout / final parent deadline | 360 / 365 | 360 / 365 |

No kill was required. Reap took approximately 0.000025 and 0.000018 seconds;
snapshot collection approximately 0.000755 and 0.000348 seconds. From wait completion
to cleanup completion took approximately 0.001662 and 0.001104 seconds. These
are parent observations, not times inside recognition's cleanup. The differences
between total parent and child diagnostic elapsed include startup/pytest setup/
teardown and cannot be assigned solely to reap or output collection.

## 7. Complete-runtime distribution and lifetime comparison

No valid A sample exists. Successful minimum/median/maximum/spread, completion
probability and complete authority-bound workload are **not established**. The two
failed prefixes show repeatable failure at attempt final validation in this local
fixture, not that every possible 120-second run must fail. Early stop does not
claim impossibility or a statistically representative distribution.

| Candidate | Complete successful-run headroom / fit | Additional maximum age versus 120 | Conclusion |
| --- | --- | --- | --- |
| 120 s | No complete sample; both observed runs expired before metadata | None | Operational completion not demonstrated |
| 180 s | Unknown; remaining metadata/target/cleanup unmeasured | +60 s, 1.5x ceiling | No measured basis to call sufficient |
| 300 s | Unknown; child elapsed includes pre-authority work | +180 s, 2.5x ceiling | Cannot infer sufficiency from ~250-second child durations |
| 600 s | Unknown; earlier original credential/consent deadlines may clip it | +480 s, 5x ceiling | No evidence justifies this exposure or establishes necessity |

No replacement lifetime is selected. Unmeasured stages receive no assumed duration;
candidate headroom is not fabricated by adding failure spans or historical samples.

## 8. Security interpretation and G-series disposition

Bounded intent age is a freshness control, not a substitute for exact action/
target/activation/profile binding, original-owner checks, current authentication,
approval/ACK, dependencies, stop, physical identity/schema, history/claim/control/
readiness or reservation/deadline validation. Replay protection, durable duplicate
fencing, concurrency and uncertain-commit handling remain independent of the
numeric ceiling. Existing independent controls mitigate a larger exposure window
but do not prove a specific longer lifetime acceptable or workload sufficient.

The observed path is **not demonstrated viable at 120 seconds**. A modest increase
has **not been demonstrated sufficient**, and a replacement authorization architecture
has **not been demonstrated necessary**. The missing complete workload/remaining
stage evidence prevents choosing among those conclusions. No automatic G-series
continuation, redesign, optimization or policy adoption follows from this sample.

## 9. Recommendation, stop and exact next boundary

Evidence remains insufficient for a replacement lifetime. Stop at two repeated
valid B failures; no further child runs are scheduled. Unlike R2, the corrected
harness returned/reaped/collected within its bounds in both cases, so another
harness correction is not justified by these observations.

The next boundary, if separately authorized, is a **measurement-policy decision
on obtaining the still-unmeasured post-expiry stages without silently extending
authority or bypassing validation**. R5 does not authorize such a method, a larger
lifetime, a new ceremony or another blind repetition. Any later proposal must
distinguish an actual successfully authorized lifecycle from a simulation or
counterfactual measurement and preserve all production/security boundaries.

## 10. Validation and explicit production blocks

Only the two bounded diagnostic children were run. New reports were inspected
and classified with the corrected parent-bound, cleanup, report and authority
integrity checks. Document whitespace/local-link checks and `git diff --check`
complete static validation. Only this source-tree document is added; the local
diagnostic collection and fixture writes are test-only. No harness/test/production
code, lifetime, security policy, schema/migration or permissions were changed.

No separate Z18 run, T, broad suite, production/hosted resources, deployment keys,
G1 adoption/producer/enforcer, business execution, activation, commit or push.

PRODUCTION AUTHORIZATION: BLOCKED

PRODUCTION EXECUTION: BLOCKED

PRODUCTION ACTIVATION: BLOCKED
