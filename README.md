# DMV Bus Stop Intelligence

DMV Bus Stop Intelligence is an open civic-data project for understanding the
places where people wait for buses across Washington, DC, Maryland, and
Virginia. It brings fragmented evidence together around a canonical physical
stop so communities can see what is known, what is uncertain, and where a
current observation would help.

Transit agencies are strong sources for routes and service. Stop-level physical
conditions are harder: responsibility is divided among agencies and local
governments, inventories cover different features, open data can be incomplete,
and street imagery can lag reality. A shelter record also cannot tell us whether
its seating is comfortable or whether riders can use the waiting area well.

This project does not turn those imperfect sources into false certainty. It
preserves their provenance, shows disagreement, and invites dated community
observations to improve the record.

## What the project brings together

- GTFS stops and routes, clustered into canonical physical stops
- the current/non-current status of each physical stop
- validated local-jurisdiction shelter and bench evidence
- explicit, identity-matched OpenStreetMap amenity tags
- append-only community observations and derived community consensus
- seating condition, comfort, accessibility, weather, and rider-use observations
- preliminary visual observations of waiting and pass-through space
- Street View review method and imagery month
- route-based rider exposure
- overlapping state, county, municipality, ward, and ANC geography

Evidence has different strengths. “Likely,” “confirmed,” “observed,”
“conflicting,” and “unknown” are deliberately not interchangeable. WMATA
shelter/bench inventory fields are not treated as authoritative current amenity
evidence; current shelter and bench synthesis relies on supported local sources,
community evidence, and safely identity-matched OSM evidence.

## What the system can do now

For every active stop, the current application can organize evidence about
bench and shelter presence, preserve conflicts, show whether community consensus
has been reached, and identify the next useful review question. It can distinguish
amenity presence from seating comfort and from preliminary visual clearance.

Every active stop also belongs to the broad seating-improvement opportunity
universe. A provisional score ranks that universe; it does not decide membership
and does not prove that construction should occur. A stop with seating can still
have a comfort problem, while apparent absence does not establish that a new
bench is feasible.

Current analysis can support work such as:

- finding stops with missing or conflicting amenity evidence
- comparing evidence coverage among jurisdictions and overlapping geographies
- identifying high-route-exposure stops where seating conditions merit attention
- separating likely amenity absence from observed comfort limitations
- building evidence-aware volunteer review queues
- retaining dated observations so conditions can be compared over time
- identifying stops that may deserve further planning review

These outputs support investigation and prioritization. They are not engineering,
ADA, ownership, right-of-way, permitting, utility, or construction decisions.

## Why a volunteer observation matters

A current observation can resolve disagreement, challenge an old or likely
status, fill a gap left by structured datasets, and describe qualities those
datasets rarely contain. New assignment-backed reviews append to history rather
than replacing earlier observations.

One observation creates a dated piece of evidence. Repeated observations add
temporal context. Stewardship can build a more durable community record of a
stop as amenities, construction, maintenance, and waiting conditions change.
The project does not yet provide automated change detection, recurring reminders,
or community photo hosting.

## Ways to review

The dashboard offers one primary **Review a seating opportunity** action. It
automatically selects a ranked stop and emphasizes the evidence currently most
useful there. Reviewers may instead choose **My Route**, **Near Me**, or a stop
from the map or stop page.

The review page keeps two questions separate:

- **Why you're reviewing this stop** explains how you arrived there.
- **What would be useful to check** is derived from the stop's current evidence.

All paths use one shared survey. Internal workflow state changes emphasis, not
the set of ordinary observations a reviewer is allowed to record.

Reviewing may remain anonymous. Optional passwordless email sign-in preserves
the same private reviewer profile, display name, history, and stewarded stops
across browsers or devices when production mail delivery is configured.
The deployment-neutral implementation supports injected transports or explicitly
configured SMTP; it never sends or reveals links through a production fallback.

See the [Volunteer Review Handbook](docs/Volunteer_Review_Handbook.md) before
reviewing a stop.

## Important limitations

- Rider exposure is based on the routes serving a stop, not observed boardings
  at that physical stop.
- Local-government evidence coverage is uneven and source records can be stale.
- Street View observations describe the imagery capture period, which may be
  older than the review submission.
- Community observation and consensus coverage is currently sparse.
- Visual clearance is preliminary and cannot establish feasibility or approval.
- Canonical “likely” states remain evidence-based estimates, not confirmations.
- The ranking model is provisional and calibratable.
- The project does not store reviewer photos.

## Running the project

The application is a Flask service backed by SQLite. Follow the concise
[local development quickstart](docs/LOCAL_DEVELOPMENT.md) to create a virtual
environment, copy `.env.example` to the ignored `.env`, generate a persistent
local secret, and start the application.

The local command is:

```bash
python -m src.api.app
```

This uses Flask's development server and is not a production deployment command.
The supported limited-pilot runner is Waitress behind operator-managed HTTPS. See
[Deploying the limited volunteer pilot](docs/DEPLOY_LIMITED_PILOT.md) for required
environment, backup, startup/restart, and smoke-test procedures.

Use `requirements.txt` for development, offline processing, and the standalone
Waitress path. Hosted WSGI environments such as PythonAnywhere should install
`requirements-pilot.txt`; PythonAnywhere supplies its own WSGI server and does not
need Waitress.

By default it uses `src/database/dmv_bus_stops.db`. To run against a copy or a
separate deployment database, set `DMV_BUS_STOPS_DB` to that path before starting
the application or an active migration that supports the override.

Run the test suite with:

```bash
python -m unittest discover -s tests -p "test_*.py" -v
git diff --check
```

Do not experiment against the production database. Make a backup, use a
temporary copy, run required migrations, and validate derived-table invariants
before any production operation.

## Documentation

- [Volunteer Review Handbook](docs/Volunteer_Review_Handbook.md) — how to review
  and steward stops
- [Technical Handoff](docs/TECHNICAL_HANDOFF.md) — authoritative implementation
  semantics and operations
- [Database Schema Guide](docs/DATABASE_SCHEMA.md) — current table roles and
  authority boundaries
- [Documentation index](docs/README.md)

Contributions are welcome in data validation, source research, reviewer UX,
testing, documentation, and careful analysis. Keep evidence provenance visible,
preserve uncertainty, and distinguish implemented behavior from future ideas.
