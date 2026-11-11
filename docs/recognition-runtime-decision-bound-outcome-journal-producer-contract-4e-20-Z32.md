# 4e-20-Z32: inert journal producer and write-protocol review

## 1. Z31 baseline and decision

[Z31](recognition-runtime-decision-outcome-journal-schema-slice-4e-20-Z31.md)
supplies inert control decision/history and target witness definitions, canonical
DATA codecs, immutability/uniqueness/transition guards and read-only inspection.
It installs nothing and confers no producer, resolver, writer or execution authority.

**BLOCK: live producer/write-protocol contract remains incomplete.** The concrete
target blocker is the absent **complete business-effect evidence verifier and
authorized target witness production in the same transaction as those effects**.
The stored `effect_evidence_sha256` is not that mechanism. Existing source audit
provenance and exact owner registration/mutation permits also cannot be inferred
from valid detached journal DATA. This document defines required ordering and
failure behavior, not a new capability or proof that current owners implement it.

No schema/code/migration/producer/target mutation is added; no existing authority
semantics or 120-second lifetime is changed. No performance conclusion follows.

## 2. One future producer owner

The sole normal producer must be the **genuine original replacement runtime
transaction owner** that independently originates the exact authorized execution
decision. This is the conceptual owner from Z27/Z28, not a new privileged journal
factory. It cannot accept historical authority/attempt/preparation DATA as its
live authority or acquire privilege merely by creating a journal row.

| Binding/ownership | Required rule |
| --- | --- |
| Process/thread/context | Exact original private registration, PID, Thread/identifier, active context and paired clock; no constructor/import/copy/pickle/provider substitution |
| Authority/D | Exact original current authority and D = authority_id/body digest, complete durable canonical source/genesis/consent/audit validation; not a caller-supplied body |
| Scope | Exact operation/event/preparation/manifest/population, proposal/ACK/approval, target/install/generation/G+2 profile/binding/owner/auth/MFA epochs and independent activation incarnation |
| Target reservation | Actual current target connection/transaction/query mode/epoch and strict observed identity/schema/fingerprint; never a journal-derived reservation lease |
| Transactions | Manager-owned BEGIN/COMMIT/ROLLBACK/cleanup; control before target; target held through required control commits; no raw handles or arbitrary SQL exposed |
| Control records | Fixed decision/history writes and exact audit linkage only, conditional on actual durable expected head and complete protected mutation proof |
| Result | Only original owner can publish its live execution result after confirmed outcomes and cleanup; factual inspection never reconstructs it |

**No existing component currently owns these journal writes.** Current coordinator
authorizers permit their exact issuance/attempt sets; metadata owner permits only
its existing marker; activated observer is read-only; legacy writer has separate
authority. Do not widen them, impersonate their contexts or add a test callback.
Actual replacement-owner eligibility/registration and its exact journal write
permit remain **UNRESOLVED**, under a separately approved authority/admission
contract. This review grants no new writer/executor API.

A future separately authenticated **outcome-only resolver** may record verified
facts as Z30 allows. It is not a second normal producer or an adopter of the
original executor. Its limited recovery transaction, authentication, provenance
and mutation proof must be reviewed before implementation; none exists here.

## 3. Creation protocol and freshness

Define F as the complete fresh set: genuine current owner authentication/MFA/
consent and all earlier deadlines; exact operation/scope/profile/generation/
installation/owner/epochs; proposal/ACK/effective approval; independent activation;
emergency stop/blocks; dependencies and required whole-population manifest;
actual strict physical identity/schema/fingerprint; current history/claim/control
and migration relationships; protected readiness; actual reservation identity/
epochs; clock-anomaly and original authority expiry checks. F must run through
genuine authoritative readers at each required boundary, not copied kernels or
cached complete admissions. Existing local schema inventory is not cross-phase
evidence or migration validity.

| Step | Required checks and owner | Transaction / durable state | Failure behavior |
| --- | --- | --- | --- |
| 1. Independent final admission | Original runtime owner; F and exact current consent, with no preparation token | Existing separately authorized admission/authority protocol; journal absent | Reject; no usable journal-derived permission |
| 2. Resolve D | Same owner; confirm exact canonical durable authority/body digest and source graph, original ownership/deadlines | Read under genuine control/target reservations; no new random journal ID | Missing/unknown/conflicting source fails closed |
| 3. Register decision and fence | Same owner; F, installed exact journal packages, global old/new operation/manifest exclusions and no existing conflicting D | Control C1: decision row, exact DECISION_CREATED genesis and correlated audit together | Known rollback removes entire uncommitted group; uncertain commit stops, never blind retry |
| 4. Spend sole start | Same original owner; F and exact confirmed C1/head | Control C2: one TARGET_PENDING append and corresponding audit atomically, expected predecessor/sequence | Missing/conflicting/expired owner rejects; once committed, start is spent even if target is never touched |
| 5. Obtain target mutation permission | Same original owner; independently approved exact-action writer/admission, F after actual final reservations/mode transition | No capability is produced by pending; target starts under approved manager-owned transaction T | If writer boundary cannot accept owner, STOP; do not synthesize legacy claims |
| 6. Business effects plus witness | Same owner; exact fresh preconditions, permitted complete family mutation, full effect verifier and final F checks | T contains all business effects and one exact target witness; no intermediate target commit | Any known failure rolls back both; missing witness/verifier blocks commit |
| 7. Confirm target outcome | Same owner; actual durable witness from validated target and complete actual effects, not a local object | Confirm target commit, invalidate old views, use required reservation reacquisition/inspection | Unknown target/cleanup result stops; no usable success |
| 8. Record corresponding control fact | Original owner or authorized factual resolver; exact D/pending/witness/effects and current recording permission | Control C3: COMPLETED and exact audit atomically, conditional on current head | Failed/unknown recording leaves target possibly committed and control unresolved; never repeat target operation |
| 9. Cleanup and publication | Original owner only; confirmed target/control facts, intact fence and all required result/deadline/owner checks | No new executable state; invalidate permits and resolve owned connections | No usable result on cleanup/publication uncertainty; history may remain |

The suggested sequence needs an explicit correction: **journal creation does not
permit the target operation**. Step 5 requires authority independently of the
decision/fence/pending rows. D already originates in genuine authority, not in a
journal constructor. Registration and duplicate exclusion are one local atomic
group, not separate partly committed states.

C1/C2/C3 are logical journal groups, not existing callable transactions. Existing
authority issuance and attempt write sets must not silently absorb them. Each
required control commit holds its actual target reservation until resolution.
If connections/reservations are released between groups, release both and reacquire
**control before target**, then repeat current checks. Never hold target while
waiting for a new control writer lock. The original lifetime and deadlines continue;
no renewal, retry loop or cross-phase observation permission is introduced.

## 4. Exact target-witness responsibility and blocker

Future writer must derive Z31 witness DATA internally from the actual authoritative
decision, exact committed pending event and complete actual business-effect evidence.
It uses the existing witness codec without extra fields. Its source authority,
pending predecessor and physical/runtime scope must match; recorded time is after
pending and before original expiry. It is a precommit record time, not proof of
the exact wall-clock commit instant.

**UNRESOLVED target mechanism:** no current replacement-authorized writer can
produce/verify the complete evidence represented by `effect_evidence_sha256` and
insert the witness atomically with those family effects. A future exact evidence
contract must specify full intended-versus-actual records/accounting, immutable
source/operation/manifest provenance, allowed target write set and independent
post-commit verification. Merely hashing a manifest, returning an issued count,
calling `validate_witness()`, or finding an inert target-entry marker cannot prove
those effects. Existing legacy receipt builders require a different authority/
claim/operation format and must not be invoked through synthetic legacy EXECUTING.

Witness insertion must occur within T before its only business-effect COMMIT.
All family effects and witness must roll back together. No witness-only commit,
post-business-commit witness repair, partial population, expiry extension or
quarantine shortcut is allowed. If witness encoding/verification/insertion fails,
rollback known uncommitted effects and record only supported failure/uncertainty
facts. An uncommitted witness is not success; durable validated witness plus full
actual evidence is required outside the transaction before control COMPLETED.

## 5. Control-journal transitions

Exact Z31 states/fields are retained; no new state or mutable head is introduced.

| Transition | Required evidence | Owner | Atomic with | Failure result |
| --- | --- | --- | --- | --- |
| Absent to DECISION_CREATED | Valid confirmed D/source graph, exact decision/genesis, no conflicts, F | Original eligible producer | Decision row, permanent unique exclusion, genesis and exact audit | No valid partial registration; known rollback or UNKNOWN |
| DECISION_CREATED to TARGET_PENDING | Exact decision digest/head, sequence 2, original current authority/F | Same original live producer | Start event and audit under control reservation | No second start; pending never reverts |
| Pending to TARGET_UNCERTAIN | Sanitized allowed classification, exact pending digest; observed uncertainty only | Original reporter or future authenticated factual resolver | One conditional event plus audit | If recording unavailable, pending prefix remains conservatively unresolved |
| Pending/uncertain to TARGET_FAILED | Exact positive original-manager no-commit evidence digest; no contradictory committed proof | Original manager/authorized factual recorder of that positive evidence | Terminal event and audit, expected head | Absent witness or process death insufficient; stay UNKNOWN if proof missing |
| Pending/uncertain to COMPLETED | Exact positive durable target witness and independently verified effects for D/pending, current recording permission | Original owner or outcome-only resolver | Terminal event and audit referencing exact witness digest | No success on absent/conflicting/unavailable evidence or uncertain recording |

No uncertain state becomes success merely because time elapsed, auth was refreshed,
the process restarted or SQL insert returned. A positive proven witness permits a
new immutable factual completion append, not rewriting/removing the uncertain fact.
Terminal states reject further events. No repeated uncertainty, pending retry,
CONTROL_COMMITTED state or new later-lifecycle AUTHORIZED evidence is added.

General audit linkage is required in the same control transaction as its journal
group. Z31's event digest is a correlation anchor, not an implementation of the
audit producer. **Exact audit action/subject codec, installed source validation
and fixed mutation/trigger proof remain UNRESOLVED integration definitions.**
Do not claim `inspect_rows()` alone verifies these external source/audit facts.

## 6. Duplicate fence and when it takes effect

The logical decision/manifest fence becomes durable at confirmed C1 commit, not
at UUID creation, successful encoding or an uncommitted INSERT. Existing source
authority exclusions already apply and are never weakened. C1 adds Z31's immutable
unique D/body digest and installation/target/operation and manifest relationships.
C2 irreversibly spends the single execution-start opportunity. Target witness
uniqueness is an independent last fence and commits with effects in T.

| Case | Mandatory behavior |
| --- | --- |
| Exact duplicate creation | Confirmed exact state may be inspected; never another producer/grant/start |
| Conflicting D/digest/scope | Hard failure; no overwrite/update/delete/replace |
| Concurrent producer | Serialize control, require exact expected head; only genuine original owner and one C2 winner |
| Retry after any spent start | Reject execution regardless of failure, success, uncertainty or timeout |
| Process restart/another ceremony | Current authenticated inspection only; cannot recover original owner/authority |
| New D for same logical operation/manifest | Reject global conflict; UUID/profile/generation/session changes do not bypass exclusion |
| Factual recovery | May resolve positive evidence once; cannot release fence or reauthorize business DML |

Fence retention is indefinite. Journal expiry/cleanup/backup rotation never deletes
history or reuses a logical decision. Restore/copy uncertainty fails closed under
existing installation/generation/identity controls; a missing row on a different
lineage proves neither no prior commit nor permission to execute again.

## 7. Transaction boundaries and coupling

Control transactions: C1 registration/genesis/audit; C2 pending/audit; C3 factual
terminal/audit. Failure/uncertainty reporting is a separate conditional control
transaction when needed. Target T contains only the separately authorized exact
business effect set, its approved supporting records and exactly one journal
witness. No journal-only helper may expose arbitrary target SQL or enable T.

An outcome-only resolver uses a separate authenticated **factual control transaction**
and validated committed target inspection. It writes no target data, issues no
grant, and cannot resume execution. Exact resolver permission/authorizer is not
implied by current admin status or by valid journal state.

No control/target co-commit is assumed. C1/C2 before T may leave excluded intent
with no effects. T before C3 may leave committed effects with unresolved recording.
Both are safe only by retained exclusion and no adoption/retry; neither is a
published success. Durable coupling is exact D/decision/pending/witness/effect
digests under validated sources, not temporal adjacency of commit calls.

## 8. Deterministic crash protocol

| Crash point | Durable interpretation | Allowed behavior |
| --- | --- | --- |
| Before journal creation | No confirmed new journal group; source authority may exist | Inspect source; no newly inferred grant or automatic replacement |
| After journal creation | C1/exclusion/genesis remain; no recorded start yet | No other ceremony adopts original owner; historical inspection |
| Before target mutation | C2 may be confirmed/spent; no reliable effect inference from process memory | Block retry; inspect exact committed facts |
| During target mutation | T uncommitted work is rolled back where known; observer still validates durable evidence | Never infer success from partial memory or failure from absent output |
| After target commit | Exact effects/witness may be durable even if control still pending | Positive verified evidence can support factual C3, never repeat T |
| Before target outcome recording | If witness absent before T commit, T must not validly commit; outcome recording cannot be deferred after business commit | Known uncommitted rollback; unknown status stays excluded |
| After target outcome recording | Witness may be uncommitted or durable; inserted is not committed | Require independent validated committed read |
| Before control outcome | Pending/uncertain may coexist with committed target effects | UNKNOWN/incomplete recording, not retryable failure |
| After control outcome | Exact terminal event may be durable; check target proof and source/audit integrity | Historical success/failure only; never restored live capability |
| Before result publication | Response/cleanup can fail after durable records | No adoption/re-execution; history may be inspected independently |

Crashes discard original process/thread/context permissions. Earlier confirmed
control/target commits are not undone by later rollback. A “probably succeeded”
response is forbidden. Missing evidence or an invalid source graph is UNKNOWN,
not authorization for repair, adoption, new D or target retry.

## 9. Uncertain commit and witness creation

| Uncertainty | Required response |
| --- | --- |
| Target commit | Poison live mutation path, publish no usable result; keep C1/C2 exclusions; inspect target witness plus complete actual effects under exact D/lineage |
| Journal C1/C2 commit | Do not start target mutation on an unconfirmed journal prefix. Inspect committed journal/audit/source by D; no blind append/retry |
| Control C3 commit | Target may already be committed. Reread exact terminal/head and target proof; no repeat business operation |
| Witness creation/encoding/INSERT | If known uncommitted, rollback entire T. If connection/commit outcome unknown, absence of local witness/result is not failure proof |
| Cleanup/publication | No usable execution result; historical positive evidence may later be recorded by an independently authorized factual resolver |

Positive original-manager confirmed rollback/no-commit evidence may support
TARGET_FAILED. Absence of witness alone cannot resolve an uncertain target to
failure. Positive durable witness/effect verification may support factual
COMPLETED even after old authority expiry; that is historical recording under
current recording permission, never permission to perform more business writes.
If factual recording or inspection is uncertain, remain UNKNOWN indefinitely.

## 10. Authorization separation

```text
journal creation != execution authorization
journal state != writer capability
journal recovery != reauthorization
target witness != authorization
```

Z31's codecs and SQL/row inspection prove bounded canonical DATA and local graph
relationships, not actual durable issuance, target effects, current authentication
or a live manager. All F gates and independent exact-action writer/admission remain
mandatory. No target witness producer may accept an arbitrary effect digest,
scope, manifest or authority supplied by a browser/caller/test provider as proof.
Journal outcome can deny use or describe facts; it cannot manufacture permission.

## 11. Concurrency and adoption

Control BEGIN IMMEDIATE and expected sequence/predecessor with immutable uniqueness
fence concurrent appends. Target writer reservation and unique D/operation/manifest
witness fence competing effects. Different nonconflicting operations still repeat
F after waiting for reservations; overlapping family/precondition conflicts reject.
Preserve BUSY/LOCKED without arbitrary retries or checkpoints.

Stale readers see a prefix only and cannot finalize from absent outcome. Concurrent
factual resolvers verify actual evidence under current reservations; one exact
terminal append wins, duplicate is inspection, conflict is an integrity stop.
No process-local lock replaces durable uniqueness. Cross-process or cross-ceremony
readers cannot gain the original owner's registration/authority from D, journal
head, source digests, prior credentials or a newly authenticated session.

## 12. Result publication

A usable original execution success requires all of: confirmed target transaction,
validated durable witness and complete effects, exact confirmed matching control
terminal/audit/source records, intact global duplicate exclusion, clean required
connection/reservation resolution, original-owner lifetime and all applicable
deadline/result checks, and no unresolved uncertainty.

Factual inspection may report positively verified historical facts with
`execution_authority=False` and `retry_authorized=False`; it cannot recreate a
lost usable execution result/capability. Every other result is absent or explicitly
non-successful/UNKNOWN. An ordinary successful API/SQL/codec return is insufficient.
The 120-second ceiling remains from actual authority creation, not journal
registration, target commit or publication. No timing feasibility is asserted.

## 13. Implementation boundary

| Category | Exact status |
| --- | --- |
| Contractually defined | Z30 identities/states/fencing/no-retry/factual-resolution principles; Z31 exact inert DDL/codecs/reader fences; Z32 required local write groups, commit ordering, fresh checks, failure/publication rules |
| Requires new complete integration contract | Genuine replacement-owner source/authority registration and exact mutation permits; journal/source audit action/linkage/proof; complete business-effect evidence/verifier and target witness atomicity; outcome-only resolver permission |
| Implementation-ready now | Existing inert DATA/DDL only. No live producer, witness writer, migration, resolver or executor is implementation-ready under this incomplete contract |

Specific current blockers are observable in
[`runtime_decision_outcome_journal_schema.py`](../src/review/recognition/runtime_decision_outcome_journal_schema.py)
(detached effect digest, no source/transaction authority),
[`writer_boundary.py`](../src/review/recognition/writer_boundary.py)
(exact distinct writer/legacy authority), and
[`runtime_execution_coordinator.py`](../src/review/recognition/runtime_execution_coordinator.py)
(fixed existing phase mutation permits). None may be widened merely to make a
producer call succeed.

## 14. Exact next boundary and validation

**BLOCK Z32: target witness production/business-effect verification remains the
exact target-side blocker.** No target-specific behavior is invented. A complete
authorized owner and exact target effect/witness/audit integration contract would
need explicit approval together before live producer work. This document does
not commission an implementation or another performance investigation.

Only this document is created. Validate `git diff --check` and document whitespace/
local links. No pytest, Z18, T, broad suite, code/schema/migration, producer,
authority, target data/DML/DDL, writer/execution capability, production/hosted
access, commit or push. No authority lifetime or security semantics change.

## 15. Production blocks

PRODUCTION AUTHORIZATION: BLOCKED

PRODUCTION EXECUTION: BLOCKED

PRODUCTION ACTIVATION: BLOCKED

WRITER CAPABILITY: BLOCKED
