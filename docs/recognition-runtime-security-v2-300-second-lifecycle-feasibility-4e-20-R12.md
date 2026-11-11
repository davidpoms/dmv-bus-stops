# 4e-20-R12 ? bounded test-only v2 lifecycle feasibility

## Baseline and isolated environment

[R11-G](recognition-runtime-security-versioned-lifetime-wal-validation-correction-4e-20-R11-G.md) validated the versioned migration and lineage surfaces: 24 tests and 59 subtests. Production/default issuance remains v1/120 seconds. The separate last-WAL-client environmental issue is not changed here.

One disposable run used the existing G+2 fixture and verified repository-root workspace adapter. Target, control and generated fixture key paths were checked to belong to that newly allocated workspace. The real lifetime migration ran once before G+2 transition preparation. No hosted/production connections or deployment credentials were used. No production database was migrated.

## Test-only authority construction

Only the dedicated diagnostic changed. Its scoped wrapper first invokes the real authority body constructor and its fresh consent checks, then selects the already-supported v2 representation before normal persistence. It computes expiry as the minimum of issue time plus 300 seconds and the original primary, session, step and confirmation deadlines; it rejects clipping below the requested 300 seconds. Canonical validation, persistence, audit, final validation and coordinator continuation remain authoritative. There is no production selector or change to the ordinary issuer.

The test authority was issued at `2099-01-01T00:18:52Z`, expiring at `2099-01-01T00:23:52Z` on the fixture's advancing test UTC clock. Policy: `recognition-runtime-authority-lifetime-300s-v2`. Original source deadlines had 29,228 / 28,628 / 503 / 503 seconds remaining at construction. No original credential or consent expiry was extended. Z15 executed: one hook, one preparation object, 2,813 reused schema-inventory reads. Migration relationships and all other mandatory live checks remained fresh.

## Harness and result

The corrected R4 parent harness enforced a 540-second child bound with five seconds of bounded cleanup (termination 542, reap 543, output 544, final return 545 seconds from parent origin). No unbounded pipe drain was introduced.

**Run 1: B ? fail-closed authority expiration.** Child lifecycle report elapsed: 465.817832 seconds, including preparation. Parent harness elapsed: 470.151880 seconds. Authority age: 300 UTC seconds; remaining: zero. Exact failure: `AdminError: administrative_session_expired_or_revoked`, during metadata-owner final validation before target commit. This is the actual emitted code, not a claim that the original session credential expired: source credentials remained longer-lived; the code propagates from the live scoped validation boundary.

No complete lifecycle sample exists. The diagnostic pytest passed because it accepts an interpretable fail-closed B outcome; that is not lifecycle success. No second attempt was made: the first valid expiry trace establishes this run's failure boundary, and another measurement was not needed to report it.

## Complete stage trace

Times are monotonic seconds from this child's diagnostic origin. Budgets are seconds from the authority's own UTC issue/expiry values; before issuance they are unavailable. Nested/overlapping stages must not be summed. Issuance and coordinator admission overlap; final validations nest within their parent operations.

| Stage | Start | End | Duration | Start budget | End budget | Status |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| authority issuance | 116.942199 | 197.200970 | 80.258771 | None | 269 | success |
| coordinator admission | 116.942208 | 197.200885 | 80.258677 | None | 269 | success |
| pre-authority/schema-inventory preparation | 166.501393 | 166.505675 | 0.004282 | None | None | success |
| coordinator final validation (issuance) | 166.538683 | 197.197322 | 30.658638 | 300 | 269 | success |
| attempt creation | 197.201040 | 307.194943 | 109.993903 | 269 | 159 | success |
| coordinator final validation (attempt) | 256.129787 | 307.192117 | 51.062330 | 210 | 159 | success |
| metadata lifecycle (parent span) | 307.194996 | 465.816836 | 158.621840 | 159 | 0 | failure |
| metadata-owner admission | 308.113182 | 355.326430 | 47.213248 | 158 | 111 | success |
| target mode transition | 355.326505 | 355.999281 | 0.672776 | 111 | 110 | success |
| metadata-owner final validation | 355.999383 | 405.915586 | 49.916204 | 110 | 60 | success |
| target-entry INSERT | 405.919026 | 405.921766 | 0.002740 | 60 | 60 | insert trace interval ended |
| metadata-owner final validation | 406.392671 | 453.689052 | 47.296381 | 60 | 12 | success |
| target mode transition | 453.689167 | 454.169328 | 0.480162 | 12 | 12 | success |
| metadata-owner final validation | 454.169473 | 465.809286 | 11.639813 | 12 | 0 | failure |
| cleanup/result publication (coordinator exit) | 465.817140 | 465.817331 | 0.000190 | 0 | 0 | success |
| target commit | UNMEASURED | UNMEASURED | UNMEASURED | UNMEASURED | None | UNMEASURED |
| reservation reacquisition | UNMEASURED | UNMEASURED | UNMEASURED | UNMEASURED | None | UNMEASURED |
| post-commit validation | UNMEASURED | UNMEASURED | UNMEASURED | UNMEASURED | None | UNMEASURED |

The INSERT interval ends at the next non-trigger SQL statement and includes intervening bookkeeping. It is not an isolated SQLite execution-cost measurement. The two mode transitions are the existing controlled write enable and return to query-only. The third metadata final validation failed before integrity/commit. Target commit, reservation reacquisition and post-commit validation were not reached. Existing exception rollback handles the uncommitted metadata transaction; no durable target entry or usable result was published. Coordinator cleanup completed after failure and is not successful result publication.

## Authority budget and parent timing

Authority construction occurred at child elapsed 166.516547 seconds. The remaining budget was 269 after issuance/admission, 159 after attempt creation, 111 after metadata admission, 60 after the first metadata final validation and INSERT, 12 after the second metadata final validation, and zero at failure. The monotonic origin observed after body construction reports approximately 0.698500 seconds remaining at the end; this is an observation-origin/whole-second UTC quantization difference, not additional lifetime. Product UTC expiry remains authoritative and was not extended.

Parent wait: 470.114432 seconds; reap: 0.001327 seconds; output snapshot: 0.021277 seconds; output-end through cleanup-end: 0.006947 seconds. Child exit code zero, reaped true, cleanup complete, no termination requested, no harness timeout, no parent-bound exceedance. Parent elapsed and child/authority elapsed have different origins and are not interchangeable.

## Lifetime comparison

There is no successful critical path or completion headroom to compare against 120/180/240/300 seconds. This test consumed the full 300-second authority before commit; it does not demonstrate that any candidate lifetime completes the lifecycle. Earlier measurements are not combined with this run. One run provides no statistical guarantee or proof of inherent infeasibility across hosts. No further lifetime increase is recommended or authorized here.

## Security interpretation and production safety

The additional 180 seconds increases exposure to an otherwise valid original holder; freshness, original credential clipping, replay protection, one-attempt/duplicate fencing, reservation concurrency, and uncertain-commit fail-closed handling remain separate requirements. The existing prospective v2 decision conditionally permits that bounded exposure; this unsuccessful measurement supplies no operational benefit evidence sufficient to justify production adoption or declare a broader exposure acceptable. It does not replace any independent control.

Production migration, canonical schema, lineage, base control schema and ordinary issuer source hashes were unchanged before and after this measurement. Ordinary issuance remains v1/120. No production policy changed, no production authority was issued, no production data was accessed, and no hosted resource was accessed. The only attempted target DML was the disposable metadata INSERT; no family/business effect, writer capability, execution completion, seal, readiness or activation was created. Downstream writer/execution entry points were test-guarded against invocation.

## Disposition and next boundary

**B ? bounded test-only v2 lifecycle feasibility incomplete.** The existing lifecycle did not complete within 300 seconds in this measured run. Stop measurement here. G1 remains unresolved and must not continue automatically. The next boundary is a separately authorized architecture/security decision on this measured pre-commit validation cost; neither automatic optimization, another lifetime increase nor T implementation is authorized by R12.

## Validation

One command only: `.\.venv\Scripts\python.exe -B -m pytest tests/test_recognition_runtime_lifecycle_deadline_trace.py::LifecycleDeadlineTraceTests::test_one_g2_v2_lifecycle -q -s -p no:cacheprovider --tb=short` ? **1 passed in 471.11s**, reporting lifecycle classification B. No Z18, T or broad suite ran. AST, document whitespace/local-link checks, unchanged-source hash checks and `git diff --check` were checked separately. No commit or push.

PRODUCTION AUTHORIZATION: BLOCKED

PRODUCTION EXECUTION: BLOCKED

PRODUCTION ACTIVATION: BLOCKED
