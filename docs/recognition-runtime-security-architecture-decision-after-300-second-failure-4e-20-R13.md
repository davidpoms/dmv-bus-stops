# 4e-20-R13 - security architecture decision after the 300-second failure

## 1. R12 baseline and decision

**Recommendation E - INSUFFICIENT EVIDENCE.** The evidence establishes failure
of the measured composition within 300 seconds, but does not establish a safe
600-second policy, an authorized shorter ceremony, or the necessity of a
replacement authority model. Retain current fail-closed behavior pending a
separately authorized security decision. This is a completed assessment whose
substantive result is uncertainty, not an implementation authorization.

[R12](recognition-runtime-security-v2-300-second-lifecycle-feasibility-4e-20-R12.md)
contains one valid isolated v2/300-second expiry trace, zero complete lifecycle
samples, and no harness timeout. Parent elapsed was 470.152 seconds; child
diagnostic elapsed was 465.818 seconds, including pre-authority setup. The exact
failure was `AdminError: administrative_session_expired_or_revoked` with zero
authority budget, during metadata-owner final validation before target commit.
That error label must not be rewritten as a different product error or treated
as proof that the original longer-lived session credential expired.

## 2. Measured critical path and authority consumption

Times below are from the single R12 child. Authority construction occurred at
child elapsed 166.516547 seconds. Approximate authority ages subtract that
observed construction instant; actual expiry uses the recorded UTC timestamps
and whole-second precision. No overlapping spans are added.

| Boundary / interval | Child elapsed, seconds | Duration, seconds | Authority remaining at end |
| --- | ---: | ---: | ---: |
| Authority issuance / coordinator admission, overlapping | 116.942-197.201 | 80.259, counted once | 269 |
| Z15 schema preparation, nested before authority construction | 166.501-166.506 | 0.004282 | Not yet issued |
| Issuance final validation, nested | 166.539-197.197 | 30.659 | 269 |
| Attempt creation, including its final validation | 197.201-307.195 | 109.994 | 159 |
| Attempt final validation, nested | 256.130-307.192 | 51.062 | 159 |
| Metadata-owner admission | 308.113-355.326 | 47.213 | 111 |
| Controlled write-mode transition | 355.327-355.999 | 0.673 | 110 |
| First metadata final validation | 355.999-405.916 | 49.916 | 60 |
| Metadata INSERT trace interval | 405.919-405.922 | 0.002740 | 60 |
| Second metadata final validation | 406.393-453.689 | 47.296 | 12 |
| Return to query-only | 453.689-454.169 | 0.480 | 12 |
| Third metadata final validation, incomplete | 454.169-465.809 | 11.640 | 0 |
| Coordinator failure cleanup | 465.817140-465.817331 | 0.000190 | 0 |
| Target integrity inspection and commit | UNMEASURED | UNMEASURED | UNMEASURED |
| Reservation reacquisition | UNMEASURED | UNMEASURED | UNMEASURED |
| Post-commit validation and successful result publication | UNMEASURED | UNMEASURED | UNMEASURED |

Approximately 189.483 authority seconds elapsed before the first metadata final
validation, and 287.653 before the third, failing validation. The metadata parent
span was 158.622 seconds and contains the metadata rows above; it is not an
additional cost. Approximately 49.574 seconds of issuance/admission preceded
authority construction and did not consume its lifetime. Subtracting the
300-second ceiling from total parent time would misstate available headroom.

The INSERT interval includes bookkeeping through the next non-trigger statement;
it is not an isolated database execution benchmark. No target commit was reached,
no durable entry was demonstrated, and failure cleanup published no usable result.

## 3. Authorization-sensitive work versus preparation

The measured expensive intervals are validation, not business mutation. That
does not make them freely movable. The metadata owner's `_evaluate_kernel()`
checks current admission, exact subject/authority/attempt, current graphs and
consent, target/control invariants and time. Its caller validates after mode
changes, after insertion, before commit and after reservation reacquisition.
See [the owner](../src/review/recognition/runtime_target_entry_owner.py).

The final failing validation is required under the original unexpired authority:
the genuine CreatedAttempt inherits that authority and original coordinator
lifetime. Moving it outside that lifetime or replacing it with an earlier allow
decision changes the authorization contract. R12 did not profile exclusive
subcomponent costs in these spans, so it cannot identify a newly redundant read.
Only Z15 schema inventory is approved preparation; it executed once with 2,813
reused inventory reads. Migration relationships and live security state remain fresh.

## 4. Reassessment of 120 and 300 seconds

[R7](recognition-runtime-security-lifetime-policy-parameterization-assessment-4e-20-R7.md)
supports finite, short, immutable versioned authority rather than a universal
security theorem at exactly 120 seconds. Historical v1 nevertheless means 120
seconds, and current default issuance remains v1. Historical existence does not
prove optimality. R12 is not a new v1 measurement and does not show that every
possible implementation fails at 120.

[R8](recognition-runtime-security-lifetime-v2-300-second-policy-decision-4e-20-R8.md)
conditionally assessed prospective 300-second exposure; it did not prove
operational sufficiency or adopt v2. R12 now shows that this actual v2 run still
expired before commit. Neither current policy nor existing authorities change.

## 5. Hypothetical 600 seconds

Keeping the measured prefix unchanged, a hypothetical 600-second authority would
have roughly 300 seconds left at the observed failure boundary. That is a
counterfactual budget, not measured completion headroom: the remaining third
validation, integrity inspection, commit, reacquisition, post-commit validation
and successful publication have no complete timings. Original consent had 503
seconds remaining at authority construction, so that same source would clip a
600-second candidate to at most 503 seconds even before considering other bounds.
No source credential or consent may be extended to make this arithmetic work.

Thus 600 might permit more progress, but remains another unproven ceiling. It
would permit up to twice v2's and five times v1's authority age when sources allow.
R12 alone supplies neither complete operational margin nor a security rationale
for that exposure. Longer lifetime compensates for expensive composition; it
does not solve a missing authorization or atomicity primitive. No v3 is defined.

## 6. Security properties and viable-option comparison

| Property | Retain current policy and limitation | Hypothetical longer policy | Proposed short final ceremony |
| --- | --- | --- | --- |
| Authority freshness | Existing immutable expiry, fail closed | Older original intent; new prospective approval required | New placement of grant/expiry needs explicit contract |
| Consent freshness | Original current checks and clipping | Consent is not renewed; may clip longer ceiling | Fresh consent and exact consumption boundary must be defined |
| Credential expiry | Original credentials remain authoritative | Never extends credentials | Cannot replace authentication with prepared evidence |
| Replay / duplicate fencing | Original one-use continuations and durable exclusions | Unchanged requirements; time alone is not a replay fence | Must preserve exact single-winner semantics |
| Concurrency | Manager reservations and epochs remain mandatory | Longer exposure does not create continuity | New ownership/epoch transitions need authorization |
| Target authorization | Metadata-only existing owner; no business authority | More time grants no extra target rights | Final write entitlement cannot derive from prepared data |
| Atomicity | Existing separate control/target transactions | No new cross-database atomicity | Combined owner/write set is not currently authorized |
| Crash / uncertain commit | No usable publication, automatic retry or adoption | Same fences; expiry does not prove rollback | New crash prefixes require a reviewed protocol |

Fresh activation, stop, physical identity, approval/ACK, dependencies and current
history/claim/control checks remain mandatory in every option. Independent
controls reduce but do not erase longer stale-intent exposure. Preparation never
becomes a writer, executor, replacement credential or recoverable authority.

## 7. Architecture options A-F

| Option | Assessment under existing contracts |
| --- | --- |
| A - retain 120 and accept limitation | Safe current operational disposition: blocked path fails closed. Does not establish that accepting the limitation indefinitely is the correct project objective. |
| B - increase to 600 | Not justified by this incomplete prefix. Original-source clipping, exposure approval and remaining cost are unresolved. |
| C - lifecycle decomposition | Z15 inventory already permitted; broader movement is not authorized. Mutable checks and post-write graphs cannot be prepared as reusable allow decisions. |
| D - fresh-late ceremony | Not expressible as a simple existing-owner rearrangement. A genuinely new reviewed owner/write-set and final entitlement could be considered without assuming G1, but neither exists as an approved implementation boundary. |
| E - replacement authority model | Existing-model composition conflicts are documented, but timing alone does not prove replacement is necessary or G1 is sufficient. |
| F - insufficient evidence | Selected architecture assessment: cannot safely distinguish a justified larger ceiling from a newly authorized shorter ceremony or replacement. Stop rather than infer permission. |

[Z21](recognition-runtime-authority-issuance-composition-contract-4e-20-Z21.md)
already places live work before construction where allowed.
[Z26](recognition-runtime-replacement-finalization-owner-write-set-decision-4e-20-Z26.md)
requires committed original continuation, separate exact issuance/attempt write
groups and the protected metadata owner. It expressly does not authorize combining
them into a new finalizer. R12 changes timing evidence, not those ownership rules.

## 8. G-series disposition, recommendation and next boundary

G1 is **potentially useful but unproven**; it is neither established as required,
made unnecessary, nor superseded by an already-authorized simpler approach.
Delegation/producer entitlement and atomic family-effect/witness authority are
different questions from metadata validation latency. No G-series continuation
or implementation follows automatically.

**Recommendation E - INSUFFICIENT EVIDENCE.** Preserve v1/default and existing
v2 historical representation, blocked execution and current fail-closed behavior.
Do not adopt 600, redesign owners, move fresh checks or run another measurement
on the strength of this assessment.

The next boundary is an explicit project security/architecture decision on
whether to accept the operational limitation or separately authorize a new
finalization ownership/write-set contract. Such authorization must resolve the
Z26 conflicts, fresh-check placement, original-holder entitlement and uncertain
commit semantics before implementation; it must not assume G1 or authorize a
larger lifetime implicitly. R13 does not choose an unproven replacement design
or propose another performance slice.

## 9. Validation and production blocks

Only this document was added. Read-only R12 trace, R7/R8, Z21/Z26 and current
metadata/coordinator source inspection; document whitespace/local-link checks
and `git diff --check`. No pytest, lifecycle, Z18, T or broad suite; no code,
policy, schema, migration, permissions, credentials or database changes. No
hosted/production resources, authority issuance, G1, producer, commit or push.

PRODUCTION AUTHORIZATION: BLOCKED

PRODUCTION EXECUTION: BLOCKED

PRODUCTION ACTIVATION: BLOCKED
