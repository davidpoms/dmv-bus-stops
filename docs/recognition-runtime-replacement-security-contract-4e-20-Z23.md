# 4e-20-Z23: replacement runtime security contract design

## 1. Z22 decision and status of this design

[Z22](recognition-runtime-architecture-exit-decision-4e-20-Z22.md) stops the current
executable composition. This document compares replacement security models; it
does not approve one for implementation or retrofit current records into one.
Existing authority semantics, original-continuation rules and the 120-second
ceiling remain unchanged. A design recommendation is not implementation approval.

Recommend candidate B's **evidence-only preparation, then fresh final consent and
admission** as the narrowest defensible direction for a further precise contract.
There must be no authority or executable attempt before that final decision and
no imported old capability afterward. The exact useful payload, final owner/write
set and demonstrated completion budget are **UNRESOLVED**. Consequently no runnable
replacement is yet fully specified or authorized. If a useful payload cannot be
defined without stale allow decisions, reject this candidate rather than relaxing
freshness or granting another authority window.

## 2. Security problem and evidence limits

Z18 measured the current issuance/admission at 80.302s and attempt creation at
84.405s. The nested issuance and attempt final validations took 35.356s and
35.328s respectively; do not add these to their enclosing spans. Authority
expired during attempt final validation, before metadata admission. The complete
metadata path remains UNMEASURED. Consent was valid, Z15 inventory preparation
ran, and the external diagnostic timeout was not reached.

The current measured implementation cannot fit the existing ceiling. No proof
shows every implementation infeasible, nor does evidence identify a large pure
construction cost that can be moved without a new contract. A division into phases
does not itself make a phase fast or make repeated fresh checks dispensable.

## 3. Existing guarantees to preserve

Sources:
[4e-11 authority contract](recognition-runtime-activation-bound-authority-contract-4e-11.md),
[4e-19-R original continuation](recognition-runtime-authority-coordinator-continuation-contract-4e-19-R.md),
[Z20-R payload/write set](recognition-runtime-attempt-preparation-late-finalization-contract-4e-20-Z20-R.md),
[Z21 issuance composition](recognition-runtime-authority-issuance-composition-contract-4e-20-Z21.md)
and [Z5 lifetime policy](recognition-runtime-admission-lifetime-contract-4e-20-Z5.md).
Older design documents describe interfaces subsequently implemented; current source
remains authoritative for actual owner registration and admission behavior.

Trusted host/code/database administrators remain inside the trusted-admin model.
Opaque local objects are integrity boundaries, not protection against arbitrary
host compromise. A content digest is not attestation, credential validity or
operator consent. Browser fields, configuration booleans and caller-supplied
physical observations cannot establish authority. No new signing infrastructure
is assumed to solve freshness or filesystem continuity.

The following requirements apply to **every candidate**. Section 4 supplies each
candidate's boundary/authority differences. A candidate that cannot implement a
requirement is incomplete, not exempt from it.

| Property | Mandatory rule for each candidate A-E |
| --- | --- |
| Authentication continuity | At each protected use validate genuine current owner credentials, MFA/epochs, revocation and all applicable expiries. Earlier login is not an evergreen permission. Never restore a process-local credential from a historical artifact. |
| Scope continuity | Derive exact operation/manifest/proposal/ACK/approval, installation/target/generation/profile/binding/owner and auth/MFA scope from authoritative readers. Mismatches reject; caller cannot rebind. |
| Activation continuity | Require current independent activation incarnation and exact authorized binding. Activation change invalidates pending use, including after a reservation change. No preactivation upgrade. |
| Physical identity continuity | No presumed filesystem continuity: freshly observe hostname, resolved paths, devices/inodes, schema/fingerprint at every required boundary. Preserve strict target/control identities and enrolled runtime scope. |
| Approval/ACK continuity | Fresh exact pairing, effective approval history and invalidation at authorization/use. An unchanged operation digest is insufficient. |
| Dependency continuity | Fresh authoritative dependency checks and required target-population/manifest regeneration. Historical preparation records do not prove current preconditions. |
| Emergency stop | Current stop/block decision at all required admission/final/use boundaries; a previous clear observation cannot override a later stop. |
| Claim/history integrity | Validate current graph, effective lifecycle state, exclusions, canonical digests, links and actual write suffix. No adoption/conversion of legacy or preactivation claims. |
| Control integrity | Validate current schema/migration/profile relationships, protected baselines, exact permitted writes, trigger/FK effects and audit chain. Z15 permits only its existing phase-local schema inventory. |
| Reservation ownership | Manager owns actual connections, transactions, query mode and epochs; control reservation precedes target reservation. Preserve target-held-through-control-commit rules and metadata commit/reacquisition requirements. No caller SQL or borrowed owner impersonation. |
| Expiration | Actual issue time starts the authority window; no restamping, grace, automatic renewal or ignored shorter credential deadline. Candidate D alone proposes a separately reviewed different maximum; current maximum remains 120s everywhere. |
| Replay resistance | Consent and live capability consumption are one-use, tied to exact scope and expected durable state, with atomic database fencing. Artifacts cannot recreate a consumed live owner. |
| Duplicate fencing | Global operation/manifest exclusions and a durable single winner under database serialization, across processes and restarts. New stages cannot evade old conflicts. |
| Crash handling | Destroy live capabilities on process/context loss. Historical rows prove facts only. No automatic adoption, retry or target-outcome inference from absent publication. |
| Uncertain commit | Stop; publish no usable result; inspect durable state read-only. Neither a new login nor a successor phase resolves uncertainty. |
| Process/thread/context | Live authority is opaque, nonserializable, non-adoptable and bound to its genuine registered owner, thread, PID, connection/transaction epochs and lifetime. Data that survives is not such authority. |
| Cross-ceremony adoption | No imported old continuation, executable attempt or authority. Any proposed successor permission must have an explicitly new reviewed authorization policy; matching IDs are not permission. |
| Auditability | Append-only canonical records of actual decisions, predecessor relationships and outcomes; no secret material or rewriting of old formats. Evidence and authority must be distinguishable to readers. |
| Rollback | Roll back known uncommitted phase writes through the owning manager; do not promise rollback of earlier commits or uncertain target/control outcomes. No cross-database atomicity claim. |

## 4. Candidate replacement models A-E

### A: one authenticated ceremony, multiple bounded phases

The original registered outer ceremony would remain the sole owner. Phases may
carry immutable intent and historical decision references, but each new reservation
must freshly validate every rule in section 3. No connection, query-only view,
epoch or admission result crosses as current permission. Process/thread/context
loss terminates the ceremony, regardless of durable phase history.

With one unchanged authority and absolute 120-second deadline, this is effectively
the already-failing composition unless actual required work changes. Giving each
phase a renewed window is a new multiple-authority policy, not preservation of
the existing single lifetime. Its total exposure, stage consent, successor scope,
single-winner consumption and failed-stage handling are **UNRESOLVED**. Prior
authentication cannot silently authorize a series of new 120-second grants.

No cross-ceremony adoption is needed if the original context remains alive, but
that alone does not justify stage authority. Atomic stage history plus original
ownership would be required for replay/duplicate prevention; exact storage and
commit/publication rules are **UNRESOLVED**. Uncertain commits terminate usable
progress. No automatic restart, resumption or second ceremony is specified.

### B: prepare, then reauthenticate and finalize

Preparation can survive only as **non-executable historical intent/data**. It
contains no live credentials, allow decision, authority, spent continuation,
attempt, target reservation entitlement or asserted current readiness. A later
fresh authentication does not renew any earlier authority because no authority
was created in preparation. This is a proposed new policy, not a reinterpretation
of existing attempts or a bypass of their durable exclusions.

Finalization must independently resolve the operation and complete section 3's
current checks under its own genuine manager. Scope, profile, activation, physical
identity, approval/ACK, dependencies, history/claims/control and stop must match
the explicitly selected intent or reject. No automatic selection of a newer
scope/profile/operation is permitted. Fresh explicit owner consent must cover
the actual current final subject; the old evidence cannot supply that consent.

Only after final consent/CAS may a new original final owner construct authority,
with the unchanged maximum 120-second exposure and earlier credential/consent
deadlines. All required actual post-write validation remains. Replay/duplicates
must be fenced at that new issuance, not by trusting a prepared artifact.
Preparation evidence must never grant writer or target-mutation access.

After a crash before finalization, ordinary historical data may remain inspectable;
a new final request starts from fresh authentication/admission, not a revived
context. Existing authority/claim/attempt conflicts still reject. After any final
authority issuance or uncertain commit, no new final request may automatically
replace/adopt it. Preserve immutable audit and inspection-only uncertainty rules.

**UNRESOLVED:** exact permissible useful preparation payload, whether any new
durable record is needed, trusted origin/selection/bounds, stale-intent rejection,
fresh-consent interface and final manager/write protocol. Z20-R found no additional
currently authorized useful payload. Existing frozen proposals may be referenced
as data, but do not establish that a replacement reduces work. Nothing here
authorizes a portable preparation codec or a second executable ceremony.

### C: short-lived phase-specific authorities

Each authority would name only an exact stage/action, exact operation/scope,
predecessor lineage and a bounded deadline. No general execution grant and no
automatic stage escalation would be permitted. Fresh section 3 validation is
required before each grant and each protected use. Original consent must either
explicitly authorize these distinct grants under an approved policy or each grant
must have separately defined fresh consent; both are **UNRESOLVED**.

Only immutable evidence and consumed-stage history could cross a boundary. A
successor authority cannot be reconstructed from that history: issuance must be
an independently authorized durable transition. It must atomically prevent
multiple successors/replays, reject scope/activation/physical/approval/claim
changes, and never transfer an old process/thread capability into another owner.
Crash loses live authority; uncertain transition blocks successors until an
explicitly reviewed inspection/retirement policy, not automatic adoption.

**UNRESOLVED:** exact stage action vocabulary, aggregate exposure and maximum
number of grants, consent freshness, successor/single-winner protocol, abandoned
stage rules, storage/audit and uncertainty disposition. Keeping each grant below
120 seconds does not preserve the old one-authority security model. No phase
writer/execution capability is defined by this candidate review.

### D: extended authority lifetime

Retain original ceremony/owner, exact scope and current consumers' full fresh
checks, but propose a separately approved larger absolute maximum. No cross-phase
artifact becomes a new credential and no process/thread adoption is introduced.
Replay, duplicates, audit, rollback, expiry at equality and uncertainty retain
section 3's rules. Longer validity does not freeze authentication, activation,
physical identity, approval, dependencies or current state.

This candidate does not preserve today's 120-second ceiling and is unapproved.
**UNRESOLVED:** threat-model justification, acceptable maximum exposure, owner/MFA
intent freshness, stop/revocation latency, contention/reservation risks, exact
versioned policy/codec/SQL/consumer compatibility and required tests. Underlying
credential/consent expiries must still shorten authority validity. Slowness alone
does not decide any of these questions. No numeric replacement is selected.

### E: fundamental runtime redesign

Consider a new execution ownership model rather than fitting a new grant into
the existing authority-to-attempt chain. Pure planning would remain data; a final
registered owner would need exact fresh authentication, consent and section 3
admission, bounded actual mutation authority, atomic target-local guarantees and
independent control/target outcome evidence. It could not derive permission from
old attempts, claims, leases or adopted original continuations.

**UNRESOLVED:** replacement mutation owner, transaction/reservation protocol,
where the 120-second permission begins/ends, current authorization versus durable
intent, exact stage uniqueness, target commit evidence and all crash prefixes.
No replacement business writer, completion or recovery semantics are proposed
here. Authentication, activation and physical observations remain current facts,
not policy constants. New capability creation must remain process/thread/context
bound; any durable record is inspectable evidence only unless a future explicit
authorization contract defines more. This option is broad, not demonstrated
necessary, and cannot use legacy EXECUTING as a shortcut.

## 5. Threat model

| Threat | Prevention required in all candidates |
| --- | --- |
| Stale authentication/activation/approval | Fresh credential epochs/revocation/expiry, current incarnation and effective approval/ACK; reject mismatches rather than refreshing intent |
| Stale physical identity | Actual repeated observations; no caller host, filesystem continuity fiction or inherited reservation epoch |
| Changed stop/dependencies | Authoritative fresh checks at required use/commit boundaries; no old clear/ready certificate |
| Changed claims/history/control | Current full graph/exclusion and post-write proof; prepared content cannot validate current global state |
| Replay/duplicate issuance | One-use consent/consumption and serialized durable uniqueness, including cross-stage lineage if ever approved |
| Cross-process adoption | Live owner destroyed on exit; data lookup/relogin never restores an old process-local object |
| Uncertain commit/crash between phases | No usable publication or automatic retry/adoption; exact durable inspection and explicit future disposition policy |
| Reservation theft/replacement | Actual registered owner, paired connections/transactions/epochs; no raw handles or caller-supplied manager |
| Authority substitution | Exact canonical authority/action/scope/lineage binding and current authoritative lookup; no digest-only admission |

Trusted administrative access does not remove races, stale intent, mistakes,
duplicate requests, process failure or uncertain SQLite outcomes. Threat-model
simplification is not permission to remove these correctness/security guarantees.

## 6. Exactly what may survive a phase boundary

| Candidate | Evidence | Authority | Executable state |
| --- | --- | --- | --- |
| A | Immutable scoped historical intent/events; no current allow decision or cross-phase inventory token | Only original in-process owner under original deadlines; new grants UNRESOLVED | No adopted attempt; any retained inert record is not a credential |
| B | Bounded intent/data selected for independent current revalidation; exact payload UNRESOLVED | NONE from preparation; later final owner must originate a new explicitly consented grant | NONE from preparation; no old attempt can be converted/imported |
| C | Exact immutable predecessor/consumption history | No imported live predecessor; only a future independently authorized stage transition could issue successor permission | No implicit execution from stage evidence; exact allowed stage actions UNRESOLVED |
| D | Existing historical facts; live checks remain fresh | Original authority only until separately approved absolute expiry, not restart/import | Existing original-owner restrictions; no adoption |
| E | Historical intent/outcome facts, never opaque owner restoration | Replacement owner/action policy UNRESOLVED | Replacement state/commit proof UNRESOLVED; none granted here |

Current Z15 inventory remains confined to its original issuance phase; Z7 remains
attempt-local. No candidate implicitly extends those observations to another
ceremony or treats schema inventory as migration validity. Durable evidence may
survive a crash without granting permission; a future reader must distinguish it
from an actionable authorization. No signed or unsigned digest changes that rule.

## 7. Comparison

| Candidate | Preserves 120s ceiling? | New security model? | Main benefit | Main risk | Contract complexity |
| --- | --- | --- | --- | --- | --- |
| A: one ceremony, multiple phases | YES only with original absolute deadline; renewed grants change model | Yes for new grants; unchanged form already exists | Original owner continuity | Hidden renewal/cached admission; unchanged timing problem | High for new stage authorization |
| B: evidence then fresh final consent | YES for the final authority; no earlier authority to extend | Yes: evidence/final-request boundary, explicitly not old attempt adoption | Carries no authority across the boundary | Treating stale intent as admission; final work may still exceed 120s | Lowest conceptual expansion if useful data-only payload exists; exact contract still missing |
| C: phase authorities | Per-grant ceiling possible; aggregate exposure UNRESOLVED | YES | Explicit least-action grants | Escalation, multiple successors, disguised aggregate extension | Very high |
| D: longer lifetime | NO under current policy | YES | Fewer new ownership concepts | Unjustified exposure/credential intent and contention | Broad policy/consumer review despite small possible code diff |
| E: new runtime owner model | Design-dependent; UNRESOLVED | YES | Can reconsider costly composition directly | New transaction/authorization/uncertainty mistakes | Very high |

**Implementation feasibility for every replacement: UNMEASURED.** No table entry
asserts a performance improvement or worst-case completion bound.

## 8. Recommended security model and missing decisions

Prefer **B as a design direction only**: no pre-final authority, no attempt,
no capability surviving fresh authentication, no adoption, and independent
current final authorization. This preserves the reason for short-lived authority
more directly than repeated phase grants or a longer deadline. It is the smallest
defensible *conceptual* change, not a claim of smallest implementation or speed.

No candidate is currently sufficiently specified to implement securely. The next
decision must explicitly authorize or reject B's evidence-only/fresh-final-consent
boundary and define a useful exact payload without moving mutable allow decisions.
It must define the final owner/transaction/write set, old-state exclusions and
every uncertainty/replay outcome. If it cannot identify useful work that can move,
do not add an empty preparation ceremony or automatically choose C/D instead.
Retain the block and return to an explicit threat-model/architecture decision.

## 9. Explicit rejected alternatives

Reject automatic authority renewal, treating multiple 120-second grants as the
old lifetime, restarting the clock at publication, cross-phase mutable-result
caches, weakening physical or history/claim checks, imported old attempts,
browser identity/enrollment, synthetic legacy claims, secret/provider callbacks
that manufacture authority, automatic recovery/adoption, and lifetime extension
solely because the current implementation is slow. Do not retrofit old immutable
authority, attempt, approval or claim records into any candidate format.

## 10. Exact next implementation boundary

**There is no approved implementation boundary yet.** The next contract must
resolve the specific B decisions in section 8, including exact payload provenance,
selection/size/canonicalization, no-authority proof, original versus fresh consent,
final fresh predicates, exact owner/phase/commit ordering and protected readers.
It must preserve denial-safe authentication, old authority/claim/attempt conflicts,
current activation/profile/generation, audit and legacy isolation. No new schema,
format, route, ceremony, target-entry producer, writer or recovery API is specified
by this review. Later implementation and bounded feasibility validation require
their own explicit authorization.

## 11. Validation and production status

Only this document is created. Validation: `git diff --check`, document whitespace
and local-link checks. No pytest, lifecycle run, Z18, T, broad suite, production
code, schema, migration, authority/attempt/target state, writer/execution
capability, hosted/production access, commit or push.

PRODUCTION AUTHORIZATION: BLOCKED

PRODUCTION EXECUTION: BLOCKED

PRODUCTION ACTIVATION: BLOCKED

WRITER CAPABILITY: BLOCKED
