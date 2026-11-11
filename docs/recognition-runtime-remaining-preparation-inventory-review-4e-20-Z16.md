# 4e-20-Z16: remaining pre-authority preparation inventory review

## 1. Z15 result and review decision

**No additional issuance observation is authorized to move into preparation under
the existing contracts.** Retain Z15's original-issuance-phase schema inventory
only. This completes the inventory review; it does not approve another preparation
implementation, a lifetime change or a deployable runtime lifecycle.

**Schema-inventory reuse does not authorize reuse of any other observation.**
In particular, it establishes no migration validity, profile eligibility, claim
disposition, authentication, readiness or admission result.

[Z14, including its Z15-C clarification](recognition-runtime-preauthority-preparation-late-issuance-contract-4e-20-Z14.md)
defines the narrow scope. Z15 implements it in
[`runtime_issuance_schema_inventory.py`](../src/review/recognition/runtime_issuance_schema_inventory.py).
`_mint()` runs after the private issuer's successful fresh evaluation and consent
lookup, before `_persist()`. Eligible finalized G+2 scopes obtain an opaque
preparation; other supported scopes retain full fresh readers. `_final_validation()`
proves the exact five writes and enables only inventory lookup reuse during the
original finalization. Original owner/connection/transaction/epoch, scope, consent
binding, code identity, physical observations and mutation accounting remain
checked. Failure, invalidation and phase closure discard the preparation.

The preparation is not returned as authority. The existing issuer still owns its
unchanged authenticated ceremony and fixed mutation protocol. No observation
crosses its commit into attempt creation or metadata admission.

## 2. Current issuance budget after Z15

There is **no post-Z15 issuance-stage timing trace or exclusive component profile**.
The budget cannot be reconstructed from test-suite wall time.

| Budget item | Post-Z15 evidence |
| --- | --- |
| Preparation, before issue-time sampling | **UNMEASURED** as a separate stage |
| Issuance final validation and publication after issue time | **UNMEASURED** |
| Current component-exclusive cost or ranking | **UNMEASURED** |
| Remaining authority lifetime at publication | **UNMEASURED** |
| Attempt and complete metadata lifecycle after Z15 | **UNMEASURED** |
| Authority policy | Still at most 120 seconds from immutable issue time, shortened by existing credential/ceremony deadlines |

Z15's first focused invocation had one pass and one deadline failure. It added
duplicate consent checks per inventory lookup; those additions were removed
without removing the original fresh validators. The isolated integration then
passed in 165.20s, including G+2 fixture preparation. The targeted regression group
passed five tests and seven subtests in 340.95s. Neither number measures authority
age or establishes a speedup. Do not compare them as a before/after benchmark.

[Z13's Z12 baseline](recognition-runtime-authority-budget-architecture-review-4e-20-Z13.md)
remains historical: issuance publication left 97s, attempt creation left 3s, and
metadata admission reached expiry before mode transition or target-entry INSERT.
It is not a post-Z15 budget. This review makes no new timing measurements and
does not rerun Z12. Full lifecycle feasibility remains unestablished after Z15.

## 3. Remaining issuance work: actual sources

[`runtime_execution_coordinator._evaluate()`](../src/review/recognition/runtime_execution_coordinator.py)
calls shared admission `_collect()`, then the issuer's `_subject_for_owner()` and
current scope/time validation. `_finish_reserved()` repeats current evaluation,
calls `_final_mutations()`, independently checks current scope/MFA, target
query-only/zero-change state and time, then commits control while target is held.

[`runtime_activation_authority_issuance._subject_for_owner()`](../src/review/recognition/runtime_activation_authority_issuance.py)
performs current session validation, approval/proposal/ACK reads, claim/block
exclusion, dependency recheck, frozen-event integrity, emergency stop, complete
history/profile validation, claim disposition, protected readiness, current
activation, runtime target and actual physical/schema observations. It constructs
the exact consent subject and rechecks owner scope/deadlines.

These are repeated or population-dependent paths with established historical
cost concerns. Their individual remaining cost **after Z15 is unmeasured**;
source inspection alone does not justify ranking them by elapsed cost:

- [`runtime_validation._history()`](../src/review/recognition/runtime_validation.py)
  invokes complete control validation, audit-head integrity and canonical
  binding/profile/challenge/enrollment relationships.
- [`administration_schema.check_control()`](../src/review/recognition/administration_schema.py)
  retains all applicable profile, claim, authority, attempt and transition row
  validators. Only its schema inventory source can use Z15.
- [`runtime_enrollment_transition_schema.historical_manifest()`](../src/review/recognition/runtime_enrollment_transition_schema.py)
  and the attempt/authority manifest-transition readers still validate migration
  audit cardinality, bodies/digests, predecessor ordering and binding scope.
- [`local_readiness._assess_coordinator()` / `_assess_inventory()` / `_runtime_inventory()`](../src/review/recognition/local_readiness.py)
  perform current owner/MFA, protected key availability, activation, stop,
  rehearsal/backup prerequisites, pending operation and recovery inventory. Runtime
  inventory rereads approval/ACK/dependencies and regenerates the frozen manifest.
- [`runtime_admission_validation._collect()`](../src/review/recognition/runtime_admission_validation.py)
  independently regenerates the whole-population manifest with `permanent._prepare()`
  and compares it with the frozen operation. This is read-only validation, not a
  business mutation primitive to be invoked by preparation.
- [`runtime_claim_disposition._inspect_reserved()`](../src/review/recognition/runtime_claim_disposition.py)
  relies on complete history validation and checks current claim scope, latest
  lifecycle and expiry/disposition against a fresh clock.
- Issuance `_body()` reads actual deadlines, samples issue time and validates the
  complete authority body. `_final_mutations()` verifies fresh consent, protected
  state, the exact new graph and audit suffix, full control validity and authority
  codec. Z15 adds its own inventory-specific ownership and exact-write proof;
  that proof is not permission to omit the manager's existing final checks.

## 4. Predicate-by-predicate matrix

"NO" prohibits moving the current authoritative check. "UNRESOLVED" likewise
means **DO NOT MOVE THIS OBSERVATION**, not provisional permission.

| Candidate | Preparation allowed? | Must remain fresh? | Existing contract | Reason |
| --- | --- | --- | --- | --- |
| Control schema inventory: object names/stored SQL and approved projections | YES, already implemented by Z15; no new scope | Eligibility/physical checks and exact-write/boundary proof remain fresh; repeated inventory enumeration alone may be avoided | Z14/Z15-C and Z15 implementation | Original issuance phase only; contains no row/migration decision |
| Migration definitions | Only as existing schema inventory | YES for every migration relationship use | Z15-C matrix | SQL text or its projection digest does not establish installation provenance |
| Migration rows/relationships | NO | YES | Z15-C; existing manifest-transition readers | Audits, predecessor order, binding scope and current transition/profile continuity are explicitly excluded |
| Immutable profile/challenge/enrollment subrelationships | UNRESOLVED for issuance preparation | YES in issuance today | Z6 P is attempt-local; Z14 excludes issuance-phase P | Unchanged historical rows do not supply an approved issuance observation or its invalidation/coverage contract |
| Current profile/generation/install/owner selection | NO | YES | Runtime validation, G+2 enrollment and Z14/Z15-C | Historical integrity cannot prove the latest eligible scope or absence of pending transition |
| Claim-local historical integrity | UNRESOLVED for issuance preparation | YES in issuance today | Z6 C covers only exact original attempt-phase I1/I2/I3 continuity | Different owner phase and five-write protocol; no existing issuance permission to move claim validation |
| Current claim disposition, operation/manifest exclusion and execution blocks | NO | YES | Claim disposition, original issuance and Z5 exclusion policy | Lifecycle, expiry, uniqueness and global relationships are current-state predicates |
| Approval/proposal/ACK | NO | YES | 4b/4c readers, shared admission, Z14 | Exact durable pairing plus current approval validity/invalidation and authenticated scope remain necessary |
| Authentication, owner and auth/MFA epochs | NO | YES | 3b kernels, shared runtime view, original coordinator | Revocation, expiry and epoch/owner changes cannot be replaced by earlier success |
| Consent step/confirmation and one-use consumption | NO | YES | Owner-consent and fixed issuer CAS protocol | Artifact binding in preparation is not consent freshness or unused status |
| Activation | NO | YES | Independent activation and activation-bound authority contracts | Current incarnation, suspension and scope must match; no preactivation promotion |
| Emergency stop | NO | YES | Execution journal and admission/issuance kernels | Earlier inactive state cannot authorize later use |
| Live dependencies | NO | YES | Dependency recheck and frozen-event contract | Exact frozen snapshot must still agree with current authoritative dependency state |
| Actual physical identity and target schema | NO | YES | Strict identity kernels; Z10; Z14 | No complete trusted filesystem continuity/invalidation mechanism; Z15's repeated checks remain |
| Complete current control validation | NO | YES | `check_control()`, Z6 V and Z14 | Static inventory does not cover current rows, FKs, graph or authority relationships |
| Complete audit/history result and latest head | NO | YES | `_history()`, `_audit_head()`, Z6 H | Issuance appends audits/authority state; pre-write complete-head predicates become stale |
| Readiness inventory/result | NO | YES | Protected readiness interface and exact owner registration | Composite live owner, key availability, activation, stop, prerequisites, operation and recovery state |
| Whole-population manifest regeneration | NO under current contracts | YES | Shared admission `_collect()` and runtime readiness | Frozen inputs do not establish current population/writer preconditions; no issuance preparation contract for this comparison |
| Protected key availability/MFA configuration check | NO | YES through existing readiness subsystem | Protected readiness and administrative authentication | No prepared key/cipher result may replace the current check or create another authentication mechanism |
| Exact five-write graph/audit/protected-baseline proof | NO, cannot be completed before the writes | YES after mutation | Original `_final_mutations()` and Z14/Z15 proof | It proves what actually happened, not a predicted future mutation set |
| Authority lifetime/body/genesis validation | NO for the final record | YES after real CAS, issue-time sampling and row construction | Existing authority codecs and issuer ordering | Final UUID/time/expiry/audit relationships must describe the actual original issuance |
| Ownership/reservation/connection/epoch checks | NO reusable allow decision | YES at existing boundaries | Coordinator/transaction owners and Z14 | A preparation token cannot own transactions or survive replacement/commit/phase closure |
| Canonicalization, digesting and object construction | No additional prepared observation authorized | Existing calls remain; no new memoization | Existing codecs and Z14's exact static scope only | Pure computation is not permission to reuse an operation/authority-dependent result; no cost or predicate mapping justifies another move |
| Any unspecified issuance predicate | NO | YES | Existing reader contract | No implicit expansion of preparation coverage |

Existing ZR/Z2/Z3 same-call reuse remains exactly as implemented. A local reader
projection or verified digest reused within one unchanged call is not new
pre-authority evidence and cannot be promoted into a separate observation.

## 5. Explicitly safe preparation: seven required properties

The sole existing candidate is Z15 schema inventory. Its seven properties are:

1. **Source:** `_mint()` obtains the native control inventory using the existing
   Z7 inventory query after complete fresh issuance evaluation. Other supported
   scopes/callers retain full readers.
2. **Predicate:** exact observed object-name/stored-definition tuples and their
   approved schema projections only. No migration row or relationship is covered.
3. **Change during interval:** schema changes would invalidate the observation;
   the exact five allowed row mutations do not themselves change inventory. This
   is not a guarantee about external physical identity or the complete database.
4. **Binding:** original context/outer/phase, PID/thread, connections, transactions,
   epochs, current operation/runtime target/profile scope, credentials/consent
   bindings and definition/code identity, as checked by Z15.
5. **Invalidation:** extra/unclassified mutations, changed scope/physical/code
   observation, denial/poison, ownership/transaction/epoch/mode loss, expiry,
   commit/cleanup uncertainty or phase exit; exact allowed-write proof is required.
6. **Non-authoritative representation:** opaque `_Preparation` and immutable
   internal facts. Inventory access conveys no SQL handle, authority, attempt,
   writer, executable continuation or adoption mechanism.
7. **Existing permission:** Z14 as narrowed by Z15-C permits this original
   issuance-phase boundary only. Z15 implements it. It is not permission for a
   later attempt or metadata phase.

There is **no additional observation proposed as safe to prepare** in this review.

## 6. Observations that must remain fresh

Every matrix row marked NO continues through its current reader at its current
boundary. Not all predicates are mutable SQL columns: immutable rows may gain new
successors, a global audit head may advance, a clock may expire, or the selected
current binding may change. Current validity is distinct from historical content
integrity. Merely holding both SQLite reservations does not authorize skipping a
contractually required check or establishing external filesystem continuity.

Readiness is not a static policy label: `_assess_inventory()` checks current state
and `_runtime_inventory()` validates each relevant operation. Its owner-bound
evidence accessor also rechecks scope/deadlines. Likewise an already frozen
manifest does not prove that fresh `permanent._prepare()` will still equal it.
No existing contract permits moving that comparison out of its live boundary.

## 7. Unresolved candidates: do not move

### Static runtime-profile subrelationships

The exact source is `_history()` and its profile/challenge/enrollment/transition
readers. A potential historical-only predicate would validate canonical immutable
records and exact predecessor/audit references while excluding current selection,
pending-transition state, physical identity and live authentication/activation.
Some individual rows are immutable, but the complete `_history()` result is not.
Z15-C also explicitly excludes migration binding/transition/profile-continuity
relationships from preparation.

For issuance, the exact permitted subset, source proof, binding to the particular
operation/G+2 profile, five-write invalidation proof and predicate-consumption
interface are **UNRESOLVED**. Non-executable representation alone does not fix
those gaps. Z6 P's original attempt-phase owner is not this issuance owner.
**UNRESOLVED — DO NOT MOVE THIS OBSERVATION.**

### Historical claim-local integrity

The exact sources are `runtime_execution_claim_schema.check_rows()` and its
historical body/history/audit readers; disposition separately depends on current
scope, latest lifecycle and a fresh clock. The potentially static claim-local
portion must exclude current disposition, operation exclusions and global graph
predicates. Z6 C describes continuity only after successful original attempt
pre-insert validation and across its exact three INSERTs.

There is no issuance-phase source/binding/invalidation contract across consent
consumption, authority creation and the two new audit rows. Claim validation also
includes migration relationships that Z15-C leaves fresh. The allowed subset,
coverage proof and safely bounded representation in this phase are **UNRESOLVED**.
**UNRESOLVED — DO NOT MOVE THIS OBSERVATION.**

Any separate proposal for codec output, historical audit prefixes or readiness
subfacts needs the same seven-point analysis. None is supplied or authorized here.
Existing body validators must still validate actual post-CAS fields and records.

## 8. TOCTOU analysis

Preparation remains inside one genuine reserved issuance phase, but the phase
contains five writes. The confirmation-use state, authority/lifecycle population,
global graph/FKs and audit head change. Z15's inventory proof covers none of their
validity. Both new audits and their predecessor linkage remain freshly checked.

Authentication/consent can expire while locked. Physical paths/devices/inodes/
hostname can change independently of SQL reservations. The current protected
key/configuration check is not a static schema fact. The next attempt phase and
metadata phase have different transactions/reservation epochs; a common outer
lineage does not preserve previous observation eligibility. No hash, synthetic
witness, lease or frozen subject closes those intervals by itself.

Fresh checks may incidentally observe unchanged rows many times. Cost and call
count are not authority to change their cadence. No complete trusted invalidation
source or new continuity guarantee is inferred from Z15's inventory object.

## 9. Crash and uncertain-commit implications

There is no new prepared storage or commit. Before issuance, preparation failure
publishes nothing; it cannot become a credential on retry. Confirmation CAS and
the existing five writes remain inside the original manager-owned transaction.
Confirmed control commit with target held and both cleanups remain prerequisites
for promoting the genuine original private continuation.

Uncertain commit/cleanup discards preparation and publishes no usable result.
Existing read-only durable inspection does not grant retry, recovery or adoption.
No restart, new authentication, matching identifiers or alternate ceremony can
restore preparation. Exact-write proof cannot be precomputed before actual writes.
No cross-database atomicity or automatic orphan/uncertain-state promotion is added.

## 10. Exact next boundary

**No additional preparation implementation boundary is authorized by existing
contracts.** Do not implement another observation or rerun the lifecycle on the
strength of this document. The approved limit remains schema inventory only.

The next architectural boundary is a separate decision on the **original
issuance -> committed original continuation -> fresh attempt reservation ->
metadata reservation composition under the fixed 120-second policy**, following
[Z13](recognition-runtime-authority-budget-architecture-review-4e-20-Z13.md) and
[Z5](recognition-runtime-admission-lifetime-contract-4e-20-Z5.md). That review must
either establish a specific new owner/predicate/mutation/invalidation contract
before any further preparation implementation, or retain rejection of this
runtime path. A proposal involving P/C or migration relationships must explicitly
address their current exclusion; this inventory review grants no exception.

Any eventual implementation needs its own approval and unchanged-decision,
invalidation, expiry, scope, uncertainty and non-authority tests. No useful speedup
or completion bound is assumed. A separately authorized timing measurement could
quantify the current Z15 budget, but no such run is performed or implicitly
authorized here. No longer lifetime, automatic retry or blind optimization is
recommended.

Only this document is added. Validation is `git diff --check` plus the established
new-document whitespace/local-link checks. No pytest, Z12, Z, T, broad suite,
implementation, migration, target change, authority/attempt creation, writer or
execution capability, hosted/production access, commit or push occurs.

PRODUCTION AUTHORIZATION: BLOCKED

PRODUCTION EXECUTION: BLOCKED

PRODUCTION ACTIVATION: BLOCKED
