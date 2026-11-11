# 4e-20-Z27: replacement runtime security-model proposal

## 1. Z26 decision and proposal status

[Z26](recognition-runtime-replacement-finalization-owner-write-set-decision-4e-20-Z26.md)
established that no existing owner can combine issuance, attempt and target entry
under current contracts. This is a new-model proposal, not another search for an
optimization inside those owners. No existing rule, record, schema or producer is
changed or reinterpreted here.

**NO MODEL READY FOR CONTRACT APPROVAL.** The alternatives below are concrete
security choices, but the current evidence does not establish the complete
authorization/outcome protocol for a runnable replacement. Recommend considering
E's transaction-owning executor in one holistic security decision, not implementing
another preparatory micro-slice. Section 11 states the precise missing decisions.

The current 120-second ceiling remains mandatory. A design recommendation does
not approve a longer lifetime, phase grants, another ceremony or a new writer.
No performance or implementation feasibility is claimed.

## 2. Security requirements and trust boundary

The trusted-admin model still assumes trusted deployed code and host/database
administrators. It must prevent stale intent, application misuse, races, replay,
duplicate execution and process/commit failure. Local opaque objects are not
cryptographic protection against arbitrary host compromise. Digests prove content
integrity, not authentication, attestation, freshness or consent.

All candidates must satisfy these common requirements at every protected use;
their candidate-specific authority/boundary differences are in section 3.

| Security dimension | Required invariant for A-E |
| --- | --- |
| Authentication/expired credentials | Genuine current owner primary/session, MFA/epochs, revocation and all expiry bounds. No refresh by lookup, new phase, publication or preparation artifact. |
| Scope/authority substitution | Exact operation/manifest/proposal/ACK/approval, installation/target/generation/profile/binding/owner/auth epochs derived from current readers. No supplied replacement scope or authority body. |
| Activation | Current independent activation incarnation and exact grant binding; reject changed head/incarnation, never upgrade preactivation intent. |
| Physical identity | Actual strict hostname/paths/devices/inodes/schema/fingerprint at all required use/commit boundaries. SQL reservation is not filesystem continuity. |
| Approval/ACK | Current exact pairing and effective approval/invalidation, not operation digest alone. |
| Stop/dependencies | Current stop/block, dependency state and required whole-population manifest/precondition checks; no historical clear/ready certificate. |
| Claim/history/control | Complete current graph/exclusions, canonical audit/history, schema/migration/profile relationships and actual protected write proof. Prior validation is not a permanent allow decision. |
| Reservation theft | Manager-only actual connections, transactions, query mode, epochs, PID/thread/context and paired clock. No SQL/cursor/commit interface escapes. |
| Replay/duplicate execution | Atomic database single-winner fencing for the logical operation, not process-local flags alone; no new request evades an unresolved predecessor. |
| Cross-process adoption | Old live authority dies with its registered owner. A durable reference, login, matching hash or inspected row cannot reconstruct it. |
| Partial mutation | Business effects must be transaction-atomic with target-local duplicate/outcome evidence; no partial family population acceptance or active per-item quarantine shortcut. |
| Uncertain commit | Stop, publish no usable execution result, inspect durable evidence; no automatic retry/adoption or inference of rollback from absent publication. |
| Audit/cleanup | Append-only decision/outcome evidence without secrets; known uncommitted work rolls back, earlier or uncertain commits are not claimed rolled back. Cleanup/publication failures cannot mint another capability. |

Current sources retained as requirements, not implicitly widened implementations:
[4e-11 authority](recognition-runtime-activation-bound-authority-contract-4e-11.md),
[Z5 lifetime](recognition-runtime-admission-lifetime-contract-4e-20-Z5.md),
[Z20-R write sets](recognition-runtime-attempt-preparation-late-finalization-contract-4e-20-Z20-R.md),
[Z21 issuance](recognition-runtime-authority-issuance-composition-contract-4e-20-Z21.md).
The current writer boundary rejects nonmatching authority/legacy scope; it cannot
be made to accept these proposals through fabricated legacy EXECUTING records.

## 3. Candidate models A-E

### A: expiring durable non-executable preparation object

**Owner:** authenticated preparation producer; later final owner is independent.
**Authority level:** read/intent recording only. **Executable capability:** none.
**Durable state:** hypothetical bounded historical intent/evidence, never an attempt
or authority. **Transaction:** a separate local evidence-write transaction, with
no target DML. **Expiry:** a reviewed data-eligibility bound, not permission lifetime;
no number is chosen. **Invalidation:** any mismatched current subject/schema/state
or failed provenance/expiry rejects its use. **Adoption:** only data could be read
after reauthentication; old owner/allow decisions could not survive.

An attacker possessing the object must receive no advantage in admission: the
final owner must perform every section 2 check afresh and originate new consent.
Replayed data cannot consume consent or claim a winner. Process death leaves
history only; uncertain evidence commit grants nothing. No authority bridges the
fresh-authentication boundary. The useful exact payload/provenance/retention and
duplicate-selection policy remain **UNRESOLVED**; Z20-R found no currently
authorized useful payload. Expiring a digest does not make its contents current.
Calling the record a capability would be misleading unless its sole action is
non-executable inspection. Reject it as an execution credential or a speedup claim.

### B: preparation, admission and execution authorities

**Owners:** distinct privately registered stage managers under a newly reviewed
lineage policy. **Authority levels:** preparation only inspection; admission only
exact decision recording; execution only exact one-shot mutation. **Capabilities:**
no arbitrary SQL or target selection; only the execution stage could mint a writer.
**Durable state:** proposed immutable stage grants/consumptions and audit lineage.
**Transactions:** each grant/consumption must be atomic locally and single-winner.
**Expiry:** each grant would be at most 120 seconds and clipped by credentials;
aggregate exposure/number of grants is **UNRESOLVED**. Per-stage 120 seconds is
not equivalent to the old single-authority ceiling.

Fresh section 2 validation is mandatory before each grant and use. A prior-stage
artifact is necessary historical lineage at most, never sufficient permission
for a successor. Scope, activation, physical identity, approval, stop, dependency,
claim/history/control and reservation changes reject; no inherited valid flag.
Successor consent, aggregate authority exposure and predecessor retirement must
be explicitly approved. Replay/substitution must fail atomic consumption and
exact scope checks. Crash loses local capability; unknown predecessor outcome
blocks successors. **UNRESOLVED:** stage action sets, consent continuity, retirement,
storage/commit proof and uncertain-state disposition. Do not implement this model
or use fresh login as a disguised authority extension.

### C: one ceremony, deferred executable authority

**Owner:** one original private process/thread/context, established before work.
**Authority before grant:** authenticated inspection only, with no execution API.
**Durable preparation:** none required. **Transactions:** actual reserved read-only
validation followed by a separately specified exact final grant/write protocol.
**Expiry:** pre-grant inspection remains bounded by actual credential/consent
deadlines; no new authenticated-context lifetime is invented. Executable authority,
if eventually granted, starts at its actual creation and ends at the earliest of
120 seconds and all earlier applicable deadlines.

No preparation object bridges anything. The original context is only trusted to
invoke current validators, not to remember that validation once succeeded. Every
section 2 check stays fresh at its required final/use/commit boundary. Credential
expiry or changed auth/security state rejects rather than restarting the context.
Crash discards it; another process cannot adopt it. Durable consent/grant writes
would still require replay/duplicate and unknown-commit fences.

This is secure as a non-authoritative inspection pattern, but the existing
coordinator already defers construction until after substantial verification.
It is not yet a replacement solution. **UNRESOLVED:** a final owner/graph proof
that avoids reproducing the expensive post-grant chain without losing checks.
The context would become an equivalent long-lived authority if mere possession
could bypass current authentication, create a grant automatically, or extend
consent. Those behaviors are explicitly rejected.

### D: extended executable authority

**Owner:** existing original ceremony/continuation model. **Authority/capability:**
same exact action restriction, but a proposed larger absolute permission window.
**Durable state/transactions:** existing authority and phase graphs with an
explicitly reviewed versioned lifetime change; no old row rewrite. **Invalidation:**
all section 2 changes still reject. **Adoption:** no new process/context import;
crash/uncertainty still stops. Duplicate/replay fences do not disappear.

This changes the security model, not merely a timeout. **UNRESOLVED:** acceptable
maximum exposure, fresh consent/MFA intent over the larger interval, contention,
activation/revocation/stop responsiveness, exact policy/codec/SQL/consumer
compatibility and threat-model justification. No new maximum is proposed or
approved. Earlier credentials/consent must still clip expiry. A longer lifetime
does not make stale observations valid or establish that the complete path fits.
Reject as an automatic response to slow validation.

### E: transaction-owning command executor replacing grant-to-attempt composition

**New-model hypothesis:** separate historical request/duplicate exclusion from
live execution permission. One original executor owns final live validation and
the exact target mutation transaction; it does not consume an existing current
authority/attempt chain as its credential. This deliberately requires a replacement
contract, not promotion of any existing owner or alteration of legacy writers.

The sole bridge across expensive work would be the original **non-authoritative
live inspection owner**, plus immutable historical request facts used only for
duplicate exclusion. Neither can mint a writer without complete current consent
and final validation. No durable executable preparation or imported attempt exists.
The prospective grant begins only after the final current admission decision,
and retains the unchanged 120-second ceiling. No required post-write/commit
predicate is removed by placing issue time later.

The phase and lifecycle tables below make E concrete enough to reject or commission
as a whole. They do not supply a new codec, table, mutation primitive or runnable
capability. The feasibility of final validation and exact execution inside the
remaining window is **UNMEASURED**.

## 4. Threat analysis for every model

Section 2 applies in full; this table identifies each model's distinctive failure
mode and required response rather than exempting apparently unchanged facts.

| Threat group | A | B | C | D | E |
| --- | --- | --- | --- | --- | --- |
| Stale/expired auth, activation or revoked approval | Data never substitutes for fresh final credentials/incarnation/pairing | Revalidate for each stage; previous grant cannot auto-renew | Current validation, not context possession | More exposure makes continued freshness essential | Complete pregrant and required prewrite/precommit checks; no request-as-permission |
| Physical identity/reservation theft | Reobserve under final owner; object owns no reservation | New actual reservations each stage, no transported epoch | Original actual reservations still checked; external paths remain mutable | No extra continuity from longer life | Exact owned target transaction and fresh physical checks; invalidate on replacement |
| Stop/dependency/claim/history/control changes | Reject stale evidence/current exclusions | Reject successor/use despite earlier stage success | Fresh state and exact actual write proof remain mandatory | Full live checks still apply | Current global state plus exact post-write proof; snapshot is not immunity |
| Replay, duplicate execution, authority substitution | Artifact cannot issue grant; final CAS/exclusion required | Single successor and action/scope-bound consumption required | One original owner plus durable grant uniqueness | Existing one-use fences remain | Durable request/global exclusion plus target-local commit fence; no duplicate from missing control result |
| Cross-process adoption/crash | Retained data is inspectable only | Durable lineage cannot restore a stage capability | Lose context; no import/restart | Lose original continuation | Lose original executor; durable state fences further execution, not resumption |
| Uncertain commit/partial target mutation | Evidence commit grants no write | Unknown predecessor blocks later grants | Unknown final commit publishes nothing | Existing stop/inspect, no retry | Atomic effects plus target outcome record; unknown publication blocks replay; exact evidence contract needed |

No model can relax fresh checks merely because an administrator is trusted.
No model is acceptable if preparation possession alone can gain writer/execution
authority after authentication/security state changes.

## 5. Recommended direction and precise limitations

E is the most coherent **holistic review direction**, because it asks whether
the separated committed-authority/attempt/metadata intermediates are necessary
to the replacement authorization model at all. It does not pretend that moving
an existing field or changing an owner name removes their contractual cost.
It retains one original live executor and one exact business action, rather than
a sequence of automatically renewable phase credentials.

However **no model is selected as ready for contract approval**. E's new operation
exclusion/outcome and final grant/transaction proof must be approved together.
A, B and C lack an established useful/preserving finalization mechanism; D lacks
threat-model approval. E must be rejected if the complete replacement cannot
preserve section 2 or if the final authority-bound work still cannot finish.

## 6. E's proposed phases and security-object lifecycle

The names here are conceptual, not existing schema states. In particular do not
map them onto existing AUTHORIZED, ATTEMPT_CREATED, EXECUTING or legacy claims.

| Phase | Owner / authority level / executable capability | Durable state and transaction boundary | Expiry / invalidation / adoption |
| --- | --- | --- | --- |
| Authentication | Existing eligible credential producer, then original executor validates; no writer | Existing auth records only; no new login mechanism implied | Actual credential/epoch deadlines; changed credentials end original binding; no owner adoption |
| Consent | Protected owner decision for exact current scope; no writer | Existing principles of one-use MFA/consent audit; replacement integration not defined | Original step/confirmation expiry and scope; cannot extend grant or reuse another ceremony |
| Scope binding | Original executor independently resolves exact operation and current installation/profile/incarnation | Immutable selected intent may be referenced; no executable row | Mismatch rejects; changing scope requires a new explicit request, subject to conflicts |
| Preparation | Original executor, inspection only; no capability | No new reusable evidence; any proposed durable request exclusion is non-executable and separately reviewed | Credential/consent bounds; process/thread/context loss destroys eligibility |
| Authority | Same executor after final current decision; at most one exact live grant | New grant/audit protocol must atomically consume final consent and fence operation | Actual issue time plus at most 120s, clipped earlier; no reissue/renewal/adoption |
| Attempt creation | No separately committed executable attempt proposed | Attempt identity, if needed, is metadata within exact final protocol, not a credential before/after crash | No independent lifetime or restart privilege; exact record format UNRESOLVED |
| Target-entry reservation | Same executor owns exact target transaction; metadata is not write permission | Target-local duplicate/outcome fence must be part of same transaction as effects; no existing marker repurposed | Actual reservation epoch/connection/mode and grant deadline; loss rejects |
| Writer admission | Same executor internally issues one opaque fixed-action permit only after fresh checks | No public token/SQL; exact grant/transaction/manifest bound | PID/thread/context/transaction single-use; every relevant state change fails closed |
| Execution | Controlled family primitive under exact executor-owned transaction | Whole approved population effects and target outcome record atomic together | Deadline must hold at all required checks including precommit; no partial quarantine shortcut |
| Completion | Same original executor verifies actual outcome; no new executable permission | Only confirmed target outcome may support control completion; separate databases remain non-atomic | Grant expiry never permits further mutation; uncertain outcome is not completion |
| Cleanup/publication | Original executor invalidates every view/permit and resolves owned connections | No usable success before all required confirmations/cleanup | Cleanup/publication failure cannot restore live permission |
| Crash recovery | Authenticated inspection only; no replacement executor from rows | Read exact request/grant/target outcome/control history; no automatic DML | Old capability permanently lost; any retirement/remediation requires a separate explicit security decision |
| Uncertain commit | No usable result, no retry/adoption | Stop and inspect durable evidence; do not infer target rollback from missing control completion | Unresolved operation stays excluded; no expiry-based automatic reuse |

### Proposed transition obligations

| Conceptual transition | Current authority and fresh checks | Performer / irreversible point | Failure / uncertainty |
| --- | --- | --- | --- |
| REQUESTED to INSPECTING | Current authenticated inspection scope; exact request and global conflicts | Original executor; no authority yet. Durable exclusion, if approved, commits only a non-executable fence | Failed setup grants nothing; uncertain fence commit blocks a second request until inspection |
| INSPECTING to FINAL_DECISION | Complete section 2 checks and exact fresh owner consent; no evidence shortcut | Original executor under actual current reservations; no published capability | Any changed/expired scope rejects; no retained allow decision |
| FINAL_DECISION to LIVE_GRANTED | Exact final subject, unused consent, current time/scope and operation exclusion | Same executor, reviewed atomic consent/grant/audit transition; actual issue time starts ceiling | Unconfirmed commit publishes no usable permit; no automatic regrant |
| LIVE_GRANTED to MUTATING | Fresh required physical/auth/activation/approval/dependency/stop/history/control/claim/reservation checks and exact target-local exclusion | Same executor only; opaque one-shot permit; target DML still uncommitted | Rejection rolls back known uncommitted target work, destroys permit; grant is not reusable |
| MUTATING to TARGET_CONFIRMED | Exact business effects and target outcome proof, required current scope/identity/time/stop checks | Executor target COMMIT is irreversible; outcome evidence must commit with effects | Unknown commit means UNKNOWN, never rollback assumed or automatic retry |
| TARGET_CONFIRMED to RECORDED | Confirm actual target outcome and exact current control lineage; no new mutation authority | Executor records completion fact through reviewed control protocol | Control failure cannot undo target commit; keep duplicate fence and inspect, not execute again |
| RECORDED to CLOSED | Confirm required records and cleanup; invalidate all live permissions | Original owner cleanup and success publication | Publication failure gives no resumable handoff; historical records remain inspectable |

No request, phase success or elapsed time implies a later transition. Any durable
exclusion is irreversible for automatic execution even after expiry; releasing or
retiring it would need a separate explicit policy. This favors safety over liveness.
The exact post-write validation equivalence and global commit ordering are not
asserted proven by this table; see section 11.

## 7. Authority boundaries and central bridge question

**No artifact needs to bridge preparation as executable authority.** Immutable
operation data can remain data; original live ownership can orchestrate reads
only while current credentials permit. A durable exclusion, if approved for E,
can prevent another request without granting anyone permission to execute.
That distinction is necessary but does not itself authorize new storage.

Final grant requires independent actual current validation and fresh exact consent.
If auth/security state changes, any preparation-created artifact remains insufficient:
the final checks reject stale scope, and the artifact cannot recreate a manager or
mint a permit. No predecessor authority/attempt is imported. Required checks after
grant and before commit remain current; frozen read state is not physical identity
continuity. Original process/thread or transaction loss permanently invalidates
the local permit. A later login may inspect facts but cannot adopt that permit.

Current lifetime semantics are not changed: 120 seconds still starts at actual
authority construction, not delayed to publication or target commit. E would need
new ownership and actual-write proofs replacing the current protocol, not a
retrospective timestamp adjustment. No minimum feasibility follows from this idea.

## 8. Crash and uncertain-commit model

The main cross-database safety requirement for E is that a confirmed control grant
cannot be mistaken for target execution, and a missing control completion cannot
permit replay after target effects. A target-local atomic outcome/fence tied to
the exact logical operation is therefore a necessary candidate requirement.
Its existence/absence can be trusted only under an approved identity/schema and
commit-evidence contract; do not invent such a record in current tables.

Known uncommitted family mutation rolls back as a whole. If target commit is
uncertain, publish no usable result and stop. If target is confirmed committed
but control recording fails, keep global duplicate exclusion and report unresolved
recording, not permission to execute again. A crash after control grant but before
target commit loses the live permit and does not authorize a new executor.
No automatic lease expiry, retry, orphan adoption, audit repair or process restart
resumes execution. No exactly-once delivery/completion claim is made: the proposal
seeks at-most-one committed business effect, with fail-closed uncertain liveness.

Recovery in this proposal is authenticated **read-only diagnosis**. Any business
correction or retirement remains a separately approved action, not resumption of
an old attempt. Permissions to record reconciled outcomes, if wanted, are
**UNRESOLVED**, not implicitly granted by administrative status.

## 9. Adoption, replay and legacy isolation

No candidate may convert existing 4d claims, 4e authorities/attempts, target markers
or legacy EXECUTING into new permission. Existing conflicting records remain
blocking until an explicit future retirement policy says otherwise. Old codecs,
tables and readers stay unchanged; a future replacement must have an explicit
version/installation eligibility policy rather than silently sharing meanings.

Replay fences must be durable and global to the logical operation/manifest, not
only to one request UUID. Fresh request IDs cannot evade an unresolved execution.
Consent cannot be spent twice, and a consumed or lost permit is not recreated.
No bearer preparation token, signed digest, console hostname override, browser
claim or provider/test callback is an alternative source of execution permission.

## 10. Decision matrix

| Model | Preserves 120s ceiling | New security object | Cross-auth boundary | Adoption risk | Crash safety | Complexity |
| --- | --- | --- | --- | --- | --- | --- |
| A: durable non-executable evidence | YES only if final authority unchanged; no speedup established | Hypothetical evidence object; exact useful payload UNRESOLVED | Data only, final full revalidation | Mislabeling evidence as permission | Safe only as non-executable history; final execution still requires its own protocol | Medium evidence contract; does not solve finalization |
| B: phase authorities | Per grant possible; aggregate policy UNRESOLVED | Stage grants and single-successor lineage | No live capability transfer; new authorized grants only | Hidden renewal/escalation and duplicate successors | Unknown predecessor must block progress; exact protocol UNRESOLVED | Very high |
| C: deferred authority | YES for final grant; original credentials still expire | Non-executable original inspection context | No adoption; context loss ends it | Inspection context becomes an allow token | Context loss safe; final grant/outcome proof UNRESOLVED | High; partly resembles existing blocked path |
| D: extended authority | NO; not approved | Revised lifetime policy | Existing no-adoption boundary | Larger exposure without justified intent freshness | Does not repair current unknown-commit problems | Broad security-policy review |
| E: transaction-owning executor | YES as proposed absolute final-grant maximum; feasibility UNMEASURED | Non-executable global exclusion, exact local grant/permit and outcome evidence, all new-contract concepts | No old permission; fresh final decision required | Request/outcome rows accidentally treated as resumable capability | At-most-once effect goal depends on approved target/control fence/outcome protocol | High but must be reviewed as one complete replacement |

## 11. Exact contract boundary and approval decision

**NO MODEL READY FOR CONTRACT APPROVAL.** The precise missing security decision
is whether to replace the committed-authority -> committed-attempt -> metadata
prerequisite chain with E's **one original transaction-owning executor, durable
non-executable global exclusion, late exact grant and target-atomic outcome proof**.
That would supersede ownership/persistence relationships, not simply shorten code.

One holistic replacement contract must settle all of the following together:

1. Exact logical-operation exclusion domain, authenticated request/consent binding,
   and whether non-executable durable exclusion before grant is accepted despite
   availability loss on abandonment. No authority is conferred by that exclusion.
2. Exact fresh validation boundaries and actual post-write proof for the new
   grant/attempt-equivalent/target writes. It must prove all required security
   predicates, trigger effects, protected state and global graph integrity without
   assuming mutable observation reuse. If no such proof exists, reject E.
3. Exact manager registrations/authorizers and control/target commit ordering:
   target reservation retained through required control commits, fresh validation
   after every reacquisition/epoch change, and no interval where borrowed authority
   survives owner loss. Current owners cannot be widened as a shortcut.
4. Exact target-local outcome evidence atomic with family effects, global duplicate
   fencing across control/target failures, and every crash prefix. State whether
   trusted restore/copy behavior could defeat the fence and how installation/
   generation changes block old requests. Do not claim cross-database atomicity.
5. Explicit legacy/old-runtime eligibility and non-adoption, completion-recording
   permissions, read-only uncertainty inspection and separate manual disposition.
   Define no new automatic recovery merely to improve availability.

Only if that complete model is explicitly approved could later schema/codecs,
owner and writer implementation be authorized. The next boundary is this full
security decision or rejection, not another performance investigation or a chain
of speculative preparation slices. No lifecycle measurement or T is authorized.
If the chosen model retains the existing post-grant composition unchanged, the
known blockage remains; if actual final work still exceeds 120 seconds, fail closed.

## 12. Validation and explicit production blocks

Only this proposal document is created. Validate `git diff --check` and document
whitespace/local links. No pytest, Z18, T, broad suite, code/schema/migration,
existing authority change, target state, writer/execution capability,
hosted/production access, commit or push.

PRODUCTION AUTHORIZATION: BLOCKED

PRODUCTION EXECUTION: BLOCKED

PRODUCTION ACTIVATION: BLOCKED

WRITER CAPABILITY: BLOCKED
