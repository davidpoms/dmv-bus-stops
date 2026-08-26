# Serving-direction evidence

“Serving direction” describes the direction of travel at a physical boarding
location. It is orientation context for distinguishing paired curbside stops;
it is not a route destination, trip headsign, vehicle bearing, or inferred road
direction.

The `/stops/<id>` field `streetview_display_heading` is different: it is a
nearest-road orientation used to aim the Street View display. It is not transit
evidence and must never be substituted for the canonical `serving_directions`
records. The API does not expose a lossy singular
`serving_direction` scalar. `serving_headings` remains only a backwards-compatible
numeric projection; `serving_directions` is the canonical structured payload and
preserves identity/provenance and multiple values. Volunteer and stop-detail
direction labels use `serving_directions` exclusively.

The application displays a WMATA heading only when the WMATA stop identifier
is explicitly connected through `gtfs_stop_map` to a `bus_stops` member of the
requested `physical_stop_id`. The `physical_stop_id` stored on
`stop_wmata_evidence` is not sufficient by itself because the historical
importer populated that field with an unbounded nearest-neighbor match.

The backend retains heading provenance including the WMATA stop ID, member and
source stop IDs, linkage method, evidence status, recorded match distance, and
confidence. WMATA `BSTP_OPS_TCD` values are reported as provenance but do not
control heading eligibility: the repository and available dataset metadata do
not define the code values authoritatively.

A physical stop can contain multiple source members. All identity-linked
headings remain visible, including contradictions. Physical-stop construction
historically used 20-meter connected-component clustering, so an opposing pair
could indicate an identity issue requiring an audited migration rather than UI
suppression. Multiple headings do not automatically mean the data is wrong:
terminals, loops, station bays, and shared boarding areas can legitimately have
more than one direction.

## Technical handoff: physical-stop identity debt

The heading display is provenance-correct and remains separate from physical-stop
identity. Physical Stop Identity V2 retired historical Stop 935 and split its two
boarding locations: current stop 7755 links source stop 1002216 to GTFS stop 7867
and 119 degrees Southeast; current stop 7756 links source stop 1002217 to GTFS stop
7868 and 297 degrees Northwest. The retired stop-detail page links to both current
successors rather than choosing or averaging a direction.

Physical Stop Identity V2 now provides persistent split lineage, intentional old-URL
handling, and deterministic identity reconciliation. Future splits or merges must
continue using that lifecycle model. Observation or reviewer history that cannot be
safely attributed to one successor must remain quarantined; no history may be
reassigned from geometry alone.

Versioned `gtfs_stop_structure` metadata supports that future audit without
changing current physical identities. `parent_station` establishes facility
membership, not equivalence of its bays or platforms.

`src.processing.heading_audit` is a supported diagnostic module for that work.
It provides circular angular separation and connected-component chaining helpers;
its contradiction threshold is an audit classification, never a display filter.
