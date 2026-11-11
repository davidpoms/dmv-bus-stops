# 4e-20-R4: bounded diagnostic timeout enforcement correction

## 1. R3 finding and scope

[R3](recognition-runtime-security-lifetime-harness-boundary-diagnosis-4e-20-R3.md)
proved that the old harness could kill its direct child yet block indefinitely
in unbounded `communicate()` waiting for descendant-held output pipes. This slice
corrects that demonstrated test-harness path only; it does not attribute R2's
particular historical delay or run any recognition lifecycle.

## 2. Exact defect and correction

`tests/runtime_deadline_harness.py` previously applied a timeout to the first
communicate, then used timeout-free communicate/wait and pipe cleanup. Its timeout
was therefore not an overall bound.

The correction removes pipe-based capture and **all communicate calls**. The
child's stdout/stderr go to one unique temporary regular file directly in the
verified writable repository root. An independently opened read handle takes
a fixed-size snapshot without waiting for EOF or moving the writer's file offset.
On Windows both handles share temporary-file deletion; descendants may retain
their inherited writer handle without keeping the parent in a pipe-reader join.
Final inherited-handle closure completes temporary-file removal. No global Temp,
permission, ACL or SQLite policy changes occur.

Process wait, termination confirmation and reap use explicit remaining monotonic
budgets. Output collection reads at most the last 256 KiB and retains at most 32
valid structured marker reports, checking its collection deadline between records.
Malformed/partial reports are not repaired. Output errors, truncation or missed
collection deadline are reported; no unbounded drain/retry is used to recover data.
This is a snapshot, not a claim of complete descendant output. stderr is merged
for collection, but only valid structured report lines are returned.

## 3. Parent/child timeout contract

All relative deadlines start at `run_child()` entry, before file creation and
process launch. Inputs must be finite positive non-boolean numbers. The lifecycle
child timeout remains **360 seconds**, unchanged. Default cleanup budget is a
separate **5 seconds**, not extra runtime authority or a longer child wait.

| Phase | Default absolute offset from harness start |
| --- | ---: |
| Child deadline | 360 s |
| Termination-confirmation deadline | 362 s (40% of cleanup budget) |
| Reap deadline | 363 s (60%) |
| Output-collection deadline | 364 s (80%) |
| Final parent-return deadline | 365 s (100%) |

The direct child is killed if still running after its wait. Reap is bounded even
if termination fails; the report exposes error class, exit/reap and cleanup status.
Past deadlines give zero remaining wait, never a fresh full timeout. No unbounded
process wait, pipe-reader thread, descendant join or EOF drain remains. Native
process creation/kill, filesystem calls and OS scheduling are not preemptible by
a Python timer: arbitrary host suspension or OS failure cannot have a guaranteed
userspace wall-clock bound. An overrun is explicitly reported by
`parent_bound_exceeded`, never accepted as a valid bounded measurement.

Reports include launch/wait/termination/reap/output/cleanup observations and all
relative deadlines. `direct_child_exit_observed` is the manager's confirmed exit
observation, not an invented exact OS-death instant. Timeout remains distinct from
the child's recognition error code. Collection/reaping failure is diagnostic loss,
not authority expiry or lifecycle success.

## 4. Lifecycle diagnostic integration (not executed)

The existing parent branch in
`tests/test_recognition_runtime_lifecycle_deadline_trace.py` now rejects parent-bound
overrun, incomplete direct-child cleanup/reaping or unavailable/deadline-limited
output collection before interpreting child exit/reports. It still rejects external
timeout independently of authority expiry. No child lifecycle code, authority time,
fixture, Z15 observation, coordinator or metadata validation changed.

No lifecycle invocation occurred in R4. This integration was inspected and parsed
statically only; the controlled tests import no recognition fixture or runtime.

## 5. Focused tests and controlled probe results

Command run once:

```text
.venv/Scripts/python.exe -B -m pytest tests/test_recognition_runtime_deadline_harness.py -q -s -p no:cacheprovider
```

Result: **7 passed, 5 subtests passed in 2.50 seconds**. Preserved existing consent
error/observer tests. Added real descendant-handle cases, bounded-output preservation
and finite-budget checks. These are not mocks of recognition authority.

The retained-output tests launch a direct child that starts a descendant requesting
a 20-second sleep with inherited stdout/stderr. The direct child either exits or
also requests a 20-second sleep. The harness uses child timeout 0.75 seconds and
cleanup budget 1 second, giving final bound 1.75 seconds. After harness return,
tests verify the descendant is still alive using its OS process handle on Windows,
then explicitly terminate and bounded-wait that test-owned descendant. Thus the
test proves the parent does not merely wait for the descendant to cooperate.

| Observation, seconds from harness entry | Direct child exits normally | Direct child times out |
| --- | ---: | ---: |
| Child timeout / cleanup budget | 0.75 / 1.00 | 0.75 / 1.00 |
| Final parent deadline | 1.75 | 1.75 |
| Child wait completes | 0.232629 | 0.754780 |
| Termination request | Not needed | 0.755309 |
| Termination wait completes | Not needed | 0.757939 |
| Reap completes | 0.232649 | 0.757949 |
| Direct-child exit observed | 0.232652, exit 0 | 0.757950, exit 1 |
| Output snapshot completes | 0.232834 | 0.758135 |
| Parent elapsed | **0.233115** | **0.758290** |
| Descendant alive at return | Yes | Yes |
| Reaped / cleanup complete / parent-bound exceeded | Yes / yes / no | Yes / yes / no |

The simple blocking-child test also preserves a structured started report after
timeout and confirms nonzero child exit/reaping. The normal error-report test
preserves exact `TrustError: authority_consent_expired` with child exit 7. Oversized
output is explicitly truncated while an available tail report survives; invalid
timeout/cleanup values are rejected. No test terminates the test runner with
`os._exit()` or invokes recognition.

## 6. Descendant behavior and remaining limits

The harness terminates/reaps its direct child, not arbitrary descendants. It neither
claims process-tree containment nor waits for descendants' file descriptors to
close. The tests clean up their own known descendant PIDs. On Windows the temporary
file can remain delete-pending until the last inherited handle closes; this is
not a parent-side collection wait. Regular-file output does not impose a disk
quota on a malicious flooder; collection size is bounded, not total child writes.
This test-only correction does not claim sandboxing against arbitrary hostile
processes or resource exhaustion, nor modify production security.

## 7. R2 historical-result treatment

The exact cause of R2's **510.753-second** return remains unresolved. Its phase
timestamps are insufficient to prove that the demonstrated unbounded pipe path
caused that particular delay. R4 fixes the proven defect, not the historical record.
The 251.840-second authority-expiry run remains the only valid R2 lifecycle outcome;
zero successful complete lifetime-selection samples exist. No new lifetime is
supported, and timeout is not reclassified as authority expiry.

## 8. Validation and next boundary

Focused harness tests passed as above. AST parsing of the three changed test/harness
files, whitespace checks, this document's local-link checks and `git diff --check`
are required static validation. All affected files were inspected directly; these
test/harness files are preexisting untracked working-tree files, so tracked diff
alone does not display their content changes. No unrelated working-tree changes
are reverted or cleaned up.

**Next boundary: 4e-20-R5 - bounded lifecycle measurement rerun.** It is not run in
R4. Future sampling must reject `parent_bound_exceeded`, incomplete cleanup and
collection failure, preserve child error/report classifications and stop on
infrastructure failure rather than extending lifetime or retrying indefinitely.

No recognition lifecycle, Z18, T, broad suites, production/hosted resources,
deployment keys, schema/migration, permissions, production behavior, lifetime or
security-policy change, commit or push.

PRODUCTION AUTHORIZATION: BLOCKED

PRODUCTION EXECUTION: BLOCKED

PRODUCTION ACTIVATION: BLOCKED
