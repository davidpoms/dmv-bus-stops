# Recognition: disposable/test-only deployment readiness

This is a manual operator checklist, not a deployment record or production
authorization. No PythonAnywhere connection or production database inspection was
performed. The supported recognition rehearsal is the existing synthetic test
suite: it creates its own disposable SQLite files and uses no production snapshot.
It is not a populated web-demo database or an automatic application migration.

## Risk inventory and startup contract

- Flask, the Waitress runner, recognition CLI imports, and their dependencies do
  not connect to SQLite or run recognition migrations/writers on import. Fresh
  subprocess tests trap connections, migration, capture, processing, sealing and
  authority provisioning. The runner is also exercised with its server stubbed.
- Flask and assignment routing formerly defaulted to the repository database.
  Both now use `configured_database()` and require an explicit absolute
  `DMV_BUS_STOPS_DB`. Missing/relative configuration selects no database; normal
  HTTP requests fail with 503. Missing files and mismatched API/router targets
  also fail before routes execute. No target is created automatically.
- `app.testing` permits fixture-controlled database injection; never enable it
  in the hosted web application. Normal WSGI configuration is not Flask TESTING.
- The API loads the repository `.env` before selecting its target. Do not upload
  a production/local `.env` or inherit production service variables in the test
  checkout. Explicit environment values take precedence over dotenv loading.
- An explicitly selected existing file is not proof of disposal. Ordinary review
  routes can write to their configured database. Keep any hosted test web app
  isolated from production storage and traffic; separately review its synthetic
  database path and permissions. Unknown hosted paths are not guessed here.

## Code, dependencies and working directory

1. Review the entire dirty tree and include required untracked recognition source
   and test files. A HEAD SHA alone does not identify this uncommitted release.
   Preserve unrelated work; do not upload repository databases, `.env`, retained
   manifests, approval/binding files, credentials, logs, or local `.tmp` artifacts.
2. Use a separate test checkout/environment. Preserve the existing production
   checkout, WSGI configuration, process and database. Record the tested code
   inventory and previous test release for rollback.
3. From the test repository root, in the explicitly selected virtualenv, use the
   repository-established hosted runtime command:

   ```bash
   python -m pip install -r requirements-pilot.txt
   ```

   The synthetic unittest rehearsal below needs the runtime and standard library.
   Pytest and optional tooling are needed for the broader release suite; use the
   project's reviewed development environment. `requirements-pilot.txt` does not
   install pytest or the scientific/offline stack. Do not install/run Waitress on
   PythonAnywhere; that host supplies WSGI. No dependency versions are changed by
   this pass. Verify compatibility in the selected host virtualenv before use.

## Explicit disposable rehearsal and migration

Run from the test repository root, without a production environment file or
production database credentials/permissions:

```bash
python -B -m unittest tests.test_recognition_deployment tests.test_recognition_authorization tests.test_live_first_looks tests.test_recognition_permanent tests.test_private_recognition_rehearsal tests.test_explorer_issuance_rehearsal
```

This is an explicitly invoked synthetic rehearsal, not startup work. It:

- allocates fresh temporary SQLite targets and minimal synthetic prerequisite data;
- provisions only `DisposableWorkspace` capabilities rooted in directories they
  create, with pinned path/device/inode identities;
- explicitly applies the Explorer prerequisite schema and authorized private/live
  migrations to those synthetic files, and checks read-only migration rehearsals;
- exercises First Look capture, pending processing, finality, immutable claims,
  Geography reports/frozen scopes/awards, rollback and Explorer isolation;
- verifies production provisioning raises `production_authority_not_provisioned`;
- removes its temporary files and revokes workspace capabilities during cleanup.

No database argument is accepted by this test command: it creates targets rather
than adopting an arbitrary existing file. This is safer than adding a generic
rehearsal command that can be pointed at a production path. All approval objects
are synthetic and process-local. None can authorize production or survive cleanup.

The existing `rehearse_private_recognition.py` verification mode remains available
for independently supplied offline artifacts. Its issuance CLI is still blocked:
`--apply-disposable` alone does not provision an authority. Do not use retained real
manifests or change its guards to make an old example command succeed.

File-backed `permanent_schema.install/migrate` and `live_first_look_schema.install/
migrate` still require exact schema approval and a provisioned authority. Their
default migration copies the source into memory; attached-file exemptions are
rejected. Production authority provisioning remains unavailable. The Explorer
`create_recognition_tables.py --apply` command retains its separate existing
contract; it does not authorize First Look or Geography and is not needed outside
the synthetic fixture setup in this procedure.

## Optional isolated WSGI configuration

The console rehearsal above does not require a hosted web app. If separately
reviewing web startup, follow the existing host mechanism in
[DEPLOY_LIMITED_PILOT.md](DEPLOY_LIMITED_PILOT.md): add the test repository root to
`sys.path`, configure the test environment before imports, and expose:

```python
from src.api.app import app as application
```

Use a separately prepared synthetic application database with the full web schema;
the minimal recognition fixture is not a general web-demo database. Do not point
this import at production or at an empty/mistyped file. Set:

- `DMV_BUS_STOPS_DB` to its reviewed existing absolute test path;
- a separate deployment-owned `FLASK_SECRET_KEY`, secure cookies and test support
  contact as described in the existing runbook;
- `LIVE_RECOGNITION_CAPTURE=0`; leave First Look gate/configuration/authority at
  their disabled/None defaults and do not set Flask TESTING or dev authentication;
- no production email credentials, authorization material, or real activation.

The test identity must lack write access to production storage. If this isolation
cannot be established, do not serve a test web app; run only the disposable console
rehearsal in an appropriately isolated environment. No automatic initialization is
added for either option. Use the existing web-app control for a manual test reload;
no host paths, SSH commands, scheduler, or service configuration are invented here.

## Existing production runbooks are not test instructions

[Reviewer deployment runbook](reviewer-deployment-runbook.md) and
[limited pilot deployment](DEPLOY_LIMITED_PILOT.md) retain their production backup,
`create_review_tables.py`, role-management and reload procedures. They operate on
the configured database and must not be copied into this recognition rehearsal.
The Waitress runner validates full pilot configuration; the direct WSGI import
does not run that complete validator. The new request guard covers database
selection, not every deployment secret/email/support requirement.

`create_review_tables.py` is a legacy explicit migration script whose module body
opens and mutates its selected database, with a repository fallback. Do not import
it from WSGI or use it to initialize this rehearsal. It is not imported by the
audited application startup. The existing `workflows/update_ridership.yml` invokes
general database initialization/ridership scripts, not recognition migrations; it
is unrelated to this test deployment and must not be repurposed as startup work.

## Rollback and remaining external responsibilities

On a rehearsal failure, retain only sanitized test output and fix the issue before
continuing. Temporary fixtures clean themselves up; do not delete an arbitrary
configured database as cleanup. If a killed test leaves a directory, identify that
exact disposable root before removing it. Stop any isolated test web app before
removing its independently recorded test artifacts or restoring its previous test
code/environment. Production rollback, migration and data restoration are outside
this procedure and must not be invoked.

Path identity checks do not protect against unrestricted Python/SQL execution,
filesystem replacement or moving production data into a disposable workspace.
Operator permissions, host enrollment, production trust root, reviewed populations
and scopes, revocation policy and production authorization remain external and
blocked. Local passing tests establish repository readiness, not hosted deployment
verification or permission to activate recognition.
