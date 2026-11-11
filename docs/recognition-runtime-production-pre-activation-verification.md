# Production pre-activation verification

## Decision

**B - PRE-ACTIVATION BLOCKED.** The approved local package passes verification;
there is no baseline mismatch or new architecture issue. Actual PythonAnywhere
configuration/installation evidence and approved public trust material remain
unverified, and activation is not authorized. These are operational prerequisites,
not requests for the owner to determine implementation details.

Owner confirmations now recorded: the target is the live PythonAnywhere
application; the project owner is its custodian/deployment operator; the intent
is to deploy the R30 package; the owner is prepared to perform rollback using
the [plain-language procedure](recognition-runtime-production-rollback-procedure.md).
These confirmations do not themselves identify the authenticated runtime account
or establish an actual public verification key.

Reviewed: [R30](recognition-runtime-security-production-authorization-decision-4e-20-R30.md),
the [preparation runbook](recognition-runtime-security-production-deployment-preparation.md),
the [owner checklist](recognition-runtime-production-activation-checklist.md),
[R29](recognition-runtime-security-final-production-readiness-review-4e-20-R29.md),
the local package/manifest and the actual provisioning, configuration and owner APIs.

## Local artifact: PASS

| Check | Result |
| --- | --- |
| ZIP SHA256 | MATCH: `d1eb8ddc0dddae3dc1e4cbd26221dc0b859ba6ca3a141b69e079ddeaa3391e59` |
| Manifest SHA256 | MATCH: `1ff86e5711893df4d54e4610496c12ee98697440e50fe96d23c9ddac64f713fd` |
| Approved baseline | All 21 recorded entries match |
| Package contents | All 88 source modules match manifest and working sources; exact ZIP membership and integrity pass |
| External dependency references | Both recorded reference hashes match locally |
| Activation/execution metadata | Both remain false |

Artifact directory: `.tmp/recognition-production-deployment/1ff86e5711893df4/`.
No installed production files were inspected. The source overlay is not a full
application release and contains no database, credentials, key, approval or
activation script. The package and its manifest were not changed.

## Technical configuration determined from code

Codex can assemble and mechanically validate these details after separately
authorized inventory/setup. The owner does not need to calculate hashes, choose
schema fields, edit SQL or reconstruct runtime identities.

| Component | Exact requirement | Still needed from the actual deployment |
| --- | --- | --- |
| Web application | Existing PythonAnywhere WSGI application; repository import is `from src.api.app import app as application`. Environment must be set before import. | Actual app selection, WSGI/source directory, Python/virtualenv and installed application/dependencies |
| Application database | `DMV_BUS_STOPS_DB`: existing absolute target database path, not a default/new empty SQLite file | Actual configured path and identity, to be discovered mechanically |
| Administrative storage | `RECOGNITION_ADMIN_CONTROL` and `RECOGNITION_ADMIN_KEY_FILE`: explicit absolute control DB and existing host-held Fernet key file, each distinct from target | Actual binding and paths; check key presence/protection without exposing its contents |
| Finalizer path scope | Target, control and host-key file share the exact canonical parent directory; no symlink/path rebinding | Filesystem identity/layout verification, not an invented path or automatic move |
| Existing web safety | Preserve existing `FLASK_SECRET_KEY`, secure HTTPS cookies, authenticated owner/MFA, non-development authentication and current service configuration | Verify configured presence/protection; do not print or rotate secrets as part of preflight |
| Recognition gates | Keep capture disabled during deployment (`LIVE_RECOGNITION_CAPTURE=0`); web issuance remains false in the reviewed app. Capture is not runtime activation. | Actual environment and activation-ledger state; do not infer activation from a flag |
| Runtime enrollment | Reviewed installation/target/owner, generation/profile and activation incarnation; runtime challenge settings only from actual reviewed enrollment | Actual current records, schema/fingerprints and enrollment evidence |
| Public trust root | Fixed file beside control named `<control filename>.governance-root.json`; canonical closed fields: `format`, `mandate`, `installation_id`, `owner_id`, `public_key` | Authorized public key/provenance and actual installation/owner IDs |
| Root constants | Format `recognition-runtime-production-governance-v1`; mandate `dmv-bus-stops-g1-governance-mandate-4e-20-G13-v1`; canonical base64 raw Ed25519 public key | Owner-approved signer/custody and protected installation; no arbitrary/test key substitution |
| Signed approvals | Canonical closed body: format, mandate, installation_id, binding_sha256, holder, subject, target, control, issued_at_utc, expires_at_utc, approvals. Ed25519 domain: `DMV-runtime-production-governance-v1` followed by a NUL byte. | Exact actual scope and authorized signature; Codex derives bodies/digests from authoritative records, not guessed values |
| Approval bounds | Current authentication and original credential-expiry clipping; existing maximum 600-second administrative approval interval | Fresh real credentials/approval timing at the authorized ceremony; this is not a 600-second source lifetime |
| Registry | Fixed `authority.provision_production_authority` verifier creates an opaque process-local handle after authentication | No registry file/env switch to install. Creation/use must stay in the original process/live thread; do not pass handles between WSGI workers or requests |
| Approval purposes | Exact journal install; separate bind/adopt/appoint/authorize issuer decisions; exact issuer revocation; exact-D inspection | Real attributable approvals. No execution issuer/source is created during this preflight or deployment preparation |
| Journal/schema | Verified A/T/E/L prerequisites for exact J control extension; existing W/Y owners install only exact ENTRY/witness packages and re-enroll profile where required | Current installed lineage and missing-package inventory, verified backups and no pending transition/unsettled runtime work |

There is no supported `ENABLE_PRODUCTION_AUTHORITY` shortcut or reusable JSON
credential. The private governance signing key stays outside this repository
and runtime package; the host MFA-encryption key is a different existing secret.
Do not generate either here. Owner identity is mapped through actual authenticated
account/enrollment records, not inferred from the phrase “project owner”.

Preserve v1/120 ordinary/default and v2/300 prospective/test-only. No policy or
test-only v2 adapter is activated by deployment configuration.

## PythonAnywhere deployment sequence - instructions only

The repository's [PythonAnywhere instructions](DEPLOY_LIMITED_PILOT.md#pythonanywhere)
and [official Flask guide](https://help.pythonanywhere.com/pages/Flask/) specify
WSGI plus the selected virtualenv; do not run Waitress or `app.run()` there.
The virtualenv Python version must match the web app, as described in the
[official import guide](https://help.pythonanywhere.com/pages/DebuggingImportError/).
Only public help pages were read; no account, app or hosted resource was accessed.

1. After permission for live inventory, Codex records the actual web app, WSGI,
   source/runtime paths, target/control/key locations, owner mapping, schema/
   profile/activation state and current code/dependency compatibility. Read-only
   discovery precedes changes. If the existing base application differs from the
   required overlay dependencies, stop; do not silently deploy unrelated files.
2. At the approved maintenance window, quiesce the affected app/recognition jobs.
   Preserve current code, WSGI/environment configuration and verified target AND
   control backups/manifests in protected storage. Keep recognition disabled.
3. Transfer the exact package/manifest/checksums, verify hashes at destination,
   install only the reviewed overlay, and verify installed module hashes. Use
   the existing selected virtualenv; the repository's lightweight runtime
   dependency reference is `requirements-pilot.txt` (including cryptography).
   Do not replace it with the geospatial/Waitress full-runtime installation.
4. Establish the independently approved protected public root before any signed
   migration that requires it. Install only missing approved packages through
   `runtime_finalization_schema_upgrade.migrate_control` and existing W/Y
   transition/enrollment APIs, with backups, exact approval and predecessor
   validation. No raw SQL, bootstrap against enrolled data or blind rerun.
5. Verify installed lineage, fingerprints, enrollment, configuration, owner
   authentication and rollback/inspection availability. These are technical
   checks Codex performs, not owner attestations about unknown internals. No
   production recognition authority or trial execution is a smoke test.
6. Reload the existing web app only after code/configuration is consistent and
   no original live ceremony is in flight. PythonAnywhere reloads replace worker
   processes; they do not preserve process-local handles. See the
   [official reload description](https://help.pythonanywhere.com/pages/ReloadWebApp).
   Check ordinary application health/logs with recognition still disabled.
7. STOP before recognition activation. Present actual verification results and
   request the separate explicit activation decision for the exact permitted
   scope. No deployment or activation step above has been performed here.

## Remaining owner decisions - only human confirmations

- [ ] Confirm the intended PythonAnywhere app if the account contains more than
  one, and authorize the next live read-only inventory/deployment maintenance
  window. Codex will discover the technical paths and identifiers afterward.
- [ ] Approve the actual signing-key custodian/public fingerprint once presented,
  or authorize a separate protected key-setup operation if none exists. Confirm
  who may activate and perform emergency revocation; the project owner is
  already confirmed as production custodian/deployment operator.
- [ ] Accept the [rollback procedure](recognition-runtime-production-rollback-procedure.md),
  including temporary downtime and no retry when commit/outcome is uncertain;
  confirm the owner will act as rollback owner as already offered.
- [ ] After installed-state verification, explicitly approve activation and the
  permitted production operation scope under unchanged policy. This preflight
  is not that approval.

Do not ask the owner to manually confirm SQL definitions, numeric IDs, runtime
hashes, registry internals or Python configuration that Codex can inspect.

## Concrete unresolved items and safety

1. No authorized live inventory has occurred: actual base-app compatibility,
   database/control/key layout, owner mapping, schema/lineage/profile and backup
   state cannot yet be mechanically verified.
2. No real approved public trust material/custody and exact approval binding has
   been supplied or established. Code defines the configuration but cannot
   establish the trustworthiness of an arbitrary key.
3. The maintenance/rollback confirmations and separate activation approval above
   remain pending. Platform and deployment-operator identity are confirmed and
   are no longer listed as unresolved.

No live PythonAnywhere access, production change, production authority issuance
or production activation occurred. Only local archive/source inspection, public
help-page reading and documentation work occurred. No tests/lifecycle, code,
schema, policy, permissions, artifacts, commit or push were changed/run.
Document checks and `git diff --check` are the final checks.

PRODUCTION AUTHORIZATION: GRANTED FOR DEPLOYMENT
PRODUCTION EXECUTION: BLOCKED
PRODUCTION ACTIVATION: BLOCKED
