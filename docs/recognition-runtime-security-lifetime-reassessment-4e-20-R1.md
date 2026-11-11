# 4e-20-R1: recognition security and authority-lifetime reassessment

## 1. Original objective and assessment result

The objective is a recognition system that works appropriately with reasonable
security for a public-facing application. A numeric timeout is a design choice
to justify against workload and threats, not a security axiom.

**Recommendation D - INSUFFICIENT EVIDENCE.** Available evidence establishes a
current enforced 120-second policy and legitimate partial workloads that exhaust
it. It does not establish why precisely 120 seconds is necessary or a complete
workload distribution from which to select a defensible replacement. This is a
completed assessment with an explicitly limited recommendation, not permission
to change policy or evidence of inherent architectural impossibility.

No production behavior, lifetime, policy, permissions, schema or migration changes.
G1 is not adopted and the G-series is not continued automatically.

## 2. Origin and classification of 120 seconds

The earliest explicit numeric source located in the relevant architectural records
is [4e-11 section 5](recognition-runtime-activation-bound-authority-contract-4e-11.md).
It calls `recognition-runtime-authority-lifetime-120s-v1` a **new explicit policy
proposal**, independently of the preactivation 4d claim's 300-second rule. It sets:

```text
expires = min(issued + 120, primary expiry, session expiry,
              producer step expiry, producer confirmation expiry)
```

That section describes a proposed bounded safety limit, expressly disclaims proof
that deployed jobs fit, and permits review of a new policy version if rehearsal
cannot finish. It supplies no quantified adversary model, exposure target or
operational SLO that singles out 120 rather than 180/300/600 seconds.

| Evidence | Classification | What it establishes |
| --- | --- | --- |
| 4e-11 explicit lifetime proposal | A: explicit normative security-policy rule once adopted in the contract | Intent to bound authority, with 120 selected; not an independently demonstrated necessity for that number |
| Authority codec, SQL and producer | C: inherited implementation/policy convention from that proposal | The current software consistently enforces the chosen number |
| Z5/Z13 and later instructions retaining a mandatory ceiling | D: defensive preservation of existing policy pending review | Legitimate change-control boundary, not independent first-principles justification |
| Operational requirement uniquely demanding 120 | B: not found | No complete-runtime SLO or exposure/availability requirement was located |
| Ultimate quantitative rationale for choosing exactly 120 | E: cannot establish from available evidence | No basis to claim a specific threat threshold was measured |

This distinguishes origin of the implemented rule from origin of its numerical
justification. Earlier 4e-3 explicitly left numeric readiness lifetime undecided;
the separate 300-second claim and 600-second consent lifetimes are neither proof
120 is correct nor automatic authorization to reuse their values.

Actual code: `runtime_activation_authority_issuance._body()` clips expiry as above;
`runtime_activation_authority_schema` fixes the policy ID and validates the same
ceiling in Python, SQL CHECK/guards and historical graph validation. Tests mirror
those rules. `runtime_execution_coordinator` and `runtime_target_entry_owner`
recheck original expiry; attempt time does not restart it. Relevant files are
currently outside committed history at local HEAD `4fc93a9`, so local git history
does not establish an earlier numeric rationale for them. No environment setting
was found making this a configurable operational timeout; secrets were not read.

## 3. Security function: bounded lifetime versus 120 seconds

**Bounded authority lifetime** limits how long an original consented decision may
remain usable. **120-second lifetime** is one possible bound. The former can be
a real security property without proving the latter uniquely correct.

| Property | Actual dependence on lifetime |
| --- | --- |
| Authority/intent freshness | Direct: longer maximum age permits an older decision to remain usable, subject to all independent current checks |
| Stale-consent exposure | Direct upper bound, additionally clipped by original consent/credential expiry; fresh mutable state does not prove the person still intends execution |
| Credential exposure | A longer bound can increase exposure if an attacker has the necessary live original context/credentials; a detached authority ID alone is not a bearer execution right |
| Replay exposure | Time bounds a possible live-use interval, but uniqueness, consumption, exact scope and original-owner registration independently reject replay. A short timeout alone never supplies exact-once behavior |
| Resource consumption | An expiry check can bound approved use, not guarantee prompt cancellation of CPU, locks, blocked I/O or commit. External diagnostic watchdogs are separate |
| Concurrency | Database reservations and exact current-state validation serialize participating writers; 120 is not a locking protocol |
| Duplicate execution | Durable unique operation/manifest and consumption/history fences are needed regardless of duration; expiration cannot remove them |
| Crash/uncertain outcome | Requires durable evidence and no blind retry. A deadline does not prove commit/rollback or authorize recovery |

The public-facing threat is not only stolen authority JSON. Consider account/session
compromise, malicious request replay/substitution, stale owner intent, changed scope
or activation, resource exhaustion, concurrency and a compromised trusted runtime.
Fresh checks reduce mutable-state exposure; they do not eliminate consent age or
make compromised trusted code safe. Shorter lifetimes likewise do not repair an
unimplemented writer authorization or outcome-attestation boundary.

## 4. Independent protections: implemented versus proposed

| Protection | Repository evidence and limit |
| --- | --- |
| Authority identity/action binding | Implemented canonical authority ID/body, exact operation/manifest/population/profile/activation/approval/auth scope; schema uniqueness and immutable AUTHORIZED genesis. Does not itself grant a writer |
| Consent | Existing owner MFA/replay-counter, one-use confirmation, exact subject/session/actor and clipped original deadline in `runtime_authority_consent`/issuer. G1-specific prospective consent remains proposed |
| Target binding | Strict actual hostname/path/device/inode/schema, installation/profile/generation/owner/epochs. No hostname allowlist or stale physical continuity assumption |
| Ownership/reservations | Genuine private registries, actual PID/Thread/context/connection/transaction/epoch, manager-owned control-first reservations and target held through required control commit |
| Fresh validation | Existing coordinator/admission/profile/auth/approval/ACK/dependency/stop/history/claim/control/readiness checks repeat at protected boundaries; no cross-boundary allow cache |
| Duplicate fencing | Source uniqueness, existing attempt/claim constraints and no-adoption paths exist. Z31 outcome decision/witness package is inert; its proposed runtime business-effect fence/producer must not be described as deployed |
| Auditability | Existing immutable canonical audit/source/attempt graphs. Generic audit text does not establish G1 governance or permission |
| Expiration | Implemented strict current time before original clipped deadline and clock checks. Generic expiry error may represent an accumulated authority bound, not independently expired login credentials |
| Crash/uncertainty | Existing managers poison live contexts and withhold usable continuations on uncertain commit/cleanup. Full new runtime business effects/witness/outcome producer is not implemented |
| Writer separation | Legacy `writer_boundary` requires its own protected claim/EXECUTING context. Metadata owner permits only its exact marker, not family business DML. Lifetime change cannot bridge this |

Claims of protection here are limited to actual code. G1, its governance bridge,
producer, atomic enforcer, witness producer and completed business-execution
protocol are not present simply because their contracts describe requirements.

## 5. Measurement method and restrictions

Ran one read-only diagnostic under a parent `subprocess.run(..., timeout=10)`.
It loaded only the two saved JSON timing reports, computed their SHA256, checked
stage data and calculated non-overlapping authority-prefix/headroom figures.
It completed successfully. No fixture, authority, coordinator, target operation,
Z18/T test or database was run by R1. This is **reanalysis of existing measurements,
not a fresh lifecycle measurement or new performance sample**.

Source artifacts, independently kept as separate runs:

| Artifact | SHA256 |
| --- | --- |
| `.tmp/recognition-z12-deadline-trace.json` | `451f5236cc55d431bd66dc9ea79e0423a552a28a14b6741e71d88cd72cd66d61` |
| `.tmp/recognition-z18-deadline-trace.json` | `6e07220c3b4ab6dae706384d22189de4488ee2c5235a111369f786d15d9374b2` |

The existing full bounded diagnostic is the explicitly prohibited Z18 path in
`test_recognition_runtime_lifecycle_deadline_trace.py`; running it under another
label would not satisfy the instruction. Its later path includes metadata target
writes, and its original deadline truncates completion. Existing narrower profiling
tests measure only selected validation components, not complete remaining work.
Therefore no fresh complete lifecycle sample can be obtained within the permitted
diagnostic path without another explicitly scoped measurement decision. No timeout
extension, suppressed expiry check, synthetic success or renamed Z18 run is used.

## 6. Lifecycle observations and distribution limits

Durations are seconds. Nested stages are shown for diagnosis and **not summed**.

| Stage | Pre-Z15 Z12 report | Post-Z15 Z18 report |
| --- | --- | --- |
| Fixture/pre-authority setup before admission | 87.750 elapsed before admission | 88.831 elapsed before admission; not authority age |
| Issuance / coordinator admission | 62.373, overlapping same span; 97 seconds left | 80.302, overlapping same span; 85 seconds left |
| Z15 schema-inventory preparation | Not this version | 0.005879 nested before authority construction; one hook/object, 12,638 reused inventory reads |
| Issuance final validation | 23.035 nested; 97 left | 35.356 nested; 85 left |
| Attempt creation including its final validation | 94.141, success; 3 left | 84.405, failure; 0 reported left |
| Attempt final validation | 46.976 nested; 3 left | 35.328 nested, failure; 0 reported left |
| Metadata-owner admission | 1.825, failed; exact error not recorded | UNMEASURED |
| Metadata-owner final validation | UNMEASURED | UNMEASURED |
| Target mode transition / INSERT / commit | UNMEASURED | UNMEASURED |
| Reservation reacquisition / postcommit validation | UNMEASURED | UNMEASURED |
| Cleanup/result publication | Failure span 2.633, overlaps metadata admission; 0 left | UNMEASURED |
| Whole diagnostic elapsed | 246.898 | 253.538 |

Z12 stored classification C with only `AdminError`, so do not invent its exact
error or upgrade it into a fully diagnosed expiry result. Post-Z15 records
`AdminError: administrative_session_expired_or_revoked`, interrupted during attempt
final validation, original source lifetime 120, reported remaining budget zero.
Authority expiry is appended to the manager's accumulated auth-expiry checks;
the generic error name alone does not prove the original login session expired.

The post-Z15 monotonic span from authority construction wrapper to attempt failure
is **119.764507 seconds**. Integer UTC accounting can report zero remaining while
this monotonic span is slightly below 120; do not present it as a precise commit
clock or as successful completion. Metadata and all remaining target work are
still unmeasured. Whole diagnostic elapsed includes pre-authority fixture work
and cannot be compared directly to a 120-second authority budget.

No defensible typical duration, p95/p99, slow legitimate complete duration or
worst-case headroom can be calculated. Two different-version partial runs are not
a workload distribution. Local Windows disposable fixtures, instrumentation,
host scheduling, SQLite behavior and fixture size may differ from deployment;
no hosted measurement is made or inferred.

For context, the existing Z8 controlled selected-finalization profile recorded
19.302 seconds reuse-disabled versus 35.339 reuse-enabled, with thread CPU
19.109/35.172 and 12.052 seconds physical-observation work in the latter. That
supports a local CPU/validation contributor, not a complete lifecycle estimate or
a new permission to omit identity checks. Repeated schema/history/manifest work
is substantial; R1 performs no optimization.

## 7. Candidate lifetime comparison

The headroom column is **arithmetic only**: candidate ceiling minus the recorded
119.764507-second post-Z15 partial prefix. It assumes unchanged work and no earlier
credential clipping. It is neither measured completion nor a prediction that
longer-lived runs take the same path or finish. Unmeasured stages have no assigned
zero duration.

| Ceiling | Nominal remaining after observed partial prefix | Maximum authority-age exposure versus 120 | Security/operational assessment |
| --- | --- | --- | --- |
| 120 s | 0.235 s monotonic arithmetic; product reported expired | Baseline | Fails this recorded prefix; no evidence uniquely requires this number |
| 180 s | 60.235 s | +60 s; 1.5x ceiling | May add useful headroom, but unknown metadata/target cost could exhaust it; older intent remains usable longer |
| 300 s | 180.235 s | +180 s; 2.5x ceiling | Plausible candidate for a later justified experiment, not a recommendation supported by a complete workload or by the separate 4d 300-second rule |
| 600 s | 480.235 s | +480 s; 5x ceiling | Largest stale-intent exposure; no evidence it is necessary. Earlier source consent/credentials may clip it substantially |

In the post-Z15 trace the earliest recorded source-step expiry is 519 seconds
after authority issue (00:18:33 to 00:27:12 in the synthetic advancing fixture
clock). Thus a 600-second ceiling would already be clipped by that consent even
before considering any earlier primary/session bound. Never extend those bounds
to obtain the table's nominal headroom.

## 8. Threat/security tradeoff and policy-change implications

Independent exact scope, original-holder provenance, revocation, fresh mutable
state checks and durable one-use fences materially reduce risk from a larger
ceiling. They do not make extra stale-intent time free, guarantee instantaneous
external revocation during commit, prevent all resource exhaustion, or solve a
compromised runtime. Conversely, retaining 120 despite repeated legitimate expiry
can make the feature unusable without adding a demonstrated threat benefit.

Changing only a constant would be incorrect: the current policy identifier,
canonical authority validation, SQL guards/CHECKs, source reconstruction, attempt/
metadata/witness deadlines, migration/history compatibility, original consent and
tests must remain coherent. Old authorities must retain original expiry and
meaning; no in-place renewal or retroactive policy lookup. A longer ceiling, if
later justified, requires an explicit separately approved policy/version and
compatibility decision, not G1 governance adoption or an operational workaround.

## 9. Recommendation D and G-series disposition

**D - INSUFFICIENT EVIDENCE.** Do not select A/C solely because the current code
and defensive contracts fixed 120. Do not select B with a specific new number
solely because one truncated prefix took about 120 seconds. Bounded lifetime is
justified as a freshness/exposure control; numerical adequacy remains unestablished.

The existing implementation remains unchanged as required by this assessment;
that is not a renewed finding that 120 is intrinsically mandatory. No G1 adoption,
producer, enforcer or governance owner implementation follows from R1.

**G-series disposition: unresolved.** If expiry alone caused the abandoned path's
liveness problem, a justified larger bound might remove the reason for some
replacement composition work. It would not implement the absent target writer,
effect/witness or recovery boundaries, nor prove G1 necessary. Assess those needs
against the actual intended feature separately rather than continuing the G-series
automatically or claiming it is already unnecessary.

## 10. Next evidence boundary and validation

The next boundary, if separately authorized, is an explicit measurement/threat
decision: define an acceptable intent/exposure age and representative workload,
then authorize a bounded diagnostic that can observe the complete permitted path
without fabricating authority or silently changing product expiry. Current R1
constraints do not authorize that experiment, a lifetime change, redesign or more
micro-optimization. No numeric recommendation is committed in advance of it.

Validation: the read-only artifact diagnostic completed under its external
10-second bound; document whitespace/local links and `git diff --check`. No pytest,
new lifecycle run, Z18, T, broad suite or production/hosted validation. Only this
document is added; no code, schema, migration, permissions, database writes,
deployment keys, commit or push.

PRODUCTION AUTHORIZATION: BLOCKED

PRODUCTION EXECUTION: BLOCKED

PRODUCTION ACTIVATION: BLOCKED
