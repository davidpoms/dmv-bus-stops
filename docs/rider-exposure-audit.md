# Rider exposure fresh-copy audit — 2026-09-10

Source: repository production database `src/database/dmv_bus_stops.db`; a fresh
verified SQLite online backup was created at 17:02 UTC and all development
rehearsals used `.tmp/rider-exposure/rehearsal.db`. No remote production host
was accessed. Production SHA-256 before and after:

`D8858055D47AF67831B19E9009612A96D78CD7C56BB8A2A97A2C2D11F0172034`

## Data quality

- Active stops: 7,117; usable exposure: 7,115; unavailable: 2.
- Source period: 2026-07-31; 126 ridership records and 128 canonical serving route IDs.
- Bands: Very High 713; High 1,109; Moderate 2,460; Lower 2,833; Unavailable 2.
- Stored assessment versus independent source derivation: zero mismatches.
- Unavailable: stop 2757 (GROSVENOR STATION + BUS BAY F) and 6550 (Rockville Pk+Marinelli Rd).
- EXP and LCL have no matching ridership snapshots. Six active stops carry at least one of these routes; four still have a positive but potentially incomplete proxy.
- Distinct routes per stop: 1: 4,751; 2: 1,624; 3: 481; 4: 182; 5: 42; 6: 26; 7: 10; 8: 1.
- Top-20 overlap: 11 physical stops: 2224, 2527, 2572, 2772, 2919, 3229, 3705, 4627, 6080, 8144, 8145.
- Maximum route count is eight at Suitland Rdwy+Suitland Federal Ctr (3971). The largest exposure is 736,536 at Alabama Av SE+24 St SE (2527), with seven routes.
- These maxima reconcile to distinct route totals. They are plausible route-demand concentrations, but not validated stop boarding or transfer counts. Shared route combinations create tied high scores at multiple nearby stops; do not interpret them as duplicate physical identities.
- No fabricated ridership source, new normalization, or separate route-count multiplier was introduced.

## Top 20 by exposure

| Stop ID | Stop | Source-period route weekday boardings | Routes | Bench |
|---|---|---:|---:|---|
| 2527 | Alabama Av SE+24 St SE | 736,536 | 7 | unknown |
| 2572 | Alabama Av SE+24 St SE | 736,536 | 7 | unknown |
| 8144 | Alabama Av SE+Irving Pl SE | 736,536 | 7 | unknown |
| 8145 | Alabama Av SE+Jasper St SE | 736,536 | 7 | unknown |
| 6204 | Georgia Av NW+Butternut St NW | 728,020 | 4 | likely_yes |
| 6080 | MARTIN LUTHER KING JR AVE SE + TALBERT ST SE | 725,335 | 7 | unknown |
| 5972 | I St NW+15 St NW | 701,784 | 6 | likely_yes |
| 2919 | I St NW+18 St NW | 701,654 | 6 | likely_yes |
| 2772 | Alabama Av SE+Hartford St SE | 690,628 | 6 | unknown |
| 3229 | Alabama Av SE+25 St SE | 690,628 | 6 | unknown |
| 3705 | Alabama Av SE+Ainger Pl SE | 690,628 | 6 | unknown |
| 4627 | Alabama Av SE+Hartford St SE | 690,628 | 6 | unknown |
| 6079 | ML King Jr Av SE+U St SE | 679,427 | 6 | unknown |
| 6425 | ML King Jr Av SE+W St SE | 679,427 | 6 | likely_no |
| 6562 | ML King Jr Av SE+W St SE | 679,427 | 6 | unknown |
| 2224 | ML King Jr Av SE+5 St SE | 648,861 | 6 | unknown |
| 5533 | Pennsylvania Av NW+22 St NW | 647,604 | 4 | likely_yes |
| 4674 | 11 St SE+O St SE | 633,438 | 4 | likely_no |
| 5550 | Marion Barry Av SE+13 St SE | 631,293 | 4 | unknown |
| 6368 | Marion Barry Av SE+14 St SE | 631,293 | 4 | unknown |

## Top 20 by distinct route count

| Stop ID | Stop | Routes | Source-period route weekday boardings |
|---|---|---:|---:|
| 3971 | Suitland Rdwy+Suitland Federal Ctr | 8 | 428,602 |
| 900 | Harkins Rd+#7900 | 7 | 462,873 |
| 943 | Harkins Rd+Annapolis Rd | 7 | 462,873 |
| 2527 | Alabama Av SE+24 St SE | 7 | 736,536 |
| 2572 | Alabama Av SE+24 St SE | 7 | 736,536 |
| 2780 | Harkins Rd+Ellin Rd | 7 | 462,873 |
| 5924 | Harkins Rd+W Lanham Dr | 7 | 462,873 |
| 6080 | MARTIN LUTHER KING JR AVE SE + TALBERT ST SE | 7 | 725,335 |
| 7399 | Harkins Rd+W Lanham Dr | 7 | 462,873 |
| 8144 | Alabama Av SE+Irving Pl SE | 7 | 736,536 |
| 8145 | Alabama Av SE+Jasper St SE | 7 | 736,536 |
| 1729 | Wisconsin Av NW+Tenley Circle NW | 6 | 482,932 |
| 2224 | ML King Jr Av SE+5 St SE | 6 | 648,861 |
| 2632 | N Randolph St+Wilson Bl | 6 | 241,928 |
| 2772 | Alabama Av SE+Hartford St SE | 6 | 690,628 |
| 2919 | I St NW+18 St NW | 6 | 701,654 |
| 3229 | Alabama Av SE+25 St SE | 6 | 690,628 |
| 3705 | Alabama Av SE+Ainger Pl SE | 6 | 690,628 |
| 4189 | Massachusetts Av NE+1 St NE | 6 | 331,636 |
| 4627 | Alabama Av SE+Hartford St SE | 6 | 690,628 |

## Validation and performance

- Fresh-copy integrity check: `ok`; foreign-key violations: `0`.
- Bulk exposure derivation: approximately 0.22 seconds locally; first map API request approximately 0.30 seconds. This is a local measurement, not a PythonAnywhere load benchmark.
- Read-only allowlisted map payload contains no reviewer email/key, authentication/session/token/IP data. Seating additions contain only public exposure and route context.
- Rehearsal artifacts are local under `.tmp/rider-exposure/`; audit is reproducible using `scripts.diagnostics.audit_rider_exposure`.
- Interpretation materially depends on route-level totals. Stop-level boarding data and unique-person counts are unavailable. Additional routes contribute source ridership rather than a fixed count bonus.

## Rehearsal results

- All **244 Python tests pass**, including five new exposure tests covering current-only
  semantics, stale inactive rows, route/physical-stop deduplication, deterministic
  ranking, band boundaries, raw route-count independence, capped selection, API
  allowlisting, read-only behavior, and seating sort/workflow preservation.
- Existing regression coverage includes normal public map behavior, jurisdiction
  summaries, review/stop links, owner/admin permissions, feedback, and lightweight
  Flask import. An existing admin test's fixed August fixture date was changed to
  the current UTC time so its rolling seven-day assertions remain valid. Admin
  application code was not changed.
- Independent fresh-copy API rehearsal checked **all 128 routes**, matching each
  result against SQL serving-route membership, enforcing the 100-point cap and
  physical-stop uniqueness. Highest exposure matched the independent top-100 SQL
  ordering. All 7,117 seating rows were current and correctly sorted; high exposure
  included both unknown/verification and likely-absent/improvement workflows.
- Subsequent local map requests took **0.119–0.125 seconds**. No hosting load test
  is implied. There is no per-marker database request in exposure mode and no new
  runtime dependency or persistent cache requiring invalidation.
- Headless Chrome rehearsal covered **1280px, 390px and 320px** widths: default Off,
  normal map (7,117 points), Highest exposure (100), popups, stop/review links,
  C53/D10/EXP route selections, exposure sorting, and restoration of normal mode.
  No JavaScript errors. Map and controls fit within the viewport. Small-screen
  fixes are scoped to the map card, seating card, dropdowns and scrollable popups;
  the existing seating table retains horizontal scrolling.
- SQLite integrity remains `ok`; foreign-key violations remain zero. Production
  SHA before/after is identical as recorded above. Development used a fresh copy;
  no commit, merge, push or production write was performed.

## Changed files

- `src/scoring/exposure_map.py`
- `src/api/app.py`
- `src/dashboard/static/exposure_map.js`
- `src/dashboard/static/dashboard.js`
- `src/dashboard/static/dashboard.css`
- `src/dashboard/templates/dashboard.html`
- `scripts/diagnostics/audit_rider_exposure.py`
- `tests/test_rider_exposure_map.py`
- `tests/test_pilot_admin_dashboard.py` (date-dependent fixture only)
- `docs/TECHNICAL_HANDOFF.md`
- `docs/PILOT_READINESS.md`
- `docs/rider-exposure-audit.md`

Appropriate for the 10–20-person pilot as an explicitly labeled route-exposure aid.
The two unmatched route IDs and absence of observed stop boarding data remain
interpretation limitations, not silently estimated values.
