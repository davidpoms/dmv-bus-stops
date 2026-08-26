# Supported diagnostics

These commands are current, read-only integrity and preflight tools. They open an
existing SQLite database with `mode=ro`; they do not create or mutate databases.

Pass a database path explicitly, or set `DMV_BUS_STOPS_DB` where the command permits
the environment default. Run diagnostics before and after a reviewed migration or
rebuild. Temporary reports should be written outside tracked repository paths.

```bash
python scripts/diagnostics/validate_geography.py <database>
python scripts/diagnostics/validate_route_integrity.py <database>
python scripts/diagnostics/preflight_amenity_review_priority.py <database>
```

Geometry helpers used by serving-direction audits remain library code in
`src/processing/heading_audit.py`; there is no supported standalone heading command.
