# 4e-20-G5: atomic enforcer implementation-design contract

## 1. G4 baseline and result

[G4](recognition-runtime-original-holder-atomic-enforcer-security-model-4e-20-G4.md)
approves a new original-holder-only atomic enforcer **for implementation design**.
It does not approve coding, supply a producer or make old sources eligible.

**Decision B - IMPLEMENTATION DESIGN INCOMPLETE.** The ownership, input, transaction
and failure obligations below can be mapped concretely. Two prerequisites are not
yet exact enough to authorize implementation: the protected producer/permission
and typed audit protocol for prospective G2 policy/consent eligibility, and the
canonical complete actual-effect evidence/verifier plus exact permitted mutation
proof. Sections 8 and 14 identify their limits. This document does not fill them
with a generic privileged callback or silently reuse a legacy receipt contract.

All names introduced as proposed interfaces below are design labels, not existing
functions, callable APIs or permission grants. No new schema or codec is installed.

## 2. Minimum component boundary

Keep one trusted owner, with private validation/storage helpers rather than
independently callable grant, writer and witness factories.

| Component | Responsibility / owner | Inputs | Outputs | Required authority | Durable state / transaction ownership |
| --- | --- | --- | --- | --- | --- |
| Prospective source eligibility reader | Validate complete original P/C/Q/E graph, original source and current policy; private owner helper | Authoritative control graph and original source registration | Immutable exact eligible-source binding or rejection | Read scope only; reader cannot adopt policy or mint eligibility | No writes; owner's reserved control connection |
| Original action owner/enforcer | Own lifetime, irreversible exercise, final admission, fixed effects/witness, commits and cleanup | Genuine original registered continuation; no raw caller scope | Historical result only after confirmed outcomes/cleanup | New G4 exact action permission from eligible source, never existing legacy lease | Manager owns C1/C2/T/C3; private live registry, no durable executable token |
| Family verifier/mutator helper | Regenerate manifest; perform only fixed supported writes; prove exact results | Owner-private target handle and authoritative frozen manifest | Verified actual-effect evidence, no capability | Only owner-internal call within consumed enforcer | No independent open/BEGIN/COMMIT; effects in T |
| Witness/evidence helper | Internally derive unchanged Z31 witness and independently verify committed effects | Exact decision, confirmed pending, actual verified records and bounded clock | Canonical witness row/evidence match or rejection | Inseparable action only; no witness-only public API | One witness INSERT in T; read-only durable inspection afterward |
| Journal/audit helper | Fixed decision/start/outcome groups and source attribution | Owner-private authoritative state, expected head and proven facts | Confirmed historical journal facts | Separately scoped exact control write protocol, not target permission | C1 decision/genesis/audit, C2 pending/audit, C3 outcome/audit |

An outcome-only recovery owner is outside the enforcer. Until its independently
authenticated recording contract exists, unavailable original recording leaves
pending/uncertain state blocked. It cannot be substituted to complete execution.

## 3. Existing integration inventory

Sources below are under `src/review/recognition/`.

| Existing component / integration | Classification | Future integration point and restriction |
| --- | --- | --- |
| `runtime_activation_authority_issuance._body`, `_persist`, `_final_mutations` | Authorization, mutation, audit | Prospective G2 source protocol only; current five-write issuer stays unchanged until an explicitly authorized protocol change. No extra eligibility write hidden in current proof |
| G2 original policy/adoption/consent/eligibility audit prefix | Validation, authorization evidence | Resolve exact P/C/Q/E and source audit sequence; absence/conflict denies. Producer permission/typed protocol remains a prerequisite |
| `runtime_activation_authority_schema.validate_authority` | Read-only validation | Canonical original source and exact closed body; no policy field inserted into old format |
| `runtime_execution_coordinator._promote`, `_continuation_entry`, `_require_outer` | Ownership validation | Pattern for confirmed original private registration, not permission to widen these current contexts or pass off new owner as an old context |
| Coordinator `_phase`, `_finish_reserved` and target-entry owner ownership checks | Reservation/validation | Preserve manager-owned connections, PID/Thread, phases, epochs, control-before-target locks and target held through control commit. No metadata-owner authorizer widening |
| `runtime_scope_validation`, `runtime_validation._history` and actual identity readers | Read-only validation | Fresh enrolled profile/binding/generation/owner/epochs and strict actual physical/schema identity |
| `runtime_admission_validation._collect`, runtime approvals/proposal records | Read-only validation | Existing exact proposal/ACK/approval/manifest and scope kernels; new owner needs an explicit narrow read adapter, not a callback impersonating registered context |
| `runtime_activation_authority_issuance._subject_for_owner` | Read-only validation | Current dispatch accepts only exact existing owner types. Do not invoke with forged state; later explicit owner adapter must preserve every current check and protected view |
| `runtime_activated_owner`, activation/readiness kernels | Read-only validation | Current independent activation incarnation and protected readiness, not a new activation route |
| `execution._stop`, execution blocks, `dependencies.recheck` | Read-only validation | Fresh stop/history/block and dependency results, exact original snapshots |
| Claim disposition, control/history/schema/migration readers | Read-only validation | Full current graph and exclusions, permitting only proved expected journal/effect changes |
| `runtime_decision_outcome_journal_schema` | Read-only codec/inspection; future mutation | Exact inert Z31 definitions and canonical decision/history/witness; no permission from parsed DATA |
| `administration.audit` and audit readers | Audit | Exact typed proposed source/journal audit groups, predecessor/sequence and protected mutation proof; generic append is insufficient |
| `permanent._prepare`, `_verify_operation_records`, integrity readers | Read-only validation; future fixed mutation extraction | Preserve complete historical family semantics; do not call `finalize()` via fabricated legacy EXECUTING/claim |
| `production_receipts._records` | Read-only candidate evidence collector | Collects actual related records; not a runtime receipt/authorization or proof of exact write set by itself |
| `writer_boundary`, legacy execution/receipts | Fence only | Unchanged; reject new enforcer as existing writer capability. No conversion, execution seal or legacy record creation |

Exact new owner adapter registration/authorization and mutation proofs require
review as part of the implementation boundary, not monkeypatching existing type
checks. Existing source code is not changed by this design.

## 4. Immutable enforcer input contract

The sole external input is a **genuine private original-owner continuation** from
confirmed prospective issuance. No caller JSON, authority body, target path,
manifest, session replacement, decision ID or witness digest can construct it.
Credentials remain private to that original owner; hashes are scope evidence,
not bearer credentials. The owner resolves the following immutable binding:

| Binding | Exact authoritative origin |
| --- | --- |
| Authority / decision | Confirmed source canonical bytes/digest and ID; D is that ID/body digest, not a new request UUID |
| G1 policy / action | Exact adopted version/digest, Q/C and original E audit-prefix reference per G2, no retroactive lookup |
| Operation / family effects | Current acknowledged approved operation/event/preparation, exact frozen private manifest bytes/digest, supported rule, full population and candidate set |
| Target / scope | Actual enrolled target/control identity, schema/fingerprint, installation/target UUID, profile/generation/binding/owner/auth/MFA epochs |
| Activation / runtime | Exact original independent activation incarnation and private original runtime/process/Thread/ceremony registration |
| Witness identity | Exact D and sole confirmed pending event plus fixed unchanged Z31 derivation. Actual effect digest/time is derived after effects; caller cannot prescribe future witness bytes |
| Reservation | Actual owner connection identities, active transactions, phase and epochs when grant is created; no serializable lease |
| Deadline | Original issue/expiry, earlier auth/consent bounds and paired monotonic/UTC clock anchor |

Deep canonical values are private immutable observations, not an executable
export. Live resource references stay in the private registry, never in a DATA
codec. Wrong context, cross-thread/process, closed phase, replaced connection,
different decision or mismatched current value rejects instead of rebinding.

## 5. Fresh validation contract

The original trusted owner runs this full set after final reservation acquisition,
immediately before consumption/DML and at final precommit. All rows are checked
while T is active; independent control reads are under the actual control
reservation. Pre-transaction review is non-authoritative. Failure poisons live use
and rolls back known uncommitted T; no usable object/result is published.

| Check | Authoritative source / freshness | Owner / transaction placement |
| --- | --- | --- |
| Original entitlement | Full source/genesis/audit and original P/C/Q/E; current effective policy revocation, no prior exercise | Original owner; reserved control while T active |
| Auth / consent | Original primary/session/runtime-auth, actor/access/revocation/MFA/epochs, exact consent and earliest expiry | Existing authoritative auth kernels via explicit owner adapter; control while T active |
| Profile / binding | `_history` and exact finalized G+2 profile/install/target/generation/owner/epochs | Scope kernel; control and actual target inside T |
| Approval / proposal / ACK | Complete current exact pairing, effective approval/invalidation history and original operation | Approved readers through owner read view; both reservations held |
| Activation | Current independent exact incarnation/sequence/digest; preactivation source cannot be promoted | Existing activated scope kernel; control while T active |
| Stop / blocks | Current authoritative stop/history and operation block, including changed-set-clear scope | Existing stop/block reader; control while T active |
| Dependencies | Frozen snapshot plus fresh graph recheck and full family source regeneration | Existing dependency/report kernels; target inside T |
| Physical identity / schema | Actual hostname/resolved path/device/inode/schema/fingerprint for target/control | Existing strict observers; actual connections inside reserved phase; no continuity cache |
| History / claims / control | Complete current graph, global exclusions, protected state/audit, FKs, schema/migration relationships | Existing kernels; both reservations, exact expected-write-aware proof |
| Readiness | Full current protected assessment, not old issuance readiness digest as allow | Protected readiness kernel through explicit owner view; both reservations |
| Reservation / time | Actual PID/Thread/registry, connections/transactions/query modes/epochs, original clock, all deadlines and no clock anomaly | Manager; every ownership/use boundary including final commit check |

No broad observation reuse is authorized. Z15 schema inventory stays within its
original issuance scope. Expected C1/C2 or business writes must be proved exactly;
they do not exempt all later history/control/claim checks. A fresh reader that
cannot safely classify those changes blocks implementation rather than skipping it.

## 6. Future transaction design

Use the Z32 logical groups, not a widened existing 3a or metadata transaction:

1. Resolve eligible original source and D under genuine reservations; run full
   current checks and all old/new operation/manifest exclusions.
2. C1 atomically inserts exact decision, DECISION_CREATED genesis and linked audit.
   Target reservation remains held through control commit. Confirm commit/cleanup;
   uncertainty stops, without new permission from an inserted row.
3. C2 atomically appends sole TARGET_PENDING and audit conditional on exact C1
   head. Revalidate live authority. Confirm this permanent spend before any grant
   becomes usable. Keep target held through this control commit as required.
4. Before beginning final action, resolve earlier reservation phase. If reacquiring,
   release both in order and reacquire control before target; never hold target
   while waiting for new control writer lock. Freshly validate everything. No
   already-created grant crosses reacquisition; original lifetime continues.
5. In final control reservation plus target T (`BEGIN IMMEDIATE`), bind original
   private enforcer to actual resources. Consume its one use before enabling only
   fixed writes. Revalidate mode transition, ownership and full fresh admission.
6. Inside T regenerate exact private manifest with `_prepare()` semantics. Reject
   any existing/conflicting family operation. Perform only fixed supported family
   writes and supporting rule/operation records. Verify actual whole-family records,
   exact accounting/write set and FKs. Derive/validate/insert one Z31 witness.
7. Perform final live checks and exact post-write proof while reservations remain
   held. Commit T once through manager. Never commit a business-only prefix.
8. Invalidate old views/epochs. Resolve final control reservation before any ordered
   reacquisition; no new control lock while holding target. Establish a committed
   target read snapshot under required control-first reservations and independently
   verify actual witness/effects/source. No reconnect-on-error or second mutation.
9. C3 records factual COMPLETED plus audit conditional on exact current journal
   head and positive durable evidence. Hold required target reservation through
   control commit. Confirm commits and cleanup before historical result publication.

These are separate commits. C1/C2 can survive absent target effects; T can survive
absent C3. Such prefixes remain permanently excluded. They are not co-commits.
Control changes between released phases require full fresh revalidation. If
expiry or another invalidation occurs after T committed, suppress usable result
and retain factual inspection rather than pretending target rollback is possible.

The exact role of each real future connection, authorizer and expected write set
must be represented by the new owner; current contexts cannot masquerade as it.

## 7. Single-use durable fence

The control C1 decision row uses Z31 keys: authority ID, authority body digest,
installation/target/operation and installation/target/private-manifest. C1's
decision/genesis/audit commit makes exclusion durable. C2's ordered sequence-2
pending transition spends the start permanently. Expected predecessor/sequence
plus serialized control ownership prevents two successful starts.

The owner marks the original construction attempt spent before publishing a
usable grant; failed construction does not reset it. Invocation consumes the
private registration before DML, refusing recursion/duplicate calls. A concurrent
caller cannot recover original private ownership from durable C1/C2.

The target witness has the corresponding unique keys and immutable collision
guards, committed in T with effects. Witness collision must roll back the entire
effects transaction. Enforcement of mandatory witness participation, not uniqueness
alone, prevents a writer committing duplicate business effects without a witness.

No fence expires or is released by failure, known rollback, completion, restart,
credential refresh, generation change or restore uncertainty. Preserve BUSY/LOCKED
without loops. A new D for the same excluded operation/manifest remains denied.
Journal definitions are inert today; installation/enrollment is not authorized here.

## 8. Witness producer interface and remaining evidence boundary

Proposed private interface: `produce_for_current_action(owner_state)` resolves all
inputs internally. It accepts no connection, witness/effect digest or replaceable
scope from an application caller. Required private inputs are exact confirmed
decision/pending, original source/audit/action, current manifest and actual verified
rows in T, original deadline and actual bounded record time. Its only permitted
write is the unchanged Z31 witness in the same T as the verified business effects.

Witness fields remain exactly `format`, `decision`, `pending`, `recorded_at_utc`,
`outcome`, `effect_evidence_sha256`. No delegation ID, PID or extra policy field.
Source policy attribution resolves through original eligibility audit. The witness
states precommit intent until durable commit; its timestamp is not an exact commit
clock. Failed verification/encoding/INSERT prohibits commit and rolls back T.

`permanent._verify_operation_records()` and First Look/Geography integrity readers
provide complete existing family semantic checks. `production_receipts._records()`
collects canonical-sorted actual rows across private operations/rules, First Look
claims, Geography snapshots/members/identities/awards/witnesses. This is a potential
input to an exact-effect proof, **not yet a specified G1 effect-evidence format**.

Still unspecified: the exact canonical bytes hashed as effect evidence, how they
bind intended/actual complete accounting and allowed reused support rows, how
unexpected writes/trigger effects outside that selected record map are proved
absent, and how independently committed inspection recomputes the identical proof.
Hashing only that map or the manifest would silently choose a new contract.
Legacy `production_receipts.build()` requires legacy claim/operation/accounting
and seal conventions; it cannot be reused as a runtime receipt by fabricated claim.
No target-specific witness logic or new evidence codec is invented in this slice.

## 9. Journal integration and result publication

Retain exact Z31/Z32 states. Decision creation is permitted only after confirmed
eligible source and fresh original owner admission; pending only after exact C1.
Neither grants execution. Target witness is written only within action T. Control
outcome is recorded only after positive committed target evidence and current
recording permission. COMPLETED is journal outcome, not a legacy execution seal.

Unknown commit/connection/cleanup uses the appropriate existing uncertainty
classification if an authorized recorder can append it. If recording permission
is gone or control commit is unknown, leave pending/uncertain state; do not force
an audit through expired authentication. TARGET_FAILED needs positive original
manager no-commit evidence; absence is insufficient. Terminal states never reopen.

Original-owner result publication requires independently verified committed
witness/effects, confirmed corresponding control outcome/audit, exact source
attribution, intact scope/deadlines, resolved connections/cleanup and destroyed
live enforcer registration. The published result is historical DATA, never a
serializable capability. Lost publication cannot justify re-execution.

## 10. Crash / uncertain-commit matrix

| Point | Required deterministic handling |
| --- | --- |
| Before validation | No new usable action; preserve already confirmed source/fences; no inferred replacement |
| After validation | Earlier allow is not reusable authority; no adoption if original owner is lost |
| During business effect | Known uncommitted rollback removes all fixed writes; unknown connection outcome stays fenced |
| After effect before witness | Commit forbidden; whole rollback when known; no witness repair after a separate effect commit |
| After witness before commit | Both uncommitted; no success from INSERT result or process memory |
| After target commit | Inspect exact durable effects/witness; never mutate again to reproduce a response |
| Before journal outcome | Committed target with pending/uncertain control remains excluded; factual recording only |
| After journal outcome | Verify positive facts and cleanup; publication failure does not restore grant/start |

Uncertain target/control commit is not a retryable exception. Original registry is
poisoned, no usable result is published and durable inspection is required. Missing
witness, elapsed time, process death or a different restored lineage proves neither
no prior commit nor safe re-execution. Indefinite unresolved exclusion is permitted.

## 11. Non-adoption proof obligations

Registry validation must use exact internal type and object membership, actual
original PID and live Thread/context identities, original issuance provenance,
exact D/scope and active ceremony. Caller callbacks cannot certify ownership.
Each use checks actual connection identity, transaction/query mode and reservation
epoch. Public DATA formats contain none of the private registration authority.

Construction/copy/pickle/JSON import cannot create membership. Connection replacement,
epoch change, cross-thread/process/ceremony/decision, expiry, context exit or a
spent invocation permanently rejects. No closure/result containing a usable handle
escapes. Recovery can inspect immutable facts but never repopulate this registry.
This assumes trusted Python/OS code and protected database access, not defense
against arbitrary hostile execution in the trusted interpreter.

## 12. Minimum audit design

Use D and existing journal event/witness digests as correlation anchors; do not
invent an independent reusable invocation credential. The sole confirmed pending
event represents the single action start. G2 source issuance sequence N resolves
E at N-2, original consumption at N-1 and issuance at N, binding original P/C/Q
and authority. C1 audit references exact decision/genesis; C2 audit references
exact decision/pending and original eligibility; C3 audit references exact head,
witness/effect digest and proven target outcome. Normal audit actor/time/predecessor
must remain validated. Full source/effect records need not be duplicated in audit.

The target witness links back to source and pending, not to a permission selected
by the caller. An auditor must resolve all referenced graphs and actual effects;
conflict fails integrity checking instead of selecting the newer domain.

G2 defines conceptual P/C/Q/E but explicitly defers exact adoption/consent producer
and authorizer. Z32 explicitly defers exact typed journal audit action/subject
codecs and protected mutation proof. Current generic `administration.audit()` does
not authorize these writes. Selecting arbitrary labels/bodies here without that
permission contract would not satisfy the requirement for an exact trusted producer.

## 13. Failure / rollback rules

| Failure class | Target | Journal / grant | Recovery / new decision |
| --- | --- | --- | --- |
| Prerequisite failure before confirmed C1 | Roll back any known open transaction, no business DML | No partial C1; no usable grant | Inspection only as needed; no automatic new issuance |
| After C1 but before C2 | No business DML | Permanent decision fence; original failed path cannot be adopted | No new decision for same excluded operation/manifest |
| After C2 / grant construction or admission failure | Roll back known T | Start stays spent even if no grant was published | Positive factual failure recording only; no renewed grant |
| Family/witness/precommit check failure | Whole T rollback, never partial family success | Consumed registration; failure only with positive no-commit evidence | No retry/new D bypass |
| Commit/connection/cleanup uncertainty | Never infer rollback or repeat mutation | Poison live use; pending/uncertain remains excluded | Authoritative factual inspection only |
| Target confirmed, control outcome fails | Cannot roll back confirmed effects | No usable success until recording/cleanup confirmed | Separately permitted factual recording, not reauthorization |
| Postcommit scope/deadline failure | Preserve committed facts | No usable execution result/live capability | No compensation, renewal or adoption inferred |

For an unrelated genuinely different nonconflicting operation, independent future
authorization may be possible under its own gates. This does not release the old
decision's exclusion or authorize replacing its failed ceremony automatically.

## 14. Implementation-ready / blocked / prohibited

### Implementation-ready design elements

- Private original-owner-only input and exact binding/ownership checks in sections
  2-5; no caller-replaceable scope or raw handles.
- Control-first C1/C2/T/C3 ordering, mandatory target-held control commits,
  explicit ordered reacquisition, whole-target atomic effect/witness and fail-closed
  uncertainty rules; no cross-database atomicity assumption.
- Permanent decision/start/witness uniqueness, irreversible live consumption,
  non-adoption and crash behavior; unchanged journal/witness shapes.
- Existing complete family semantic kernels and read-only source integration
  points, with explicit new protected read adapter required for a new owner.

These are ready as design obligations. **No implementation work is authorized by
G4 or this document alone.**

### Requires another security contract

1. **Prospective eligibility and control write protocol:** exact independently
   authorized policy-adoption owner, G1-specific consent producer and typed P/Q/E
   audit subjects; original issuance mutation/authorizer proof; exact C1/C2/C3 audit
   subjects and fixed protected-state mutation proof. Existing activated source
   consent, admin status or generic audit access cannot supply these permissions.
2. **Complete actual-effect evidence and fixed mutation proof:** exact canonical
   evidence/accounting, allowed supporting rows/writes/triggers and independent
   durable verifier in section 8, preserving existing family semantics without
   importing legacy execution authority.

Concrete storage installation/manifest/fingerprint/enrollment compatibility must
also be resolved before implementation; inert Z31 definitions cannot be assumed
installed. No existing migration or production enrollment is changed here.

### Prohibited

Grandfathered authorities; policy inferred from IDs/time/flags; generic callbacks
or context impersonation; arbitrary SQL/target selection; independent witness
factory; partial family effects; synthetic legacy claims/EXECUTING/seals; reuse
of legacy receipt authority; cross-phase caches; skipped fresh validation; retries,
adoption/recovery execution or fence deletion; longer lifetime; production execution
or activation from this design.

## 15. Test-design boundary (not executed)

| Category | Required future adversarial coverage |
| --- | --- |
| Unit / ownership | Original exact context and source; fake/copy/serialization, PID/Thread reuse, cross-context/runtime/operator, expired or closed phase, connection/epoch replacement |
| Authorization | Old source, missing/wrong policy/Q/E prefix, policy revocation, forged consent/audit, each exact scope field mismatch, no privilege from journal or witness |
| Fresh admission | Auth/MFA/revocation, approval/ACK, activation, profile/generation/owner, stop set-clear, dependencies, physical/schema/fingerprint, history/claims/control/migrations/readiness, clock/deadline changes at every boundary |
| Family / write proof | Full First Look competitor/claim set and Geography scopes/membership/awards/facts, rule/support collisions, existing private operation, unexpected row/trigger/schema write, missing/extra effects, all rollback together |
| Witness consistency | Wrong D/pending/source/manifest/effect/time, fabricated effect digest, exact canonical proof recomputation, witness absent or inserted separately, committed-snapshot verification |
| Duplicate / replay | Concurrent original invocation, recursive use, duplicate start/witness, new D same operation/manifest, restart, known failure and uncertain commit all remain fenced |
| Transaction / crash | Failure at every C1/C2/T/C3 mutation and commit/cleanup, process termination before/after effects/witness, target committed/control pending, unknown commit, no automatic retry |
| Audit / outcome | Typed original eligibility/source/journal linkage, exact expected audit sequence/head, positive no-commit evidence versus absence, no recorder permission from an enforcer |
| Separation | No legacy rows/format changes; no writer-boundary acceptance, raw handle, grant-of-grant, recovery executor, completion seal, readiness/activation side effect |

Tests must use genuine disposable trusted lifecycle where relevant, not verifier
callbacks that manufacture permission. Timing tests require separate authorization.

## 16. 120-second distinction

Authority remains at most 120 seconds from actual original issuance, clipped by
earlier bounds. No journal write, grant construction, commit or phase reacquisition
restarts it. This document proves no lifecycle timing feasibility and authorizes
no production execution. Performance measurement is deferred until implementation
is separately authorized. No Z18, T or performance investigation is proposed here.

## 17. Decision B and stop

**B - IMPLEMENTATION DESIGN INCOMPLETE.** G4's model is bounded, but the exact
prospective protected source/control producer protocol and complete actual-effect
evidence/write proof in section 14 are still unspecified. Those are authorization
and attestation requirements, not details that can safely be selected in code.
The design must not claim completion merely because SQLite supports atomicity or
because an inert witness codec accepts a digest.

Stop here. No implementation or performance work is proposed. No permissions are
granted; no existing authority, transaction owner, writer or lifecycle is altered.

## 18. Validation and production blocks

Only this document is added. Validate document whitespace/local links and
`git diff --check`. No Python/schema/migration, pytest, Z18, T, broad suites,
grant/enforcer, target DML/DDL, production/hosted resources, key reads, commit or push.

PRODUCTION AUTHORIZATION: BLOCKED

PRODUCTION EXECUTION: BLOCKED

PRODUCTION ACTIVATION: BLOCKED
