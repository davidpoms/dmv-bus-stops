# 4e-20-R3: diagnostic harness boundary diagnosis

## 1. R2 baseline and result

[R2](recognition-runtime-security-lifetime-measurement-4e-20-R2.md) obtained no
successful complete lifecycle. Run 1 reported fail-closed authority expiration
at child elapsed 251.840 seconds. Run 2 reported parent `subprocess_timeout` after
510.753 seconds despite a configured 360-second timeout; its child report elapsed
504.663 seconds, with exit code zero and reaping confirmed.

**Historical failure classification F - cause remains unresolved.** A concrete
parent-side unbounded output-drain defect is proved by controlled probes, but R2
lacks the phase timestamps needed to attribute its particular 150.753-second
overrun to that defect rather than late timeout detection/other process behavior.
Do not equate a reproduced possible path with proof of the historical cause.
No harness fix or lifecycle rerun is performed.

## 2. Harness architecture and exact timeout path

Inspected `tests/runtime_deadline_harness.py`, its existing focused tests, and the
actual installed CPython 3.14.6 `subprocess.Popen` source through read-only
`inspect.getsource()`. No internet/runtime service or database was accessed.

`TIMEOUT_SECONDS = 360` is passed to `run_child()`'s first
`process.communicate(timeout=timeout)`. The harness samples `time.monotonic()`
before `Popen`, but does not create an overall absolute deadline. CPython creates
its communicate deadline using `subprocess._time()` (the monotonic clock), after
process creation. Thus launch time is outside that timeout while included in
reported parent elapsed time.

On Windows, communicate starts stdout/stderr reader threads and joins them with
remaining time, then waits for process termination with remaining time. Reader
thread liveness or a timed-out process wait raises `TimeoutExpired`. This is not
an independent OS-enforced termination at the nominal deadline; the parent must
resume and handle the exception.

The exception handler sets `timed_out=True`, calls `process.kill()`, and then calls
**`process.communicate()` with no timeout**. In `finally`, it polls, kills if still
running, calls **`process.wait()` with no timeout**, and closes both pipe objects.
Only after that does it parse marker-prefixed stdout lines and return a monotonic
elapsed value. stderr is read but not returned. Structured output is available
when captured stdout contains complete valid JSON report lines.

The explicit overrun path is:

```text
bounded initial communicate
  -> TimeoutExpired
  -> kill direct child
  -> unbounded communicate / reader joins until pipe EOF
  -> unbounded final wait and stream cleanup
  -> stdout splitting / JSON parsing
  -> parent return
```

Killing the direct child does not necessarily close pipe handles inherited by
its descendants. The second communicate can therefore remain blocked after the
direct child is dead. Process launch, kill, final wait/close and output parsing
also have no end-to-end budget. Closing streams involved in concurrent I/O must
not be assumed nonblocking. A late-scheduled parent is another distinct possibility;
none of these elapsed phases was measured in R2.

## 3. Historical child versus parent timing

| R2 run 2 quantity | Available observation |
| --- | --- |
| Configured first communicate timeout | 360 seconds |
| Child diagnostic elapsed | 504.663 seconds; includes fixture and lifecycle diagnostic work, not just authority age |
| Parent total elapsed | 510.753 seconds; includes launch/wait/collection/cleanup/report parsing |
| Initial parent wait duration / timeout detection time | UNMEASURED |
| Kill invocation/completion and child exit timing | UNMEASURED |
| Reap duration | UNMEASURED; final `reaped=True` only |
| Output collection / pipe-close duration | UNMEASURED |
| Parent final parsing/reporting duration | UNMEASURED |

The numerical difference of 6.089 seconds is not a measured reap or output duration:
child and parent have different start/end boundaries. Exit zero with timeout
status is consistent with a child exiting before a delayed kill attempt, but does
not prove that happened. There is no evidence of inherited descendant handles in
that historical run. Its child-reported expiry does not explain the parent bound.

## 4. Controlled probe method

Ran minimal inline test-only diagnostics, not pytest or recognition. They call the
real unmodified `run_child()` through an instrumented `Popen` subclass that records
entry/exit of launch, communicate, kill and wait while invoking the original
methods. A separate supervising subprocess applies a 12-second bound to each
short diagnostic batch. No `os._exit()` is used.

Case 1: child emits one benign structured started report and requests a 10-second
sleep; harness timeout is 0.25 seconds. Case 2 adds a synthetic descendant that
inherits stdout/stderr and sleeps only 1.5 seconds. This deliberately exposes
the output-pipe ownership distinction without an unbounded descendant. A follow-up
of case 2 observes direct-child OS termination using Windows
`WaitForSingleObject` with a finite 5-second wait in a test-only observer thread;
it does not reap or mutate `Popen.returncode` itself.

Outputs: `.tmp/recognition-r3-harness-probe.json` and
`.tmp/recognition-r3-termination-observation.json`. These are diagnostic records,
not security state. All short-lived synthetic children completed or were killed
and reaped; pipe-holder descendants exited normally. No production code or shared
harness/test infrastructure changed.

## 5. Probe measurements

Times are seconds from the observed harness-call boundary. The native termination
time is when the OS wait observation completed, not an assertion of an exact CPU
instruction timestamp. Nested communicate/wait times are not summed.

| Event | Simple sleeping child | Pipe-holder case | Pipe-holder with OS exit observation |
| --- | ---: | ---: | ---: |
| Configured timeout | 0.250 | 0.250 | 0.250 |
| Launch complete | 0.008866 | 0.006236 | 0.016093 |
| Initial communicate starts | 0.008876 | 0.006245 | 0.018235 |
| Timeout detected | 0.263860 | 0.257485 | 0.271186 |
| Kill starts / returns | 0.263898 / 0.265179 | 0.257520 / 0.257855 | 0.271204 / 0.271560 |
| Unbounded second communicate starts | 0.265185 | 0.257862 | 0.271569 |
| Direct child OS termination observed | Not independently timestamped | Not independently timestamped | 0.273657, exit 1 |
| First process wait starts | 0.268051 | 1.847995 | 1.841054 |
| First process wait ends | 0.268079 | 1.848049 | 1.841092 |
| Second communicate ends | 0.268081 | 1.848054 | 1.841097 |
| Final wait/reap completes | 0.268096 | 1.848078 | 1.841120 |
| Parent return observed | 0.268186 | 1.848227 | 1.841259 |
| Harness-reported elapsed | 0.268039 | 1.848070 | 1.841122 |

Every probe returned `subprocess_timeout`, nonzero child exit and `reaped=True`;
the structured started report survived collection. In the independently observed
case the child was dead by 0.273657, but the parent did not start its process wait
until 1.841054. Roughly 1.568 seconds elapsed after observed child termination,
inside output collection before reaping. The first process wait itself took about
0.000038 seconds. Parsing/last cleanup after the second communicate took about
0.00016 seconds, including observer/logging overhead.

This demonstrates a parent output-collection blockage, not a failed child kill or
a 1.8-second child lifecycle. Instrumentation perturbs small timings; conclusions
depend on the operation ordering and large drain interval, not microsecond accuracy.

## 6. Failure classification A-F

| Candidate cause | Finding |
| --- | --- |
| A - Timeout measurement bug | No evidence of wrong configured value or arithmetic. The timeout scopes one communicate, not the complete call |
| B - Parent wait/reap/pipe/output blockage | **Confirmed structural defect and controlled reproduction:** post-kill unbounded output drain outlives a terminated child. Historical attribution remains unproved |
| C - Child termination failure | Not reproduced; direct child termination observed promptly in the controlled case. R2 has no kill timing to establish this |
| D - Test-runner/process isolation | Possible historically, not established; probes do not invoke pytest or recognition |
| E - Another identified cause | None established for the historical result |
| F - Cause unresolved | **Selected for the exact 510.753-second R2 event**, because phase/OS scheduling/handle evidence is missing |

## 7. Correction required, not applied

The exact demonstrated defect requires removing unbounded post-timeout drain/
reap/cleanup from the enforcing parent's return path. A timeout on only the first
communicate is insufficient. A correction must use one explicit monotonic diagnostic
budget and bounded termination/reap/output handling, preserve already available
structured reports, and report incomplete collection distinctly. It must not wait
for arbitrary descendants to close pipes after the direct child is terminated.

Simply adding `wait(timeout=...)` while retaining unbounded `communicate()` is not
a correction. Nor is catching drain timeout then synchronously closing a still-read
pipe without proving that close cannot block. Concrete choices such as bounded
file-backed output collection or process-tree containment need test-only design
review; neither is implemented or claimed already supported here. No increase to
360 or to authority lifetime is a remedy.

For the **historical** delay, an exact minimal correction cannot honestly be
selected until its location is known. Necessary diagnostic evidence is monotonic
launch start/end, initial wait start/timeout, kill start/end with observed exit,
independent OS exit/reap and drain/close/parse boundaries. The probes demonstrate
this decomposition without rerunning recognition. Host scheduling can prevent
prompt userspace response; no Python-level change guarantees a hard wall-clock
deadline under arbitrary process suspension.

## 8. Impact on lifetime measurement

- No valid successful lifetime-selection sample exists.
- The 251.840-second fail-closed expiry remains R2's only valid lifecycle outcome;
  its elapsed time includes setup and is not the authority lifetime.
- The 510.753-second run cannot be used as a valid 360-second bounded measurement
  until the harness issue is resolved. Its surviving child report is evidence,
  not a successful or properly bounded runtime sample.
- No 120/180/300/600-second lifetime recommendation is newly supported. The product
  lifetime, policy, validation and all permissions remain unchanged.

## 9. Stop and exact next boundary

**R3 diagnosis is incomplete for the historical overrun.** Stop before applying
a fix or rerunning Z12/R2/Z18. The next boundary is a separately authorized test-only
decision on bounded post-timeout collection/cleanup, with the missing parent-phase
instrumentation needed to determine whether that correction addresses the observed
R2 delay. It is not another lifecycle sample or lifetime/policy change.

Validation performed only the short synthetic probes, read-only code inspection,
document whitespace/local links and `git diff --check`. No pytest suite, recognition
lifecycle, T, broad test, production/hosted resource, deployment key, migration,
permission change, code fix, commit or push. Only this document is added to the
source tree; inline test instrumentation and local diagnostic reports are test-only.

PRODUCTION AUTHORIZATION: BLOCKED

PRODUCTION EXECUTION: BLOCKED

PRODUCTION ACTIVATION: BLOCKED
