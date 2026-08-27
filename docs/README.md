# Documentation

DMV Bus Stop Intelligence has three primary documentation layers:

- [Project README](../README.md) introduces the civic purpose, current
  capabilities, volunteer value, limitations, and high-level setup.
- [Volunteer Review Handbook](Volunteer_Review_Handbook.md) is the task-oriented
  guide for reviewing and stewarding stops.
- [Technical Handoff](TECHNICAL_HANDOFF.md) is the authoritative maintainer
  reference for data authority, derivations, routing, migrations, rebuilds, and
  compatibility boundaries.

Supporting references:

- [Database Schema Guide](DATABASE_SCHEMA.md) explains the current conceptual
  schema and table authority.
- [Project Handbook](DMV_Bus_Stop_Intelligence_Handbook.md) summarizes the civic
  principles behind the project and points to the current audience-specific
  guides.
- `ROADMAP.md` is intentionally empty; do not infer planned functionality from
  it. Future work should be documented only after scope is approved.
- [Local development](LOCAL_DEVELOPMENT.md) provides the repeatable `.env` setup
  and local-only startup/test commands.
- [Limited-pilot deployment](DEPLOY_LIMITED_PILOT.md) defines production environment,
  Waitress startup, backup/restore, logging, and smoke-test operations.
- [Small-pilot readiness audit](PILOT_READINESS.md) records deployment blockers,
  repository housekeeping decisions, and the supervised-pilot checklist.
- [`scripts/active`](../scripts/active/README.md) inventories supported mutating
  commands; [`scripts/diagnostics`](../scripts/diagnostics/README.md) lists supported
  read-only checks.

The executable schema is `src/database/schema.sql`. Existing SQLite databases
also depend on active idempotent migrations, so schema prose is not a substitute
for inspecting a deployment database before operating on it.
