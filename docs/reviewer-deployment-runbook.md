# Reviewer release deployment runbook

Prepared 2026-09-28. This is an operator procedure, not a record of deployment.
See [Street View investigation](reviewer-streetview-investigation.md) and
[pilot deployment configuration](DEPLOY_LIMITED_PILOT.md) for supporting evidence.

## 1. Pre-deployment

1. Inspect `git status --short`, `git diff --stat`, and the complete diff. Account
   for every modified/untracked file; do not discard unrelated work. This review
   was against an uncommitted tree based on
   `fa82b74218c03c28bad6dd254daf1bb0c4803856`, not a deployable release SHA.
   Record `git rev-parse HEAD` for the approved release and the previous release.
2. Quiesce submissions before backup/migration. Set `DMV_BUS_STOPS_DB` in both the
   migration shell and production service to the intended persistent, absolute
   database path. Verify the file exists; never let SQLite create an empty DB at
   a mistyped path. Confirm API and assignment router resolve the same path.
3. Back up that database with the existing online-backup utility (POSIX shell;
   variables below must be set to operator-owned locations):

   ```bash
   python scripts/active/backup_database.py --source "$DMV_BUS_STOPS_DB" --output "$BACKUP_DB" --manifest "$BACKUP_MANIFEST"
   ```

   Keep backup and manifest in access-controlled storage separate from the live
   DB. Verify the manifest/hash, integrity result, and FK check. Record reviewer,
   observation and assignment counts and representative history before migration.
4. Record the active-stop count from the selected DB using exactly:

   ```sql
   SELECT COUNT(*) FROM stop_gtfs_status WHERE stop_gtfs_status.current_gtfs = 1;
   ```

   The local reference was 7,117; investigate differences rather than forcing a
   production database to match that snapshot.

## 2. Migration

Run the reviewed migration explicitly before serving the new code:

```bash
DMV_BUS_STOPS_DB=<deployment db> python scripts/active/create_review_tables.py
```

`<deployment db>` is a placeholder: replace it with the quoted intended absolute
path. If the variable is already exported, use
`DMV_BUS_STOPS_DB="$DMV_BUS_STOPS_DB" python scripts/active/create_review_tables.py`.
PowerShell equivalent: set `$env:DMV_BUS_STOPS_DB` to the intended path, then run
`python scripts/active/create_review_tables.py`.

On that same database verify:

```sql
PRAGMA integrity_check;
PRAGMA foreign_key_check;
PRAGMA table_info(observation_attachments);
PRAGMA index_list(observation_attachments);
PRAGMA index_info(observation_attachments_observation);
PRAGMA foreign_key_list(observation_attachments);
```

Expect integrity `ok`, no FK violations, columns `id`, `observation_id`,
`attachment_type`, `external_url`, `storage_key`, `provider`, `created_at`, and
index `observation_attachments_observation` on `observation_id`. The FK must
reference `stop_observations(id)`. Compare historical counts and open existing
reviews with and without attachments; pre-migration history must remain readable.

Foreign-key enforcement is connection-specific. The migration connection and
application observation/attachment write connection execute
`PRAGMA foreign_keys=ON` before beginning a transaction. Verify this on the actual
write connection (`PRAGMA foreign_keys` must return `1`) in a staging smoke run
or debugger, and run the review workflow tests against the release. Checking a
separate SQLite shell connection does not prove application enforcement. This is
not a claim that every legacy read/derived connection enables FKs. Normal review
requests must never create the attachment schema.

## 3. Application deployment and restart

Follow the configured host mechanism in [DEPLOY_LIMITED_PILOT.md](DEPLOY_LIMITED_PILOT.md):

- PythonAnywhere: install `requirements-pilot.txt` in the selected environment;
  configure the WSGI environment before importing
  `from src.api.app import app as application`; reload using the web-app control.
- Supervised Waitress host: stop inbound traffic and the supervised process,
  install the approved release/runtime requirements, migrate, then start
  `python scripts/active/serve_pilot.py` through the existing supervisor. It uses
  four threads in one process. No specific systemd unit is supplied by this repo.

Preserve persistent secret, HTTPS/secure-cookie settings, DB path, support contact,
and configured email provider. Never run the development Flask server as the
production service. Do not run a database reset or physical-stop cutover.

## 4. Post-deployment smoke tests

Use a designated reviewer and intentional, accurate test contributions. Record
their IDs; do not delete or overwrite submitted evidence afterward.

1. Dashboard loads.
2. Map popup opens; normal, hover and keyboard-focus buttons remain readable.
3. Reviewer profile loads, including exposure coverage and history.
4. An active stop can be assigned for review.
5. Submit an accurate review without a photo.
6. Submit another accurate review with a safe HTTPS test photo URL (no credentials).
7. Retry the same assignment; receive success with the same observation ID, one
   observation and unchanged attachment even if the retry supplies another URL.
   Exercise failed-refresh recovery in staging, without injecting a production failure.
8. History displays the attachment and older reviews without photos still work.
9. An inactive stop cannot enter a new active assignment/submission workflow.
10. Single/multiple/no-direction pages render correctly (reference IDs 7755,
    406 and 407; confirm their current data before asserting labels).
11. Open in Google Maps uses the actual stop coordinate; check 7755, 837 and 2231.
12. Try Street View is optional and warns that imagery may be unavailable. If Google
    returns no imagery, the review tab remains usable with in-person/other visual
    evidence. Maps remains available. Do not infer absent amenities from no imagery.
13. Dashboard and review pages have no page-level horizontal overflow at mobile
    widths; check action ordering and real-device keyboard behavior.

Record release SHA, migration output, DB identity, browser/device, smoke results,
and operator. Reopen traffic only after required checks pass.

## 5. Rollback

Stop inbound traffic and the application first. Preserve the failed database and
logs; record any contributions made since backup. Assess/reconcile those records
before restoring, since backup restoration would otherwise lose them.

Restore the previous approved code release and its pinned runtime/environment.
If a DB restore is needed, verify the backup SHA against its manifest and run
integrity/FK checks on a copy. Copy the verified backup to a new explicit persistent
path, point both service and migration environment at that path, and use only the
schema migration compatible with the restored release. Do not overwrite the only
backup or use the obsolete pre-cutover database. Restart through the same host
mechanism, verify history/active counts and smoke tests, then reopen traffic.
