# Physical Stop Identity v2 handoff

V2 defines a physical stop as one passenger boarding/waiting location. The
production migration remains deferred; current `physical_stop_id` values have not
changed.

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
successor IDs.

## Current feed limitation

WMATA snapshot `S1000250` (2026-06-21 through 2026-09-12) supplies stop ID, code,
name, description, coordinates, and URL, but does not populate `parent_station`,
`platform_code`, `location_type`, `zone_id`, or `wheelchair_boarding`. The new
snapshot tables preserve those fields if future feeds provide them. Previously
unarchived historical versions cannot be reconstructed.
