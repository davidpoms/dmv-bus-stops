# 4e-20-Z35: non-adoptable original-runtime mutation-grant review

## 1. Z34 blocker and disposition

[Z34](recognition-runtime-target-mutation-commit-attestation-contract-4e-20-Z34.md)
left the original-runtime family-effect-plus-witness mutation grant unresolved.
This review concludes **B: one specific primitive remains missing — an explicit
original-authority-to-target-action delegation rule**. It must establish that the
genuine original activated authority owner is entitled to originate exactly this
transaction-local mutation grant. Existing profile/ownership/digest checks cannot
create that entitlement by themselves.

The proposed restrictions below define what such delegation would have to preserve,
not a new grant, constructor, owner authorizer exception or accepted writer type.
No authority semantics or 120-second lifetime changes. No implementation, target
mutation, schema/migration or next performance investigation is authorized.

## 2. Original-runtime identity

Originality is a conjunction, not a copied durable identifier or PID comparison:

| Existing evidence/mechanism | What it establishes | What it does not establish |
| --- | --- | --- |
| Enrolled runtime profile/current binding | Exact installation/target/generation/profile/owner and actual worker host/paths/devices/inodes/schema scope through current identity checks | Unique process instance, hardware attestation or permission to mutate |
| Private original coordinator registration | Exact original outer/context, original issuance phase/notice and continuation, live object provenance | Any new target action not permitted by its current authorizer |
| PID plus exact Thread object/identifier | Original execution locality when checked with private registry and context identity | Security against arbitrary trusted-host/code compromise, or originality from PID equality alone |
| Current authentication/consent | Genuine current owner credentials/MFA/epochs, exact consent subject and deadlines | Writer permission merely from login, TOTP or a confirmation flag |
| Current independent activation | Exact incarnation/sequence/digest matching authority scope | General authorization of every old operation or another incarnation |
| Original authority/D | Exact immutable authority ID/body digest and current original live issuance relationship | A bearer mutation permit or permission to restore an owner from rows |
| Exact owned reservations/connections/transactions | Actual current manager ownership and epochs, control before target, required modes | A transferable lease, external filesystem continuity or authority after commit/rollback |

Sources:
[`runtime_execution_coordinator._Outer.check/_require_outer/_continuation_entry`](../src/review/recognition/runtime_execution_coordinator.py),
[`runtime_validation`](../src/review/recognition/runtime_validation.py),
[`authorization.target_identity`](../src/review/recognition/authorization.py).

These mechanisms suffice to identify an original live owner within the existing
trusted-code/host model. No new runtime-profile attestation key, hostname allowlist
or remote identity witness is needed or invented. They do not supply the missing
delegation of the target action. No existing process/thread check is asserted to
resist malicious arbitrary memory manipulation by trusted host administrators.

## 3. Exact smallest proposed grant scope

The only candidate is an internal opaque, nonserializable, transaction-local,
one-shot permit, usable through a fixed family mutation entry point rather than
SQL or connection access. It would have to bind all of:

- D = exact source authority ID/body digest and genuine original live owner;
- one exact runtime operation UUID/digest, family, frozen manifest/population,
  source event/preparation and exact proposal/ACK/effective approval;
- installation/target UUID, enrolled actual target physical identity/schema,
  G+2 profile/generation/binding/owner/auth/MFA epochs and independent activation
  incarnation/sequence/digest;
- exact actual target connection, open transaction, reservation identity/epoch,
  controlled query mode and original PID/Thread/context/phase registration;
- exact confirmed journal decision and sole pending-start event, with permanent
  operation/manifest exclusion and no conflicting old/runtime/legacy records;
- the entire existing atomic First Look or Geography family effect set and exactly
  one Z31 witness derived internally from those effects and that same D/pending;
- original issue/expiry and every earlier applicable credential/consent deadline.

The grant cannot freeze the future witness's byte digest before effects/time are
known. It must bind the **unique permitted derivation**: exact Z31 shape, same D/
decision/pending, actual verified effect-evidence digest, and recorded time inside
the existing deadline. No caller-supplied alternate witness/effect digest is allowed.
Actual witness and whole write set must be verified before commit and afterward.

No alternate decision, target, manifest, transaction, ceremony or process can be
selected. No raw handle, cursor, SQL, commit/rollback, schema write, arbitrary row
write, lifecycle mutation or recovery method is exposed. This is a scoped design
requirement, not a new concrete type or API that current code accepts.

## 4. Creation authority and no bootstrap

Required fresh checks at the prospective grant point:

| Predicate | Current source / requirement |
| --- | --- |
| Authentication/consent | Genuine original owner primary/session/runtime-auth and current MFA/epochs/revocation, protected TOTP/exact one-use consent subject, all deadlines; never a journal token |
| Operation/approval/ACK | Current durable exact operation/event/preparation/frozen manifest, acknowledged proposal, effective approved state and invalidation history |
| Activation/profile/scope | Current independently validated activation incarnation and enrolled finalized G+2 identity/profile/generation/install/owner/binding/epochs |
| Physical identity | Actual host/resolved paths/devices/inodes/schema/fingerprint for target/control at all required boundaries; no assumed filesystem continuity |
| Stop/dependencies/readiness | Current clear emergency stop/operation blocks, authoritative dependency/precondition/whole-population manifest recheck and protected readiness |
| Claim/history/control | Complete current graph/exclusions/audit/migration/profile relationships, protected baseline and exact decision/pending integrity |
| Reservations/time | Exact original registrations, actual connections/transactions/modes/epochs and paired clock strictly before every expiry |

Only a creator **already entitled by a separately approved target-action delegation
rule** could issue the grant after these checks. The grant cannot make its own
creator entitled, and a successful validator cannot be promoted into an issuer.

No current creator possesses that delegation for this transaction:
coordinator target remains query-only; metadata authorizer permits its marker only;
activated observation is read-only; existing writer leases accept distinct exact
legacy/local/disposable authority. Their source authorization is not transferable.
`writer_boundary.acquire()` rejects unsupported capability types and consumes its
existing leases only under their existing contract. Those checks remain unchanged.

Therefore **creation authority is UNRESOLVED**. Possession of an original runtime
authority and matching D is necessary context, not sufficient existing permission
to mint this new transaction grant. No grant implementation is ready.

## 5. Non-adoption argument and scope of proof

| Event/attempt | Required rejection mechanism |
| --- | --- |
| Process restart or another process | Private original registry/object/outer/issuance lineage absent; matching PID/host/profile/D cannot recreate it |
| Thread change | Exact original Thread/identifier and active context checks fail |
| Connection replacement | Exact connection object and manager registration no longer match |
| Transaction/epoch/mode change | Old permit invalidated; no rebinding to a new reservation or target transaction |
| Runtime profile/generation/activation change | Fresh current scope/incarnation must match original grant; changed values reject, not refresh |
| Cross-ceremony recovery | New authentication may inspect facts only; cannot inherit old original-owner authority |
| Copied IDs/stale rows | Durable source is historical DATA; it cannot instantiate private live registration |
| Replayed grant material | No supported export/import/copy/pickle/public constructor; one-shot private registration already spent/invalid |

Existing private provenance mechanisms illustrate how a future scoped object could
be non-adoptable in the trusted-code model, but no mutation-grant registry currently
exists. This is not a claim that inert codecs already enforce live non-adoption,
or that Python visibility is a cryptographic boundary. The missing primitive is
delegation, not a reason to invent a new hardware/process identity scheme.

## 6. Non-replay and durable fencing

Two distinct mechanisms are required: consume the private local permit before its
only write invocation, and enforce permanent durable decision/operation/manifest
exclusion independently of the local object's state. A process-local consumed
flag alone does not prove single execution across crashes.

The defined Z30/Z31 journal semantics provide one D/body digest, unique installation/
target/operation and manifest identities, one pending start, and one target witness
committed with the whole effect. Their current definitions are inert and not
installed; no live fence implementation is claimed. Original authority/attempt/
entry/legacy conflicts remain exclusions, not migration/adoption inputs.

After successful, known failed or uncertain commit, consumed permit never becomes
available again. A rollback resolves known target writes, not the spent start or
another grant. Process restart cannot reset durable exclusion. New decision/session/
generation/profile IDs cannot evade logical operation/manifest conflict. No deletion,
TTL release, terminal-failure reuse or automatic reauthorization is defined.

## 7. Atomic family-effect plus witness transaction

The required prospective sequence is:

```text
actual control reservation then exact target reservation
  -> complete current admission and family preconditions
  -> genuine independently authorized local grant, consumed once
  -> existing exact whole-population family effects
  -> complete actual effects/accounting verification
  -> exact D/pending/effect-bound Z31 witness inside the same target transaction
  -> actual write-set and required fresh final checks
  -> manager-owned target commit
  -> positive committed-target inspection and corresponding control recording
```

Business rule/operation/family rows and exactly one witness must be atomically
committed in **one target transaction on the owned connection**. Existing read-only
`permanent._prepare` and outcome integrity checks define the family correctness
requirements; they do not grant permission to perform writes. Source credit,
frozen geography evaluation and atomic population accounting remain unchanged;
no active per-item quarantine or Explorer mutation is allowed.

SQLite can provide this local atomicity in principle. The actual runtime grant/
authorized mutation boundary remains UNRESOLVED; no target mechanics or new SQL
are invented. Current unleased `finalize()` commits itself; adding a witness
afterward is forbidden. Fabricating a legacy lease to avoid that commit is forbidden.
No cross-database atomicity is claimed for later control outcome recording.

## 8. Grant lifecycle

These are conceptual local lifecycle terms, not new journal/table enums.
There is no durable executable grant or adoptable continuation added here.

| Transition | Owner / authority | Durable evidence / transaction | Invalidation and retry |
| --- | --- | --- | --- |
| ABSENT to BOUND_UNUSED | Only an already-delegated original target-action creator after full fresh checks; currently UNRESOLVED | Exact source D and confirmed pending/fence; no durable transferable grant | Failure publishes nothing; copied evidence cannot create one |
| BOUND_UNUSED to CONSUMED | Same genuine original owner/connection/transaction; current scope and deadlines | Private one-shot consumption plus existing permanent pending/fence; target still uncommitted | Spent before first DML; never reset, including if DML never starts |
| CONSUMED to COMMIT_CONFIRMED | Same original owner; complete effects/witness/actual write and fresh final verification | Target effects and witness commit atomically; positive independent committed verification | Permit ends; no further business writes; control recording separate |
| BOUND_UNUSED/CONSUMED to INVALID_FAILED | Expiry/revocation/owner/reservation loss or known failure | Rollback known uncommitted work; positive no-commit fact may be recorded only by authorized factual path | No new permit/retry from failure |
| BOUND_UNUSED/CONSUMED to INVALID_UNCERTAIN | Unknown commit/connection/cleanup outcome | Retain durable exclusions and exact pending prefix; uncertainty may be appended | No usable result or retry; only independent factual inspection |
| Any state to CLOSED | Owner context exit/thread/process/transaction lifetime ends | Historical source/journal facts may remain | No resurrection, adoption or fresh grant via old identity |

Authority lifetime is the intersection of the original at-most-120-second window,
all earlier auth/consent expiries and the exact owner/transaction lifetime.
Creation/publication/journal/witness timestamps never restart the clock. No
contract here permits the creator to extend existing auth or authority validity.

## 9. Crash and uncertain commit

| Crash point | Grant state | Family effects | Witness | Recovery |
| --- | --- | --- | --- | --- |
| Before consumption | Lost with original owner; not restorable | None known from this invocation | None | Inspect durable prefixes; no imported/reissued permit |
| After consumption | Permanently unavailable | None or uncommitted work | Absent/uncommitted | Keep pending/fence; no retry |
| During family effects | Lost/spent | Whole transaction uncommitted unless commit later actually confirmed | Not yet a durable outcome | Known rollback only; read exact durable facts, never process memory |
| After effects before witness | Lost/spent | Must still be uncommitted | Absent | Commit forbidden; unknown outcome stays blocked rather than repaired |
| After witness before commit | Lost/spent | Uncommitted | Same uncommitted T | Inserted witness is not success; inspect actual committed target |
| After target commit | Spent/closed | May be confirmed complete | Must commit in same T for valid positive outcome | Verify exact durable witness/full effects; no re-execution |
| Before control outcome | Spent/closed | Target may be committed | Actual proof may exist despite control pending | Factual recording only; missing control result is not permission |

Uncertain commit poisons live grant use and publishes no usable execution result.
An independently authenticated outcome-only inspector validates intended target/
control identity/schema/restore lineage, D/source/approval/consent history, exact
pending, committed witness and complete actual records. Positive proof can establish
historical commit and support exact factual control completion. Original positive
no-commit evidence may establish failure; absent witness, failed response or process
exit cannot. If proof, identity or inspection is uncertain, remain UNKNOWN.

UNKNOWN is terminally non-retryable for execution, even if facts can later be
resolved. No new decision for the blocked logical operation/manifest is permitted
merely to bypass uncertainty. Current journal history and source exclusions stay
effective indefinitely. Any manual correction/retirement remains outside this
grant; it cannot be exposed as a recovery method on the permit.

## 10. Security separation

```text
mutation grant != general writer capability
mutation grant != reusable authority
mutation grant != recovery authority
mutation grant != journal authority
mutation grant != target witness
```

Only a previously authorized exact transaction could use the hypothetical permit.
It grants no control journal mutation/repair or resolver privilege, and a witness
or journal does not mint it. Once consumed it cannot be used to perform another
effect, certify an unrelated outcome or extend authority. Fresh checks remain
independent at required grant/use/commit boundaries; actual physical identity can
change outside SQLite and must be reobserved. Required checks are not optimized
or cached across contexts. No guarantee of real-time cancellation inside SQLite
commit is invented; deadline/result failure after a possible commit stays excluded
and subject to factual inspection, not usable success or retry.

## 11. Existing-model assessment B

| Existing guarantee | Supported contribution | Limit |
| --- | --- | --- |
| Authority | Exact immutable intended decision and original consent/deadlines | Does not currently authorize a new target-grant issuer by itself |
| Runtime profile | Strict current enrolled runtime/target scope | Not live process authority or delegated target privilege |
| Original registration/reservations | Non-adoptable live provenance and manager ownership pattern | Current target authorizers remain query-only or metadata-only |
| Target transaction/family contract | Exact atomic historical mutation and integrity semantics | Existing writer authorization accepts different fixed capability/claim paths |
| Journal/witness contracts | Permanent outcome/duplicate correlation semantics and inert codecs | No installed live fence, writer producer, grant source or execution permission |

**B: the explicit original-authority-to-target-action delegation rule remains
missing.** It must establish which already-authorized original owner may originate
the exact family-effect-plus-witness transaction permit, under what fixed privilege,
without promoting a read-only/metadata/legacy context or bootstrapping a new owner
from DATA. Existing source checks cannot be combined into an implied grant.

This is not a proof that non-adoptable authority is impossible under the trusted
host model (C). It is a precise failure to establish creation authority from the
existing contracts. The other restrictions above are requirements of any eventual
grant, not a grantor or capability implementation. No security primitive is
invented simply to reach assessment A.

## 12. Stop and validation

**Stop the architectural chain.** No further performance or implementation slice,
executor, grant API, journal migration, target mutation or timing run is proposed
by this review. There is no implementation-ready mutation privilege to activate.

Only this document is created. Validate `git diff --check` and document whitespace/
local links. No pytest, Z18, T, broad suite, code/schema/migration, grant or mutation
permission, target DML/DDL, executor, production/hosted access, commit or push.
The 120-second ceiling and existing authority/legacy semantics remain unchanged.

## 13. Production blocks

PRODUCTION AUTHORIZATION: BLOCKED

PRODUCTION EXECUTION: BLOCKED

PRODUCTION ACTIVATION: BLOCKED

WRITER CAPABILITY: BLOCKED
