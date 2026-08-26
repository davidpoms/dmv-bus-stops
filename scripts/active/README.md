# Supported maintainer commands

This directory contains commands a maintainer may legitimately run against current
code and schema. Commands that touch SQLite use `DMV_BUS_STOPS_DB`, an explicit
database argument, or both. Always target a copy first; back up and hash any database
before an approved mutation.

| Command | Purpose | Effect / safe use |
|---|---|---|
| `build_gtfs_stop_map.py` | rebuild GTFS-to-stop mappings | mutates selected DB; reviewed source refresh only |
| `import_gtfs_stop_structure.py <feed.zip> --feed-id <id>` | preserve immutable GTFS stop/facility metadata | metadata-only import; idempotent by feed ID and ZIP SHA-256 |
| `build_gtfs_stop_status.py` | rebuild canonical active-stop status | mutates selected DB and creates a local backup |
| `create_review_tables.py` | idempotent review/auth schema migration | mutates selected DB; deployment migration |
| `create_physical_stop_identity_v2.py [db] --apply` | install additive V2 lifecycle tables | idempotent selected-DB migration; dry run without `--apply` |
| `download_census_boundaries.py` | refresh Census geography files | network/file write; review generated diffs |
| `download_dc_boundaries.py` | refresh DC geography files | network/file write; review generated diffs |
| `download_dcgis_stops.py` | download DC stop-source data | network/file write; intentional source refresh only |
| `download_wmata_stops.py` | download WMATA stop-source data | network/file write; intentional source refresh only |
| `generate_improvement_recommendations.py` | compatibility recommendation rebuild | mutates selected DB; current-stop invariant enforced |
| `generate_priority_levels.py` | compatibility impact-level rebuild | mutates selected DB; current-stop invariant enforced |
| `generate_seating_improvement_opportunities.py` | canonical seating-opportunity rebuild | mutates explicit/selected DB |
| `import_centerlines_paginated.py` | refresh regional centerlines | network and selected-DB mutation |
| `import_falls_church_amenities.py` | curated Falls Church amenity import | preflight by default; `--apply` mutates explicit DB |
| `import_prince_georges_centerlines.py` | refresh Prince George's centerlines | network and selected-DB mutation |
| `import_prince_georges_raw_evidence.py` | raw PG provenance import | preflight by default; `--apply` mutates explicit DB |
| `import_prince_georges_thebus_amenities.py` | TheBus amenity import | preflight by default; `--apply` mutates explicit DB |
| `migrate_amenity_evidence_identity.py` | amenity evidence identity migration | mutates explicit/selected DB after collision audit |
| `migrate_physical_stops_v2.py --db <copy> --plan/--apply --report <json>` | complete V2 identity cutover and derived rebuild | explicit DB required; repository production DB refused without production-only override; report is an atomic phase checkpoint |
| `rebuild_amenity_review_priority.py` | canonical amenity status/priority rebuild | mutates explicit/selected DB |
| `rebuild_stop_amenity_status.py` | canonical shelter/bench synthesis rebuild | mutates explicit/selected DB |
| `rebuild_stop_routes_clean.py` | specialized route repair | destructive selected-DB rebuild with backup; not routine |
| `replace_ddot_shelter_evidence.py` | atomic DDOT evidence replacement | preflight default; `--apply` mutates explicit/selected DB |
| `reset_v2_test_contributions.py --db <copy> --confirm "RESET DISPOSABLE V2 TEST CONTRIBUTIONS"` | one-time pre-pilot test-data reset | destructive and narrow; refuses the default DB unless separately authorized |

`src/processing/build_physical_stops.py` is bootstrap-only. It requires
`--bootstrap-empty-database` and refuses a populated identity registry.

The V2 manifest generator lives under `scripts/diagnostics` because proposal
generation is read-only. The active cutover command regenerates and validates that
proposal itself; it never accepts an external manifest as authority.

Read-only checks belong in `scripts/diagnostics`. Historical implementations belong
in Git history or the curated `scripts/archive/migrations` reference set.

The stop-structure importer requires an explicit local ZIP and never downloads or
rebuilds current pipelines. Obtain the WMATA Bus GTFS ZIP through the configured
WMATA source, keep it outside Git, and use the stable feed ID `wmata-bus`.
