# Recognition production deployment preparation

## Status and authorization

**A - DEPLOYMENT PACKAGE READY; ACTIVATION PREREQUISITES REMAIN.**

[R30](recognition-runtime-security-production-authorization-decision-4e-20-R30.md)
authorizes deployment only. This task prepares local files and operating
instructions; it does not deploy them. Production execution and activation
remain blocked. No architecture stage, implementation change or new permission
is introduced.

The validated basis remains
[R28](recognition-runtime-security-production-integration-4e-20-R28.md) and
[R29](recognition-runtime-security-final-production-readiness-review-4e-20-R29.md):
88 focused tests / 96 subtests, owner-failure coverage and one clean isolated
owner lifecycle. No test or lifecycle was rerun for this preparation.

## Prepared artifact and verification

The source-only overlay is
`recognition-r28-source.zip` (available through the approved artifact handoff).
It contains 88 `src/review/recognition/*.py` modules and an inert deployment
manifest. It is an overlay for the existing approved application/runtime, not
a standalone web application, installer or executable production configuration.
It does not package unrelated working-tree changes.

| Material | SHA256 |
| --- | --- |
| Source ZIP, 342379 bytes | `d1eb8ddc0dddae3dc1e4cbd26221dc0b859ba6ca3a141b69e079ddeaa3391e59` |
| Deployment manifest | `1ff86e5711893df4d54e4610496c12ee98697440e50fe96d23c9ddac64f713fd` |

The matching `DEPLOYMENT-MANIFEST.json`
records every source hash, approved baseline checks, exclusions, dependency
references and migration entry points.
`SHA256SUMS`
records the archive and manifest digests. These metadata files are not authority
formats and are never consumed as production approvals or activation settings.

The [versioned source-hash record](recognition-runtime-r30-approved-source-manifest.md)
retains the approved source/dependency and test-evidence hashes for Git delivery.
Archives, private fixture evidence and local `.tmp` paths are not Git content.
Repository attributes preserve approved source bytes across Git checkouts;
they do not change Python behavior, policy or the approved ZIP.

All **21 recorded baseline entries** match: R28's final 16 entries plus five
non-replaced R26 entries. R28 intentionally updated files use the final R28
digest. The explicit authority-schema, lifetime-policy, journal-installer,
lineage, provisioning and finalizer baselines are unchanged. No implementation
file was modified. Archive members were checked for exact source bytes, exact
membership and ZIP integrity; approved input hashes were rechecked afterward.

The manifest additionally freezes all packaged recognition dependencies. It
references, without packaging or changing, the existing
`requirements-pilot.txt` and `src/amenities/status_synthesis.py` by hash. The
receiving base application must satisfy those dependencies and the reviewed
runtime, including the existing cryptography dependency. An absent or different
base application is not silently replaced by an arbitrary full-workspace release.

The archive contains no databases, credentials, private/public deployment key
material, signed approvals, production configuration, tests, test-only v2
adapters, activation scripts or automatic migration entry point. The existing
inert package initializer is unchanged. `.tmp` is local staging, not a committed
release store: retain or transfer these exact files through the authorized
release handoff before cleaning local staging, then verify the recorded hashes
again. No transfer or publication has occurred here.

## Deployment components

| Component | Prepared material / exact existing owner | Limits |
| --- | --- | --- |
| Recognition code | Source overlay and file manifest | Reviewed package only; no unrelated application rollout |
| Control journal migration | `runtime_finalization_schema_upgrade.migrate_control`; exact `recognition-runtime-finalization-journal-extension-v1` J edge | Verified A/T/E/L predecessors, inactive state, exact approval/generation/identity, no unfinished transition or unsettled runtime work |
| Target metadata/witness package | `runtime_enrollment_transition.transition`, then `enroll_transition_runtime_profile` | Only exact ENTRY or `recognition-runtime-outcome-witness-storage-v1`; existing W/Y reservations, verified backups, fingerprinting and reviewed profile enrollment |
| Historical compatibility | Existing ordered `runtime_schema_package_lineage` and historical plan projections | Preserve old hashes and verified audit position; reject arbitrary predecessors and packages |
| Lifetime compatibility storage | Existing `runtime_authority_lifetime_policy.migrate`, only if actually missing and approved | Storage compatibility is not v2 policy activation; do not rerun an already-installed migration blindly |
| Production provisioning | Fixed `authority.provision_production_authority` / `runtime_production_governance` | Exact signed approval, protected root and current authenticated owner; no caller verifier or disposable substitution |
| Outcome inspection | Existing `runtime_finalization.inspect_outcome` | Exact-D factual inspection, never a retry credential |

The migration package is the exact validated Python modules in the overlay, not
an extracted SQL script. Do not invoke a bootstrap installer against an enrolled
database, manually edit fingerprints, rewrite historical hashes or bypass the
owners with direct SQL. No schema is installed or migration invoked here.

## Required real production bindings

No actual production values were supplied for this preparation, and production
was not queried to discover them. Each item below is **UNRESOLVED**. No placeholder
trust file, `.env`, credential or runtime configuration is generated.

| Binding | Required actual evidence |
| --- | --- |
| Deployment/installation | Approved environment and release artifact, installation ID, target ID, original owner ID, current generation/profile and activation incarnation |
| Target/control databases | Explicit approved absolute paths, physical identities, current schema/fingerprints, installed lineage/predecessors and verified paired backups; never infer a target from this workspace |
| Public trust root | Independently approved public key/fingerprint and custody, exact mandate/installation/owner binding, protected destination beside actual control, authorized installation/replacement process |
| Owner/governance | Attributable actual installation-owner identity and existing primary/session/MFA permissions; project-owner text alone is not runtime identity |
| Issuer/custodian | Named authorized original holder and exact constrained appointment/action scope; no automatic appointment occurs during deployment preparation |
| Signed approvals | Real attributable exact subjects, policy, holder scope, physical identities and clipped validity; no synthetic signatures or test credentials |
| Production approval registry | Genuine process-local registration created by the fixed verifier after actual authentication; it is not a file to copy or a disposable registry to relabel |
| Deployment configuration | Actual approved application/runtime and dependency match, paths, inactive state and current v1/default policy; no test clock, fixture profile or test-only v2 adapter |
| Rollback | Named custodian with existing permissions, verified backups, compatible inspection/rollback artifact and accepted pending/uncertainty procedure |

## Custodian confirmation and trust-root instructions

Record the actual deployment operator, installation/governance owner, public-key
and signing-approval custodian, prospective constrained issuer holder and rollback
custodian. Confirm each role's existing authority and exact scope. This is an
inventory of responsibilities, not a new requirement that each be a distinct
person; apply the approved separation rules and never infer self-appointment.

The production operator must independently check each named identity and approved
key fingerprint against attributable governance input. A developer account,
test owner, disposable capability or locally generated arbitrary key is not
substitutable. No such identities or appointments are verified in this task.

The fixed verifier expects a canonical public-root file beside the approved
control database named `<control filename>.governance-root.json`. Its closed
fields are `format`, `mandate`, `installation_id`, `owner_id`, `public_key`;
the existing format is `recognition-runtime-production-governance-v1` and the
mandate is the exact approved constant. Supply only real independently approved
values. No example JSON with plausible credentials/identities is provided.

Only the public root is installed on the runtime through the authorized protected
configuration process. Keep private signing material outside this repository and
outside the package. Exact signed approvals must match the verifier's closed
schema and fixed domain, actual physical target/control identity, holder,
installation binding, policy and original credential-clipped interval. Use fresh
authenticated original-owner verification; deployment documentation cannot create
the registry handle. Missing, mismatched or expired evidence must deny.

## Operational sequence and activation stop

1. Obtain the unresolved actual bindings and custodians before any production
   operation. Verify archive and manifest hashes, exact file membership and
   receiving application/dependency compatibility. Keep recognition inactive.
2. When separately instructed to deploy, install only the verified source
   artifact. Verify installed bytes before using any migration/provisioning API.
   This preparation task does not perform that installation.
3. Install/verify the independently approved protected public trust input before
   any migration requiring its signed approval. Verify backups and exact current
   schema/generation first. Use only missing reviewed migrations through their
   existing owners, in verified predecessor order. Complete required W/Y profile
   review; never adopt a partially committed transition automatically.
4. Verify the resulting lineage, physical identities, fingerprints, reviewed
   profile, approvals, registry prerequisites, policy and rollback path. Do not
   create an execution issuer/source or recognition operation to perform this
   preparation. Production recognition authorities remain prohibited.
5. **STOP before activation.** Obtain the explicit R30 activation decision with
   actual bindings/custodians confirmed. Do not treat deployment permission,
   successful tests or this package as that decision.

| Activation prerequisite | Current confirmation |
| --- | --- |
| Actual target/control/installation/owner bindings | UNRESOLVED |
| Authorized deployment, governance, signer, issuer and rollback custodians | UNRESOLVED |
| Actual protected public root and fingerprint | UNRESOLVED |
| Actual signed approvals and genuine registry verification | UNRESOLVED |
| Actual installed schema/journal lineage and reviewed profile | UNRESOLVED |
| Local package hash | VERIFIED above; installed production hash remains UNVERIFIED |
| Actual backup, compatible inspection and rollback path | UNRESOLVED |
| Explicit production activation authorization | NOT GRANTED |

The stop condition is met: required items are missing, so no activation or
production action follows. This package alone cannot establish runtime authority:
it contains no credentials/root/approvals/configuration, runs no activation step,
and does not change the existing default-disabled package gate. Missing trust
input or invalid authentication/scope denies through the existing runtime
mechanisms. Custodian confirmation and rollback acceptance also remain explicit
operational authorization requirements; no new automatic enforcement mechanism
is claimed or added. No statement about a currently deployed production state is
made, because no production connection occurred.

## Policy and rollback instructions

Preserve **v1 = 120 seconds**, ordinary/default, and **v2 = 300 seconds**,
prospective/test-only. No 600-second source policy, automatic selection or
expiry extension is introduced. The issuer/finalizer model, original-holder
binding, exact action/write set, fresh checks and permanent duplicate fencing
are unchanged.

For an incident, the named authorized operator stops new ceremonies and uses
existing authenticated revocation/activation controls under their current
permissions. Preserve both databases, audit/lineage, decision exclusions,
witnesses and outcome inspection. Retain readers compatible with installed J
and lifetime history; do not revert to an incompatible binary or drop storage.

Inspect the original D and recompute actual target proof for an uncertain
outcome. Target effect plus witness may be committed while control is pending;
that does not authorize another effect. Missing witness alone is not proof of
rollback. Do not restore one database to an earlier point, erase exclusions,
automatically repair control history, adopt an old handoff or retry execution.
Halt and retain evidence if outcome or rollback compatibility is uncertain.

## Validation and final status

Baseline and source/archive hash verification, exact ZIP membership/integrity,
document whitespace/local links and `git diff --check` passed. The artifact was
built without importing recognition runtime modules or opening SQLite. No
implementation, schema, permission or policy change; no production connection,
migration, schema installation, trust provisioning, authority issuance,
recognition execution or activation; no tests/lifecycle, commit or push.

**A - DEPLOYMENT PACKAGE READY; ACTIVATION PREREQUISITES REMAIN.** The next
operational input is the real deployment binding/custodian record followed by
the explicit R30 activation decision. No R31 or architecture chain is created.

**PRODUCTION AUTHORIZATION: GRANTED FOR DEPLOYMENT**
**PRODUCTION EXECUTION: BLOCKED**
**PRODUCTION ACTIVATION: BLOCKED**
