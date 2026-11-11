# 4e-20-G1: G1 implementation-authorization gate

## 1. Z37 policy decision and gate result

[Z37](recognition-runtime-source-authority-grant-right-policy-4e-20-Z37.md)
is approved with assessment B: G1 is a **new prospective entitlement**, not a
right found in existing authority formats. It permits one original-holder-only
action grant, bound at source issuance, with no transfer, re-delegation, renewal
or retry. Existing authorities receive no new rights.

**Gate decision B: BLOCKED.** The policy entitlement itself is defined. The exact
remaining eligibility ambiguity is the **authoritative original-issuance policy/
action binding that proves an authority was originated under G1 rather than
retroactively labeled eligible**. Z37 requires that binding but does not define
its authoritative representation, adoption provenance, consent linkage or atomic
relationship to source issuance. No current reader can establish it. Other
execution integration dependencies are inventoried separately below.

This gate adds no implementation authorization. It is not a finding that an
unimplemented feature is automatically unsafe: an unimplemented but complete
contract differs from a missing security rule. G1's normative entitlement can be
reviewed; its eligibility evidence and live dependency boundaries are not yet
complete enough to authorize implementation without making security decisions.

## 2. Exact entitlement predicate

Let S be the source authority; D its canonical authority ID/body digest; O the
genuine original live holder; A the exact action; and T the actual original-owner
target transaction. G1 eligibility is the conjunction below, never a standalone
boolean supplied by a caller:

```text
Eligible(S, O, A, T) =
    G1 explicitly adopted for source issuer before original decision/consent
AND original informed owner consent covers the exact family effect and witness
AND immutable original issuance provenance binds D to exact G1 version/action
AND confirmed exact source authority/genesis/consumption/audit and original lineage
AND O is the genuine original active holder, not imported or recovered DATA
AND A exactly matches D/operation/manifest/population/target/profile/incarnation
AND all independent current authentication/security/reservation/deadline gates hold
AND original one-exercise path and global logical-operation/manifest fences permit it
AND no conflicting old/new authority/claim/attempt/entry/effect/outcome exists
AND prospective action grant is single-transaction, non-transferable, non-renewable
AND no prior construction/use or uncertain failure can be retried or adopted
```

G1's explicit adopted source policy is the source of the entitlement. Identity,
ownership, authentication/consent, reservation and source ID possession merely
restrict its exercise. They cannot substitute for the first three policy/issuance
terms. Failure to prove any term must deny, not fall back to old authority behavior.

For the current checkout, G1 eligibility is **not established for any source**.
This document does not create an adoption record, policy switch, grant or capability.

## 3. Grant boundary

| Permitted by proposed G1 | Exact restriction |
| --- | --- |
| One original holder | Original private source/outer/context/issuance lineage plus actual PID/exact thread/current lifetime; no recreated owner |
| One execution decision | Exact D and canonical source subject; no source-ID-only admission |
| One family-effect-plus-witness action | Existing supported atomic First Look or Geography finalize population and exactly one internally derived Z31 D/pending/effect-bound witness |
| One issue-time-bound grant | Source must have original G1 provenance; grant expires no later than original at-most-120-second authority and all shorter credential/consent/owner/transaction bounds |
| One actual transaction | Exact enrolled target, connection/transaction/reservation epoch and original runtime/profile/activation scope |

G1 permits **no** transfer to another holder/process/thread/connection/transaction/
operator/ceremony/decision, no re-delegation or grant-of-grant, no renewal,
construction/use retry after failure/uncertainty, general writer capability,
arbitrary SQL/target selection, broader execution authority, recovery privilege,
journal repair or automatic retirement of duplicate fences. The witness is bound
as an exact derivation rule, not an arbitrary prechosen evidence hash.

## 4. Existing-authority impact and eligibility ambiguity

**No existing authority gains new rights.** Existing original authority rows,
typed consent/audit bodies, AUTHORIZED genesis, attempts, target metadata, legacy
claims/seals and readers retain their current exact semantics. Same authority
format, current ownership, a valid signature/hash, current activation or new TOTP
cannot grandfather an old source into G1.

Z37 specifically requires original prospective policy provenance. Current source
authority bodies and typed issuance/consent audits have exact field sets; none
currently establishes this new grant-right applicability. A later generic audit
append or code/config flag would be retroactive labeling, not original provenance.

The blocking security contract must specify **what authoritative fact binds
policy/action to original source consent and issuance, who may establish that
fact, when it becomes immutable, and how all old/missing/conflicting facts reject**.
This is more than selecting a serialization spelling. It must preserve one-use
consent, source digests, original transaction/audit ordering and all old-reader
fences without broadening an old authority. This gate does not select a new field,
audit event, format, issuer privilege or migration to fill that gap.

Implementation does not necessarily have to broaden existing authorities: a
prospective-only binding could conceptually avoid that. But no such exact
representation/trust rule is approved here, so absence cannot be treated as true.
Any implementation that necessarily reinterprets existing sources is expressly
BLOCKED by this gate.

## 5. Enforcement-point inventory

| Point | Required later enforcement, design only | Status |
| --- | --- | --- |
| Source adoption/issuance | Prove prospective G1 policy/action provenance and informed exact consent atomically tied to newly originated authority; reject all old/missing/conflicting provenance | Security eligibility contract unresolved |
| Grant issuance | Full Eligible predicate through genuine original registration/current readers; exact fixed action and no grant-of-grant; one construction attempt before exposing permission | Policy restrictions defined; concrete source/owner enforcement not defined |
| Grant consumption | Same original process/thread/context/connection/transaction/epoch; consume once before fixed action; never reset after no DML, rollback or unknown commit | Required behavior defined; no implemented/approved concrete G1 owner protocol |
| Target mutation | Fresh source/auth/MFA/activation/profile/approval/ACK/stop/dependency/identity/history/claim/control/schema/readiness/time and actual reservations; exact complete family write set | Existing family semantics; replacement mutation permit/owner integration unresolved |
| Witness creation | Derive exact D/pending witness from complete actual verified effects inside same target transaction; independent committed proof afterward | Inert codec exists; actual effect/atomic attestation integration unresolved |
| Duplicate fencing | Permanent D/logical-operation/manifest exclusions, unique pending start and target witness; old-runtime/legacy conflicts preserved | Journal definitions and policy exist; live cross-owner enforcement unimplemented |
| Crash recovery | Destroy local permissions, inspect durable identities/proofs under current factual-inspection rights, no restored execution owner | Fail-closed policy defined; outcome-only recorder/permission/source evidence integration unresolved |
| Uncertainty | No usable result or blind retry; retain exclusions; positive proof only for factual resolution; indeterminate may remain blocked indefinitely | Semantics defined; no live G1 outcome producer/resolver authorized |

All mutable checks remain fresh at required exercise/use/precommit/result boundaries.
No inventory reuse crosses contexts, no deadline is extended, and no process-local
flag alone replaces durable single-winner fencing. A concrete enforcement inventory
is not permission to implement its currently undefined bindings.

## 6. Dependency inventory

| Dependency | Existing contract/implementation | Gate finding |
| --- | --- | --- |
| Execution-decision identity | Z29: authority ID plus exact body digest; current canonical authority/source readers | Identity definition available, not a live grant or G1 eligibility proof |
| Decision-bound outcome journal | Z30 semantics and Z31 inert control decision/history and target-witness schema/codecs | Inert DATA ready; no installer/migration/producer; no atomic source-audit enforcement supplied |
| Target witness | Z31 exact shape/D/pending/time and effect-evidence digest binding | Detached validation only; does not prove durable effects or authorize insertion |
| Original-runtime binding | Current private original coordinator/continuation/PID/thread/connection/epoch rules and strict profile/physical checks | Existing origin mechanisms available; cannot promote query-only/metadata/legacy owners to G1 writers |
| Duplicate fencing | Existing authority/attempt/metadata/family constraints plus Z30/Z31 permanent logical identity/start/witness rules | Required invariants defined; not installed/enforced for new G1 path, and no producer may be presumed |
| Uncertain commit | Z30-Z34 no-adoption/no-retry/positive-proof/UNKNOWN policy | Conservative semantics available; concrete authorized target/control resolution integration remains incomplete |
| Target mutation/commit attestation | Z33/Z34 exact historical effects/read-only integrity foundations and same-transaction witness requirement | Complete decision-scoped runtime mutation/effect proof/permit boundary remains unresolved; current writer contracts do not accept it |
| Source-audit integration | Existing exact typed source audits; Z31 event digests and Z32 required correlated control audit | Exact new policy applicability and journal/audit action/subject/source mutation proof not defined |
| G1 grant-right policy | Approved Z37 prospective original-holder-only normative rule | Entitlement defined, not implemented; issue-time applicability trust/binding contract still absent |

Relevant sources:
[Z29](recognition-runtime-execution-decision-identity-contract-4e-20-Z29.md),
[Z30](recognition-runtime-decision-bound-outcome-journal-contract-4e-20-Z30.md),
[Z31](recognition-runtime-decision-outcome-journal-schema-slice-4e-20-Z31.md),
[Z32](recognition-runtime-decision-bound-outcome-journal-producer-contract-4e-20-Z32.md),
[Z34](recognition-runtime-target-mutation-commit-attestation-contract-4e-20-Z34.md).
No missing source/effect contract is invented by this gate, and successful inert
tests are not evidence of producer or production readiness.

## 7. Implementation-ready versus unresolved versus prohibited

| Category | Boundary |
| --- | --- |
| Implementation-ready as already scoped | Existing approved inert journal DATA/DDL/codecs and existing origin/identity/read-only integrity mechanisms retain their exact scopes. No new executable G1 code is authorized. |
| Requires a new complete security/integration contract | Original G1 policy/action applicability bound to newly originated consent/source issuance with explicit authoritative provenance and old-source rejection; exact source-audit/owner mutation proof and target-effect/witness attestation integration |
| Explicitly prohibited until separate authorization | G1 issuer/consumer, grant object or mutation permit, writer/target action, new executor/authority path, journal installer/migration/producer/resolver, new schema/authority fields/audit formats, activated reauthentication changes, old-source upgrades, target DML/DDL, lifecycle tests or deployment |

The grant source must not be made implementation-ready by inventing a generic
provider, test callback, policy flag, grant-right token, lookup or authority wrapper.
There is no harmless “G1 enabled” branch that can skip prospective eligibility.

## 8. Decision B

**G1 implementation gate BLOCKED.** Z37's entitlement policy is precise as an
abstract rule, but the authoritative original-issuance eligibility binding is not
contractually specified. A later implementer would have to decide what makes a
new source G1-eligible, how that fact joins exact original consent and issuance,
and why older matching-format sources cannot acquire the right. Those are security
decisions, not routine implementation choices this gate may infer.

The unresolved mutation/target-witness/source-audit dependencies independently
prevent authorizing a complete executable path. Their unimplemented code is not
the sole problem; their complete new-owner/evidence/provenance contracts remain
incomplete. No claim is made that the 120-second lifecycle becomes feasible.

## 9. Stop and validation

Because decision A was not reached, there is **no next implementation boundary
authorized by this gate**. Stop; no optimization, implementation slice, grant,
executor or performance investigation is proposed. The policy remains a prospective
approved design rule with no live rights granted.

Only this document is created. Validation: `git diff --check`, document whitespace
and local links. No Python/schema/migration changes, pytest, Z18, T, broad suite,
grant/permit/writer/execution authority, existing-authority behavior change,
target DML/DDL, production/hosted access, commit or push. No 120-second lifetime
change or production authorization.

## 10. Production blocks

PRODUCTION AUTHORIZATION: BLOCKED

PRODUCTION EXECUTION: BLOCKED

PRODUCTION ACTIVATION: BLOCKED

WRITER CAPABILITY: BLOCKED
