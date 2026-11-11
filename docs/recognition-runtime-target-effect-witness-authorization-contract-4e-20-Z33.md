# 4e-20-Z33: target business effects and authorized witness review

## 1. Z32 blocker and decision

[Z32](recognition-runtime-decision-bound-outcome-journal-producer-contract-4e-20-Z32.md)
defined required journal ordering but not an authorized business-effect/witness
producer. This review concludes **B: one specific target security primitive is
missing — a decision-scoped target mutation-and-commit attestation boundary**.
That boundary must combine actual original-owner authority, the exact existing
family mutation, complete effect verification, same-transaction journal witness
and source-audit correlation. None of its facets follows from valid journal DATA.

The existing business effect and important read-only integrity checks are defined.
The missing primitive is not another UUID, hash function, metadata marker or table
of candidate awards. No code, target behavior, mutation permit, authority, witness
producer, schema, migration or source-audit writer is added here. The unchanged
120-second ceiling does not become a feasibility promise.

## 2. Exact existing business-effect definition

Sources:
[`permanent.finalize`](../src/review/recognition/permanent.py),
[`permanent_schema.TABLES`](../src/review/recognition/permanent_schema.py),
[`local_execution.SUPPORTED/POLICY`](../src/review/recognition/local_execution.py).
Supported effects are `finalize` of `first_look` or `geography_steward`, under
`atomic-historical-v1`, with no quarantine or other outcome categories. They are
not corrections, active capture, review reassignment, arbitrary SQL or Explorer
mutations. Do not extend the set because a generic branch accepts another value.

The private writer's `operation_id` is **digest of the frozen private manifest**.
It is not the runtime operation UUID. Runtime operation/authority must bind that
same `writer_manifest_sha256`; confusing these domains would break correlation.
Existing rule/operation/family rows are immutable and whole-population effects
remain atomic. The target transaction must regenerate all required preconditions
before any new-family write, using the manifest's frozen evaluation and inputs.

| Effect group / target tables | Exact existing semantic operation | Scope / observable outcome / failure |
| --- | --- | --- |
| `recognition_private_rules` | Reuse exact matching stored rule, or insert the existing canonical rule definition | Rule key/family/digest must match frozen manifest; mismatch rejects |
| `recognition_private_operations` | Insert canonical manifest, manifest-derived operation key, rule key, explicit authorization reference and existing sealed-at metadata | One operation exactly identifying the whole business manifest; prior operation is historical/idempotent only under its existing path, not a new runtime decision's effects |
| `recognition_first_look_claims` | Insert one immutable claim for each frozen candidate, binding physical stop, reviewer, assignment, manifest operation, earned time and canonical evidence/digest | Exact selected population and existing immutable completion evidence; any conflicting stop/assignment or changed source rejects entire transaction |
| `recognition_geography_scope_identities` | Insert each frozen catch-up scope identity | One existing-policy catch-up per scope; later snapshots/denominator changes are not implicitly permitted |
| `recognition_geography_snapshots`, `recognition_geography_members` | Insert exact frozen scope snapshot/digest and complete frozen physical-stop membership | No recalculation against a later geography or silently smaller denominator |
| `recognition_geography_awards`, `recognition_geography_witnesses` | Insert each candidate award's exact reviewer/scope/tier/snapshot/time/numerator/denominator/percentage/size/evidence and qualifying assignment witnesses | Exact award/witness sets, frozen membership and completion facts; conflict/missing/extra source rejects |

`recognition_first_look_discrepancies` is not a finalize effect; explicit discrepancy
corrections have a separate existing operation/authorization path. Review/source
tables and Explorer are prerequisites, not mutation targets. Historical First Look
credit is not transferred because reviews were later deleted or changed.

Existing mutation ownership is `permanent.finalize()` under its own verified
authority/transaction, or its exact accepted existing leased writer context. It
owns commit when unleased. The replacement runtime cannot legally call through
that boundary merely with a new D or journal pending row. Existing authorization,
production guard and legacy claim requirements remain in force.

## 3. Authoritative effect verification

| Status | Authoritative source / what it does not prove |
| --- | --- |
| Attempted | Original manager knows it entered a write path or issued statements; process logs/SQL trace do not prove persistence |
| Accepted | Successful statements and existing writer result describe work accepted in that transaction; leased `finalize()` can return before its owner commits |
| Committed | Confirmed target transaction and independently observed durable complete records/witness on the exact target lineage; a local result or uncommitted witness is insufficient |
| Observable | Rows readable from a validated committed snapshot; wrong-target/restored/stale snapshots cannot establish original outcome |
| Verified | Full canonical manifest/record/population integrity plus exact D/pending/target witness/effect digest and durable source/audit correlation |
| Uncertain | Missing, conflicting, unavailable, wrong-lineage or not-confirmed commit evidence; neither an error nor an absent response resolves it |

Existing read-only checks in `permanent.py` provide a concrete basis:

- `_operation()` checks stored canonical manifest, manifest-derived key/digest,
  explicit authorization reference, rule key/definition/family and stored time.
- `_verify_operation_records()` requires exact First Look claim set or Geography
  snapshot and award sets, validates scope identities and membership, and invokes
  per-record integrity checks. Counting rows alone is not sufficient.
- `check_claim_integrity()` checks exact candidate evidence/digest, reviewer,
  assignment, earned time and immutable competing qualifying-completion facts.
- `check_geography_integrity()` checks every candidate field/evidence, exact scope/
  snapshot/membership/denominator, assignment witness set, distinct physical-stop
  numerator, reviewer identity and immutable source completions/rules.
- Existing prewrite `_prepare()` equality checks all current required qualifiers,
  competitors, identities, members and candidates against the frozen manifest;
  historical record verification does not replace this live prerequisite check.

The existing actual-record extraction set is
`production_receipts._records(target, manifest)`: private operation and rule;
First Look claims; Geography snapshots/awards and their scope identities,
members and assignment witnesses, with canonical deterministic sorting. A minimum
candidate effect-evidence digest is `digest(that exact extracted record set)`
**after** full manifest/record integrity validation. This is a definition of the
existing read-only record set to be bound, not a new legacy receipt or permission
to invoke its writer. Shared historical source facts must still be validated by
the integrity readers. No additional effect or arbitrary evidence object is added.

The complete replacement verification boundary must bind that record set and
validated whole-population accounting to the exact runtime operation/manifest/D,
and prove no unpermitted target writes occurred. The existing extraction/checks
do not by themselves supply producer authorization, exact-write ownership or a
new commit attestation. This integrated boundary remains **UNRESOLVED**.

## 4. Exact inert witness and required production semantics

Use the Z31 witness shape unchanged:

```text
format
decision
pending
recorded_at_utc
outcome = TARGET_COMMITTED
effect_evidence_sha256
```

`decision` embeds the exact canonical authority; D is authority ID/body digest.
`pending` is the unique exact TARGET_PENDING event with verified decision digest,
genesis/predecessor, actor and time. Authority runtime target/physical snapshot
bind installation, target, G+2 profile/generation/owner/epochs and independently
validated activation incarnation. The writer manifest and runtime operation
UUID/digest remain separate exact bindings. No caller supplies replacement data.

`effect_evidence_sha256` must be derived internally from complete verified actual
record evidence, not accepted from a request or manufactured by a test callback.
Its positive verification must be repeated from actual committed rows when resolving
outcome. Z31 validates only the detached reference's shape and graph; it does not
claim to verify these business facts.

SQLite has no required new global transaction ID here. The equivalent commit
proof would be **durable visibility of the immutable D/pending/effect-bound witness
outside the original transaction, whose approved writer committed that witness
atomically with every permitted business effect**, followed by full independent
actual-record verification on the validated target. The recorded timestamp is
not a claimed exact commit instant. No filesystem continuity is inferred.

Lookup uses D and exact operation/manifest constraints on the intended target,
not whichever witness matches one digest. Absence cannot prove no commit. Existing
Z31 witness immutability/uniqueness protects DATA; it cannot prove an authorized
writer produced it. **The authorized same-transaction mutation/witness producer
and complete commit/effect verifier remain the missing target primitive.**

## 5. Smallest atomic unit

All actual new rule/operation/family rows for one frozen manifest, plus exactly one
decision-bound journal witness, must be within **one target transaction**. Existing
matching rule rows need not be reinserted. Every inserted family row remains in
the expected effect set. No intermediate family commit or witness-only commit
is allowed. Required fresh admission, source regeneration, actual-effect checks,
FK/integrity and deadline/physical/stop/scope checks precede target commit.

SQLite can represent this local all-or-nothing transaction in principle; the
current authorized runtime writer interface cannot perform it. Calling unleased
`permanent.finalize()` then inserting a witness afterward would create precisely
the forbidden committed-effect/no-witness crash window. Fabricating a leased
legacy context to suppress its commit is equally prohibited.

If the witness cannot be encoded, verified or inserted, rollback all known
uncommitted target effects. If target commit is uncertain, retain permanent
decision/manifest exclusion and report UNKNOWN. No future repair may insert a
witness after effects merely to make an incomplete history look atomic.

## 6. Owner mutation permit: required boundary, not a grant

| Category | Requirement |
| --- | --- |
| Authentication | Current genuine owner primary/session/MFA/epochs; necessary but not mutation permission |
| Admission | Fresh exact operation/proposal/ACK/approval, activated G+2 scope, identity/schema, dependency/readiness/stop, claim/history/control and all deadlines |
| Target mutation permission | Only an approved original runtime transaction owner may enable a fixed set of exact family/journal writes after fresh final admission; no arbitrary SQL or alternate target |
| Writer capability | Opaque, nonserializable, one-shot original PID/thread/context/connection/transaction/reservation-epoch binding to D, manifest/operation, target and activation/profile/install/generation/owner/epochs |
| Execution capability | No broader privilege inferred; invoking the permitted fixed mutation still requires live original registration, current scope/deadlines and no duplicate use |

Only the genuine independently authorized runtime execution owner could eventually
grant its internal exact-action permit. Z31 validators, journal state, an outcome
resolver, caller arguments and general administration cannot grant it. Actual
authority expires at original issue plus at most 120 seconds, clipped by earlier
auth/consent deadlines. No timestamp renewal. Activation/profile/generation/owner/
auth/MFA/approval/stop/dependency/physical/reservation changes fail required current
checks; rollback known uncommitted work and poison the local permit on failure.
Cross-thread/process/context use, connection/transaction replacement, duplicate
use or owner exit rejects. No journal recovery restores the permit.

Current `writer_boundary._local_lease/verify_local` requires exact existing
local/legacy claim and EXECUTING history, and `_lease` is disposable-only. No
replacement runtime owner can legally receive this new permit through them.
The exact **decision-scoped target mutation-and-commit attestation boundary is
UNRESOLVED**. This document defines what it must prove, not a new capability,
constructor, callback, authorizer exception or extraction from the legacy writer.

## 7. Minimum source-audit relationship

The existing source authority/consent/genesis and effective approval/ACK histories
remain authoritative for **original permission and intent**. Their exact scope
is not replaced by a new journal audit or target hash.

The minimum outcome chain is:

```text
validated source authority/consent/audit for D
  -> exact journal decision and unique pending event
  -> D/pending-bound target witness and verified actual records
  -> control COMPLETED referencing that exact witness digest
  -> required corresponding control audit and original-owner publication
```

Each control journal group and its audit must commit atomically under the future
owner's fixed mutation proof. The audit need bind D and the exact journal event
digest; the journal event already binds decision/pending/witness, so duplicating
all business rows and source approval history into general audit is unnecessary.
Exact action/subject codec and installed audit/producer proof remain unimplemented;
no new audit fields/events or generic append permission are added here.

Authority sources answer whether an action was permitted; a verified target witness
and actual records answer what target effects committed; matching control terminal
and audit answer whether that fact was recorded. No one record overrides a conflict
in another domain. If witness, actual effects, source authority or control outcome
disagree, fail integrity inspection, publish no usable success, keep exclusions
and stop. Do not prefer a newer control record or rewrite target/source history.

## 8. Crash and uncertain-commit protocol

| Failure point | Target effect | Witness | Control journal | Recovery |
| --- | --- | --- | --- | --- |
| Before mutation | No known effect of this attempt | None | Confirmed decision/pending may exist | Inspect durable facts; no adopter/retry |
| During mutation | Uncommitted population in original T | Absent or uncommitted | Pending; uncertainty event may be absent after crash | Known rollback resolves only original T; observer does not guess |
| After effect before witness | Business DML executed but must remain uncommitted | Not yet inserted | Pending | Commit forbidden; rollback known uncommitted work; unknown connection outcome stays UNKNOWN |
| After witness before commit | Effects and witness both uncommitted in T | Inserted is not durable | Pending | Do not publish success or claim target committed from memory |
| After target commit | Full effects may be durable | Must be durable in same T for valid outcome | May remain pending/uncertain | Positive independent witness/effect verification; never repeat mutation |
| Before control outcome | Target may already be committed | Validate exact durable source | Pending/uncertain, not completed | Authenticated factual recording only on positive evidence |
| After control outcome | Positive exact target proof must remain verifiable | Immutable D-bound witness | Exact terminal/audit may be committed | Historical inspection; no restored live permission |

On uncertain target commit the original executor loses usable mutation permission
and publishes no usable success. Keep decision/start and logical operation/manifest
exclusions. A currently authenticated outcome-only inspector may read intended
identities/schema/lineage, D/source graph, pending and witness plus complete actual
family evidence from a committed snapshot. Only positive exact proof can support
factual completion; missing output, missing marker or unavailable records cannot.

Definitive TARGET_FAILED requires positive original-manager no-commit evidence,
not an inspector's absent-witness inference. If source/target/control proof is
missing, conflicting, copied/restored into unclear lineage or inspection itself
fails, remain indeterminate indefinitely. Expiry or a fresh login cannot authorize
new D for the same blocked operation/manifest. Any permitted factual resolution
must commit matching control/audit facts and publish only historical non-executable
data when the original live execution result was lost.

## 9. Duplicate and replay protection

The required safety argument is conditional on the missing authorized target
boundary; it is not proof that the current replacement can execute:

- Existing confirmed source/journal exclusions and the unique pending start fence
  give one original logical winner; competing owners serialize control before target.
- Exact unique target witness on D/operation/manifest and whole-effect atomicity
  prevent another committed effect under that decision. Business manifest and
  First Look/scope/award uniqueness continue to reject their existing conflicts.
- A new D cannot match an old witness: source authority digest, operation/manifest,
  pending event and current scope must be exact. An old effect without a valid
  replacement witness is a conflict/UNKNOWN, never permission to certify it anew.
- Witness lookup is outcome inspection, never an input that grants a new writer.
  A resolver writes no target data and cannot replay business effects.
- Lost or spent original owners cannot restart or transfer process/thread/context/
  reservation identity. New request/session/profile/incarnation IDs do not reset
  logical duplicate exclusion. Uncertainty/failure never releases fences.

No extra lock, reservation lease, recovery/adoption state or retry loop is defined.
Without the missing same-transaction owner/verifier boundary, uniqueness by itself
does not prove that a witness's digest describes its actual committed effects.

## 10. Security separation

```text
target witness != authorization
target outcome != authorization
journal state != writer capability
source audit != execution permission
recovery != reauthorization
```

All current authentication, activation, effective approval/ACK, stop, dependency,
physical identity, history/claim/control, schema/migration/profile, readiness and
original deadline/reservation checks remain independent and fresh at required
use/finalization boundaries. Atomic SQL does not guarantee filesystem continuity.
No data digest substitutes for current checks or original-owner registration.
Completion facts do not authorize another mutation, even if the old grant is
still within its window.

## 11. Decision B

**One specific target security primitive is missing: the decision-scoped target
mutation-and-commit attestation boundary.** It must legally bind the original
runtime mutation permit, exact existing atomic family effects, complete actual
record verification, same-target-transaction D/pending witness and corresponding
source-audit provenance. Read-only verification foundations exist, and SQLite
can support local atomicity, so this is not a claim of fundamental impossibility.

Current `permanent.finalize()` and `writer_boundary` cannot provide that boundary
for the replacement D without a separately approved authority/ownership interface.
The inert effect digest cannot fill it. No permit, extraction, producer or new
target behavior is invented to turn the result into A.

## 12. Exact stopping point and validation

**Stop the architectural chain.** There is no approved implementation, additional
performance investigation or proposed next review/micro-slice from this result.
Keep the target runtime path blocked; no mutation permit or witness writer may be
implemented on the strength of this document. Existing source integrity and
legacy authorization remain unchanged.

Only this document is created. Validate `git diff --check` and document whitespace/
local links. No pytest, Z18, T, broad suite, code/schema/migration, target DML/DDL,
journal installation, producer, authority/writer/execution capability, production/
hosted access, commit or push. The 120-second ceiling is unchanged.

## 13. Production blocks

PRODUCTION AUTHORIZATION: BLOCKED

PRODUCTION EXECUTION: BLOCKED

PRODUCTION ACTIVATION: BLOCKED

WRITER CAPABILITY: BLOCKED
