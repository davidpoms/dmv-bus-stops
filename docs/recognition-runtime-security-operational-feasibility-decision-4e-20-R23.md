# 4e-20-R23 - operational feasibility decision

## 1. R22 baseline

[R21-B](recognition-runtime-security-consolidated-finalization-contract-4e-20-R21-B.md)
remains the approved security contract. This decision does not reopen it or
start another security-architecture chain.

[R22](recognition-runtime-security-consolidated-finalization-implementation-4e-20-R22.md)
implemented protected issuer/finalizer integration, durable fencing/outcome
handling and complete-effect/witness mechanisms. Focused validation passed
**32 tests and 37 subtests**. The equivalent immutable SQLite deny-set optimization
removed repeated construction without removing fresh checks or changing policy.
This establishes implemented mechanisms and focused security evidence, not
successful end-to-end execution or production readiness. R22 remains blocked.

Evidence inspected for this decision: R21-B, the R22 report, and the existing
`.tmp/recognition-r22-lifecycle.json` and `.tmp/recognition-r22-parent.json`
artifacts. No new measurement or runtime action was performed.

## 2. Measured validation cost

The following measurements come from the single latest R22 child trace. Nested
spans are not summed, and pre-authority preparation is not charged to an
authority that did not yet exist.

| Boundary | Duration | Authority remaining | Meaning |
| --- | ---: | --- | --- |
| G+2 fixture preparation | 177.9362s | Not issued | Disposable setup, outside the authority window |
| Governance/MFA | 4.5434s | Not issued | Approved disposable issuer setup |
| Fresh original consent | 190.0882s | Not issued | Pre-authority ceremony |
| Source construction | Child elapsed 494.3631s | 120s | Original lifetime begins; no later refresh |
| Issuance final validation | 50.1470s | 120s -> 70s | Includes a 49.6517s live evaluation |
| Attempt admission evaluation | 52.8792s | 69s -> 16s | Current scope/history evaluation |
| Attempt pre-insert evaluation, incomplete | 15.4285s | 16s -> 0s | Expired before graph INSERT |
| Attempt final validation | UNMEASURED | Not reached | Not included in the pre-insert timing |
| Metadata entry and its later checks | UNMEASURED | Not reached | No marker was created in this run |
| Protected finalization/effects/witness/control outcome | UNMEASURED | Not reached | No completion evidence |

Exact failure: **AdminError: administrative_session_expired_or_revoked**, during
`coordinator attempt live evaluation`, with **0 seconds remaining**. Source
timestamps were `2099-01-01T00:24:52Z` and `2099-01-01T00:26:52Z`, exactly
120 seconds. Child elapsed was 613.9560s; that total is not authority age.

The separate partial source-owner profile found current history/scope validation
dominant: `_identity_snapshot` 9.3215s inclusive, including `_history` 8.4308s
and `check_control` 6.2147s. These are nested component measurements, not an
additional complete G+2 lifecycle or a measured lower bound for every stage.
The deny-callback benchmark improved 30,000 identical calls from median
0.2601s to 0.0101s; it did not demonstrate lifecycle viability.

There is a distinct measurement defect: the parent reported `subprocess_timeout`
and returned after 617.6702s against child/parent limits of 540s/545s. It reaped
the naturally exited child (exit 0) but skipped stdout collection after its output
deadline. The recovered, newly written child artifact records actual product
expiry; the parent timeout does not itself prove expiry. This was not a successful
bounded harness run. Its overrun cause remains unresolved.

## 3. Root-cause classification

**B - excessive but potentially optimizable validation cost.**

Repeated current graph/scope evaluation consumes the measured authority window
before metadata entry. Slowness and correct fail-closed expiry do not constitute
a security defect. No concrete product authorization defect was established by
the latest expiry. The harness bound failure is a separate test-infrastructure
defect and must not be hidden or interpreted as a longer product lifetime.

Classification C, fundamental incompatibility, is not established: the evidence
does not prove that all security-equivalent query, serialization and round-trip
improvements have been exhausted or that the measured costs are irreducible.
Classification D is unnecessary for this decision: a successful lifecycle and
remaining-stage timings are missing, but the existing evidence is sufficient to
authorize a constrained attempt to improve the known costly path. It is not
sufficient to promise success, select a longer lifetime or approve deployment.

## 4. Option A - accept the limitation

This option is safe only as acceptance of operational incompleteness: retain
v1/120s and fail-closed expiry, terminate the current implementation/deployment
path, perform no further R22/R23 implementation, and leave production blocked.
It cannot mean deployment of an executable recognition path without a successful
isolated lifecycle. Component test success is insufficient for activation.

**Not selected.** This decision does not accept an unusable measured path as the
finished recognition objective. The observed implementation costs justify one
bounded engineering tranche before accepting permanent operational limitation.

## 5. Option B - one targeted validation-path redesign

**Selected.** Authorize exactly one targeted engineering tranche to reduce the
cost of history/scope validation under R21-B. This authorizes that future scope;
no implementation is performed by this documentation decision.

Permitted investigations are indexing/query-plan improvements, provably redundant
read elimination, non-authoritative preparation, deterministic serialization,
fewer database round trips and equivalent implementation improvements. Any
index/schema proposal remains an explicit, reviewable part of that same tranche;
this decision executes no migration and authorizes no production migration.

Prepared history/scope evidence or a committed snapshot/digest may be used only
where R21-B already permits the exact continuity and rebinding. Binding a digest
to D alone cannot establish freshness. No new cross-phase history cache is
authorized: source/attempt writes invalidate prior complete history observations,
and reservation ownership does not establish external physical-identity
continuity. Z15 schema inventory retains its exact existing scope. An optimization
without a demonstrable existing-contract equivalence must not be implemented.

For each change, the tranche must identify the expensive operation, the retained
fresh predicate, exact decision/operation/target scope, mutation invalidation,
resource/epoch boundaries and focused adversarial evidence. Similar outputs or
high call counts alone do not prove redundancy. Actual family regeneration,
row-delta proof, witness atomicity and committed-target inspection remain intact.

The same tranche must diagnose/correct and prove the test-only harness bound
before relying on another lifecycle measurement. This is measurement integrity
work, not permission to alter a product deadline or start a separate architecture
chain. No lifecycle experiment is authorized in R23 itself.

## 6. Security invariants that cannot change

- Genuine original holder, same D, exact operation, target/family and write set;
  no copied evidence or audit record becomes execution permission.
- Fresh authentication/credential expiry, consent/authorization, issuer policy,
  revocation, activation, profile/generation/installation/owner/MFA scope,
  dependencies/readiness, stop, physical/schema identity and current required
  history/claim/control state at every R21-B boundary.
- Existing control-before-target reservations, connection/transaction/epoch and
  process/thread/lifetime ownership; manager-owned commit/rollback and cleanup.
- Durable single-use issuance/start and duplicate/concurrency exclusions;
  commit-ordered revocation and exact decision-bound evidence.
- Atomic complete target family effects plus witness; separate verified control
  outcome, without any claim of cross-database atomicity.
- No transfer, re-delegation, renewal, stale-history trust, automatic retry,
  adoption or recovery-based reauthorization. Uncertainty publishes no usable
  result and never releases an exclusion.
- No new issuer, producer role, broader runtime permission or delegation
  mechanism. If a genuinely new primitive is required, stop and identify it;
  this decision does not authorize its introduction.

## 7. Lifetime disposition

**v1 remains 120 seconds, ordinary/default. v2 remains 300 seconds,
prospective/test-only.** Existing versioned authorities retain their own policy
and original clipping. No policy is changed or newly adopted. No 600-second
lifetime, extension, refreshed timestamp or second authority ceremony is
authorized. v2 must not be selected merely to force the v1 path to pass.

The engineering question is whether equivalent implementation can satisfy the
existing ceremony within its existing authorized lifetime, not whether a slower
implementation earns a longer authorization window.

## 8. Streamlined deployment path

The requested process is one targeted tranche followed by validation, not one
architecture document or new authority proposal per optimization:

1. R23 records this operational decision and bounded scope.
2. **R24 - targeted validation-path redesign and isolated lifecycle validation**
   implements only that scope, with focused regression and harness-bound proof.
3. After focused validation is stable, one isolated end-to-end lifecycle must
   demonstrate actual metadata entry, authorized finalization, atomic actual
   effects/witness, verified durable outcome and cleanup within the original
   lifetime. No automatic retry or unbounded sampling is authorized.
4. Only a successful isolated lifecycle and security regression evidence permit
   production-readiness review.
5. Production still requires explicit production authorization after that review.

Failure remains fail-closed and is reported within the same engineering tranche;
it does not silently authorize weaker checks, a new lifetime, a replacement
authority or another serial architecture chain. R23 supplies no evidence that
the downstream validation gates have already passed.

## 9. Decision A-D

**B - AUTHORIZE ONE TARGETED VALIDATION-PATH REDESIGN.**

The decision is complete. It authorizes a constrained engineering effort, not a
claim of demonstrated operational feasibility. The project does not proceed to
production with the currently unsuccessful lifecycle, and it does not label
performance alone a security defect or proven fundamental impossibility.

## 10. Exact next boundary

**4e-20-R24 - targeted validation-path redesign and isolated lifecycle validation.**

No R24 work is performed in R23. There is no new security authority, lifetime
change, policy adoption, permission, authority issuance or deployment approval.

## 11. Validation and production blocks

Documentation-only validation: document whitespace/local-link checks and
`git diff --check`. No pytest, lifecycle, schema/code change, database write,
production/hosted access, commit or push.

PRODUCTION AUTHORIZATION: BLOCKED

PRODUCTION EXECUTION: BLOCKED

PRODUCTION ACTIVATION: BLOCKED
