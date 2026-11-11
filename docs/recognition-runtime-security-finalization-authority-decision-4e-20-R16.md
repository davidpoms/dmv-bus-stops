# 4e-20-R16 - finalization security-authority requirement decision

## 1. R15 baseline and decision scope

[R15](recognition-runtime-security-finalization-ownership-write-set-contract-4e-20-R15.md)
could not complete the replacement contract under existing authority. Original-
holder action entitlement, authenticated governance-to-producer integration,
complete effect proof and combined control/target atomicity remain unresolved.
Existing v1/default is 120 seconds; test-only v2/300 did not complete. Neither
policy changes here, and the measured failure grants no additional permission.

**Decision A - AUTHORIZE NEW FINALIZATION SECURITY-AUTHORITY DESIGN.** This is
approval to specify and assess the narrow missing authority, not approval to
introduce it operationally. No grant, producer appointment, policy adoption,
runtime entitlement, target mutation or implementation is authorized. The
independent atomicity question remains open and cannot be solved by authority.

## 2. Missing authority: exact requirement

The missing authority is prospective permission for a protected source producer
to establish that one original holder is entitled to one exact historical
family-effect-plus-decision-witness action. It is not a general executor or
writer class. Its final enforceable contract is the subject of R17, not presumed
to exist already.

| Question | Required boundary / established evidence |
| --- | --- |
| Who grants it? | Only a prospectively adopted, explicitly appointed and authenticated protected source producer could establish original issue-time eligibility. None is appointed by this decision. The original eligible holder could exercise only that exact action; it cannot grant a new right to another holder. |
| Governance basis? | The verified project-owner G13/G14 mandate covers prospective adoption of the exact G2 policy and appointment of one constrained producer. It is not itself the executable grant-right or authenticated transaction bridge. |
| Exact action? | Complete supported historical First Look **or** Geography family effects for one approved frozen manifest, inseparably verified and committed with its exact decision-bound target witness. No partial population, discrepancy/correction path, capture, arbitrary SQL or unrelated family. |
| Target/family binding? | One exact enrolled target, installation, operation and private manifest digest, supported family/rule/population, profile/generation, activation incarnation, original owner and auth/MFA scope. No caller rebinding. |
| Decision binding? | D is the original authority ID plus exact canonical body digest under Z30, with its sole pending/start reference. No independent grant ID may permit a divergent decision or evade permanent operation/manifest exclusion. |
| Validity? | One finite, immutable issue-time interval, intersected with original source, consent and credential deadlines and live eligibility. Numerical policy and precise start/consumption/commit rules require R17 specification; this decision selects no new duration. |
| Transfer / re-delegation? | Prohibited across process, Thread, context, runtime incarnation, connection, ceremony, operator, target or decision. An identifier or stored row is not ownership proof. |
| Renewal / retry? | Prohibited. No restamping, expiry extension, replacement source or recovery-based reauthorization to repeat the action. |
| Issuance evidence? | Exact authenticated governance adoption and appointment provenance, policy/action version and digest, original fresh action-specific consent, original eligibility/source/genesis/audit relationship and confirmed manager-owned commit. G2/G16 specify obligations; their protected executable production remains unresolved. |
| Revocation? | Required live policy/appointment/source revocation, credential/auth/MFA change, activation/profile/owner/dependency/physical-state change, stop, reservation loss, spent state, closure or deadline deny use. Exact authoritative applicability and ordering must be specified, not inferred from missing revocation records. |
| Uncertain state? | No grant/use/publication, no automatic retry or adoption. Stop for independently authorized read-only durable inspection; uncertainty is never permission. |

No codec, database field, credential mechanism, new producer identity, API or
permission bit is invented by this requirements table.

## 3. Governance versus runtime authority

[G13](recognition-runtime-g1-formal-governance-mandate-4e-20-G13.md)
records the project owner's explicit independent approval under mandate
`dmv-bus-stops-g1-governance-mandate-4e-20-G13-v1`, revision 1. Its indefinite
duration is governance duration only. No additional person's approval is required
for its specified governance decisions; runtime/producer self-appointment remains
prohibited. This accepted mandate is not reopened or replaced here.

The mandate is sufficient as the documentary governance basis **only within its
exact existing G2 policy/action and appointment scope**. It is not sufficient to
instantiate this new runtime authority. It does not approve another action,
broader executor, new lifetime or altered atomicity model. Any such departure
would require an explicit scope decision, not an inferred mandate extension.

Maintain four distinct concepts:

- Governance authority: who may approve the exact prospective policy/appointment.
- Producer appointment: the independently approved constrained source role and scope.
- Runtime execution authority: actual original issue-time eligibility and live entitled holder.
- Target mutation authority: one permitted fixed transaction exercised under all fresh checks.

None implies the next merely through identity, database access or ownership.
Existing authorities receive no new rights; later adoption cannot retrofit them.

## 4. Original-holder binding and authenticated bridge

The action must remain original-holder-bound. Otherwise historical source DATA,
a copied grant or a restarted runtime could become transferable permission and
defeat the original consent, lifetime, one-use and uncertainty restrictions.
Require genuine private issuance provenance, exact live process/Thread/context
and runtime incarnation, original actor/credentials, actual owner-controlled
connections/transactions/reservations and exact decision/action scope. Possession
of matching IDs, witness or journal state supplies none of that entitlement.

An internal finalizer can act only as the same original holder's fixed-action
transaction owner. An independent executor, operator or replacement process is
not implicitly permitted to act on that holder's behalf.

[G17](recognition-runtime-g1-protected-governance-owner-binding-contract-4e-20-G17.md)
identifies the exact missing bridge: independently authenticate that the verified
project owner approved this exact typed adoption or appointment, bind its complete
immutable subject and expected predecessor/audit head to a manager-owned control
transaction, durably fence approval consumption, prove only permitted writes,
and confirm commit/cleanup before publication. Adoption approval and appointment
approval are separate decisions. Existing runtime authentication and operation
consent authenticate different scopes and cannot be silently repurposed.

The bridge must then support the prospectively entitled source producer and
original issue-time action binding required by G2; it must not itself become a
target writer. R17 must resolve that contract without assuming a signing key,
login route, trusted callback or raw SQL handle is sufficient. No such mechanism
is chosen or implemented here.

## 5. Atomicity is a separate unresolved primitive

Authority is necessary but not sufficient. The authorized action must cover
**all** required family effects and its decision-bound witness, with duplicate
fences and audit/outcome requirements explicitly accounted for. No write may be
dropped to fit a deadline.

[Z30](recognition-runtime-decision-bound-outcome-journal-contract-4e-20-Z30.md)
uses one logical decision journal with separate control and target placements:
control decision/start and audit, one target transaction containing full effects
plus target witness, then factual control outcome. Existing attempt/history and
source records are earlier separate control transactions. Reservation state is
live ownership state, not another atomically committed row.

That protocol does **not** make target effect, target witness, attempt/history,
control outcome/audit and all duplicate fences one atomic multi-database commit.
A new authority cannot create that property. Existing target-local atomicity is
compatible with a split factual control outcome only if that split is explicitly
accepted as satisfying the requirement. Otherwise a separately authorized storage/
transaction-model decision is necessary. R16 neither accepts the split on the
project's behalf nor authorizes a storage redesign or ATTACH workaround.

R17 must identify this issue as unresolved unless separately decided; it cannot
claim implementation readiness while claiming nonexistent combined atomicity.
Committed target evidence with missing/uncertain control outcome stays blocked
for mutation. Missing outcome is not evidence of rollback or permission to retry.

## 6. Lifetime and invalidation model

The new permission requires its own explicit finite validity semantics: actual
start event, immutable expiry, one-use consumption point, revocation checks,
commit-time checks and closure. These must be specified independently rather
than borrowing a consent or harness timeout as its lifetime.

Minimum constraint: usable time is no later than every original applicable
authority, credential and consent deadline. It cannot outlive, renew or restart
the source. The existing exact G2/G13 descriptor remains tied to v1/120; support
for v2 historical representation does not broaden that mandate or policy.
No new numeric interval is selected. Any need to exceed the original window or
to use a different policy is a future explicit security decision, not approved
here. Feasibility within either 120 or 300 seconds remains unproved.

Expiry/revocation prevents future use; it does not undo a confirmed commit,
release exclusions or authorize compensation. Exact effective revocation state
must be authoritative at the required checks. Uncertain applicability denies use.

## 7. Security tradeoff: options A-C

| Risk / choice | A - design the constrained authority | B - reject and accept limitation | C - require another architecture |
| --- | --- | --- | --- |
| Attack surface / privilege concentration | Adds a privileged source/bridge/finalizer trust surface; exact action and mutation proof must constrain it | Adds no privilege, but desired completion remains unavailable | Could relocate or concentrate privilege; no evidence yet establishes a safer supported replacement |
| Delegation / confused deputy | Original-holder-only; authenticated full subjects and exact target/action prevent caller-selected substitution; no independent executor entitlement | No new delegation | Must define its own entitlement rather than inherit permissions |
| Audit / revocation | Attributable prospective adoption, appointment, consent, eligibility, source and outcomes; authoritative current revocation required | Existing audit and expiry remain | New model must preserve historical meaning and explicit revocation |
| Replay / duplicate execution | Private lifetime binding plus durable decision/operation/manifest fences; no renewal or retry, even after known failure | Existing failure remains closed | New identity cannot evade old exclusions |
| Crash / uncertainty | Separate commit facts, no usable uncertain result or adoption; authority cannot fix atomicity | Known safe blocked operational state | Must explicitly resolve changed durable prefixes and outcome meaning |
| Operational claim | Design may be useful; no performance or implementation claim | Safe but terminally accepts the limitation rejected as desired end state in R14 | Replacement necessity has not been demonstrated |

Select A for **further design only**. R14's continuing recognition objective
supports investigating the minimum missing entitlement rather than abandoning
completion. This does not establish that privilege expansion is acceptable for
deployment, that it solves timing, or that G1 must be implemented. B is a safe
holding state but is not chosen as the terminal objective. C is premature without
resolving whether the constrained design and atomicity requirement can coexist.

## 8. Minimum authority and decision

**A - AUTHORIZE NEW FINALIZATION SECURITY-AUTHORITY DESIGN**, constrained to one
exact action, one exact D, one exact target/family, one original holder, one
bounded immutable period and one use. No transfer, re-delegation, renewal, retry
authorization, general writer, arbitrary SQL, producer self-appointment or
recovery-based permission. No existing authority is broadened retroactively.

The exact next boundary is **4e-20-R17 - finalization security-authority contract
design**. R17 is design-only: specify enforceable entitlement, authenticated
bridge, prospective issue-time binding, validity/revocation, permitted mutation
scope, complete audit proof and uncertainty behavior. Explicitly retain the
independent atomicity blocker and complete-effect proof obligations from R15.
It must stop rather than invent entitlement, lifespan or transaction guarantees.
No R17 work, implementation, lifecycle run or permission grant occurs in R16.

## 9. Validation and production blocks

Only this document is added. Read-only review of R15, G13/G17 and existing
referenced security contracts. Document whitespace/local-link checks and
`git diff --check` passed. No pytest, lifecycle, Z18, T, broad suite, code,
schema, migration, policy, permissions, target behavior, producer appointment,
authority issuance or production/hosted access. No commit or push.

PRODUCTION AUTHORIZATION: BLOCKED

PRODUCTION EXECUTION: BLOCKED

PRODUCTION ACTIVATION: BLOCKED
