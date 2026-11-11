# 4e-20-R15 - finalization ownership/write-set security contract

## 1. Baseline, objective and result

[R14](recognition-runtime-security-operational-limitation-decision-4e-20-R14.md)
authorizes design, not implementation, a producer appointment or runtime rights.
The measured v1/120 and test-only v2/300 paths expired before completion. In
[R12](recognition-runtime-security-v2-300-second-lifecycle-feasibility-4e-20-R12.md),
the metadata owner exhausted the 300-second budget before target commit. There
is no complete successful trace and no justification for 600 seconds. Existing
fail-closed behavior remains correct.

**Recommendation C - NEW SECURITY AUTHORITY REQUIRED.** A single original-holder
finalizer is the bounded candidate assessed here, not an available executable
owner. Its grant-right and authenticated producer integration are unresolved.
Cross-database outcome atomicity and complete effect proof also prevent claiming
implementation-design readiness. Stop; no new authority is established by this
document. The final report is blocked because the requested replacement contract
cannot yet be completed, rather than because another timing run is needed.

The design question is whether non-authoritative evidence can be assembled before
a short fresh ceremony in which one entitled owner validates current state and
performs the complete supported business effect. Preparation is never permission.

## 2. Exact candidate finalization owner

The one candidate is the **original-holder transaction-owning finalizer** described
prospectively by [G4](recognition-runtime-original-holder-atomic-enforcer-security-model-4e-20-G4.md).
It is trusted internal code acting only for one exact original source decision,
not the operator, a historical authority row, an arbitrary executor or the current
metadata owner with a widened authorizer.

Required ownership proof is genuine private original issuance provenance after
confirmed commit/cleanup, exact live PID/Thread/context/runtime incarnation,
original authenticated actor and credentials, current manager-owned connections,
transactions and reservation epochs, and the original bounded expiry. Bind the
owner to D = original `authority_id` plus canonical authority-body digest, exact
operation and manifest, target, installation/profile/generation, owner/epochs,
activation and the once-only pending decision. Copied identifiers cannot recreate it.

What permits it to act is **UNRESOLVED**: existing activated authority permits
neither this target action nor implicit delegation merely through possession.
[G2](recognition-runtime-g1-issue-time-policy-action-binding-contract-4e-20-G2.md)
requires prospective policy/action/consent/eligibility provenance. G4's proposed
capability is not an adopted source policy or an appointed producer.
[G17](recognition-runtime-g1-protected-governance-owner-binding-contract-4e-20-G17.md)
still lacks an authenticated exact-action bridge from verified project-owner
governance approval to the protected control transaction. The documentary mandate
is accepted; no new human mandate or extra approver is presumed necessary.

Only the original holder could exercise a prospectively entitled exact action;
no transfer, re-delegation, renewal, retry or replacement session is allowed.
No owner may appoint itself. Uncertain ownership denies all mutation and usable
publication. R15 does not establish an alternative permission source to bypass G17.

## 3. Complete effect and write-set inventory

Sources are the actual
[`permanent.finalize()`](../src/review/recognition/permanent.py),
[`writer_boundary`](../src/review/recognition/writer_boundary.py),
[Z26](recognition-runtime-replacement-finalization-owner-write-set-decision-4e-20-Z26.md)
and [G5](recognition-runtime-original-holder-atomic-enforcer-implementation-design-4e-20-G5.md).
The family INSERT block is inside the historical writer's authorization and
transaction path. No independently authorized runtime primitive is inferred
from those SQL statements. Legacy authorization and idempotent return semantics
cannot be copied as permission; G4 treats an existing operation as a conflict.

| Effect | Actual source / placement | Atomicity and unresolved requirement |
| --- | --- | --- |
| Consent consumption, canonical authority, AUTHORIZED genesis, two audits | Existing issuer, one control transaction, fixed five mutations | Preserve complete group. New producer/eligibility additions require an explicitly reviewed source protocol. |
| Attempt, ATTEMPT_CREATED history, creation audit | Current original coordinator, later control transaction, fixed three mutations | Not part of current target commit. Cannot omit or fold into issuance silently; replacement placement unresolved. |
| Target-entry metadata | Existing protected metadata owner, separate target transaction | Does not authorize effects. Whether a replacement retains this separate entry or folds its meaning into target action is unresolved; no state is removed for performance. |
| Rule | `recognition_private_rules`: verify identical existing rule or INSERT missing exact rule | Part of complete target family transaction; conflicting definitions reject. |
| Private operation | `recognition_private_operations`: exact canonical manifest, digest, authorization reference and actual time | Target operation/manifest exclusion and actual family attribution; not the runtime operation UUID. |
| First Look effects | `recognition_first_look_claims` for every manifest candidate | Regenerate all qualifiers/competitors and reject existing claims; no partial population. |
| Geography effects | `recognition_geography_scope_identities`, `recognition_geography_snapshots`, `recognition_geography_members`, `recognition_geography_awards`, `recognition_geography_witnesses` | Full scopes/membership/awards/supporting facts; reject previously sealed scope and preserve historical family rules. These family witnesses are distinct from the decision outcome witness. |
| Exact decision-bound witness | Target placement defined by Z30/G4 | Same transaction as all family effects, derived from actual verified complete records and exact D/pending. Complete privileged effect proof remains unresolved under G5. |
| Decision and duplicate/start fence | Z30 control decision/history and linked audit groups | Must be durable before target action; no new D to retry an excluded operation/manifest. Not atomic with separate target commit. |
| Control outcome/journal audit | Z30 later factual outcome group | Requires validated target evidence or positive no-commit evidence; never permission. Cannot share target atomicity under current model. |
| Reservations/modes/epochs and local publication | Manager-owned live state | Not durable rows or an atomic business commit; resource changes invalidate views and require fresh validation. |

This is a complete inventory of established categories, not a new table/field
definition or proof that the replacement write set is executable. Capture,
Explorer, discrepancy/correction paths, arbitrary SQL, legacy claims/EXECUTING,
execution seals, readiness receipts and activation are excluded. Business effect
coverage and any replacement of existing attempt/entry records must be resolved
explicitly before a minimum allowed-write proof can be declared complete.

## 4. Maximum preparation payload

No new serialized payload or field set is authorized. The maximum *currently
approved reusable observation* remains Z15's opaque same-issuance schema inventory
under exact Z7 continuity. Other material may be collected as candidate evidence,
but has no trusted reusable predicate and cannot cross a new phase as authority.

| Candidate content | Source / purpose | Integrity binding | Freshness / authoritative use |
| --- | --- | --- | --- |
| Schema inventory | Existing Z15/Z7 observation, avoid repeated inventory construction | Exact registered original issuance context, resource/continuity rules | Inventory only; no migration validity or cross-phase reuse. |
| Operation reference, frozen private manifest, family/rule/inputs/evaluation/population | Existing proposal/envelope/preparation and historical manifest | Exact canonical bytes/digests resolved against current authoritative sources | Candidate action description, not permission; regenerate `_prepare` and compare complete manifest under target reservation. |
| Proposal/ACK/approval references | Existing canonical durable records | Exact operation, full scope and canonical digest relationship | Lookup hints only; current authoritative pairing and effective approval independently revalidated. |
| Source identity D | Only an actually confirmed original authority | Original canonical authority bytes/digest, genesis and audit provenance | Cannot exist as authority before issuance or be reconstructed from preparation; IDs alone are non-authoritative. |
| Dependencies, readiness, activation, target/physical scope snapshots | Existing authoritative readers | Existing exact source bindings | Advisory comparison data only; no reusable clear/ready/authenticated result. Fresh finalization reads required. |
| Migration/history/claim/control observations | Existing current readers | Current graph, audit head and binding scope | Not reusable authorization; relationship and mutation validation remains fresh. |
| Witness/outcome | Actual effects, exact D and pending record | Derived and verified after effects inside target transaction | Future witness bytes cannot be prescribed during preparation; no prepared success or completion evidence. |

Every candidate must resolve authoritative full content, not merely agree with a
caller digest. No bearer token, SQL handle, adopted handoff or caller-selected
target is exposed. Whether any additional candidate evidence can cross a proposed
new phase is unresolved; this table does not extend Z15 continuity permissions.

## 5. Fresh-validation boundary

The entitled owner would have to perform all required checks immediately before
mutation under actual manager-owned control/target reservations and again at any
required invalidating transition. A new owner adapter must be explicitly reviewed;
existing kernels cannot be invoked with forged existing context types.

| Check | Why current / preparation limit | Finalization requirement |
| --- | --- | --- |
| Authority, policy/version, original holder | Expiry, scope and prospective eligibility cannot arise from evidence | Exact source graph, original grant-right/provenance, closed policy mapping, unexpired original scope; unknown policy denies. |
| Consent and credential expiry | Consent/revocation/time can change; original deadlines must clip authority | Original exact consent, current primary/session/auth/MFA epochs, revocation and all original deadlines; no renewal. |
| Target identity and ownership | Physical identity can change independently of database reservation | Actual current paths/device/inode/schema/fingerprint, owner, installation/profile/generation and activation incarnation. |
| Duplicate and decision state | Another action or uncertain prior commit can exclude execution | Exact D/pending/head, permanent operation/manifest fences, no existing effect/witness conflict; spend once. |
| Concurrency/reservation | Connections, transaction, epoch and mode may change | Genuine registered owner, current resources/epochs, no gap between final admission and permitted action; reacquisition revalidates. |
| Source/control/history/claims/migrations | Graph changes invalidate earlier observations | Current full integrity, audit lineage, exact expected prior writes and exclusions; no cached graph allowance. |
| Target family state | Qualifiers, competitors, scopes/membership or claims can change | Regenerate complete historical manifest, validate every existing precondition and exact allowed-effect proof inside transaction. |
| Approval/proposal/ACK, activation, stop, dependencies/readiness | All are current eligibility conditions | Exact authoritative current readers and comparisons, no prepared allow decision. |
| Commit and result | Time or ownership may fail after effects are staged | Preserve required final deadline/identity checks and post-commit inspection; publish nothing usable on uncertainty. |

These obligations define requirements, not an assertion that a small fresh
ceremony has been achieved. No check is moved outside its current required
boundary, and neither 120 nor 300 seconds is claimed sufficient.

## 6. Atomicity and decision identity

The request's decision-identity reference to "R30" is resolved to the inspected
[Z30 outcome-journal contract](recognition-runtime-decision-bound-outcome-journal-contract-4e-20-Z30.md);
no separate R30 artifact was identified. D remains original authority ID plus
exact canonical body digest. Pending/event hashes and witness digests correlate
facts under D, not independent execution decisions. Same ID/different digest is
a hard conflict. No new request UUID may escape duplicate fencing.

One target transaction could contain complete family effects, target-local
duplicate constraints and exact decision-bound witness. It would be owned and
committed only by the entitled finalizer, with no raw transaction controls exposed.
SQLite's ability to commit those rows does not establish that owner's entitlement.

**The full requested control-plus-target set is not atomic under existing
contracts.** Z30 deliberately specifies control decision/start, atomic target
effects/witness, then factual control outcome as separate local transactions.
Original authority/attempt records are earlier control commits. Holding both
reservations does not atomically couple their commits. R15 cannot replace that
protocol with an ATTACH transaction, move control records to target, or declare
missing control outcome to mean rollback. Those would need a separate explicit
security/storage decision, not an implementation convenience.

Accordingly a finalizer cannot yet promise that decision authorization, duplicate
fence, family effects, witness and control outcome all commit together. The exact
unresolved boundary is whether separately committed factual control outcomes with
Z30 uncertainty semantics satisfy the product requirement, or whether a different
authorized storage/ownership model is required. Neither is selected silently here.

## 7. Crash, uncertainty and failure boundaries

| Boundary | Required fail-closed outcome and later inspection |
| --- | --- |
| Before preparation | No candidate output or right exists; ordinary prerequisite failure stops. |
| During preparation | Discard partial evidence; publish no usable preparation on failure. No target effect or authority. |
| Between preparation and finalization | Expired/changed scope or uncertain ownership rejects. Evidence cannot be promoted or adopted. |
| During fresh validation / before transaction | Reject without business effects; existing committed source/control facts are not erased or reused as a retry credential. |
| During target transaction | Known uncommitted work rolls back completely, including family effects and witness. Rollback/connection uncertainty is unknown, not positive no-commit evidence. |
| Timeout | Deny at required expiry checks, no publication. Process timeout alone says nothing about durable commit. |
| After target commit, before control outcome | Exact target witness/effect inspection may establish target fact; control remains pending/uncertain. No re-execution to fill the gap. |
| After commit, before response / lost response | Return no inferred executable success. Only read-only inspection of D, witness, full effects and control correlation can establish recorded outcome. |
| Duplicate retry | Reject mutation, including known failure, lost response and uncertain commit. Historical lookup supplies data only. |
| Result-publication/cleanup failure | Publish no usable owner/capability; committed records remain historical. Uncertain cleanup does not restore the spent right. |

Later inspection must validate exact source D/digest, full journal/audit chain,
pending reference, target identity, actual complete effects and the witness in a
committed snapshot. Missing witness/control rows alone do not prove no commit.
Contradiction or unavailable evidence stays blocked. Recovery must never create
another mutation right; separately authenticated factual recording remains distinct
and is not implemented or authorized here.

## 8. Options A-D

| Option | Preserved properties | New authority / write-set feasibility | Crash / concurrency | Unresolved assumptions |
| --- | --- | --- | --- | --- |
| A - retain current owners/write sets | Existing freshness, original continuation, exact mutations and fail-closed expiry | No new rights, but metadata owner cannot perform family business action; measured composition does not complete | Existing ordered transactions, exclusions and poisoned-owner rules | Does not supply desired final business transaction or measured viability. |
| B - original-holder finalization owner | Could retain exact original-holder scope, single-use, no transfer/delegation/renewal | Prospective G2 entitlement, protected source producer and complete-effect proof required; target group possible conceptually, whole control/target atomicity unresolved | Must retain G4/G5 no-retry and Z30 uncertainty/reservation rules | Grant-right, authenticated governance bridge, write-set proof and changed owner placement not established. |
| C - explicitly governed transaction-owning executor | Could enforce fixed action and private resources if expressly entitled | No existing independent executor permission; a different process/operator cannot inherit original-holder rights | New handoff, concurrency and crash protocol would be required | Mandate is not executor permission; transfer prohibition prevents assuming this is equivalent to B. |
| D - other repository owner (legacy writer/local execution or read-only owner) | Existing narrow contracts remain valid only in their scopes | Legacy writer requires its actual legacy authorization/claim; read-only/metadata owners cannot be promoted | Original legacy behavior must remain unchanged | Synthetic EXECUTING, fabricated claims, widened authorizers or observer-to-writer promotion are prohibited. No supported replacement found. |

## 9. Recommendation, G-series and exact boundary

**C - NEW SECURITY AUTHORITY REQUIRED.** Existing contract is not sufficient (A);
owner entitlement, complete write proof and atomicity are not ready for an
implementation-design slice (B). This is more specific than unexplained timing
uncertainty (D): inspected authority contracts identify a missing enforceable
original-holder exact-action permission path.

Stop here. The required governance/security decision is whether and how verified
project-owner exact-action approval is authenticated and bound to a protected
prospective adoption/appointment/source producer, thereby entitling only the
original holder to the exact action under G2. G17's accepted mandate must not be
mistaken for this executable approval bridge. Existing authorities gain no new
rights, and G1's v1/120-bound descriptor is not silently extended by v2 support.

Separately, the decision must explicitly accept or reject Z30's split outcome
protocol for the requested atomicity requirement; a permission grant alone cannot
solve cross-database atomicity. G5's complete effect proof remains required even
after entitlement is resolved. No automatic G-series continuation, new performance
slice, producer implementation or replacement-model design is authorized here.
There is no next implementation boundary until these decisions are separately
authorized and resolved. Feasibility remains unmeasured.

## 10. Validation and production blocks

Only this document is added. Read-only inspection of R12/R14, Z26/Z30, G2/G4/G5,
G15/G16/G17 and actual family writer, writer boundary and metadata ownership.
Document whitespace/local-link checks and `git diff --check` passed. No pytest,
lifecycle, Z18, T or broad suite; no code, schema, migration, policy, target,
permissions, producer appointment or authority issuance changes. No production/
hosted resources, deployment key reads, commit or push.

PRODUCTION AUTHORIZATION: BLOCKED

PRODUCTION EXECUTION: BLOCKED

PRODUCTION ACTIVATION: BLOCKED
