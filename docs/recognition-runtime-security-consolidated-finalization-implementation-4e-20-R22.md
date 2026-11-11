# 4e-20-R22 - consolidated finalization implementation status

## Baseline and decision

[R21-B](recognition-runtime-security-consolidated-finalization-contract-4e-20-R21-B.md)
remains authoritative. No additional architecture stage is proposed.

**R22 remains BLOCKED.** Under the latest continuation's outcome definitions,
**decision B - operational limitation remains**: the child again exhausted the
unchanged authority during required attempt validation after the narrow safe
optimization. The external harness also overran its own bound, so this is not a
successful bounded measurement. That result does not establish that all downstream
implementation requirements pass: metadata entry, protected finalization and
successful outcome publication were not reached end to end. No implementation
completion or readiness for R23 is claimed.

## Implementation and affected files

- `runtime_finalization.py`: distinct protected owner, authenticated governance
  and issuer provisioning, original-holder/source binding, durable issuance
  exclusion, revocation, decision/pending/outcome protocol and read-only durable
  inspection. No arbitrary SQL or general writer API.
- `runtime_finalization_storage.py`: existing Z31 package installation only into
  explicitly approved fresh disposable databases before enrollment; closed row
  projections/inserts. No production installer or enrolled-fingerprint repair.
- `runtime_finalization_contract.py`: closed canonical issuer/action DATA codecs;
  parsing or copying evidence confers no authority.
- `runtime_finalization_effects.py`: independently expected actual family rows,
  exact delta proof, complete-effect evidence and decision/pending/witness checks.
- `permanent.py`: private fixed family INSERT extraction. Legacy authorization,
  regeneration, verification, idempotency and transaction ownership remain in its
  wrapper. The private kernel accepts an explicitly validated sealing timestamp;
  legacy default clock behavior remains system UTC.
- `runtime_execution_coordinator.py` and
  `runtime_activation_authority_issuance.py`: optional exact original-owner
  finalization binding and separately proved extra eligibility audit. Ordinary
  issuance retains its five-write proof and v1 policy. The additional audit
  invalidates the original five-write preparation observation; fresh validation
  replaces reuse instead of broadening that continuity proof.
- `runtime_scope_validation.py` and `runtime_admission_validation.py`: explicit
  new-owner adapters retaining actual connection/transaction/reservation,
  epoch, process/thread and lifetime binding.
- `local_readiness.py`: only the exact original finalization owner can account
  for its independently verified own family delta during post-effect checks.
  All other dependency predicates remain freshly verified. Other owners and
  public readiness/activation gates retain their behavior. No receipt is issued.
- `administration_schema.py`, `runtime_schema_package_lineage.py` and
  `runtime_decision_outcome_journal_schema.py`: exact existing Z31 package
  recognition and bootstrap lineage. Base control inspection validates local
  structure; full COMPLETED inspection still requires actual target witness
  proof. Local structure never establishes a target commit.
- `tests/recognition_finalization_fixture.py` and the three
  `test_recognition_runtime_finalization*.py` files: dedicated disposable
  provisioning, component/integration tests and bounded lifecycle diagnostic.
  Shared workspace allocation and SQLite configuration are unchanged.

## Protected issuer and source entitlement

Four distinct scope-exact approvals bind governance identity, prospective policy
adoption, appointment and issuer authorization. Existing authentication and real
owner MFA are required. A private registry binds the provisioned disposable
approval to the exact configuration, process, live thread and credential hashes.
Issuer IDs, serialized evidence and restart inspection cannot recreate it.

A separately committed issuer-start audit spends the one issuance opportunity
before original source construction. Failure or uncertainty cannot reuse it.
Original source issuance records exact eligibility bound to the original
authority/decision digest, operation, manifest/write set, holder, target and
expiry. Original confirmation CAS remains authoritative; no authority is
reconstructed from caller input.

Issuer eligibility evidence is clipped by original credential expiry and the
existing bounded consent window. It is not a second execution lifetime. Action
expiry is clipped by the original source authority deadline. Existing authorities
gain no automatic new rights; v1 remains exactly 120 seconds.

Revocation and finalization serialize through the same control writer
reservation. Committed revocation rejects later use. A request waiting behind a
finalizer has not committed and is not falsely represented as already effective.

## Durable fencing, outcome and uncertainty

The genuine original attempt and its exact live metadata result are required.
The new owner preserves control-before-target reservation order, manager-owned
commit/rollback, raw-handle protection and view invalidation across mode/epoch
changes. Existing contexts are not promoted into general writer authority.

The selected Z30 split protocol is implemented:

1. Commit decision registration, permanent operation/manifest exclusion, genesis
   and audit while retaining target reservation.
2. In a separately confirmed transaction, freshly validate and append the sole
   TARGET_PENDING plus audit against the exact prior head.
3. Under a new control reservation, verify current original scope and pending
   identity, and regenerate the exact manifest before mutation.
4. Insert only the fixed family effects and exact decision-bound witness in one
   target transaction. Verify complete family deltas, non-family target data,
   control immutability, staged witness bytes and database integrity before commit.
5. Independently reopen/reserve the committed target, repeat current validation
   and recompute actual family/witness evidence. Append COMPLETED and audit;
   commit control while retaining target reservation.
6. Publish only a non-authorizing historical result after confirmed cleanup.

Cross-database atomicity is not claimed. Target-commit/control-publication
uncertainty leaves permanent exclusion and requires read-only durable inspection.
Inspection cannot retry, adopt, renew or create authority. Existing journal
uniqueness constraints fence competing decisions for an operation/manifest.
Local single-use guards supplement durable database fencing, never replace it.

## Focused results and coverage limits

- Finalization components, real governance/source integration and existing
  journal schema tests: **31 passed, 37 subtests passed in 159.09s**.
- After adding the final durable issuer-start fence, the exact original-source
  binding integration test passed separately: **1 passed, 4 subtests passed in
  97.05s**. No full lifecycle was repeated for this addition.
- Coverage includes actual MFA, distinct approvals, durable authentication
  denial, exact source binding, malformed/mismatched evidence, expiry,
  revocation/thread rejection, actual family rows, atomic family/witness
  commit/rollback, subprocess termination around target commit, separate-file
  control publication failure and SQLite duplicate/writer-reservation fencing.
- Earlier directly affected legacy family regression: **26 passed in 7.14s**.
  This preceded the private explicit-timestamp addition; it is not a fresh
  regression run of every final edit.
- Full journal inspection still rejects COMPLETED without actual witness proof.
  Component SQL concurrency/crash tests do not establish every protected public
  finalizer concurrency or fault-injection scenario.
- An extra binding diagnostic that performed two full live subject validations
  expired. It was reduced to its actual binding assertion. Production fresh
  validation remained intact; the complete ceremony was measured separately.
- Final static checks passed: AST and whitespace for 17 Python files; lifetime
  policy and authority schema hashes unchanged from the recorded baseline;
  legacy writer boundary, local execution and execution schema unchanged from
  HEAD; fixed family INSERT SQL literals identical to HEAD. R22 document
  whitespace/local links and `git diff --check` passed (existing CRLF conversion
  warnings only). Existing journal schema checks passed in the focused group.
  No broad suite ran. These checks do not replace missing end-to-end success.

## Isolated lifecycle result

The first isolated attempt exposed `issuance_inventory_invalid`: the extra
eligibility audit cannot reuse the original five-write schema observation.
The correction discards that observation and keeps fresh validation. It does not
relax its proof or any deadline. The corrected bounded run produced this valid
fail-closed trace. Measurements below are from that run only; nested spans are
not summed.

| Stage | Start (s) | End (s) | Duration (s) | Authority remaining | Result |
| --- | ---: | ---: | ---: | --- | --- |
| Finalized G+2 preparation | 0.0004 | 96.8550 | 96.8546 | Not issued | Success |
| Governance approvals/owner MFA | 97.2489 | 99.8159 | 2.5670 | Not issued | Success |
| Fresh original source consent | 99.8159 | 155.2635 | 55.4476 | Not issued | Success |
| Original issuance/coordinator admission | 155.2639 | 232.1675 | 76.9035 | 93s | Success |
| Attempt creation/final validation | 232.1676 | 324.8612 | 92.6937 | 0s | Expiry |
| Metadata-owner admission/final validation | UNMEASURED | UNMEASURED | UNMEASURED | Not reached | Not reached |
| Metadata mode/INSERT/commit/reacquisition | UNMEASURED | UNMEASURED | UNMEASURED | Not reached | Not reached |
| Finalizer admission/fresh validation | UNMEASURED | UNMEASURED | UNMEASURED | Not reached | Not reached |
| Business effect/witness/target commit | UNMEASURED | UNMEASURED | UNMEASURED | Not reached | Not reached |
| Inspection/control COMPLETED/result | UNMEASURED | UNMEASURED | UNMEASURED | Not reached | Not reached |
| Failure cleanup | 324.861522 | 324.861666 | 0.000144 | 0s | Success; no usable result |

Exact failure: **AdminError: administrative_session_expired_or_revoked** during
attempt creation/final validation. Source timestamps were
`2099-01-01T00:20:40Z` to `2099-01-01T00:22:40Z`, exactly 120 seconds.
Child elapsed: **324.8620s**. Parent return: **328.2210s**; child exit 0,
reaped, cleanup complete, no timeout or parent-bound overrun. External diagnostic
limit was 540s with 5s bounded cleanup, distinct from the product deadline.
The lifecycle diagnostic's pytest pass means a valid fail-closed outcome was
captured, not successful lifecycle completion.

This trace predates the final durable issuer-start fence and subsequent focused
hardening. It is not relabeled as a measurement of the final source revision.
No further complete lifecycle was run in that earlier continuation. The single
retry authorized by the subsequent cost-diagnosis request is recorded below.

## Pre-finalization cost diagnosis within R22

The preceding lifecycle table is the historical baseline, not a measurement of
this continuation. Its 76.9035s issuance/admission span included work before D
construction; only 27s of original authority budget had elapsed at admission.
The following 92.6937s attempt span included admission, pre-insert validation,
three graph inserts and final validation. It cannot be labeled 92.6937s of final
validation alone. Metadata and business-effect work did not execute and therefore
cannot explain that baseline's pre-metadata cost.

Two test-only G+2 profiling attempts hit the 360s external diagnostic cutoff
without obtaining an attempt-final profile (pytest totals 362.53s and 435.27s).
The first short-stop hook missed the imported physical-identity alias; after its
correction the second attempt still obtained no attempt-final entry marker.
These are diagnostic failures, not authority-expiry evidence or successful
lifecycle samples. No extra complete lifecycle was sampled. Their two dedicated
disposable workspaces were removed after child termination, using verified
workspace-contained paths. No old restricted directory or permission was changed.

The replacement component diagnostic used the real disposable original-holder
source-claim path, with authority construction explicitly forbidden, and stopped
after 12s at an original-owner check. It passed in 59.46s including fixture/setup
and cleanup; parent elapsed was 57.7214s, normally reaped, without timeout. This
component is not a complete G+2 lifecycle or an attempt-final timing substitute.
It identifies costs in the same current-scope/history kernels called by the
reviewed attempt path. There were zero authority-construction calls and no
metadata or family action.

| Measured component | Calls | Inclusive seconds | Interpretation |
| --- | ---: | ---: | --- |
| Original source claim (partial) | 1 | 11.7240 | Profiled original-owner component |
| `_subject_for_owner` (partial) | 1 | 10.3802 | Contains current-scope and inventory readers |
| `_identity_snapshot` | 117 | 9.3215 | Fresh identity plus current control/history |
| `_history` | 119 | 8.4308 | Dominant current graph-validation subtree |
| `check_control` | 120 | 6.2147 | Included in history, not additional budget |
| `_audit_head` | 252 | 2.4109 | Complete current audit-chain checks |
| `_authentication_writes` | 32,508 | 0.7308 | Pure SQL-callback policy evaluation |

These are nested, instrumented partial-component measurements and must not be
summed or extrapolated into a completion guarantee. Exclusive costs included
SQLite execution 1.2356s/18,062 calls; Windows final-path observation
0.9942s/3,856 calls; JSON encoding 0.7123s/14,498 calls; timestamp parsing
0.5172s/24,271 calls; and string splitting 0.4523s/104,873 calls. Required physical
observations were not cached. The sampled deadline list contained 16 entries
representing two distinct constraints; it was not modified merely because of
that duplication.

### Call-path classification

A means fresh security validation; B means permissible non-authoritative
preparation; C means deterministic computation only; D means demonstrated
redundant computation; E means required work implemented unnecessarily expensively.

| Operation in actual order | Class | Boundary and disposition |
| --- | --- | --- |
| Detached intent, candidate manifest, fixed write-set descriptor | B/C | Already prepared before original source issuance; DATA only. Current exact operation and write-set binding remain A. |
| Governance approvals, authenticated owner/MFA, issuer entitlement and revocation | A | Current exact scope, credentials and approved action; no earlier allow result is reusable. |
| Fresh source step-up and confirmation | A | Original consent, subject and credential clipping; not replaced by preparation. |
| Original issuer-start reservation, subject comparison and one-use audit | A | Durable no-retry issuance opportunity before source construction; current state must be checked. |
| Control/target acquisition, connection identity, thread/process, epochs and mode | A | Every original owner phase retains its reservation and lifetime checks. |
| Current profile, generation/owner, activation, physical/schema/fingerprint and MFA state | A | Re-read through `_current`, `_identity_snapshot` and shared view adapters. No filesystem continuity assumption. |
| Policy/version and deadline enforcement | A | Exact original policy, credential/consent intersection and current clock at each required boundary. Static expected constants alone are C. |
| Migration rows, history/audits, claim graph and control integrity | A | Writes invalidate prior complete graph observations; no cross-phase cache. |
| SQL definitions and schema inventory | C/B | Pure definition construction is deterministic; inventory reuse is only Z15's exact approved same-phase proof. The R22 extra source audit still invalidates the original five-write observation. |
| Admission `_collect` and issuer `_subject_for_owner` | A | Approval/proposal/ACK, exact decision/action, dependencies, stop, readiness and actual target scope remain independently fresh. Similar output is not proof of redundancy. |
| Manifest regeneration and exact equality | A | Actual whole-population preconditions under reservation; earlier candidate construction does not replace it. |
| Canonical encoding, expected row plans and payload construction | C/B | Non-authorizing computation may be prepared, but D originates only in its genuine constructor and actual rows must be regenerated/verified. No measured pre-metadata dominance justifies a new plan cache. |
| Source constructor, original five writes plus exact eligibility audit | A/C | Actual D, clipped original issue/expiry, CAS and durable original binding; no timestamp moved after writes. |
| Source final validation and confirmed publication | A | Fresh subject, complete mutation proof/control graph and identity/deadline checks before commit; cleanup precedes continuation. |
| Attempt admission, pre-insert evaluation, exact three graph inserts | A/C | Genuine original continuation, current graph/subject, attempt-body construction and exact audit binding. Two pre-insert checks are existing protected boundaries, not automatically removable duplicates. |
| Attempt final validation | A | Repeats `_evaluate`, exact attempt/authority/consent graph, full history, current scope/deadlines after the three writes. Earlier history cannot stand in for this graph. |
| SQL authorization deny-set construction | D/E | Same 21 immutable SQLite action constants were reconstructed on every callback. This deterministic construction was removed; every callback and fresh read remains. |
| Metadata admission/mode switch/INSERT/commit/reacquisition/final checks | A | Genuine original attempt and finalized G+2 required. This is a separate protected metadata transaction, not the later family-effect transaction. |
| Finalizer admission, exclusion/pending, revocation/finalization ordering | A | Original D/holder/current authorization, exact action/write set, duplicate state and retained control reservation; no preparation grants permission. |
| Family delta, actual-row witness and committed inspection | A/C | Encoding is deterministic, but actual protected snapshots/deltas and positive committed proof remain fresh; no cost is invented for unreached stages. |

Metadata protects the one immutable entry for the exact original attempt and its
authority, G+2 profile, activation, target, approval/ACK, authentication and
deadlines. It gives no writer authority. R21-B explicitly retains the original
source/attempt/metadata phases: it cannot be moved before the source/attempt or
outside the original authority window. Its static inputs can be prepared only
as non-authoritative DATA; all existing admission/mode/commit/reacquisition
checks remain. Expiry before entry is caused by preceding work, not a delayed
metadata INSERT or target business effect.

### Narrow optimization and security proof

Only `runtime_validation._authentication_writes` changed in production code in
this continuation: its identical per-callback DDL/ATTACH/DETACH deny-set
comprehension became one module-local immutable `frozenset` of the same 21
SQLite action numbers. This is executable-policy constant construction, not a
cached schema, migration, history, physical identity or authorization observation.
No validation result survives a boundary and no read/check/callback is skipped.
DML categories, allowed denial reductions, permission decisions, reservations,
revocation, duplicate fencing, clocks, deadlines and uncertainty behavior are
unchanged. No work was moved across an authority boundary.

`test_recognition_runtime_finalization_authorizer_cost.py` reconstructs the old
callback membership computation and compares every SQLite numeric action code
and all affected table categories. It also measures equal 30,000-call workloads
three times per implementation: median **0.2600882s -> 0.0100880s**, approximately
25.8 times faster for that isolated callback workload. It is not a lifecycle
speedup claim. The initial benchmark test had a test-only missing imported-name
setup error; its namespace was corrected before the focused run.

The focused group then passed **32 tests and 37 subtests in 158.66s**, retaining
the original 31-test security coverage and adding policy-equivalence coverage.
No broad suite ran. The only other new/changed files in this continuation are
the component profile test, callback-cost test, lifecycle test timing wrappers
and this report. The timing wrappers call the actual implementation once and
capture nested spans without changing returned evidence, validation or clocks.

### Single isolated retry after the optimization

Only one post-optimization complete-lifecycle invocation was made. The child
persisted a fresh trace and exited 0 after recording product expiry. The parent
classified a subprocess timeout and the pytest invocation failed; neither the
exit code nor the recoverable child artifact is reported as a successful bounded
end-to-end test.

| Stage from this child run | Start (s) | End (s) | Duration (s) | Remaining authority | Result |
| --- | ---: | ---: | ---: | --- | --- |
| Finalized G+2 fixture preparation | 0.0010 | 177.9373 | 177.9362 | Not issued | Success |
| Issuer governance/MFA | 178.6357 | 183.1791 | 4.5434 | Not issued | Success |
| Governance control commit (nested) | 182.9811 | 183.1735 | 0.1924 | Not issued | Success |
| Fresh original consent | 183.1792 | 373.2673 | 190.0882 | Not issued | Success |
| Issuance and coordinator admission (outer) | 373.2677 | 544.6419 | 171.3742 | 70s at end | Success |
| Issuer-start validation/commit (nested) | 373.2774 | 401.5782 | 28.3008 | Not issued | Success |
| Issuer-start control commit (nested) | 401.3631 | 401.5731 | 0.2101 | Not issued | Success |
| Initial issuance live evaluation (nested) | 402.4900 | 448.1573 | 45.6673 | Not issued | Success |
| Producer pre-construction evaluation (nested) | 448.1574 | 494.3274 | 46.1700 | Not issued | Success |
| Issuance final validation (nested) | 494.4886 | 544.6356 | 50.1470 | 120s -> 70s | Success |
| Issuance-final live evaluation (nested) | 494.4889 | 544.1406 | 49.6517 | 120s -> 70s | Success |
| Attempt creation (outer) | 544.6421 | 613.9554 | 69.3133 | 70s -> 0s | Expiry |
| Attempt admission evaluation (nested) | 545.6430 | 598.5223 | 52.8792 | 69s -> 16s | Success |
| Attempt pre-insert preparation (nested) | 598.5226 | 613.9518 | 15.4292 | 16s -> 0s | Expiry before INSERT |
| Pre-insert live evaluation (nested) | 598.5232 | 613.9517 | 15.4285 | 16s -> 0s | Expiry |
| Attempt graph INSERT and final validation | UNMEASURED | UNMEASURED | UNMEASURED | Not reached | Not reached |
| Metadata preparation/admission/mode/INSERT | UNMEASURED | UNMEASURED | UNMEASURED | Not reached | Not reached |
| Metadata commit/reacquisition/post-commit checks | UNMEASURED | UNMEASURED | UNMEASURED | Not reached | Not reached |
| Protected finalization/family+witness commit | UNMEASURED | UNMEASURED | UNMEASURED | Not reached | Not reached |
| Committed target inspection/control outcome | UNMEASURED | UNMEASURED | UNMEASURED | Not reached | Not reached |
| Failure cleanup | 613.955585 | 613.955707 | 0.000121 | 0s | Success; no usable result |

Nested spans must not be summed. Source construction occurred at child elapsed
**494.363066s**. The source's actual timestamps were
`2099-01-01T00:24:52Z` and `2099-01-01T00:26:52Z`, exactly 120 seconds.
The 494s pre-authority work does not consume an authority that did not yet exist.
Approximately 0.1255s elapsed between construction and issuance-final entry;
50.1470s issuance final validation then left 70s. Attempt admission alone consumed
52.8792s and left 16s. The second attempt evaluation, inside `_persist_attempt`
before observation minting or any graph INSERT, reached the original deadline.

Exact child failure: **AdminError: administrative_session_expired_or_revoked**,
`interrupted_stage=coordinator attempt live evaluation`, **0 seconds remaining**.
Child elapsed was **613.956031s**. This refines the previous combined-stage label:
the new run did not reach attempt final validation, rather than spending 69s in
that final boundary. No metadata or target business/witness transaction executed.
No usable result was published and no retry/adoption occurred.

There was also a separate harness failure: configured child limit **540s**,
termination **542s**, reap **543s**, output **544s**, parent return **545s**;
actual parent wait ended at **617.668870s** and parent returned at **617.670200s**.
It reported `subprocess_timeout`, `parent_bound_exceeded=true`, `exit_code=0`,
`termination_requested=false`, `reaped=true`, `cleanup_complete=true`, and
`output_status=collection_deadline`. No structured stdout reports were collected.
The exact cause of this parent wait overrun is not established here. Its timeout
is not product expiry. The child report was recovered from the newly written
dedicated JSON artifact after process exit; it is not the historical baseline.
The pytest result was **1 failed in 619.87s**, on the parent status assertion.
No second lifecycle or harness investigation was started after this result.

The callback benchmark demonstrates a narrow deterministic improvement; these
different wall-clock lifecycle runs do not establish an overall speedup or
regression attributable to it. Required current graph/scope evaluations still
consume the window. No additional observation is safely moved out of the fresh
ceremony under the existing continuity contracts. Outcome B identifies the
observed operational block, not a certificate that unexecuted downstream code
has been validated. No new product defect was identified by the passing focused
tests, but full R21-B acceptance remains unverified and the parent-bound failure
is an additional measurement limitation. Stop for a deliberate product/security
decision; do not increase a lifetime, create another architecture chain or advance
to R23 on this evidence.

Final continuation checks passed: changed Python AST/whitespace, document
whitespace/local links and `git diff --check`; policy/authority-schema baseline
hashes, legacy writer/local-execution/execution-schema contents and family INSERT
SQL remain unchanged. The new child trace's exact timestamps/error/budget and
parent PID/reap/cleanup were cross-checked. All R22 disposable workspace
directories were cleaned; only intended test diagnostic artifacts remain in
`.tmp`. No further pytest or lifecycle invocation followed the single retry.

## Safety and exact stopping boundary

The observed blocker is the unchanged operational authority window, not a newly
identified primitive. Complete protected-owner success and every protected-owner
concurrency/crash case remain unverified. Thus implementation acceptance remains
incomplete despite passing components. Stop within R22; do not advance to R23,
create another architecture stage, increase a lifetime or authorize retry.

Only fresh disposable databases were provisioned/mutated. No production or
hosted resource access, production migration, permission/policy change,
production authority issuance, activation or deployment-key read occurred.
v1 remains 120 seconds/default; v2 remains 300 seconds/prospective-test-only.
No G1 producer, legacy EXECUTING conversion, general writer capability or
readiness receipt was created. No commit or push occurred.

PRODUCTION AUTHORIZATION: BLOCKED

PRODUCTION EXECUTION: BLOCKED

PRODUCTION ACTIVATION: BLOCKED
