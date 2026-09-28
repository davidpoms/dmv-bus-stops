# Final Street View investigation — 2026-09-28

## Finding and release decision

Google reported no imagery for all three samples using the generated road-point
URL, the road point without heading, an encoded road-point URL, and the actual
stop coordinate without heading. Ordinary Maps coordinate searches opened the
intended locations. The best-supported finding is unsuccessful panorama selection
in this Chrome environment, not a demonstrated coordinate-order or heading bug.
Actual coverage remains **inconclusive**: these results cannot distinguish absent
nearby imagery from Google/browser/session/service behavior. They do not establish
that the surrounding stops have no imagery. No metadata service or API key was used.

Street View need not block deployment of the in-person/other-visual review workflow
with the fallback implemented here. It remains unsuitable as a guaranteed remote
imagery source. A pilot requiring Street View for every assignment must first
verify imagery manually in its supported browser/device.

## Trace and documented semantics

`src/api/app.py:streetview_for_stop(latitude, longitude)` calls
`get_road_index().nearest_road(longitude, latitude)`. The cached index loads
`geometry, road_class` from `road_centerlines`. `RoadSpatialIndex` constructs a
KD-tree of segment midpoints in approximate local Cartesian coordinates, considers
eight nearby midpoints, and selects the closest projected point on those candidate
segments. This is a geometric estimate, not a Google imagery lookup or a guarantee
of the globally nearest segment. Its metadata is `road_class`, `distance_m`,
`road_lat`, `road_lon`, and segment `heading`; it does not retain road names/IDs.

The selected road point becomes `viewpoint=latitude,longitude`.
`bearing_to_stop` computes the initial spherical bearing from that road point to
the stop. That becomes `streetview_camera_heading` and the optional `heading=`.
It is neither the segment orientation nor transit serving direction. Without a
road point the helper uses the actual stop coordinate and omits heading. Coincident
points also omit heading. `/stops/<id>` passes row[1], row[2];
`/review/<id>/info` passes row[2], row[3]; both are latitude then longitude.

Google's [Maps URLs documentation](https://developers.google.com/maps/documentation/urls/get-started)
defines `viewpoint` as a location used to select the nearest photographed panorama;
it does not require a panorama exactly at that point. Heading controls orientation,
not coverage. Snapping can change the real camera location, so the calculated
road-to-stop bearing cannot guarantee the resulting camera faces the stop.
No coverage guarantee or search-radius parameter is documented for this URL.
Maps URLs need no API key. The documented encoded-comma construction also failed
in the browser experiment; encoding was not an observed remedy.

Other constructions: the review-queue JSON in `app.py` emits stop-coordinate pano
URLs without heading; `review_stop.js` also builds that form but is explicitly
disabled in the current review template. Legacy `survey.js` consumes the supplied
URL and has stale road-heading presentation, but `/survey/<id>` has no current
route in `app.py`; neither legacy script is used by the active review/stop pages.
They were left unchanged. Current `review_info_loader.js` and `stop_detail.js`
consume the shared API panorama URL.

## Browser experiment

Installed headless Chrome opened only public documented Maps URLs, waited eight
seconds per variant, and recorded rendered text, final navigation URL and a
screenshot. No private API, scraping pipeline, invented pano ID, photo retrieval,
or external lookup infrastructure was introduced. Screenshots were visually
inspected for all three stop-coordinate failures and all three Maps results.
The browser observations are distinct from programmatic bearing/coordinate tests.

| Physical stop | Road distance | Road + heading | Road, no heading | Encoded road + heading | Stop, no heading | Maps search |
|---|---:|---|---|---|---|---|
| 7755 DC | 5.225 m | No imagery | No imagery | No imagery | No imagery | Correct coordinates |
| 837 MD | 12.210 m | No imagery | No imagery | No imagery | No imagery | Correct coordinates |
| 2231 VA | 34.503 m | No imagery | No imagery | No imagery | No imagery | Correct coordinates |

Google's final panorama navigation retained the requested location and heading
but showed “No Street View imagery available here.” There is no positive evidence
of stop-only coverage or a heading-dependent failure. Maps screenshots show the
coordinate place panel and surrounding streets in Washington, Suitland-Silver Hill,
and Arlington respectively. We did not validate panorama coverage by walking
Pegman around the area or on physical phones.

## Narrow changes

Panorama coordinates/heading and generated URLs are **unchanged**. There was no
demonstrated alternative panorama construction that worked better.

- `review_info_loader.js`: actual-stop Maps search is now the first reference
  action; optional imagery reads “Try Street View” and includes a fallback caveat.
- `stop_detail.js`: adds the independent actual-stop Maps search before optional
  Street View, removes the dead `#` fallback, and sets safe new-tab attributes.
- `nearest_road.py`: corrects only its misleading module description of segment
  heading. No spatial algorithm or direction data changed.
- `tests/test_streetview_links.py`: two regression checks protect Maps coordinate
  source, ordering, optional imagery and caveat. Existing bearing tests remain.

The caveat directs reviewers to Maps for location and to in-person or another
visual source for evidence. No Google failure is a submission prerequisite, and
no imagery absence is interpreted as an amenity observation.

## Exact sample URLs and validation record

The following generated appendix records before/after URLs (unchanged panorama,
new/promoted Maps action), every tested variant, road metadata, final checks,
and the complete working-tree status/stat. Local detailed browser artifacts remain
under `.tmp/deployment_validation/` and are not release dependencies.

### Stop 7755 (DC)
Actual stop: `38.935845999953386,-77.05637299940237`.
Road metadata: `{"heading": 294.10469913476055, "distance_m": 5.2250836647743135, "road_class": "1", "road_lat": 38.935888892737175, "road_lon": -77.05634834283994}`.
Before and after panorama URL (unchanged):

```text
https://www.google.com/maps/@?api=1&map_action=pano&viewpoint=38.935888892737175,-77.05634834283994&heading=204.09136409059505
```
road_heading (tested variant):

```text
https://www.google.com/maps/@?api=1&map_action=pano&viewpoint=38.935888892737175,-77.05634834283994&heading=204.09136409059505
```
road_no_heading (tested variant):

```text
https://www.google.com/maps/@?api=1&map_action=pano&viewpoint=38.935888892737175,-77.05634834283994
```
road_encoded (tested variant):

```text
https://www.google.com/maps/@?api=1&map_action=pano&viewpoint=38.935888892737175%2C-77.05634834283994&heading=204.09136409059505
```
stop_no_heading (tested variant):

```text
https://www.google.com/maps/@?api=1&map_action=pano&viewpoint=38.935845999953386%2C-77.05637299940237
```
maps (primary Maps action after change):

```text
https://www.google.com/maps/search/?api=1&query=38.935845999953386%2C-77.05637299940237
```

### Stop 837 (MD)
Actual stop: `38.8473710002392,-76.898712999814`.
Road metadata: `{"heading": 115.89202937565119, "distance_m": 12.209647825392347, "road_class": "C", "road_lat": 38.84747856700005, "road_lon": -76.89868466699994}`.
Before and after panorama URL (unchanged):

```text
https://www.google.com/maps/@?api=1&map_action=pano&viewpoint=38.84747856700005,-76.89868466699994&heading=191.59277652685336
```
road_heading (tested variant):

```text
https://www.google.com/maps/@?api=1&map_action=pano&viewpoint=38.84747856700005,-76.89868466699994&heading=191.59277652685336
```
road_no_heading (tested variant):

```text
https://www.google.com/maps/@?api=1&map_action=pano&viewpoint=38.84747856700005,-76.89868466699994
```
road_encoded (tested variant):

```text
https://www.google.com/maps/@?api=1&map_action=pano&viewpoint=38.84747856700005%2C-76.89868466699994&heading=191.59277652685336
```
stop_no_heading (tested variant):

```text
https://www.google.com/maps/@?api=1&map_action=pano&viewpoint=38.8473710002392%2C-76.898712999814
```
maps (primary Maps action after change):

```text
https://www.google.com/maps/search/?api=1&query=38.8473710002392%2C-76.898712999814
```

### Stop 2231 (VA)
Actual stop: `38.886570130106854,-77.15692079910946`.
Road metadata: `{"heading": 293.38815687605677, "distance_m": 34.50289822541021, "road_class": "INT", "road_lat": 38.886285332705526, "road_lon": -77.15707905074841}`.
Before and after panorama URL (unchanged):

```text
https://www.google.com/maps/@?api=1&map_action=pano&viewpoint=38.886285332705526,-77.15707905074841&heading=23.389604612072148
```
road_heading (tested variant):

```text
https://www.google.com/maps/@?api=1&map_action=pano&viewpoint=38.886285332705526,-77.15707905074841&heading=23.389604612072148
```
road_no_heading (tested variant):

```text
https://www.google.com/maps/@?api=1&map_action=pano&viewpoint=38.886285332705526,-77.15707905074841
```
road_encoded (tested variant):

```text
https://www.google.com/maps/@?api=1&map_action=pano&viewpoint=38.886285332705526%2C-77.15707905074841&heading=23.389604612072148
```
stop_no_heading (tested variant):

```text
https://www.google.com/maps/@?api=1&map_action=pano&viewpoint=38.886570130106854%2C-77.15692079910946
```
maps (primary Maps action after change):

```text
https://www.google.com/maps/search/?api=1&query=38.886570130106854%2C-77.15692079910946
```

### Final validation

- Full unit suite: **267 passed**. Initial sandbox attempt could not access
  temporary test DBs; the approved unrestricted rerun passed (24.149 seconds).
- Focused suites passed: active workflow 17, field audit 8, auth 21, serving
  directions 12, review context UX 10, new Street View links 2. These are subsets
  of the full suite, not additional tests in the total.
- `python -m compileall -q src scripts/active/create_review_tables.py tests` passed.
- `git diff --check` passed (only existing LF/CRLF conversion notices).
- Chrome: **30 stop/review page cases passed**: IDs 7755, 837, 2231, 407 (no trusted
  direction), 406 (multiple), each at 320x568, 390x844 and 844x390. Exact Maps query
  coordinates, action order, new-tab safety, caveat, no horizontal page overflow,
  in-person mode and submit control checked. Both APIs agreed on panorama URLs.
  Chrome parsed both changed JavaScript files. Node was not used.
- Visual inspection: 320px review and stop action screenshots are readable and
  correctly ordered. External Google screenshots confirm the three coordinate
  panels and three no-imagery messages. Physical mobile devices, installed Google
  Maps app handoff, live-host deployment, and real mobile keyboards remain manual.
- Existing prior five-viewport dashboard checks are in the linked deployment
  validation report; dashboard code was not changed in this follow-up.
- Live repository DB SHA-256 remains
  `d8858055d47af67831b19e9009612a96d78cd7c56bb8a2a97a2c2d11f0172034`.
  All application browser checks used the disposable staging copy. No commit,
  production migration or deployment was performed.

### Working tree at completion

This includes preserved earlier work, not just this follow-up. Untracked files
are listed by status and excluded from the tracked diff stat.

`git status --short`

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
 M src/spatial/nearest_road.py
 M tests/test_active_review_workflow.py
 M tests/test_reviewer_auth.py
 M tests/test_serving_directions.py
?? docs/reviewer-dashboard-audit.md
?? docs/reviewer-deployment-runbook.md
?? docs/reviewer-deployment-validation.md
?? docs/reviewer-streetview-investigation.md
?? src/dashboard/static/photo_links.js
?? src/review/attachments.py
?? src/spatial/camera_heading.py
?? tests/test_reviewer_field_audit.py
?? tests/test_streetview_links.py
```

`git diff --stat`

```text
 docs/serving-directions.md                    |  19 +-
 scripts/active/create_review_tables.py        |   9 +
 src/api/app.py                                | 542 +++++++++++---------------
 src/dashboard/static/dashboard.css            | 101 +++--
 src/dashboard/static/review_info_loader.js    |  14 +-
 src/dashboard/static/stop_detail.js           |  23 +-
 src/dashboard/templates/review.html           |  89 ++---
 src/dashboard/templates/review_routes.html    |   1 +
 src/dashboard/templates/reviewer_profile.html |  15 +-
 src/dashboard/templates/reviewer_sign_in.html |   3 +-
 src/dashboard/templates/stop_detail.html      |   2 +
 src/dashboard/templates/survey.html           |   2 +
 src/review/community_survey_v1.py             |   7 +
 src/review/render_survey.py                   |  10 +-
 src/spatial/nearest_road.py                   |   2 +-
 tests/test_active_review_workflow.py          | 228 ++++++++++-
 tests/test_reviewer_auth.py                   |  26 +-
 tests/test_serving_directions.py              |   6 +-
 18 files changed, 660 insertions(+), 439 deletions(-)
```
