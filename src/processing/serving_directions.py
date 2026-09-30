"""Canonical member-linked serving-direction selection."""

from __future__ import annotations

import math
from collections import defaultdict

from src.processing.gtfs_member_linkage import classify_member_links


LATEST_DIRECTIONS_SQL = """
WITH latest AS (
 SELECT id,wmata_stop_id,wmata_heading,wmata_status,match_distance_m,
        match_confidence,created_at,
        ROW_NUMBER() OVER(PARTITION BY CAST(wmata_stop_id AS TEXT)
                          ORDER BY datetime(created_at) DESC,id DESC) sequence
 FROM stop_wmata_evidence
 WHERE wmata_heading IS NOT NULL AND TRIM(wmata_heading)!=''
)
SELECT pm.physical_stop_id,pm.bus_stop_id,b.external_stop_id,
       CAST(g.gtfs_stop_id AS TEXT),g.match_method,l.wmata_heading,
       l.wmata_status,l.match_distance_m,l.match_confidence,l.id
FROM physical_stop_members pm
JOIN bus_stops b ON b.id=pm.bus_stop_id
JOIN gtfs_stop_map g ON g.bus_stop_id=pm.bus_stop_id
LEFT JOIN latest l ON CAST(l.wmata_stop_id AS TEXT)=CAST(g.gtfs_stop_id AS TEXT)
                  AND l.sequence=1
ORDER BY pm.physical_stop_id,pm.bus_stop_id,CAST(g.gtfs_stop_id AS TEXT),l.id
"""


STOP_DIRECTIONS_SQL = """
WITH members AS (
 SELECT pm.physical_stop_id,pm.bus_stop_id,b.external_stop_id,
        CAST(g.gtfs_stop_id AS TEXT) gtfs_stop_id,g.match_method
 FROM physical_stop_members pm
 JOIN bus_stops b ON b.id=pm.bus_stop_id
 JOIN gtfs_stop_map g ON g.bus_stop_id=pm.bus_stop_id
 WHERE pm.physical_stop_id=?
), latest AS (
 SELECT id,wmata_stop_id,wmata_heading,wmata_status,match_distance_m,
        match_confidence,created_at,
        ROW_NUMBER() OVER(PARTITION BY CAST(wmata_stop_id AS TEXT)
                          ORDER BY datetime(created_at) DESC,id DESC) sequence
 FROM stop_wmata_evidence
 WHERE wmata_heading IS NOT NULL AND TRIM(wmata_heading)!=''
   AND CAST(wmata_stop_id AS TEXT) IN (SELECT gtfs_stop_id FROM members)
)
SELECT m.physical_stop_id,m.bus_stop_id,m.external_stop_id,
       m.gtfs_stop_id,m.match_method,l.wmata_heading,
       l.wmata_status,l.match_distance_m,l.match_confidence,l.id
FROM members m
LEFT JOIN latest l ON CAST(l.wmata_stop_id AS TEXT)=m.gtfs_stop_id AND l.sequence=1
ORDER BY m.physical_stop_id,m.bus_stop_id,m.gtfs_stop_id,l.id
"""


def valid_heading(value):
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number % 360 if math.isfinite(number) else None


def load_member_directions(conn):
    """Return identity-eligible latest directions keyed by physical stop/member."""
    return _classify_direction_rows(conn.execute(LATEST_DIRECTIONS_SQL))


def _classify_direction_rows(rows):
    """Keep mappings without headings so identity conflicts still fail closed."""
    raw = defaultdict(list)
    for row in rows:
        (stop_id, member_id, external_id, gtfs_id, method, heading, status,
         distance, confidence, evidence_id) = row
        raw[(stop_id, member_id, external_id)].append({
            "gtfs_stop_id": gtfs_id, "match_method": method, "stop_code": None,
            "heading": heading, "status": status, "match_distance_m": distance,
            "confidence": confidence, "evidence_id": evidence_id,
        })
    result = defaultdict(lambda: defaultdict(list))
    for (stop_id, member_id, external_id), mappings in sorted(raw.items()):
        for mapping in classify_member_links(external_id, mappings):
            heading = valid_heading(mapping["heading"])
            if not mapping["identity_eligible"] or heading is None:
                continue
            result[stop_id][member_id].append({
                "gtfs_stop_id": mapping["gtfs_stop_id"],
                "heading_degrees": heading,
                "linkage_method": mapping["match_method"],
                "evidence_status": mapping["status"],
                "match_distance_m": mapping["match_distance_m"],
                "confidence": mapping["confidence"],
            })
    return result


def serving_directions_for_stop(conn, physical_stop_id):
    """Resolve one stop without classifying unrelated members or evidence."""
    rows = conn.execute(STOP_DIRECTIONS_SQL, (physical_stop_id,))
    return _classify_direction_rows(rows).get(physical_stop_id, {})
