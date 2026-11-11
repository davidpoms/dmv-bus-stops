# 4e-20-Z14: pre-authority preparation and late-issuance ownership contract

## 1. Purpose

**Preparation is evidence, not authority.** Define a narrowly owned, volatile
preparation boundary inside the original coordinator issuance reservation, before
confirmation consumption and authority construction. As clarified by Z15-C below,
only the schema inventory represented by the existing Z7 observation may be
reused within the proposed same-issuance-phase scope. No migration-row or
migration-relationship result is reusable. All live decisions remain fresh.

This is a new design boundary, not a claim that this preparation owner or its
reader integration exists. It is not implied by Z6. No implementation, schema,
migration, new API or authority is added here. Wider preparation transport across
issuance/attempt/metadata reservations is **UNRESOLVED** and prohibited pending
its own contract. Unsupported reuse means a fresh read, not an exemption.

The source contracts are [Z13](recognition-runtime-authority-budget-architecture-review-4e-20-Z13.md),
[Z5](recognition-runtime-admission-lifetime-contract-4e-20-Z5.md),
[Z6](recognition-runtime-final-validation-observation-continuity-contract-4e-20-Z6.md),
[Z7](recognition-runtime-attempt-schema-manifest-observation-slice-4e-20-Z7.md),
[Z9](recognition-runtime-schema-manifest-observation-consumption-contract-4e-20-Z9.md)
and [Z10](recognition-runtime-physical-identity-continuity-contract-4e-20-Z10.md).
The contract retains the original continuation, authenticated consent, G+2
enrollment and independently verified activation. It grants no runtime admission.

## 2. Z13 measured constraint

Z12's one measured lifecycle entered issuance/admission at 87.750s overall and
published the coordinator at 150.123s with 97 seconds remaining. Its nested
issuance finalization took 23.035s. Attempt creation then took 94.141s, including
46.976s finalization, and finished with 3 seconds remaining. Metadata admission
expired with zero remaining before mode transition or INSERT. Nothing later was
measured. These overlapping intervals must not be summed as independent costs.

The maximum remains 120 seconds **from immutable authority issue time**, shortened
by existing earlier credential/ceremony expiries. Publication cannot restart it.
Moving static computation before issue time could reduce work charged afterward;
there is no measured speedup or feasibility claim for this contract. In particular,
attempt creation alone spent most of the remaining budget; this narrow boundary
does not promise to solve that problem. It authorizes neither another timing run
nor extending the lifetime.

## 3. Preparation owner

The future preparation owner is a distinct private, nonserializable subordinate
of the genuine coordinator's **issuance-phase** `CoordinatorAdmissionContext`.
It is not another transaction primitive, runtime validator, session issuer or
coordinator. It receives no raw connection or caller-supplied scope. Its original
parent must resolve through the existing private registrations and `_state()`.
The same outer coordinator, exact PID/Thread object/identifier and paired clock
remain authoritative. An unregistered object or compatible-looking adapter fails.

Creation is permitted only after the private issuer's complete successful fresh
`coordinator._evaluate(state)`, with both original reservations held, before
`_persist()` consumes confirmation. There must be no pending authority/notice,
attempt creation or other preparation in flight on that owner. Existing durable
authority/manifest exclusions and exact consent checks are not replaced.

The implementation source is
[`runtime_execution_coordinator.py`](../src/review/recognition/runtime_execution_coordinator.py)
(`_phase`, `_evaluate`, `_state`, `_finish`, `_promote`) and
[`runtime_activation_authority_issuance.py`](../src/review/recognition/runtime_activation_authority_issuance.py)
(`_issue_for_coordinator`, `_persist`, `_body`, `_final_mutations`). This document
specifies proposed ownership requirements; it does not relabel an existing 3a,
activated, consent, metadata or issuance inspection object as a preparation owner.

Preparation itself has no SQL mutation permit: no target DML/DDL, control DML,
attempt, authority, audit event, auth issuance or denial-reduction write. Existing
parent validation may retain its independently defined denial behavior; any such
write makes preparation ineligible. No success token is returned to the caller.

## 4. Late-issuance owner

The existing manager remains the sole issuance transaction owner. Preparation
does not gain commit, rollback, SQL, cursor or connection access. The existing
private `_issue_for_coordinator()` boundary must still resolve the genuine parent,
freshly check current scope and consent, and use `_persist()`'s exact protocol.
The public `issue()` remains inspection-only in continuation terms; it cannot
import preparation or manufacture an original coordinator continuation.

"Late issuance" here means static evidence is ready **before** the existing
one-use confirmation CAS and `_body()` issue-time sample. It does not mean changing
issue time after constructing the authority, postponing it until publication, or
creating the attempt first. No existing mutation ordering or transaction ownership
is changed by this contract. Issuance final validation and manager commit still
consume the original live authority window.

## 5. Binding identity

The proposed private preparation record binds these authoritative identities;
caller expectations must be compared with durable/current scope, never accepted
as replacement values:

- original outer/context/phase identities, PID, exact Thread and identifier;
- exact original control and target connection objects, active transactions,
  reservation identities/epochs and target query-only mode;
- installation ID, target UUID, owner, finalized G+2 generation, binding digest,
  runtime-profile digest and exact U/V/Y finalized-transition relationships;
- operation ID/digest, writer-manifest digest, runtime operation target,
  proposal identity and exact control acknowledgement;
- approval identity/digest and invalidation scope; original primary/session
  scope digests and authentication/MFA epochs;
- current independently verified activation incarnation/sequence/digest;
- exact consent step/confirmation artifact and intended subject/reason binding;
- schema/code policy identity, expected package/definition identities, baseline
  mutation accounting and audit position. Migration relationships are verified
  freshly through existing readers; they are not prepared evidence;
- original paired-clock scope and all accumulated credential/ceremony deadlines.

Physical identity/schema and live dependency/readiness/stop observations may be
recorded for exact comparison but do not become reusable permission. No plaintext
credentials, key material, nonce or request-supplied host/device/path establishes
source provenance. A digest binds content; private original-owner registration
establishes in-process provenance within the existing trusted-host model.

## 6. Preparation evidence

The minimum candidate, called **issuance-phase M** here as a design label rather
than a format/API name, covers only the exact control schema inventory represented
by Z7's observation: object names and stored SQL definitions, with their existing
projections/normalization/digests. It does not cover migration validity, verified
migration rows/relationships, complete control validation or history. The Z15-C
matrix below supersedes the earlier wording that included verified migration
relationships. A fact is not included because its reader is called a manifest
reader.

### Z15-C: explicit reusable-predicate boundary

**Schema inventory preparation does not establish migration validity.**

| Observation | Reusable? | Fresh validation required? | Binding |
| --- | --- | --- | --- |
| Schema inventory | YES, only the immutable observation of the exact inventory represented by Z7 | No repeated inventory enumeration within proved continuity; all existing eligibility, physical-identity and boundary checks remain fresh | Exact original issuance context, connections, transactions, reservation epochs, owner and scope |
| Migration definitions | Only insofar as they are immutable schema inventory | YES for every relationship use; an inventory projection/digest is not migration approval | Existing issuance binding and current reader contract |
| Migration audit rows | NO | YES, including canonical body/digest, action, cardinality, actor/time and scope checks required by the reader | Current issuance context |
| Predecessor ordering | NO | YES, including predecessor audit ordering and schema-digest relationships | Current manifest/transition |
| Binding relationships | NO | YES, including installation, generation, profile and migration scope relationships | Current operation/profile and existing reader contract |
| Transition state | NO | YES, including current migration/profile continuity and pending/finalized state | Current transition |
| Any unspecified relationship | NO | YES | Existing reader contract |

"Immutable" describes the captured inventory content, not an assumption that an
installation can never change. The proposed issuance use must retain Z7's
ownership, isolation, definition/code identity, exact-write proof, invalidation
and per-consumption physical checks, applied only to Z14's separately specified
issuance phase. Z7 itself remains attempt-phase infrastructure: this clarification
neither expands its implementation nor allows its objects to cross phases. If
the proposed issuance implementation cannot prove equivalent inventory continuity,
reuse is unavailable; it must keep fresh reads or stop. No once-only physical
identity check is permitted.

Existing reader behavior makes the split concrete:

- `runtime_enrollment_transition_schema.historical_manifest()` may obtain object
  definitions through an eligible inventory reader. Its migration audit rows,
  predecessor ordering, installation/generation binding and transition predicates
  must still be read and validated freshly.
- `runtime_execution_attempt_schema.check_manifest_transition()` may project
  eligible definitions, but its migration audit, schema-digest relationships,
  predecessor and binding checks remain fresh.
- `runtime_execution_claim_schema.check_rows()`,
  `runtime_activation_authority_schema.check_manifest_transition()` and the other
  existing control/profile/history readers retain all row and relationship
  predicates. Nothing in a prepared inventory substitutes for their success.
- Z7 `_objects()` provides schema inventory only. Its use inside a manifest
  reader does not widen that inventory into migration evidence.

No prepared migration evidence is created by Z15. It cannot authorize issuance
or attempt creation, substitute for fresh migration validation, be adopted by
another context or survive as an executable handoff. Existing source-row bindings
remain the responsibility of the fresh reader; no new migration-observation
fields, binding rules, portable formats or invalidation mechanism are defined.

All evidence content is immutable. Eligibility is a live manager-owned decision,
not an immutable `valid=true` flag. Pure expected definitions/canonical digests
can be computed without authority, but do not prove an installed schema. Verified
installed facts must originate in the fresh parent validation above. No durable
record, exported envelope, signed file, portable hash, public constructor, JSON,
pickle/copy restoration, browser claim or provider callback is an accepted source.

Static G+2 profile relationships (Z6 P) and historical claim-local integrity (Z6 C)
remain possible separately reviewed preparation classes, **not included in the
minimum implementation**. Z6 creates them only in its exact original attempt
transaction. Earlier issuance-phase creation/consumption needs its own complete
predicate/write/invalidation mapping and is **UNRESOLVED**. Current profile,
claim disposition and full history/control readers remain fresh.

## 7. Fresh-validation matrix

Every column preserves the existing authoritative kernels and exact scope. There
is no new boolean to suppress checks and no cached full admission decision.

| Predicate | Immediately before issuance/CAS | Before attempt creation | Before metadata admission and later transitions |
| --- | --- | --- | --- |
| Authentication and time | Current primary/session, owner, revocation, auth/MFA epochs, consent freshness, all earlier deadlines and paired-clock checks | Fresh original credentials/epochs, authority/consent scope and original expiry | Fresh original credentials/epochs and all applicable live deadlines |
| Activation | Current independent incarnation/ledger, exact scope | Fresh exact authority incarnation; reject changes | Fresh exact incarnation; no preactivation upgrade |
| Proposal/ACK/approval | Exact current pairing, approval digest/validity/invalidation, operation target | Fresh current pairing and authority binding | Fresh exact attempt/authority pairing and current validity |
| Dependencies/readiness/stop | Fresh current kernel decisions | Fresh current kernel decisions | Fresh at all existing metadata boundaries |
| Physical identity/schema | Actual hostname, both canonical paths/devices/inodes, target schema and exact package | All required actual checks repeated | All required actual checks repeated, including mode/commit/reacquisition boundaries |
| History/audit/control | Full current graph/head/time/FKs and protected state; no reused complete result | Fresh new phase, then fresh changed attempt/audit/FK predicates | Fresh new phase and changed target-entry/commit predicates |
| Claims/exclusions | Fresh disposition/lifetime/global graph/operation uniqueness | Fresh disposition and authority/attempt exclusions | Fresh current graph and exclusions |
| Static inventory M | May consume only covered schema inventory with fresh eligibility; every migration row/relationship predicate remains fresh | Discard issuance M. Existing Z6/Z7 attempt-local creation may run only under its own scope | Discard prior-phase M; no Z6 crossing into metadata |
| Profile/enrollment | Current finalized G+2 binding/profile and no pending transition | Fresh current selection and relationships | Fresh exact G+2 and target-entry schema/fingerprint relationships |
| Ownership/reservations | Exact original parent, both transactions/connections/epochs | Original continuation plus new phase's genuine ownership | Original created attempt plus metadata's new ownership; no inherited old view |

The fresh pre-CAS gate does not eliminate existing post-write `_finish()` checks.
After authority construction, all current predicates and exact mutation/audit
checks required by that manager still run before control commit. Target remains
reserved through that control commit. No observation crosses into the next phase.

## 8. Invalidation rules and exact lifetime

Preparation is volatile and single-owner. Its exact lifetime is the intersection
of the original active issuance-phase reservation and all existing parent
authentication/ceremony deadlines. There is no new TTL, grace period or numeric
preparation lifetime. It ends on the first invalidation below; it never resets
the later 120-second authority clock. No caller controls time.

Invalidate on parent exit/poison/exception/denial, PID/thread/scope change,
connection/transaction replacement, commit/rollback/savepoint, reservation loss or
epoch change, query-only/mode change, code/schema/package/policy change, DDL/ATTACH,
extra/unclassified DML, altered expected write, missing/changed graph, clock
anomaly or applicable deadline. Commit or cleanup uncertainty also destroys
eligibility. A later reread does not revive the original object.

Changes to authentication, activation, profile/generation/install/owner,
approval/ACK, dependency state, stop, physical identity or current control/history
must reject stale preparation at its next checked use. No universal event listener
is claimed. Current live predicates are read again; SQL authorization and exact
mutation proofs cover the local write set only. External physical changes remain
subject to fresh physical checks, not an invented filesystem continuity guarantee.

The only proposed local continuity exception is issuance-phase M across exactly:

1. confirmation `used=0 -> used=1` CAS;
2. its consumption audit INSERT;
3. exact authority INSERT;
4. exact AUTHORIZED genesis INSERT;
5. exact issuance audit INSERT.

These do not themselves change schema definitions. Even though preexisting
migration rows are not changed by this protocol, Z15-C grants no reuse of their
validation results: those rows and their relationships remain freshly validated.
They do change credentials' confirmation-use state, authority/lifecycle population,
audit head and global FK/graph predicates. Those facts are outside M and must be
validated fresh. Authority body scope/digest, expiry, original consent and exact
expected audits remain mandatory. This is a specifically proposed **new issuance
scope**, not permission inferred from Z6's three attempt INSERTs.

Implementation must prove the full fixed write set and installed trigger behavior,
not merely `total_changes == baseline + 5`: exact rows/bodies, one changed expected
confirmation, exact audit suffix/predecessors, unchanged protected baseline apart
from that CAS, no target changes, no extra SQL mutation and authoritative installed
definitions. Existing `_final_mutations()` is a required reference, not automatic
proof that a new preparation adapter satisfies this contract. If the proof or
complete predicate partition fails, reread fresh or stop; do not extend M coverage.

## 9. Crash/uncertain-commit behavior

There is **no preparation commit**: preparation is read-only volatile evidence.
It creates no durable PREPARED record or resumable operation. A connection/cleanup
failure during preparation poisons/discards it and publishes nothing. Any proposal
requiring durable preparation storage or a preparation commit is outside this
contract and **UNRESOLVED**.

Before issuance, loss of the owner loses preparation. After confirmation/authority
mutations start, retain the existing rollback, consumed-ceremony and uncertainty
rules. Never infer rollback from an absent notice/result. Uncertain authority
commit publishes no usable continuation and permits only existing read-only
inspection, not automatic retry, adoption or reconstruction. Confirmed commit
still needs both cleanups before original-owner promotion.

Attempt commit and metadata target commit remain distinct transactions. Nothing
here changes their spent-continuation, target-held-through-control-commit or
post-target-commit reacquisition/cleanup requirements. No cross-database atomicity,
recovery/adoption or automatic compensation is introduced.

## 10. Duplicate/concurrency behavior

No duplicate-preparation API, background preparer or process-local lock is added.
Only one internal preparation may be active in the original issuance phase. An
extra call cannot replace scope, refresh deadlines or create another authority.
How an implementation represents the one internal slot is not a public contract;
it must reject substitution and cannot be used to retry a poisoned phase.

Existing control-first/target-second reservations serialize durable issuance;
ordinary SQLite BUSY/LOCKED behavior stays unchanged. Authority uniqueness by
operation/writer manifest, one-use confirmation CAS and original pending-notice
rules remain decisive. The coordinator cannot turn duplicate durable authority
inspection into an original continuation. Concurrent different owners must each
validate their own current state; preparation is never shared between them.

## 11. Adoption prohibition

Preparation, authority JSON/digest, `IssuedAuthority` inspection, durable attempt
rows and historical target-entry data cannot reconstruct the original lifetime.
No other process, thread, context or authenticated ceremony may adopt preparation,
even with identical installation/profile/operation fields. An expired original
owner cannot be revived by new authentication or matching digests. Prepared but
never issued data is discarded, not recovered. There is no durable record to
resume. A new genuinely permitted operation still needs its full existing
proposal/ACK/approval/consent path and all historical exclusion gates.

## 12. Security/TOCTOU analysis

Preparation borrows only the parent's existing control BEGIN IMMEDIATE and target
BEGIN IMMEDIATE/query-only reservations. It reserves no additional resource and
creates no permanent filesystem or execution lease. Reservations are needed for
current authoritative reads and fixed local mutation accounting. The preparation
object neither owns their release nor extends their lifetime.

Only immutable covered data plus original-owner provenance may cross the internal
preparation-to-issuance call boundary. Recompute current authentication, activation,
stop, dependencies/readiness, physical identity/schema, current graph/head/FKs,
claim disposition, ownership and deadlines as the existing kernels require.
Discard all observation eligibility on phase commit/release and before attempt or
metadata phases. Neither SQL locks nor synthetic witnesses guarantee unchanged
external paths, devices, inodes or hostname. Z10 remains decisive.

Expected definitions and digests alone cannot establish installed state. An
immutable body alone cannot establish current approval or authorizing provenance.
No pre-authority operation/attempt/target marker is inserted. The future writer
boundary must reject preparation exactly as it rejects other inert DATA.

## 13. Storage requirements

No new schema/storage, migration, format version, durable digest column, signed
preparation artifact or administrative enrollment transition is required for this
volatile minimum. Existing G+2 finalization and exact target-entry package/schema
guards remain authoritative; preparation cannot enroll, rebind or approve them.

The existing immutable authority format, genesis, five-write issuance protocol,
attempt relationship and target-entry codec stay unchanged. A preparation-owner
registry would be private process-local implementation state, never persistence
or a global/TTL cache. A design needing cross-phase durable preparations or a
pre-authority attempt requires a separate storage/security contract and is not
approved by this document.

## 14. Exact lifecycle ordering

1. Enter the existing genuine authenticated original coordinator issuance phase;
   acquire control, then target reservation/query-only, and validate current state.
2. Perform the private issuer's complete fresh evaluation. Construct only the
   internal static preparation evidence while the exact original scope is live.
3. Check eligibility and freshly validate all current scope/consent/exclusion
   predicates immediately before consumption. Any mismatch fails closed.
4. Perform the existing one-use confirmation CAS. Only then construct the authority
   with the existing issue-time sample and earliest expiry; do not resample later.
5. Complete the exact five-write protocol. Preparation may cover only its proved
   static predicates. Freshly validate changed/current predicates and final state.
6. Manager commits control while target remains held; invalidate preparation at
   the transaction/epoch boundary. Clean up both connections. Only the original
   genuine private notice may promote the original continuation.
7. Attempt creation uses a fresh registered phase, fresh reservations and full
   current validation. Existing Z6/Z7 attempt observations are independent of
   issuance preparation. Its exact three INSERTs, finalization, control commit
   with target held and cleanup remain unchanged.
8. Metadata-owner admission uses the genuine original created attempt, finalized
   G+2 and independent activation. Its fresh reservations, validations, view/mode
   transitions, permitted future marker INSERT/commit, reacquisition and final
   checks are unchanged. No earlier preparation can authorize any of these.
9. Expiry at any stage rejects; uncertain commit/cleanup yields no usable result.
   No retry, renewal, adoption, writer capability or completion follows.

This sequence is a contract only, not permission to run Z/T or target DML here.

## 15. Rejected alternatives and unresolved extensions

Reject public preparation imports, caller-supplied scope or "checked" flags,
database-selected resume authority, fabricated legacy claims/EXECUTING, delayed
issue-time rewriting, deadline extensions and creation of attempts before their
authority. Reject complete-history/control caching and once-only physical checks.
Do not merge/widen 3a, consent, issuance, attempt and metadata owners to make a
token survive. Do not change operation portability or authentication semantics.

**UNRESOLVED:** useful continuity across issuance commit/new attempt reservation;
issuance-phase P/C preparation; complete-history delta validation; transport into
metadata mode changes/commit/reacquisition; durable/recoverable preparation; and
whether this scoped preparation provides any measurable positive budget saving.
Each needs its own exact predicate/provenance/mutation/invalidation/uncertainty
contract. Here they mean reject reuse and keep current readers, not leave a
discretionary bypass. Existing G+2/activation contracts do not fill these gaps.

## 16. Next implementation boundary

The smallest candidate implementation is **one private issuance-phase static
schema-inventory preparation observation**, consumed only within its original
registered issuance transaction around the exact five mutations. No broader
phase restructuring, profile/claim/history reuse, metadata optimization, schema,
durable record or public interface belongs to it. Implementation requires separate
authorization and must stop if any covered inventory predicate or exact-write proof cannot
be established; a nominal "preparation" object without reader consumption is not
an authority-budget improvement.

Required focused acceptance tests: exact predicate equivalence; genuine-owner-only
creation/consumption; immutable/nonserializable evidence; exact scope/consent and
five-write proof; invalidation on extra/altered writes, denial, schema/code change,
epoch/connection/transaction/mode changes and cleanup; fresh physical/auth/activation/
approval/stop/dependency/current graph checks; expiry/clock rejection; wrong process/
thread/ceremony and duplicate issuance; uncertain commit and no adoption; unchanged
attempt/metadata reader behavior; zero preparation DML and no downstream authority.
Fresh migration-row/relationship validation must be explicitly exercised; tests
must reject malformed migration audit, predecessor, binding and transition data
even when the prepared inventory still matches. No speedup or complete-lifecycle
feasibility claim precedes later separately
authorized measurement. If this contract's narrow scope cannot yield useful safe
preparation, return to the Z13/Z5 architectural decision, not blind optimization.

Required-question coverage: sections 3–6 answer 1–8; sections 7–8 answer 9–20;
sections 3/9/12 answer 21–27; sections 10–11 answer 28–30; sections 6/12/14–15
answer 31–34; sections 13 and 16 answer 35–36. Unsupported wider semantics are
explicitly unresolved and prohibited.

Documentation validation only: `git diff --check` and established new-document
whitespace/link checks. No pytest, Z12, Z, T, broad suites, implementation,
migration, hosted/production access, commit or push.

PRODUCTION AUTHORIZATION: BLOCKED

PRODUCTION EXECUTION: BLOCKED

PRODUCTION ACTIVATION: BLOCKED
