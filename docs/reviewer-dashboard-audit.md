# Reviewer/dashboard audit — 2026-09-28

This document records successive audit passes. The final state is **267 passing
tests**, Chrome responsive checks completed, Maps as the primary wayfinding action,
and optional “Try Street View”. See the [final investigation](reviewer-streetview-investigation.md)
and [deployment runbook](reviewer-deployment-runbook.md). Earlier counts and
unverified-browser statements below are historical, not current release gates.

Scope: clean initial working tree, HEAD `fa82b74`; inspected recent exposure-map,
reviewer-profile, authentication and member-direction changes before editing.
Production database inspected read-only; no data migration or backfill executed.

## A. Reviewer exposure

Both completion `reviewer_stats.total_route_boardings_represented` and profile
`stats.ridership_impacted` summed `stop_improvement_impact.daily_route_exposure`
once per distinct completed physical stop. Despite its name, that field copies
`combined_route_weekday_boardings` from opportunity factors: a sum of each linked
route's monthly weekday boarding total (MAX per route in the global latest
ridership period). It is not a daily quantity. Route linkage is physical members
→ stop_routes → routes. The impact generator divides this monthly quantity by
calendar weekdays in the latest month to derive `average_weekday_boardings`.

The latest snapshot is `2026-07-31` (23 calendar weekdays). Selection is global
`MAX(period)`, not each route's latest available month. Missing routes therefore
do not get an older month fallback. This relies on sortable ISO dates. The map
uses `src/scoring/exposure_map.py:weekday_divisor`; API route summaries have
another calendar-weekday implementation. No hard-coded /21 or /23 was found in
the active source/display paths. Those duplicate derivations are left unchanged;
reviewer totals now consume the existing canonical impact field directly.

New field on both responses: `average_weekday_route_exposure_represented`, a
rounded sum of canonical `average_weekday_boardings` for distinct completed
physical stops, including inactive historical stops. Deployment validation added
explicit coverage counts: missing rows now produce an incomplete subtotal, or null
when no reviewed stop has a value; genuine zero remains numeric zero. Old fields were removed
because all discovered consumers were updated together. Stop detail no longer
falls back to the monthly-scale field when displaying weekday exposure.

These are current derived estimates, not review-time snapshots. Old reviews can
change totals when route mapping/ridership changes; absent historical derived
rows cannot be reconstructed here. Routes shared by multiple reviewed stops
contribute at each stop. This is neither unique riders nor observed stop-level
boardings. The inspected database has zero completed assignments and zero
observations; historical semantics are tested using fixtures.

## B. Popup buttons

Two duplicate rules supplied conflicting padding, rounding and backgrounds.
Leaflet's `.leaflet-container a` has greater specificity than `.stop-review-button`
and could replace its white foreground. Even white on the old #2c7be5 was only
4.14:1. One rule set now explicitly targets `.leaflet-popup-content a.stop-review-button`,
including visited/hover/focus states, without `!important` or hover opacity.
White on #1756a9 calculates to 7.14:1; hover #123f7b to 10.38:1. Keyboard focus
uses an offset dark outline and white separation. Targets are at least 44px high.
Popup actions in dashboard.js all use this class; stop-detail, review-info and
legacy review_stop.js links share it. These are cascade/contrast calculations,
not measured browser-computed styles.

## C. Serving direction and Street View

Current frontends already deduplicated/displayed `serving_directions`, including
multiple values. The reported null-singular failure was not reproducible in this
checkout: neither API emitted a singular field, and `/stops/<id>` omitted the
array altogether despite its comment. Both APIs now share the trusted payload.
`serving_direction` is a structured direction record for exactly one unique
heading; null otherwise. Arrays retain all provenance and multiple values.
The UI continues to read the array, not the optional singular projection.

Eligibility remains explicit physical member → trusted GTFS/stop-code identity
→ latest WMATA heading. Distance, unexplained status codes and the evidence row's
nearest-neighbor physical ID do not establish eligibility. WMATA amenity fields
remain excluded from authoritative amenity status. Compass conversion is unchanged.

Read-only counts, restricted exactly to `stop_gtfs_status.current_gtfs=1`:

| Quantity | Count |
| --- | ---: |
| Active physical stops | 7,117 |
| At least one trusted direction | 4,903 |
| No trusted direction | 2,214 |
| Exactly one distinct heading | 4,897 |
| Multiple distinct headings | 6 |
| Before: missing singular with nonempty trusted array in review-info | 4,903 |
| After: null singular with nonempty array (intentional multiple headings) | 6 |

Strictly, baseline singular was absent, not explicitly JSON null. Treating a
missing property as null explains the 4,903 count; no current UI reads it.
Recommend validating secondary GTFS shape/adjacent-stop bearings against a
sample of known boarding locations, retaining trip direction, provenance and
confidence. Do not infer them from road orientation. No such fallback implemented.

RoadSpatialIndex's `heading` is segment orientation, despite its old docstring.
The review-info caller also supplied latitude/longitude in the wrong order.
Shared `streetview_for_stop` now calls the index with longitude, latitude and
requests its road coordinate as viewpoint, with spherical bearing FROM that
viewpoint TO the actual stop. `/stops` replaces `streetview_display_heading` with
`streetview_camera_heading`; review-info adds that field. Missing/coincident road
viewpoints yield null and omit `heading=`. No known consumer used the old field.
Google can snap to a different panorama; exact alignment at that actual panorama
is unverified without panorama metadata. No external lookup was introduced.
A dead legacy observation-endpoint block using undefined `row` was removed.

## D. Concrete reward proposal (not implemented)

Current storage has reviewer identity/display name, completed assignment timestamps,
dated observations and a completion-time `first_review` boolean. That boolean is
a count check, not a persisted, concurrency-safe award. No consent or award ledger
exists. Geography is available in physical_stops and stop_jurisdiction columns
(state, county, municipality, ward, ANC); jurisdiction_source_evidence provides
local-source provenance. Current route mappings are not historical snapshots.

Proposed permanent awards, all based on completed evidence and distinct entities:

| Award | Proposed rule / decision needed |
| --- | --- |
| First Look | Earliest completed community observation at a physical stop; deterministic timestamp then assignment-ID tie break; award once |
| Jurisdiction Pioneer | First completed observation for a `(dimension, geography_id)`; same tie break |
| Local Explorer | 5/20/50 distinct physical stops within a chosen dimension/value |
| Route Connector | 5/10/25 distinct agency-qualified routes; freeze qualifying links when awarded |
| Regional Explorer | Contributions to 2/3/5 values in ONE selected dimension, not a sum of overlapping ward/county/state memberships |
| Consensus Builder | Defer: canonical synthesis uses at least 3 observations and confidence ≥0.75; raw observations are not necessarily independent reviewers. Define independent-voter eligibility and capture before/after transition atomically first |
| Photo Contributor | Defer until link review/moderation verifies useful evidence; a submitted URL alone is not proof of a photo |

Proposed tables: `reviewer_public_preferences(reviewer_id PK, leaderboard_opt_in,
consented_at)`; `geography_dimensions(key PK, label)`; `geography_units(id PK,
dimension_key, stable_key UNIQUE, label)`; `physical_stop_geographies(physical_stop_id,
geography_id, source, valid_from, valid_to)`; `reviewer_achievements(id PK,
reviewer_id, badge_key, rule_version, dimension_key, geography_id, tier,
qualifying_observation_id, awarded_at, evidence_snapshot_json)` with a unique
reviewer/badge/scope/tier constraint. Store permanent qualification evidence,
including route/geography versions. No fixed geography hierarchy.

Proposed `GET /api/leaderboard?metric=distinct_stops&dimension=county&geography_id=…&limit=5`:
return period/rule version, metric, dimension, compact rows of display_name/rank/value,
and a private session-owned `self` rank even outside top five. Metrics: distinct
stops, distinct routes, distinct geography values within the selected dimension,
first-review count. Active ranking populations join exactly `current_gtfs=1`;
permanent historical awards survive inactivity. Rank ties share rank; deterministic
display ordering must not confer an extra achievement. No opaque score, emails,
anonymous reviewer keys or cross-user private IDs in public responses. Opt-in is
required, and anonymous reviewers are excluded. A display name alone is not consent.

Product decisions: confirm thresholds, eligible identity/abuse rules, geography
dimension defaults and overlap semantics, all-time versus recent ranking period,
tie policy, moderation/revocation, identity merges, historical backfill and consent.
Until then, no leaderboard schema, public population or reward changes are shipped.

## E. Photos and immutable evidence

Survey definition/renderer adds optional `photo_url`, carried by existing FormData
serialization. Validation accepts HTTP/HTTPS, rejects credentials, malformed URLs,
control/space characters and backslashes, and caps input at 2048 characters.
Server never fetches the URL. Guidance asks contributors to avoid identifiable
faces/license plates where practical and makes public link visibility explicit.

`observation_attachments` has id, observation_id FK, attachment_type, external_url,
nullable storage_key/provider, created_at and an observation index. At least one
of external_url/storage_key must exist, supporting future first-party objects.
`scripts/active/create_review_tables.py` creates the table and index idempotently.
Normal attachment writes perform no schema creation. Deployments must run
`python scripts/active/create_review_tables.py` against the intended
`DMV_BUS_STOPS_DB` before accepting photo links. A new photo submission without
the table returns 503 `review_schema_migration_required` before saving evidence;
no-photo submissions can proceed without the optional attachment table. History
reads still return an empty attachment list on older schemas. Migration was tested
on temporary DBs, not run on the repository DB. Observation and attachment save
in one transaction.

Saved observations cannot be overwritten via review/submit. A retry identifies the
community observation by assignment ID and verifies the assignment and saved
observation both belong to the same reviewer and physical stop. A write-lock
recheck serializes duplicate submissions; only the first inserts evidence/photo.
Mismatched or duplicate historical assignment observations fail closed with 409.

A matching retry returns normal success with `observation_id`,
`evidence_already_saved`, and `already_completed`. Pending assignments rerun only
consensus and derived refresh from stored evidence before completing; completed
assignments return the saved consensus without rerunning refresh. Replacement
photo/observation values never change saved evidence. The original completion
timestamp is preserved. No new observation can be created for an inactive stop;
matching saved historical evidence can still be acknowledged on retry.

Consensus, derived refresh and completion-write failures return retryable 500
`derived_refresh_failed` with `evidence_saved: true` and the observation ID.
A reviewer can retry rather than require manual recovery. The refresh operations
are rebuildable, though their individual commits are not one atomic transaction
with the initial evidence save. A new dated review requires a new assignment.

History responses (`/stops/<id>/community-reviews` and review-info community reviews)
add `attachments: [{id, attachment_type, external_url, created_at}]`; old rows get
an empty list. Both history displays render validated URLs with DOM escaping,
`target="_blank" rel="noopener noreferrer"`. No canonical amenity field stores links.

## F. Responsive audit and manual test matrix

Added missing viewport tags to review, detail, route selection, profile, sign-in
and legacy survey templates. Shared CSS reduces mobile margins, wraps long names,
stacks controls, constrains popups, gives inputs 16px text and targets 44px height,
allows table scrolling, and limits map height in portrait/landscape. Review
navigation now sits beside serving direction; evidence/context is collapsed;
essential questions precede optional identity and stewardship content.

The original pass did not run a browser harness. The later deployment validation
used installed headless Chrome and is recorded in [reviewer-deployment-validation.md](reviewer-deployment-validation.md).
Physical-phone keyboard/zoom behavior still needs manual validation. The matrix uses 320×568, 375×812, 390×844, 430×932 and 844×390 landscape:

| Page/state | Manual checks still required |
| --- | --- |
| Dashboard/map/filter/geography | No document overflow; long route/county/ANC names; filters wrap; map usable; tables scroll locally |
| Leaflet popup | Long stop name, default/visited/hover/focus action colors; visible focus; popup stays within viewport |
| Stop detail | Single/multiple/no directions; empty/populated photo history; retired-stop successor links |
| Review form | Identity → directions → Street View/Maps → essential questions; mode switching; imagery month; keyboard open; URL error; submit reachable |
| Route selection | Long route labels, checkbox targets, saving/error/empty states |
| Reviewer profile/sign-in | Long display name, stats, stewardship links, anonymous and signed-in states, errors |
| Completion | Long route list, total qualification, continue/return controls |
| Feedback/legacy survey | Input zoom, stacking, keyboard navigation, error messages |

Remaining: actual Leaflet inline-size interactions, phone keyboard occlusion,
all zoom/orientation behavior and loading/error layout need browser verification.
Legacy root `dmv_bus_stops_dashboard.html` and raw handbook HTML are not the active
dashboard/reviewer templates and were not redesigned. No leaderboard page added.

## Validation and intentional limits

Previous audit baseline: 254 tests passed (the working-tree report, rather than
the older 253-test summary). Merge-readiness validation is recorded below.
Tests cover distinct historical exposure, trusted single/multiple/missing direction
payloads, camera coordinate order/bearing, URL rejection/storage/rollback, attachment
history, immutable assignment evidence, active-stop submission restrictions and
template viewport presence. Existing member-identity and active-population tests
remain in the suite. Python compilation and `git diff --check` passed.
JavaScript `node --check` was attempted but unavailable; no browser tests claimed.

No live DB mutation, identity migration, GTFS fallback, WMATA amenity authority,
ridership pipeline redesign, historical snapshots, cloud upload, photo retrieval,
badge awards, ranking or deployment was performed.

## Exact changed files

- `docs/serving-directions.md`
- `scripts/active/create_review_tables.py`
- `src/api/app.py`
- `src/dashboard/static/dashboard.css`
- `src/dashboard/static/review_info_loader.js`
- `src/dashboard/static/stop_detail.js`
- `src/dashboard/templates/review.html`
- `src/dashboard/templates/review_routes.html`
- `src/dashboard/templates/reviewer_profile.html`
- `src/dashboard/templates/reviewer_sign_in.html`
- `src/dashboard/templates/stop_detail.html`
- `src/dashboard/templates/survey.html`
- `src/review/community_survey_v1.py`
- `src/review/render_survey.py`
- `tests/test_active_review_workflow.py`
- `tests/test_reviewer_auth.py`
- `tests/test_serving_directions.py`

New files (untracked until staged):

- `docs/reviewer-dashboard-audit.md`
- `src/dashboard/static/photo_links.js`
- `src/review/attachments.py`
- `src/spatial/camera_heading.py`
- `tests/test_reviewer_field_audit.py`

## Merge-readiness cleanup validation

The focused cleanup changed only `src/api/app.py`, `src/review/attachments.py`,
`tests/test_active_review_workflow.py`, `tests/test_reviewer_field_audit.py`, and
this report. Existing migration and frontend changes were reviewed and preserved.
The request ended mid-sentence in item 2; only the supplied retry-safety and
request-time-schema requirements were implemented.

- Full discovery: **261 tests passed** in 18.563 seconds. The initial sandbox run
  encountered Windows temporary-directory permission errors; the unrestricted
  rerun passed.
- Focused fixtures cover first submission, exact completed replay, replacement
  photo/notes preservation, consensus and derived-refresh failure recovery,
  mismatched assignment/saved-observation ownership, two concurrent submissions,
  missing attachment schema, no request-time DDL, and repeatable migration
  preserving observations/attachments.
- Python compilation passed for the touched API/helper, migration and tests.
- `git diff --check` passed (only repository line-ending notices).
- Browser/mobile rendering remains unverified. No badges, leaderboards, GTFS
  direction fallback, live database changes, staging, commit or deployment.

## git diff --stat

```text
 docs/serving-directions.md                    |  19 +-
 scripts/active/create_review_tables.py        |   8 +
 src/api/app.py                                | 526 ++++++++++----------------
 src/dashboard/static/dashboard.css            |  92 +++--
 src/dashboard/static/review_info_loader.js    |  12 +-
 src/dashboard/static/stop_detail.js           |   6 +-
 src/dashboard/templates/review.html           |  70 ++--
 src/dashboard/templates/review_routes.html    |   1 +
 src/dashboard/templates/reviewer_profile.html |   8 +-
 src/dashboard/templates/reviewer_sign_in.html |   3 +-
 src/dashboard/templates/stop_detail.html      |   2 +
 src/dashboard/templates/survey.html           |   2 +
 src/review/community_survey_v1.py             |   7 +
 src/review/render_survey.py                   |  10 +-
 tests/test_active_review_workflow.py          | 185 ++++++++-
 tests/test_reviewer_auth.py                   |   5 +-
 tests/test_serving_directions.py              |   6 +-
 17 files changed, 539 insertions(+), 423 deletions(-)
```

Git excludes the five new files listed above from this unstaged diff statistic.

## Deployment-validation follow-up

See [reviewer-deployment-validation.md](reviewer-deployment-validation.md) for the
that pass's results: 265 passing tests, real copied-database submission
and migration checks, FK enforcement, coverage metadata, all six multi-heading
stops, five emulated mobile viewports, and the unresolved Google no-imagery
results. No live migration/deployment was performed. Earlier counts and browser
limitations above describe the prior passes, not the final validation state.

## Final release-candidate review

Final rerun: **267 tests passed** (19.853 seconds); the five focused suites also
passed. Python compilation and `git diff --check` passed. Existing Chrome results
remain applicable: this review removed only console logging, not rendering logic.
No new browser run or Node validation is claimed.

Cleanup removed three full-payload console logs from `stop_detail.js` and one
submission-response log from `review.html`, corrected the API camera-bearing
comment, removed the machine-specific Chrome executable path from the validation
report, and clarified superseded browser/Street View statements in these reports.
No substantive behavior, schema, direction data, or live database was changed.
The repository database SHA-256 remains
`d8858055d47af67831b19e9009612a96d78cd7c56bb8a2a97a2c2d11f0172034`.

Contract review confirmed canonical average-weekday exposure plus coverage,
distinct historical completed stops, exact `current_gtfs=1` active eligibility,
non-authoritative WMATA amenity fields, trusted member/GTFS direction linkage,
actual-stop Maps navigation, optional Street View, immutable non-fetched photo
references, and identity-checked idempotent retries with a write-lock recheck.
The runbook includes backup, explicit DB selection, migration, schema/FK checks,
host-specific restart choices, production smoke tests, and code/DB rollback.

All nine non-ignored untracked files belong in the release:

- `docs/reviewer-dashboard-audit.md`
- `docs/reviewer-deployment-runbook.md`
- `docs/reviewer-deployment-validation.md`
- `docs/reviewer-streetview-investigation.md`
- `src/dashboard/static/photo_links.js`
- `src/review/attachments.py`
- `src/spatial/camera_heading.py`
- `tests/test_reviewer_field_audit.py`
- `tests/test_streetview_links.py`

No untracked candidate requires a human disposition decision. Keep `.tmp/`
(including scripts, disposable DBs, screenshots, logs and Chrome profiles),
Python caches and `.env` ignored; none should be force-added. No uncertain file
was deleted. No tracked `.tmp`, DB, log or PNG artifact was found. Review of the
candidate files and a targeted key/token scan found no release credentials;
test URLs and mock identities are fixtures, not production credentials.

`feedback.html` and `pilot_reviewer_management.html` have only CRLF/LF differences
and match HEAD after normalization. Preserve them but exclude them from the
release commit. Include the other 18 tracked changed files and nine files above.
Do not use a blanket add that obscures this distinction.

No accidental duplicate API definition was found. The legacy 409 completion UI,
disabled `review_stop.js`, unused legacy survey presentation, and existing
compatibility direction projection are outside this release's cleanup; they do
not alter the matching-retry success path. They were retained rather than removed
without a separate compatibility review. Existing duplicate legacy history helpers
in `src/dashboard/data.py` were likewise not introduced or changed here.

No code release blocker identified. Ready for human commit approval; deployment
still requires the runbook's production backup/migration/restart/smoke steps.
Street View coverage, physical-phone keyboard behavior, and the six previously
documented multi-heading identities retain their stated limitations. No commit,
staging, production migration, or deployment was performed by this review.
