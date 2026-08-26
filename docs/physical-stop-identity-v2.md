# Physical Stop Identity v2 handoff

V2 defines a physical stop as one passenger boarding/waiting location. The
production migration remains deferred; current `physical_stop_id` values have not
changed.

## Persistent identity foundation

V2 changes physical stops from rebuild output into a persistent registry. IDs are
never reused. A current identity can be retired, but its row remains resolvable.
Lifecycle events, predecessor/successor edges, explicit state, and member lineage
record splits, merges, movement, retirement, and membership changes. Reconciliation
first produces a read-only plan; applying reviewed actions is a separate transaction.

Exact source/member identity and structured GTFS provenance outrank geometry.
Coordinates support change detection and review but cannot establish identity by
themselves. Missing or conflicting identity and the five frozen exceptions fail
closed.

The old `build_physical_stops.py` command is bootstrap-only for an empty registry.
It can no longer truncate established identities. Geography is recomputed from
canonical coordinates; unavailable dimensions remain null rather than being copied.
Evidence attribution is stored separately from raw evidence, and ambiguous spatial
evidence may remain unresolved.

Current reviewer/community content is disposable owner-created test data for the
one-time V2 cutover only. Its reset is explicit and confirmed, not part of routine
reconciliation. After the V2 baseline, reviewer identities and contribution history
are durable and future changes must use lineage and explicit disposition.

## Deterministic automatic proposal

`src.processing.physical_stop_v2_proposal` is the single supported proposal engine.
It reads committed database inputs only and never mutates identities. Generate and
validate the canonical proposal with:

```bash
python scripts/diagnostics/generate_physical_stop_v2_manifest.py \
  --db <database> --out <manifest.json> --summary --validate
```

Proposal version: `physical-stop-v2-proposal-1`

Canonical SHA-256 on the reviewed current database:

```text
A21D2223DBC08C6D6327C7072404B8B9912C17898AA91282511F2A4B8B724D23
```

The canonical JSON excludes timestamps, paths, test-review history, and formatting.
The exact drift gate is 384 automatic parents, 791 child groups, and the five manual
exceptions. A mismatch exits nonzero under `--validate`.

The engine requires `physical_stops`, `physical_stop_members`, `bus_stops`,
`gtfs_stop_map`, `stop_wmata_evidence`, `stop_routes`, `routes`, and
`stop_gtfs_status`. It uses canonical exact-over-fallback linkage, latest
member-linked headings, a 160-degree ordinary-curb threshold, reviewed named-bay
partitions, and the previously adjudicated additions/exclusions. No `.tmp` file,
prior worktree, archived script, network lookup, or incidental row order is input.

The old ignored manifest and the committed engine have identical parent, child, and
member partitions. Names, coordinates, and route sets also agree. The new payload
adds 738 child heading/GTFS review fields, removes test-only history, and corrects
eight child current expectations using current `gtfs_stop_map` membership rather
than inheriting the predecessor's active flag. These intentional metadata changes
explain why the old canonical hash does not match.

Proposal is not migration: it allocates no IDs and does not rebuild downstream data.
The next migration command must validate this version/hash before applying lineage.

## GTFS member linkage

Identity diagnostics apply this explicit precedence:

1. exact `stop_code`/external-stop identity or another explicit crosswalk;
2. coordinate fallback only when no exact identity exists;
3. a fallback conflicting with an available exact identity remains provenance but
   cannot contribute headings or boarding identities;
4. multiple conflicting exact identities fail closed.

This excludes mapping contamination at physical stops 506, 658, 1437, 1917,
2340, 2451, 3313, 3752, 3802, 4088, and 4563. It does not delete their historical
`gtfs_stop_map` rows.

## Frozen review classification

The automatic manifest contains 384 affected parents and 791 proposed child
groups: 341 ordinary-curb splits and 43 named-bay splits. Stops 82, 2048, and
3021 are included as resolved ordinary splits. Five identities remain quarantined
from automatic migration:

- 406: opposed headings and a transitive four-member chain permit more than one
  plausible partition.
- 2231: East Falls Church repeats Bay B/C/D labels across source generations with
  inconsistent coordinates and no platform/version evidence.
- 4468, 5196, and 6080: each contains current and source-only members in an
  over-wide proximity chain without exact evidence for the bridge member.

All five have disposition `RETAIN_MANUAL_EXCEPTION`. The local review artifact is
`.tmp/physical-stop-v2-manifest.json`; it is intentionally ignored and assigns no
successor IDs. It is comparison evidence only and is not an input to the committed
generator.

## Derived rebuild inventory and order

After a future temporary identity migration, use this dependency order:

1. validate proposal/version/hash and apply identity lineage;
2. explicitly reset disposable pre-pilot contributions;
3. recompute child geography and evidence attribution;
4. rebuild `stop_gtfs_status`;
5. rebuild opportunity assessments and rider percentile;
6. rebuild canonical amenity status and review priority;
7. rebuild compatibility and seating opportunities;
8. rebuild bench candidates, recommendations, impacts, and priorities;
9. rebuild review queue/ranks;
10. run integrity, FK, membership, lifecycle, and active-scope invariants.

Current rebuild-path inventory:

| Derived output | Full command | Library rebuild | Explicit-DB integration |
|---|---|---|---|
| `stop_jurisdiction` | no standalone command | supported | supported |
| `physical_stop_evidence_attribution` | no standalone command | supported | supported |
| `stop_gtfs_status` | supported | supported | supported |
| `opportunity_assessments` and rider percentile | no standalone command | supported | supported |
| `stop_amenity_status` | supported | supported/targeted | supported |
| `stop_amenity_review_priority` | supported | supported/targeted | supported |
| `improvement_opportunities` | no standalone command | supported | supported |
| `seating_improvement_opportunities` | supported | supported/targeted | supported |
| `bench_installation_candidates` | no standalone command | supported | supported |
| `improvement_recommendations` | supported compatibility command | supported | supported |
| `stop_improvement_impact` | supported compatibility command | supported | supported |
| `review_queue` and deterministic ranks | no standalone command | supported/targeted | supported |
| `stop_priority_snapshots` | partial compatibility path | library uses a fixed default | **incomplete** |
| `recommendation_confidence` | no current command | compatibility library only | **incomplete** |
| `project_priorities` | no current command | compatibility library only | **incomplete** |
| reporting/project exports | partial commands | mixed | **incomplete** |

The remaining cutover blocker is a single reviewed, explicit-database migration and
rebuild orchestrator covering the identity apply plus every row above. It is
deliberately outside this foundation commit; maintainers must not assemble a
production cutover ad hoc from the individual calls.

## Current feed limitation

WMATA snapshot `S1000250` (2026-06-21 through 2026-09-12) supplies stop ID, code,
name, description, coordinates, and URL, but does not populate `parent_station`,
`platform_code`, `location_type`, `zone_id`, or `wheelchair_boarding`. The new
snapshot tables preserve those fields if future feeds provide them. Previously
unarchived historical versions cannot be reconstructed.
