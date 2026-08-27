# DMV Bus Stop Intelligence — Technical Handoff

This document is the implementation-oriented reference for the current system.
When prose conflicts with code, inspect the named producer and its tests before
changing data. The SQLite schema has evolved incrementally. `schema.sql` describes
an important baseline but is not a complete production bootstrap; several evolved
observation fields and tables are created by separate producers or migrations.
Active migrations upgrade existing databases.

## 1. Runtime and safety

The Flask application is `src/api/app.py`. Its default database is
`src/database/dmv_bus_stops.db`, resolved from the repository root. Set
`DMV_BUS_STOPS_DB` to an explicit path when using a linked worktree, test copy,
or deployment database. `src/review/assignment_router.py` uses the same override,
so API and assignment operations cannot diverge when it is set.

Operational rules:

1. Never test a rebuild or migration first against production.
2. Record a SHA-256 hash and make a recoverable backup.
3. Run against a temporary copy and validate row-count/identity invariants.
4. Apply only the required migration/rebuild to production.
5. Recompute the production hash and validate again.

Physical Stop V2 was applied to production with
`scripts/active/migrate_physical_stops_v2.py`; its persistent lifecycle and lineage
state are authoritative. The migration orchestrator remains useful for provenance
and idempotency checks, but it is not a routine maintenance command.

The nested contribution reset existed only inside the first pre-volunteer cutover.
The standalone reset now refuses any database where V2 cutover state exists. After
cutover, all reviewer and contribution records are durable. Recovery must stop
application access, restore the newest independently hashed backup that includes
durable contributions, verify its SHA, SQLite integrity, and foreign keys, and then
replay only reviewed, contribution-preserving migrations. Never restore the pre-V2
baseline or use the disposable reset as normal recovery.

Some older producers still accept their database as a positional argument or
Python parameter instead of reading `DMV_BUS_STOPS_DB`. Check each entry point;
do not assume the override is universal outside the application, assignment
router, and active review-table migration.

## 2. Canonical identity and active stops

`bus_stops` contains source/GTFS stop records. `physical_stops` is the canonical
place identity, with `physical_stop_members` connecting source records to it.
Public review, amenity, and opportunity logic uses `physical_stop_id`.

Physical Stop Identity V2 makes that identity persistent. Routine refreshes produce
a reconciliation plan and preserve IDs; the old connected-component builder is
bootstrap-only. Lifecycle tables retain retired identities and successor lineage.
Geography is recomputed from coordinates, while evidence attribution is versioned
separately from raw claims. The applied automatic proposal is reproducible through
`scripts/diagnostics/generate_physical_stop_v2_manifest.py`; its reviewed cardinality
gate is 384 parents and 791 child groups. Proposal generation is read-only and is not
permission to alter authoritative production identities. The explicit-database
orchestrator and compatibility rebuild contracts are covered by the cutover tests.

Versioned facility context is preserved separately in `gtfs_feed_snapshots` and
`gtfs_stop_structure`. Import an explicit ZIP against a database copy with
`python scripts/active/import_gtfs_stop_structure.py <feed.zip> --feed-id
wmata-bus --db <copy>`. A shared `parent_station` means shared facility, not the
same boarding point; platform identity, snapshot, coordinates, and provenance
must be evaluated together before a future physical-stop migration.
The frozen diagnostic disposition and exact-versus-fallback precedence are in
`docs/physical-stop-identity-v2.md`.

An active stop means exactly:

```sql
stop_gtfs_status.current_gtfs = 1
```

`stop_gtfs_status` is produced by `scripts/active/build_gtfs_stop_status.py`.
Non-current physical stops can remain for history but must not enter current
amenity synthesis, review priority, seating opportunity, or assignment pools.

## 3. Evidence layers and authority

Keep three layers distinct:

1. **Evidence** is a source-specific record or dated observation.
2. **Canonical synthesis** summarizes the usable evidence without erasing its
   provenance or disagreement.
3. **Community consensus** is a derived result from multiple community reviews;
   it is neither an imported record nor a manual truth flag.

### Local-jurisdiction evidence

`stop_amenity_evidence` stores source-centric amenity records with stable source
identity and match provenance. The current database contains supported local
evidence for:

- District of Columbia (`DDOT_ARCGIS` clean replacement path)
- Montgomery County (`MONTGOMERY_COUNTY_WMATA`; public wording is “Montgomery
  County inventory,” not WMATA amenity authority)
- Prince George's County TheBus (currently shelter/trash fields)
- City of Alexandria (including shelter/bench and other infrastructure fields)
- Arlington County (currently accessibility pad/path fields, not shelter/bench)
- City of Falls Church
- Fairfax County (currently shelter evidence)

Coverage and supported fields vary. An importer’s existence does not imply full
jurisdiction or amenity coverage. `source='DDOT'` is quarantined legacy evidence and is
explicitly excluded from canonical synthesis. Clean `DDOT_ARCGIS` evidence is a
different source.

WMATA remains useful for service, stops, and route association, but its historical
shelter/bench inventory fields are not authoritative current-condition evidence.

### OSM evidence

`stop_osm_evidence` is usable for canonical shelter/bench synthesis only when an
explicit `yes` or `no` tag is present and an OSM `ref`/`ref:wmata` matches a full
external stop ID belonging to the physical stop. Proximity-only, missing, bare
zero, and suffix matches fail closed.

### Community observations and consensus

`stop_observations` is append-only review evidence. Only rows with
`source='community_review'` feed `src/review/consensus.py` and canonical amenity
synthesis. Unknown/blank values do not count as votes.

`stop_consensus` is recalculated from observation history. For shelter/bench to
be authoritative in amenity synthesis, there must be at least three community
observations, confidence at least `0.75`, and a usable boolean consensus value.
Pre-consensus community observations still contribute likely/conflicting evidence.

## 4. Canonical amenity status

Producer: `src/amenities/status_synthesis.py`

Table: `stop_amenity_status`

The rebuild produces exactly two rows—`shelter` and `bench`—for every active
physical stop. Identity is unique on `(physical_stop_id, amenity_type)`.

Statuses are:

- `confirmed_yes`: full community consensus confirms presence
- `confirmed_no`: full community consensus confirms absence
- `likely_yes`: usable non-consensus evidence indicates presence only
- `likely_no`: usable non-consensus evidence indicates absence only
- `conflicting`: usable positive and negative non-consensus evidence coexist
- `unknown`: no usable semantic evidence

Full consensus determines the confirmed status. Conflicts with other evidence
remain visible in `consensus_conflicts_with_other_evidence`; they are not deleted.
Counts, source lists, OSM flags, community counts, rationale, and timestamp make
the synthesis auditable.

Rebuild commands:

```bash
python scripts/active/rebuild_stop_amenity_status.py --db <database>
python scripts/active/rebuild_amenity_review_priority.py <database>
```

The second command rebuilds canonical status and then amenity review priority.

## 5. Amenity verification priority

Producer: `src/amenities/review_priority.py`

Table: `stop_amenity_review_priority`

This table prioritizes evidence collection for each active stop/amenity pair; it
is not an amenity truth source. Current workflow states are:

- `consensus_reached`
- `conflicting`
- `one_observation_short`
- `likely_without_consensus`
- `unknown_with_evidence`
- `no_evidence`

The score combines fixed conflict/consensus-progress components with one-tenth
of `rider_exposure_percentile` for unresolved rows. This review-priority score is
separate from the seating-opportunity score described below.

## 6. Rider exposure

Current producer flow:

```text
ridership_snapshots
  -> opportunity_assessments.combined_route_weekday_boardings
  -> opportunity_assessments.rider_exposure_percentile
  -> amenity review priority and seating opportunities
```

`src/assessment/create_opportunity_assessments.py` finds distinct routes serving
each active physical stop. For the globally latest `ridership_snapshots.period`,
it takes `MAX(weekday_boardings)` per route, sums those route values into
`combined_route_weekday_boardings`, and also stores the highest route value.
This deduplicates repeated snapshot rows and repeated route membership.

`src/scoring/rider_exposure.py` computes an empirical, CUME_DIST-style percentile
over the active opportunity-assessment population:

```text
100 * count(exposure values <= this value) / active population size
```

Values are normalized to numeric zero when missing; ties receive the same
percentile. The percentile is persisted both in the
`opportunity_assessments.rider_exposure_percentile` column and in
`assessment_json`, then copied to current derived consumers.

This is route-based exposure: the sum of latest-period weekday boardings for
routes serving the stop. It is **not** observed boarding activity at that physical
stop. `route_exposure_score` in `stop_priority_snapshots.factors` is retained
legacy scoring context and must not be presented as a percentile or substituted
for the canonical rider percentile.

## 7. Broad seating-improvement opportunities

Producer: `src/assessment/generate_seating_improvement_opportunities.py`

Wrapper:

```bash
python scripts/active/generate_seating_improvement_opportunities.py <database>
```

Table: `seating_improvement_opportunities`

There is one row per active stop. Membership has no minimum score and is not
gated by bench or shelter presence. Presence, adequacy, preliminary clearance,
and rider benefit remain separate.

### Adequacy

`limitation_observed` wins when any observation reports a seating limitation,
fair/poor comfort, possible/blocked accessibility, partial/exposed weather, or
riders avoiding facilities. `no_limitation_observed` requires affirmative
observed seating plus explicit `bench_condition='none'`, good comfort, good
accessibility, and no adverse weather/avoidance signal. Otherwise adequacy is
`unknown`.

### Preliminary clearance

`bench_feasible` observations aggregate as:

- any `no` -> `observed_constrained`
- otherwise any `yes` -> `observed_clear`
- otherwise -> `unknown`

These are visual observations only—not engineering feasibility, ADA compliance,
ownership/right-of-way authority, permitting, utility clearance, or construction
readiness.

### Workflow

- unknown/conflicting bench status -> `verify_presence`
- present plus affirmative no-limitation evidence -> `no_current_action`
- observed constraint -> `constrained_or_special_review`
- limitation or bench absence with observed clear space -> `planning_review`
- limitation or absence without observed clear space ->
  `collect_clearance_observation`
- otherwise -> `assess_adequacy`

### Provisional ranking

`documented_need_index` is the maximum applicable signal, never a sum:

| Signal | Value |
|---|---:|
| observed seating limitation | 90 |
| poor comfort | 75 |
| confirmed bench absence | 55 |
| likely bench absence | 45 |
| fair comfort | 40 |
| shelter absence context | 20 |
| otherwise | 0 |

```text
priority_score = documented_need_index * 0.60
               + rider_exposure_percentile * 0.40
```

Rider exposure appears once. There is no uncertainty bonus, workflow/readiness
component, `review_priority_score`, or legacy opportunity score in this formula.
Rows rank by score descending, rider percentile descending, then physical stop
ID. The model is provisional and calibratable; it ranks investigation, not the
objective worth of a stop or construction feasibility.

## 8. Narrow bench candidates and generic recommendations

`bench_installation_candidates` remains the authoritative narrow derived
representation for physical bench-installation candidacy. It is a separate,
evidence-qualified planning funnel and is not the main seating-opportunity
universe. Generic `improvement_recommendations` no longer independently creates
`bench_installation_candidate`; generic presence/verification recommendations
remain for compatibility and other amenity actions.

Older `improvement_opportunities`, `opportunity_score`, recommendation, impact,
project, and priority tables remain because APIs and compatibility workflows
still consume portions of them. Do not mistake them for the canonical broad
seating ranking or delete them without a consumer migration.

## 9. Review routing and context

Key files:

- `src/review/assignment_router.py`
- `src/review/context.py`
- `src/api/app.py`
- `src/review/community_survey_v1.py`

Assignment scenarios preserve how a reviewer reached a stop:

- `opportunity`: highest-ranked eligible seating opportunity; all workflow
  states except `no_current_action`
- `route`: pending available queue stop on a reviewer-selected route
- `nearby`: pending available queue stop nearest supplied coordinates
- `map` / `direct`: reviewer-selected current stop

Route, nearby, and direct selection do not borrow Opportunity Review ranking.
Unknown opportunity campaigns fail closed. Historical `campaign=NULL` rows
remain readable.

For a generic opportunity assignment, workflow maps to campaign:

| Seating workflow | Assignment campaign |
|---|---|
| `verify_presence` | `presence_verification` |
| `assess_adequacy` | `seating_adequacy` |
| `collect_clearance_observation` | `bench_clearance` |
| `planning_review` | `planning_review` |
| `constrained_or_special_review` | `constrained_review` |

Campaign/review focus controls emphasized survey fields. Public context keeps
entry explanation (“Why you're reviewing this stop”) separate from evidence need
(“What would be useful to check”). One survey is shared across paths.

## 10. Assignments, observations, and temporal provenance

`stop_review_assignments` records stop, reviewer, scenario, nullable campaign,
status, and timestamps. `stop_observations.assignment_id` is a nullable indexed
foreign key linking a new observation to the assignment that produced it. It is
not unique because the append-only design and compatibility model do not use it
as observation identity. Historical observations can legitimately have a null
assignment ID.

Assignment-backed submissions insert a new observation and never overwrite a
prior reviewer/stop row. Relevant prospective fields include `review_mode`,

### Reviewer identity and passwordless login

`community_reviewers.id` is the durable identity referenced by assignments,
observations, and stewardship rows. `reviewer_key` remains an anonymous browser
handle in Flask's signed session; it is not an account credential. Claimed
profiles add normalized private `email`, `email_verified_at`, and `claimed_at`.

`reviewer_login_tokens` stores only SHA-256 token hashes. Links expire after 20
minutes and are invalid after one use. Claiming an unused email updates the same
anonymous reviewer row. A new browser using an existing verified email attaches
to that ID. An anonymous profile with history is never automatically merged into
a different claimed account.

Authenticated Flask sessions last 30 days, use `HttpOnly` and deliberate
`SameSite=Lax` cookies, and are rotated by clearing the anonymous session during
verification. Sign-out requires the session CSRF token and deletes no durable
records. `REVIEWER_AUTH_DEV_MODE` defaults off and is never inferred from Flask
debug mode.

Run `python scripts/active/create_review_tables.py` before deployment. Set a
strong `FLASK_SECRET_KEY`, `DMV_BUS_STOPS_DB`, and `SESSION_COOKIE_SECURE=1`
under HTTPS. Email delivery uses the provider-neutral callable
`(recipient, verification_url, expires_minutes)`. Tests may inject
`REVIEWER_EMAIL_SENDER`; production can select either the Resend HTTPS adapter with
`REVIEWER_EMAIL_BACKEND=resend`, `REVIEWER_EMAIL_FROM`, and `RESEND_API_KEY`, or the
standard-library SMTP adapter with `REVIEWER_EMAIL_BACKEND=smtp`,
`REVIEWER_EMAIL_FROM`, `SMTP_HOST`, `SMTP_PORT`, `SMTP_USE_TLS`, and optional paired
`SMTP_USERNAME` / `SMTP_PASSWORD`. No provider is mandatory and no credentials
belong in the repository. The HTTPS adapter posts the same plain-text message to
Resend's `/emails` endpoint with a ten-second timeout and requires a 2xx response
containing a nonempty provider message ID. Provider errors are reduced to a fixed,
non-sensitive application error; there is no SDK or request-loop retry.
`SMTP_USE_TLS=1` means STARTTLS on the configured connection; TLS negotiation
completes before optional authentication, and failure does not downgrade.
`SMTP_USE_TLS=0` is intended only when transport security is supplied by the
deployment/provider. SMTP-over-SSL is not implemented. Sender, host, and port
are mandatory, TLS accepts only `0` or `1`, and credentials must be supplied as
a pair.

Magic-link requests are persistently limited to 3/15 minutes and 10/day per
normalized email, plus 20/15 minutes and 100/day per direct source address.
Rate-limit keys are HMAC-SHA-256 values; raw email and IP are not duplicated in
`reviewer_auth_attempts`, and records older than 48 hours are cleaned during
enforcement. `request.remote_addr` is used directly and arbitrary
`X-Forwarded-For` is ignored. A trusted-proxy deployment must configure address
translation at the WSGI layer rather than trusting public forwarded headers.

Successful delivery invalidates older unused links for the same email. Definite
delivery failure invalidates the new link immediately; there is no request-loop
retry or background queue. Without valid mail configuration, the login UI says
email sign-in is temporarily unavailable while anonymous review remains usable.
Links are captured only in tests or explicit `REVIEWER_AUTH_DEV_MODE=1`, which
defaults off. Public APIs do not expose email or auth metadata. Legacy text
reviewer identifiers are not migrated by this feature.

### Pilot review-lead dashboard

`community_reviewers.role` is constrained to `reviewer` or `review_lead` and
defaults to `reviewer`. `/admin` and `/api/admin/pilot-summary` share one
server-side authorization check: the session must contain the verified reviewer
ID and matching reviewer key, the database row must remain email verified, and
its role must be `review_lead`. Anonymous reviewer keys and ordinary verified
reviewers are denied. There is no public role-escalation endpoint.

The dashboard is read-only. It summarizes submitted `community_review`
observations, active-stop coverage using exactly
`stop_gtfs_status.current_gtfs=1`, separate geography dimensions, route/mode
activity, consensus progress, conflicts, unknown amenity status, integrity
cautions, and recent contributions. “Active reviewer” means a reviewer with a
submitted observation in the stated window; login/session activity is not
counted. Historical inactive or retired-stop contributions are marked as such.
The median is calculated among contributors with at least one review. A repeat
reviewer has at least two reviews; repeat-observation rate is all reviews beyond
each contributor's first divided by total reviews. Geography groups submitted
reviews at active stops independently for state, county, municipality, ward, and
ANC. Route counts include a review in every route serving that stop. Reached and
near consensus use the canonical amenity workflow states `consensus_reached` and
`one_observation_short`; conflict counts describe disagreement, not reviewer
quality.

Review leads can see public display names, contribution counts, timestamps,
routes, and geography. The API excludes email, token hashes, auth-attempt keys,
sessions, IP addresses, and private auth metadata. It provides no edits,
deletion, overrides, evidence or identity mutation, account management, or
assignment mutation.

After backup and migration, operators assign the role explicitly:

```text
python scripts/active/set_reviewer_role.py --db <explicit-db> \
  --reviewer-id <id> --role review_lead
```

The repository production path additionally requires
`--allow-production-database`. Demotion uses `--role reviewer`.

`GET /api/reviewer/email-auth-health` reports only availability, backend name,
secure-cookie status, and required configuration names. It never returns SMTP
credentials, API keys, or secret values. Configuration names may include
`RESEND_API_KEY` when that backend is selected. Rotating `FLASK_SECRET_KEY` invalidates sessions and
makes earlier HMAC rate-limit buckets unreachable; durable reviewer history is
unchanged.

The supported limited-pilot process is `python -m scripts.active.serve_pilot`,
which runs Waitress after validating the secret, absolute database path, secure
cookie setting, support contact, development-auth state, and optional SMTP. It
binds to localhost by default; HTTPS termination and process supervision are
operator-managed. Backup, restore, restart, logging, and smoke-test procedures are
in `docs/DEPLOY_LIMITED_PILOT.md`.

The prospective observation schema stores
`assignment_id`, `streetview_imagery_month`, `weather_exposure`, and
`riders_avoid_facilities` alongside presence, type, condition, comfort,
accessibility, clearance, notes, and stewardship-interest fields.

`observed_at` records observation/submission time.
`streetview_imagery_month` records the imagery capture month. They must not be
conflated. Unknown imagery date can be acknowledged explicitly. No photo/blob
storage exists.

## 11. Targeted post-review refresh

After a valid submission, `src/api/app.py` recalculates consensus and calls
`refresh_after_community_mutation` for the affected physical stop:

```text
community observations
  -> stop consensus
  -> two canonical amenity-status rows
  -> two amenity review-priority rows
  -> affected seating opportunity
  -> affected review-queue rollup
  -> deterministic seating rank refresh
```

This is targeted; it does not perform a global evidence or 6,723-row opportunity
rebuild per submission.

## 12. Geography and dashboard APIs

`stop_jurisdiction` and DC boundary associations support overlapping dimensions.
Dashboard reporting intentionally exposes state, county, municipality, ward,
ANC, and other available jurisdictions as separate searchable rows rather than
forcing one hierarchy. A stop may contribute to several useful geographic views.

Important routes include:

- `/`, `/dashboard` — dashboard
- `/stop/<physical_stop_id>` — stop detail
- `/review/start` — routed assignment entry
- `/review/<physical_stop_id>` — shared survey
- `/review/<physical_stop_id>/info` — evidence and plain review context
- `/review/<physical_stop_id>/assignment` — assignment API
- `/review/submit` — append observation and targeted refresh
- `/seating-opportunities` — broad seating universe and summary
- `/bench-candidates` — narrow physical bench candidates
- `/api/review-queue` — review queue
- `/geography/states`, `/geography/counties`, `/geography/municipalities`
- `/geography/dc-wards`, `/geography/dc-ancs`

## 13. Migrations and rebuild order

For an existing database, the active review migration is idempotent:

```bash
python scripts/active/create_review_tables.py
```

It creates review tables when absent, adds nullable
`stop_review_assignments.campaign`, adds nullable observation fields
`assignment_id`, `weather_exposure`, and `riders_avoid_facilities`, and creates
the assignment index. Set `DMV_BUS_STOPS_DB` for a non-default database.

A full derived refresh, when evidence or upstream ridership actually changed,
should respect dependencies:

```text
active GTFS status and physical-stop membership
  -> source evidence / community observations
  -> opportunity assessments and rider percentile
  -> canonical amenity status
  -> amenity review priority
  -> broad seating opportunities
  -> review queue and downstream compatibility summaries as required
```

Verified entry points include:

```bash
python -c "from src.assessment.create_opportunity_assessments import create_assessments; create_assessments('/path/to/copy.db')"
python scripts/active/rebuild_stop_amenity_status.py --db <database>
python scripts/active/rebuild_amenity_review_priority.py <database>
python scripts/active/generate_seating_improvement_opportunities.py <database>
python -c "from src.review.create_review_queue import create_review_queue; create_review_queue('/path/to/copy.db')"
```

Several module producers default to the repository database and do not accept
`DMV_BUS_STOPS_DB`; invoke their Python function with an explicit database path
or use a copied database in a controlled process. Never run a copied command
against production without inspecting its current argument behavior.

## 14. Tests and invariants

Run:

```bash
python -m unittest discover -s tests -p "test_*.py" -v
python -m compileall -q src scripts/active scripts/diagnostics tests
git diff --check
```

High-value invariants include:

- active scope always equals `current_gtfs=1`
- exactly two canonical amenity rows per active stop
- one seating opportunity per active stop
- no score threshold controls seating membership
- canonical identities are unique and inactive rows are excluded
- rider percentile column and assessment JSON agree
- assignment-backed reviews append and retain assignment linkage
- Street View imagery month remains separate from observation time
- unknown campaigns and incomplete migrations fail closed
- WMATA amenity fields and quarantined legacy DDOT rows do not become current
  shelter/bench authority

## 15. Current, compatibility, and future boundaries

### Current and authoritative for their purpose

- `stop_gtfs_status` for current-stop scope
- source evidence plus `stop_consensus` as inputs
- `stop_amenity_status` for canonical current shelter/bench synthesis
- `stop_amenity_review_priority` for amenity verification ordering
- `opportunity_assessments.rider_exposure_percentile` for rider exposure
- `seating_improvement_opportunities` for broad seating review/ranking
- `bench_installation_candidates` for narrow physical bench candidacy
- assignment-linked append-only `stop_observations` for review history

### Retained compatibility or legacy context

- `route_exposure_score` in older priority factors
- `improvement_opportunities.opportunity_score`
- generic recommendation/impact/project/priority tables and APIs
- historical assignments with `campaign=NULL`
- historical observations with `assignment_id=NULL` or legacy remote modes
- quarantined legacy DDOT records and archived patch scripts

These may still have consumers. “Legacy” does not mean safe to delete.

### Not implemented

- observed stop-level boarding counts as the rider-exposure metric
- automatic evidence freshness weighting or change detection
- reviewer photo upload/storage
- automated stewardship reminders
- formal agency escalation or ownership/permit workflows
- engineering, ADA, utility, right-of-way, or construction approval

## 16. Known technical debt

- The schema is larger than the canonical product surface and contains multiple
  generations of opportunity/recommendation data.
- `schema.sql` does not yet bootstrap every production table/column; the review
  migration covers the prospective campaign/observation additions, while older
  mature fields still depend on existing database history and other producers.
- Some active and root-level operational scripts have inconsistent database-path
  interfaces.
- Route assignments persist the route scenario but not the exact selected route
  ID in the assignment row.
- Historical observation and assignment rows have nullable prospective fields.
- Local evidence coverage and community consensus are uneven.
- Archived scripts include obsolete one-off patches and may not compile; they are
  historical evidence, not an executable migration set.

Prefer small, idempotent active migrations; explicit source authority; temporary-
copy preflights; and consumer audits before retiring compatibility fields.

## 17. Repository map and supported operations

- `src/`: active application and domain code. The Flask entry point is
  `src/api/app.py`; supported diagnostic modules also live under their domain,
  including `src/processing/heading_audit.py`.
- `scripts/active/`: supported current migrations, imports, and rebuilds. Its
  [command inventory](../scripts/active/README.md) identifies mutations and safe use.
- `scripts/diagnostics/`: supported read-only checks. Diagnostics open existing
  databases in SQLite read-only mode and are compiled with active code.
- `scripts/archive/`: selected historical migration records only. They may target
  old schemas, are unsupported, and are excluded from compilation requirements.
- `tests/`: active regression suite.
- `docs/`: current project, volunteer, schema, operations, and pilot guidance.
- `src/database/dmv_bus_stops.db`: default local SQLite location. Deployment should
  set an absolute `DMV_BUS_STOPS_DB`. `src/database/backups/` and other database
  copies are local operational material, not normal source changes.
- `.env`: ignored local/deployment configuration. Start from `.env.example`; never
  commit real secrets.

Verified routine commands:

```bash
python -m src.api.app
python -m unittest discover -s tests -p "test_*.py" -v
python -m compileall -q src scripts/active scripts/diagnostics tests
git diff --check
python scripts/active/create_review_tables.py
python scripts/diagnostics/preflight_amenity_review_priority.py <database>
python scripts/active/rebuild_stop_amenity_status.py --db <database>
python scripts/active/rebuild_amenity_review_priority.py <database>
python scripts/active/generate_seating_improvement_opportunities.py <database>
```

The first command is local development only, not a production WSGI server. Before
every migration/rebuild, use an explicit database target, backup and hash it, test a
copy, and verify post-operation invariants. Do not execute archived migrations as a
set, compile `scripts/archive`, rebuild physical stops, or treat an ambiguous loose
script as a supported command.

See [Local development](LOCAL_DEVELOPMENT.md) and
[Small-pilot readiness audit](PILOT_READINESS.md).
