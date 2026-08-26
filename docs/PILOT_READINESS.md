# Small-pilot readiness audit

This audit targets a supervised 3–5 person volunteer pilot. It does not approve
a public production launch or change data, scoring, evidence, review routing, or
physical-stop identity.

## Configuration inventory

| Setting | Classification | Default and failure behavior |
|---|---|---|
| `FLASK_SECRET_KEY` | required in all served environments | No fallback. Non-test requests return 503 until configured. |
| `DMV_BUS_STOPS_DB` | optional locally; required explicitly in production/operations | Defaults to repository `src/database/dmv_bus_stops.db`. |
| `SESSION_COOKIE_SECURE` | required production choice | Defaults `0`; set `1` only with HTTPS. Cookies are HttpOnly, SameSite=Lax, with a 30-day permanent-session lifetime. |
| `REVIEWER_EMAIL_BACKEND` | required for production email login | Must equal `smtp`; otherwise email login reports unavailable while anonymous review remains available. |
| `REVIEWER_EMAIL_FROM`, `SMTP_HOST`, `SMTP_PORT` | required when SMTP is enabled | Missing/invalid values fail closed with a generic 503 login response. |
| `SMTP_USE_TLS` | optional SMTP setting | Defaults `1` for STARTTLS; only `0` or `1` accepted. No silent downgrade. |
| `SMTP_USERNAME`, `SMTP_PASSWORD` | optional paired SMTP credentials | Either both or neither; an incomplete pair is rejected. |
| `REVIEWER_AUTH_DEV_MODE` | local-development only | Defaults off. `1` captures magic links in responses/outbox and must never be production configuration. |
| `DATABASE_URL` | inactive/legacy configuration | Defaults to local PostgreSQL URL but the active Flask/SQLite path does not consume it. |
| `GOOGLE_STREETVIEW_API_KEY`, `WMATA_API_KEY` | optional ingestion/legacy configuration | No active Flask route requires either value. |
| `LOG_LEVEL` | optional/legacy | Defaults `INFO`; active Flask logging is not centrally configured from it. |

The repository already depends on `python-dotenv`. `src.api.app` now loads the
repository-root `.env` before importing assignment/database consumers. Production
still fails without an explicit secret; `.env` provides no insecure fallback.

For Resend, use its dashboard-provided SMTP host, port, username, password, and a
verified sender/domain. Map them to the provider-neutral SMTP variables in
`.env.example`; do not guess or commit provider credentials.

## HTTPS, proxy, and server deployment

- Local HTTP: `SESSION_COOKIE_SECURE=0`.
- Production HTTPS: `SESSION_COOKIE_SECURE=1`.
- `HttpOnly=True`, `SameSite=Lax`, permanent session lifetime 30 days.
- Login rate limiting uses `request.remote_addr`; arbitrary
  `X-Forwarded-For` is intentionally ignored.
- No nginx, Caddy, Apache, ProxyFix, gunicorn, waitress, or other production WSGI
  configuration is currently committed.
- If a trusted proxy is introduced, trusted address translation must be configured
  at the WSGI/proxy boundary, with an explicit trusted-hop count.
- `python -m src.api.app` is Flask's local development server only.

A production WSGI server and HTTPS termination are deployment blockers, not choices
made by this housekeeping branch. For the current Windows environment, Waitress is
the simplest Windows-native candidate; a Linux deployment could instead use
Gunicorn. Select and test one rather than committing both speculative paths.

## Database safety

The Flask app, assignment router, and active review-table migration honor
`DMV_BUS_STOPS_DB`. Many other scripts in `scripts/active` still hard-code the
repository database or accept a positional `--db`/database argument. Never assume
the environment override applies to an operational script without checking it.

Standard PowerShell production operation pattern:

```powershell
$env:DMV_BUS_STOPS_DB = 'C:\absolute\path\dmv_bus_stops.db'
Get-FileHash -Algorithm SHA256 -LiteralPath $env:DMV_BUS_STOPS_DB
Copy-Item -LiteralPath $env:DMV_BUS_STOPS_DB -Destination '<dated-backup-path>'
# Run one reviewed migration/rebuild command.
Get-FileHash -Algorithm SHA256 -LiteralPath $env:DMV_BUS_STOPS_DB
Remove-Item Env:DMV_BUS_STOPS_DB
```

First validate every mutation against a temporary copy. A hash proves byte-level
change/no-change; it does not replace row-count and invariant checks.

## Repository and filesystem classification

| Area | Class | Contract |
|---|---|---|
| `src/` | A — active/supported | Application, domain producers, schema, and diagnostic modules. |
| `src/processing/heading_audit.py` | B — active diagnostic | Tested circular-heading/chaining helpers; never a display filter. |
| `scripts/active/` | A/F — supported intent, mixed readiness | Maintainer-command namespace; individual DB targeting remains inconsistent. |
| `scripts/archive/` | C — archived/historical | Not supported execution; malformed historical patches need not compile. |
| `tests/` | A — active/supported | Full regression suite. |
| `docs/` | A — active/supported | Audience-specific guidance and technical handoff. |
| `src/database/dmv_bus_stops.db` | D — local/deployment data | Ignored by pattern but may exist locally; not changed by this audit. |
| `src/database/backups/`, other `*.db` copies | D — generated/local only | Keep outside commits; retain/delete under an explicit backup policy. |
| `.worktrees/`, `.venv/`, `.env`, caches, `*.pyc` | D — local only | Ignored. |
| root CSV/JSON/HTML reports and raw downloads | D/F | Ignored generated evidence; provenance/retention owner needs review. |
| root `archive/`, `clients/`, `pipeline/`, `review/`, `workflows/` | F — ambiguous | Do not delete without consumer/history audit. |

No repository data/backups tracking policy was changed. Existing broad `*.db` ignore
rules remain; tracked files would remain tracked despite ignore rules.

## `scripts/active` audit

`scripts/active` should contain commands a maintainer may legitimately run today.
Compilation succeeds, but presence here does not yet imply production-safe defaults.

| Script | Purpose/status | DB behavior | Mutation/safety |
|---|---|---|---|
| `build_gtfs_stop_map.py` | current GTFS mapping producer | hard-coded repo DB | destructive rebuild; copy/preflight required |
| `build_gtfs_stop_status.py` | canonical active-stop producer | hard-coded repo DB | destructive derived rebuild; tested indirectly |
| `build_stop_profile_page.py` | legacy static-page builder | no DB override | generated output; likely superseded by Flask page |
| `build_stop_transit_evidence.py` | compatibility transit evidence | hard-coded repo DB | delete/insert rebuild |
| `create_evidence_schema.py` | historical schema bootstrap | hard-coded repo DB | schema mutation; review before use |
| `create_review_tables.py` | supported deployment migration | honors override | idempotent schema migration; covered by tests |
| `create_stop_observations_table.py` | earlier schema bootstrap | hard-coded repo DB | superseded in part by review migration |
| `download_census_boundaries.py` | source downloader | files/network | current only for intentional source refresh |
| `download_dc_boundaries.py` | source downloader | files/network | current only for intentional source refresh |
| `download_dcgis_stops.py` | source downloader | files/network | source refresh; provenance review required |
| `download_wmata_stops.py` | source downloader | files/network | source refresh; no production DB write |
| `generate_seating_improvement_opportunities.py` | canonical seating derived producer | positional DB | destructive derived rebuild; tested |
| `import_centerlines.py` | centerline importer | hard-coded repo DB | mutating; older one-shot path |
| `import_centerlines_paginated.py` | paginated centerline importer | hard-coded repo DB | mutating; likely preferred over prior script |
| `import_prince_georges_centerlines.py` | PG centerline importer | hard-coded repo DB | mutating jurisdiction path |
| `import_wmata_evidence.py` | historical WMATA evidence import | hard-coded repo DB | unbounded nearest-neighbor evidence; not safe for routine rerun |
| `import_wmata_transit_evidence.py` | compatibility wrapper/import | inspect explicit inputs | not a normal pilot operation |
| `preflight_amenity_review_priority.py` | read-only derived-table validation | positional DB | supported preflight; direct/module tested |
| `rebuild_active_wmata_view.py` | legacy WMATA view | hard-coded repo DB | status semantics unresolved; do not use for pilot |
| `rebuild_amenity_review_priority.py` | canonical status/priority rebuild | positional/default DB | supported with explicit DB; tested |
| `rebuild_stop_amenity_status.py` | canonical amenity synthesis | `--db` supported | supported with explicit DB; tested |
| `rebuild_stop_routes_clean.py` | route repair/rebuild | hard-coded repo DB | destructive specialized maintenance |
| `rebuild_stop_transit_evidence.py` | compatibility updater | hard-coded repo DB | specialized mutation |
| `rebuild_transit_evidence.py` | compatibility rebuild | hard-coded repo DB | delete/insert; overlaps prior producer |
| `validate_geography.py` | geography diagnostic | hard-coded repo DB | read-only but target unsafe by default |
| `validate_route_integrity.py` | route diagnostic | hard-coded repo DB | read-only but target unsafe by default |

Recommended follow-up: move clearly superseded scripts only after consumer/history
review, and make every retained mutating command require an explicit database target.
No scripts were moved in this branch.

## Secrets and private data

A tracked-file pattern scan found configuration names and placeholders in code/docs,
but no tracked private key, credential assignment, bearer token, reviewer-email dump,
or real SMTP secret. The local `.env` is ignored and was not inspected or printed.
If a credential has ever been committed outside these patterns, rotate it rather than
assuming deletion from the working tree removes Git history.

## Public route and link audit

| Source/link | Destination/type | Result |
|---|---|---|
| `/`, `/dashboard` | dashboard HTML | correct |
| map “View stop details” | `/stop/<id>` HTML | correct; does not expose `/stops/<id>` JSON |
| map/direct review | `/review/<id>?mode=map|direct` HTML | correct |
| primary opportunity | `/review/start?mode=opportunity` redirect | correct; creates assignment only during actual use |
| Choose My Routes | `/review/routes` HTML | correct |
| My Routes | `/review/start?mode=route` redirect | correct |
| Near Me | client coordinates to nearby review start | correct; browser permission required |
| reviewer profile/sign-in | `/reviewer/profile`, `/reviewer/sign-in` HTML | correct |
| sign-out | POST `/reviewer/sign-out` JSON | correct, CSRF protected |
| post-submission stop link | `/stop/<id>` HTML | correct |
| handbooks | `/handbook`, `/volunteer-handbook` HTML | correct |
| Street View/WMATA tools | external links | generated from stop context; open in new tab |
| `/stops/<id>` | JSON API | intentionally used only by JS data loading |

The unused `/survey/<id>` call exists only in legacy `survey.html`/`survey.js`; the
active review page uses `review_survey.js`. Keep it classified as stale until the
template’s history is reviewed.

## Error and empty states

Existing tests cover missing secret, unavailable/failing email, rate limiting,
expired/invalid assignments, unknown campaigns, inactive stops, incomplete schema,
anonymous profile access, conflicting/unknown evidence, and missing heading. APIs
appropriately return JSON. Authentication error endpoints also return JSON when
visited directly; a polished browser error page for expired magic links is a pilot
caution, not a data-safety blocker.

No normal UI link points to a raw JSON stop endpoint. The legacy community-action
endpoint appears inconsistent with the current observation schema and has no current
UI caller; do not expose it during the pilot pending retirement/repair review.

## Language, privacy, feedback, and observability

Technical terms such as `campaign`, `workflow_state`, and review-mode codes remain
internal or in technical documentation. Public text uses “Review a seating
opportunity,” preliminary visual clearance, route-based rider exposure, and cautious
canonical-status language. No stale public “bench feasible” or WMATA amenity-authority
claim was found.

The handbook and current sign-in/profile/review UI explain anonymous review, optional
private email, public display-name intent, dated observations, imagery provenance, no
photo uploads, and stewardship without ownership. This is adequate as a concise pilot
notice; link the handbook during onboarding rather than drafting a legal policy here.

`review_feedback` and `community_requests` tables exist but have no coherent current
general-feedback route/UI. The legacy community-action path is not a substitute.
Before inviting volunteers, designate a monitored email or issue-form URL and add one
link after an owner is chosen. No admin/feedback system was built.

Existing database data can measure assignments created/completed, scenario, campaign,
observations, reviewers, verified-email claims, repeat reviewers, distinct reviewed
stops, consensus progress, and submitted field completion. It cannot measure page
views before assignment, page/form abandonment, or client-side errors. For 3–5 users,
manual onboarding plus database queries and a monitored feedback channel are adequate;
third-party analytics are unnecessary.

## Reviewer-auth deployment order

1. Choose Resend SMTP and verify its sender/domain externally.
2. Generate/configure a strong persistent `FLASK_SECRET_KEY`.
3. Configure an absolute `DMV_BUS_STOPS_DB`.
4. Configure provider SMTP values; ensure `REVIEWER_AUTH_DEV_MODE` is absent/off.
5. Deploy behind HTTPS with `SESSION_COOKIE_SECURE=1`.
6. Hash and back up the database.
7. Run `python scripts/active/create_review_tables.py` with the explicit DB override.
8. Validate schema and restart the selected production WSGI service.
9. Smoke-test anonymous review without creating unintended production test history.
10. Perform one designated email sign-in smoke test.
11. Verify recovery from a second browser/device and sign-out behavior.
12. Confirm email privacy, public display name, and pilot feedback instructions.

## Pilot-blocker matrix

| Item | Supervised 3–5 | Broader/remote | Required action | Owner/type |
|---|---:|---:|---|---|
| Resend/email login | No if anonymous | Only if email login is advertised | verify sender and configure SMTP | deployment |
| Anonymous review | Ready | Ready | smoke test | deployment |
| Profile recovery | No | Conditional | SMTP plus second-device test | deployment |
| Production WSGI server | No for local supervision | Blocker | select/test server | deployment |
| HTTPS termination | No for local supervision | Blocker | configure/test HTTPS | deployment |
| Persistent `FLASK_SECRET_KEY` | Required locally and remotely | Blocker | configure persistent secret | deployment |
| Explicit `DMV_BUS_STOPS_DB` | Recommended for a local copy | Blocker | configure absolute deployment path | deployment |
| `SESSION_COOKIE_SECURE=1` | No over local HTTP | Blocker | enable after HTTPS is active | deployment |
| DB backup/migration | Required before using production | Blocker | backup/hash/migrate/verify | data/deployment |
| Link integrity | Ready | Ready after deployed smoke test | smoke test deployed base URL | code/deployment |
| Language consistency | Ready | Ready | onboarding review | documentation |
| Privacy notice | Ready | Ready | include handbook in onboarding | documentation |
| Feedback mechanism | Operational requirement | Operational requirement | choose monitored contact and link it | operations/docs |
| Error handling | Caution | Caution | supervised rollout; improve later | code/deferred |
| Serving direction | Ready | Ready | explain occasional multiple headings | documentation |
| Physical-stop identity migration | Not a blocker | Not a deployment blocker | defer repair; flag examples | data/deferred |
| Local evidence gaps | Not a blocker | Not a blocker | communicate uncertainty | data |
| Observation sparsity | Not a blocker | Not a blocker | pilot purpose is collection | data |
| Admin layer | Not a blocker | Not a pilot prerequisite | manual triage for small pilot | deferred |
| Photo uploads | Not a blocker | Not a pilot prerequisite | no action | deferred |
| Steward notifications | Not a blocker | Not a pilot prerequisite | set expectations | deferred |
| Geographic continuity | Not a blocker | Not a deployment blocker | choose bounded pilot area/tasks | operations |
| Pilot observability | Ready | Ready | prepare read-only queries | operations |

Physical-stop identity is a **pilot caution**, not a blocker: display provenance is
safe, contradictions remain visible, and the pilot is evidence collection rather
than identity migration. Avoid presenting a contradictory stop as a single known curb.

The admin layer is post-pilot. Account merge/recovery exceptions, moderation,
conflict/source inspection, feedback triage, stewardship, and assignment management
can be handled manually for 3–5 supervised volunteers. Evidence deletion/moderation
and account merging require designed audit trails before automation.

## Remaining invitation checklist

Before inviting volunteers:

1. Select production WSGI hosting and HTTPS termination.
2. Configure persistent secret, absolute DB path, and secure cookies.
3. Back up/hash, run the review migration, and verify production schema.
4. Configure/test Resend if email sign-in will be advertised.
5. Choose and publish a monitored feedback contact.
6. Run anonymous, opportunity, route, nearby, stop-detail, submission, profile, and
   second-device smoke tests on the deployed URL.
7. Choose a bounded pilot geography/task set and brief volunteers on uncertainty and
   occasional contradictory serving directions.

Post-pilot backlog: physical-stop lineage/splitting, active-script DB-target cleanup,
retiring legacy routes/templates, browser-friendly auth error pages, feedback triage,
minimal client-error/abandonment observability if justified, and admin workflows based
on actual pilot needs.
