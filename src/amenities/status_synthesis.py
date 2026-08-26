"""Canonical, rebuildable shelter and bench evidence synthesis."""

from __future__ import annotations

import json
import sqlite3
from collections import defaultdict
from datetime import datetime, timezone


AMENITY_TYPES = ("shelter", "bench")
DERIVED_STATUSES = (
    "confirmed_yes",
    "confirmed_no",
    "likely_yes",
    "likely_no",
    "conflicting",
    "unknown",
)
CONSENSUS_REVIEW_THRESHOLD = 3
CONSENSUS_CONFIDENCE_THRESHOLD = 0.75


SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS stop_amenity_status (
    physical_stop_id INTEGER NOT NULL,
    amenity_type TEXT NOT NULL CHECK (amenity_type IN ('shelter', 'bench')),
    derived_status TEXT NOT NULL CHECK (derived_status IN (
        'confirmed_yes', 'confirmed_no', 'likely_yes', 'likely_no',
        'conflicting', 'unknown'
    )),
    consensus_status TEXT NOT NULL,
    local_yes_count INTEGER NOT NULL DEFAULT 0,
    local_no_count INTEGER NOT NULL DEFAULT 0,
    local_yes_sources TEXT NOT NULL DEFAULT '[]',
    local_no_sources TEXT NOT NULL DEFAULT '[]',
    osm_yes INTEGER NOT NULL DEFAULT 0,
    osm_no INTEGER NOT NULL DEFAULT 0,
    community_yes_count INTEGER NOT NULL DEFAULT 0,
    community_no_count INTEGER NOT NULL DEFAULT 0,
    community_observation_count INTEGER NOT NULL DEFAULT 0,
    evidence_conflict INTEGER NOT NULL DEFAULT 0,
    consensus_conflicts_with_other_evidence INTEGER NOT NULL DEFAULT 0,
    rationale TEXT NOT NULL DEFAULT '[]',
    updated_at TEXT NOT NULL,
    FOREIGN KEY (physical_stop_id) REFERENCES physical_stops(id)
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_stop_amenity_status_identity
ON stop_amenity_status (physical_stop_id, amenity_type);
"""


def _normalized_value(present, value):
    normalized = str(value or "").strip().lower()
    if normalized == "yes" or present == 1:
        return "yes"
    if normalized == "no" or present == 0:
        return "no"
    return None


def _external_stop_ids(conn):
    result = defaultdict(set)
    rows = conn.execute(
        """
        SELECT pm.physical_stop_id, bs.external_stop_id
        FROM physical_stop_members pm
        JOIN bus_stops bs ON bs.id = pm.bus_stop_id
        WHERE bs.external_stop_id IS NOT NULL
        """
    )
    for stop_id, external_stop_id in rows:
        result[stop_id].add(str(external_stop_id).strip())
    return result


def _osm_tags(raw_tags):
    if not raw_tags:
        return {}
    try:
        value = json.loads(raw_tags)
    except (TypeError, ValueError):
        return {}
    return value if isinstance(value, dict) else {}


def _osm_refs(tags):
    refs = set()
    for key in ("ref:wmata", "ref"):
        value = tags.get(key)
        if value is None:
            continue
        for item in str(value).replace(",", ";").split(";"):
            if item.strip():
                refs.add(item.strip())
    return refs


def _has_full_consensus(observation_count, confidence, value):
    return (
        observation_count >= CONSENSUS_REVIEW_THRESHOLD
        and confidence is not None
        and confidence >= CONSENSUS_CONFIDENCE_THRESHOLD
        and value in (0, 1)
    )


def _derive_status(consensus_value, positive, negative):
    if consensus_value == 1:
        return "confirmed_yes"
    if consensus_value == 0:
        return "confirmed_no"
    if positive and negative:
        return "conflicting"
    if positive:
        return "likely_yes"
    if negative:
        return "likely_no"
    return "unknown"


def synthesize_rows(conn, updated_at=None, physical_stop_ids=None):
    """Return exactly two derived rows for every canonical current stop."""
    updated_at = updated_at or datetime.now(timezone.utc).isoformat()
    active_stops = {
        row[0]
        for row in conn.execute(
            "SELECT physical_stop_id FROM stop_gtfs_status WHERE current_gtfs=1"
        )
    }
    if physical_stop_ids is not None:
        active_stops &= {int(stop_id) for stop_id in physical_stop_ids}
    external_ids = _external_stop_ids(conn)

    local = {
        amenity: defaultdict(lambda: {"yes": 0, "no": 0,
                                      "yes_sources": set(), "no_sources": set()})
        for amenity in AMENITY_TYPES
    }
    has_attribution = conn.execute("""SELECT 1 FROM sqlite_master WHERE type='table'
        AND name='physical_stop_evidence_attribution'""").fetchone() is not None
    local_sql = """
        SELECT COALESCE(a.physical_stop_id,e.physical_stop_id),
               e.source,e.amenity_type,e.present,e.value
        FROM stop_amenity_evidence e
        LEFT JOIN physical_stop_evidence_attribution a
          ON a.evidence_table='stop_amenity_evidence'
         AND a.evidence_row_id=e.id
         AND a.attribution_version='physical-stop-v2-cutover-1'
        WHERE e.source != 'DDOT'
          AND (a.attribution_method IS NULL OR a.attribution_method!='unresolved')
          AND e.amenity_type IN ('shelter', 'bench')
        """ if has_attribution else """SELECT physical_stop_id,source,amenity_type,
          present,value FROM stop_amenity_evidence WHERE source!='DDOT'
          AND amenity_type IN ('shelter','bench')"""
    for row in conn.execute(local_sql):
        stop_id, source, amenity, present, value = row
        if stop_id not in active_stops:
            continue
        normalized = _normalized_value(present, value)
        if normalized:
            local[amenity][stop_id][normalized] += 1
            local[amenity][stop_id][f"{normalized}_sources"].add(source)

    osm = {
        amenity: defaultdict(lambda: {"yes": False, "no": False})
        for amenity in AMENITY_TYPES
    }
    osm_sql = """SELECT COALESCE(a.physical_stop_id,e.stop_id),e.osm_tags
           FROM stop_osm_evidence e
           LEFT JOIN physical_stop_evidence_attribution a
             ON a.evidence_table='stop_osm_evidence' AND a.evidence_row_id=e.id
            AND a.attribution_version='physical-stop-v2-cutover-1'
           WHERE a.attribution_method IS NULL OR a.attribution_method!='unresolved'""" \
        if has_attribution else "SELECT stop_id,osm_tags FROM stop_osm_evidence"
    for stop_id, raw_tags in conn.execute(osm_sql):
        if stop_id not in active_stops:
            continue
        tags = _osm_tags(raw_tags)
        # The historical proximity matcher was non-deterministic. Only an
        # exact source ref tied to this physical stop establishes identity.
        if not (_osm_refs(tags) & external_ids.get(stop_id, set())):
            continue
        for amenity in AMENITY_TYPES:
            value = str(tags.get(amenity, "")).strip().lower()
            if value in ("yes", "no"):
                osm[amenity][stop_id][value] = True

    community = {
        amenity: defaultdict(lambda: {"yes": 0, "no": 0, "observations": 0})
        for amenity in AMENITY_TYPES
    }
    for stop_id, shelter, bench in conn.execute(
        """
        SELECT physical_stop_id, shelter_present, bench_present
        FROM stop_observations
        WHERE source='community_review'
        """
    ):
        if stop_id not in active_stops:
            continue
        for amenity, value in (("shelter", shelter), ("bench", bench)):
            community[amenity][stop_id]["observations"] += 1
            normalized = str(value or "").strip().lower()
            if normalized in ("yes", "no"):
                community[amenity][stop_id][normalized] += 1

    consensus = {amenity: {} for amenity in AMENITY_TYPES}
    for stop_id, has_shelter, has_bench, confidence in conn.execute(
        "SELECT stop_id, has_shelter, has_bench, confidence FROM stop_consensus"
    ):
        if stop_id not in active_stops:
            continue
        for amenity, value in (("shelter", has_shelter), ("bench", has_bench)):
            observation_count = community[amenity][stop_id]["observations"]
            if _has_full_consensus(observation_count, confidence, value):
                consensus[amenity][stop_id] = value

    results = []
    for stop_id in sorted(active_stops):
        for amenity in AMENITY_TYPES:
            local_row = local[amenity][stop_id]
            osm_row = osm[amenity][stop_id]
            community_row = community[amenity][stop_id]
            consensus_value = consensus[amenity].get(stop_id)
            non_consensus_yes = bool(
                local_row["yes"] or osm_row["yes"] or community_row["yes"]
            )
            non_consensus_no = bool(
                local_row["no"] or osm_row["no"] or community_row["no"]
            )
            status = _derive_status(
                consensus_value, non_consensus_yes, non_consensus_no
            )
            conflict = non_consensus_yes and non_consensus_no
            consensus_conflict = bool(
                consensus_value is not None
                and ((consensus_value == 1 and non_consensus_no)
                     or (consensus_value == 0 and non_consensus_yes))
            )
            rationale = []
            if consensus_value is not None:
                rationale.append(
                    "Full community consensus confirms "
                    + ("presence." if consensus_value else "absence.")
                )
            if local_row["yes"]:
                rationale.append("Supported local records indicate presence.")
            if local_row["no"]:
                rationale.append("Supported local records indicate absence.")
            if osm_row["yes"]:
                rationale.append("Identity-matched OSM tags explicitly indicate presence.")
            if osm_row["no"]:
                rationale.append("Identity-matched OSM tags explicitly indicate absence.")
            if community_row["yes"] or community_row["no"]:
                rationale.append("Community observations contribute pre-consensus evidence.")
            if not rationale:
                rationale.append("No usable semantic evidence is available.")

            results.append({
                "physical_stop_id": stop_id,
                "amenity_type": amenity,
                "derived_status": status,
                "consensus_status": (
                    "yes" if consensus_value == 1
                    else "no" if consensus_value == 0
                    else "not_reached"
                ),
                "local_yes_count": local_row["yes"],
                "local_no_count": local_row["no"],
                "local_yes_sources": json.dumps(sorted(local_row["yes_sources"])),
                "local_no_sources": json.dumps(sorted(local_row["no_sources"])),
                "osm_yes": int(osm_row["yes"]),
                "osm_no": int(osm_row["no"]),
                "community_yes_count": community_row["yes"],
                "community_no_count": community_row["no"],
                "community_observation_count": community_row["observations"],
                "evidence_conflict": int(conflict),
                "consensus_conflicts_with_other_evidence": int(consensus_conflict),
                "rationale": json.dumps(rationale),
                "updated_at": updated_at,
            })
    return results


INSERT_SQL = """
INSERT INTO stop_amenity_status (
    physical_stop_id, amenity_type, derived_status, consensus_status,
    local_yes_count, local_no_count, local_yes_sources, local_no_sources,
    osm_yes, osm_no, community_yes_count, community_no_count,
    community_observation_count, evidence_conflict,
    consensus_conflicts_with_other_evidence, rationale, updated_at
) VALUES (
    :physical_stop_id, :amenity_type, :derived_status, :consensus_status,
    :local_yes_count, :local_no_count, :local_yes_sources, :local_no_sources,
    :osm_yes, :osm_no, :community_yes_count, :community_no_count,
    :community_observation_count, :evidence_conflict,
    :consensus_conflicts_with_other_evidence, :rationale, :updated_at
)
"""


def rebuild_stop_amenity_status(conn):
    """Transactionally replace only derived shelter/bench status rows."""
    conn.executescript(SCHEMA_SQL)
    rows = synthesize_rows(conn)
    expected = conn.execute(
        "SELECT COUNT(*) * 2 FROM stop_gtfs_status WHERE current_gtfs=1"
    ).fetchone()[0]
    if len(rows) != expected:
        raise RuntimeError(f"Synthesis produced {len(rows)} rows; expected {expected}")

    with conn:
        conn.execute("DELETE FROM stop_amenity_status")
        conn.executemany(INSERT_SQL, rows)

        checks = conn.execute(
            """
            SELECT
                COUNT(*),
                COUNT(*) - COUNT(DISTINCT a.physical_stop_id || ':' || a.amenity_type),
                SUM(CASE WHEN s.current_gtfs IS NULL OR s.current_gtfs != 1 THEN 1 ELSE 0 END)
            FROM stop_amenity_status a
            LEFT JOIN stop_gtfs_status s
              ON s.physical_stop_id = a.physical_stop_id
            """
        ).fetchone()
        if tuple(checks) != (expected, 0, 0):
            raise RuntimeError(f"Derived-table validation failed: {tuple(checks)}")
    return rows


def refresh_stop_amenity_status(conn, physical_stop_id):
    """Refresh only one current stop's two canonical amenity rows."""
    conn.executescript(SCHEMA_SQL)
    rows = synthesize_rows(conn, physical_stop_ids=(physical_stop_id,))
    with conn:
        conn.execute(
            "DELETE FROM stop_amenity_status WHERE physical_stop_id=?",
            (physical_stop_id,),
        )
        conn.executemany(INSERT_SQL, rows)
    return rows


def geography_status_rows(conn):
    """Aggregate canonical statuses over intentionally overlapping geographies."""
    geography_sql = """
    WITH geography AS (
        SELECT stop_id, 'State' geography_type,
               CASE state WHEN 'DC' THEN 'District of Columbia'
                          WHEN 'MD' THEN 'Maryland'
                          WHEN 'VA' THEN 'Virginia'
                          ELSE state END geography_name
        FROM stop_jurisdiction WHERE state IS NOT NULL
        UNION ALL
        SELECT stop_id, 'County',
               CASE county
                   WHEN 'Alexandria' THEN 'City of Alexandria'
                   WHEN 'Falls Church' THEN 'City of Falls Church'
                   ELSE county || ' County'
               END
        FROM stop_jurisdiction WHERE county IS NOT NULL
        UNION ALL
        SELECT stop_id, 'Municipality', municipality
        FROM stop_jurisdiction WHERE municipality IS NOT NULL
        UNION ALL
        SELECT stop_id, 'DC Ward', dc_ward FROM stop_jurisdiction WHERE dc_ward IS NOT NULL
        UNION ALL
        SELECT stop_id, 'ANC', dc_anc FROM stop_jurisdiction WHERE dc_anc IS NOT NULL
    )
    SELECT g.geography_type, g.geography_name, a.amenity_type,
           COUNT(*) current_stop_count,
           SUM(a.derived_status='confirmed_yes') confirmed_yes,
           SUM(a.derived_status='confirmed_no') confirmed_no,
           SUM(a.derived_status='likely_yes') likely_yes,
           SUM(a.derived_status='likely_no') likely_no,
           SUM(a.derived_status='conflicting') conflicting,
           SUM(a.derived_status='unknown') unknown,
           SUM(a.consensus_status IN ('yes','no')) consensus_reached,
           SUM(a.consensus_status='not_reached' AND a.derived_status IN ('likely_yes','likely_no')) likely_without_consensus,
           SUM(a.derived_status='conflicting') conflicting_priority_verification,
           SUM(a.derived_status='unknown') no_evidence_needs_first_observation
    FROM geography g
    JOIN stop_gtfs_status s ON s.physical_stop_id=g.stop_id AND s.current_gtfs=1
    JOIN stop_amenity_status a ON a.physical_stop_id=g.stop_id
    GROUP BY g.geography_type, g.geography_name, a.amenity_type
    ORDER BY g.geography_type, g.geography_name, a.amenity_type
    """
    grouped = {}
    for row in conn.execute(geography_sql):
        values = dict(row) if isinstance(row, sqlite3.Row) else dict(zip(
            ("geography_type", "geography_name", "amenity_type",
             "current_stop_count", *DERIVED_STATUSES, "consensus_reached",
             "likely_without_consensus", "conflicting_priority_verification",
             "no_evidence_needs_first_observation"), row
        ))
        key = (values["geography_type"], values["geography_name"])
        output = grouped.setdefault(key, {
            "type": values["geography_type"],
            "geography": values["geography_name"],
            "total_stops": values["current_stop_count"],
        })
        amenity = values.pop("amenity_type")
        values.pop("geography_type")
        values.pop("geography_name")
        values.pop("current_stop_count")
        for name, value in values.items():
            output[f"{amenity}_{name}"] = value
        output[f"{amenity}_known_or_likely_present"] = (
            output[f"{amenity}_confirmed_yes"] + output[f"{amenity}_likely_yes"]
        )
        output[f"{amenity}_known_or_likely_absent"] = (
            output[f"{amenity}_confirmed_no"] + output[f"{amenity}_likely_no"]
        )
        output[f"{amenity}_needs_consensus_or_evidence"] = (
            output["total_stops"] - output[f"{amenity}_confirmed_yes"]
            - output[f"{amenity}_confirmed_no"]
        )
    return list(grouped.values())
