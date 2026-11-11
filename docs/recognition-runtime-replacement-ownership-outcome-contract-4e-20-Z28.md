# 4e-20-Z28: replacement ownership, validation, fencing and outcome decision

## 1. Z27 conclusion and review disposition

[Z27](recognition-runtime-replacement-security-model-4e-20-Z27.md) selected no model
ready for contract approval. This review addresses only its transaction-owning
executor candidate, not another broad candidate comparison.

**Decision B: one specific security gap remains — an authoritative, crash-stable
cross-store execution decision identity coupling global duplicate exclusion to
the target's actual committed outcome.** Existing storage/readers do not provide
that property for the replacement runtime. Its uniqueness and outcome-correlation
facets are one missing end-to-end property, not permission to invent several new
fences. The proposed owner/validation obligations below do not close it.

Stop the architectural chain. No implementation, further optimization, timing
investigation or new review slice is proposed by this result. The 120-second
ceiling and all existing production gates remain unchanged.

## 2. Complete proposed ownership boundary

Define exactly one **replacement transaction-owning executor**, as a conceptual
new component in this candidate model, not an existing owner relabeled or widened.
It originates one exact operation decision in one process/thread/context. It owns
all its transaction lifecycle calls and publishes only its own confirmed result.
This is a design obligation; no module/API/registration is implemented here.

| Responsibility | Required ownership rule |
| --- | --- |
| Authentication | Accept only genuine eligible existing owner primary/session references; use authoritative current auth/MFA/scope kernels. An activated credential issuer is not manufactured by this owner. No earlier preparation authentication grants permission. |
| Consent/authority | Independently validate fresh exact-subject TOTP/one-use consent. Receive no imported authority, attempt, continuation or preparation permit. Only after final admission may it originate a local grant for one exact operation, at most 120 seconds and clipped by existing credential/consent expiry. |
| Operation/scope | Derive exact operation/event/preparation/manifest/population, proposal/ACK, effective approval, installation/target/generation/binding/owner/auth/MFA epochs through authoritative readers. Supplied lookup IDs/digests are expectations only. |
| Runtime profile | Actual current enrolled runtime identity and finalized G+2 profile/generation/binding continuity; no caller profile or console identity override. |
| Activation | Current independent activation incarnation/ledger and exact grant binding. Binding `production_state` alone is not activation authority. |
| Process/thread/context | Private original owner registration, exact PID/Thread/identifier/context and paired clock; no public constructor, SQL handle, pickle/import/adoption interface. Process/thread/context loss destroys local authority permanently. |
| Reservations | Control BEGIN IMMEDIATE precedes target BEGIN IMMEDIATE/query-only. Prove actual connections, transactions, mode and epochs at every use. No inherited reservation token from preparation. |
| Transactions/target | Own known rollback, commit and cleanup exclusively. Only a separately approved exact-action permit could enable controlled target writes; no arbitrary SQL/target/manifest selection. Control reservation remains held through target mutation/commit checks wherever the eventual protocol requires it; earlier control commit would require immediate new reservation and full fresh validation, never inherited validity. |
| Result | Non-adoptable original-owner result only after confirmed target outcome, confirmed corresponding control recording and required cleanup. An uncertain/expired/poisoned owner publishes no usable success. Historical inspection is not that result. |

No preparation artifact is accepted as authority. Even immutable request facts
must be freshly resolved and compared with the actual current subject. Live grant
possession alone cannot bypass required current checks or survive a changed
security scope. This proposed owner grants no authority to current components.

## 3. Fresh-validation proof obligations

Freshness points: **V0** inside newly acquired reservations before any proposed
control grant; **V1** immediately before enabling target mutation; **V2** after
permitted writes and before committing the corresponding effects; **V3** after
commit/reacquisition before result publication. These labels name requirements,
not newly callable validators or authorization to reuse V0 at V1/V2/V3.

The replacement executor is the sole validation owner in every row. It must call
authoritative kernels through genuine reviewed adapters; no cached complete
admission or copied validation algorithm is accepted. New adapters are not
implemented by this contract review.

| Check | Source of truth | Freshness point | Owner | Required before mutation? |
| --- | --- | --- | --- | --- |
| Authentication/consent | Current owner/access, primary/session/runtime scope, MFA epoch/replay/throttle, exact step/confirmation and use/expiry | V0, V1, V2; deadline/scope also V3; consume consent only atomically with grant decision | Executor, existing genuine auth/consent kernels | YES; no prepared credential or reused confirmation |
| Exact scope | Durable current operation/manifest/population and installation/target/generation/profile/binding/owner/epochs | V0/V1; actual unchanged intended scope at V2/V3 | Executor/current scope and operation readers | YES |
| Proposal/ACK/approval | Exact pairing, v2 approval and effective invalidation/history | V0/V1/V2; reject altered scope at V3 | Executor/current proposal/approval readers | YES |
| Activation | Independent current ledger/incarnation and grant binding | V0/V1/V2/V3 | Executor/activated readers | YES |
| Physical identity | Actual hostname, resolved control/target paths/devices/inodes, schema/fingerprint | Actual observations at V0/V1/V2 and after reacquisition at V3 | Executor/strict identity kernels | YES; never inferred from SQL locks |
| Emergency stop | Current global stop and operation blocks | V0/V1/V2 and current use at V3 | Executor/authoritative stop readers | YES |
| Dependencies | Current dependency graph/state and full target population preconditions | V0/V1; V2 must verify authorized actual effects without declaring mutated preconditions unchanged | Executor/shared dependency and manifest readers | YES; no evidence-only ready flag |
| History/audit | Complete current binding/profile/authority/claim/audit graph | V0/V1; exact permitted actual suffix and global integrity V2/V3 | Executor/history/schema readers | YES |
| Claim state | Current full inventory/disposition and selected/global exclusions, including legacy/old-runtime conflicts | V0/V1; new exact decision must preserve exclusions at V2/V3 | Executor/inventory readers | YES |
| Control state | Current protected baseline, exact changes, global FKs, immutable graph and actual consent use | V0/V1; actual complete write proof V2/V3 | Executor/schema and protected-state readers | YES |
| Schema/migrations | Exact installed packages and current migration audits/predecessors/binding/G+2 relationships | V0/V1/V2 and after any new reservation V3 | Executor/manifest and transition readers | YES; schema inventory is not migration validity |
| Readiness | Current protected policy, rehearsal/config evidence and complete inventory | V0/V1/V2; required post-boundary checks V3 | Executor/approved private readiness interface | YES |
| Reservation | Actual original owner/connections/transactions/query mode/epochs | Every borrowed use and V0-V3 | Executor only | YES; loss rejects |
| Deadline | Authoritative paired clock, no rollback/anomaly; all original consent/auth/grant bounds | Every required use, especially V1/V2 and publication V3 | Executor only | YES; equality expired; no extension/renewal |

No prior-auth schema inventory crosses into this executor. Any inventory reuse
would need its own already approved exact local continuity eligibility; absent
that, read fresh. No additional observation reuse is proposed here.

This table preserves the required predicates but does not claim a runnable
replacement post-mutation validator already exists. Exact effects/outcome graph
verification at V2/V3 depends on the missing execution-decision/outcome property
in section 6; a precondition cannot be blindly reread as if authorized effects
had not happened. No security predicate is waived to bridge that gap.

## 4. Duplicate-fencing model and exact missing identity

The required logical-operation uniqueness domain is the authoritative tuple
`(installation_id, target_id, operation_id)`, with exact `operation_sha256` and
`writer_manifest_sha256` binding. A conflicting operation reusing a previously
committed manifest must also be excluded within the same installation/target.
These names are existing scope fields, not a new schema or codec. Attempt ID,
request UUID, session, profile, generation or activation must not become the
sole uniqueness key: changing them cannot permit executing the same logical
operation/manifest twice. They remain exact scope checks; no cross-generation
execution/adoption is allowed.

**The durable enforcement of this replacement identity is UNRESOLVED.** In the
current repository:

- Control runtime authority storage binds operation/manifest/consent; attempt
  storage uniquely binds an attempt to its authority, under the old producer.
- Target `recognition_runtime_execution_entries` has unique attempt, operation,
  authority and manifest identifiers, but is explicitly TARGET_ENTRY_CREATED
  metadata, not a business-effect commit record or replacement decision fence.
- `recognition_private_operations` records the business manifest and family
  effects. Its current historical writer authorization is not the proposed
  replacement authorization or control-decision provenance.
- Legacy claim/seal/audit and production receipt readers bind legacy/local
  execution formats; their integrity does not make them a replacement-runtime
  completion protocol. Do not synthesize legacy EXECUTING or convert old claims.

Sources:
[`runtime_target_entry_storage.py`](../src/review/recognition/runtime_target_entry_storage.py),
[`permanent.py`](../src/review/recognition/permanent.py),
[`execution_schema.py`](../src/review/recognition/execution_schema.py),
[`production_receipts.py`](../src/review/recognition/production_receipts.py).

The exact replacement attempt, target-entry and single-winner relationships must
be enforced by that same durable decision identity, not independent process flags
or an invented new fence. Existing fences must continue rejecting conflicts;
none currently supplies the missing replacement outcome meaning. No UPDATE,
DELETE, expiry-based reuse or unique-key collision replacement is authorized.

## 5. Target/control outcome protocol: required outcomes, not an invented commit

Control and target are separate databases. The table is the required publication/
failure policy for the candidate, not a claim that its missing decision records
or commit protocol exist. “Pending/excluded” denotes a conceptual non-success
condition; it is not a new stored state name or a resumable credential.

| Outcome | Control state | Target state | Published result | Recovery |
| --- | --- | --- | --- | --- |
| Success | Confirmed exact final decision and confirmed outcome recording linked to target proof | Confirmed complete atomic family effects plus exact target outcome/fence | Success only after both required confirmations and cleanup | Historical inspection only; no further execution |
| Validation failure | No successful grant; known uncommitted work rolled back, existing safe denial behavior retained | No effects | Exact sanitized rejection; no usable capability | No automatic retry/adoption |
| Target mutation failure | Any earlier confirmed decision stays excluded, not completed; uncommitted current changes rolled back where known | Entire uncommitted family mutation rolls back | Failure, no usable result | Read-only inspection if any outcome uncertain |
| Control commit failure before target mutation | Failed/unknown decision, never assumed usable | No authorized effects may start | No usable success/capability | Stop; inspect exact durable control state |
| Control commit failure after target commit | Final control recording failed/unknown; prior exclusion must remain authoritative | May be confirmed committed | No usable success; no re-execution permission | Inspect target/control; missing completion is not rollback |
| Target commit failure | Control must not say completed without target proof; pending/excluded if prior decision exists | Rolled back only when known; otherwise UNKNOWN | No success | Stop, read-only inspection |
| Uncertain commit in either store | Known facts only; no speculative completed state or renewed grant | Known facts only; no absent-row inference across a different identity/restore | No usable result | UNKNOWN blocks automatic execution/adoption |
| Process crash | Confirmed prefixes remain; uncommitted writes resolved by SQLite, not assumed from memory | May be no effects, uncommitted effects or committed effects depending on crash point | No restored process-local capability/result | Authenticated durable inspection; no resume |
| Deadline expiry | Reject grant/use, preserve committed facts; do not restamp or reissue | Roll back known uncommitted effects; in-flight commit status must be inspected/confirmed | No usable execution success after required deadline checks fail | No retry/adoption; inspect uncertain commit |

Where the table needs a linked target outcome/fence and stable control exclusion,
its enforceability is **UNRESOLVED** because that one property is missing. This
table does not claim to have solved it by naming the desired states.

## 6. Atomicity boundary and the single security gap

Within target, approved family effects must be all-or-nothing together with a
validated decision-bound duplicate/outcome record. Within control, grant/one-use
consent/decision/audit must resolve atomically under exact current validation.
Publishing completion must require confirmed target evidence and confirmed
corresponding control recording. Memory registration/cleanup cannot be made
SQLite-atomic by calling both stores from the same Python object.

Strict instantaneous target/control co-commit cannot be claimed. Whichever store
commits first creates a possible crash prefix:

1. Control first: a durable decision may exist with no target effects. It must
   exclude competitors without authorizing another process to adopt the grant.
2. Target first: committed effects may exist before control records completion.
   A target-local proof must prevent re-execution despite missing control success.

Thus a temporarily unmatched outcome can be explicitly UNKNOWN or unresolved
recording; it cannot be called synchronized success. If the requirement instead
demands that both stores always contain simultaneous completion, the separate-
database premise cannot provide it through ordinary local commits.

**Missing property:** an authoritative, crash-stable execution decision identity
whose durable single-winner exclusion and target-atomic committed-effect proof
remain correlatable under the exact enrolled installation/target and every
permitted restore/generation transition, without becoming a resumable authority.
Its safe outcome readers would have to distinguish “no effect,” “effect committed,”
“recording incomplete” and UNKNOWN without authorizing a retry. Existing metadata,
business-manifest and legacy seal facts do not jointly establish this property
for the proposed replacement owner.

This is the exact new security contract that would be required; this review does
not invent its tables, evidence codecs, transitions, repair permissions or commit
ordering. Replacing that proof with a request ID, timeout, unique metadata marker
or assertion that a family writer is atomic would not close the gap.

## 7. Crash and uncertainty protocol

| Owner dies | Required interpretation |
| --- | --- |
| Before validation | No live grant or execution; no capability survives |
| After validation, before grant/mutation | Validation is not durable permission; no other owner may use it |
| Before target mutation, after some control commit | Historical decision may exist; no automatic adoption or renewed authority; duplicate exclusion must remain |
| During target mutation | Known uncommitted transaction rolls back atomically; process disappearance alone is not a committed-outcome proof |
| After target mutation but before its commit | DML executed is not DML committed; inspect durable evidence, never infer from memory |
| Before control commit | Distinguish initial decision commit from later outcome recording; target may be untouched or already committed, depending on the actual protocol prefix |
| After control commit | A grant commit is not completion; a completion record requires actual correlated target proof |
| Before result publication | Cleanup/publication may fail despite durable facts; do not recreate a live success capability from those facts |

On uncertainty, stop and publish no usable success. No automatic recovery,
adoption, expiry-driven fence release or retry is allowed. The current owner
loses all permits on process/thread/context loss or poison. A read-only inspector
may report exact historical facts, but cannot resolve missing outcome evidence
by guessing. Without the section 6 property, the candidate cannot fully distinguish
all prefixes, so it is not ready for approval.

## 8. Last-validation to outcome gap

| Mutable condition | Same transaction/lock protects what? | Required action through mutation/commit |
| --- | --- | --- |
| Control auth/owner/MFA, activation, approval/ACK, stop, claims/history/control | Holding the actual control writer reservation prevents ordinary competing control writes on that database | Recheck expiry/current scope and actual own writes; releasing/reacquiring control invalidates prior eligibility and requires full fresh validation |
| Target owner/epochs/dependencies/population | Actual target writer reservation prevents ordinary competing target writers, not external filesystem changes | Validate current preconditions before DML; verify exact permitted effects/graph afterward; fail on unexpected effects |
| Physical hostname/path/device/inode/schema | No SQL lock guarantees external physical continuity | Repeat actual strict observations at required use/precommit/reacquisition checks; observed mismatch fails closed. Never claim atomic filesystem continuity from earlier validation |
| Migration/profile/schema state | Database locks protect ordinary row/DDL changes while actually held; owner/epoch changes break eligibility | Fresh current relationship/package validation; no prepared migration result; revalidate after any boundary |
| Reservations/connection/query mode | Only exact genuine owned connection/transaction/epochs establish current eligibility | Reject replacement/loss; controlled mode transition invalidates old views and requires fresh admission |
| Time/auth/consent/authority expiry | Locks do not stop time | Fresh authoritative clock at required use and before commit/publication; no deadline extension or interrupted-commit assumption |
| Own writes/new decision and target effects | Locks do not make earlier graph validation cover new rows or earlier preconditions describe effects | Verify exact actual changed graph and target outcome under section 6's missing contract; do not reuse initial admission as proof |

These are required observation/check boundaries, not a guarantee that a path
cannot be externally replaced in the interval after a stat, or that an in-flight
SQLite commit can be canceled at a clock tick. Any claim of stronger continuity
or hard real-time commit completion is unsupported and is not used to approve
this candidate. Deadline/identity failure detected after a possible target commit
publishes no usable result and enters the same excluded outcome-inspection policy.

## 9. Decision B and end of architectural chain

**One specific security gap remains:** the replacement's authoritative crash-stable
execution decision identity with durable global exclusion and target-atomic outcome
correlation, as defined in section 6. It prevents approval even with the owner
and all fresh checks constrained as above. No assumption that existing unique
rows, metadata or legacy receipts collectively provide it is permitted.

This does not prove the model fundamentally impossible; it establishes that the
required end-to-end property is not supplied or defined by current guarantees.
Choosing local commit order alone cannot supply it. No new fence or outcome
schema is invented to make the answer A.

**Stop the architectural chain here.** No next review/optimization/micro-slice,
timing run, executor, target-entry producer or writer implementation is proposed.
No replacement model, authority path or outcome protocol is approved.

## 10. Implementation boundary

There is none because decision A was not reached. Runtime execution remains
unavailable. Existing ownership, strict identities, authority/attempt/metadata
meanings, schema and 120-second policy remain unchanged.

## 11. Validation and production blocks

Only this document is created. Validation: `git diff --check`, document whitespace
and local links. No pytest, Z18, T, broad suite, code/schema/migration, production
or hosted access, authority/executor/target state, target DML/DDL, writer/execution
capability, commit or push.

PRODUCTION AUTHORIZATION: BLOCKED

PRODUCTION EXECUTION: BLOCKED

PRODUCTION ACTIVATION: BLOCKED

WRITER CAPABILITY: BLOCKED
