# 4e-20-G3: authorized atomic target-effect/witness enforcement decision

## 1. G2 blocker and decision

[G2](recognition-runtime-g1-issue-time-policy-action-binding-contract-4e-20-G2.md)
defines prospective policy, consent, action and original issuance-audit-prefix
binding. It does not authorize a runtime target writer. Existing authorities gain
no rights from that proposal.

**Assessment B: one specific new target security primitive is required: an
original-holder-only, decision-scoped atomic family-effect/witness transaction
enforcer.** This is a missing enforcement boundary, not evidence that SQLite
cannot atomically store the records. No implementation is authorized here.

## 2. Existing target transaction authority

The relevant implementation sources are `permanent.py`, `writer_boundary.py`,
`local_execution.py`, `runtime_target_entry_owner.py` and
`runtime_decision_outcome_journal_schema.py` under `src/review/recognition/`.

`permanent.finalize()` is the historical business writer. Without a leased
execution context it validates explicit manifest authorization, opens its writer
connection, starts `BEGIN IMMEDIATE`, repeats authorization/schema checks and owns
commit. With an accepted capability, the existing coordinator owns the transaction.
`_writer_connection()` obtains that connection through `writer_boundary.acquire()`.

`writer_boundary._local_lease()` requires a genuine existing execution context,
protected final-verification binding, exact manifest/claim, active connection and
strict target identity. It checks durable legacy `recognition_execution_claims`,
latest legacy `EXECUTING` history and absence of a seal. The production-operation
branch additionally verifies current control binding, activation, approval and
operation. `verify_local()` rechecks the registered context, connection, transaction,
target, manifest and durable claim. `acquire()` consumes its lease once. The
separate `_lease()` path is disposable-only, with its own authorization checks;
`production_guard()` rejects ordinary production authorization provisioning.

These permissions bind the existing legacy/disposable execution model, not the
new execution decision D or a G1 action. No copied authority ID, runtime claim,
G1 eligibility audit or journal row satisfies those capability checks. The runtime
metadata owner owns a reserved target transaction but its authorizer permits only
the exact target-entry metadata INSERT. Reservation ownership is not family-write
permission. Its commit does not authorize witness creation or business effects.

Consequently **no existing runtime target-side authority can commit the requested
G1 business-effect/witness action**. Legacy authorization remains unchanged; no
synthetic claim, `EXECUTING` event or substituted execution context is permitted.

## 3. Complete existing family-effect verification

Scope is the supported historical private First Look and Geography Steward
families, not live-first-look execution, Explorer, source/review mutation or
discrepancy correction. The runtime operation UUID must resolve its exact frozen
private manifest; the private operation key is `digest(manifest)`, not that UUID.

| Family effect / predicate | Authoritative source | Freshness | Verified by | Required inside target transaction? |
| --- | --- | --- | --- | --- |
| Exact rule, inputs, evaluation, population, identity history, ledger and candidates | Frozen approved manifest plus current target report sources and immutable completion ledger | Regenerate before any family write | `permanent._validate_manifest()` and `_prepare()`; exact equality with reviewed manifest | Yes; earlier preparation is insufficient |
| First Look qualifying competitors and selected assignment/reviewer/time per physical stop | Current report and captured `recognition_completions` | Whole population, including competing qualifiers | `_prepare()`, `_check_facts()` and `check_claim_integrity()` | Yes |
| First Look absence of prior claims and exact resulting claim set | `recognition_first_look_claims` and private operation | Before each insertion and after all insertions | `finalize()` collision checks and `_verify_operation_records()` | Yes |
| Geography independently certified scope identity, quality, exact active members and evaluation cutoff | Reviewed scope inputs, report, current `stop_gtfs_status` and completion ledger | Regenerate full report; no threshold override or changed membership | `_prepare()` and existing report/rule readers | Yes |
| Geography first catch-up identity, snapshot and complete membership | Scope identities, snapshots and members | Reject existing catch-up; verify complete resulting sets | `finalize()` and `_verify_operation_records()` | Yes |
| Geography exact awards, tiers, reviewer, time, numerator/denominator, percentage, size and witness assignments | Manifest candidates, snapshots, members and immutable completion facts | Verify actual resulting rows and exact sets | `check_geography_integrity()`, `_check_facts()`, `_verify_operation_records()` | Yes |
| Rule/operation identity and all family referential integrity | `recognition_private_rules`, `recognition_private_operations`, family rows and foreign keys | Before/after fixed writes as applicable | `_operation()`, `_verify_operation_records()`, `PRAGMA foreign_key_check` | Yes |

The fixed existing writes are private rule insertion when absent, private operation
insertion, and either First Look claims or Geography scope identities, snapshots,
members, awards and witnesses. Family witnesses here are assignment evidence,
distinct from the new decision-bound outcome witness.

These readers provide existing semantic foundations, not a new runtime producer.
They do not prove that a G1-authorized writer alone performed those writes or
that the outcome witness shares their commit. A matching digest alone does not
verify business effects. Existing idempotent `finalize()` return for a previously
stored private operation cannot adopt its effects into a new decision.

## 4. Atomicity and TOCTOU

SQLite can atomically commit supported business rows and an outcome witness if
both reside in the same target database and the same actual write transaction.
This storage property does not supply permission to execute that transaction.

The required boundary separates: preliminary read-only review; final fresh
security admission with control and target reservations held; target-local full
manifest regeneration inside the target transaction; fixed family mutation;
complete verification of resulting rows; internally derived decision/pending/effect
witness insertion; final permitted-state/deadline checks; and manager-owned target
commit. Any known precommit failure must roll back the entire target transaction.
Application sequencing across separate transactions is not atomicity.

Target writer reservation protects target-local data against competing SQLite
writers; control reservation protects relevant control changes by participating
writers. Neither establishes filesystem physical-identity continuity. Actual
physical/schema checks remain required. Authentication/time, independent activation,
approval/ACK, profile/generation/owner/epochs, dependencies, stop, history/claim/
control/migration/readiness and reservation checks remain fresh at required
boundaries. No reservation extends a credential deadline or freezes an external
emergency-stop source. No guarantee of instantaneous revocation during SQLite
commit, interruption exactly at expiry, or immunity to external file replacement
is inferred. The missing enforcer must define and enforce its final admission and
commit responsibility within those existing limits; it cannot reuse an old allow
decision as a substitute.

Control journal commit and target commit are separate. There is no cross-database
atomicity claim. A committed target with pending/uncertain control is a valid
failure prefix requiring factual inspection, never repeat mutation.

## 5. Witness authority and the single missing primitive

The Z31 target witness codec binds the complete decision, unique pending event,
recorded time, `TARGET_COMMITTED` outcome and effect-evidence digest. It validates
content relationships, not producer permission or the truth of the effect digest.
Its inert SQL package is not an installed runtime writer or attestation service.

The missing **atomic family-effect/witness transaction enforcer** must exclusively
consume the prospective G1 original holder's one exact action and own its actual
target transaction through commit. Its indivisible responsibilities are:

- Verify original live holder, confirmed G2 eligibility/source audit and exact D,
  operation/private manifest, target, pending event and all current admission.
- Bind actual process/thread, runtime incarnation, connection, transaction and
  reservation lineage; accept no caller SQL, replacement scope or witness digest.
- Permit only the exact supported fixed family writes and one internally derived
  unchanged Z31 outcome witness, after complete precondition/result verification.
- Enforce permanent duplicate exclusion and one exercise; retain no transferable,
  renewable, retryable or recoverable permission.
- Own rollback/commit, suppress usable publication on uncertainty and provide
  authoritative positive effect/witness verification for outcome-only inspection.

This is one combined privileged enforcement primitive, not several new authority
classes. Its concrete authorizer, exact effect-evidence derivation/verification
and ownership interface do not exist merely because their obligations can be
listed. They are not implemented or approved by this decision. G1 eligibility
does not itself toggle target query-only or entitle a raw connection to write.

## 6. G1 boundary

Only a prospectively eligible original source under exact P/C/Q/E from G2 could
be a future input, with its original at-most-120-second deadline and all shorter
bounds. The action remains one authority, one D/body digest, one operation and
private manifest, one target, complete family-effect set, one pending/witness,
one original runtime and actual reservation/transaction. Unknown policy, conflicting
scope or absent original registration denies use. Existing authorities remain
ineligible. No grant implementation or new rights are created here.

Neither detached source/consent/audit DATA nor a witness can recreate the original
owner after process/thread/context loss. No transfer, re-delegation, renewal,
retry, arbitrary SQL, target selection, general writer or recovery execution is
authorized. An opaque identifier alone would not enforce these properties; the
missing privileged consumer must enforce them.

## 7. Crash matrix

This table states required outcomes, not a claim that a new producer exists.

| Failure point | Family effects | Business effect | Witness | Commit | Recovery |
| --- | --- | --- | --- | --- | --- |
| Before transaction | No new writes | Absent | Absent | None | Preserve any confirmed journal exclusion; no reconstructed right |
| During verification | Read-only preconditions may be incomplete | Absent | Absent | None | Reject; no success inferred |
| After verification | Preconditions are historical observations only | Absent | Absent | None | Lost original ownership cannot be adopted |
| During business effect | Partial uncommitted fixed rows possible | Uncommitted | Absent | Not confirmed | Known rollback removes all; otherwise inspect, do not retry |
| After effect before witness | Complete rows may be uncommitted | Uncommitted | Absent | Must not commit this prefix | Whole rollback required; absence alone is not failure proof |
| After witness before commit | Actual effects verified inside transaction | Uncommitted | Uncommitted | Not confirmed | Known rollback removes both; unknown outcome stays fenced |
| After target commit | Complete effects must verify durably | Durable if commit succeeded | Same committed transaction | May be confirmed or response uncertain | Positive exact target proof only; control outcome may still be pending |

Process memory, successful INSERT return, timeout or lack of response proves
neither commit nor rollback. Crash resolution cannot create a fresh mutation right.

## 8. Uncertain commit and journal relationship

The Z30/Z32 protocol requires confirmed control decision/genesis and sole
`TARGET_PENDING` before mutation. Unknown control commit publishes no usable start.
Unknown target commit publishes no usable success and triggers no automatic retry,
reconnect/adoption or second action. Keep durable operation/manifest exclusion.

Outcome-only authoritative inspection must establish intended target identity,
schema/lineage and a committed snapshot; look up exact D/body and pending witness;
validate canonical content; resolve original authority and G2 P/C/Q/E audit chain;
and independently verify the complete actual effect records against the approved
manifest and witness effect digest. Only positive proof permits factual COMPLETED
recording with linked control audit. Missing/mismatching rows, unclear restore
lineage or inaccessible target cannot prove safe failure or authorize re-execution.
Positive original-manager no-commit evidence is required for TARGET_FAILED.

The existing journal inspector can validate structural/canonical relationships;
it cannot establish producer privilege or complete effect truth from a digest.
Thus current target state/codecs alone do not supply the required authoritative
resolution. That verification belongs to the same missing enforcement/attestation
primitive, not a recovery executor. An independently authorized factual recorder
may record proven outcome without reviving expired mutation permission.

## 9. Durable duplicate fencing

Z31 `definitions('target')` defines `recognition_runtime_outcome_witnesses` with
primary key `authority_id`, uniqueness of authority digest and body digest, and
unique `(installation_id,target_id,operation_id)` and
`(installation_id,target_id,writer_manifest_sha256)`. Immutable UPDATE/DELETE and
collision INSERT/REPLACE guards preserve those exclusions. Control decisions use
the corresponding keys; history permits one ordered pending transition, not a
second execution start. These are inert definitions, not deployed guarantees.

If installed and consumed by an authorized producer, unique witness insertion
inside the same transaction would force rollback of a second attempted effect
transaction on collision. A constraint alone cannot stop a writer that commits
effects without inserting the witness. Existing family uniqueness likewise does
not bind effects to D. Mandatory witness participation is the missing enforcer's
obligation. No new fence is invented here.

Concurrent originals must serialize through control-first/target reservations;
BUSY/LOCKED remains visible, without retry loops. Duplicate requests, stale grants,
replayed decisions and restart cannot reconstruct original permission. Successful,
failed or uncertain terminal outcomes never delete exclusion. Recovery reads facts;
it cannot reset pending, fabricate a new D for the same excluded operation/manifest,
or use legacy idempotence to claim a new decision's success.

## 10. Source-audit coupling

The minimum chain is G2 original issuance audit prefix E/P/C/Q -> exact original
authority D/body -> control decision and unique pending -> same-transaction target
effects and witness -> factual control outcome and its audit. Full references must
resolve and agree; a hash without the referenced validated graph is insufficient.
The target witness already contains decision/source and pending references; no
extra witness fields or later lifecycle codecs are defined here. Policy attribution
is indirect through the immutable original G2 eligibility audit, not a new target
authorization flag. Existing source formats remain unchanged.

The target proves actual effects, source audit establishes intended prospective
entitlement, and control journal records outcome. None overrides a conflicting
domain or independently grants write permission. Audit integration and exact
producer checks are obligations, not currently accepted arbitrary audit inserts.

## 11. Decision B and architectural stop

Existing SQLite target storage can support atomic effects plus witness, and
existing family readers provide substantive verification foundations. Existing
authority consumers do not enforce the new source-bound action. Therefore A is
not established. No evidence demonstrates fundamental incompatibility, so C is
not justified either.

**B: the one missing primitive is the original-holder-only decision-scoped atomic
family-effect/witness transaction enforcer defined in section 5.** G1/G2 resolve
prospective entitlement policy, not that consumer's permission/write/commit proof.
The architectural chain stops. The unresolved boundary is explicitly identified;
no implementation slice, optimization, schema change or executor is proposed.

## 12. Validation and production blocks

Documentation only: document whitespace/local-link checks and `git diff --check`.
No pytest, Z18, T, broad suite, code/schema/migration, grant, witness production,
target DML/DDL, hosted/production access, key read, commit or push. The 120-second
ceiling and all fresh validation remain unchanged. No runtime feasibility claim.

PRODUCTION AUTHORIZATION: BLOCKED

PRODUCTION EXECUTION: BLOCKED

PRODUCTION ACTIVATION: BLOCKED
