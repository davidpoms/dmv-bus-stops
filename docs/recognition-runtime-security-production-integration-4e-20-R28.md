# 4e-20-R28 - production integration implementation and validation

## 1. Decision and baseline

**A - R28 PRODUCTION INTEGRATION COMPLETE.**

[R21-B](recognition-runtime-security-consolidated-finalization-contract-4e-20-R21-B.md)
remains the security contract. The hardened R24 validation and successful
[R26](recognition-runtime-security-v2-300-second-lifecycle-validation-4e-20-R26.md)
baseline are preserved. This is completion of R28, not a new architecture stage.

[R27](recognition-runtime-security-production-readiness-review-4e-20-R27.md)
identified missing production provisioning, a bootstrap-only journal installer,
target-entry-only SQL admission, historical manifest incompatibility and missing
full-owner interruption evidence. These are implemented and tested below.

## 2. Production provisioning and trust input

`authority.provision_production_authority()` now uses the fixed
`runtime_production_governance` implementation. Unconfigured calls still reject.
It does not accept a caller-supplied verifier, trust key or general authorization
callback. Direct construction and serialization of Authority handles reject.

The deployment supplies an independently installed, OS-protected canonical public
trust file beside control: `<control filename>.governance-root.json`. Its closed
fields are format, mandate, installation_id, owner_id and public_key. The format
is `recognition-runtime-production-governance-v1`; the mandate is the existing
R21-B mandate. Production code never creates this root, signs approvals or reads
a private deployment key. Deployment review must protect installation/replacement
of this file under R21-B's protected-host configuration boundary.

Ed25519 verification uses the fixed domain `DMV-runtime-production-governance-v1`
followed by a NUL. The canonical signed body has only format, mandate,
installation_id, binding_sha256, holder, subject, target, control, issued_at_utc,
expires_at_utc and approvals. It binds actual target/control physical identities,
current installation binding and original actor/primary/session hashes. Invalid
signature, scope, owner, root replacement, thread, expiry or credentials deny.

Provisioning independently validates the existing primary/session/profile kernels
under the protected finalization owner, with query-only target and manager-owned
control commit/cleanup. It does not widen the activated-state 3a boundary or
expose its connections. Registered handles bind PID, live Thread, exact config,
original credentials, scope, root and exact approval tuple. Every use rechecks
the signature/root/identity/expiry and live authentication. R24 work sharing is
limited to its already-registered validation operation; no cross-phase cache is
introduced.

Closed subjects allow only the exact issuer intent/policy (four separately
enumerated bind/adopt/appoint/authorize approvals), exact journal migration,
exact issuer revocation or exact source outcome inspection. Each issuer approval
has a separate attributable audit relationship. Fresh owner MFA and all existing
source/decision/write-set/consumption/revocation fences remain mandatory. Signed
expiry clips to original credential expiry and remains checked through commit
and cleanup. The existing 600-second administrative freshness maximum bounds
these governance approvals; it is not a new source-authority lifetime.

## 3. Journal installation and exact SQL package scope

`runtime_finalization_schema_upgrade.migrate_control` installs the fixed
`recognition-runtime-finalization-journal-extension-v1` edge J after verified
A/T/E/L predecessors. It requires exact migration approval, generation/identity,
inactive state, no unfinished enrollment transition and no unsettled runtime
source/attempt/claim work. It checks current schema/history, takes the control
reservation then query-only target reservation, audits signed production approval,
installs only the existing journal definitions and one exact successor trigger,
validates the full graph and identities again, re-verifies approval, then commits
control while target remains reserved. Confirmed idempotent inspection installs
nothing again. No target DML occurs in this control installer.

The successor source guard permits exactly
`recognition-runtime-target-entry-storage-v1` or
`recognition-runtime-outcome-witness-storage-v1`. Every other original predicate
is retained. Python plan validation and the target DDL authorizer select only
these two exact packages. Arbitrary package SQL admission fails. Original E
definitions remain the historical root; the J successor does not rewrite them.

The existing W/Y owner performs the actual target package installation with
verified backups, full fingerprinting, reservation ownership, schema-bound
generation and reviewed runtime-profile finalization. It is not the disposable
pre-enrollment journal bootstrap. Multiple completed plans are allowed; a
different unfinished plan still rejects. Existing bootstrap guards are retained.

## 4. Historical manifest compatibility

The ordered graph independently reconstructs every predecessor and installed
manifest and checks its exact audit identity, ordering and hashes. J replaces
only the known original E guard and adds the fixed journal objects. Unknown
objects, predecessor substitution, collisions and skipped/reordered prerequisites
reject. No historical hash or authority is rewritten.

Historical plan manifests are selected by the plan's original audit position in
that verified graph, rather than compared to today's schema. Tests cover both
lifetime-before-entry and completed-entry-before-lifetime, followed by journal
installation and a second completed target/profile transition. The graph is
validated once only within a single native reserved reader operation when
sharing its local projections; unrelated readers still validate independently.

## 5. Isolated owner topology

The new test fixture starts with an already-enrolled owner database. It performs
real ENTRY W/Y G3-to-G5 enrollment, independently signed production-path J control
installation, then witness W/Y G5-to-G7 enrollment. Old credentials/approvals are
invalidated by those transitions and fresh G7 authentication/proposal/approval is
created. Production-labelled approvals enter the genuine production registry;
they are not relabelled disposable approvals. All files, identities and signing
keys are synthetic and test-local. No actual deployment trust root is installed.

The original-holder ceremony then provisions exact owner approvals, authorizes
the issuer, obtains new original consent, issues one source, creates its original
attempt/entry and enters protected fixed-action finalization. Only the isolated
approved R12/R26 pre-persistence adapter selects v2; source SQL/codec/expiry
checks remain enabled and ordinary issuance remains v1.

## 6. Full-owner crash and uncertainty evidence

**Eight owner-failure tests passed in 1756.52 seconds.** Five independent fault
children were used. Lost-response/restart/duplicate assertions reuse factual
inspection of the same interrupted durable state, not another authority or
another attempted execution. Each inspection runs in a new process, revalidates
the original browser credentials using the actual protected owner and obtains
inspection-only approval. The original executable handoff cannot be recreated.

| Fault | Child seconds | Fresh inspection seconds | Durable control state | Effects / witnesses | Retry authorized |
| --- | --- | --- | --- | --- | --- |
| concurrent | 286.833 | 7.511 | NO_DECISION | 0 / 0 | No |
| control_failure | 360.026 | 8.892 | TARGET_PENDING | 1 / 1 | No |
| after_commit | 365.244 | 8.176 | TARGET_PENDING | 1 / 1 | No |
| before_commit | 381.022 | 8.188 | TARGET_PENDING | 0 / 0 | No |
| revoked | 322.228 | 8.258 | NO_DECISION | 0 / 0 | No |

Before-commit termination rolls back the entire family snapshot and witness.
After-commit termination/lost response preserves the one complete effect and
witness; control can remain TARGET_PENDING. Control recording failure has that
same positive target fact without fabricated completion. Two inspections agree
and no retry right is restored. Foreign-thread use poisons the original
continuation, leaving zero effects/witnesses; it does not transfer execution.
Revocation denies with `finalization_issuer_revoked` before any decision/effect.
Each scenario has exactly one source. Repeated in-process finalization rejects.

Control and target are separate transactions: this is not cross-database
atomicity. Uncertainty publishes no usable success and never authorizes another
target execution, automatic repair, adoption or recovery-based reauthorization.

## 7. Focused regression and static integrity

**80 tests and 96 subtests passed in 292.08 seconds** in the final focused regression. Together with the eight owner-failure tests, this is **88 focused tests and 96 subtests passed**. The regression covered lifetime/default/clipping compatibility, R24 history validation, the bounded harness, R22 fixed-effect finalization and integration, outcome journal schema, ordered schema-package lineage, four late-journal tests and three production provisioning/history tests.

The earlier 63-test/51-subtest regression is superseded by the final focused run.
A newly added late-history test initially reached valid enrollment but used the
wrong assertion key (`audit.sequence` instead of the verified edge's `sequence`);
only that test diagnostic was corrected. No security check was relaxed.

AST and whitespace checks cover all 16 R28 Python files. Source snapshots are
compared before/after the clean lifecycle. The authority schema and lifetime
policy hashes remain unchanged. Legacy writer boundary, local execution and
legacy execution schema match HEAD; extracted family INSERT SQL literals match
the original. Exact SQL guards, schema lineage and old-row compatibility are
covered by the focused tests. Local document links/whitespace and
`git diff --check` are checked. No broad suite was run.

## 8. One clean owner lifecycle

Exactly one clean isolated owner lifecycle was run after focused tests passed.
Run ID: `f299c187-29ac-4b82-be4e-b8d28e1d00a2`. Classification: **A**.
Child elapsed: **337.871s** including pre-authority topology
and governance preparation. Parent elapsed: **342.333s**.
The harness uses a 540-second child bound with bounded cleanup; this is a test
process bound, not an authority lifetime. Parent status: `child_exited`,
exit code `0`, reaped `True`,
cleanup complete `True`.

Authority issued: `2099-01-01T00:21:20Z`;
expires: `2099-01-01T00:26:20Z`.
Measured authority elapsed: **159.102s**;
remaining after protected cleanup: **141.000s**.
All nested spans below are individual observations and must not be summed.
Dash budgets precede source issuance. Times are relative to child start.

| Stage | Start s | End s | Duration s | Start / end authority budget s | Status |
| --- | --- | --- | --- | --- | --- |
| owner topology preparation | 0.001 | 72.900 | 72.899 | - / - | success |
| control commit | 17.607 | 17.717 | 0.110 | - / - | success |
| signed owner production provisioning | 73.344 | 76.126 | 2.782 | - / - | success |
| control commit | 76.005 | 76.123 | 0.118 | - / - | success |
| issuer governance authorization | 76.127 | 80.848 | 4.721 | - / - | success |
| control commit | 80.711 | 80.843 | 0.132 | - / - | success |
| fresh original consent | 80.849 | 159.048 | 78.199 | - / - | success |
| source issuance and coordinator admission | 159.049 | 186.004 | 26.956 | - / 292.000 | success |
| control commit | 164.843 | 164.973 | 0.129 | - / - | success |
| coordinator final validation | 179.041 | 186.000 | 6.958 | 299.000 / 292.000 | success |
| original attempt creation and final validation | 186.005 | 208.689 | 22.684 | 292.000 / 270.000 | success |
| coordinator final validation | 200.669 | 208.684 | 8.015 | 278.000 / 270.000 | success |
| protected metadata | 208.690 | 267.318 | 58.628 | 270.000 / 211.000 | success |
| metadata fresh validation | 209.831 | 219.969 | 10.138 | 269.000 / 258.000 | success |
| metadata fresh validation | 220.566 | 230.523 | 9.958 | 258.000 / 248.000 | success |
| metadata fresh validation | 231.104 | 241.942 | 10.838 | 247.000 / 236.000 | success |
| metadata fresh validation | 242.566 | 253.839 | 11.273 | 236.000 / 225.000 | success |
| metadata commit | 253.847 | 253.851 | 0.004 | 225.000 / 225.000 | success |
| metadata reservation reacquisition | 253.854 | 254.444 | 0.589 | 225.000 / 224.000 | success |
| metadata fresh validation | 254.445 | 267.313 | 12.868 | 224.000 / 211.000 | success |
| protected owner finalization | 267.319 | 331.160 | 63.842 | 211.000 / 147.000 | success |
| durable decision and pending | 267.645 | 301.814 | 34.169 | 211.000 / 177.000 | success |
| fresh finalizer validation | 270.332 | 276.463 | 6.131 | 208.000 / 202.000 | success |
| fresh finalizer validation | 277.549 | 283.698 | 6.149 | 201.000 / 195.000 | success |
| control commit | 283.957 | 284.218 | 0.261 | 194.000 / 194.000 | success |
| fresh finalizer validation | 287.148 | 294.019 | 6.871 | 191.000 / 184.000 | success |
| fresh finalizer validation | 295.183 | 301.506 | 6.322 | 183.000 / 177.000 | success |
| control commit | 301.524 | 301.809 | 0.285 | 177.000 / 177.000 | success |
| fresh finalizer validation | 304.961 | 311.369 | 6.408 | 173.000 / 167.000 | success |
| fresh finalizer validation | 311.939 | 318.684 | 6.746 | 166.000 / 160.000 | success |
| fixed family business effect | 318.685 | 318.688 | 0.003 | 160.000 / 160.000 | success |
| complete-effect witness evidence | 318.692 | 318.695 | 0.002 | 160.000 / 160.000 | success |
| fresh finalizer validation | 319.409 | 324.434 | 5.025 | 159.000 / 154.000 | success |
| atomic effect/witness target commit | 324.437 | 324.446 | 0.009 | 154.000 / 154.000 | success |
| fresh finalizer validation | 325.033 | 329.480 | 4.448 | 153.000 / 149.000 | success |
| complete-effect witness evidence | 329.501 | 329.504 | 0.003 | 149.000 / 149.000 | success |
| control commit | 330.825 | 331.154 | 0.328 | 148.000 / 147.000 | success |
| independent production-path outcome inspection | 331.162 | 337.868 | 6.706 | 147.000 / 141.000 | success |
| control commit | 336.812 | 337.138 | 0.326 | 142.000 / 141.000 | success |
| complete-effect witness evidence | 337.821 | 337.823 | 0.003 | 141.000 / 141.000 | success |
| owner cleanup | 337.869 | 337.870 | 0.001 | 141.000 / 141.000 | success |

Durable outcome: `{"authority_id": "95f30796-c4d8-4b7f-83a6-6ec15ca1521f", "authority_sha256": "c80e4df73e7609d5ad727d44122c3b3bdbd79ce6d8af34df519479ef34e6ea32", "execution_authority": false, "retry_authorized": false, "state": "COMPLETED", "target_commit_verified": true}`.
The target family effect and decision-bound witness commit atomically. Control
COMPLETED and independent exact-D positive target verification are required for
success. Original manager cleanup and test workspace cleanup complete before
the child exits normally. No second clean lifecycle is run.

## 9. Production safety and remaining deployment boundary

No actual production database was accessed, authority issued, credential changed,
permission changed, migration executed or activation performed. All provisioned
production-labelled handles in these tests refer only to fresh synthetic local
databases. No real private deployment key was read. No hosted resource was used.
No commit or push was performed.

v1 remains **120 seconds and the ordinary/default production policy**. v2 remains
**300 seconds and prospective/test-only**. No default, expiry clipping, source
schema, execution authority or production configuration was broadened. G1 is
not implemented or automatically continued.

## 10. Next boundary and explicit blocks

Next: **4e-20-R29 - final consolidated production-readiness review and explicit deployment authorization preparation**. That review is evidence-based and does not reopen architecture. Actual protected trust input, deployment authorization and acceptance of the pending/uncertainty window remain deployment prerequisites; this implementation/test result does not supply them.

**PRODUCTION AUTHORIZATION: BLOCKED**
**PRODUCTION EXECUTION: BLOCKED**
**PRODUCTION ACTIVATION: BLOCKED**
