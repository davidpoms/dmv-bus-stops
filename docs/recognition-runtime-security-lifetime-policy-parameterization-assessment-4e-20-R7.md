# 4e-20-R7: authority-lifetime policy parameterization assessment

## 1. R6 baseline and recommendation

[R6](recognition-runtime-security-lifetime-test-only-feasibility-4e-20-R6.md)
could not construct a genuine 600-second diagnostic authority without altering
the existing persisted schema/codec contract. No attempt ran; no lifetime or
production code changed. Complete-workload lifetime selection remains unsupported.

**Recommendation B - lifetime should be an explicit bounded security-policy
parameter, with immutable per-authority policy/version meaning.** This is a
design recommendation, not authorization to introduce a mutable global timeout.
The smallest defensible initial model retains **default 120 seconds and maximum
120 seconds** until a separately approved policy establishes a different ceiling.
No larger numeric production maximum is justified by current measurements.

There is a crucial distinction: 120 is a structural/data-integrity invariant of
the existing v1 authority contract; the evidence does not establish it as an
unchangeable security property for every future policy version. Parameterization
must preserve the former while making future policy decisions explicit.

## 2. Enforcement inventory and relative authority

Inspected recognition source, relevant tests, `.env.example`, local administration
CLI, and architectural records. Secret configuration and databases were not read.

| Enforcement / occurrence | Classification | Actual authority |
| --- | --- | --- |
| `runtime_activation_authority_schema.LIFETIME`, exact `validate_authority()` format/policy check | Security-policy identity and canonical data integrity | Accepts only `recognition-runtime-authority-lifetime-120s-v1`; no unknown/new policy accepted implicitly |
| `validate_authority()` issue-time range and `issued < expires <= issued+120` | Canonical invariant of v1 / overflow safety | Rejects malformed or extended detached source DATA |
| `definitions()` `issued_at` maximum and SQL `CHECK(issued_at<expires_at AND expires_at<=issued_at+120)` | Persisted data-integrity constraint | Prevents insertion of a longer authority, even if Python issuance is patched |
| `definitions()` body/index binding trigger with exact `lifetime_policy` | Persisted canonical-to-index consistency | SQL body policy must match known v1; no free-form policy is meaningful |
| `runtime_activation_authority_issuance._body()` | Current issuance policy/implementation | Derives `min(issued+120, step, confirmation, primary, session expiry)`; caller cannot choose expiry |
| Schema `_historical_scope()` reached from `check_rows()` | Historical security/data-integrity reconstruction | Requires exact original min formula and resolves original consent/authentication; does not accept arbitrary <= ceiling as equivalent issuance |
| Schema `check_manifest_transition()`, `historical_claim_manifest()`, `migrate()`; administration exact-schema validation | Schema/manifest compatibility and installation contract | Definitions and historical projection are checked exactly; replacing an expected SQL string is not a migration |
| `runtime_execution_coordinator` `_Outer.check()`, `_evaluate()`, `_time()`, `_persist_attempt()` | Live ownership/time invariant | Enforces current accumulated original deadlines; attempt expiry equals source expiry, never restarts |
| `runtime_execution_attempt_schema` authority validation and scope/expiry equality | Referential/canonical integrity | Imports original authority semantics, not an independent lifetime selection |
| `runtime_target_entry_storage` validators and `runtime_target_entry_owner` `_time()`, `_evaluate_kernel()`, result lifetime | Downstream scope and live deadline invariant | Exact attempt/source deadline and current original owner; cannot extend metadata lifetime independently |
| `runtime_decision_outcome_journal_schema` decision/event/witness validators | Inert proposed outcome DATA integrity | Resolves original source and bounds start/witness times. It is not installed execution permission |
| Existing authentication/consent expiry/paired clock checks | Independent live security bounds | Shorter primary/session/step/confirmation deadlines still apply; no parameter may extend them |
| Authority schema/issuance tests and coordinator tests | Tests of current contract | Synthetic 120-second bodies, exact issuance assertions, >120 rejection and historical extension rejection mirror v1, not an independent numerical threat rationale |
| Lifecycle trace assertion and timing-profile fixtures | Diagnostic/test assumptions | Expect original actual source interval 120; assertion alone cannot change SQL or authority |
| `.env.example` / local administration CLI | Configuration inventory | No authority-lifetime selection setting was identified; no environment value is authoritative for this policy |
| 4e-11 section 5 | Original explicit policy proposal | Introduces 120 as a bounded safety limit, disclaims workload-fit proof and explicitly permits review of a new policy version |
| 4e-12/15 and later Z/G contracts, Z5 retention decision | Normative current-version policy and conservative change control | Preserve 120 during those slices; they do not supply a quantitative justification for that number universally |
| R1/R5/R6 reports | Assessment/measurement evidence | Partial expiry traces and schema conflict, not authority to change policy or proof another number is sufficient |

Primary direct numeric enforcement is confined to issuer/schema. Other readers
inherit those validators and compare actual recorded deadlines. A numeric literal
search alone would miss that transitive enforcement. Unrelated 300-second 4d claims,
600-second consent/challenges and 360-second harness timeout are separate domains.

Relevant test sources include `test_recognition_runtime_activation_authority_schema.py`
(including lifetime and historical-extension cases), authority issuance, execution
coordinator/attempt schema, the dedicated lifecycle trace, and diagnostic final-
validation/readiness fixtures. Tests were read, not run or changed.

## 3. Intended security semantics

[4e-11](recognition-runtime-activation-bound-authority-contract-4e-11.md) calls the
number a new explicit proposal, independent of 4d's lifetime, and says to review
a new policy version if fixed-writer rehearsal cannot fit. That is direct evidence
that the design allows a policy decision rather than requiring every future
authority to have the same immutable universal constant.

The general invariants supported by code/contracts are: finite positive bounded
authority age; original issue/expiry immutability; strict current time before all
bounds; no renewal/restamping; manager-derived rather than caller-chosen expiry;
exact historical policy meaning; and consistent issuer/codec/SQL/reader behavior.
They do not identify a threat threshold at exactly 120 seconds. A larger bound
still increases stale-intent exposure; lack of a unique rationale is not proof
that any larger number is acceptable.

Thus **120 remains mandatory when validating or using v1**, but need not be a
universal constant across a deliberately approved future version. Current code
cannot simply reinterpret v1 or accept a caller-configured number.

## 4. Parameterization feasibility and smallest safe model

Use immutable, explicitly supported policy versions, not an unbounded numeric
environment/HTTP/CLI setting. The source issuer selects an explicitly approved
effective policy for *new* authorities; the caller cannot raise or override it.
An active default is an issuance selection, not a historical validation rule.

| Model element | Recommended minimum |
| --- | --- |
| Initial default | Existing v1, 120-second ceiling, unchanged |
| Initial maximum permitted lifetime | 120 seconds; no evidence-supported higher production ceiling yet |
| Future maximum | A finite positive explicitly reviewed ceiling in an immutable known policy version; no unlimited/unrecognized value and no automatic 600-second promotion |
| Derived expiry | Original issue plus selected policy ceiling, clipped by all original credential/consent bounds, with overflow checks and exact historical reconstruction |
| Version selection | Explicit authorized prospective policy change/audit; never requested by operation/browser or silently changed through configuration |
| Historical resolution | Resolve the authority's exact recorded original policy, not active default; retain old validators/definitions or an explicitly reviewed compatible historical representation |
| Invalid policy/state | Reject unknown, malformed, unauditable, contradictory or uncertain policy selection and applicability |

This recommendation establishes no new policy ID, schema/table/column, codec,
configuration switch, permission or migration. It identifies requirements for a
future design. Supporting a >120 version requires explicit SQL/schema/manifest/
reader compatibility work: existing persisted CHECKs prohibit it. No test-only
600 variant can be inferred from the conceptual recommendation.

## 5. Historical-data implications

The authority **already stores** `lifetime_policy`, `issued_at_utc` and
`expires_at_utc` inside canonical body/digest, with indexed times and exact binding.
The policy identifier explicitly names 120s/v1. An additional numeric lifetime
field is not automatically necessary; exact immutable policy semantics can supply
the ceiling if every historical reader retains that mapping. Actual interval is
not sufficient alone because shorter credentials can clip it.

Example: an original v1 authority issued at I retains its original policy and
recorded expiry, historically validated by `min(I+120, original bounds)`, even
if a future separately approved policy permits 300. It does not gain 180 seconds,
change body digest or become usable again. A 60-second clipped original interval
does not imply a 60-second policy or authorize recomputation against current
credentials. A new policy requires distinct meaning, not relabeling v1.

The data-model requirement is durable unambiguous *issue-time policy/version*
binding and retained historical semantics, plus attributable prospective policy
selection. Existing body fields are a foundation, not proof the present SQL can
represent multiple policies. Exact additional storage/migration needs require
future design; no schema change is invented in this assessment.

## 6. Security tradeoff and change authority

Explicit parameterization does not inherently weaken expiration, historical
integrity, audit or fail-closed behavior if the policy is finite/versioned, original
expiry immutable and all enforcement layers agree. It can improve auditability
compared with unexplained duplicate literals. Conversely, a mutable global default
used to revalidate old records would weaken integrity and could revive old rights.

Increasing an approved ceiling materially increases the maximum age of original
intent and potential live-authority exposure. Fresh authentication, revocation,
exact profile/activation/target/action scope and one-use original-owner registries
mitigate but do not erase that risk. Durable duplicate/consumption fences,
reservation concurrency and crash/no-blind-retry rules must remain unchanged;
they do not depend on the specific 120 value. A timeout is not process cancellation
or proof of commit outcome.

Who may change policy must be explicitly established for lifetime policy itself.
The project owner's separately authorized security-policy decision must identify
exact version, ceiling, default/effective ordering and audit evidence. Do not infer
an operational permission from database access or the G13 mandate: G13 binds G1
to the existing 120-second lifetime policy and does not silently authorize a
different runtime lifetime. Ordinary runtime/producer/request input cannot change
it or appoint itself to do so. An indefinite governance mandate does not imply
unbounded runtime authority.

Changing defaults is prospective only, never modifies issued bodies/expiries and
cannot release prior operation/manifest exclusions or repair an uncertain commit.
Policy change and its original applicability need auditability, not just current
configuration or a policy-looking string without resolved authorized meaning.

## 7. Recommendation B and numerical limits

**B - lifetime should become an explicit bounded security-policy parameter.**
The architectural direction is supported by the existing version field, original
4e-11 new-version option and separation of time-based freshness from independent
integrity/replay/concurrency controls. Current v1 remains structurally 120.

Recommend default **120**, maximum **120 initially**, prospective-only effective
version selection and immutable audited historical policy binding. Any proposed
larger production maximum is **not selected** here: complete workload, appropriate
intent-age exposure and compatibility evidence remain insufficient. This is a
recommendation for policy representation, not a claim parameterization has already
solved liveness or a replacement lifetime has been measured.

Option A would overstate the evidence by making 120 universally immutable. Option
C accurately describes uncertainty about a larger number, but not the broader
architectural choice: the existing contract expressly supports separately reviewing
a new version while preserving original sources' meaning.

## 8. G-series disposition and next boundary

No modest policy-controlled increase has been shown to complete the lifecycle;
R5 has no complete success samples and R6 could not run. Therefore G1 cannot be
declared unnecessary for the original recognition objective on this evidence.
Its necessity also has not been proved: a lifetime problem alone is not evidence
that a replacement authorization architecture is required.

Do not continue G1 automatically. The exact next boundary, if separately authorized,
is a **versioned bounded-lifetime policy/data-compatibility design**, including
explicit authority to approve a non-default diagnostic variant, preserved v1 SQL/
history semantics and unchanged other credential/time checks. A narrowly isolated
disposable measurement exception could then be considered explicitly rather than
silently bypassing R6's schema restriction. Neither that design, exception, migration,
measurement nor higher production limit is implemented or authorized by R7.

## 9. Validation and explicit production blocks

Read-only source/test/configuration-example/document inspection only. No lifecycle
tests, pytest, Z18, T or broad suites. Document whitespace/local-link checks and
`git diff --check`; only this document is added. No code/schema/migration,
validator/policy/database/permission changes, production/hosted resources,
deployment key reads, commit or push.

PRODUCTION AUTHORIZATION: BLOCKED

PRODUCTION EXECUTION: BLOCKED

PRODUCTION ACTIVATION: BLOCKED
