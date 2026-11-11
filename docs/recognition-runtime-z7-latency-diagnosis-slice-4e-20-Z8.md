# 4e-20-Z8: bounded Z7 latency-regression diagnosis

**Outcome B: the regression is localized, but correcting its dominant cost would
require a separately reviewed physical-observation strategy. No production-code
correction is made.** Z7's approved per-use physical checks, owner/connection/
transaction/reservation binding, invalidation rules and 120-second ceiling remain
unchanged. Z and T were not run.

## Method and bounds

Only `tests/test_recognition_runtime_attempt_schema_manifest_observation.py` is
run. Its existing genuine disposable coordinator comparison is retained. Reuse
disabled means fresh inventory readers; source observation construction and the
entry write proof still run, making the comparison conservative. Both cases use
the same restored disposable installation and a live UTC/monotonic clock.

Test-only wrappers measure hierarchical exclusive wall time and counts. They
call the real functions, preserve method binding and do not replace a validator
with a stub. Digest/canonicalization aliases are instrumented so nested codec
time is separated from digest time. The earlier per-check MagicMock counter is
replaced with a plain timing/counting wrapper; this is instrumentation only.

Full profiling is limited to construction once and at most eight reader calls
per reader/connection kind (objects/names; native/adapter). There are 32 final
reader samples per case. Full-lifecycle profiling is not enabled. The existing
300-second hard watchdog remains, as do every live authority deadline and all
eleven live-validator count comparisons. No secrets, function arguments, local
variables, observations or database contents are exported.

Aggregate and sampled evidence is in the existing diagnostic artifact
`.tmp/recognition-z7-final-timing.json`, under each result's `z8_profile`. Detailed
rows identify source functions, counts and timings only.

## Whole-finalization measurements

| Measure | Reuse disabled | Reuse enabled |
| --- | ---: | ---: |
| Wall seconds | 19.302 | 35.339 |
| Thread CPU seconds | 19.109 | 35.172 |
| Schema SELECTs | 18,274 | 2,124 |
| Observation validations | 1 | 16,151 |
| Physical boundary observations | 1 | 16,151 |
| Digest calls | 68,688 | 84,838 |
| Canonicalization calls | 102,594 | 151,044 |
| Object-copy calls | 5,352 | 5,352 |

Construction is separate from finalization: one call per case, 0.008814s disabled
and 0.003288s enabled. Its exclusive self times are 0.006578s and 0.001224s. It
cannot explain a multi-second regression.

The following are **exclusive times**, not a sum of overlapping inclusive layers.
Selected layers do not cover every function in finalization.

| Component | Disabled seconds | Enabled seconds | Calls disabled / enabled |
| --- | ---: | ---: | ---: |
| Physical observation, including strict filesystem helpers | 0.000916 | 12.052008 | 1 / 16,151 |
| Canonical codec | 3.264954 | 5.010047 | 102,594 / 151,044 |
| Digest, excluding codec children | 0.855139 | 1.059428 | 68,688 / 84,838 |
| Definition-code identity | 0.000036 | 0.456318 | 1 / 16,151 |
| Observation validation self | 0.000051 | 0.586328 | 1 / 16,151 |
| Registry/provenance self | 0.000033 | 0.117945 | 3 / 16,153 |
| Coordinator ownership self | 0.193295 | 0.261279 | 17,989 / 21,584 |
| Owner/deadline checks | 1.070958 | 1.698784 | 17,996 / 21,591 |
| Reservation/query-only mode self | 0.509865 | 0.801621 | 17,989 / 21,584 |
| Connection/transaction checks | 0.054906 | 0.075938 | 17,989 / 21,584 |
| Credential scope, excluding digest/codec | 0.000011 | 0.091930 | 1 / 16,151 |
| Schema-object reader self | 0.939121 | 0.098767 | 8,328 / 16,151 |
| Schema-name reader self | 0.591186 | 0.172448 | 7,823 / 7,823 |
| Object copy, excluding codec children | 0.660522 | 0.687044 | 5,352 / 5,352 |

Observation validation's inclusive cost rises from 0.001347s to 17.295227s.
Reader reuse replaces relatively cheap inventory reads with 16,150 additional
validations. Each validation observes both control and target physical identity:
32,302 strict identity observations in the enabled finalization. This is the
dominant measured mechanism, not construction, bulk copying or digesting alone.

## Native work, Python work and uncertainty

The 32 enabled samples contain 31 reused observations (the initial independent
manifest read is fresh). They show 62 real `target_identity()` calls and 124 Windows
`nt._getfinalpathname` calls. Exclusive sample times include:

| Sampled work | Calls | Exclusive seconds |
| --- | ---: | ---: |
| Windows final-path resolution | 124 | 0.015247 |
| Hostname syscall | 62 | 0.002517 |
| File-type syscall | 62 | 0.001368 |
| File stat syscall | 62 | 0.001035 |
| JSON encoder iteration | 93 | 0.002693 |

The native filesystem work dominates the sampled observation path. This is a
local Windows/disposable-fixture measurement, not a PythonAnywhere claim. The
fixture also substitutes the synthetic runtime tuple and records calls through
mock objects. Those contributions are visible in sampled `mock.py`/dataclass
functions; they are not assumed to be production overhead.

Sampled native SQLite execute self time is 0.012402s disabled (1,520 calls) and
0.000531s enabled (32 calls). Fetch-one self time is 0.001471s (1,488 calls) and
0.000042s (31 calls). The known `PRAGMA query_only` execute caller accounts for
0.011717s/1,488 calls disabled and 0.000513s/31 calls enabled. These are sampled
times, **not estimates of whole-finalization SQL time**. Native cursor iteration
is partly charged to its Python caller, so reader self time is not labeled pure
Python time. Sampled constructor/copy functions and the full object-copy layer
are retained separately in the artifact; unprofiled inline allocations are not
assigned invented exact costs.

The stock SQLite API does not separately expose internal lock-wait duration.
Control/target reservations are already held during finalization. Wall minus
thread CPU is approximately 0.193s disabled and 0.167s enabled: an upper bound on
all non-CPU delay in each measured window, not a measurement of SQLite lock wait.
The measured 16.037s wall regression is accompanied by a 16.063s CPU increase.
That strongly supports repeated observation work, rather than a large new
lock/wait delay. No busy/locked behavior is changed or retried.

The regression direction repeats earlier bounded Z7 measurements (18.147s to
30.732s; another run was 19.996s to 36.138s). Detailed instrumentation perturbs
absolute costs, and the small sample cohorts must not be extrapolated as an
exact whole-run syscall/SQL partition. The complete per-use physical timer and
call counts independently establish the dominant overhead. No additional long
lifecycle is needed merely to repeat that conclusion.

## Security result and decision

The focused run passed **2 tests and 29 subtests in 170.04s**. Schema digest,
scope, subject and the exact inert attempt graph remain equivalent. All eleven
watched live-validator call counts remain equal. Existing malformed-scope,
physical-identity, schema/manifest, ownership and authorizer invalidation probes
remain in the same focused file. There is no target DML, writer or execution.

Removing or carrying forward the independently mutable physical observations
would change the approved Z7 checks and is not an admissible performance fix in
this slice. Replacing them with browser claims, hostname exemptions, weaker path
resolution, a cross-boundary cache, fewer live checks or a longer lifetime is
also excluded. Codec and code-identity costs are smaller; they do not justify a
new unrelated optimization while the dominant cost remains.

The precise remaining review question is whether an explicitly approved way to
perform the same per-use strict physical observations can reduce their cost on
the supported filesystem, without changing frequency, identity semantics or
ownership. No such correction is established here. Production code is unchanged;
no follow-up optimization, Z retry, T implementation or deadline change is
automatically authorized. No hosted resources, production databases, deployed
keys, commit or push were accessed/performed.

PRODUCTION AUTHORIZATION: BLOCKED

PRODUCTION EXECUTION: BLOCKED

PRODUCTION ACTIVATION: BLOCKED
