# 4e-20-R26 - v2/300-second lifecycle validation and compatibility correction

## 1. R25 authorization and original preflight defect

[R25](recognition-runtime-security-v2-final-lifecycle-decision-4e-20-R25.md)
authorized one isolated v2/300-second end-to-end validation under unchanged
[R21-B](recognition-runtime-security-consolidated-finalization-contract-4e-20-R21-B.md).
Original R26 preflight stopped without a lifecycle: the finalization policy codec
and action/source comparison were v1-only (`TrustError: finalization_policy`),
and the existing diagnostic asserted a 120-second source. That was a concrete
compatibility defect, not evidence against 300-second feasibility. The original
inert rejection evidence remains in `.tmp/recognition-r26-preflight.json`.

The project owner's R26-FIX request authorized correcting that compatibility
inside the existing implementation tranche, focused regression and then exactly
one lifecycle. No new architecture, issuer model or security policy is introduced.

**Final classification A - COMPLETE LIFECYCLE SUCCESS.** Exactly one R26 lifecycle
ran after the correction and focused validation. The operation completed within
the original v2 authority, with 194 seconds remaining after cleanup. No second
lifecycle, retry, adoption or deadline extension occurred.

## 2. Minimal compatibility correction

| Surface | Correction and preserved boundary |
| --- | --- |
| `runtime_finalization_contract._policy` | Resolve the lifetime ID through the existing closed `runtime_authority_lifetime_policy.seconds` resolver; retain all exact policy fields, policy format/version 1, action and one-grant limit. Only the two existing lifetime IDs are accepted. The finalization policy format version is distinct from the immutable lifetime-policy ID. |
| `runtime_finalization_contract.validate_action` | Require source authority lifetime policy to equal the exact approved issuer/action policy instead of a hard-coded v1 constant. Original source digest, decision, holder, operation/target/family/write set and interval checks remain. |
| `runtime_finalization.authorize_issuer` | Add an explicit lifetime-policy selection defaulting to v1. It must pass the closed codec and all four original exact-policy-digest governance approvals. v1 approvals cannot authorize v2. No numeric lifetime input or automatic policy selection. |
| `test_recognition_runtime_finalization_lifetime_policy.py` | Detached DATA tests for old/new codecs, historical canonical bytes, version/duration rejection, source-policy mismatch, original digest, exact action/target/write set and clipping. |
| `test_recognition_runtime_finalization_integration.py` | Real disposable governance check: v1 proofs reject v2 selection, while four exact v2 proofs authorize and historically validate that v2 issuer subject. |
| `test_recognition_runtime_finalization_lifecycle.py` | Explicit test-only `RECOGNITION_R26_V2=1` mode, separate R26 evidence files, existing disposable pre-enrollment compatibility migration/selection adapter and additional witness/journal timing. Ordinary diagnostic mode remains v1. |

No schema definition, migration implementation, historical source reader, ordinary
source issuer default, authority policy mapping or fixed target mutation primitive
was changed. Existing finalization issuer/action bodies and their historical v1
meaning remain unchanged. Their parsers still validate original canonical bytes
and digests; new support does not rewrite or reinterpret old records. A v2 action
cannot bind a v1 source, and a v1 action cannot bind a v2 source.

## 3. Exact code/configuration under test

The run used final hardened R24, including fresh historical-path re-resolution,
plus only the compatibility changes above. No implementation was modified during
or after the lifecycle. Source SHA256 snapshots are recorded in
`.tmp/recognition-r26-fix-source-hashes.json` and rechecked after execution.

The unchanged authority-schema SHA256 is
`f399540df6b27866b1c539b38e21aa3da584bed4c7de43f6e801197de7a52644`;
the unchanged lifetime-policy implementation SHA256 is
`d6119d7cccb28ecd8e99c6f45c4b0bdac8b44c37d8d2904d132aaa94f4c0e84b`.
The original R26 preflight hashes document the prior v1-only finalization sources;
they are historical evidence, not hashes of the corrected implementation.

The invocation was one pytest run of
`tests/test_recognition_runtime_finalization_lifecycle.py` with the explicit
`RECOGNITION_R26_V2=1` child-inherited environment flag, removed from the invoking
shell afterward. It reported **1 passed in 340.30s**. Unlike R24's accepted
fail-closed-expiry pass, this run's child classification and independently
verified outcome are both successful.

## 4. Test authority and isolation

The source policy was exactly `recognition-runtime-authority-lifetime-300s-v2`.
The unchanged resolver maps v1 to 120 seconds and v2 to 300 seconds. Ordinary
source issuance/default remains v1. No v3, alternate duration or 600-second policy.

The existing R12 test-only adapter selects v2 before persistence, after the real
source constructor has performed original consent/fresh-scope checks. It resolves
actual primary, session, step and confirmation deadlines and computes their
minimum with issue time plus 300. No source validator, SQL CHECK, clock predicate,
consent validity or credential expiry is relaxed. The adapter asserts an exact
300-second resulting interval; it does not extend a clipped credential.
The coordinator's committed canonical source was checked equal to that exact body.

The original credential/consent remaining bounds at issuance were respectively
29128, 28528, 532 and 532 seconds. These are observed fixture bounds, not new
lifetimes. Consequently clipping allowed the selected source interval unchanged:
`2099-01-01T00:20:33Z` to `2099-01-01T00:25:33Z` (synthetic fixture UTC).
The source was constructed at child elapsed 228.603848s. Its original live clock
advanced with monotonic time; no post-issuance fixture time extension occurred.

One unique repository-root disposable workspace contained all target/control/key
fixture paths. The adapter verified its registered disposable ownership and path
containment. It installed the existing lifetime compatibility migration exactly
once before the W/G+2 schema/profile binding and before authority consent. This
was a disposable migration, not a new migration implementation or a production
migration. The fixture retained synthetic keys/approvals and existing SQLite
configuration/cleanup. No deployment key or hosted resource was accessed.

## 5. Focused compatibility and regression

Before lifecycle execution:

- New detached compatibility file: **9 passed, 9 subtests passed in 1.00s**.
- Full relevant R22/R24 security group plus that compatibility file:
  **58 passed, 51 subtests passed in 187.15s**. This retains the prior
  49-test/42-subtest coverage, including the original R22 security tests.
- Additional targeted checks: **3 passed, 5 subtests passed in 33.36s**:
  exact-v2 governance approval binding; existing v1 normal/near-expiry/credential-
  clipped migration preservation; existing v2 representation/clipping,
  immutability and invalid/unknown-policy rejection. These retain predecessor
  manifests, canonical historical rows and isolated-admin checks.

The added governance test was separately run after the larger group's collection;
it was not counted as an extra test in that group's 58. No broad suite ran.

Tests cover: v1 acceptance and lossless historical round trips; exact v2/300
acceptance; unknown IDs/policy versions; arbitrary duration/extension; no v1-to-v2
reinterpretation or reverse mismatch; immutable original source digest;
exact action/target/write-set binding; source/issuer interval intersection;
v1 default; and real approval-policy digest enforcement. Migration tests also
exercise persisted SQL guards and historical credential-expiry reconstruction.

## 6. Complete single-run timing table

Run identity: `1df0eb7b-1b58-4a55-8c09-6efc92fcb17c`.
Child evidence: `.tmp/recognition-r26-lifecycle.json`.
Parent evidence: `.tmp/recognition-r26-parent.json`.
All rows below are from that one run, in recorded start order. Times are seconds
from child start. Nested/overlapping spans must not be summed.

| Stage | Start | End | Duration | Authority remaining | Result |
| --- | ---: | ---: | ---: | --- | --- |
| preparation / finalized G+2 fixture | 0.001044 | 140.901839 | 140.900795 | Not issued | success |
| issuer governance / MFA validation | 141.188014 | 144.074871 | 2.886857 | Not issued | success |
| finalization control commit | 143.940099 | 144.069093 | 0.128994 | Not issued | success |
| fresh original source consent | 144.077255 | 215.596093 | 71.518838 | Not issued | success |
| authority issuance / original coordinator admission | 215.598150 | 233.487912 | 17.889762 | Not issued -> 295 | success |
| prospective issuer-start validation and commit | 215.604817 | 219.797387 | 4.192570 | Not issued | success |
| finalization control commit | 219.644281 | 219.792553 | 0.148272 | Not issued | success |
| coordinator issuance live evaluation | 220.322285 | 224.472583 | 4.150299 | Not issued | success |
| coordinator issuance live evaluation | 224.475085 | 228.570843 | 4.095757 | Not issued | success |
| coordinator issuance final validation | 228.659851 | 233.481017 | 4.821166 | 300 -> 295 | success |
| coordinator issuance live evaluation | 228.662494 | 233.155833 | 4.493339 | 300 -> 295 | success |
| attempt creation / final validation | 233.490456 | 249.038762 | 15.548306 | 295 -> 279 | success |
| coordinator attempt live evaluation | 234.156837 | 238.940494 | 4.783657 | 294 -> 289 | success |
| attempt preparation and exact graph INSERT | 238.943134 | 243.509020 | 4.565885 | 289 -> 285 | success |
| coordinator attempt live evaluation | 238.945360 | 243.383674 | 4.438314 | 289 -> 285 | success |
| coordinator attempt final validation | 243.511636 | 249.032943 | 5.521308 | 285 -> 279 | success |
| coordinator attempt live evaluation | 243.518642 | 248.360121 | 4.841479 | 285 -> 280 | success |
| protected target-entry metadata | 249.041241 | 288.564430 | 39.523189 | 279 -> 240 | success |
| metadata fresh validation | 250.716438 | 257.527396 | 6.810958 | 278 -> 271 | success |
| metadata target mode transition | 257.530198 | 258.390038 | 0.859840 | 271 -> 270 | success |
| metadata fresh validation | 258.392433 | 265.237571 | 6.845138 | 270 -> 263 | success |
| metadata fresh validation | 265.782644 | 273.030065 | 7.247421 | 263 -> 255 | success |
| metadata target mode transition | 273.032959 | 273.574184 | 0.541225 | 255 -> 255 | success |
| metadata fresh validation | 273.576393 | 281.025479 | 7.449086 | 255 -> 247 | success |
| metadata target commit | 281.034722 | 281.040917 | 0.006194 | 247 -> 247 | success |
| metadata reservation reacquisition | 281.045329 | 281.577313 | 0.531984 | 247 -> 247 | success |
| metadata fresh validation | 281.579908 | 288.556929 | 6.977021 | 247 -> 240 | success |
| fresh finalization / atomic effect and witness / control outcome | 288.567338 | 334.254806 | 45.687467 | 240 -> 194 | success |
| durable decision and pending fence | 288.576859 | 314.119054 | 25.542195 | 240 -> 214 | success |
| finalizer fresh validation | 290.955396 | 294.844492 | 3.889096 | 237 -> 234 | success |
| durable journal INSERT / recognition_runtime_outcome_decisions | 295.352653 | 295.356814 | 0.004161 | 233 -> 233 | success |
| durable journal INSERT / recognition_runtime_outcome_history | 295.359753 | 295.363068 | 0.003315 | 233 -> 233 | success |
| finalizer fresh validation | 295.869345 | 300.521357 | 4.652011 | 233 -> 228 | success |
| finalization control commit | 300.779727 | 301.043171 | 0.263444 | 228 -> 227 | success |
| finalizer fresh validation | 304.229048 | 308.566449 | 4.337401 | 224 -> 220 | success |
| durable journal INSERT / recognition_runtime_outcome_history | 309.080788 | 309.084597 | 0.003809 | 219 -> 219 | success |
| finalizer fresh validation | 309.618684 | 313.812053 | 4.193369 | 219 -> 215 | success |
| finalization control commit | 313.839145 | 314.112354 | 0.273209 | 215 -> 214 | success |
| finalizer fresh validation | 316.851908 | 320.995754 | 4.143846 | 212 -> 207 | success |
| finalizer fresh validation | 321.540169 | 325.667215 | 4.127047 | 207 -> 203 | success |
| fixed family INSERT kernel | 325.669894 | 325.674399 | 0.004505 | 203 -> 203 | success |
| actual family-effect witness evidence | 325.679333 | 325.684123 | 0.004790 | 203 -> 203 | success |
| target witness INSERT | 325.710836 | 325.714082 | 0.003246 | 203 -> 203 | success |
| finalizer fresh validation | 326.253384 | 329.175551 | 2.922167 | 202 -> 199 | success |
| atomic family and witness target commit | 329.179993 | 329.187328 | 0.007335 | 199 -> 199 | success |
| finalizer fresh validation | 329.719053 | 332.656333 | 2.937280 | 199 -> 196 | success |
| actual family-effect witness evidence | 332.685343 | 332.688971 | 0.003627 | 196 -> 196 | success |
| durable journal INSERT / recognition_runtime_outcome_history | 333.265789 | 333.270114 | 0.004325 | 195 -> 195 | success |
| finalization control commit | 333.923499 | 334.246326 | 0.322828 | 194 -> 194 | success |
| durable outcome inspection | 334.257561 | 334.652929 | 0.395368 | 194 -> 194 | success |
| actual family-effect witness evidence | 334.594513 | 334.600066 | 0.005553 | 194 -> 194 | success |
| cleanup / result publication | 334.655169 | 334.657360 | 0.002191 | 194 -> 194 | success |

Target-entry marker construction/INSERT occurred between its post-transition and
post-INSERT metadata validations; its SQL execution time was not separately
measured and is **UNMEASURED**, not zero. The preparation/exact-graph span and
its nested live evaluation overlap; pre-insert validation is the nested attempt
evaluation starting at 238.945360s. Five metadata validations remain separate,
including post-commit reservation reacquisition and validation. Journal INSERT
rows are SQL-call spans, not claims of durable commit before their following
manager-owned commit. Witness evidence is measured again during independent
committed inspection; those spans are distinct checks, not repeated mutations.

## 7. Remaining authority and lifecycle result

| Boundary | Remaining source lifetime |
| --- | ---: |
| Source construction / issuance-final entry | 300s |
| Coordinator admission complete | 295s |
| Attempt creation/final validation complete | 279s |
| Metadata/post-commit validation complete | 240s |
| Decision and pending fence committed | 214s |
| Fixed family effect and witness INSERT | 203s |
| Atomic target commit | 199s |
| Control COMPLETED commit | 194s |
| Independent outcome inspection and cleanup/publication | 194s |

Whole child duration was **334.659600s**. Approximately **106.053512s** elapsed
from source construction to cleanup completion (334.657360 - 228.603848), while
whole-second product observations reported 106 seconds of authority age and
194 seconds remaining. Pre-authority preparation/consent is not authority age.
The entire child can therefore exceed 300 wall-clock seconds while completing
within its original 300-second authority. No previous timing run is combined here.

The same source decision was retained throughout:
authority ID `6a3a64df-d407-43d3-819a-dd1e953cda37`,
source digest `664466aa8faf0fbbca6e15a5af3a26bea75cc1ea650bc08ae303475c838987ce`.
The finalizer returned COMPLETED. Independent read-only inspection confirmed
COMPLETED, actual committed family effects, the decision/pending-bound witness
and matching control outcome for that same authority, with `retry_authorized=false`.
Result inspection and original manager cleanup both completed before expiry.

## 8. Security invariant results and limits

Actual fresh issuer/finalizer authentication and consent, exact approved policy,
original holder, source/decision digest, target/family/action/write set,
credential clipping and expiry checks ran through their existing boundaries.
The lifecycle kept control-before-target ownership, reservation epochs, physical
identity/path checks, current migration/history/control/claim/approval/ACK,
activation, readiness, dependency, emergency-stop and revocation checks.
R24 observation reuse did not replace physical validation or cross phases/writes.

The fixed family kernel ran once. Complete actual row-delta verification and
protected-table checks preceded the decision-bound witness INSERT. Family effects
and witness shared the original target transaction and one target commit.
A newly reserved independent connection verified the committed witness/effects
before the conditional control COMPLETED event and commit. Control and target
are separate databases; no cross-database atomicity is claimed.

Duplicate/concurrency fences and fail-closed uncertainty handling are unchanged,
with relevant focused regression still passing. This success run did not inject
every crash, revocation or uncertainty case; it does not replace those tests or
constitute a statistical runtime guarantee. No retry, renewal, adoption, general
writer capability or new authority class was introduced. There was no observed
R21-B invariant failure, authority expiry, implementation error or ambiguous
commit in this run.

## 9. Harness result

The existing corrected harness retained child timeout 540s, termination deadline
542s, reap 543s, output 544s and final parent deadline 545s. Those are diagnostic
bounds; source authority remained exactly 300 seconds. It used nonblocking polls,
bounded cleanup and fixed file snapshots without unbounded pipe draining.

Parent result: **338.637159s**, `child_exited`, exit code 0; child reaped and
cleanup complete; no termination requested, no truncation and
`parent_bound_exceeded=false`. Wait ended at 338.635825s, reap ended at
338.635831s, output collection ended at 338.636346s and cleanup ended at
338.637157s. Parent wait includes child pytest/fixture teardown; it is not source
age or a summed lifecycle phase. The child and parent report run IDs match.
No timeout occurred and no second lifecycle was launched.

## 10. Static and production-safety verification

Changed Python AST/whitespace, source snapshot, schema/source integrity,
legacy writer/local-execution/execution-schema and fixed family INSERT SQL checks
passed. The unchanged lifetime/schema mappings and migration lineage were also
covered by focused validation. Report whitespace/local-link checks and
`git diff --check` passed. No broad suite or production migration was run.

No production database/configuration/permissions/policy/activation, hosted
resource or deployment private key was accessed or changed. v1 remains the
production/default policy, and no production v2 authority was issued.
Only disposable fixtures received their synthetic approvals, migration, source,
metadata and tested business effects/witness/outcomes. No G1 implementation or
producer, schema change, new lifetime, permission broadening, commit or push.

## 11. Classification and exact next boundary

**A - COMPLETE LIFECYCLE SUCCESS.** The original preflight compatibility defect
was corrected within the authorized tranche, focused compatibility/security
checks passed, and the single v2 lifecycle completed with 194 seconds remaining.
This demonstrates isolated feasibility for this run, not production readiness or
universal timing guarantees.

Next: **4e-20-R27 - consolidated production-readiness review**, directly. It must
cover implementation, focused security tests, this successful isolated lifecycle,
timing, crash/uncertainty, duplicates/replay, revocation, complete-effect proof
and production-safety evidence in one review. Do not create architecture stages
for individual passing properties. No R27 review, production authorization,
production execution or activation is performed by this report.

PRODUCTION AUTHORIZATION: BLOCKED

PRODUCTION EXECUTION: BLOCKED

PRODUCTION ACTIVATION: BLOCKED
