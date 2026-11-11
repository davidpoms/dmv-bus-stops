# 4e-20-Z3: bounded coordinator final-validation efficiency

Z3 changes only the redundant predecessor projection in attempt
`authority_manifest()`. Coordinator `_finish()`, `_evaluate()`, authentication,
readiness, target observation, activation and transaction ownership are unchanged.

## Boundary review

The issuance phase and attempt phase have distinct reservations. Within the
attempt phase, entry `_evaluate()` and `_persist_attempt()`'s `_evaluate()` precede
three control INSERTs (attempt, history and audit). `_finish()` must validate the
new graph and current authority after those mutations. Earlier admission/history
results must not be reused across that boundary. Z3 does not carry them forward.

Final `_finish()` checks original PID/thread/connection/epoch ownership and live
deadlines, invokes `_evaluate()`, checks the exact pending graph and protected
baseline in `_final_attempt()`, invokes fresh current identity/MFA and time checks,
then commits control while target remains reserved and query-only. `_evaluate()`
uses shared admission, issuer `_subject_for_owner()`, approval/proposal/ACK
readers, dependencies, claim disposition, protected readiness and independent
activation verification. Borrowed reads repeatedly re-enter identity/history and
control validation. No security decision is removed from this sequence.

The narrow redundancy is below those decisions. Attempt
`check_manifest_transition()` already verifies exact extension definitions, audit
digest/body, migration identity, installed and predecessor schema digests,
installation/generation scope, and the predecessor migration's audit. The
predecessor digest is recomputed via V `historical_manifest(exclude=attempts)`.
The caller `authority_manifest()` then formerly reconstructed that same S1 digest
again. Z3 returns the already-verified digest for the default empty-tuple exclusion
only, on an exact native SQLite connection with an active transaction. Other
exclusions, adapters, unreserved calls and invalid inputs keep their original
read/error behavior.

`check_manifest_transition()` now returns its verified subject to this caller.
It does not accept supplied observations. Its full validation runs on every call.
The returned digest is an immutable string from the same function invocation;
it is not stored on any owner, connection, registry, thread or process cache.
No write, yield, mode or transaction change intervenes. SQLite's transaction
snapshot and existing manager ownership enforce the unchanged projection.
Every next invocation reads again. No auth/activation/physical observation or
claim lifecycle result is cached. A schema digest never grants admission.

## Bounded focused validation

Only `tests/test_recognition_runtime_coordinator_final_validation_efficiency.py`
was run. It contains scalar-reader tests using disposable V schema fixtures,
and a separate real coordinator fixture so simulated identity observers cannot
leak between installations. The real comparison restores disposable baseline
files between independent before/after cases, preserving their physical identity.
Each case uses real consent, issuance, admission and attempt creation. Only the
before case restores the exact pre-Z3 projection reader. The instrumented original
`_finish()` executes normally, including manager-owned control COMMIT, with no
target DML and no new connections. No metadata owner or target entry is invoked.

Timing/counter wrappers call the original functions without changing results,
clocks or permissions. Aggregate output contains no SQL text, credentials, seeds,
row data or key material. The real comparison has a 240-second hard watchdog and
per-phase progress output. Authority lifetime remains 120 seconds per independent
case; both successful created authorities retain that exact lifetime.

### Final-validation measurements

| Layer | Calls before / after | Inclusive seconds before / after | Exclusive seconds before / after |
| --- | ---: | ---: | ---: |
| whole original `_finish()` | 1 / 1 | 28.604 / 20.561 | measured across all nested work |
| coordinator `_evaluate()` | 1 / 1 | 28.323 / 20.286 | .656 / .423 |
| issuer `_subject_for_owner()` | 1 / 1 | 19.870 / 14.570 | .456 / .485 |
| readiness inventory | 1 / 1 | 10.631 / 6.718 | .633 / .373 |
| physical/identity snapshot | 169 / 169 | 24.275 / 17.315 | .797 / .629 |
| history validation | 171 / 171 | 23.786 / 16.925 | 1.364 / 1.067 |
| control validation | 172 / 172 | 24.594 / 17.489 | 15.034 / 11.109 |
| claim validation | 172 / 172 | 5.161 / 3.431 | 1.851 / 1.332 |
| V historical manifest | 6,069 / 5,207 | 7.745 / 5.076 | 7.745 / 5.076 |

Nested times overlap. Host load varied; the time difference is not attributed
entirely to the optimization and no timing assertion is used. Read-count reductions
are structural. This fixture does not establish G+2 metadata-phase performance.

| Read category | Before | After |
| --- | ---: | ---: |
| SELECT | 57,142 | 54,556 |
| schema SELECT | 19,996 | 18,272 |
| audit SELECT (including ACK chain traversal) | 19,519 | 18,657 |
| approval SELECT | 1,077 | 1,077 |
| claim SELECT | 698 | 698 |
| activation SELECT | 1,911 | 1,911 |
| profile SELECT | 1,394 | 1,394 |
| PRAGMA | 20,288 | 20,288 |
| connection opens in final validator | 0 | 0 |
| control COMMIT | 1 | 1 |
| target INSERT/UPDATE/DELETE/DDL | 0 | 0 |

Read categories overlap. ACK readers validate complete audit chains rather than
SQL-filtered ACK rows; ACK activity is included in audit SELECT counts, not claimed
as a separately attributable ACK-row count. PRAGMAs remain: 17,990 query_only,
691 database_list, 1,041 foreign_key_check, 171 application_id, 171 user_version,
224 table_info. None were removed or cached.

## Security coverage and outcomes

Tests cover exact predecessor digest equivalence; two reconstruction calls rather
than three inside the permitted scalar scope; original unreserved/adapter and
extra-exclusion paths; fresh calls after auth/MFA/mode/transaction changes;
schema/audit/generation corruption rejection with exact triggers restored;
borrowed admission rejection after reservation epoch change; newly active
emergency stop and changed activation integrity; original 120-second codec limit;
and unchanged rejection of non-iterable exclusions.

The real comparison invokes the actual `_finish()` and `_evaluate()`, proves
readiness/history/control/claim/identity checks still run, rejects an altered
physical observation even after initial admission, and commits each exact inert
attempt through its original manager. It returns only historical CreatedAttempt
data, not a writer or metadata capability. No target entry, business mutation,
completion, seal, readiness issuance or production activation is implemented.

Initial file run: three tests / three subtests passed; real fixture construction
failed due cross-fixture observer lifetime. Separating fixture classes corrected
that test-only problem. An initial isolated comparison reached its 180-second
test watchdog without completing all scenarios; it is not a pass. The corrected
two-case comparison with per-phase diagnostics passed in **187.13 seconds**, under
its 240-second test bound, with no authority deadline change. Three additional
focused boundary tests passed in **11.49 seconds**; the new invalid-exclusion test
passed with three subtests in **6.77 seconds**. No whole-file repeated runs or
regression suites were used after the initial focused failure.

Z was not rerun. This approves only the stateless manifest efficiency change;
Z remains blocked pending separate metadata-owner validation. It does not prove
that all required Z validations fit within a live authority lifetime.

No hosted/production resource, deployment key, commit or push.

PRODUCTION AUTHORIZATION: BLOCKED

PRODUCTION EXECUTION: BLOCKED

PRODUCTION ACTIVATION: BLOCKED
