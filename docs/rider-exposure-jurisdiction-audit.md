# Rider exposure jurisdiction refinement audit — 2026-09-10

## Provenance and units

- Source file: `data/raw/ridership/wmata_ridership.csv`, tab-delimited fields `Route`, `Weekday`, `Sunday`, `Saturday`, `Monthly Total`.
- Ingestion: `src/ingestion/load_ridership.py` copies comma-stripped `Weekday` unchanged to `ridership_snapshots.weekday_boardings`; the assessment producer takes MAX per distinct route in the latest global `period`, then SUM across serving routes into `opportunity_assessments.combined_route_weekday_boardings`.
- All 126 retained CSV weekday values match the current snapshot. All 126 weekday/Saturday/Sunday sums reconcile to Monthly Total within one boarding. **The stored field is a monthly weekday boarding total, not a daily average and not a five-day total.**
- Example C53: weekday 292,652 + Saturday 59,845 + Sunday 36,715 = 389,212, versus exported monthly total 389,211 (one boarding rounding difference).
- The existing API `latest_ridership_weekdays()` and `src/assessment/generate_impact_summary.py` normalize by calendar Monday–Friday dates in the recorded month. The exposure popup now follows that convention: raw total / 23 for recorded period `2026-07-31`. No divide-by-five conversion is used.
- Daily label: **Estimated combined average weekday route boardings**. The divisor and “Not observed boarding activity at this stop” appear in the popup. The canonical raw score is unchanged across geography and route selections; daily conversion is for display only.
- Source limitation: the CSV retains no original export month/filter or holiday service-day counts. `period` is recorded as July 31; the import log is August 1, and the loader normally stamps import date. Thus this is a **calendar-weekday estimate based on the recorded month**, not an independently verified WMATA average service-day measure. A more precise claim would require the original export metadata/day counts. Missing/invalid period yields an unavailable daily display, not fabricated arithmetic.

[WMATA’s source portal](https://www.wmata.com/about/open-data-hub/ridership-data/metrobus-ridership-summary.html) documents filtered Summary versus Full Data exports. Its dashboard view name contains “AverageDailyBoardings,” but that name does not establish the units of this retained aggregate CSV. The reconciliation above establishes the retained values as totals; the agency page does not recover this file’s missing filter metadata.

## Fresh-copy safeguards and coverage

Source: repository production database `src/database/dmv_bus_stops.db`. A fresh verified online SQLite copy was made at 17:46 UTC on September 10. All rehearsals used `.tmp/exposure-refinement/rehearsal.db`; no remote production host was accessed. Production SHA-256 before and after:

`D8858055D47AF67831B19E9009612A96D78CD7C56BB8A2A97A2C2D11F0172034`

- Active population: **7,117**, using only `stop_gtfs_status.current_gtfs=1`.
- Usable raw exposure: **7,115**; unavailable: **2**. Existing EXP/LCL ridership gaps remain unfilled.
- SQLite integrity: `ok`; foreign-key violations: `0`.

| Dimension | Assigned active stops | Missing/blank | Distinct displayed values |
|---|---:|---:|---:|
| state | 7,117 | 0 | 3 |
| county | 4,773 | 2,344 | 6 |
| municipality | 4,884 | 2,233 | 130 |
| dc_ward | 2,399 | 4,718 | 8 |
| dc_anc | 2,399 | 4,718 | 46 |

Missing assignments are not inferred. These dimensions overlap independently; their counts must not be added as disjoint populations. Ward and ANC coverage is all 2,399 DC active stops, so 4,718 blanks in those dimensions are expected outside DC. County and municipality blanks are retained rather than filled from other dimensions.

Data-quality flags: ward labels `1`/`1.0` through `8`/`8.0` split the raw data into 16 labels. The presentation combines equivalent numeric labels into eight wards without updating any database row. There are **55 DC-state stops with county assignments**, and municipality includes `District of Columbia` for only a subset of DC stops. These deserve an upstream geography review; the exposure feature preserves them. The county field also contains independent-city labels such as Alexandria and Falls Church; it is not recast into a forced hierarchy.

## Comparison policy

Entire DMV retains its existing raw-score order and percentile denominator, including zero normalization for unavailable data. Jurisdiction percentiles use only positive usable exposure among current stops in that jurisdiction. The same numeric raw score and daily display value are retained. Rank is deterministic by raw score descending then physical-stop ID ascending; ties share their cumulative percentile. Route/bench filtering and map capping occur after population comparison.

Bands: Very High >=90; High >=75 and <90; Moderate >=40 and <75; Lower <40. With **fewer than 20 usable stops**, show **Small comparison group** with rank #X of Y usable stops and the separate DMV band; local percentile is null. This bounds percentile steps to at most five points for banded groups, not a statistical assurance. Unavailable data stays Unavailable. Tiny and all-unavailable groups remain selectable.

There are **61 groups below the 20-usable-stop threshold**. The tables below mark them explicitly.

## Complete active-stop counts by geography

### state

| Value | Active | Usable exposure | Band policy |
|---|---:|---:|---|
| DC | 2399 | 2399 | Percentile bands |
| MD | 2971 | 2969 | Percentile bands |
| VA | 1747 | 1747 | Percentile bands |

### county

| Value | Active | Usable exposure | Band policy |
|---|---:|---:|---|
| Alexandria | 273 | 273 | Percentile bands |
| Arlington | 473 | 473 | Percentile bands |
| Fairfax | 960 | 960 | Percentile bands |
| Falls Church | 41 | 41 | Percentile bands |
| Montgomery | 870 | 868 | Percentile bands |
| Prince George's | 2156 | 2156 | Percentile bands |

### municipality

| Value | Active | Usable exposure | Band policy |
|---|---:|---:|---|
| Adelphi | 45 | 45 | Percentile bands |
| Alexandria | 273 | 273 | Percentile bands |
| Andrews AFB | 1 | 1 | Rank only |
| Annandale | 91 | 91 | Percentile bands |
| Arlington | 473 | 473 | Percentile bands |
| Aspen Hill | 17 | 17 | Rank only |
| Bailey's Crossroads | 66 | 66 | Percentile bands |
| Belle Haven | 5 | 5 | Rank only |
| Beltsville | 79 | 79 | Percentile bands |
| Berwyn Heights | 17 | 17 | Rank only |
| Bethesda | 88 | 88 | Percentile bands |
| Bladensburg | 34 | 34 | Percentile bands |
| Bowie | 65 | 65 | Percentile bands |
| Brentwood | 22 | 22 | Percentile bands |
| Brock Hall | 9 | 9 | Rank only |
| Burke | 74 | 74 | Percentile bands |
| Burke Centre | 28 | 28 | Percentile bands |
| Burnt Mills | 5 | 5 | Rank only |
| Burtonsville | 14 | 14 | Rank only |
| Calverton | 43 | 43 | Percentile bands |
| Camp Springs | 50 | 50 | Percentile bands |
| Capitol Heights | 21 | 21 | Percentile bands |
| Cedar Heights | 1 | 1 | Rank only |
| Cheverly | 6 | 6 | Rank only |
| Chevy Chase | 28 | 28 | Percentile bands |
| Chevy Chase View | 4 | 4 | Rank only |
| Chevy Chase Village | 1 | 1 | Rank only |
| Chillum | 126 | 126 | Percentile bands |
| Colesville | 51 | 51 | Percentile bands |
| College Park | 86 | 86 | Percentile bands |
| Colmar Manor | 3 | 3 | Rank only |
| Coral Hills | 41 | 41 | Percentile bands |
| Cottage City | 7 | 7 | Rank only |
| District Heights | 39 | 39 | Percentile bands |
| District of Columbia | 233 | 233 | Percentile bands |
| East Riverdale | 30 | 30 | Percentile bands |
| Edmonston | 5 | 5 | Rank only |
| Fair Oaks | 26 | 26 | Percentile bands |
| Fairfax | 84 | 84 | Percentile bands |
| Fairland | 71 | 71 | Percentile bands |
| Fairmount Heights | 6 | 6 | Rank only |
| Falls Church | 41 | 41 | Percentile bands |
| Forest Glen | 6 | 6 | Rank only |
| Forest Heights | 19 | 19 | Rank only |
| Forestville | 31 | 31 | Percentile bands |
| Fort Belvoir | 13 | 13 | Rank only |
| Fort Hunt | 35 | 35 | Percentile bands |
| Fort Washington | 53 | 53 | Percentile bands |
| Four Corners | 23 | 23 | Percentile bands |
| Friendship Heights Village | 2 | 2 | Rank only |
| George Mason | 10 | 10 | Rank only |
| Glassmanor | 49 | 49 | Percentile bands |
| Glenarden | 23 | 23 | Percentile bands |
| Glenmont | 31 | 31 | Percentile bands |
| Glenn Dale | 15 | 15 | Rank only |
| Greenbelt | 158 | 158 | Percentile bands |
| Groveton | 3 | 3 | Rank only |
| Hillandale | 18 | 18 | Rank only |
| Hillcrest Heights | 34 | 34 | Percentile bands |
| Huntington | 11 | 11 | Rank only |
| Hyattsville | 94 | 94 | Percentile bands |
| Hybla Valley | 7 | 7 | Rank only |
| Idylwood | 16 | 16 | Rank only |
| Kemp Mill | 6 | 6 | Rank only |
| Kensington | 13 | 13 | Rank only |
| Kettering | 43 | 43 | Percentile bands |
| Kings Park | 25 | 25 | Percentile bands |
| Kings Park West | 41 | 41 | Percentile bands |
| Konterra | 16 | 16 | Rank only |
| Lake Arbor | 51 | 51 | Percentile bands |
| Lake Barcroft | 13 | 13 | Rank only |
| Landover | 41 | 41 | Percentile bands |
| Landover Hills | 10 | 10 | Rank only |
| Langley Park | 31 | 31 | Percentile bands |
| Lanham | 10 | 10 | Rank only |
| Largo | 15 | 15 | Rank only |
| Laurel | 44 | 44 | Percentile bands |
| Leisure World | 8 | 8 | Rank only |
| Lincolnia | 26 | 26 | Percentile bands |
| Long Branch | 22 | 22 | Percentile bands |
| Mantua | 13 | 13 | Rank only |
| Marlow Heights | 36 | 36 | Percentile bands |
| Maryland Park | 4 | 4 | Rank only |
| McLean | 25 | 25 | Percentile bands |
| Merrifield | 45 | 45 | Percentile bands |
| Mitchellville | 2 | 2 | Rank only |
| Morningside | 15 | 15 | Rank only |
| Mount Rainier | 13 | 13 | Rank only |
| Mount Vernon | 23 | 23 | Percentile bands |
| National Harbor | 12 | 12 | Rank only |
| New Carrollton | 63 | 63 | Percentile bands |
| North Bethesda | 44 | 42 | Percentile bands |
| North Brentwood | 3 | 3 | Rank only |
| North Chevy Chase | 1 | 1 | Rank only |
| North Kensington | 17 | 17 | Rank only |
| North Springfield | 5 | 5 | Rank only |
| Oakton | 38 | 38 | Percentile bands |
| Olney | 31 | 31 | Percentile bands |
| Oxon Hill | 40 | 40 | Percentile bands |
| Peppermill Village | 11 | 11 | Rank only |
| Pimmit Hills | 7 | 7 | Rank only |
| Potomac | 60 | 60 | Percentile bands |
| Ravensworth | 3 | 3 | Rank only |
| Riverdale Park | 48 | 48 | Percentile bands |
| Rockville | 26 | 26 | Percentile bands |
| Seabrook | 61 | 61 | Percentile bands |
| Seat Pleasant | 50 | 50 | Percentile bands |
| Seven Corners | 30 | 30 | Percentile bands |
| Silver Hill | 11 | 11 | Rank only |
| Silver Spring | 108 | 108 | Percentile bands |
| Somerset | 2 | 2 | Rank only |
| South Kensington | 8 | 8 | Rank only |
| South Laurel | 14 | 14 | Rank only |
| Springfield | 16 | 16 | Rank only |
| Suitland | 90 | 90 | Percentile bands |
| Summerfield | 25 | 25 | Percentile bands |
| Takoma Park | 40 | 40 | Percentile bands |
| Temple Hills | 29 | 29 | Percentile bands |
| Tysons | 12 | 12 | Rank only |
| University Park | 10 | 10 | Rank only |
| Wakefield | 17 | 17 | Rank only |
| Walker Mill | 46 | 46 | Percentile bands |
| West Falls Church | 42 | 42 | Percentile bands |
| West Springfield | 67 | 67 | Percentile bands |
| Westphalia | 2 | 2 | Rank only |
| Wheaton | 81 | 81 | Percentile bands |
| White Oak | 33 | 33 | Percentile bands |
| Woodburn | 16 | 16 | Rank only |
| Woodlawn | 10 | 10 | Rank only |
| Woodmore | 4 | 4 | Rank only |

### dc_ward

| Value | Active | Usable exposure | Band policy |
|---|---:|---:|---|
| 1 | 153 | 153 | Percentile bands |
| 2 | 294 | 294 | Percentile bands |
| 3 | 301 | 301 | Percentile bands |
| 4 | 303 | 303 | Percentile bands |
| 5 | 423 | 423 | Percentile bands |
| 6 | 197 | 197 | Percentile bands |
| 7 | 361 | 361 | Percentile bands |
| 8 | 367 | 367 | Percentile bands |

### dc_anc

| Value | Active | Usable exposure | Band policy |
|---|---:|---:|---|
| 1A | 32 | 32 | Percentile bands |
| 1B | 44 | 44 | Percentile bands |
| 1C | 25 | 25 | Percentile bands |
| 1D | 26 | 26 | Percentile bands |
| 1E | 26 | 26 | Percentile bands |
| 2A | 44 | 44 | Percentile bands |
| 2B | 39 | 39 | Percentile bands |
| 2C | 101 | 101 | Percentile bands |
| 2D | 13 | 13 | Rank only |
| 2E | 48 | 48 | Percentile bands |
| 2F | 22 | 22 | Percentile bands |
| 2G | 27 | 27 | Percentile bands |
| 3/4G | 58 | 58 | Percentile bands |
| 3A | 33 | 33 | Percentile bands |
| 3B | 27 | 27 | Percentile bands |
| 3C | 64 | 64 | Percentile bands |
| 3D | 67 | 67 | Percentile bands |
| 3E | 56 | 56 | Percentile bands |
| 3F | 34 | 34 | Percentile bands |
| 4A | 61 | 61 | Percentile bands |
| 4B | 78 | 78 | Percentile bands |
| 4C | 46 | 46 | Percentile bands |
| 4D | 37 | 37 | Percentile bands |
| 4E | 43 | 43 | Percentile bands |
| 5A | 68 | 68 | Percentile bands |
| 5B | 125 | 125 | Percentile bands |
| 5C | 79 | 79 | Percentile bands |
| 5D | 49 | 49 | Percentile bands |
| 5E | 49 | 49 | Percentile bands |
| 5F | 53 | 53 | Percentile bands |
| 6A | 43 | 43 | Percentile bands |
| 6B | 30 | 30 | Percentile bands |
| 6C | 35 | 35 | Percentile bands |
| 6D | 38 | 38 | Percentile bands |
| 6E | 49 | 49 | Percentile bands |
| 7B | 97 | 97 | Percentile bands |
| 7C | 93 | 93 | Percentile bands |
| 7D | 67 | 67 | Percentile bands |
| 7E | 41 | 41 | Percentile bands |
| 7F | 63 | 63 | Percentile bands |
| 8A | 54 | 54 | Percentile bands |
| 8B | 54 | 54 | Percentile bands |
| 8C | 106 | 106 | Percentile bands |
| 8D | 55 | 55 | Percentile bands |
| 8E | 87 | 87 | Percentile bands |
| 8F | 13 | 13 | Rank only |

## Regional versus jurisdiction examples

| Stop | Jurisdiction | DMV band | Local band | Local rank / active population | Raw exposure | Daily estimate |
|---|---|---|---|---|---:|---:|
| 54: Veirs Mill Rd+Gail St | state: MD | High | Very High | 257 / 2971 | 163,967 | 7,129 |
| 789: Seminary Rd+Gorham St | state: VA | High | Very High | 120 / 1747 | 156,223 | 6,792 |
| 1683: Seminary Rd+#4647 | county: Alexandria | High | Very High | 28 / 273 | 156,223 | 6,792 |
| 1151: Columbia Pk+S Joyce St | county: Arlington | High | Very High | 37 / 473 | 161,792 | 7,034 |
| 325: Arlington Bl+Jaguar Tr | county: Fairfax | Moderate | Very High | 88 / 960 | 89,442 | 3,889 |
| 154: Roosevelt Bl+Wilson Bl | county: Falls Church | High | Very High | 5 / 41 | 169,351 | 7,363 |
| 47: Georgia Av+Bel Pre Rd | county: Montgomery | High | Very High | 53 / 870 | 193,487 | 8,412 |
| 663: Silver Hill Rd+Porter Av | county: Prince George's | High | Very High | 215 / 2156 | 150,077 | 6,525 |

Local rank uses the usable population; the table reports active population for context. Montgomery has 868 usable stops of 870 active; the other example groups have full usable coverage.

## Top 10 exposure stops by comparison

### DMV

| Stop ID | Stop | Raw exposure | Daily estimate | DMV band | Local band |
|---|---|---:|---:|---|---|
| 2527 | Alabama Av SE+24 St SE | 736,536 | 32,023 | Very High | — |
| 2572 | Alabama Av SE+24 St SE | 736,536 | 32,023 | Very High | — |
| 8144 | Alabama Av SE+Irving Pl SE | 736,536 | 32,023 | Very High | — |
| 8145 | Alabama Av SE+Jasper St SE | 736,536 | 32,023 | Very High | — |
| 6204 | Georgia Av NW+Butternut St NW | 728,020 | 31,653 | Very High | — |
| 6080 | MARTIN LUTHER KING JR AVE SE + TALBERT ST SE | 725,335 | 31,536 | Very High | — |
| 5972 | I St NW+15 St NW | 701,784 | 30,512 | Very High | — |
| 2919 | I St NW+18 St NW | 701,654 | 30,507 | Very High | — |
| 2772 | Alabama Av SE+Hartford St SE | 690,628 | 30,027 | Very High | — |
| 3229 | Alabama Av SE+25 St SE | 690,628 | 30,027 | Very High | — |

### state: DC

| Stop ID | Stop | Raw exposure | Daily estimate | DMV band | Local band |
|---|---|---:|---:|---|---|
| 2527 | Alabama Av SE+24 St SE | 736,536 | 32,023 | Very High | Very High |
| 2572 | Alabama Av SE+24 St SE | 736,536 | 32,023 | Very High | Very High |
| 8144 | Alabama Av SE+Irving Pl SE | 736,536 | 32,023 | Very High | Very High |
| 8145 | Alabama Av SE+Jasper St SE | 736,536 | 32,023 | Very High | Very High |
| 6204 | Georgia Av NW+Butternut St NW | 728,020 | 31,653 | Very High | Very High |
| 6080 | MARTIN LUTHER KING JR AVE SE + TALBERT ST SE | 725,335 | 31,536 | Very High | Very High |
| 5972 | I St NW+15 St NW | 701,784 | 30,512 | Very High | Very High |
| 2919 | I St NW+18 St NW | 701,654 | 30,507 | Very High | Very High |
| 2772 | Alabama Av SE+Hartford St SE | 690,628 | 30,027 | Very High | Very High |
| 3229 | Alabama Av SE+25 St SE | 690,628 | 30,027 | Very High | Very High |

### state: MD

| Stop ID | Stop | Raw exposure | Daily estimate | DMV band | Local band |
|---|---|---:|---:|---|---|
| 900 | Harkins Rd+#7900 | 462,873 | 20,125 | Very High | Very High |
| 943 | Harkins Rd+Annapolis Rd | 462,873 | 20,125 | Very High | Very High |
| 2780 | Harkins Rd+Ellin Rd | 462,873 | 20,125 | Very High | Very High |
| 5924 | Harkins Rd+W Lanham Dr | 462,873 | 20,125 | Very High | Very High |
| 7399 | Harkins Rd+W Lanham Dr | 462,873 | 20,125 | Very High | Very High |
| 1741 | East-West Hwy+23 Av | 447,053 | 19,437 | Very High | Very High |
| 3646 | East-West Hwy+19 Pl | 447,053 | 19,437 | Very High | Very High |
| 4841 | East-West Hwy+Ager Rd | 447,053 | 19,437 | Very High | Very High |
| 6172 | East-West Hwy+Ager Rd | 447,053 | 19,437 | Very High | Very High |
| 3971 | Suitland Rdwy+Suitland Federal Ctr | 428,602 | 18,635 | Very High | Very High |

### state: VA

| Stop ID | Stop | Raw exposure | Daily estimate | DMV band | Local band |
|---|---|---:|---:|---|---|
| 1267 | Leesburg Pk+Patrick Henry Dr | 287,441 | 12,497 | Very High | Very High |
| 4820 | Leesburg Pk+Castle Rd | 287,441 | 12,497 | Very High | Very High |
| 716 | Seminary Rd+#5501 | 269,134 | 11,701 | Very High | Very High |
| 4561 | Seminary Rd+Magnolia Ln | 269,134 | 11,701 | Very High | Very High |
| 3996 | Castle Rd+Leesburg Pk | 258,793 | 11,252 | Very High | Very High |
| 6944 | Leesburg Pk+Sleepy Hollow Rd | 258,793 | 11,252 | Very High | Very High |
| 2632 | N Randolph St+Wilson Bl | 241,928 | 10,519 | Very High | Very High |
| 5224 | Wilson Bl+N Randolph St | 241,928 | 10,519 | Very High | Very High |
| 1823 | Beauregard St+Hermitage Hill Apt | 231,654 | 10,072 | Very High | Very High |
| 5610 | Southern Towers Rd+Graham Bldg | 231,654 | 10,072 | Very High | Very High |

### county: Alexandria

| Stop ID | Stop | Raw exposure | Daily estimate | DMV band | Local band |
|---|---|---:|---:|---|---|
| 1823 | Beauregard St+Hermitage Hill Apt | 231,654 | 10,072 | Very High | Very High |
| 5610 | Southern Towers Rd+Graham Bldg | 231,654 | 10,072 | Very High | Very High |
| 6162 | Southern Towers Rd+Sherwood Bldg | 231,654 | 10,072 | Very High | Very High |
| 6635 | Southern Towers Rd+Sherwood Bldg | 231,654 | 10,072 | Very High | Very High |
| 8235 | Southern Towers Rd+Stratford Bldg | 231,654 | 10,072 | Very High | Very High |
| 8236 | Southern Towers Rd+Stratford Bldg | 231,654 | 10,072 | Very High | Very High |
| 2232 | Duke St+S Earley St | 200,815 | 8,731 | High | Very High |
| 2247 | Duke St+S Jordan St | 200,815 | 8,731 | High | Very High |
| 4816 | Duke St+Alexandria Commons | 200,815 | 8,731 | High | Very High |
| 4975 | Duke St+Alexandria Commons | 200,815 | 8,731 | High | Very High |

### county: Arlington

| Stop ID | Stop | Raw exposure | Daily estimate | DMV band | Local band |
|---|---|---:|---:|---|---|
| 2632 | N Randolph St+Wilson Bl | 241,928 | 10,519 | Very High | Very High |
| 5224 | Wilson Bl+N Randolph St | 241,928 | 10,519 | Very High | Very High |
| 3362 | 15 St S+S Eads St | 206,922 | 8,997 | High | Very High |
| 5376 | 15 St S+S Grant St | 206,922 | 8,997 | High | Very High |
| 8211 | 15 St S+S Fern St | 206,922 | 8,997 | High | Very High |
| 8212 | 15 St S+S Fern St | 206,922 | 8,997 | High | Very High |
| 2231 | EAST FALLS CHURCH + BUS BAY F | 199,927 | 8,692 | High | Very High |
| 1421 | Army-Navy Dr+S Hayes St | 191,250 | 8,315 | High | Very High |
| 5822 | Army-Navy Dr+S Joyce St | 191,250 | 8,315 | High | Very High |
| 5760 | Columbia Pk+S Taylor St | 189,214 | 8,227 | High | Very High |

### county: Fairfax

| Stop ID | Stop | Raw exposure | Daily estimate | DMV band | Local band |
|---|---|---:|---:|---|---|
| 1267 | Leesburg Pk+Patrick Henry Dr | 287,441 | 12,497 | Very High | Very High |
| 4820 | Leesburg Pk+Castle Rd | 287,441 | 12,497 | Very High | Very High |
| 716 | Seminary Rd+#5501 | 269,134 | 11,701 | Very High | Very High |
| 4561 | Seminary Rd+Magnolia Ln | 269,134 | 11,701 | Very High | Very High |
| 3996 | Castle Rd+Leesburg Pk | 258,793 | 11,252 | Very High | Very High |
| 6944 | Leesburg Pk+Sleepy Hollow Rd | 258,793 | 11,252 | Very High | Very High |
| 3585 | Columbia Pk+Carlin Hill Dr | 217,932 | 9,475 | Very High | Very High |
| 5893 | Columbia Pk+Moray Ln | 217,932 | 9,475 | Very High | Very High |
| 5894 | Columbia Pk+Carlin Springs Rd | 217,932 | 9,475 | Very High | Very High |
| 6229 | Columbia Pk+Carlin Hill Dr | 217,932 | 9,475 | Very High | Very High |

### county: Falls Church

| Stop ID | Stop | Raw exposure | Daily estimate | DMV band | Local band |
|---|---|---:|---:|---|---|
| 1127 | N Washington St+Park Av | 186,799 | 8,122 | High | Very High |
| 1678 | N Washington St+Columbia St | 186,799 | 8,122 | High | Very High |
| 2873 | N Washington St+Columbia St | 186,799 | 8,122 | High | Very High |
| 5944 | N Washington St+Park Pl | 186,799 | 8,122 | High | Very High |
| 154 | Roosevelt Bl+Wilson Bl | 169,351 | 7,363 | High | Very High |
| 4757 | Roosevelt Bl+Oakwood Apt | 169,351 | 7,363 | High | Very High |
| 6014 | Roosevelt Bl+Roosevelt Towers | 169,351 | 7,363 | High | Very High |
| 7356 | Roosevelt Bl+N Roosevelt St | 169,351 | 7,363 | High | Very High |
| 7357 | Roosevelt Bl+N Roosevelt St | 169,351 | 7,363 | High | Very High |
| 2567 | W Broad St+S Oak St | 156,223 | 6,792 | High | High |

### county: Montgomery

| Stop ID | Stop | Raw exposure | Daily estimate | DMV band | Local band |
|---|---|---:|---:|---|---|
| 2564 | PLUM ORCHARD DR + BROADBIRCH DR | 382,727 | 16,640 | Very High | Very High |
| 4843 | PLUM ORCHARD DR + POST OFFICE ANNEX | 382,727 | 16,640 | Very High | Very High |
| 6769 | Plum Orchard Dr+Adventist Medical Ctr | 382,727 | 16,640 | Very High | Very High |
| 1477 | Georgia Av+Blair Rd | 380,349 | 16,537 | Very High | Very High |
| 8 | Broadbirch Dr+Bournefield Wy | 357,479 | 15,543 | Very High | Very High |
| 3818 | Broadbirch Dr+Bournefield Wy | 357,479 | 15,543 | Very High | Very High |
| 3960 | Broadbirch Dr+Plum Orchard Dr | 357,479 | 15,543 | Very High | Very High |
| 2502 | Veirs Mill Rd+University Bl | 357,454 | 15,541 | Very High | Very High |
| 2960 | Wayne Av+Dixon Av | 352,721 | 15,336 | Very High | Very High |
| 847 | Georgia Av+Judson Rd | 334,375 | 14,538 | Very High | Very High |

### county: Prince George's

| Stop ID | Stop | Raw exposure | Daily estimate | DMV band | Local band |
|---|---|---:|---:|---|---|
| 900 | Harkins Rd+#7900 | 462,873 | 20,125 | Very High | Very High |
| 943 | Harkins Rd+Annapolis Rd | 462,873 | 20,125 | Very High | Very High |
| 2780 | Harkins Rd+Ellin Rd | 462,873 | 20,125 | Very High | Very High |
| 5924 | Harkins Rd+W Lanham Dr | 462,873 | 20,125 | Very High | Very High |
| 7399 | Harkins Rd+W Lanham Dr | 462,873 | 20,125 | Very High | Very High |
| 1741 | East-West Hwy+23 Av | 447,053 | 19,437 | Very High | Very High |
| 3646 | East-West Hwy+19 Pl | 447,053 | 19,437 | Very High | Very High |
| 4841 | East-West Hwy+Ager Rd | 447,053 | 19,437 | Very High | Very High |
| 6172 | East-West Hwy+Ager Rd | 447,053 | 19,437 | Very High | Very High |
| 3971 | Suitland Rdwy+Suitland Federal Ctr | 428,602 | 18,635 | Very High | Very High |

## Verification and performance

- Full regression suite: **248 tests pass**. Nine exposure tests cover daily conversion, geography validation, independent dimensions, active-only membership, local denominators, raw-value invariance, ties, unavailable data, tiny groups, route deduplication, and seating workflow preservation. Existing owner/admin/feedback, normal dashboard, jurisdiction rows, and lightweight-import tests remain passing.
- Independent fresh-copy API rehearsal: all **193 geography groups** matched independent SQL membership, sorting, raw scores, and percentile calculations. Regional top 100 matched the existing raw ranking. Route plus geography combinations retained all serving-route exposure. Public payloads passed recursive private-field checks.
- Local endpoint timings: approximately **0.15–0.21 seconds**, similar to the original feature. No per-popup fetch, new runtime dependency, geography SQL identifier interpolation, database migration, or production write. Comparisons are bulk reads plus standard-Python grouping/ranking. This is not a PythonAnywhere load benchmark.
- Headless Chrome: **1280px, 390px, 320px**. All five comparison dimensions, tiny municipality, county popups, daily wording, route/geography combination, Prince George's likely-absent seating sort, Arlington unknown/verification sort, stop/review links and restoration of Off mode passed with no JavaScript errors. The new controls fit existing scoped mobile styles.
- Exposure comparison controls are hidden when Off. Seating comparison is independent from map selection. Source evidence, physical identity and amenity synthesis are unchanged.

## Changed files

- `src/scoring/exposure_map.py`
- `src/api/app.py`
- `src/dashboard/static/exposure_map.js`
- `src/dashboard/static/dashboard.js`
- `src/dashboard/templates/dashboard.html`
- `src/ingestion/load_ridership.py` (provenance comment only)
- `tests/test_rider_exposure_map.py`
- `scripts/diagnostics/audit_exposure_jurisdictions.py`
- `docs/TECHNICAL_HANDOFF.md`
- `docs/PILOT_READINESS.md`
- `docs/rider-exposure-audit.md` (link to refinement)
- `docs/rider-exposure-jurisdiction-audit.md`

Jurisdiction-relative exposure is a comparison aid, not an official agency priority ranking. Daily estimates remain route-level proxies; original service-day averages cannot be recovered from the retained export alone. No commit, merge, push or production modification was performed.
