# 4e-20-G4: original-holder atomic enforcer security-model approval gate

## 1. G3 blocker and decision scope

[G3](recognition-runtime-g1-atomic-target-effect-witness-enforcement-decision-4e-20-G3.md)
found that SQLite atomicity and existing family integrity readers do not supply
an authorized runtime consumer for the exact family-effect/witness action.

**Decision A: NEW SECURITY CAPABILITY APPROVED FOR IMPLEMENTATION DESIGN.**
This document defines the new consumer's normative security model. It does not
find that the consumer already exists, approve implementation, confer deployment
permissions, establish runtime feasibility or unblock production. A later design
must demonstrate the concrete enforcement obligations below before code is
authorized. Failure to represent any obligation blocks that design.

## 2. Capability definition and trust assumptions

The enforcer is a trusted internal transaction owner for one prospectively
authorized G1 action. It alone may consume that exact action grant, regenerate
the supported historical family preconditions, write the complete fixed family
effect, verify actual records, insert its internally derived decision-bound
outcome witness and commit that single target transaction.

| Concept | Meaning and limit |
| --- | --- |
| Source authority | Original confirmed activation-bound authority; only new sources satisfying G2 policy/consent/audit provenance may possess G1 eligibility |
| Action grant | One issue-time-bound original-holder-only exercise of G1; no right to grant again |
| Enforcer capability | Private live registration binding the one grant to the exact manager-owned transaction and action; no caller SQL or raw handle |
| Target mutation | Fixed supported First Look or Geography historical finalize effects only |
| Witness creation | Inseparable attestation of those actual verified effects and exact decision/pending in the same target transaction |
| Journal recording | Separate control-side factual decision/start/outcome protocol; not permission conferred by the enforcer |
| Recovery | Independently authorized inspection/factual recording only; cannot recreate a grant or enforcer |

Trusted code and the operating-system/account boundary must protect internal
registries and database access. This is not isolation against arbitrary malicious
Python executing in the trusted interpreter, a compromised host or an administrator
rewriting database files. Public/request input and other application callers are
untrusted. SQLite constraints alone do not establish privileged producer identity.

No arbitrary SQL, caller-selected connection/target, DDL, UPDATE/DELETE/REPLACE,
partial population, changed evaluation, discrepancy correction, capture, Explorer,
legacy conversion, completion seal, activation or general writer access is allowed.
An existing identical business operation is a conflict, not adoptable success.

## 3. Authoritative original-holder binding

Original-holder proof is the conjunction of confirmed source provenance and live
non-adoptable ownership, never an ID check alone:

- Exact source authority ID/canonical body digest, immutable source/genesis/audit
  graph and G2 P/C/Q/E original issue-time eligibility prefix. Policy must be the
  expressly adopted version applicable before original consent; existing sources
  cannot acquire eligibility by a later audit append or matching scope.
- Genuine private original issuance-to-owner registration, created through the
  protected original producer and promoted only after confirmed issuance commit
  and required cleanup. Existing coordinator registries illustrate this mechanism;
  their current permissions do not already include this new enforcer.
- Actual original PID, exact live Thread/context identity, runtime incarnation,
  active ceremony and lifetime. Integer thread/PID values persisted as DATA do
  not authenticate a new live owner; thread-ID reuse must not recreate ownership.
- The same original authenticated actor, primary/session/runtime-auth scope and
  authentication/MFA epochs; no replacement session, operator or repaired consent.
- Exact current manager-owned connection, active transaction and reservation
  identity/epoch. Registration must be checked against actual resources, not a
  caller-supplied ownership callback or claimed epoch.

The proposed private registration must be opaque and nonserializable, expose no
SQL/connection/transaction controls, and reject direct construction, copied DATA,
cross-thread/process use, import, pickle/JSON reconstruction and use after closure.
No durable row can promote itself into that registration. These are mandatory
properties for implementation design, not claims about a new implemented object.

## 4. Exact decision scope

Bind the registration to D = exact original authority ID/body digest; current
operation UUID/digest and frozen private manifest/population; actual enrolled
target/control paths and physical/schema/fingerprint identity; installation,
target UUID, G+2 profile/generation/binding, owner and auth/MFA epochs; independent
activation incarnation; original runtime/ceremony; exact confirmed journal pending;
actual target connection/transaction/reservation epoch; and original deadlines.

The private manifest key is its canonical digest, not the runtime operation UUID.
Only the existing supported family rule, complete population and exact effect
derivation are permitted. Witness bytes are derived from actual verified effects,
the exact D/pending and bounded actual time, not supplied as a caller-selected
digest. No new witness fields or later lifecycle codecs are defined here.

A different decision requires its own prospectively eligible source/grant and
must pass all permanent operation/manifest exclusions. It cannot be used to retry
the same excluded action. Deadline is at most original issue plus 120 seconds,
clipped by every shorter credential/consent bound; construction does not restart it.

## 5. Atomic transaction and ownership

The permitted atomic unit is one actual target transaction containing whole-family
precondition verification, fixed business writes, complete resulting-record
verification and one decision-bound witness. The trusted manager owns commit and
rollback. A capability cannot transfer that ownership or return a raw connection.

Required ordering is: control-first reservation; target writer reservation;
complete current admission; confirm sole durable journal start under the separately
authorized control protocol while retaining required target reservation; final
fresh admission; consume the private action; allow only fixed target writes;
verify effects; insert witness; perform final current checks and exact write-set
proof; commit target once. No release/replacement of the target reservation
between final admission, capability binding and mutation/commit is allowed.
Required control commits retain the target reservation through successful commit.

If a prior phase released resources, reacquisition and full fresh validation must
precede creation of the grant/enforcer binding. No already-created enforcer crosses
that boundary. Reservation loss after creation poisons it instead of rebinding it.

Target-local `permanent._prepare()` semantics must regenerate the exact reviewed
manifest inside the transaction, including all qualifiers/competitors, immutable
completion facts, identity history, independently certified Geography scope and
current membership. Existing collision/rule checks and complete
`_verify_operation_records()`/claim/Geography integrity semantics remain mandatory.
Only the G3 fixed rule/operation/family records and unchanged Z31 witness are
allowed. Post-write verification must prove complete exact effects and absence of
extra DML, unexpected trigger effects, schema changes or unrelated state changes.

Any known precommit failure rolls back the entire target transaction. Committing
effects before witness, or witness after a separate effects commit, is forbidden.
Control and target commits remain separate: no cross-database atomicity is claimed.

## 6. Mandatory fresh validation

Before mutation and again at the final precommit boundary, the trusted owner must
validate current authoritative state, allowing only exact expected protocol writes:

| Condition | Required current predicate |
| --- | --- |
| Authentication | Original actor/access, primary/session/runtime-auth links, revocation, MFA/epochs and all expiries; no replacement credentials |
| G1/source | Exact original canonical source/audit/consent/policy/action, unrevoked applicable policy and unused original exercise path |
| Approval/proposal/ACK | Exact operation/proposal/ACK/approval digests and effective invalidation/history scope |
| Activation/profile | Independent current activation incarnation and exact finalized profile/generation/install/owner/binding |
| Emergency stop | Current authoritative stop/block state/history; set-clear cannot revive an old action |
| Dependencies | Complete authoritative dependency graph/snapshots and family source preconditions; no stale allow result |
| Physical identity | Actual strict hostname, resolved paths, device/inode, schema/fingerprint, target/control relationship |
| Claims/history/control | Current complete graph/exclusions, exact source/journal/audit lineage, protected state, migrations/FKs and readiness |
| Reservation | Actual original owner, same connection/transaction/query mode and reservation epoch; no gap or replacement |
| Time | Paired clock validity, no rollback anomaly, strictly before original authority and every shorter bound |

Expected writes must be verified explicitly, not exempted by declaring all local
mutations trusted. Z15 schema-inventory reuse stays within its exact approved
issuance scope; it supplies no cross-phase permission or migration validity.
There is no filesystem continuity assumption or skipped physical observation.

Reservations serialize participating database writers; they do not freeze clocks,
external stop sources or filesystem replacement. This model uses fresh checks
immediately before commit, not a promise of instantaneous external revocation
during a SQLite commit. No guaranteed cancellation at the exact expiry tick is
invented. A changed or expired condition detected before commit denies commit;
uncertainty or late discovery of a possible committed outcome invokes inspection,
not a success publication or another mutation. No feasibility guarantee is made.

## 7. Non-adoption and single-use fencing

Before any usable enforcer is published, the unique decision/genesis/pending
exclusion must be confirmed durably. At the first grant-construction attempt the
original owner path is irreversibly marked spent. Failure to construct or validate
does not reset that path. At invocation the enforcer is consumed before DML and
cannot be invoked recursively or twice. It authorizes one transaction only.

Concurrent callers serialize through authoritative control/target reservations;
only the original registered thread may exercise the private action. Durable
journal and target uniqueness provide crash-stable fencing, not Python locks.
Z31 specifies unique authority ID/digest, installation/target/operation and
installation/target/private-manifest relationships, immutable rows and one pending
start. Mandatory witness insertion in the same effects transaction makes witness
collision fail the whole transaction. Constraints without enforced witness
participation are insufficient. Their current inert definitions are not deployed
protection; installation and producer enforcement require later reviewed design.

Confirmed success, known rollback, commit error, uncertainty, context exit, process
crash or transaction completion permanently ends live use. No failed or terminal
journal state frees operation/manifest exclusion. Restart cannot reconstruct the
original registry. Fresh authentication cannot adopt it. An exact duplicate yields
denial or outcome-only DATA, never a new execution path. BUSY/LOCKED is preserved
without arbitrary retries. A second process/runtime/ceremony/operator/decision
cannot use copied source, grant, pending, witness or result identifiers.

## 8. Witness, journal and source-audit coupling

The required attribution chain is G2 original policy/adoption/consent/action and
eligibility audit -> exact source D -> confirmed decision/pending -> complete
actual target effects and witness in one commit -> factual control outcome/audit.
All referenced canonical graphs must resolve and agree. No digest is self-proof.

The enforcer may create exactly one witness as an inseparable part of its action;
it has no independent witness-issuance API or permission to attest caller-provided
effects. The witness's precommit `TARGET_COMMITTED` text is uncommitted intent until
the transaction actually commits. Outcome verification must use a durable committed
snapshot, exact witness/pending/D and the complete actual effect records/digest.

The enforcer has no general journal append authority. Control decision/start and
outcome/audit recording require their separately scoped trusted producer/recorder.
Target commit followed by unknown control outcome leaves permanent exclusion and
no usable success publication. A later independently authorized factual inspector
may record proven outcome; that permission cannot write business data or recreate
original runtime authority. Existing journal codecs do not themselves prove effects.

## 9. Crash and uncertain commit

| Point | Required behavior |
| --- | --- |
| Before mutation | No business writes; keep any confirmed exclusion and spent original exercise; no adoption |
| During mutation | Whole transaction must roll back if rollback is known; otherwise inspect actual durable state |
| After effect, before witness | Never commit this prefix; rollback both as one transaction; absence alone proves nothing |
| After witness, before commit | Both remain uncommitted; no result from successful INSERT or in-memory state |
| After target commit | Exact positive effects/witness may exist despite lost response; no repeat transaction |
| Before journal outcome | Target-committed/control-pending is possible; only factual resolution, not recovery execution |
| Unknown target commit/cleanup | Poison live registration, publish no usable result, retain exclusion, no reconnect/retry/adoption |

Inspection must establish intended target/control identity/schema and restore
lineage, exact original source/policy/audit and journal graph, committed witness
and complete effects. Positive verified evidence can establish committed outcome;
missing rows, timeout or process death cannot establish safe failure. TARGET_FAILED
requires positive original-manager no-commit evidence, not absence. Unresolvable
uncertainty may remain blocked indefinitely. Expired original credentials cannot
authorize late control recording; a separate factual permission is necessary.

## 10. Revocation and invalidation

Every mismatch in section 6 denies creation/use or final commit. Specifically,
authority/credential/deadline expiry, policy revocation, reservation loss, stop,
auth revocation, approval/ACK invalidation/change, dependency change, physical
identity/schema change, profile/generation/activation change, unexpected control/
history mutation, owner/thread/context loss or transaction completion permanently
invalidates live use. Restoring earlier-looking values does not resurrect it.
Expected fixed writes are admitted only by exact write/result proof.

After a possible target commit, invalidation cannot promise to undo durable effects.
It suppresses usable publication/further mutation and preserves outcome inspection.
No automatic rollback of confirmed commits, renewed deadline or replacement grant.

## 11. Security non-escalation

| Separation | Enforced restriction |
| --- | --- |
| Enforcer is not a general writer | Fixed complete family write set plus inseparable witness; no raw SQL/handle or arbitrary target |
| Enforcer is not reusable authority | One consumed original action/transaction with original deadline and permanent exclusion |
| Enforcer is not recovery authority | Lost original registration is unrecoverable; durable evidence supports factual inspection only |
| Enforcer is not journal authority | No free journal/audit append interface; separate scoped recorder |
| Enforcer is not independent witness authority | Witness only internally derived from its own verified effects in the same commit |
| Enforcer cannot issue another grant | Zero grant-rights, no copy/redelegation/renewal/transfer |

These are proof obligations on a future implementation. This document does not
claim opaque Python types alone can enforce them or bless a bypass of existing
legacy writer checks. Legacy execution and its claims/history remain unchanged.

## 12. Implementation consequences

| Category | Boundary |
| --- | --- |
| IMPLEMENTATION-READY for design, not coding permission | Specify the exact private owner registry/API, original-source/grant checks, irreversible spend rules, fixed write authorizer/proof, complete effect verifier, atomic witness/commit owner and outcome-only inspection interface required above |
| REQUIRES ADDITIONAL SECURITY CONTRACT before implementation | Concrete prospective policy adoption/G2 consent/audit producer and authorizers; exact permitted write/trigger/result and effect-evidence representation; transaction/phase integration, journal installation/producer/source-audit write sets and migration/enrollment compatibility. Each must realize this model without widening authority |
| PROHIBITED | Implementing or deploying from this gate alone; grandfathering authorities; raw SQL/general writer; cross-context handoff; retry/adoption/recovery execution; schema changes or legacy claim fabrication to bypass gates; lifetime extension or removed fresh validation |

The model fixes who may act, what may change, when authority is consumed, what is
atomic and what failure permits. Concrete representations are deliberately deferred
to implementation design, not treated as already existing primitives. If design
needs another authority, action, phase transfer or different revocation/atomicity
rule, it must stop for a new security decision instead of filling the gap in code.

## 13. Decision A and exact next boundary

**A - NEW SECURITY CAPABILITY APPROVED FOR IMPLEMENTATION DESIGN.** A trusted
original-holder enforcer can fit the prospective G1 model with the exact action,
fresh admission, atomic mandatory witness, permanent fences and non-adoption rules
above. There is no identified need for broader transferable permission or legacy
reinterpretation. This is a normative new capability, not a claim existing target
guarantees already implement G3's missing consumer.

The next boundary is a separately authorized **implementation-design contract for
the exact enforcer ownership/API, fixed family-effect/witness write proof and
commit/outcome protocol**, including the dependencies in section 12. No code or
production permission follows automatically. Timing feasibility under the unchanged
120-second ceiling remains unestablished and cannot be inferred from this approval.

## 14. Validation and production blocks

Only this document is added. Validate document whitespace/local links and
`git diff --check`. No pytest, Z18, T, broad suites, Python/schema/migration,
permissions/grant/enforcer, target DML/DDL, production/hosted access, commit or push.

PRODUCTION AUTHORIZATION: BLOCKED

PRODUCTION EXECUTION: BLOCKED

PRODUCTION ACTIVATION: BLOCKED
