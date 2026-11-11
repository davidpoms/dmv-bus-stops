# 4e-20-R8: prospective 300-second authority-lifetime policy decision

## 1. R7 baseline and decision scope

[R7](recognition-runtime-security-lifetime-policy-parameterization-assessment-4e-20-R7.md)
recommends immutable versioned bounded lifetime policy. Existing v1 remains 120
seconds, and a larger ceiling needs separate security justification. R8 supplies
that assessment, not policy adoption or implementation.

**Recommendation A - 300 seconds is a defensible prospective v2 maximum**, subject
to all conditions in section 8. This is a bounded exposure/security-design judgment,
not proof the lifecycle completes or a requirement to deploy that lifetime. The
current default/maximum, validators, SQL and permissions stay unchanged.

## 2. Current measured evidence and its limits

[R5](recognition-runtime-security-lifetime-measurement-rerun-4e-20-R5.md) records:

| Run | Child diagnostic elapsed | Outcome | Harness |
| --- | ---: | --- | --- |
| 1 | 250.680923 s | Fail-closed authority expiry in attempt final validation | Normal child exit/reaped, within 365-second parent bound |
| 2 | 248.271822 s | Same fail-closed expiry | Normal child exit/reaped, within parent bound |

Both actual authority intervals were 120 seconds. Metadata-owner, target-entry,
postcommit validation and successful publication were unmeasured. No complete
successful lifecycle distribution exists. R6 could not run a 600-second override
because the exact SQL/codec/historical contract structurally enforced 120.

These observations justify reviewing the restrictive current bound; they do not
prove 300 sufficient, show 300 required, or establish a five-minute worst case.
No new measurement is run or past failed trace relabeled successful.

## 3. Security purpose and incremental exposure

Moving the maximum from 120 to 300 permits original authority/intent to remain
usable **up to 180 seconds longer**, a 2.5x ceiling. It does not imply a 2.5x
attack probability or extend any shorter credential/consent deadline.

| Property | Effect of proposed increase / independent protection |
| --- | --- |
| Freshness | Older original owner intent may remain usable for up to five minutes. This is the direct additional exposure and is not eliminated by fresh database checks |
| Stale consent | A bounded longer intent window, still clipped by original step/confirmation and credentials; no renewal or new confirmation to extend the same authority |
| Credential/live authority compromise | More time may be available to an attacker who also satisfies original-context/credential requirements. This judgment assumes the existing trusted-code/host boundary, not safety against arbitrary compromised runtime code |
| Replay | Original-holder registration, exact subject, consumed confirmation and source/operation uniqueness reject copied/replayed requests independently; expiry is an additional bound, not the replay mechanism |
| Duplicate effects | Existing durable exclusions and separately required effect/witness fences remain mandatory. Neither 120 nor 300 supplies exactly-once behavior by itself |
| Concurrency | Control-first reservations, exact expected state and target transaction ownership serialize participating writers independently of the numeric lifetime |
| Fail-closed expiry | Still strict `issued <= now < expires`, original clocks/anomaly checks and all shorter bounds. No grace, paused clock or skipped final check |
| Crash/uncertain commit | No retry/adoption from historical DATA, no success from timeout, and positive outcome inspection remain required; longer lifetime resolves none of these issues |

Existing exact action/operation/target/profile/generation/owner/epochs/activation,
fresh auth/approval/ACK/dependency/stop/physical/schema/history/claim/control/readiness
checks materially constrain stale mutable state. They do not substitute for
bounded age of intent, undo committed effects or promise instantaneous cancellation
during an irreversible SQLite commit.

## 4. Prospective v2 policy definition

The assessed candidate has **default ceiling 300 seconds and absolute policy
maximum 300 seconds**. It is not a request-controlled duration or an unbounded
environment parameter. The producer derives actual expiry:

```text
expires = min(issued + ceiling_of_authority_policy,
              original primary expiry, original session expiry,
              original producer step expiry, original confirmation expiry)
```

Actual lifetime may therefore be less than 300. Never extend original consent,
credentials or issue time to attain the ceiling. Retain canonical integer UTC,
range/overflow checks, paired monotonic/wall-clock rules and exact historical
reconstruction. Attempt/entry/witness phases inherit the original source deadline.

The future policy must have a distinct immutable version/identifier whose resolved
meaning is exactly 300 seconds; it must never reuse the existing
`recognition-runtime-authority-lifetime-120s-v1` identifier for new semantics.
This assessment creates no new accepted codec constant or active policy record.
Default selection applies only to newly authorized sources after a separately
explicit effective adoption; no current default is changed by R8.

## 5. Historical compatibility and data requirements

Current canonical authority body already binds `lifetime_policy` and original
issue/expiry in its digest; indexed timestamps are checked against that body.
This can distinguish future v2 from v1 conceptually without assuming a new column.
The reader must resolve each authority's own immutable policy, never today's
default or a caller-provided ceiling.

For an old v1 source I, historical expiry remains exactly
`min(I+120, original credential/consent bounds)`. Its body, digest, policy and
expiry never change when the future default becomes 300. Expired/spent v1 cannot
become live, acquire new rights or release any exclusion. Future v2 historical
validation uses its own original policy ceiling and original bounds.

Existing SQL CHECKs, policy-binding trigger, Python canonical validator and
historical reconstruction only admit v1. Safe coexistence therefore requires an
explicit future schema/manifest/reader compatibility design and, where necessary,
reviewed migration. A single constant replacement, expected-schema string rewrite,
CHECK disabling or revalidation of all history against current default is unsafe.
No migration or such change is specified/implemented here. The current model's
closed policy field is a foundation, not existing operational support for v2.

## 6. Security-ceiling assessment

Five minutes is a reasonable finite candidate because the proposed permission
remains exact-operation, original-holder and nonrenewable, with original MFA/
confirmation, credential clipping, current independent validation and permanent
single-use controls. Adding three minutes of intent age is a constrained policy
tradeoff for a locally measured validation workload that repeatedly exhausts two
minutes before reaching later phases. It is not general browser/session authority
for arbitrary actions. Fresh-state security must not be traded away for completion.

No repository evidence identifies a threat threshold uniquely requiring 120;
conversely, there is no measured need to permit 600 or an unlimited configurable
value. A maximum remains necessary. This decision accepts 300 as a defensible
bounded security ceiling for further engineering/measurement, not a mathematically
optimal or minimum workload-fitting value. No stronger smaller numeric maximum
is established by current threat evidence, and no higher maximum is approved.

Risk assumptions must be revisited if the eventual interface broadens actions,
permits transfer, weakens revocation/fresh checks, exposes a bearer execution
credential or extends trust beyond the existing protected runtime. R8 supplies
no authority for those changes.

## 7. Operational margin: two different clocks

Relative to **whole child elapsed time**, a hypothetical 300-second elapsed-time
cutoff is 49.319077 seconds beyond run 1 and 51.728178 seconds beyond run 2:
approximately **49-52 seconds beyond those observed runs**. This is arithmetic
on reported child durations, not remaining authority lifetime.

Both child durations include about 129-132 seconds before actual source construction.
Observed authority age reached its own 120-second expiry during attempt final
validation. Changing that authority ceiling to 300 would nominally add up to
180 seconds at the same authority-age boundary, subject to original credential
clipping and changed future path behavior. It does not merely add 49-52 seconds.

The observed failures were caused by the enforced 120-second authority bound,
not by a child measurement exceeding 300 seconds. **Neither comparison proves
that the complete lifecycle finishes within 300 authority seconds.** Remaining
metadata/target/cleanup stages remain unmeasured, and a longer run may encounter
different failures. No complete-runtime headroom, percentile or worst-case margin
is inferred from truncated prefixes or sums of nested spans.

## 8. Recommendation A and mandatory accompanying conditions

**A - 300 seconds is a defensible prospective v2 maximum**, with all of these
conditions required before any runtime adoption/use:

1. Explicit separately authorized security-policy adoption/effective ordering and
   auditability of the exact immutable v2, default 300 and maximum 300. R8 is a
   decision assessment, not the adoption operation or a runtime permission grant.
2. Closed supported policy-version resolution; unknown, malformed, contradictory,
   unauditable or uncertain policy applicability fails closed. No caller selection
   of arbitrary duration or silent environment override.
3. All v1 rows, original consent, expiry, digests and historical interpretation stay
   unchanged; no retroactive extension, renewed source or older-operation adoption.
4. Consistent issuer, canonical validator, SQL/body/index guards, historical readers,
   manifest/migration and downstream exact deadline handling. Test old/new coexistence
   and rollback explicitly in later authorized engineering.
5. Unchanged clipping by original auth/consent; original-holder, exact scope, fresh
   mutable/physical state, reservation/commit order, clock checks and fail-closed
   expiry remain mandatory at every existing boundary.
6. No weaker duplicate/replay fences, transferable capability, retry/recovery or
   uncertain-commit handling; no writer/readiness/activation authority added merely
   through a longer policy.
7. A bounded test-only v2 lifecycle measurement before any claim of operational
   readiness. One successful run would establish feasibility, not a statistical
   completion guarantee or permission for production deployment.

The conditional acceptability judgment is supported independently of complete
timing proof. B would treat 120 as a demonstrated unique security boundary, which
the record does not establish. C remains true for *operational sufficiency*, but
is not the selected security-policy judgment for this constrained candidate.

## 9. G-series disposition and exact next boundary

**G1 is not automatically required.** The expiry observations alone do not justify
replacement authorization architecture. The next engineering step should be the
**smallest separately authorized implementation supporting immutable versioned
lifetime policy with preserved v1 history and explicit schema/reader compatibility**.
Only after that should a bounded test-only v2 lifecycle measurement be performed.

Neither step is implemented, adopted or executed in R8. Whether a modest increase
makes the original recognition path viable remains unproved; existing unimplemented
writer/effect/outcome boundaries are not created by this policy decision. Do not
continue G1, declare it unnecessary in all respects, or expand lifetime beyond
300 automatically if a later measurement fails.

## 10. Validation and explicit production blocks

Only this document is added. Read-only R5/R7 and authoritative lifetime code review;
document whitespace/local-link checks and `git diff --check`. No lifecycle tests,
pytest, Z18, T, broad suites, production code/schema/validators/migration, active
policy/database/permission/authority changes, G1 implementation, hosted/production
resources, deployment keys, commit or push. Current v1/default remains 120 seconds.

PRODUCTION AUTHORIZATION: BLOCKED

PRODUCTION EXECUTION: BLOCKED

PRODUCTION ACTIVATION: BLOCKED
