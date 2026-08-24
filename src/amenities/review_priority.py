"""Derived amenity verification priority; never an amenity truth source."""

from datetime import datetime, timezone
import json


SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS stop_amenity_review_priority (
    physical_stop_id INTEGER NOT NULL,
    amenity_type TEXT NOT NULL CHECK (amenity_type IN ('shelter','bench')),
    derived_status TEXT NOT NULL,
    consensus_status TEXT NOT NULL,
    workflow_state TEXT NOT NULL,
    rider_exposure_percentile REAL NOT NULL,
    evidence_conflict_component REAL NOT NULL,
    consensus_progress_component REAL NOT NULL,
    exposure_component REAL NOT NULL,
    review_priority_score REAL NOT NULL,
    priority_tier TEXT NOT NULL,
    evidence_conflict INTEGER NOT NULL,
    consensus_conflicts_with_other_evidence INTEGER NOT NULL,
    community_observation_count INTEGER NOT NULL,
    observations_needed_for_consensus INTEGER NOT NULL,
    rationale TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    PRIMARY KEY (physical_stop_id, amenity_type)
);
CREATE INDEX IF NOT EXISTS idx_amenity_review_priority_order
ON stop_amenity_review_priority(priority_tier, review_priority_score DESC);
"""


def _priority_values(status):
    derived = status["derived_status"]
    observations = status["community_observation_count"]
    yes_count = status["community_yes_count"]
    no_count = status["community_no_count"]
    consensus = status["consensus_status"] in ("yes", "no")
    if consensus:
        return "consensus_reached", 0, 0, "resolved"
    if derived == "conflicting":
        return "conflicting", 100, 0, "critical"
    if observations == 2 and max(yes_count, no_count) == 2:
        return "one_observation_short", 0, 80, "high"
    if derived in ("likely_yes", "likely_no"):
        return "likely_without_consensus", 60, 0, "medium"
    if observations:
        return "unknown_with_evidence", 0, 40, "medium"
    return "no_evidence", 0, 20, "low"


def build_priority_row(status, percentile, updated_at=None):
    workflow, evidence_component, consensus_component, tier = _priority_values(status)
    exposure_component = 0 if tier == "resolved" else float(percentile or 0) / 10.0
    score = evidence_component + consensus_component + exposure_component
    needed = max(0, 3 - int(status["community_observation_count"] or 0))
    reason = {
        "workflow_state": workflow,
        "amenity_status": status["derived_status"],
        "rider_exposure_percentile": float(percentile or 0),
        "summary": (
            "Community consensus reached."
            if workflow == "consensus_reached"
            else f"{workflow.replace('_', ' ')}; rider exposure percentile "
                 f"{round(float(percentile or 0))}."
        ),
    }
    return {
        "physical_stop_id": status["physical_stop_id"],
        "amenity_type": status["amenity_type"],
        "derived_status": status["derived_status"],
        "consensus_status": status["consensus_status"],
        "workflow_state": workflow,
        "rider_exposure_percentile": float(percentile or 0),
        "evidence_conflict_component": evidence_component,
        "consensus_progress_component": consensus_component,
        "exposure_component": exposure_component,
        "review_priority_score": score,
        "priority_tier": tier,
        "evidence_conflict": status["evidence_conflict"],
        "consensus_conflicts_with_other_evidence":
            status["consensus_conflicts_with_other_evidence"],
        "community_observation_count": status["community_observation_count"],
        "observations_needed_for_consensus": needed,
        "rationale": json.dumps(reason, sort_keys=True),
        "updated_at": updated_at or datetime.now(timezone.utc).isoformat(),
    }


UPSERT_SQL = """
INSERT INTO stop_amenity_review_priority (
 physical_stop_id,amenity_type,derived_status,consensus_status,workflow_state,
 rider_exposure_percentile,evidence_conflict_component,
 consensus_progress_component,exposure_component,review_priority_score,
 priority_tier,evidence_conflict,consensus_conflicts_with_other_evidence,
 community_observation_count,observations_needed_for_consensus,rationale,updated_at
) VALUES (
 :physical_stop_id,:amenity_type,:derived_status,:consensus_status,:workflow_state,
 :rider_exposure_percentile,:evidence_conflict_component,
 :consensus_progress_component,:exposure_component,:review_priority_score,
 :priority_tier,:evidence_conflict,:consensus_conflicts_with_other_evidence,
 :community_observation_count,
 :observations_needed_for_consensus,:rationale,:updated_at)
ON CONFLICT(physical_stop_id, amenity_type) DO UPDATE SET
 derived_status=excluded.derived_status, consensus_status=excluded.consensus_status,
 workflow_state=excluded.workflow_state,
 rider_exposure_percentile=excluded.rider_exposure_percentile,
 evidence_conflict_component=excluded.evidence_conflict_component,
 consensus_progress_component=excluded.consensus_progress_component,
 exposure_component=excluded.exposure_component,
 review_priority_score=excluded.review_priority_score,
 priority_tier=excluded.priority_tier, evidence_conflict=excluded.evidence_conflict,
 consensus_conflicts_with_other_evidence=excluded.consensus_conflicts_with_other_evidence,
 community_observation_count=excluded.community_observation_count,
 observations_needed_for_consensus=excluded.observations_needed_for_consensus,
 rationale=excluded.rationale, updated_at=excluded.updated_at
"""


def rebuild_review_priority(conn, physical_stop_id=None):
    conn.executescript(SCHEMA_SQL)
    columns = {row[1] for row in conn.execute(
        "PRAGMA table_info(stop_amenity_review_priority)"
    )}
    if "consensus_conflicts_with_other_evidence" not in columns:
        conn.execute(
            "ALTER TABLE stop_amenity_review_priority ADD COLUMN "
            "consensus_conflicts_with_other_evidence INTEGER NOT NULL DEFAULT 0"
        )
    params = () if physical_stop_id is None else (physical_stop_id,)
    where = "" if physical_stop_id is None else "WHERE a.physical_stop_id=?"
    conn.row_factory = __import__("sqlite3").Row
    statuses = conn.execute(
        f"""SELECT a.* FROM stop_amenity_status a
        JOIN stop_gtfs_status s ON s.physical_stop_id=a.physical_stop_id
                               AND s.current_gtfs=1 {where}""", params
    ).fetchall()
    percentiles = dict(conn.execute(
        "SELECT physical_stop_id, COALESCE(rider_exposure_percentile,0) "
        "FROM opportunity_assessments"
    ))
    rows = [build_priority_row(row, percentiles.get(row["physical_stop_id"], 0))
            for row in statuses]
    if physical_stop_id is None:
        expected = conn.execute(
            "SELECT COUNT(*)*2 FROM stop_gtfs_status WHERE current_gtfs=1"
        ).fetchone()[0]
        if len(rows) != expected:
            raise RuntimeError(
                f"Review priority produced {len(rows)} rows; expected {expected}"
            )
    elif len(rows) not in (0, 2):
        raise RuntimeError(
            f"Targeted review priority produced {len(rows)} rows for stop "
            f"{physical_stop_id}; expected 0 or 2"
        )
    with conn:
        if physical_stop_id is None:
            conn.execute("DELETE FROM stop_amenity_review_priority")
        else:
            conn.execute("DELETE FROM stop_amenity_review_priority WHERE physical_stop_id=?",
                         (physical_stop_id,))
        conn.executemany(UPSERT_SQL, rows)
    return rows


def refresh_review_queue_stop(conn, physical_stop_id):
    """Refresh a pre-existing stop-level queue rollup without changing assignments."""
    if not conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='review_queue'"
    ).fetchone():
        return
    rows = conn.execute(
        """
        SELECT amenity_type, review_priority_score, rider_exposure_percentile,
               json_extract(rationale, '$.summary')
        FROM stop_amenity_review_priority
        WHERE physical_stop_id=? AND workflow_state!='consensus_reached'
        ORDER BY review_priority_score DESC,
                 CASE amenity_type WHEN 'shelter' THEN 0 ELSE 1 END
        """,
        (physical_stop_id,),
    ).fetchall()
    shelter = next((row[1] for row in rows if row[0] == "shelter"), None)
    bench = next((row[1] for row in rows if row[0] == "bench"), None)
    if not rows:
        conn.execute(
            "UPDATE review_queue SET review_status='resolved', verification_needed=0, "
            "review_priority_score=0, priority_amenity=NULL, priority_reason=? "
            "WHERE physical_stop_id=?",
            ("Shelter and bench community consensus reached.", physical_stop_id),
        )
        return
    top = rows[0]
    conn.execute(
        """
        UPDATE review_queue SET review_status='pending', verification_needed=1,
          review_priority_score=?, priority_amenity=?,
          shelter_review_priority=?, bench_review_priority=?,
          rider_exposure_percentile=?, priority_reason=?
        WHERE physical_stop_id=?
        """,
        (top[1], top[0], shelter, bench, top[2], top[3], physical_stop_id),
    )


def refresh_after_community_mutation(conn, physical_stop_id):
    """Target the two canonical status/priority rows and queue rollup for one stop."""
    from src.amenities.status_synthesis import refresh_stop_amenity_status

    refresh_stop_amenity_status(conn, physical_stop_id)
    rebuild_review_priority(conn, physical_stop_id)
    with conn:
        refresh_review_queue_stop(conn, physical_stop_id)
