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
