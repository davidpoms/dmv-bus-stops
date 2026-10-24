# Slice F: disposable deployment rehearsal

PythonAnywhere classification: **NOT ASSESSED — disposable access unavailable**.
The request permits hosted contact only when an operator explicitly supplies
disposable access. None was supplied. No account, application, SSH session,
external documentation, production storage or provider was contacted. Selecting
one of the three suitability classifications without hosted observations would
misrepresent the evidence. PythonAnywhere remains preferred, pending rehearsal.

This report completes the available local work and records the unavailable
hosted work. It does **not** certify a completed PythonAnywhere deployment.
No application code, production rejection, readiness evidence or authority was
changed by Slice F. High-assurance Slices 4–7 remain dormant/test-only.

## Deployment inspection

Repository inspection, rather than inspection of any deployed account, found:

- `docs/DEPLOY_LIMITED_PILOT.md` configures PythonAnywhere's WSGI service with
  `from src.api.app import app as application`; no account-specific WSGI file is
  present. The separate `scripts/active/serve_pilot.py` validates configuration
  and runs Waitress with four threads. Do not use that runner on PythonAnywhere.
- `src/api/deployment.py` requires an explicit absolute `DMV_BUS_STOPS_DB`.
  Runtime request checks require an existing file and matching API/assignment
  targets. Missing, relative or mismatched configuration fails closed. Flask
  testing injection remains fixture-only. The application loads dotenv: a
  disposable deployment must not inherit a production `.env` or credentials.
- `RECOGNITION_ADMIN_CONTROL` and `RECOGNITION_ADMIN_KEY_FILE` are explicit
  separate paths, configured before import. No administrative store is installed
  at startup. Target/control/key separation is checked. The key is host-held;
  encrypted MFA state is in control storage, not plaintext in the target.
- Dashboard static files are served from `src/dashboard/static` through
  `send_from_directory`; database, control, backup and key directories must never
  be configured as a public static/media directory.
- `administration.connect` opens existing files only (`mode=ro`/`rw`), enables
  foreign keys, uses query-only readers and `synchronous=FULL` writers. It leaves
  journal mode unchanged and uses SQLite's Python default connection timeout
  (five seconds). No recognition WAL/checkpoint scheduler is installed. WAL must
  be assessed explicitly; merely switching it on is not a mitigation proven here.
- Control then target `BEGIN IMMEDIATE` is the administrative lock order. Writer
  effects and the durable execution seal share one target commit. Control/target
  commits are separate transactions; cross-database atomicity is not claimed.
- `manage_recognition_administration.py scan-approved` is a bounded trusted-host
  entry to discovery and the normal coordinator. It is not an installed daemon
  or scheduled task. No PythonAnywhere task schedule/process configuration is
  available in this checkout. Explorer's separate processing CLI is not a
  replacement recognition worker.
- `scripts/active/backup_database.py` already uses SQLite's backup API and checks
  integrity/FKs and pilot table counts. It backs up one database, has no paired
  recognition-control barrier or retention mechanism, and was not invoked.
  Its source-file hash is not proof of an online WAL snapshot's logical content.

## Observation register

All local observations use newly allocated synthetic SQLite files and synthetic
owner/MFA/installation data. They do not use a production copy. The local runtime
is Windows 11, repository `.venv` Python 3.14.6, SQLite 3.50.4, and the local
temporary filesystem.
Tests use fixed UTC clocks for administrative and retention behavior.

| Requested report item | TESTED LOCALLY / repository finding | NOT TESTED ON PYTHONANYWHERE |
| --- | --- | --- |
| 1. Disposable environment | Fresh registered production-format fixture; no arbitrary target argument | Account, plan, app, host, filesystem and process identities unavailable |
| 2. Configuration | WSGI import, strict configured target, explicit control/key, default disabled gates covered by startup and A–E tests | Real WSGI environment, proxy, virtualenv, routing and reload |
| 3. Filesystem | Temporary target/control writes, replacement detection; local DELETE and WAL processes | Hosted inode/device observations, WAL/shm creation, shared filesystem locking and persistence |
| 4. Concurrency | Separate-process writer reservation excludes another writer; reader sees prior committed value; lock timeout; writer succeeds after release/restart. A–E barriers cover duplicate workers/approvals/operations | Real hosted web/worker concurrent load, timeout envelope and process visibility |
| 5. Worker lifecycle | Existing restart discovery/continuation tests, completed/claimed fencing, stop/stale/session/generation checks | Actual scheduling, duplicate startup, termination, task limits, supervision and reload |
| 6. Writer locks | Existing production-format disposable First Look/Geography tests exercise fixed writers, one-use capabilities, rollback, seals and duplicate exclusion | Both families under actual hosted web/worker process model |
| 7. Backup mechanism | Explicit disposable paired SQLite backup, control-then-target barrier, UUID, UTC time, daily policy and 30-day metadata | Installation of daily hosted schedule, scheduler failure notification and storage capacity |
| 8. Verification | Reopens both stores; integrity and FK checks; exact schema/table inventory, row counts/content hashes, control binding/install/target/generation checks; changed backup rejected | Real hosted backups and restore drills |
| 9. Retention | Fixed clocks: exact 30-day boundary retained; older eligible; deterministic repeat; latest verified point retained even when old; active files rejected; unknown contents fail closed | Hosted scheduled pruning and filesystem permissions |
| 10. Restore | Offline target replacement from verified backup with completed and approved pending operations; surviving control inventory unchanged; invalid backups refused | Hosted stop/checkpoint/restore/restart sequence |
| 11. Generation | Target mismatch detected; explicit preview/rebind advances 1→2, invalidates pending approval and session, preserves completed history; no pending continuation; activation resets | Independent hosted placement, operational controls and recovery after loss of control store |
| 12. Crash/restart | Actual local subprocess kill before/after SQLite commit in DELETE/WAL, integrity and subsequent writer acquisition. Existing coordinator fault tests cover claim, writer, seal and projection boundaries | Actual hosted coordinator/worker/web termination at each boundary |
| 13. Permissions | Backup files request 0600 and directory 0700; traversal/alias/unknown-file checks | Windows mode bits do not establish POSIX ACLs; hosted writable principals, database parents, journals, logs, secret and backup ACLs unknown |
| 14. Secrets | Synthetic fixtures only; no key/seed/session values printed by new rehearsal code; MFA/key and HTTP tests rerun | Host environment visibility, log capture, secret ACLs and static mappings |
| 15. Startup safety | Fresh subprocess import/runner tests prohibit connections, migrations, enrollment, provisioning and recognition writers; disabled configuration checks | Actual hosted startup/reload process |
| 16. Production gates | Existing unconditional activation and writer-provisioning rejection preserved and rerun | No production activation attempted or authorized |
| 17. Validation | See results below | Hosted validation unavailable |
| 18. Files | This report; `tests/recognition_storage_rehearsal.py`; `tests/test_recognition_deployment_rehearsal.py` | No deployed file changed |
| 19. Blockers | No local application failure requiring a code change; hosted evidence absent | Hosting compatibility, permissions, scheduling, daily backup operations remain deployment blockers |
| 20. Classification | NOT ASSESSED; absence of access is not evidence against PythonAnywhere | Cannot honestly classify acceptable/mitigated/unacceptable yet |
| 21. Mitigations | Preserve explicit paths, gates, stop, final checks, claim fencing, verified backups and explicit rebind | Determine any platform-specific mitigation from observations; none invented here |
| 22. Before activation | Complete hosted checklist, approved release/configuration and separate explicit production provisioning/activation work | This slice cannot authorize production |

## Disposable backup experiment

The helper is under `tests`, is never imported by application startup, and accepts
only a registered fresh `DisposableProductionExecutionWorkspace` context. It owns
a new temporary backup directory. It cannot be passed a production path through
a CLI, HTTP request, environment setting or configuration file. Each backup gets
a new UUID directory; repeated daily invocations create distinct verified sets.
This is an explicit experiment, not an installed production backup service.

The control writer reservation and target writer reservation span both SQLite
backup calls. Separate read-only source connections avoid calling `backup()` on
a connection with an active write transaction. The barrier prevents coordinator
and ordinary SQLite writers from changing either source during the pair. All
writers, including future tools, must respect SQLite locks. No distributed or
anti-administrator guarantee is claimed. Backup cost holds writer reservations;
hosted size/latency and timeout impact must be measured before scheduling.

Verification compares full logical schema/content inventories, file hashes,
integrity/FK results and target/control identities. These are corruption and
consistency checks, not signatures against a trusted administrator. Incomplete
or damaged entries fail closed and cannot authorize pruning or restore.
Unknown directory contents also prevent deletion. Only three explicitly named
files in validated owned backup directories are removed; no shell recursive
deletion is used. The active target/control/key live outside that root. The
latest verified backup always survives pruning; a backup exactly 30 days old
is retained. Local synthetic dates test daily cadence without waiting.

Backups contain administrative data and must be protected as sensitive. Host
Fernet/Flask keys are not included or printed. Recovery of those keys requires a
separately reviewed protected host-secret procedure; losing them is not solved
by copying the target. Copied control storage is recovery evidence, not an
automatically usable control installation at another path.

## Restore boundary

Stop web traffic and every worker; close connections and explicitly checkpoint
WAL if applicable before an offline restore. The helper refuses journal/WAL/shm
artifacts and never installs a control-store copy. It creates and verifies a new
target file before replacement. Existing control remains authoritative and
records the advancing generation. Run the existing trusted-host preview and
`advance-restore` ceremony with the exact expected generation and target digest;
never derive operator consent or a new approval from a restored session.

The local test starts with a completed First Look operation and an approved,
unexecuted Geography operation. Replacement is rejected by physical identity
checks. Explicit rebind rotates target identity, advances generation, invalidates
approvals/authentication and disables activation. Completed receipt/history and
writer effects remain historical. Worker discovery/continuation produces no old
executable work. This does not authorize reusing the old approval or writer.

Target commit and control commit during rebind are not atomic across databases.
Interruption can leave a mismatch that must remain blocked for explicit repair.
Do not restore control alongside target as an ordinary procedure. Loss of the
independent control store needs a separately reviewed disaster recovery ceremony.
No protection is claimed against deliberate trusted-administrator restoration of
both stores or metadata-identical unreported in-place restoration.

## Explicit answers

| Question | Answer supported by this rehearsal |
| --- | --- |
| Is SQLite reliable under actual PythonAnywhere processes? | Unknown; no hosted processes tested. Local DELETE/WAL observations passed. |
| Can concurrent writers be serialized? | Yes in local subprocess and coordinator tests; hosted behavior remains unknown. |
| Can worker restart duplicate recognition? | Local tested restart/claim/seal paths prevent automatic duplicate issuance and fence uncertainty; actual hosting remains untested. |
| Can backup integrity be verified? | Yes locally, including schema/content/control checks and rejection of changed data; hosted schedule and artifacts unverified. |
| Can restore avoid resurrecting executable work? | Yes in the tested target-only replacement plus explicit rebind scenario; pending approvals/sessions invalidated and activation disabled. |
| Can restore generation remain independent? | With original control retained, locally yes. Both-store rewind and unreported identical in-place restore are outside the guarantee. |
| Can startup activate recognition? | Tested startup paths do not; real production activation stays unconditionally rejected. Hosted reload still needs observation. |
| Can ordinary HTTP invoke a writer? | No direct raw-writer route; approval uses the guarded fixed coordinator. Current real production attempts are blocked. Disposable capability selection is not exposed over HTTP. |
| Can the application select arbitrary databases? | Ordinary HTTP cannot select a database; runtime requires configured existing absolute target plus administrative identity checks. Trusted deployment administrators can set configuration and are outside the threat model. |
| Are required secrets protected? | Application encryption/session/HTTP protections are tested locally. Actual host ACLs, deployment environment and logs remain unverified. |
| Is PythonAnywhere acceptable? | Not assessed without disposable hosted observations. No migration recommendation is supported. |

## Remaining hosted procedure

An operator must first provide an explicitly disposable account/application and
access method with no production storage or secrets accessible to its principal.
Record the host, plan, Python/SQLite versions, mount/path identities, application
and task model, code inventory (including required untracked files), and test
configuration. Do not install or contact a host until that access is supplied.

Use a separate test checkout/virtualenv, no inherited `.env`, no real users or
email credentials, explicit synthetic target/control/key, HTTPS secure cookies,
capture disabled, and no synthetic provider selection in production routes.
Minimal recognition fixtures are not a fully populated web-demo schema; prepare
any full synthetic web fixture separately and explicitly. Apply no startup DDL.
Follow the isolated WSGI procedure in `recognition-test-deployment.md`.

Run the local command below in the disposable checkout to exercise fresh local
files on that host, then separately exercise actual WSGI and scheduled workers.
The test command alone does not establish real worker/web interoperability.
Record barriers and observations for simultaneous same/different operation,
approval/control writes, readers, web+worker, timeout and both journal modes
where supported. For each writer family test rollback/commit/one-use admission.
Kill/restart the actual processes before claim, after claim, during writer,
after seal commit/before projection and after projection. Require durable fencing
of uncertainty, recovery without writer retry, completed idempotency, stop/stale
blocking, and pending discovery followed by all normal final checks.

Measure persistent target/control and journal permissions/visibility across
reload. List actual writable principals for code, parent directories, both DBs,
journals, backups, keys/configuration and logs; check response/log secret leaks.
Demonstrate no public path can serve private stores. Ordinary requests cannot
choose paths, but the trusted application process necessarily needs intended DB
write permissions; do not claim OS isolation from arbitrary deployed-code access.

Schedule paired verified backups daily only in that disposable environment,
observe success and failure reporting, perform retention with fixed dates, and
restore while control survives. Repeat the explicit generation/rebind and actual
worker restart sequence. Record verified backup IDs, time and sanitized evidence.
Do not submit synthetic digests as hosted `record_deployment_rehearsal` evidence.
No production activation or writer capability may be provisioned even on success.

## Reproduction and results

From the repository root in the reviewed virtualenv, the new local rehearsal is:

```text
python -B -m pytest tests/test_recognition_deployment_rehearsal.py -q -p no:cacheprovider
```

It accepts no database argument. A Windows sandbox run could not access its own
temporary SQLite fixtures; it was rerun with temporary-directory permission.
The initial local harness assertions/time sequencing were corrected; these were
not application failures. Network connects/name resolution and repository
`src/database` SQLite access were denied by the validation launcher's audit hook.
New subprocess probes receive only fresh synthetic temporary paths; existing
startup tests stub dotenv and database access. No external service was contacted.

The final focused Slice F run passed: **8 passed, 6 subtests passed** in 9.97s.
The full suite passed: **1061 passed, 3 skipped, 1049 subtests passed** in
291.49s. It includes deployment/startup, Slices A–E, recognition writers,
concurrency, crash/recovery, authorization and the new backup/restore tests.
The helper was then renamed to avoid the repository's backup-artifact ignore
pattern; the final focused run above verified the new import path. No application
code changed between these runs. `git diff --check` and explicit no-index
whitespace checks for all three new files passed (no-index returns 1 for added
content with no whitespace output). Existing LF→CRLF notices are informational.

No production database accessed; no production recognition executed; no production
award created; no production activation; no production keys created; no external
trust infrastructure created; no production secrets used; no commit/push.

IMPLEMENTATION SLICE F: COMPLETE
PRODUCTION AUTHORIZATION: BLOCKED
PRODUCTION EXECUTION: BLOCKED
PRODUCTION ACTIVATION: BLOCKED
