# Deploying the limited volunteer pilot

This is the supported operational path for the current small pilot. The Flask
development server is local-only. Production uses Waitress behind an operator-managed
HTTPS terminator. The repository does not provide DNS, certificates, firewall rules,
machine provisioning, process supervision, SMTP credentials, or a support mailbox.

## External prerequisites

The operator must supply:

- a Windows or compatible Python host with persistent storage;
- HTTPS termination and a hostname/certificate;
- a process supervisor or service account with restart-on-failure behavior;
- an absolute path to the authoritative post-V2 SQLite database;
- a generated persistent secret stored outside Git;
- a monitored support email address or URL;
- SMTP credentials and a verified sender only if email login is advertised.

Do not expose Waitress directly to the public internet. Its default pilot bind is
`127.0.0.1:8080`; route HTTPS traffic to that listener through the selected trusted
terminator. The application intentionally does not trust forwarded client-IP headers.

## Environment

Create a deployment-owned environment file or service environment outside the
repository. `.env.example` documents names but contains placeholders only.

Required:

```text
FLASK_SECRET_KEY=<persistent random value, at least 32 characters>
DMV_BUS_STOPS_DB=C:\absolute\persistent\path\dmv_bus_stops.db
SESSION_COOKIE_SECURE=1
PILOT_SUPPORT_CONTACT=<monitored email address or support URL>
PILOT_BIND_HOST=127.0.0.1
PILOT_BIND_PORT=8080
LOG_LEVEL=INFO
```

Generate the secret outside Git:

```powershell
python -c "import secrets; print(secrets.token_hex(32))"
```

Keep `REVIEWER_AUTH_DEV_MODE` unset. Anonymous review works without SMTP. If email
login is offered, additionally supply the complete `REVIEWER_EMAIL_BACKEND=smtp`,
sender, host, port, TLS choice, and paired username/password documented in
`.env.example`. Partial or invalid SMTP configuration prevents pilot startup.

## Install, migrate, and start

From a reviewed release checkout and activated virtual environment:

```powershell
python -m pip install -r requirements.txt
python scripts/active/create_review_tables.py
python -m scripts.active.serve_pilot
```

The runner fails before binding if the secret is weak/placeholder, database path is
relative or missing, secure cookies are disabled, development auth is enabled, the
support contact is missing, SMTP is partial, or API/assignment database paths differ.
It uses four Waitress threads. SQLite remains the durability boundary; keep this as
one application process for the limited pilot.

For restart: stop inbound traffic, stop the supervised Waitress process cleanly,
verify the configured database path, deploy/install the reviewed release, run only
the reviewed idempotent schema migration, start the same command through the process
supervisor, and perform the smoke checks below. Do not run the V2 cutover or reset.

## Backup and restore

Create an online, verified backup before deployment and before every schema migration:

```powershell
python scripts/active/backup_database.py `
  --source $env:DMV_BUS_STOPS_DB `
  --output C:\secure-backups\dmv_bus_stops-YYYYMMDD-HHMMSS.db `
  --manifest C:\secure-backups\dmv_bus_stops-YYYYMMDD-HHMMSS.json
```

Store the database and manifest on access-controlled storage separate from the live
database. The command refuses overwrite and verifies integrity, foreign keys, active
stops, reviewers, and observations. SQLite online-backup output can have a different
file hash from the source while representing the same committed database state.

Restore procedure:

1. Stop inbound traffic and the application process.
2. Preserve the failed/current database and logs for diagnosis.
3. Verify the chosen backup against its manifest SHA, then run `PRAGMA integrity_check`
   and `PRAGMA foreign_key_check` on a copy.
4. Copy the verified backup to a new explicit live path; do not overwrite the only
   copy and never restore the pre-V2 baseline.
5. Set `DMV_BUS_STOPS_DB` to the restored absolute path, run the idempotent review
   schema migration, start Waitress, and complete the smoke test.

## Logging

The runner emits timestamped application events to stdout/stderr for the process
supervisor to retain and rotate. It records startup, completed review IDs, and failed
review/auth request method, path, and status. It never logs request bodies, notes,
email addresses, cookies, raw magic tokens, or URL query strings. Ordinary Waitress
access logging is suppressed because magic links carry tokens in query strings.

## Deployment smoke test

Use a designated pilot reviewer and record any created production review as an
intentional smoke contribution. Never delete it afterward.

1. Open `/dashboard`; confirm the map and monitored support contact render.
2. Start `/review/start?mode=opportunity`; confirm a current stop and assignment.
3. Load review context and submit one realistic observation.
4. Open the resulting `/stop/<id>` profile and confirm the observation/status update.
5. Restart the supervised process and confirm the same reviewer session/profile,
   completed review, and next assignment remain available.
6. Open `/stops/935` and `/stop/935`; confirm retired status and links to both 7755
   and 7756, with no silent redirect.
7. Confirm `/review/7755/info` reports 119° Southeast and `/review/7756/info` reports
   297° Northwest.
8. Continue through the next opportunity and a saved-route review.
9. If email login is advertised, request and consume one real link, confirm reuse
   fails, then check `/api/reviewer/email-auth-health` contains no credentials.
10. Check retained logs for startup/review events and verify they contain no email,
    notes, cookie, token, or query-string values.
11. Recompute the live database SHA, run integrity/FK checks, and retain the result
    with the deployment record.
