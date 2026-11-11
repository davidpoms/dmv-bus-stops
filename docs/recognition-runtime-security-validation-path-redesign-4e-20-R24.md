# 4e-20-R24 - targeted validation-path redesign and lifecycle validation

## 1. Authorization and decision

[R23](recognition-runtime-security-operational-feasibility-decision-4e-20-R23.md)
authorized one engineering tranche under the unchanged
[R21-B contract](recognition-runtime-security-consolidated-finalization-contract-4e-20-R21-B.md).
No new authority model or architecture chain is introduced.

**Decision B - R24 OPERATIONAL LIMITATION REMAINS.** The targeted redesign and
focused regressions succeeded. The single isolated run completed the original
attempt and protected metadata path but exhausted v1's original 120-second
window during finalization reservation setup. No business effect, witness or
completed control outcome was produced. Full end-to-end acceptance remains
unverified; this report does not certify unexecuted finalizer paths.

The harness completed normally within its bound. The lifecycle diagnostic's
pytest pass means a valid fail-closed expiry was captured, not successful
recognition execution. Do not advance to R25 on this result.

## 2. Original bottleneck

[R22](recognition-runtime-security-consolidated-finalization-implementation-4e-20-R22.md)
recorded 50.1470s issuance final validation, 52.8792s attempt admission and expiry
during the next pre-insert evaluation with 0s remaining. Metadata was not reached.
The partial source-owner profile recorded 119 `_history` calls taking 8.4308s
inclusive inside a roughly 12s diagnostic, with current identity/history checks
dominating. That profile was not a complete G+2 lifecycle.

The identical SQL deny-set construction had already been removed. R24 does not
repeat or claim that R22 optimization as new work.

## 3. Root cause and equivalent read boundary

Within one original live evaluation, approval, proposal/ACK, readiness and scope
readers repeatedly requested the complete control graph through `_read_parts`
and `_identity_snapshot`. Each request repeated full schema, migration,
profile/binding, audit and claim/history validation even though the same genuine
manager retained its control `BEGIN IMMEDIATE` and no intervening control write
had occurred. Fresh target identity and authentication checks are distinct from
this repeated control-graph computation.

R24 deduplicates that graph work inside one synchronous registered evaluation.
It does not move it into pre-authority preparation, reuse an earlier phase's
history, or create durable prepared history evidence. The first history request
per evaluation still executes the complete original validator. Each later
evaluation starts empty, including evaluations after source writes, attempt
inserts, target mode changes, metadata commit/reacquisition and journal writes.

This relies on the existing transaction owner's authoritative control writer
reservation, not a new lease. Cooperating revocation writers retain R21-B's
commit ordering; requests blocked behind the reservation are not already
committed revocations. No control lock is treated as filesystem continuity.

## 4. Implemented changes

| File | Change |
| --- | --- |
| `runtime_history_validation.py` | Private operation-local work sharing, exact original-owner/resource/scope guard, mutation invalidation and fresh physical checks. No public capability or SQL interface. |
| `runtime_validation.py` | `_history` consults only that active exact scope; `_history_fresh` retains the original full validation body. All unsupported/out-of-scope calls follow the full original path. |
| `runtime_enrollment.py`, `runtime_profile_schema.py` | Record the original canonical-path predicates during full validation and repeat those same validators on consumption, including historical paths outside the current database pair. No schema definitions changed. |
| `runtime_enrollment_transition_schema.py` | Avoid repeated transition-row validation only when the same operation already completed full current history validation; the pending-transition query still executes. |
| `runtime_execution_coordinator.py` | Scope each live `_evaluate`; invalidate operation facts from the existing authorizer on mutations/transaction/mode changes. |
| `runtime_activation_authority_issuance.py` | Scope genuine coordinator/metadata/finalizer subject collection; other context types retain their original path. Nested subject collection shares only the current evaluation. |
| `runtime_target_entry_owner.py` | Scope each separate metadata evaluation and invalidate on attempted writes/mode changes. No evaluation, marker check or commit/reacquisition boundary removed. |
| `runtime_finalization.py` | Scope each separate `_fresh`; retain authorizer invalidation. Extract the existing target commit into private `_commit_target`, requiring its genuine state before invalidating views, for precise timing. |
| `tests/runtime_deadline_harness.py` | Replace one long native wait with nonblocking polls and at most 25ms sleeps against the same absolute deadlines; retain bounded cleanup and file-snapshot output. |
| Focused tests | Add history ownership/invalidation/equivalence tests and a harness test forbidding use of `Popen.wait`. |
| Lifecycle diagnostic | Preserve R24 phase checkpoints atomically, aggregate actual full-history passes, and capture metadata/target commit spans. No product clock or predicate substitution. |

There are no new SQL definitions, indexes, schema migrations, policy versions or
runtime permissions. No new issuer, producer, delegation or grant is introduced.

### Ownership and invalidation proof

The private scope accepts only actual registered coordinator-admission,
metadata or finalization states. It checks the original PID/thread/lifetime
through their existing resolvers, actual native SQLite connections and active
transactions, context/phase identity, reservation epochs, frozen scope, original
credentials, approval/reference/activation, MFA/mode and original authority JSON
and digest. The native control row factory must remain the expected SQLite Row.
Scope/resource changes reject rather than silently rebinding.

All attempted DML, including zero-row writes, transaction/savepoint actions,
DDL/ATTACH/DETACH and modifying mode/schema PRAGMAs invalidate operation facts
through the existing authorizers. Changed mutation counts require another full
graph pass; they do not permit reuse across the writes. Read-only introspection
PRAGMA arguments are not confused with mode changes. Denial paths retain their
existing manager-owned reductions and resolution.

Only a successfully completed `_history_fresh` may populate the scope. Returned
binding/profile DATA is defensively copied; the audit-head SQLite Row is
immutable. Failure publishes no saved success and scope exit always drops the
facts. Nothing survives into another evaluation, phase, transaction or ceremony.
No serialized snapshot can construct an owner or authorize execution.

## 5. Security invariants preserved

- Authentication, credential/authority expiry, consent, approval/proposal/ACK,
  decision identity, policy, exact action/write set and original holder checks
  still execute at their existing fresh boundaries.
- Physical control/target identities are reobserved on each consumption, and
  `_identity_snapshot` retains its actual identity/schema/fingerprint, ownership
  and epoch checks. There is no filesystem continuity assumption or TTL cache.
- Historical enrollment/profile path canonicalization is also repeated on every
  consumption; unchanged current database identities do not establish continuity
  for older or unselected historical paths.
- Migration relationships are validated in the full current pass, never
  established by Z15 inventory alone. Z15's scope is not enlarged and the R22
  additional source audit still invalidates the original five-write observation.
- Activation, stop, dependencies/readiness, duplicate state, effective revocation,
  exclusions and pending state are not cached as authorization decisions.
- Source, attempt and metadata ownership remain separate. Full fresh graph
  validation restarts after their writes and mode/connection/epoch changes.
- Control-before-target ordering, manager commits/rollback, original deadlines,
  credential clipping and commit-ordered revocation remain unchanged.
- Family regeneration, complete row-delta proof, target effects plus witness
  atomicity, positive committed inspection and conditional control outcome remain
  required. No cross-database atomicity or retry/adoption is introduced.

v1 remains **120 seconds/default**; v2 remains **300 seconds/prospective-test-only**.
No 600-second policy, test extension or switch to v2 to manufacture success.

## 6. Focused regression results

Initial harness/source-binding check: **8 passed, 9 subtests passed in 40.32s**.
The first history-focused file passed **7 tests in 57.23s** before adding the
mode-change test and strengthening the scope guard.

The strengthened guard's revocation test caught a concrete implementation error:
mutation-count tuple positions were incorrectly treated as immutable scope.
This was fixed within R24 by separating scope and mutation counts explicitly.
The isolated failing test then passed in **8.56s**. No security check was relaxed
and no new contract was requested.

Final focused invocation covered:

- `test_recognition_runtime_history_validation.py`;
- `test_recognition_runtime_deadline_harness.py`;
- the four existing R22 authorizer-cost, finalization component, integration and
  decision-outcome-journal schema files.

Before the isolated lifecycle: **48 passed, 42 subtests passed in 149.12s**.
Final-review hardening also preserves fresh historical-path canonicalization.
Its isolated rejection test passed in **7.24s**; the final focused invocation
then passed **49 tests, 42 subtests in 168.70s**. The prior 32-test/37-subtest security
coverage remains included. New tests prove fresh evaluation boundaries, defensive
copies, zero-row mutation invalidation, fresh revocation rejection, physical
replacement rejection, scope/mode and thread rejection, forged-state rejection
and query-result equivalence, including externally changed noncurrent historical
paths. Harness probes retain live-descendant output-handle
coverage and prohibit long native waits on timeout/cleanup paths.

For four identical current-history reads on the same disposable state, the
controlled comparison produced identical DATA with **344 -> 86 control
statements**, **0.1147282s -> 0.0317862s** on the final hardened revision. Every consumption still performed its
physical observation. This is a local operation comparison, not a statistical
guarantee of lifecycle latency. No broad suite ran.

## 7. Single isolated lifecycle timing

Final review after this measurement added fresh historical-path re-resolution
and its focused rejection test. Consequently the lifecycle timings below describe
the measured revision, not an end-to-end run of that final hardening. The original
current-database physical checks were present in the measured run. No second
lifecycle was run; successful final-revision end-to-end acceptance is not claimed.

Exactly one R24 lifecycle invocation ran, after focused tests passed. It used one
disposable G+2 fixture, original issuer/authority/coordinator and reservation
lineage, with the existing live monotonic-consistent clock. Run identity:
`e479368f-ce7e-477d-b37f-5ece21663856`. Evidence is in the dedicated
`.tmp/recognition-r24-lifecycle.json` and `.tmp/recognition-r24-parent.json`.
These are not R22's older artifacts.

| Stage | Start (s) | End (s) | Duration (s) | Authority budget | Result |
| --- | ---: | ---: | ---: | --- | --- |
| G+2 fixture preparation | 0.0010 | 101.6785 | 101.6775 | Not issued | Success |
| Issuer governance/MFA | 102.3880 | 105.5725 | 3.1846 | Not issued | Success |
| Fresh original consent | 105.5759 | 162.2799 | 56.7039 | Not issued | Success |
| Authority issuance/coordinator admission | 162.2830 | 184.8613 | 22.5783 | 113s at end | Success |
| Issuer-start validation/commit (nested) | 162.2932 | 166.5684 | 4.2752 | Not issued | Success |
| Initial issuance evaluation (nested) | 167.0215 | 172.3506 | 5.3291 | Not issued | Success |
| Producer pre-construction evaluation (nested) | 172.3529 | 178.3448 | 5.9919 | Not issued | Success |
| Issuance final validation (nested) | 178.4303 | 184.8548 | 6.4246 | 120s -> 113s | Success |
| Attempt creation (outer) | 184.8646 | 212.3266 | 27.4620 | 113s -> 86s | Success |
| Attempt admission evaluation (nested) | 185.3931 | 198.8728 | 13.4798 | 113s -> 99s | Success |
| Pre-insert evaluation (nested) | 198.8892 | 206.2346 | 7.3454 | 99s -> 92s | Success |
| Attempt final validation (nested) | 206.4065 | 212.3211 | 5.9146 | 92s -> 86s | Success |
| Protected metadata path (outer) | 212.3287 | 297.2928 | 84.9641 | 86s -> 1s | Success |
| Metadata admission validation | 213.4362 | 230.9255 | 17.4893 | 85s -> 67s | Success |
| Target mode transition | 230.9291 | 231.8963 | 0.9672 | 67s -> 66s | Success |
| Post-transition metadata validation | 231.9003 | 252.5583 | 20.6580 | 66s -> 46s | Success |
| Post-INSERT metadata validation | 253.0442 | 267.4716 | 14.4274 | 45s -> 31s | Success |
| Return to query-only mode | 267.4741 | 267.9267 | 0.4527 | 31s -> 30s | Success |
| Precommit metadata validation | 267.9290 | 282.6466 | 14.7177 | 30s -> 16s | Success |
| Metadata target commit | 282.6550 | 282.6620 | 0.0070 | 16s -> 16s | Success |
| Target reservation reacquisition | 282.6669 | 283.1254 | 0.4585 | 16s -> 15s | Success |
| Post-commit metadata validation | 283.1284 | 297.2850 | 14.1566 | 15s -> 1s | Success |
| Finalization entry (outer) | 297.2952 | 297.8737 | 0.5785 | 1s -> 0s | Expiry |
| Decision/pending-fence reservation setup (nested) | 297.3029 | 297.8710 | 0.5681 | 1s -> 0s | Expiry |
| Finalizer fresh action validation | UNMEASURED | UNMEASURED | UNMEASURED | Not reached | Not reached |
| Business effect/witness transaction and commit | UNMEASURED | UNMEASURED | UNMEASURED | Not reached | Not reached |
| Durable target outcome/committed inspection | UNMEASURED | UNMEASURED | UNMEASURED | Not reached | Not reached |
| Control COMPLETED/outcome publication | UNMEASURED | UNMEASURED | UNMEASURED | Not reached | Not reached |
| Failure cleanup | 297.875965 | 297.878596 | 0.002632 | 0s | Success |

Nested spans must not be summed. Marker construction/INSERT occurred between
post-transition and post-INSERT checks; its SQL execution time was not separately
instrumented and is not estimated as zero. No new business transaction is
confused with the successful metadata-only commit.

Each issuance/attempt live evaluation recorded **one full current history pass**.
The outer issuance-final span additionally recorded one pass outside its nested
evaluation, and attempt finalization recorded two additional passes outside its
nested evaluation. These final-boundary checks were not removed. Each of the five
metadata evaluations recorded one full pass, taking 0.1780s to 0.4661s each;
those five evaluations still took 14.1566s to 20.6580s overall. The remaining cost
therefore is not repeated `_history_fresh` traversal inside those evaluations.
These counters measure that function specifically: direct schema/history readers
outside it still execute and are not included. Other internal metadata cost was
not separately profiled in this run; this does not prove that every redundant
read elsewhere has been eliminated.

Observed issuance final validation improved from R22's 50.1470s to 6.4246s;
attempt admission from 52.8792s to 13.4798s. Different-run timings are not a
controlled guarantee or proof that every difference is caused by R24. The local
equivalence/query-count test and per-evaluation full-pass counts establish the
specific redundant-work reduction.

## 8. Lifecycle result and remaining budget

Source construction occurred at child elapsed **178.3686684s**. Original source
timestamps were `2099-01-01T00:20:08Z` and `2099-01-01T00:22:08Z`, exactly
120 seconds. Pre-authority setup is not authority age. Whole-second UTC expiry
and the original monotonic consistency checks are unchanged.

Exact failure: **AdminError: administrative_session_expired_or_revoked**, at
`durable decision and pending fence`, with **0 seconds remaining**. Finalization
reservation setup recorded three full history passes totalling 0.5252s and
expired before its first fresh finalizer action evaluation or decision INSERT.
The successful metadata path left only 1s for all remaining finalization work.

Child elapsed was **297.8812853s**. A genuine attempt and immutable metadata
marker were confirmed; the latter was independently revalidated after target
commit/reacquisition. Its opaque result was DATA, not writer authority. The
failed finalizer published no usable execution/completion result. The original
owner closed and no result was adopted or retried.

The five separate metadata validations and their surrounding boundaries consumed
84.9641s. R21-B requires those original protected phases, mode/write/commit and
post-commit checks. They cannot simply share pre-write history across a mode
change or commit to obtain a pass. Under this measured retained schedule the
window is already spent before finalization; a new issuer, permission or security
architecture would not supply missing time. A separately approved lifetime/product
decision is the relevant next decision if this implementation/workload must be
supported. No additional time is authorized here, and no higher value is claimed
sufficient because finalizer execution remains unmeasured.

This is not a proof that every further equivalent optimization is impossible,
nor a global correctness certificate. The tested redesign preserves the security
invariants and no product defect was identified at the observed expiry. Stop
instead of automatically starting another optimization or architecture chain.

## 9. Harness result

The corrected parent used nonblocking polls, never `communicate()` or an
unbounded pipe drain. Configured deadlines remained child 540s, termination 542s,
reap 543s, output 544s and final parent return 545s. Small controlled probes
proved direct-child timeout/termination/reaping and retained-descendant output
handling, including a test that makes any `Popen.wait` call fail.

Actual R24 parent: **301.8267915s**, `child_exited`, exit 0, reaped true,
cleanup complete, no termination requested, `parent_bound_exceeded=false`,
output snapshot collected and not truncated. Output collection finished at
301.8255425s. No parent timeout occurred. OS scheduling/native filesystem calls
are not represented as hard-real-time guarantees; late return remains a separate
measurement failure, never authority expiry.

The lifecycle pytest invocation reported **1 passed in 302.87s** because the
diagnostic accepts a valid fail-closed expiry. Its legacy internal classification
`C` means authority expiry, mapping to **R24 decision B**, not a new security
primitive or successful execution. `complete=true` marks a completed trace, not
a completed recognition operation. No second R24 lifecycle ran.

## 10. Production safety and static validation

Only fresh disposable fixtures/databases and repository source/test/report files
were accessed. Existing synthetic G+2 activation/enrollment prerequisites were
used; no production database, hosted resource, deployment key, permission,
authority, policy/lifetime or activation was accessed/changed/issued. No G1
producer or new authority class was implemented. No commit or push.

AST/whitespace checks passed for 13 changed Python files. Baseline lifetime-policy
and authority-schema hashes, legacy writer/local-execution/execution-schema
contents and fixed family INSERT SQL are checked unchanged. Existing journal
schema checks are included in focused validation; no schema or migration was
added. Report whitespace/local-link checks and `git diff --check` passed as
final checks. No broad suite or additional lifecycle is used to substitute for
the missing successful finalization.

## 11. Classification

Under the requested lifecycle classification: **B - remaining operational/lifetime
limitation**. Under the requested decision: **B - R24 OPERATIONAL LIMITATION
REMAINS**. No genuinely new authority/security primitive was revealed. The
scope-guard implementation defect found by focused testing was fixed and
revalidated before the isolated run; it is not the remaining lifecycle failure.

## 12. Exact next boundary

Stop for an **explicit product/security decision** about supporting the measured
retained ceremony within its authorized budget. Do not advance to R25, change
v1/v2, automatically grant a longer test lifetime, authorize 600 seconds, adopt
old state, retry after uncertainty or create another architecture chain.

PRODUCTION AUTHORIZATION: BLOCKED

PRODUCTION EXECUTION: BLOCKED

PRODUCTION ACTIVATION: BLOCKED
