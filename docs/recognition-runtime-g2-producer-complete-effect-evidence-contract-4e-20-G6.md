# 4e-20-G6: prospective G2 producer and complete-effect evidence

## 1. G5 blockers and assessment

[G5](recognition-runtime-original-holder-atomic-enforcer-implementation-design-4e-20-G5.md)
identified prospective eligibility producer/audit permission and complete-effect
evidence/write proof as unresolved. G4 approves a bounded capability model for
design; it does not grant policy-adoption permission to an existing owner.

**Assessment B: the single most fundamental missing primitive is independently
authorized prospective G1 policy adoption, binding the permitted source issuer
and G1-specific consent producer to that policy.** No existing installation,
runtime source, consent or execution authority inspected supplies that grant-right.
This document specifies conditional producer and evidence obligations, but cannot
make that prerequisite true. Stop the architectural chain; no implementation or
performance slice is proposed.

## 2. Exactly one future eligibility producer

The sole normal producer would be the **prospective original runtime source
issuer**, inside the same original protected source-issuance ceremony. It is not
a new public eligibility factory, policy administrator or outcome resolver.

| Property | Required meaning |
| --- | --- |
| Owner | Genuine original private source issuance owner; actual PID, live Thread/context, runtime incarnation and original reservation lineage |
| Authority | Independently adopted exact P granting this issuer only the prospective G2 source-production role; **UNRESOLVED** adoption authority below |
| Authentication | Original current owner primary/session/runtime-auth, access/MFA/epochs and exact protected G1-specific consent Q; no replacement credential or generic confirmation flag |
| Context | Exact current operation/manifest/population, target/install/generation/profile/owner, activation, approval/ACK, dependencies/stop/readiness and physical identity |
| Transaction | Manager-owned control BEGIN IMMEDIATE before target reservation; target held through control commit; no target writes |
| Inputs | Authoritative adopted P/audit, original fresh consent artifacts, durable operation graph and actual scope observations; never caller assertions of eligibility |
| Output | Confirmed immutable source/genesis/audit-prefix relationship; private original continuation only after confirmed commit/cleanup, not a transferable eligibility token |
| Failure | Roll back known uncommitted control changes; no usable publication on failure/uncertainty, no retry/adoption or synthesized eligibility |

`runtime_activation_authority_issuance._persist()` currently permits its exact
five-write protocol. The consent owner permits existing protected source-consent
writes, not new policy adoption. `administration.py` explicitly does not authorize
recognition. Verified project-owner status, local console access, MFA, consent,
activation and possession of a source authority are not an independent power to
adopt a new source grant-right policy.

The proposed issuer must only consume an already-authorized policy/adoption fact.
It must be unable to create/alter adoption, authorize itself, select a broader
policy, or turn an existing source into an eligible one. Who may independently
adopt P, under which permission/ceremony and with which exact protected write
proof remains **UNRESOLVED**. Naming a trusted owner is not that permission.

## 3. Conditional typed audit/write protocol

Retain G2's P/C/Q/E definitions without adding source-authority or witness fields.
P is the exact versioned policy descriptor; C binds its digest to the exact
original source-consent subject; Q binds explicit G1 consent to P/adoption/C and
the protected original actor/artifacts/time; E binds actual authority ID/body digest
to P/adoption/C/Q. Source body supplies actual issue/expiry, runtime/target/action
scope and D. Full referenced objects must resolve, not merely have valid hashes.

| Durable fact | Meaning | Immutability / permission limit |
| --- | --- | --- |
| P and adoption audit | Policy/version, installation, adopting actor, effective time and permitted producer role | No update/delete; adoption cannot predate actual adoption audit; **authorized producer for this fact is missing** |
| Q consent evidence | Original authenticated explicit decision for exactly P/C and original source subject | Immutable; no reinterpretation of old source consent; existing consent owner has no inferred permission to emit a new artifact kind |
| E original eligibility audit | Exact source D/P/adoption/C/Q relationship in original prefix | Immutable and original-transaction-only; a generic audit append cannot create authority |
| Existing source/genesis | Exact unchanged authority state and original AUTHORIZED evidence | All old closed field sets and meanings unchanged |
| Later decision/pending/outcome audit | Correlation to D and original E plus exact journal event/witness | Factual lineage, not original eligibility or execution permission |

All fields, canonical object bytes/digests, audit sequence/predecessors, source
issue time and relationship references are immutable. Revocation is a new
authorized immutable fact, never an edit or broader replacement policy lookup.

The exact typed action identifiers/subject codecs, adoption and Q authorizers,
and allowed protected writes cannot be declared authorized through existing
`administration._audit()` merely because it accepts a subject. They remain
conditional on the missing policy-adoption/producer authorization primitive.
No schema implementation or new generic audit permission is specified here.

## 4. Issue-time atomicity and publication

G2's original source issuance audit sequence N must have E at N-2, unchanged
confirmation-consumption audit at N-1 and unchanged issuance audit at N. In one
control transaction: consume exact source confirmation with CAS; construct actual
source body/time; append E; append consumption audit; insert authority and exact
genesis referencing N; append issuance audit. This is the prospective six-mutation
protocol, not the current five-write issuer.

Eligibility evaluation, exact C/Q/source binding, source creation and original
audit prefix must commit together with complete expected-write, graph and final
live checks. Adoption and Q may precede this transaction but must be independently
authorized, committed, fresh/applicable and exactly resolved at source issuance.
Hold target reservation through control commit. No target DML is involved.

Publication is not database-atomic: only confirmed commit and required cleanup
can promote the original private continuation. A committed source with lost
publication remains historical DATA, not an adoptable permission. Unknown commit
publishes nothing usable and requires inspection, not automatic source reissuance.

## 5. No retroactive broadening

Old source at sequence N cannot acquire an E later at its immutable N-2 slot.
Exact P/C/Q/source/time/order comparisons prevent borrowing unrelated audit facts.
Sources issued after adoption are not eligible without the complete original
prefix. Unknown versions, missing/conflicting Q/E or uncertain source issuance
deny live use. Policy revisions apply only to newly authorized sources and never
resolve old sources against a broader latest policy. Revocation removes current
usability without rewriting historical eligibility or restoring consumed rights.
Recovery cannot insert original consent, original registry membership or an old
audit prefix. All existing authorities retain exactly their existing rights.

## 6. Complete existing family effects

Scope is the existing historical `private-recognition-operation-v1` families only.
Let M be the exact frozen private manifest and W = digest(M); runtime operation
UUID and W are distinct. Regenerate the full manifest inside the reserved target
transaction before mutation, not just candidate winners.

| Effect | Authoritative source | Required observation | Freshness | Verification owner |
| --- | --- | --- | --- | --- |
| Private rule and operation | M/rule definition; private rules/operations | Exact rule definition/digest; operation manifest/reference/rule key and valid stored time | Precondition and actual resulting state in T | Trusted enforcer via `permanent._prepare`, `_operation`, integrity readers |
| First Look claims | Whole report including qualifiers/competitors and immutable completion ledger | Exact stop/reviewer/assignment/earned time/evidence; no prior claim; exact complete candidate set | Regenerate before writes and verify all actual rows after writes | Same owner via `_prepare`, `_check_facts`, `check_claim_integrity`, `_verify_operation_records` |
| Geography identity/snapshot/members | Certified reviewed scopes, current active membership, scope identities and report | Independent certification/quality, unchanged cutoff/identity and complete member set; no prior catch-up | Whole report inside T and actual resulting rows | Same owner via existing Geography/report/integrity kernels |
| Geography awards/assignment witnesses | M candidates, captured completion facts and exact snapshot/member graph | Exact tiers/reviewer/time/numerator/denominator/percentage/size, award set and witness assignment identities | Inside T and independently committed afterward | `check_geography_integrity`, `_check_facts`, `_verify_operation_records` |
| Referential integrity/accounting | Exact operation and all related records | No missing/extra supported family rows, FKs valid, full population accounted without quarantine | Post-write before commit and durable inspection | Trusted verifier, not a returned issued count |

The family set is established by `permanent.finalize()` and its readers. No new
family member, live-family behavior, correction, Explorer/review/source write or
partial-population policy is added. Existing matching shared rule may be reused
without rewriting; old private operation/effects cannot be adopted for a new D.

## 7. Canonical complete-effect evidence definition

Define the proposed evidence payload as **exactly the eight-table record map
returned by `production_receipts._records(connection, M)`**, after all complete
family integrity/accounting checks in section 6 succeed. This fixes selection,
full row columns and canonical sorting to that existing authoritative collector:

- Private operations, First Look claims, Geography snapshots and awards by W.
- Private rule by M's rule key.
- Geography members by those snapshots, assignment witnesses by those awards,
  and scope identities by those snapshots' scope keys.

All eight keys remain present, including empty family lists. Each list is sorted
by existing `canonical(row)`; full actual rows, including canonical stored evidence
and operation time, are included. `effect_evidence_sha256 = digest(record_map)`
using existing `canonical()`/`digest()` rules, with no volatile clock/PID/token or
extra invented evidence field. A malformed value/row/schema or unverified family
graph rejects before hashing. This is a proposed contract use of a read-only
collector, not a call to legacy `production_receipts.build()` or its authorization.

Source/effect identity is the actual intended target and W embedded in the verified
rows. D, source authority, runtime/target scope and observation time are bound by
the unchanged surrounding Z31 decision/pending/witness, rather than duplicated
inside the record map. Witness record time is inside original deadlines; it is
not an exact commit timestamp. Private process/Thread/transaction membership remains
live ownership proof, not a serialized assertion in evidence.

Committed rows and witness are immutable under their exact schema guards; later
inspection rejects changed definitions or records. The hash proves equality of
verified state, not historic authorship, permitted writes, commit or authorization.
The same rule may be shared; its presence alone is not proof this action inserted
it. The source/action and privileged fixed-write producer supply that relationship.

## 8. Permitted-write proof versus entitlement

Observed record map + original ownership + eligible G2 source are necessary but
not sufficient. Mutation requires a genuine one-use G4 enforcer admitted under
the independently authorized original G1 grant, current auth/activation/approval/
ACK/profile/epochs/dependencies/stop/history/claims/control/readiness/physical
scope, actual reservation and original deadlines. Evidence does not grant this.

The conditional exact-write proof must enforce: deny DDL and all target UPDATE,
DELETE/REPLACE or unrelated INSERT; permit only existing family rule/operation and
selected family records plus one internally derived unchanged Z31 witness. Reject
unexpected trigger-originated changes. Derive expected inserted rows from the
fresh exact M, permitting zero or one matching shared-rule insertion according
to its initial state; require all other relevant effects absent initially. Compare
actual resulting full sets and expected unchanged protected state inside T and
verify exact change accounting. Do not use total-change count alone as permission.

This specifies an obligation on the future privileged producer, not an existing
SQLite authorizer. Exact installed schema/trigger inventory must make all implicit
writes classifiable; an unsupported trigger or unprovable delta blocks execution.
Postcommit state verification cannot reconstruct this execution trace by itself.
The enforcement/attestation proof relies on trusted code and protected database
access, not protection against arbitrary hostile code inside the trusted process.

## 9. Independent durable verification

After confirmed target commit, invalidate prior views/epochs and inspect an actual
committed target snapshot using manager-owned ordered control-before-target
reservations. Establish actual physical/schema/fingerprint and installation/restore
lineage; resolve exact source/P/C/Q/E and decision/pending/witness graph. Reload M
from the durable event/preparation/operation relationship, validate its canonical
digest and complete scope, then run full actual-operation/family integrity checks.
Recollect the eight-table map from durable rows and recompute its digest; require
exact witness equality and effect digest match. No local cached map, uncommitted
connection state or detached caller witness is authoritative.

This uses existing target read capabilities and semantic readers; there is no
identified need for another storage-level read primitive. It requires a separately
authorized verifier integration and correct installed packages, not a legacy
receipt/claim fabricated to satisfy its API. Independent verification proves
current committed effects matching the original trusted producer's attestation;
it cannot alone prove mutation permission or that an arbitrary writer never
committed unrelated changes. That responsibility remains the enforcer/write proof.

If verification cannot establish positive evidence, publish no usable success;
preserve permanent decision/operation/manifest exclusion. Do not repair a witness,
repeat mutation or infer rollback from missing state on an unclear lineage.

## 10. Effect/witness and audit coupling

Fresh intended-effect verification precedes permitted business writes; actual
record verification follows them inside T. Compute record-map digest only from
verified actual rows; bind it to exact D and sole confirmed pending in the unchanged
witness, INSERT that witness in T, perform final live/write proof and commit T
once. Known failure rolls back family effects and witness together.

Only then may independent committed verification support factual control COMPLETED
and its audit under exact expected head/current recording permission. No control/
target co-commit is claimed. Postcommit verification is not a substitute for
mandatory atomic witness production or permission at the time of mutation.
Source audit establishes original entitlement; target witness attests actual
outcome; control journal records that fact. None is an independent writer credential.

## 11. Crash / uncertainty protocol

| Failure | Required handling |
| --- | --- |
| Eligibility producer crash before commit | Known rollback removes source/prefix group; no published eligibility or reconstructed original owner |
| Eligibility commit uncertain / publication lost | Resolve exact atomic source graph as historical DATA only; no usable grant, retry or adoption |
| Evidence generation fails inside T | Roll back whole known uncommitted T, spend original action and retain confirmed exclusion |
| Target mutation or witness commit uncertain | Poison original use, publish nothing usable; exact durable inspection only, no witness repair or blind retry |
| Postcommit verifier fails | Keep target-possibly-committed and control pending/uncertain; no completion from elapsed time or local object |
| Source/audit write fails before its commit | Roll back its exact local atomic group; missing required audit denies eligibility/outcome |
| Control outcome audit/commit fails after target commit | Preserve committed target facts and exclusion; no cross-database rollback claim; independently authorized factual recording only |

Known positive no-commit evidence may support TARGET_FAILED; absent witness,
process death, timeout or inaccessible database does not. Unknown outcomes may
remain unresolved indefinitely. Recovery never obtains a mutation right, and
expired original credentials cannot authorize late factual writes automatically.

## 12. Security separation

| Separation | Reason |
| --- | --- |
| G2 eligibility is not mutation authority | Only original prospective source grant-right; target requires current independently admitted one-use enforcer |
| Complete-effect evidence is not mutation authority | Canonical verified state has no live owner, permission or SQL capability |
| Audit is not execution authority | Referenced typed provenance is necessary; generic append/hash alone grants nothing |
| Witness is not authorization | It records exact claimed/verified outcome only when committed with effects |
| Verification is not reauthorization | Reloading durable records cannot recreate original private registration or spend a second start |
| Recovery is not reauthorization | Outcome-only facts never release exclusion, renew expiry, adopt owner or permit target writes |

## 13. Implementation boundary

**Contract-established design obligations:** one conditional original source
producer; immutable original G2 prefix and atomic publication rules; complete
existing family inventory; exact proposed record-map digest and independent durable
recomputation; fixed-write/fresh-check obligations and failure discipline.
None is permission to code or deploy from this slice.

**Requires an authoritative security primitive:** independent prospective policy
adoption with authority to appoint/restrict the G2 source/consent producer. Exact
adoption authentication/consent and typed authorized audit/write proof must follow
from that primitive; the source issuer cannot supply it to itself. This is the
fundamental blocker, not a request to add another general authority class.

**Prohibited:** inferring policy-adoption power from admin/MFA/owner/activation;
grandfathering sources; arbitrary audit or SQL callbacks; synthetic legacy claims/
EXECUTING/receipts; caller-selected evidence; partial family success; schema or
enrollment changes here; transfer, renewal, retries, recovery mutation, dropped
fresh checks or longer authority lifetime.

## 14. Decision B and stop

The proposed evidence contract can be expressed from existing complete historical
family records and readers without inventing another family or claiming a hash
grants permission. But no existing inspected authority lawfully establishes the
independent adoption/appointment fact required before prospective issuance.

**B - One specific security primitive remains missing: independently authorized
prospective G1 policy adoption and constrained producer appointment.** A solely
self-declared producer would bootstrap its entitlement and violate the request.
Therefore both G5 blockers cannot be declared fully resolved. No evidence shows
the whole model inherently impossible (C), and A is not justified.

Stop the architectural chain. No implementation or performance work is proposed.
The unresolved policy-authority boundary is identified, not implemented or granted.
The 120-second ceiling remains unchanged; no timing feasibility claim follows.

## 15. Validation and production blocks

Only this document is added. Document whitespace/local links and `git diff --check`
only; no pytest, Z18, T, broad suites, code/schema/migration, permission/grant,
target DML/DDL, hosted/production access, key reads, commit or push.

PRODUCTION AUTHORIZATION: BLOCKED

PRODUCTION EXECUTION: BLOCKED

PRODUCTION ACTIVATION: BLOCKED
