# 4e-20-Z26: replacement finalization owner/write-set decision

## 1. Z25 conclusion and final disposition

[Z25](recognition-runtime-fresh-finalization-ceremony-contract-4e-20-Z25.md)
concluded C: existing fresh consent/issuance/attempt composition repeats the
already-blocked lifecycle. This last existing-contract review concludes
**B. Existing contracts do not permit a replacement combined owner/write set;
a genuinely new security-model contract is required.** Stop this boundary.

The current outer coordinator already owns the overall original lifetime. That
does not mean one reservation-local owner can combine all writes, discard phase
finalization, or replace the target-entry manager. Reusing an existing SQLite
table is not authorization for a new producer or transaction protocol.

No further optimization, timing run or speculative implementation slice is
proposed. The authority maximum remains 120 seconds. The Z18 measured failure is
evidence against the current implementation, not proof against all possible models.

## 2. Existing mutation inventory

Sources:
[`runtime_activation_authority_issuance.py`](../src/review/recognition/runtime_activation_authority_issuance.py),
[`runtime_execution_coordinator.py`](../src/review/recognition/runtime_execution_coordinator.py),
[`runtime_target_entry_owner.py`](../src/review/recognition/runtime_target_entry_owner.py)
and [Z20-R](recognition-runtime-attempt-preparation-late-finalization-contract-4e-20-Z20-R.md).

“Fresh checks” below means current authentication/consent/deadlines, exact
operation/proposal/ACK/approval, finalized G+2 scope/profile/generation/install/
owner/epochs, independent activation, readiness/dependencies/stop, actual physical
identity/schema/fingerprint, history/claim/control integrity and genuine current
reservations. Each owner additionally proves its actual permitted writes.

| Mutation | Existing owner | Required authority | Required fresh checks | Must be atomic with | Can owner change? |
| --- | --- | --- | --- | --- | --- |
| Confirmation `used=0 -> used=1` CAS | Private issuer under original coordinator issuance phase; standalone public issuer has separate existing manager | Current exact owner consent and one-use artifact; original coordinator for continuation | Exact subject/credentials/artifacts/expiry, all issuance checks and exclusions | Entire five-write issuance group | NO under existing contracts |
| Canonical authority INSERT in `recognition_runtime_execution_authorities` | Same issuance owner | Actual authority constructed after CAS from current authoritative subject | Fresh checks plus canonical scope/digest/time and projected row integrity | CAS, consumption audit, AUTHORIZED genesis, issuance audit | NO |
| AUTHORIZED INSERT in `recognition_runtime_execution_lifecycle` | Same issuance owner | Exact newly inserted authority | Exact genesis/authority/audit graph | Same issuance group | NO |
| Consumption and issuance audits in `recognition_admin_audit` | Same issuance owner through `_audit` | Exact actual consent consumption/authority/genesis facts | Current predecessor/time/actor and actual suffix | Same issuance group | NO |
| Attempt INSERT in `recognition_runtime_execution_attempts` | Original coordinator's separate attempt phase | Genuine original continuation after confirmed authority commit and cleanup | Full fresh attempt admission, current authority binding/expiry/exclusions | Exact history and creation audit | NO |
| ATTEMPT_CREATED INSERT in `recognition_runtime_execution_attempt_history` | Same attempt owner | Exact attempt and its authority | Actual attempt digest, sequence 1, time, owner/reason, null predecessor | Attempt and creation audit | NO |
| Attempt creation audit | Same attempt owner | Exact newly written attempt/history | Current chain head and exact event/attempt digest | Three-write attempt group | NO |
| Target-entry INSERT in target `recognition_runtime_execution_entries` | Existing protected metadata owner | Genuine original CreatedAttempt, same original authority/lifetime; no writer authority | Full metadata admission before/after mode change, actual entry integrity, target commit and reacquired reservation validation | Its target-local metadata transaction, not the earlier control transactions | NO |
| Reservation/mode/epoch/phase transitions | Corresponding manager | Exact registered phase and original outer | Actual PID/thread/context/connections/transactions/query mode/epochs/time | Lifecycle ordering, not a fourth durable row | NO delegation or caller control |

The canonical authority row is not a second authority write. AUTHORIZED evidence
is exactly `format`, `authority_id`, `authority_sha256`; the enclosing genesis
event has separate unchanged fields. No new lifecycle evidence, writer, completion,
seal, readiness receipt or legacy execution record belongs in these groups.

Existing authentication denial reductions are a separate manager-controlled
failure path; they are not extra successful finalization writes or permission to
relax a group's exact mutation proof.

## 3. Candidate existing owners

All candidates require genuine private registration, exact PID/thread/context,
active lifetime and actual owned connections/transactions/epochs. None can accept
a supplied compatible-looking state, raw connection or validation callback.

| Existing candidate | Authentication / authority boundary | Reservations, transactions and target | Failure / uncertainty / duplicate fencing | Complete replacement owner? |
| --- | --- | --- | --- | --- |
| Original coordinator outer plus issuance/attempt phases | Validates original genuine credentials; private original issuance then one-use continuation; no imported authority | Own control-first/query-only-target reservations per phase; permits issuance five writes OR attempt three writes; target mutation denied | Poison on failure; known rollback, no uncertain publication; exclusions/CAS/UNIQUE authority and spent continuation | NO: it already orchestrates the blocked composition, not one combined phase |
| Standalone issuance owner | Current credential/consent subject; public duplicates are inspection DATA only | Dedicated control commit while target remains query-only/reserved; fixed issuance writes | Exact five-write proof, no publication before commit/cleanup; duplicate lookup cannot mint continuation | NO: no attempt or target-entry authority |
| Consent owner | Protected current TOTP/step/confirmation, not authority issuance | Fixed consent control writes; target reserved/query-only; own final commit | Existing denial/throttle/replay semantics; exact consent proof and uncertainty fences | NO: cannot become issuer/coordinator/metadata owner |
| Activated read-only owner | Validates existing auth, approval/readiness/current activation; produces observation only | Success read-only, fixed denial handling; query-only target | Poison/deny on misuse; no mutation permit or adoptable result | NO: observer cannot be promoted to writer or finalization producer |
| Metadata target-entry owner | Validates exact genuine CreatedAttempt from original outer; inherits original auth/authority deadlines, not new authority | Owns control reservation plus target; only exact metadata INSERT enabled after mode transition; target commit/reacquisition; successful path no control mutation/commit | Spend result once; failure poisons original; unknown target outcome publishes nothing; exact-entry fences and no adoption | NO: cannot issue authority or create attempt/control graph |

The 3a authentication owner, preactivation claim owners, proposal/approval owners
and legacy execution/writer components are also not candidates for this activated
combined transition: their fixed actions, state policy and registries prohibit
that promotion. Shared kernel functions do not convey producer ownership.

## 4. Candidate write-set decompositions

| Decomposition | Existing support | Required ordering / reason |
| --- | --- | --- |
| Authority separated from confirmation consumption | NO as independent commits | One-use decision and actual grant must resolve together; standalone consumed confirmation or granted authority would violate exact five-write graph/proof |
| Genesis or either issuance audit separated from authority | NO | Existing canonical graph, audit/FK/trigger linkage and finalization require actual complete issuance group, not a repairable orphan prefix |
| Attempt separated from ATTEMPT_CREATED/history/audit | NO | Actual immutable three-row graph, deferred audit FK and exact audit guard/proof require one control transaction |
| Issuance group, then attempt group | YES, existing original-owner protocol only | Confirm issuance control commit with target held, complete both cleanups, promote original continuation; spend once, reacquire fresh reservations, fully revalidate current authority/scope/eligibility, insert/finalize/commit attempt and clean up |
| Attempt group, then target-entry | YES, existing metadata protocol only | Confirm attempt commit/cleanup and original CreatedAttempt; spend original result once; fresh metadata reservations and admission; controlled mode transition; entry INSERT; final checks; target commit; reacquire and freshly validate; cleanup/publication |
| Combine issuance and attempt in one phase | NOT permitted by existing owner contracts | Attempt requires committed original continuation; issuance `_final_mutations` proves exactly five writes, attempt `_final_attempt` exactly three. Authorizers are phase-specific. New eight-write owner/proof is **UNRESOLVED** |
| Combine either control group with target-entry into one atomic finalization | NOT permitted | Query-only control owners lack target INSERT permit; metadata requires committed original attempt. No reviewed combined ownership or cross-database commit/uncertainty protocol exists: **UNRESOLVED** |

No new PREPARED, continuation ledger, resumable token or other durable bridge is
introduced. Existing incomplete states remain fail-closed historical states,
not a reason to repair audits or promote orphans automatically.

## 5. Atomicity analysis

The smallest supported durable sets remain:

1. One control transaction: confirmation CAS, consumption audit, authority,
   AUTHORIZED genesis and issuance audit.
2. Another control transaction: attempt, ATTEMPT_CREATED history and creation audit.
3. Later target transaction: exactly one metadata entry, under the metadata owner.

Each group's database writes have local atomicity. Reservation epochs, borrowed
view invalidation, cleanup and process-local result publication are not durable
rows atomically committed with those writes. They have separate ordered ownership
requirements. There is no cross-database atomicity. Control commit precedes target
reservation release in issuance and attempt phases. Metadata intentionally commits
target, reacquires/validates, and resolves its unchanged control reservation without
using that resolution as evidence of atomic target/control commit.

Moving all SQL onto one connection or one outer object would not prove identical
authorization. It would remove existing committed-continuation prerequisites,
change exact write baselines and audit sequences, and require a new finalizer and
failure policy. Existing storage alone cannot grant those permissions.

## 6. Security and TOCTOU tests of the splits

“Reject” below describes required existing behavior, not tests run in this review.

| Security question | Existing ordered split | Proposed combined/replacement split |
| --- | --- | --- |
| Obtain later phase without predecessor? | Attempt requires original committed continuation; metadata requires registered original attempt result | **UNRESOLVED** predecessor/owner proof if those boundaries are removed |
| Adopt another ceremony's earlier phase? | Private original outer/notice/phase/result identities reject; historical rows do not recreate them | **UNRESOLVED** if a new owner consumes historical IDs instead |
| Authentication change/expiry? | Fresh primary/session scope, owner/auth/MFA epochs and all original deadlines reject changed/expired scope | All checks must remain; no approved replacement placement/proof |
| Activation change? | Fresh exact incarnation and subject comparison reject substitution | Must remain fresh; new boundary **UNRESOLVED** |
| Approval/proposal/ACK change? | Current exact pairing/effective approval and subject equality reject | Cannot retain old allow decision; proof **UNRESOLVED** |
| Physical identity change? | Actual strict hostname/path/device/inode/schema/fingerprint checks repeated; SQL reservation is not continuity | No new witness exists; elimination is not permitted |
| Stop or dependency/population change? | Fresh stop/block, dependency and required manifest checks reject | No cached clear/ready certificate; placement **UNRESOLVED** |
| Claims/history/control change? | Current graph/exclusions, baselines, exact writes/audit/FKs and migration relationships checked in each phase | Changed mixed graph would need new exact validation contract: **UNRESOLVED** |
| Reservations change or race? | Current phase proves exact owner/connections/transactions/epochs/query mode; reacquisition receives fresh validation | Same outer alone insufficient; new transition protocol **UNRESOLVED** |

The supported splits preserve freshness by doing the required work again. They
are not a reduced-cost replacement. Schema inventory reuse remains confined to
approved Z15/Z7 phases; no mutable observation or complete admission crosses.

## 7. Crash and uncertain commit

An issuance rollback resolves only known uncommitted issuance work, not earlier
consent commits. A later attempt rollback does not remove committed authority.
Attempt/metadata inputs are spent in their original lifetime even when failure
prevents publication. A crash can leave historical authority/attempt/entry rows,
but not a resumable executable credential. No writer/execution capability is
created by these records.

Uncertain control commit cannot create a second grant through retry: poison the
owner, publish nothing usable, stop for read-only durable inspection. Existing
exclusions still apply to another request. Target commit/cleanup uncertainty
also stops without adoption; missing control history does not prove target rollback.
Cleanup or result-publication failure cannot recreate the original private notice
or continuation. Confirmed rows without publication are not an adoptable handoff.

New crash prefixes for an eight-write or mixed target/control protocol are
**UNRESOLVED**. Neither old finalizer can be assumed to cover them. This is an
authorization/uncertainty gap, not a reason to add automatic recovery.

## 8. Adoption and concurrency

Control BEGIN IMMEDIATE serializes competitors, while current durable exclusions,
confirmation CAS, unique/immutable guards and original single-use continuation
fence duplicates. Metadata result consumption is additionally tied to its genuine
original coordinator and exact attempt. No process-local flag substitutes for
durable uniqueness; no durable row substitutes for live ownership.

Public exact-duplicate issuance is inspection only, never a new private original
continuation. A new login/process, equal digests, matching physical observations,
or new activation cannot adopt or rebind an earlier authority/attempt. Competing
requests must reject conflicts rather than regenerate a missing predecessor.
No replacement concurrency/adoption rule is supplied by the currently shared
tables; changing these relationships requires a genuinely new security model.

## 9. Decision B

**Existing contracts do not permit a replacement finalization owner/write set.**
No existing component owns the entire combined transition with appropriate
authorizers, committed-predecessor requirements, exact mutation proofs, reservation
ordering and uncertainty handling. Existing safe separation is exactly the
composition already blocked by the measured 120-second budget. It cannot be
repackaged as a new owner or a shorter finalization by a documentation alias.

This is the final existing-contract determination for this boundary. Stop; no
new speculative implementation or optimization slice follows from it.

## 10. Exact next boundary and validation

The only possible next design boundary is an explicitly commissioned **new
security-model contract**. It must deliberately decide which original-authority/
committed-continuation/phase-ownership invariants are superseded and define their
replacement authorization, atomic write groups, predecessor provenance, freshness,
durable single-winner and crash/uncertainty guarantees. No such change is implicitly
approved here. Until that separate decision, keep runtime execution unavailable.

Do not schedule another performance investigation, lifecycle run, preparation
payload, finalization-owner implementation, T, writer admission or lifetime change
from this result. The 120-second ceiling and every existing gate remain unchanged.

Only this document is added. Validate `git diff --check` and document whitespace/
local links. No pytest, Z18, T, broad suite, code/schema/migration, authority,
attempt, target-entry state, writer/execution capability, hosted/production access,
commit or push.

PRODUCTION AUTHORIZATION: BLOCKED

PRODUCTION EXECUTION: BLOCKED

PRODUCTION ACTIVATION: BLOCKED

WRITER CAPABILITY: BLOCKED
