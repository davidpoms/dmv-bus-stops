# 4e-20-Z5: runtime admission lifetime contract decision

## Decision and scope

**Retain Option A: the existing 120-second authority ceiling remains unchanged.**
This decision accepts fail-closed rejection when validation cannot finish in time;
it does not accept incomplete validation or establish production readiness.
Z remains BLOCKED. Z5 approves neither Z, target-entry production, writer admission,
execution nor activation. There is no timeout, code, schema, migration or test
change in this slice.

Option B is evaluated below as an unapproved future policy change. No replacement
numeric lifetime is selected. Slowness is evidence of a liveness/deployment
problem, not authorization to increase credential exposure.

## Existing contract and evidence

The relevant implemented boundary is the activation-bound 4e authority, not the
distinct preactivation 4d execution claim. The latter has a separate fixed
300-second lifetime; that value grants no permission to lengthen 4e authority.

The existing 4e producer sets:

```text
expires = min(issued + 120,
              primary expiry, session expiry,
              producer step expiry, producer confirmation expiry)
```

The ceiling is enforced in the lifetime policy identifier, canonical codec,
SQL CHECKs/guards and historical authority validation. Live owner checks also
enforce accumulated authentication deadlines and clock-anomaly rules. Thus 120
seconds is a maximum, not a guaranteed available validation budget. An earlier
credential deadline can make the window shorter.

The clock starts at authority issuance. Issuance finalization/commit/cleanup,
attempt admission/creation/finalization and later permitted uses spend that same
remaining window. Publication, a new reservation, context cleanup or attempt
creation does not start another 120 seconds. Time before issuance is not itself
authority age. Current time must remain strictly less than every applicable
deadline; equality is expired. Validation is not allowed to refresh issue time,
extend expiry, use caller time or ignore clock anomalies.

Sources:

- [4e-11 lifetime and invalidation](recognition-runtime-activation-bound-authority-contract-4e-11.md), section 5;
- [4e-19-R original continuation contract](recognition-runtime-authority-coordinator-continuation-contract-4e-19-R.md);
- [4e-19-T attempt creation and uncertainty](recognition-runtime-execution-attempt-creation-slice-4e-19-T.md);
- [authority codec/storage](../src/review/recognition/runtime_activation_authority_schema.py):
  `LIFETIME`, `validate_authority()`, `definitions()`, `_historical_scope()`;
- [authority producer](../src/review/recognition/runtime_activation_authority_issuance.py):
  `_body()`, `_existing()`, `issue()`;
- [coordinator](../src/review/recognition/runtime_execution_coordinator.py):
  `_Outer.check()`, `_phase()`, `_finish()`, `_persist_attempt()`, `_create_attempt()`.

ZR/Z2/Z3 reduced selected redundant manifest work without changing those rules.
The Z4 bounded G+2 diagnostic nevertheless stopped with final validation incomplete
after 37.53 seconds, including 22.13 seconds inside `_subject_for_owner()`.
Its largest exclusive categories were manifest/schema (17.597 seconds) and history
(15.101 seconds). Authentication, approval/proposal/ACK, physical identity,
activation, emergency stop, dependencies and readiness remained required checks.

The diagnostic stopped at its 240-second overall bound, with approximately 9.6
seconds estimated remaining on the issued authority. It did not demonstrate expiry,
completion of the metadata path, or an irreducible lower bound for every component.
Instrumentation and host load affect elapsed time. Neither these partial results
nor a single successful timing run establishes a completion guarantee.

## Option A: retain 120 seconds

All required fresh validation and each permitted authority use must fit inside
the actual remaining lifetime. The deadline bounds permission; it is not a
performance target whose enforcement can be deferred until work completes.
If required validation cannot finish before expiry, the operation must fail
closed. No skipped check, grace interval, renewed token, retry loop or delayed
expiry check can substitute for successful validation within the live window.

**Can the current system safely guarantee completion of required fresh validation
within the existing 120-second lifetime? No: the available evidence does not
establish that guarantee.** There is no demonstrated worst-case bound for the
complete G+2 coordinator/metadata path under scheduling, I/O and contention.
Even a typical-time improvement cannot guarantee completion under arbitrary
process suspension. This is a completion/liveness limitation; expiry must still
deny authority safely. Retaining the policy does not certify Z or deployment.

When the window is insufficient:

1. Reject use and publish no usable capability/result from the failed phase.
   Failed/uncertain original owners are poisoned; their registrations cannot be
   recreated from durable JSON, process memory or a new request.
2. Roll back uncommitted phase writes through the existing manager while preserving
   reservation ordering. Do not promise that earlier committed issuance or a
   commit with an uncertain outcome was rolled back.
3. If commit, cleanup or publication is uncertain, stop and inspect exact durable
   history through existing read-only mechanisms. Historical presence or absence
   is not a live continuation or retry permission. Preserve immutable records,
   uniqueness and any recovery/incomplete-state fence.
4. Do not automatically replay, adopt, complete, remove or replace authority,
   attempt or target-entry records. Z5 defines no recovery procedure.

A caller has **no unconditional right to restart the same operation**. Existing
authority uniqueness covers operation and writer-manifest identity; an expired
authority remains a historical exclusion. A prior attempt can independently block
another coordinator. The original one-use continuation remains spent after a
failed attempt, even if that phase's INSERTs were rolled back. Changing only an ID,
reason, process, approval or activation cannot be used to renew the same authority.

A caller may deliberately request a genuinely new operation only through the
existing proposal/ACK/approval and fresh owner-consent path, and only if every
current exclusion and production gate permits it. Z5 grants no new entry point or
exception. A new identifier cannot evade a writer-manifest conflict, uncertain
prior state or an incomplete-attempt fence. Fresh authentication or consent alone
does not retire those records. If a retirement/recovery contract is needed but
absent, the caller remains blocked.

This distinction prevents retry from becoming automatic recovery: there is no
replay of the failed continuation, no inference of safe rollback from silence,
no automatic promotion of historical state and no restored authority after restart.
Z's missing complete validation remains a blocker under this decision.

## Option B: change the lifetime — not approved or implemented

A future proposal must pass a separate security/contract review before any numeric
change. At minimum that review must decide:

| Review area | Required decision/evidence |
| --- | --- |
| Security rationale | Explain why a larger exposure window is acceptable, beyond making a slow test pass; distinguish permission lifetime from request/SQLite timeouts. |
| Threat model | Assess longer possession of live authority in a trusted-host/admin system, stale consent, suspended workers and delayed revocation observation. Trusted administrators do not make a stale capability current. |
| Maximum lifetime | Select and justify an explicit bounded maximum. No larger number is approved here. It must not be inferred from session duration, 4d's 300 seconds, caller preference or measured average runtime. |
| Authentication freshness | Retain current primary/session/MFA/epoch, recent-authentication, step-up and one-use confirmation semantics. Review every earliest-expiry constraint and paired-clock anomaly rule. Longer authority must not silently lengthen any credential or ceremony deadline. |
| Activation/authority exposure | Preserve exact activation incarnation, generation, profile, installation, owner, operation, approval and dependency scope. Recheck activation, emergency stop and physical identity at the required boundaries; do not revive preactivation or expired authority. |
| Concurrency | Review lock/reservation duration, contention, single-winner uniqueness, manager-owned commit/rollback, starvation and commit/cleanup uncertainty. A longer validity window must not introduce retries or adoption. |
| Existing contracts | The implemented 4e policy explicitly caps authority at 120 seconds. 4e-11 requires a reviewed new policy version if work cannot fit; 4e-19-R forbids a new TTL/grace period or renewal. These do not already authorize a longer lifetime. 4d's policy is a separate lineage. |
| Versioning/storage | Identify all affected policy identifiers, codecs, hardcoded SQL limits, historical readers, issuance/admission guards and frozen manifest/migration contracts. Review compatibility and any explicit migration needed. Historical 120-second records must retain their original interpretation. No migration framework or schema change is authorized by Z5. |
| Release approval | Require a new explicit lifetime-policy approval gate, followed by separately reviewed implementation and validation. That approval is distinct from operator consent for an operation and from production activation. |

Required future regression coverage includes exact expiry equality and earlier
credential bounds; no renewal; malformed/canonical timestamps; rollback, stalled
and jumping clocks; stale/revoked authentication and MFA epochs; activation,
generation/profile/installation/owner changes; emergency stop; changed approvals,
ACKs, dependencies and physical/schema identity; concurrent/duplicate attempts;
reservation ordering; DELETE/WAL behavior; process/thread/context lifetime;
commit/cleanup/publication uncertainty; restart non-adoption; immutable history;
old/new policy compatibility and migration rollback where applicable; and unchanged
writer, readiness, execution and activation fences. Rehearsal must cover the
complete required path under contention and representative scheduling/I/O, rather
than only its fastest run. None of this coverage is run or implemented in Z5.

## C-class components: future reuse is not authorized

The three attempt/history/audit INSERTs between pre-insert admission and final
validation change the control graph. Identical connection or generation alone
does not make an earlier complete validation current. Within an unchanged phase,
repeated calls suggest potential overlap but do not by themselves establish
identical observations or permission to share a result.

| Component | Could a later reuse contract be safe? | What remains unresolved |
| --- | --- | --- |
| Manifest/schema | Potentially, for a separately established exact schema observation. | Define which definitions/projections were independently verified, code/schema authority, ownership scope and invalidation on DDL, migration, attachment, connection/mode/epoch or transaction change. Existing per-call ZR/Z2/Z3 reuse does not authorize cross-reader reuse. |
| History | Potentially, for a complete verified graph with an explicitly bounded scope. | Bind the validated audit head and all covered tables/rows. Define local writes, denial/audit writes, savepoints/rollback and the three creation INSERTs as reviewable invalidation boundaries. A prior graph must not hide appended or malformed history. |
| Claim validation | Potentially, for historical graph integrity only; current eligibility remains separate. | Define coverage of claims, lifecycle, audit linkage, binding/profile/authentication relationships and new rows. Lifecycle or authentication changes and advancing expiry require appropriate fresh checks; a historical digest cannot become execution authority. |
| Runtime profile | Potentially, for immutable durable profile relationships within a proven snapshot. | Specify exact installation/generation/profile binding, enrolled schema, restoration/rebinding and pending-transition fences. Actual runtime physical identity, owner/authentication state and time must not be silently inherited from a historical profile observation. |
| Control validation | Potentially, for a precisely defined validation result, not a generic checked flag. | Separate schema integrity from row/history validity and manager ownership. Define mutation and reservation/connection/epoch/phase invalidation, including guarded adapters and denial paths. The present checked handle is not a reusable proof for every later reader. |

Each would introduce a **new security semantic requiring a future explicit
contract**, if it carries validation authority beyond the currently approved
single-call reuse. Z5 does not invent its type, API, invalidation mechanism or
fallback policy. That review must establish process/thread/connection/reservation,
transaction/phase, authentication, generation/profile/activation and mutation
conditions, and prove fail-closed invalidation before implementation. No such
contract is approved merely by listing these review requirements.

## Security conclusion and next boundary

Retain the current 120-second ceiling and all earlier expiry constraints. Reject
when required fresh validation cannot complete. The system's complete validation
path is not shown to fit; Z remains BLOCKED, not implicitly approved by this policy
decision. A longer lifetime requires the separate Option B approval gate. Any
C-class observation reuse requires its own prior security contract. Neither is
authorized as the next automatic implementation step.

This is a completed conservative policy decision, not resolution of Z's runtime
blocker. It grants no hosted access, migration, production authorization, execution
or activation. Validation for this documentation-only slice is `git diff --check`
only; no pytest, Z or broad suite is run. No commit or push.

PRODUCTION AUTHORIZATION: BLOCKED

PRODUCTION EXECUTION: BLOCKED

PRODUCTION ACTIVATION: BLOCKED
