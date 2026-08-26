# Database Schema Guide

This guide describes the current conceptual schema. The executable baseline is
`src/database/schema.sql`; existing databases may require active idempotent
migrations because SQLite does not retroactively apply new column definitions.

Important: `schema.sql` is not yet a complete bootstrap of every evolved table.
For example, several mature observation fields and tables such as
`community_stewardships`, `physical_stops`, source evidence, consensus, and
opportunity assessments originated in separate producers or migrations. Inspect
`PRAGMA table_info` on the target database and run active migrations; do not
assume executing `schema.sql` alone recreates production.

## Design boundaries

The database deliberately separates:

1. source stop and route records
2. canonical physical-stop identity and current status
3. source evidence and human observations
4. derived consensus and canonical synthesis
5. prioritization, opportunities, and recommendations
6. review assignments and historical workflow state

Do not use a downstream score as evidence or a source field as canonical truth.

## Stop and service identity

### `bus_stops`, `routes`, `stop_routes`

Agency/GTFS stop records, route identities, and their many-to-many relationship.

### `physical_stops`, `physical_stop_members`

Canonical physical locations and the source stop records clustered into each
location. `physical_stop_id` is the public and analytical stop identity.

### `gtfs_feed_snapshots`, `gtfs_stop_structure`

Immutable source-level GTFS metadata is keyed by feed ID plus ZIP SHA-256; stop IDs
are unique only within a snapshot. Source values including `parent_station`,
`platform_code`, `location_type`, `stop_code`, `zone_id`, and
`wheelchair_boarding` are retained faithfully. Quality flags expose unresolved
parents or malformed coordinates. This metadata does not change physical IDs.

### `stop_gtfs_status`

Current service scope. The only active-stop predicate is:

```sql
current_gtfs = 1
```

Historical physical stops may remain even when they are not current.

### `stop_jurisdiction` and boundary tables

State, county, municipality, ward, ANC, and other geographic associations.
These dimensions overlap intentionally.

## Source evidence

### `stop_amenity_evidence`

Validated local-jurisdiction amenity records. Identity is source-centric and
includes source, source record ID, and amenity type. Rows retain matching and
provenance metadata. Quarantined `source='DDOT'` rows are not canonical inputs;
clean `DDOT_ARCGIS` is distinct.

### `stop_osm_evidence`

OSM tags and feature metadata. Canonical synthesis accepts only explicit yes/no
amenity tags with a full identity match to a member stop—not proximity alone.

### Transit and ridership tables

`ridership_snapshots` stores period/route ridership source values.
`stop_transit_evidence` and related tables retain service context. WMATA amenity
inventory fields are not authoritative current shelter/bench evidence.

## Community review

### `community_reviewers`

Durable reviewer identity is the numeric `id`. `reviewer_key` is an anonymous
browser handle. Nullable `email`, `email_verified_at`, and `claimed_at` represent
an optional claimed account; email is private and uniquely indexed only after
verification. `reviewer_login_tokens` stores expiring, one-use SHA-256 token
hashes and never raw magic-link tokens.

### `stop_review_assignments`

| Field | Meaning |
|---|---|
| `id` | assignment identity |
| `stop_id` | canonical physical stop |
| `reviewer_id` | assigned reviewer |
| `scenario` | opportunity, route, nearby, map, or direct context |
| `campaign` | nullable internal evidence focus |
| `status` | assigned/completed workflow status |
| timestamps | creation and completion history |

Indexes support stop and reviewer lookup. Historical `campaign=NULL` is valid.

### `stop_observations`

Append-only dated observations keyed by `id`. Important fields include:

- `physical_stop_id`, `reviewer_id`, `source`, `observed_at`
- shelter/bench presence, seating type/condition, comfort and limitations
- accessibility and preliminary `bench_feasible`/pad observations
- `weather_exposure`, `riders_avoid_facilities`, rider activity, and notes
- `review_mode` and `streetview_imagery_month`
- nullable indexed `assignment_id` foreign key to `stop_review_assignments`
- stewardship interest/contact fields

Historical rows can have null prospective fields. `assignment_id` is not unique;
observation `id` remains identity. `streetview_imagery_month` is not the same as
`observed_at`. There is no photo/blob column or photo storage subsystem.

### `stop_consensus`

Derived majority values and confidence from usable community observations.
Unknown responses do not vote. It is recalculated, not manually asserted.

## Canonical and derived layers

### `stop_amenity_status`

Exactly one `bench` and one `shelter` row per active stop. Unique identity:
`(physical_stop_id, amenity_type)`. Status is one of `confirmed_yes`,
`confirmed_no`, `likely_yes`, `likely_no`, `conflicting`, or `unknown`.
Source counts, source lists, community counts, conflict flags, rationale, and
timestamp preserve auditability.

### `stop_amenity_review_priority`

Exactly one row per active stop/amenity pair. It orders unresolved evidence work
using canonical status, consensus progress, conflict, and rider percentile. It
does not determine amenity truth.

### `opportunity_assessments`

One current assessment per active physical stop. Stores distinct-route exposure:
`combined_route_weekday_boardings`, `highest_route_weekday_boardings`, route
counts, assessment JSON, and canonical `rider_exposure_percentile`.

### `seating_improvement_opportunities`

One row per active stop. Stores canonical bench/shelter status, evidence strength,
adequacy, preliminary clearance, workflow, rider percentile, documented need,
transparent components, rank, rationale, and update time. Membership is not
score-gated.

### `bench_installation_candidates`

Narrow, evidence-qualified physical bench-candidacy table. It is not the broad
seating-opportunity universe.

### `review_queue`

Compatibility/assignment queue with current-stop filtering, pending/availability
state, legacy opportunity context, amenity review-priority rollups, rider
percentile, and review questions. Opportunity mode selects directly from
`seating_improvement_opportunities`; route and nearby modes retain queue behavior.

## Compatibility tables

The database still includes earlier analytical layers such as
`stop_priority_snapshots`, `improvement_opportunities`,
`improvement_recommendations`, impact summaries, project tables, validation
tables, and reporting snapshots. Some APIs still consume them. They are not the
canonical broad seating model and must not be removed without tracing consumers.

`route_exposure_score` is legacy priority-factor context. The current percentile
is `opportunity_assessments.rider_exposure_percentile`.

## Active review migration

Run from the repository root with a deliberate database target:

```bash
# Set this in the shell to a temporary/deployment database first.
DMV_BUS_STOPS_DB=/path/to/copy.db python scripts/active/create_review_tables.py
```

On PowerShell:

```powershell
$env:DMV_BUS_STOPS_DB = "C:\path\to\copy.db"
python scripts/active/create_review_tables.py
```

The migration is idempotent. It creates review tables if absent; adds nullable
`campaign`, `assignment_id`, `weather_exposure`, and
`riders_avoid_facilities` when missing; preserves existing IDs/rows; and creates
the assignment lookup index. Always back up and preflight a copy first.
