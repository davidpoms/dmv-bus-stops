"""Canonical route-exposure quantities and empirical percentiles."""

import json


def percentile_by_stop(exposures):
    """Return CUME_DIST-style 0-100 ranks; ties receive the same value."""
    if not exposures:
        return {}
    normalized = {stop_id: float(value or 0) for stop_id, value in exposures.items()}
    counts = {}
    for value in normalized.values():
        counts[value] = counts.get(value, 0) + 1
    cumulative = 0
    ranks = {}
    for value in sorted(counts):
        cumulative += counts[value]
        ranks[value] = round(cumulative * 100.0 / len(normalized), 6)
    return {stop_id: ranks[value] for stop_id, value in normalized.items()}


def persist_assessment_percentiles(conn):
    """Regenerate percentiles for the canonical active assessment population."""
    columns = {row[1] for row in conn.execute("PRAGMA table_info(opportunity_assessments)")}
    if "rider_exposure_percentile" not in columns:
        conn.execute(
            "ALTER TABLE opportunity_assessments "
            "ADD COLUMN rider_exposure_percentile REAL"
        )
    rows = conn.execute(
        """
        SELECT oa.physical_stop_id, oa.combined_route_weekday_boardings,
               oa.assessment_json
        FROM opportunity_assessments oa
        JOIN stop_gtfs_status sgs
          ON sgs.physical_stop_id=oa.physical_stop_id
         AND sgs.current_gtfs=1
        """
    ).fetchall()
    ranks = percentile_by_stop({row[0]: row[1] for row in rows})
    updates = []
    for stop_id, _exposure, raw_json in rows:
        try:
            payload = json.loads(raw_json or "{}")
        except (TypeError, ValueError):
            payload = {}
        payload["rider_exposure_percentile"] = ranks[stop_id]
        updates.append((ranks[stop_id], json.dumps(payload), stop_id))
    conn.executemany(
        """
        UPDATE opportunity_assessments
        SET rider_exposure_percentile=?, assessment_json=?
        WHERE physical_stop_id=?
        """,
        updates,
    )
    return ranks
