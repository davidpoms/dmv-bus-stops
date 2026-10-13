# Recognition authorization boundary

For local validation and manual disposable-only hosting preparation, see
[Recognition test-deployment readiness](recognition-test-deployment.md).

Production provisioning is unavailable. This change enables synthetic disposable
rehearsals only. No production activation, approval, target enrollment, migration,
First Look sealing, or Geography issuance is provided.

## A. Content and binding validation

`authorization.Authorization` is immutable approval data, not an authority.
`verify()` validates its exact type, target identity (host, resolved path, device,
inode), environment, family, permission, action, operation, policy, population,
reference and optional expiration against writer-derived expectations. It then
checks a provisioned authority capability. No writer accepts a verifier callback.
Passing a lambda, custom accepting object, unregistered Authority instance, or
legacy `authorization_verifier` argument cannot authorize a write.

Historical finalization freezes the manifest before computing bindings, regenerates
it under BEGIN IMMEDIATE, writes and checks all records in its owned transaction,
and checks authority again before commit. Geography binds the exact reviewed scope
snapshot, report, identity history and ledger. Certification flags and hashes are
content assertions, not independent production approval.

Live sealing requires two distinct approvals:

- `delivery_authorization`: `delivery_binding(conn, assignment_id)` binds the exact
  selected pending row (including attempts/state), configuration, current immutable
  ledger and identity snapshot, and any stored claim. Its action is process_delivery.
  It authorizes processing, deferral, or evidence quarantine of that delivery only.
- `authorization`: the complete live manifest binding authorizes claim issuance.
  It cannot be replaced by delivery permission, capture permission, or finality.

The sealer acquires a writer lock using an UPDATE that matches no rows, then checks
all delivery fields before any row mutation. Completed acknowledgements require
an approval for that exact completed context and stored claim. Retry-state recording
uses the same complete delivery binding with a separate record_retryable_failure
action. Changed delivery state or population requires a freshly reviewed approval.
A delivery approval alone never permits a new claim: the current read-only finality
guard, sealed baseline, re-preparation and manifest approval remain mandatory.

There are no standalone operation/claim insertion functions. The SQL exists only
inside the complete historical finalizer and live sealer. The live savepoint covers
rule, operation, claim and delivery writes. Catching a failure and committing the
outer transaction cannot retain partial inserts. Historical finalization owns its
rollback/commit. Manifest candidates, finality decisions and discrepancy evidence
are canonicalized/copied before binding and the frozen values are serialized.

## B. Application authority provisioning

`authority.py` separates provisioning from data validation. The opaque Authority
class cannot be directly constructed; verification accepts only registered handles
of the exact class. Merely wrapping a verifier does not register an authority.

The only implemented provisioner is explicitly disposable: DisposableWorkspace
creates a new random temporary directory itself. It cannot adopt an existing root.
The internal registry pins that root's path/device/inode independently of mutable
wrapper attributes. Its allowlist may approve only files below that root, with
matching observed identity, no hardlink alias, and environment disposable. A caller
cannot enroll an existing production target, change the approval's environment or
target, or change the wrapper's name to extend this capability. Approval removal or
workspace cleanup revokes it. Synthetic fixture adapters use this path; their
allowlist is test approval, never represented as independent production approval.

The disposable rehearsal API requires this capability as well as an approval-data
provider. The provider alone conveys no authority. Existing target path/receipt
checks remain. The CLI has no provisioning integration: verification-only use is
available, while --apply-disposable alone fails closed.

Flask defaults LIVE_FIRST_LOOK_AUTHORITY and LIVE_FIRST_LOOK_AUTHORIZATION to None,
keeps capture disabled, and rejects issuance-enabled submission gates. No startup
migration, dispatcher, scheduler, automatic provisioning, or issuance flag is added.

File-backed private/live install and migrate(apply=True) require schema-bound
approval and authority. Default migration opens the source read-only and rehearses
DDL in memory. Only an unattached memory database is exempt; attached files are
rejected. Schema definitions remain additive/idempotent and Explorer is unchanged.

## C. External production trust root

`provision_production_authority()` always raises production_authority_not_provisioned.
It does not accept a callback, mint production approval, or load an artifact. Real
production capability issuance needs a separate reviewed integration with authentic
approval/revocation state and protected target/environment enrollment. No fake
verifier or local accepting fallback is supplied.

Still external: trusted production verification, approved policy and First Look
historical/live populations, independently certified Geography scopes, revocation
availability and approval lifetime, retained approval evidence, and deployment
operator permissions. Approval expiration is enforced when supplied; production
lifetime policy remains unspecified. Existing launch build_guard callback injection
is a finality-policy test seam, not a way to provision writer authority.

## D. OS, filesystem and process boundary

This is an application API boundary, not protection against arbitrary Python code
execution with unrestricted process/database/filesystem privileges. Monkeypatching,
closure introspection, replacing modules, moving a database into a disposable root,
or direct SQL are outside this guarantee. Production protection against those
actors requires an independently privileged writer/control plane and OS permissions.
A module-global callback would not supply that isolation; none is used as authority.

SQLite target identity is observed through its pathname, not an OS descriptor
attestation. Deployment must prevent concurrent path replacement, junction/symlink
changes and database substitution. Local disposable root checks do not establish
that protection on PythonAnywhere. Production deployment state is unknown here.
Revocation is checked at writer verification points, including before historical
commit and before live savepoint completion; there is no atomic external revocation
contract spanning a caller's later outer commit. That remains a provisioning and
transaction-policy requirement for production.

## Production Trust Contract (proposed; not implemented)

This section specifies future production requirements, not an authorization or
operator activation procedure. Phase 1 changes documentation only. The existing
disposable design, writer semantics and Explorer behavior remain unchanged.
No production signature profile, transaction coordinator or production provisioner
is implemented. The separate Phase 2 synthetic profile below exercises validation
without enabling this production contract.

**Synthetic approvals are not production approvals. DisposableWorkspace cannot
authorize production. Production provisioning remains intentionally unavailable.
No application-side JSON field establishes issuer identity. No database content
hash substitutes for target enrollment identity.**

### Trust root and roles

Production approvals must be independently signed and verified with a pinned,
non-secret public verification key. Signing secrets remain outside the application.
Protected trust configuration maps key IDs to authenticated issuers and permitted
families/actions; an artifact cannot select its own trust root or grant issuer roles.
Use a reviewed signature library and a fixed, independently approved algorithm;
algorithm selection and key lifecycle remain blocking implementation decisions.

The independent approver reviews evidence and authorizes scope; the issuer signs
that decision and authenticates the approver. A separate enrollment administrator
controls target/deployment enrollment. The operator executes approved operations
but cannot approve their own inputs merely by editing application configuration.
Trust pins, verifier code, enrollment and revocation state must be protected from
unauthorized application identities. A protected local file is independent only
when its owner and parent-directory permissions enforce that separation. An
external authorization service is an alternative implementation, not a requirement
or an automatic solution to commit races. Neither file possession nor a remote
boolean response replaces exact binding and current authorization verification.

### Signed envelope and canonical payload

The proposed envelope has exactly these fields:

| Field | Contract |
| --- | --- |
| `format` | Versioned production-approval format; unknown versions rejected. |
| `algorithm` | Must match the protected, approved algorithm; no negotiation fallback. |
| `key_id` | Identifier resolved only through pinned trust configuration. |
| `payload` | Strict object with exactly the fields below. |
| `signature` | Signature over the version-specific domain separator and canonical UTF-8 payload. Encoding must be fixed by the reviewed format version. |

The payload has exactly these fields; nullable fields must be present as `null`,
not omitted. All other fields are mandatory and non-null.

| Field | Contract |
| --- | --- |
| `approval_id` | Unique approval identifier used for revocation and replay tracking. |
| `issuer_id` | Must match the identity authenticated by the pinned signing key. |
| `approver_id` | Independently authenticated reviewer identity attested by the issuer. |
| `environment` | Exactly `production`; disposable artifacts cannot be promoted. |
| `enrollment_id` | Independently controlled target enrollment identifier. |
| `enrollment_generation` | Positive integer; must equal the currently enrolled generation. |
| `enrollment_sha256` | Digest of the exact authenticated enrollment record. |
| `target` | Exact object `{hostname, database, device, inode}` matching existing Target fields and enrollment. |
| `deployment_id` | Protected identity of reviewed code/configuration inventory, not a caller-selected label. |
| `family` | Exact family from the approval matrix. |
| `permission` | Exact permission from the approval matrix. |
| `action` | Exact action from the approval matrix; no wildcard grants. |
| `operation_sha256` | Digest of the exact writer-derived operation or configuration/schema binding. |
| `policy_sha256` | Exact policy digest using the existing binding semantics. |
| `rule_sha256` | Award rule digest, or shared qualification rule digest for capture; `null` for migration. |
| `population_sha256` | Existing operation-specific population digest; `null` for capture and migration. |
| `manifest_sha256` | Canonical manifest digest; `null` for capture, delivery and migration. |
| `snapshot_sha256` | Geography scope-snapshot digest; `null` for First Look and migration. |
| `reference` | Retained independent review reference; not proof of identity. |
| `issued_at_utc` | Canonical whole-second UTC issuance time. |
| `not_before_utc` | Mandatory start of authorization validity. |
| `expires_at_utc` | Mandatory exclusive expiry; no unlimited production approvals. |
| `revocation_registry_id` | Protected registry identity, not an artifact-selected URL. |
| `minimum_revocation_sequence` | Nonnegative integer lower bound on authenticated registry state. |
| `usage` | Action-specific bounded capture window or one exact operation with integrity-only retries. |
| `evidence` | Action-specific retained evidence references, digests and dependent approval IDs. |

Reject duplicate JSON keys, unknown fields, wrong types (including booleans used
as integers), non-finite numbers, malformed hashes and noncanonical timestamps.
Hashes are lowercase SHA-256 hex. Preserve existing `rules.canonical()` and
`digest()` semantics for current bindings; do not change immutable manifest hashes.
The signed-format version must define exact canonical encoding, domain separator,
signature encoding and action-specific `usage`/`evidence` schemas before a parser
can be enabled. No free-form evidence object can grant extra permission.
Redundant explicit hashes must agree with content inside the operation binding.

### Approval matrix

These are proposed production approvals, not currently accepted signed artifacts.
Finality is a proposed distinct permission; existing writer action names stay intact.

| Approval | Family | Permission / action | Required binding and evidence |
| --- | --- | --- | --- |
| First Look capture | `first_look` | `capture / enqueue` | Existing `admission_binding(configuration)`: operation is configuration digest; policy is launch-policy digest. Bind activation/cutoff/provenance and shared qualification rule. Population, manifest and snapshot are null. Capture usage is time-bounded and does not authorize awards. |
| First Look finality | `first_look` | `finality / approve_closed_population` | Operation and manifest bind the complete reviewed First Look population manifest; population binds its inputs/report/identity/ledger; policy binds launch policy and rule binds the reviewed manifest rule. Evidence binds historical operation, qualified baseline hash, activation, exclusive frontier, gap inventory and baseline-link review. Snapshot is null. Grants no writes. |
| First Look delivery | `first_look` | `issuance / process_delivery` | Existing `delivery_binding()`: exact row/state/attempts, configuration, ledger/identity and stored claim. Policy is configuration policy; rule is the corresponding live rule. Manifest and snapshot are null. Does not authorize a new claim. |
| First Look live issuance | `first_look` | `issuance / seal_pending` | Existing `manifest_binding()` of exact live manifest; policy is configuration policy, rule is live rule, population binds inputs/report/identity/ledger. Evidence references authenticated finality approval; snapshot is null. Separate delivery approval remains required. |
| First Look historical baseline | `first_look` | `issuance / finalize` | Exact historical manifest, rule and population using `manifest_binding()`; policy equals manifest rule digest. Snapshot is null. Does not authorize activation or live finality. |
| Geography issuance | `geography_steward` | `issuance / finalize` | Exact manifest/rule/population using `manifest_binding()`; policy equals rule digest. Snapshot binds the supplied scope envelope. Evidence binds independent certification approvals and complete scope package. |
| Migration | `private_recognition` or `first_look`, matching the schema module | `migration / install` | Existing `migration_binding()`: operation and policy equal exact schema-definition digest. Rule, population, manifest and snapshot are null. Evidence binds prerequisite schema, target enrollment and deployment. |

Geography certification must authenticate complete membership, scope identity and
version, source/boundary evidence, snapshot hash, identity review, reconciliation,
evaluation timestamp and independent approver. Flags such as `independent: true`
are assertions, not authentication. Discovery labels never supply an approved
denominator. Finality approval must use the same opaque-authority infrastructure;
`build_guard()` remains an unwired policy helper today, not a second production
trust root. Its callback seam must not be used to provision production authority.
Retry recording and discrepancy append retain separate exact actions; an issuance
approval from this matrix does not implicitly authorize either.

### Target enrollment

An authenticated enrollment record must contain environment, hostname, protected
host identity, canonical absolute database path, file device/inode, canonical parent
directory path and device/inode, required link count (one), deployment identity,
enrollment ID and generation. It must also retain administrator/issuer identity,
review reference and issuance time. Store it outside the application database under
independent administrative control. Hostname alone is not host authentication.

Require an existing regular file, reject symlink/junction aliases and attached
databases, and match the connection's actual main database to enrollment. Protect
the path hierarchy from replacement. A filename or database content hash does not
prove enrollment. Existing pathname observations are not descriptor attestation.

Replacement, restore, relocation or host transfer retires the enrollment and
requires a new generation and new approvals. Device/inode checks alone cannot
detect every in-place restore or inode reuse: controlled maintenance must retire
enrollment before replacement. The application cannot self-enroll a selected path.

### Lifetime, trusted clock and revocation

Require `issued_at_utc <= not_before_utc < expires_at_utc`, no future issuance,
and `not_before_utc <= trusted_now < expires_at_utc` at authorization decision.
Protected policy must set finite maximum lifetime per action, registry freshness
limit and permitted clock uncertainty before production is enabled; these numeric
limits remain unapproved, so production remains blocked. Missing limits never
mean unlimited validity. Detect clock rollback and reject unreliable time; a
monotonic clock can bound elapsed time but does not establish UTC by itself.

Use an authenticated monotonically versioned revocation registry covering approval
IDs, issuer keys, enrollments and deployments. Verify sequence, freshness and
rollback protection, including across restart. An artifact's minimum sequence is
only a floor, not permission to ignore newer state. Signed offline lists provide
bounded freshness, not instantaneous revocation; the reviewed policy must define
when revocation becomes effective at the transaction coordinator.

| Condition | Required behavior |
| --- | --- |
| Revoked approval | Reject new authorization decisions; roll back uncommitted work before the final decision. |
| Revoked issuer/key | Reject every dependent approval, including otherwise unexpired artifacts. |
| Revoked enrollment | Reject all approvals for that enrollment/generation. |
| Expired/not-yet-valid approval | Reject; no grace period or automatic renewal. |
| Stale/unavailable/rolled-back registry | Fail closed; no cached-allow fallback for a new decision. |
| Target replacement or identity mismatch | Stop and require independent re-enrollment. |
| Manifest/population/snapshot change | Reject and require new preparation, review and exact approval. |
| Policy/rule change | Reject and require matching independent approval. |
| Invalidation after admission but before final commit authorization | Roll back the recognition transaction. |
| Uncertain commit outcome | Stop; reconcile the exact operation before retrying. |

Revocation prevents future authorization; it does not delete or reassign immutable
awards. Dependent finality and scope-certification approvals must also be current.

### Transaction linearization and crash reconciliation

Current repeated verification is not an atomic production revocation contract.
Historical finalization and migration recheck before commit, but live sealing
returns before its caller commits. Capture/retry/discrepancy paths also lack a
uniform final check. SQLite locks protect evidence, not external authorization
state, expiry or filesystem replacement. Another verifier call alone leaves a race.

A future protected coordinator must own the committing connection and serialize
the final authorization decision with revocation/enrollment changes. It must
validate all dependencies, freeze exact operation bindings, retain a unique commit
decision, and hold the coordination boundary through commit or rollback. Define
one consistent lock order. No arbitrary caller may receive a production-authorized
transaction and commit it later. Capture must encompass assignment completion,
shared evidence and pending insertion in that boundary. None of this is implemented
or changes current disposable writer semantics in Phase 1.

The proposed linearization point is the final authorization decision. Invalidation
before that point aborts the transaction. A decision already granted permits only
its immediate exact commit attempt; later revocation cannot retroactively undo it.
Expiry is evaluated at that decision, not guaranteed at the physical instant of
durable commit. If policy instead requires cancellation until physical durability,
this proposal is insufficient and implementation must stop for a stronger design.

Retain approval IDs/digests, enrollment generation, deployment, registry sequence,
operation digest and decision/outcome evidence. On crash, reconcile durable SQLite
records and coordinator evidence before releasing an uncertain operation for retry.
Do not mark success from a decision record alone, assume absence from a timeout,
reuse a decision for another operation, or blindly issue a replacement operation.
Exact recovery and durable receipt mechanics require later review and tests.

Migration approval is schema-, target- and deployment-specific: one transition
per enrolled generation and approved definition/deployment, with recorded outcome.
Integrity-only idempotent verification is permitted; a restore or new transition
needs new approval. No startup migration or automatic gate follows from approval.

### Production security stop conditions

- Production provisioning, signature verification or transaction coordination is absent.
- Trust pins, verifier code, enrollment or approval state lack independent protection.
- Issuer/approver identity, roles, signature or canonical format cannot be authenticated.
- Lifetime limits, clock reliability, registry freshness or revocation semantics are undefined.
- Any approval/dependency is revoked, expired, unavailable, stale or mismatched.
- Target replacement, restoration, aliasing or generation is uncertain.
- First Look baseline/finality or Geography complete-membership evidence is unresolved.
- A caller can bypass the protected commit boundary, or commit outcome is uncertain.
- Implementation would require fixture authority, permissive callbacks or relaxed guards.

Synthetic rehearsal success never clears these production stop conditions.

## Phase 2: strict synthetic artifact and enrollment verification

`artifacts.py` is an isolated validation module, not imported by any writer or
Flask integration. `authority.py`, `authorization.py`, existing canonical/hash
helpers and all writer transaction semantics remain unchanged. Production trust
configuration is unavailable; validation without the exact synthetic verifier
raises `production_trust_configuration_unavailable`. Nothing registers a production
authority, loads deployment artifacts, opens SQLite, contacts a registry or signs
an approval. A successful result is data and cannot authorize a writer.

### Explicit synthetic wire profile

The Phase 1 envelope and payload field sets are unchanged. Only the test profile
fixes the previously open encoding choices: format
`recognition-synthetic-approval-v1`, algorithm `Ed25519`, standard padded canonical
Base64 for 32-byte public keys and 64-byte signatures. Signature input is exactly
the ASCII bytes `DMV-recognition-synthetic-approval-v1`, one NUL byte, then
`rules.canonical(payload).encode('utf-8')`. Input key order and whitespace do not
matter; existing sorted-key, compact, ASCII-escaped JSON semantics remain intact.
Duplicate keys at any depth, unknown fields, floats (including overflow forms),
non-finite values and non-exact types are rejected. Existing ledger/report hashing
is not changed. This algorithm/profile is not an approved production wire format.

Unicode is preserved without normalization: equivalent JSON escape sequences and
literal characters decode to the same value and signature bytes, while composed
and decomposed Unicode sequences remain distinct. Python string JSON inputs also
accept lone surrogate code points; canonical ASCII escaping represents them as
`\ud800`-style escapes, so signature bytes remain deterministic. A raw lone
surrogate cannot be encoded with strict UTF-8. This describes the existing
string-input API, not comprehensive Unicode validation or a production Unicode
policy; the parser and existing ledger hashes are unchanged.

Tests include a fixed public-key/message/signature vector prepared independently
of repository signing/canonicalization helpers. The vector test stubs the entire
`validate_enrollment()` function because temporary paths/inodes cannot be fixed
across hosts; signature verification remains real. Separate tests exercise real
enrollment validation and filesystem behavior, preserve
original expected hashes and exercise target replacement, real ancestor symlinks
and parent-directory replacement. Symlink tests explicitly skip when Windows
does not grant the required creation privilege; mocked guard checks are not a
substitute for a real Linux run. A passing local run does not establish hosted
filesystem coverage.

Install `requirements-recognition-tests.txt` in the development test environment.
It pins the `cryptography` dependency; the hosted runtime requirements are not
changed. Private signing keys are generated only in tests and never persisted.

The following nested schemas explicitly complete the synthetic profile; they do
not silently fill in production policy. Every listed key is required, no extra
keys are accepted, and all digest fields are lowercase SHA-256 hex.

| Action | Exact `evidence` fields |
| --- | --- |
| `enqueue` | `activation_at_utc`, `historical_cutoff_utc`, `sqlite_utc_provenance` (text or null) |
| `approve_closed_population` | `historical_operation_id`, `historical_qualified_sha256`, `activation_at_utc`, `frontier_at_utc`, `gap_assignment_ids` (sorted unique positive integers), `baseline_link_review_reference` |
| `process_delivery` | `assignment_id` (positive integer) |
| `seal_pending` | `finality_approval_id`, `delivery_approval_id` |
| First Look `finalize` | `review_package_sha256` |
| Geography `finalize` | `review_package_sha256`, `certification_approval_ids` (nonempty unique string list), `evaluation_at_utc` |
| `install` | `prerequisite_schema_sha256` |

Capture `usage` has exactly `mode: bounded_capture`, `starts_at_utc`, `ends_at_utc`;
its nonempty window must lie within the approval lifetime and contain trusted now.
Other actions have exactly `mode: exact_operation`, `integrity_only_retries: true`.
These describe permitted usage; there is no consumption/replay ledger or coordinator
in Phase 2. References/digests do not certify the underlying package. Production
authentication of dependent approvals and retained evidence remains unimplemented.

### Synthetic trust, clock and revocation inputs

`SyntheticArtifactVerifier(trust_json)` accepts only strict serialized JSON. Its
trust object has exactly `keys`, `host_id`, `deployment_id`,
`revocation_registry_id`, `max_registry_age_seconds`, `minimum_registry_sequence`.
Each key has exactly `key_id`, `issuer_id`, `public_key`, `grants`. Each grant has
exactly `approver_id`, `family`, `permission`, `action`, `max_lifetime_seconds`.
Duplicate key IDs/public keys or grants are rejected. Issuer, approver and action
must match that separately supplied test configuration, never payload assertions.
Limits must be positive integers; no default lifetime/freshness policy is supplied.
Tests choose a 600-second maximum lifetime and 120-second registry freshness,
strictly as synthetic values, not production policy.

Trusted current time is an explicitly supplied canonical UTC value, not a callback
or system-clock fallback. `validate_artifact()` rejects time earlier than its
context's recorded time, updating that history before artifact parsing; a failed
artifact attempt can therefore still advance clock history. Standalone
`validate_enrollment()` checks enrollment issuance against supplied current time
but neither reads nor updates that history. It does not independently guarantee
monotonic time. Both reject future issuance relative to their supplied time, and
artifact validation separately enforces approval lifetime/expiry. The synthetic registry
has exactly `registry_id`, `sequence`, `issued_at_utc`, `expires_at_utc`,
`revoked_approvals`, `revoked_issuers`, `revoked_keys`, `revoked_enrollments`,
`revoked_deployments`; revoked lists contain unique nonblank strings. Registry
sequence cannot regress below configured, artifact or previously observed floors;
different content at the same observed sequence is rejected. Revoked dependent
approval IDs are rejected too. Missing/stale registry fails closed. Registry/clock
state is in memory only: no authenticated registry transport, restart-persistent
rollback protection, dependent artifact validation or production trusted clock is
claimed. Registry data and expected bindings are explicitly trusted test inputs.

### Synthetic enrollment and APIs

The verifier allocates a new temporary directory and pins its identity. It cannot
adopt an existing root. Tests create their own files there; validation rejects
outside paths before statting them. A fixture may model a production-labeled
enrollment, but this is never production enrollment or DisposableWorkspace authority.
The exact enrollment fields are `enrollment_id`, `enrollment_generation`,
`environment`, `host_id`, `hostname`, `database_absolute_path`, `device`, `inode`,
`parent_directory_absolute_path`, `parent_device`, `parent_inode`,
`required_link_count`, `deployment_id`, `reference`, `issuer_id`, `issued_at_utc`.
The environment must be `production` to model the Phase 1 representation; a
disposable label cannot be substituted. Expected enrollment ID, generation and
canonical hash must be supplied independently of the artifact by the test harness.
An enrollment hash is not a hash of database contents and does not authenticate an
administrator by itself. Production enrollment authentication remains unavailable.

- `canonical_payload_bytes(payload_json)` defines synthetic signature input only.
- `validate_enrollment(...)` checks strict representation, expected hash/generation,
  deployment/host, existing regular file, canonical absolute path, alias rejection,
  device/inode, parent identity and link count. It returns data, not registration.
- `validate_artifact(...)` checks the signature, authorized issuer/approver/action,
  exact action bindings/nulls, enrollment, mandatory bounded lifetime and registry.
  `expected_binding_json` must contain exactly family, permission, action,
  operation/policy/rule/population/manifest/snapshot hashes, reference and evidence.
  This input represents independently computed bindings; the validator does not
  replace existing manifest preparation, certification or finality evaluation.
- `ValidatedArtifact` holds only immutable canonical JSON and its digest, retaining
  no mutable caller input and providing no conversion into Authority/Authorization.
- `SyntheticArtifactVerifier.directory` exposes only its fresh fixture root;
  `cleanup()` closes that context and removes its temporary files.

The current production provisioner still unconditionally rejects. Neither a valid
signature nor a synthetic verifier/result can satisfy existing writer authority
checks. Production provisioning, transaction coordination and activation remain
outside this phase.

## Validation

Adversarial tests exercise actual writer APIs: accepting callbacks/custom objects,
unregistered handles, production provisioning rejection, environment/target changes,
disposable root isolation, cross-delivery deferral/quarantine/retry replay, completed
acknowledgement binding, removed direct insert APIs, live-manifest rejection by the
historical finalizer, caught insert failures followed by outer commit, authority
failure after insertion, and nested manifest/candidate/discrepancy mutation.
Existing tests retain qualification, finality, frozen-denominator, immutable-ledger,
migration, Flask workflow, and Explorer issuance/isolation coverage. No production
data is used by these synthetic tests.
