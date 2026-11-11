# 4e-20-Z17: runtime lifecycle composition architecture decision

## 1. Executive decision

**No executable composition A–E can currently be approved as demonstrated to
complete the full protected G+2 metadata path within 120 seconds.** Retain the
runtime block: option F's rejection of deployment is the present operational
decision. This is approval of an architecture decision, not of Z, T, an authority,
attempt, writer, execution path or production activation.

Option D, one original authority spanning multiple freshly validated phases, is
already the lawful composition. Retain it with Z15's narrow inventory change as
the only existing-contract candidate for a future measurement. This document
does not authorize that run. It does not establish D's post-Z15 feasibility or
approve any new owner, reuse class, shortened validation or replacement ceremony.

If new post-Z15 evidence still cannot establish completion, the next design must
explicitly reconsider the phase/authority composition or reject this runtime
path. Do not infer a new reuse contract or longer credential lifetime from cost.
Substantial restructuring may be necessary, but its necessity and safety are not
proven by an incomplete budget for the current implementation.

## 2. Z12 measured baseline

The single accepted Z12 trace in `.tmp/recognition-z12-deadline-trace.json`
reported these overall elapsed boundaries. Nested spans are not additive.

| Span | Start/end elapsed | Duration | Remaining authority at end |
| --- | --- | --- | --- |
| Issuance/coordinator admission, overlapping labels | 87.750–150.123s | 62.373s | 97s |
| Issuance finalization, nested | 127.085–150.120s | 23.035s | 97s |
| Attempt creation, including finalization | 150.123–244.265s | 94.141s | 3s |
| Attempt finalization, nested | 197.285–244.261s | 46.976s | 3s |
| Metadata admission, expired | 245.070–246.895s | 1.825s | 0s |
| Metadata call/result-publication span, failed | 244.265–246.898s | 2.633s | 0s |

No target mode transition, entry INSERT, target commit, reacquisition or
post-commit validation occurred. Those stages remain **UNMEASURED**. The failed
result span is not completed metadata cleanup/publication. No usable metadata
result or writer/execution capability was produced. The accepted review treats
the deadline failure as B; the diagnostic's narrow error-name classifier labeled
it C. No rerun merely to change that label is appropriate.

Preparation before authority issue time is not authority age. The 62.373s outer
span includes pre-issue work; only about 23s of the original window had elapsed at
publication. The actual deadline is the earliest of immutable issue time plus
120 seconds and existing credential/ceremony constraints. There is no guaranteed
120s available after publication, reservation reacquisition or phase entry.

Z12 demonstrates this measured composition failed on that fixture. It does not
prove a host-independent minimum duration or that every post-Z15 run must fail.

## 3. Z15/Z16 constraints and current implementation

[Z14/Z15-C](recognition-runtime-preauthority-preparation-late-issuance-contract-4e-20-Z14.md)
and [Z16](recognition-runtime-remaining-preparation-inventory-review-4e-20-Z16.md)
remain binding:

**Schema-inventory reuse does not authorize profile, claim-history,
authentication, activation, physical-identity, control, or migration-observation
reuse.**

Z15 prepares inventory in the original issuance transaction. Its predicates do
not cross issuance commit into the attempt transaction or metadata owner. Z6's
separate attempt-local observations do not create issuance or metadata permission.
All current migration rows/relationships and live kernels remain freshly checked.
No additional permitted preparation was identified by Z16.

The source flow is:

- [`runtime_activation_authority_issuance._issue_for_coordinator()`](../src/review/recognition/runtime_activation_authority_issuance.py)
  resolves the original registered owner, freshly evaluates current admission,
  checks exclusions/consent, prepares inventory, and stages the fixed five writes.
  `_body()` samples actual issue time only after confirmation CAS. `_final_mutations()`
  verifies actual graph/audit/protected-state changes and full control validity.
- [`runtime_execution_coordinator._phase()` / `_finish()` / `_promote()`](../src/review/recognition/runtime_execution_coordinator.py)
  retain control-first/target-second reservations, full final validation and
  control commit with target held. Only confirmed commit and both cleanups promote
  the private original continuation. Borrowed observations do not survive cleanup.
- `_create_attempt()` spends that continuation once; a fresh phase and
  `_persist_attempt()` validate before its three INSERTs and after the changed
  graph. Publication requires confirmed commit/cleanup and the original lifetime.
- [`runtime_execution_attempt_schema.validate_binding()` / `validate_expiry()`](../src/review/recognition/runtime_execution_attempt_schema.py)
  bind exact immutable authority ID/digest, require creation no earlier than issue
  time, and copy the original expiry exactly. Attempt creation cannot renew it.
- [`runtime_target_entry_owner.create_target_entry()`](../src/review/recognition/runtime_target_entry_owner.py)
  requires the genuine original created attempt, marks it spent and enters new
  control/target reservations. Metadata admission, mode changes, commit,
  reacquisition and publication retain their existing fresh checks and deadline.

Z15's successful focused integration took 165.20s including setup, and its
targeted regressions passed. Neither recorded the post-Z15 authority-stage budget
or the complete metadata path. Post-Z15 component times, remaining lifetime after
publication, attempt cost and complete-path feasibility are **UNMEASURED**.
Functional correctness is not timing feasibility. Do not subtract historical
schema-read costs from Z12 and claim a new budget.

## 4. Composition options A–F

### A — Late authority issuance

Permitted inventory preparation already precedes the confirmation CAS and issue
time sample. Moving only permitted work there is lawful within Z14/Z15's original
phase; no other observation has permission to move. Existing post-write checks
must still validate actual authority/lifecycle/audit records before publication.
Issue time cannot be rewritten after finalization or moved to publication to hide
that cost. Moving issuance after attempt creation violates the attempt's existing
authority/creation-time relationship and original-continuation protocol.

After issuance, full current finalization, confirmed commit/cleanup, original
continuation promotion, fresh attempt admission/creation/finalization, and every
metadata stage remain necessary. Z12's 23.035s plus 94.141s are observations of
that composition, not irreducible lower bounds or authority to move the checks.
Post-Z15 completion within 120s is **UNMEASURED**.

### B — Split attempt creation

Frozen proposal data and static computation may describe intent without execution
authority. They cannot establish a future attempt's current eligibility. Current
storage requires an existing exact authority and original continuation before
attempt insertion. Original `_persist_attempt()` also reevaluates admission before
writing, and `_finish()` validates the new graph and head afterward.

An additional preparation-to-commit split would need an exact contract for source
predicates, original owner/provenance, operation/profile/activation binding,
reservation/transaction/epoch changes, consent and deadline handling, actual write
proof, final fresh checks and every crash prefix. No such new split is approved.
Z6 alone does not move pre-insert validation to a pre-authority phase. A short
commit cannot simply assume away required validation. Safety and timing are
**UNRESOLVED / UNMEASURED**, respectively.

### C — Split metadata admission

The existing metadata owner already separates initial admission, mode change,
post-transition validation, row validation, target commit and fresh post-commit
reservation/validation. It is not a single cheap final decision. Complete metadata
timings are unavailable because Z12 expired in the initial admission.

An additional preparation split needs its own precise predicate and owner contract
across query-only/write-ready view invalidation, epoch changes, target commit and
connection replacement. No Z15 or Z6 observation crosses into these stages.
Current authentication, activation, actual physical/schema identity, claim/history,
control, approval/ACK, dependency, readiness, stop and deadlines remain fresh.
Independent bounded completion is **UNRESOLVED**; duration is **UNMEASURED**.

### D — Same-authority multi-stage lifetime

This already exists and is security-valid as a fail-closed composition. Original
outer provenance survives lawful phase cleanup, while each new reserved phase
has fresh views, connections/epochs and validation. Original deadlines accumulate;
no phase pauses or renews the clock. Equality is expired. A 120s-per-stage budget,
new rolling deadline or a detached reusable continuation would violate it.

Its full pre-Z15 measured lifecycle failed. Its post-Z15 complete lifecycle is
**UNMEASURED**. Multiple phases are legally possible; their count does not prove
sufficient time remains or guarantee completion under arbitrary suspension/load.

### E — Separate authority ceremonies

Fresh authentication/consent alone does not authorize adoption or retire old work.
Current authority storage is unique by operation ID, writer-manifest digest and
confirmation digest; immutable attempts reference their original authority ID and
digest. The private coordinator rejects preexisting authority rather than adopting
it. Its created-attempt registry and spent lifetime cannot be reconstructed by
another process/thread/ceremony. Renewing the same operation with a second 120s
authority would therefore conflict with existing lifetime/exclusion semantics.

A new operation with a new identifier cannot silently evade the manifest conflict,
old attempt or uncertain state. A separate later-stage authority could be considered
only under a new explicit authority-lineage, one-winner/exclusion, stage-consent,
authentication/activation/identity, ownership, expiry and uncertainty contract. It
must decide whether the change is prohibited adoption/renewal and how immutable
old references remain authoritative. Storage compatibility must be reviewed;
no table, transition, retirement or adoption rule is invented here. This option
is **not authorized**, safety **UNRESOLVED**, complete timing **UNMEASURED**.

### F — Reject/rearchitect the current lifecycle

Keeping the runtime blocked is a security-valid decision and the current
recommendation. No target action occurs, so no permission lifetime is extended.
Z12 establishes the measured path was unusable at its ceiling, and no complete
post-Z15 result establishes otherwise. This does not prove all possible designs
are infeasible or justify claiming that every remaining check has irreducible cost.

If the existing composition still fails after a separately approved current-path
measurement, a new architecture must explicitly address phase/authority ownership
and the mandatory checks; rejection remains the fallback if no acceptable contract
exists. Reinterpreting old attempts, adding a second ceremony, or silently widening
observation continuity is not an approved rearchitecture.

## 5. Decision matrix

| Option | Security-valid? | Fits 120s? | Existing contract support | New contract required | Implementation risk |
| --- | --- | --- | --- | --- | --- |
| A: latest permitted issuance | YES only within existing inventory scope; broader postponement UNRESOLVED | **UNMEASURED** post-Z15 | Z14/Z15; existing CAS/body/finalization ordering | Any further movement or timestamp/ordering change | Stale scope; inconsistent immutable timestamps/digests/audits |
| B: additional attempt split | **UNRESOLVED**, not authorized | **UNMEASURED** | Existing frozen intent and Z6 original attempt scope only | Explicit preparation/commit ownership, predicate coverage, exclusion and crash contract | Detached/adoptable intent; stale graph; attempt before authority |
| C: additional metadata split | **UNRESOLVED**, not authorized | **UNMEASURED** | Existing Z metadata owner, no imported observation continuity | Exact mode/epoch/commit/reacquisition and fresh-check contract | TOCTOU; stale identity; target/control uncertainty |
| D: one original authority across phases | YES with all existing fresh checks and fail-closed expiry | Pre-Z15 measured failure; post-Z15 **UNMEASURED** | Original coordinator continuation, attempt expiry and Z5 | None to retain current composition; any per-stage renewal needs a new policy and is prohibited here | Exhausted lifetime; spent/incomplete durable work; no completion guarantee |
| E: separate ceremonies for later phases | NOT under current contracts; replacement safety **UNRESOLVED** | **UNMEASURED**; two windows are not one proven 120s path | Fresh auth exists; renewal/adoption does not | New authority/stage lineage, consent, uniqueness, storage and uncertainty decisions | Renewal masquerading as fresh consent; adoption; multiple winners |
| F: reject/rearchitect | YES to continued rejection; future redesign UNRESOLVED | Rejection N/A; redesign **UNMEASURED** | Z5 fail-closed policy and current production fences | Explicit replacement architecture before implementation | Availability remains blocked; no authority exposure from rejection |

## 6. Security/TOCTOU analysis and required answers

1. **Minimum authority-bound work:** after actual authority construction, retain
   fresh current issuance finalization and exact record/audit checks, confirmed
   control commit/cleanup, original continuation, current attempt validation and
   immutable insertion/finalization, then every metadata admission/mode/commit/
   reacquisition/final check. Current credentials/consent/deadlines, activation,
   approval/ACK, physical identity/schema, dependencies/readiness/stop, claim and
   history/control state and exact reservation ownership remain authoritative.
   Pure preparation data cannot establish any of those allow decisions.
2. **Measured cost of that minimum:** no exclusive lower-bound measurement exists.
   Z12 measured issuance finalization at 23.035s and attempt phase at 94.141s,
   including its 46.976s finalization; metadata admission was incomplete after
   1.825s. These are observed composite costs, not a certified minimum. All later
   metadata costs and the post-Z15 budget are **UNMEASURED**.
3. **Expensive stages that cannot move:** current history/control/claim validity,
   live auth/activation/approval/ACK/dependency/stop/readiness/physical predicates
   and actual post-write graph/audit verification. Z16 grants no extra preparation
   for profile/claim historical subfacts or migration relationships.
4. **Can an authority-bound attempt avoid most of the window?** Not demonstrated.
   Z12's 94.141s consumed most of 120s. Z15 did not authorize changing that phase
   or prove a new attempt timing. A shorter split needs B's unresolved contract.
5. **Can metadata be independently bounded?** No demonstrated time bound. It
   currently inherits original expiry, not an independent 120s. A separate fresh
   decision still needs every required check and C's ownership/continuity review.
6. **Would a second ceremony be adoption?** Using it to continue an old attempt
   outside the original registered lifetime would be forbidden adoption under
   current contracts. New authentication is necessary for some future design,
   but insufficient to make that design legal or safe.
7. **Can preparation be destroyed between ceremonies?** Yes: Z15 evidence is
   volatile and discarded at phase exit/commit/uncertainty. Destroying it does not
   retire durable authority/attempt exclusions or create a new ceremony link.
8. **What is revalidated after boundaries?** Exact current scope, generation/G+2
   profile/install/owner/epochs, activation incarnation, credentials/deadlines,
   proposal/ACK/approval, dependencies/readiness/stop, physical/schema/fingerprint,
   history/control/claim graph, operation exclusions and new reservation/connection/
   transaction/epoch identity. Existing target-mode and post-commit checks remain.

Immutable row content is not immutable current eligibility. SQL reservations
cannot guarantee external filesystem continuity. Original outer lineage does not
preserve a prior connection, transaction or epoch. Hash equality alone establishes
neither freshness nor originating authenticated ceremony. No adopted observation,
synthetic witness, lease, global/TTL cache or caller-selected validation mode is
introduced to bridge those distinctions.

## 7. Crash/uncertain-commit analysis

9. **Every proposed boundary must retain these outcomes:**

| Boundary | Required outcome |
| --- | --- |
| Preparation before issuance | No durable preparation commit or authority; discard volatile data on failure/cleanup/exit. A new durable preparation would need a new contract. |
| Issuance CAS/five writes before control commit | Manager rollback under existing reservation ordering; no usable continuation. Do not assume earlier committed state is rolled back. |
| Issuance control commit/publication uncertainty | Stop, poison original owner, publish no usable continuation; existing read-only inspection only. No retry/adoption inferred from absence of a result. |
| Attempt insertion/control commit | Original continuation is spent. Keep exact rollback/confirmed-commit/uncertainty and incomplete-attempt fences; no alternate ceremony reconstruction. |
| Metadata before target commit | No usable result on failure; rollback only known uncommitted work through its manager. No automatic retry. |
| Metadata target commit or cleanup uncertainty | No usable result; durable read-only inspection, no adoption or inference of target outcome from missing control history. |
| Successful target commit/reacquisition | Fresh reservation/connection/epoch and post-commit validation; do not carry pre-commit authorization across it. |
| Proposed B/C/E new boundary | **UNRESOLVED** until its exact durable prefixes, original ownership, uniqueness and uncertainty handling are reviewed. Existing finalizers cannot be assumed to cover it. |

Control commit remains before target reservation release in issuance and attempt
phases. Metadata target commit and later validation are not a cross-database atomic
commit. A second ceremony cannot make an uncertain first commit certain. No recovery,
retirement, adoption, automatic retry or completion mechanism is specified here.

## 8. Feasibility evidence versus UNMEASURED items

10. **Can any executable option be proven feasible without another bounded same-run
    measurement? No.** Existing successful issuance tests omit the complete
    metadata path. A contract review cannot turn unmeasured stages into zero cost.
    Conversely, Z12 alone does not prove all possible post-Z15 runs infeasible.
11. **Smallest next evidence:** one separately authorized, bounded, post-Z15
    same-run trace of the existing option D composition, with only Z15's approved
    inventory preparation. It must retain the actual failure code, original
    issue/expiry and stage start/end/remaining budgets through confirmed cleanup,
    or fail closed at the first deadline. It needs no new observation reuse,
    production code, longer lifetime or second ceremony. No such run is authorized
    or performed by this document. If the diagnostic cannot record those facts,
    address that test-only reporting defect before asking it to prove feasibility.

The future trace must use one disposable G+2 fixture, independent valid activation,
one original authority/continuation lineage and the same accumulating live deadline.
No retry, adoption, stage renewal or combination of historical timings is permitted.
If it fails, retain all unexecuted stages as **UNMEASURED** and stop for an explicit
B/C/E/F architecture decision rather than another blind performance iteration.

Even a successful trace establishes feasibility under the measured conditions,
not a worst-case completion guarantee under arbitrary scheduling or host load.
The permission deadline remains authoritative regardless of availability.

## 9. Recommended architecture

12. **Recommend F's operational rejection now, while retaining D unchanged as the
    only current-contract measurement candidate.** Do not implement A beyond Z15,
    B, C or E on the current evidence. No additional preparation is approved, and
    there is no demonstrated need or permission for a longer lifetime.

This preserves exact originating consent/provenance, current checks, immutable
durable references and uncertainty fences. It also avoids claiming a new design
is faster without measured work or a contract defining what may move. If D cannot
be made feasible without unapproved semantics, explicitly redesign/reject the
lifecycle rather than weakening its security properties to force deployment.

## 10. Exact next boundary and validation

**No runtime implementation boundary is approved by Z17.** The next proposed
boundary is the single separately authorized current-path measurement described
in section 8, with complete test-only deadline/error reporting. That is not an
instruction to rerun Z12 here, create reusable evidence or enter T. A failure
returns to an explicit lifecycle rearchitecture decision; no micro-optimization
or lifetime extension is automatically selected.

Only this document is created. Validation: `git diff --check`, explicit new-file
whitespace and local-link checks. No pytest, Z12, Z, T or broad suites; no code,
schema, migration, cache, target action, authority/attempt/writer/execution
capability, hosted/production access, commit or push.

PRODUCTION AUTHORIZATION: BLOCKED

PRODUCTION EXECUTION: BLOCKED

PRODUCTION ACTIVATION: BLOCKED
