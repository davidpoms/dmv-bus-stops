# 4e-20-R14 - operational-limitation / finalization-contract decision

## 1. R13 baseline

[R13](recognition-runtime-security-architecture-decision-after-300-second-failure-4e-20-R13.md)
found insufficient evidence to justify 600 seconds, establish a shorter ceremony
under existing contracts, or require a replacement authority model. Exactly
120 seconds is not established as a universal security optimum; nevertheless
v1/default remains 120 seconds. Prospective v2/300-second representation does
not authorize its production adoption. G1 remains potentially useful but unproven.

## 2. Exact operational limitation

The existing lifecycle did not complete within the currently tested authority
windows under the measured workload. This is a completion-time limitation of
that composition, not a finding that recognition generally is broken or that
every future implementation must fail.

[R12](recognition-runtime-security-v2-300-second-lifecycle-feasibility-4e-20-R12.md)
provides one valid isolated v2 trace: all 300 authority seconds were exhausted
during metadata-owner final validation, with
`AdminError: administrative_session_expired_or_revoked` and zero budget. The
parent returned in 470.152 seconds without harness timeout and reaped the child.
Parent time includes preparation and must not be treated as authority age.

The disposable metadata INSERT was reached but target commit was not. No
complete lifecycle, usable business result or business execution was demonstrated.
The lifecycle failed closed rather than executing after expiry. No production
execution or activation has been authorized. These results do not prove how
long the unmeasured commit/reacquisition/post-commit path would take.

## 3. Option A - accept limitation

Retaining v1/120, fail-closed expiration, no completed measured lifecycle and
no production activation is a safe operational holding state. It can reasonably
serve an explicitly deferred or inspection-only recognition objective.

As a terminal product outcome it would leave the intended complete runtime
lifecycle unavailable under the measured workload. The ongoing request seeks
a path toward that objective; it does not instruct that completion be abandoned.
Consequently terminal acceptance is not selected here. Safety of the blocked
state does not by itself establish that its limitation meets the product objective.

If A were selected, this architecture chain would terminate: no further lifetime
escalation would be justified, G1 work would stop, and production execution would
remain blocked until a separately approved operational change based on a new
business requirement. This document does not select those terminal consequences.

## 4. Option B - authorize a new finalization contract

**Selected decision: B - AUTHORIZE NEW FINALIZATION OWNERSHIP/WRITE-SET DESIGN.**
Within the decision-making scope of the R14 request, authorize only investigation
and design of the next contract. This is not a claim that repository code already
permits a new owner, a governance mandate granting operational rights, or an
authorization to implement a candidate design.

The exact question for that design is:

> Can the existing recognition operation be divided so that expensive
> non-authoritative preparation occurs before the final fresh authority ceremony,
> while the final owner performs all required fresh validation and the complete
> atomic business-effect/write-set operation?

The design must establish each of the following without presuming an answer:

| Requirement | Required resolution in the design |
| --- | --- |
| Exact owner | Genuine producer identity, original-holder entitlement, process/thread/context lifetime and transaction ownership; reconcile existing owner restrictions explicitly. |
| Exact write set | Enumerate every permitted business, metadata, witness, history and audit effect and every prohibited effect; define the actual atomic group. |
| Fresh validations | Identify exact predicates, their authoritative readers and required timing; preparation cannot substitute for mutable security checks. |
| Authority boundary | Define issue/consumption/expiry placement, original credential clipping, required fresh consent, scope and non-transferability without renewal or implicit delegation. |
| Target/control effects | Distinguish database-local atomicity from cross-database ordering; never claim cross-database atomicity. |
| Duplicate fencing | Prove one logical decision cannot produce duplicate successful effects, including concurrent requests and uncertain outcomes. |
| Concurrency | Define reservations, connection/transaction ownership, epochs, mode transitions and revalidation after changes. |
| Crash behavior | Enumerate durable prefixes and distinguish absent, committed and uncertain effects without recreating authority from historical records. |
| Uncertainty | Publish no usable result on uncertain commit/cleanup; no automatic retry, adoption or recovery-based reauthorization. |
| Rollback | Define what can actually roll back, what is already durable and how rollback failure is reported. |
| Audit lineage | Bind original authority, exact decision/action, target outcome and control evidence without treating correlation as permission. |

[Z26](recognition-runtime-replacement-finalization-owner-write-set-decision-4e-20-Z26.md)
documents the existing separate issuance/attempt/metadata owners and write sets.
R14 permits proposing a new contract that addresses those conflicts; it does
not waive them or authorize combining their writes. An unresolved entitlement,
ownership, fresh-check or commit boundary must remain explicitly unresolved.

## 5. Security invariants

Both the current holding state and any proposed design must preserve:

- A finite, explicitly bounded authority lifetime and immutable issue-time policy.
- Original credential-expiry clipping and fresh consent/authorization wherever required.
- Fail-closed expiration, without restamping, renewal or a second ceremony assumed as a workaround.
- Duplicate exclusion and concurrency protection independent of timeout length.
- Atomic business effects with the exact required evidence; no partial effect adopted as success.
- Crash-stable outcome identity, auditability and explicit uncertain-commit handling.

Authentication, activation, approval/proposal/ACK, emergency stop, dependencies,
physical identity and current history/claim/control/reservation validation must
remain fresh as required. Z15 schema-inventory reuse authorizes no broader reuse.
The design may not silently move an authorization-sensitive observation merely
because it is expensive or called validation rather than mutation.

## 6. No performance assumption

A new finalization contract is **not presumed to solve the runtime problem**.
Its security coherence and operational feasibility must be demonstrated
separately. R14 authorizes neither another measurement nor a claim of sufficient
headroom. No 600-second policy, v3 policy, lifetime extension or optimization is
approved. Current v1/120 and existing v2/300 meanings remain unchanged.

## 7. G1 disposition

**B - G1 DESIGN MAY CONTINUE**, limited to the separately scoped finalization
contract investigation. This does not establish G1 as necessary or select its
replacement model. The design must test whether a simpler sound boundary exists
and must not infer source grant-right, appoint a producer, implement G1, or grant
writer/execution authority. The G-series does not resume automatically as an
implementation chain. Existing governance documentation conveys no runtime right.

## 8. Decision and exact next boundary

**B - AUTHORIZE NEW FINALIZATION OWNERSHIP/WRITE-SET DESIGN.** Do not accept the
completion limitation as the terminal product outcome; continue only with design.
The safe blocked operational state remains in force throughout that work.

The exact next boundary is **4e-20-R15 - finalization ownership/write-set security
contract design**. R15 is design-only and must not implement or alter production
behavior. No R15 design work or runtime action is performed in R14. Implementation,
policy adoption, migration, authority issuance and measurement each require their
own subsequent authorization; this decision supplies none of them.

## 9. Validation and production blocks

Only this document was created. R12/R13 and existing Z26 ownership constraints
were reviewed. Document whitespace/local-link checks and `git diff --check`
passed. No pytest, lifecycle, Z18, T or broad suite was run. No code, schema,
migration, policy, permissions, target behavior, production/hosted access,
authority issuance, producer appointment, commit or push.

PRODUCTION AUTHORIZATION: BLOCKED

PRODUCTION EXECUTION: BLOCKED

PRODUCTION ACTIVATION: BLOCKED
