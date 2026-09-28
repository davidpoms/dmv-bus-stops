# Reviewer deployment-readiness validation — 2026-09-28

Follow-up: [final Street View investigation](reviewer-streetview-investigation.md)
supersedes this report's Street View gate and test count. The optional-imagery
fallback and operator procedure are in the [deployment runbook](reviewer-deployment-runbook.md).

This pass used the existing working tree. No commit, deployment or live migration
was performed. Existing unrelated modifications were preserved. Validation found
and corrected three narrow gaps: SQLite FK enforcement on the submission/setup
connections, exposure coverage metadata/wording, and measured mobile popup/input
CSS problems. No ridership formula, badge, leaderboard, GTFS fallback, WMATA amenity
authority, upload or photo-fetch behavior was added.

## 1–3. Disposable migration and real submission lifecycle

The live database was opened using a SQLite `mode=ro` URI and copied through
`Connection.backup()` to `.tmp/deployment_validation/staging.db`. Negative-schema
checks used a second copy, `missing_schema.db`. The repository database SHA-256
before and after validation is:

`d8858055d47af67831b19e9009612a96d78cd7c56bb8a2a97a2c2d11f0172034`

Exact setup path tested (PowerShell, from repository root):

```powershell
$env:DMV_BUS_STOPS_DB = (Resolve-Path '.tmp/deployment_validation/staging.db').Path
python scripts/active/create_review_tables.py
```

Deployment uses **the same `scripts/active/create_review_tables.py` command** after
setting `DMV_BUS_STOPS_DB` to the intended deployment database. It was NOT run
against the repository database. No normal request executes attachment DDL.

Migration results:

- Created `observation_attachments` with `id`, `observation_id`, `attachment_type`,
  `external_url`, `storage_key`, `provider`, `created_at`.
- Created index `observation_attachments_observation` on observation_id.
- Foreign key targets `stop_observations(id)`. Orphan insertion raised
  `sqlite3.IntegrityError`; a valid linked attachment succeeded; attachment
  `foreign_key_check` returned no violations.
- Setup and the application's evidence-write connection now explicitly enable
  `PRAGMA foreign_keys=ON`. SQLite enforcement is connection-local: the database
  file cannot turn it on for arbitrary third-party connections. The regression
  test verifies the application's actual write connection, not just a test connection.
- Two reruns preserved complete observation/attachment row contents and counts.
  History API reads passed both with a photo and without a photo after rerunning.

Real Flask lifecycle on the copied schema/data, **without mocking consensus or
canonical refresh**:

1. `/review/start?stop_id=7755&mode=map` created/reused a reviewer and obtained
   active assignment 130 (reviewer 144).
2. `/review/7755/info?assignment_id=130` returned 200 with trusted direction.
3. `/review/submit` with `https://example.org/validation-photo` returned 200,
   observation 31, exactly one observation and one attachment for assignment 130,
   correct attachment FK, and completed assignment.
4. Real consensus persisted bench=yes, shelter=no, confidence=1.0; canonical status
   became bench=likely_yes and shelter=likely_no, with both review-priority rows.
   Reviewer stats and canonical average-weekday exposure (9,034 rounded) returned.
5. Exact retry and replacement-photo/notes retry both returned 200, the same
   observation ID, `already_completed=true`, `evidence_already_saved=true`.
   Original rows, attachment URL and completion timestamp were unchanged.
6. Invalid scheme returned 400; wrong stop 400; wrong reviewer 403; a non-current
   stop with an assignment returned 409 `stop_not_current`; missing attachment
   schema returned 503 before inserting any observation for that assignment.

Later browser fixtures deliberately added historical/coverage records only to
this disposable copy. The primary smoke counts above are per assignment, not
an assertion that the entire copy contains only one review forever.

## 4. Exposure coverage

The initial implementation failed the requested distinction: COALESCE made missing
rows indistinguishable from true zero, and the completion UI hid numeric zero.
The narrow correction still sums only canonical `average_weekday_boardings` once
per distinct completed physical stop. No divisor or new ridership estimate exists.

Both profile stats and completion reviewer_stats now include
`route_exposure_coverage` with `reviewed_stops`, `stops_with_exposure`,
`missing_stops`, and `complete`. The quantity is null when reviewed stops exist
but none have a value; zero remains a real numeric zero. A partial known subtotal
has incomplete coverage. With no completed stops the quantity is 0 and coverage
is 0/0 complete.

| Fixture | Result |
| --- | --- |
| Every reviewed stop has a value | Numeric total; complete coverage |
| Missing derived impact row | Partial subtotal; missing count >0 |
| Stored value is 0 | Numeric 0; counted as covered |
| Stored value is NULL / all rows absent | Not available / JSON null; incomplete coverage |
| Duplicate completed assignments at one stop | One contribution and one coverage unit |
| Historical/non-current completed stop | Included in total and coverage denominator |
| Assigned but incomplete | Excluded |
| Another reviewer's completed review | Excluded |

Fixture matrix: four distinct completed stops (including one inactive), three
covered values 10/0/20 and one missing row returned 30 with 3/4 coverage; duplicates,
pending work and the other reviewer did not contribute. Full profile and completion
API tests also passed zero/missing cases. Chrome displayed numeric `0` with `2 of 2`
coverage and `Not available` with `0 of 2` coverage, plus the partial `1 of 2` wording.
Historical estimates still use current mappings rather than review-time snapshots.

## 5. All six active multi-heading stops

Read-only population is exactly `stop_gtfs_status.current_gtfs=1`. It remains
7,117 active stops: 4,903 with trusted headings, 2,214 without, six with more than
one distinct heading. All trusted records below use `wmata_stop_code` identity
linkage. No road orientation was used, and no heading/member data was edited.
Classifications are evidence-based triage, not field verification.

| Physical stop | Name / jurisdiction | Trusted member ID → source stop ID → GTFS ID | Headings and labels | Routes on trusted members | Classification |
| --- | --- | --- | --- | --- | --- |
| 406 | Mississippi Av SE+4 St SE / DC, Ward 8.0, ANC 8C | 409 → 1000095 → 2135; 1030 → 1000094 → 2133 | 54° Northeast; 236° Southwest | 409: C17; 1030: C17 | likely data/linkage issue |
| 738 | Calvert St NW+Duke Ellington Bridge / DC, Ward 1.0, ANC 1C | 757 → 1001838 → 7206; 4208 → 1001832 → 7198 | 202° Southbound; 273° Westbound | 757: C53; 4208: C51, C53 | needs manual field/map verification |
| 837 | Surrey Service Dr+Park Berkshire Apt / MD, Prince George's, Suitland | 858 → 3003273 → 15103; 1767 → 3000698 → 16747 | 116° Southeast; 27° Northeast | 858: P66; 1767: P66 | needs manual field/map verification |
| 2192 | Falls Rd+Falls Farm Dr / MD, Montgomery, Potomac | 2283 → 2005418 → 17634; 2623 → 2001308 → 15463 | 0° Northbound; 226° Southwest | 2283: M82; 2623: M82 | needs manual field/map verification |
| 2231 | EAST FALLS CHURCH + BUS BAY F / VA, Arlington, Arlington | 2323 → 6000821 → 14082; 4292 → 6000799 → 14043 | 109° Eastbound; 298° Northwest | 2323: F20, F50; 4292: F20, F26 | likely data/linkage issue |
| 3263 | Princess Garden Pkwy+#6512 / MD, Prince George's, Seabrook | 3430 → 3003972 → 17227; 3505 → 3003971 → 17226 | 220° Southwest; 310° Northwest | 3430: P21; 3505: P21 | needs manual field/map verification |

Member structure and reasoning (includes members without a trusted heading):

- **406**: Four members span Mississippi Avenue and 4th Street; two trusted headings are nearly opposite on the same route. This looks like a physical-location grouping issue, not grounds to discard a heading. All routes: C15, C17. Members: 409/1000095 (Mississippi Av SE+4 St SE); 1030/1000094 (Mississippi Av SE+4 St SE); 7830/1004028 (4 St SE+Mississippi Av SE); 7829/1004027 (4 St SE+Mississippi Av SE).
- **738**: Two differently named corner/bridge members share C53; C51 appears only on one member. Could be corner geometry or separate boarding points. All routes: C51, C53. Members: 757/1001838 (Calvert St NW+Duke Ellington Bridge); 4208/1001832 (Calvert St NW+Biltmore St NW).
- **837**: Two service-road/apartment-roadway members on P66 have headings roughly 90 degrees apart. A loop/corner is plausible but shared boarding-location identity is unproven. All routes: P66. Members: 858/3003273 (Surrey Service Dr+Park Berkshire Apt); 1767/3000698 (Avenue Apt Roadwy+Surrey Service Dr).
- **2192**: Two members at the same intersection on M82 differ by 134 degrees. Check whether these are opposing boarding points; zero degrees is retained as a valid north heading. All routes: M82. Members: 2283/2005418 (Falls Rd+Falls Farm Dr); 2623/2001308 (Falls Rd+Falls Farm Dr).
- **2231**: Ten members name distinct bays A through G, while the physical stop is named Bay F; the trusted headings belong to Bay C and Bay B. Facility membership should not by itself collapse distinct boarding bays. All routes: F20, F26, F50. Members: 2323/6000821 (East Falls Church+Bay C); 7663/6001453 (EAST FALLS CHURCH + BUS BAY F); 7664/6001454 (EAST FALLS CHURCH + BUS BAY G); 6037/6000822 (East Falls Church+Bay D); 7662/6001452 (EAST FALLS CHURCH + BUS BAY E); 7661/6001451 (EAST FALLS CHURCH + BUS BAY D); 7660/6001450 (EAST FALLS CHURCH + BUS BAY C); 4292/6000799 (East Falls Church+Bay B); 7659/6001449 (EAST FALLS CHURCH + BUS BAY B); 7658/6001448 (EAST FALLS CHURCH + BAY A).
- **3263**: Two same-address P21 members differ by 90 degrees. Member names alone cannot establish a legitimate shared boarding location. All routes: P21. Members: 3430/3003972 (Princess Garden Pkwy+#6512); 3505/3003971 (Princess Garden Pkwy+#6512).

## 6. Browser/mobile validation

Found installed Chrome and Edge. Node, Playwright, Selenium, pyppeteer and a project browser harness were not
available. Used installed headless Chrome through its built-in DevTools protocol
with a small disposable Python/stdlib driver; no dependency was installed.
Flask served only the staging copy at `http://127.0.0.1:8765`.

Tested 320×568, 375×812, 390×844, 430×932 and 844×390 device emulation. Each size
covered dashboard/map, single-direction detail (7755), multiple-direction detail
(406), no-direction detail (407), review form, profile and completion: **35 page/state
checks**. Long selected route/county/ANC text and a long-name Leaflet popup were
injected as layout fixtures. Profile used a long reviewer name; a supplemental
70-route list also wrapped without page overflow.

Measured defects fixed and retested:

- Popup content plus Leaflet margins was 286px wide inside a 270px map at 320px.
  Mobile max-width now accounts for those margins: 246px popup inside the 270px map.
- More-specific filter rules kept text at 14px and controls at 42px. Final filter
  controls are at least 44px, and visible inputs/selects/textareas are at least 16px,
  including phone landscape.

Final measurements: no page-level horizontal overflow in all 35 states; popup
horizontal bounds within the map at all five sizes; white text on #1756a9, forced
hover state white on #123f7b; keyboard Tab showed a solid 3px focus outline. Popup
buttons measured 44px high. A final 320px check after initial map movement settled
also verified vertical containment before and after keyboard focus (popup top
187.53px/bottom 374.20px inside map top 182.20px/bottom 494.59px). An earlier fixture
opened during initial map movement and captured temporary title clipping; this
was not treated as a passed settled-layout check. Visited styling shares the explicit white-text rule;
Chrome privacy restrictions prevent treating computed-style reads as proof of
visited history. It was cascade-inspected, not claimed as independently measured.

One/multiple/unavailable serving-direction displays and photo absent/present
history rendered. Photo links include noopener/noreferrer. Review identity,
direction, Street View/Maps links precede essential questions; optional identity
and stewardship remain secondary. Remote/in-person mode switching passed at all
sizes. Valid URLs and malformed URL validity were checked; a javascript-scheme
submission produced the application's server-error alert (400), which was handled
in Chrome. Submit remained enabled, reachable and 44px high at all five sizes.
Completion renders successfully after retry and shows coverage wording.

Table containers have local `overflow-x:auto`; at landscape a 879px table scrolled
inside a 764px container without page overflow. Long route-list and zero/missing
coverage display checks also passed. At this pass, only the review form had a
separate Maps action. The later Street View investigation added primary
“Open in Google Maps” actions to both review and stop-detail pages.

Emulation does not validate a physical phone's keyboard, touch precision or iOS
zoom behavior. Existing map marker density and the remaining field checks below
were not redesigned. See the local artifacts under `.tmp/deployment_validation/`:
`browser_results_final.json`, `browser_supplement.json`, `popup_states.json`,
`dashboard-320.png`, `review-320.png`, `profile-320.png`, `multiple-320.png`.

## 7. Street View sanity

| Stop | State | Requested road viewpoint (lat, lon) | Camera heading | Transit headings | Result |
| --- | --- | --- | ---: | --- | --- |
| 7755 Porter St NW+#2724 | DC | 38.93588889, -77.05634834 | 204.09136° | 119° | Coordinate order and viewpoint→stop bearing passed; Google returned no imagery |
| 837 Surrey Service Dr+Park Berkshire Apt | MD | 38.84747857, -76.89868467 | 191.59278° | 27, 116° | Coordinate order and viewpoint→stop bearing passed; Google returned no imagery |
| 2231 EAST FALLS CHURCH + BUS BAY F | VA | 38.88628533, -77.15707905 | 23.38960° | 109, 298° | Coordinate order and viewpoint→stop bearing passed; Google returned no imagery |

All three URLs were opened in Chrome. Google displayed **“No Street View imagery
available here.”** Screenshots confirm this. Consequently visual stop-facing
alignment did NOT pass; no panorama was available to inspect. The no-road fixture
correctly returns null camera heading and omits `heading=`. The algorithm was not
changed based on this Google behavior. Exact URLs and outcomes are in
`streetview_results.json` and `streetview_browser.json` in the local artifact folder.

## 8. Validation and deployment decisions

- Full discovery: **265 tests passed**, exit 0, 20.304 seconds.
- Focused review workflow: 17; exposure/field audit: 8; reviewer auth/profile: 21;
  serving directions: 12; review-context UX: 10. All passed, exit 0.
- Python compilation passed for changed Python API/helpers/migration/tests.
- `git diff --check` passed (line-ending notices only).
- Node remains unavailable. Chrome's JS parser accepted all three changed external
  JS files; the rendered profile and completion scripts also executed successfully.
- The first sandbox suite run hit Windows temporary-directory permissions;
  the unrestricted full and focused reruns passed.

**Deployment gates:** run the explicit migration on the deployment database before
accepting photo URLs, then follow the deployment runbook's smoke tests. The later
Street View investigation established a working Maps fallback and made imagery
explicitly optional; Street View does not block in-person/other-visual review.
Guaranteed imagery and visual camera alignment remain unverified. Production
migration and deployment were deliberately not performed.

**Safe to defer within this scope:** independent review of the six multi-heading
identities (arrays/provenance are preserved), physical-phone keyboard/touch testing,
historical ridership snapshots, and all badge,
leaderboard, GTFS fallback and cloud-upload work. No direction-data repair was made.

Manual follow-up URLs/test records (serve staging only): `/dashboard`, `/stop/7755`,
`/stop/406`, `/stop/407`, `/review/7755?assignment_id=130&mode=map`, `/reviewer/profile`.
Use the staging smoke reviewer session to inspect photo history and incomplete
coverage; repeat the five viewport sizes on a physical phone, verify popup title
visibility during map movement, then open the three Street View URLs above.

## 9. Final working-tree state

The status includes pre-existing modifications. This pass did not stage or commit
anything. The diff statistics exclude untracked files.

`git status --short`:

```text
 M docs/serving-directions.md
 M scripts/active/create_review_tables.py
 M src/api/app.py
 M src/dashboard/static/dashboard.css
 M src/dashboard/static/review_info_loader.js
 M src/dashboard/static/stop_detail.js
 M src/dashboard/templates/feedback.html
 M src/dashboard/templates/pilot_reviewer_management.html
 M src/dashboard/templates/review.html
 M src/dashboard/templates/review_routes.html
 M src/dashboard/templates/reviewer_profile.html
 M src/dashboard/templates/reviewer_sign_in.html
 M src/dashboard/templates/stop_detail.html
 M src/dashboard/templates/survey.html
 M src/review/community_survey_v1.py
 M src/review/render_survey.py
 M tests/test_active_review_workflow.py
 M tests/test_reviewer_auth.py
 M tests/test_serving_directions.py
?? docs/reviewer-dashboard-audit.md
?? docs/reviewer-deployment-validation.md
?? src/dashboard/static/photo_links.js
?? src/review/attachments.py
?? src/spatial/camera_heading.py
?? tests/test_reviewer_field_audit.py
```

`git diff --stat`:

```text
 docs/serving-directions.md                    |  19 +-
 scripts/active/create_review_tables.py        |   9 +
 src/api/app.py                                | 542 +++++++++++---------------
 src/dashboard/static/dashboard.css            | 101 +++--
 src/dashboard/static/review_info_loader.js    |  12 +-
 src/dashboard/static/stop_detail.js           |   6 +-
 src/dashboard/templates/review.html           |  89 ++---
 src/dashboard/templates/review_routes.html    |   1 +
 src/dashboard/templates/reviewer_profile.html |  15 +-
 src/dashboard/templates/reviewer_sign_in.html |   3 +-
 src/dashboard/templates/stop_detail.html      |   2 +
 src/dashboard/templates/survey.html           |   2 +
 src/review/community_survey_v1.py             |   7 +
 src/review/render_survey.py                   |  10 +-
 tests/test_active_review_workflow.py          | 228 ++++++++++-
 tests/test_reviewer_auth.py                   |  26 +-
 tests/test_serving_directions.py              |   6 +-
 17 files changed, 644 insertions(+), 434 deletions(-)
```
