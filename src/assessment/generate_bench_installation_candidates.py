"""Build the first-class bench installation candidate product."""

import json
import sqlite3
from pathlib import Path

from src.assessment.amenity_recommendation_policy import (
    ELIGIBLE_LOCAL_NEGATIVE_SOURCES,
    LOCAL_SOURCE_PUBLIC_LABELS,
    classify_negative_evidence,
    source_applies_to_jurisdiction,
)

BASE_DIR = Path(__file__).resolve().parents[2]
DATABASE_PATH = BASE_DIR / "src" / "database" / "dmv_bus_stops.db"
INSTALLATION_OPPORTUNITY_THRESHOLD = 70


def setup_table(cursor):
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS bench_installation_candidates (
            physical_stop_id INTEGER PRIMARY KEY,
            candidate_rank INTEGER NOT NULL,
            primary_name TEXT,
            state TEXT,
            county TEXT,
            municipality TEXT,
            canonical_status TEXT NOT NULL,
            evidence_strength TEXT NOT NULL,
            local_negative_sources TEXT NOT NULL,
            osm_negative INTEGER NOT NULL,
            community_negative_count INTEGER NOT NULL,
            community_consensus_status TEXT NOT NULL,
            opportunity_score REAL NOT NULL,
            rider_exposure_percentile REAL NOT NULL,
            review_priority_score REAL,
            review_priority_tier TEXT,
            clearance_status TEXT NOT NULL,
            clearance_yes_count INTEGER NOT NULL,
            clearance_no_count INTEGER NOT NULL,
            recommendation_confidence TEXT NOT NULL,
            rationale TEXT NOT NULL,
            next_action TEXT NOT NULL,
            verification_still_needed INTEGER NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
    )
    cursor.execute(
        """CREATE INDEX IF NOT EXISTS idx_bench_candidates_order
           ON bench_installation_candidates(
               next_action, opportunity_score DESC,
               rider_exposure_percentile DESC, physical_stop_id
           )"""
    )


def classify_clearance(yes_count, no_count):
    """Interpret field answers as preliminary clearance observations only."""
    if no_count:
        return "observed_constrained"
    if yes_count:
        return "observed_clear"
    return "unknown"


def classify_next_action(canonical_status, clearance_status):
    if clearance_status == "unknown":
        return "collect_clearance_observation"
    if canonical_status == "confirmed_no" and clearance_status == "observed_clear":
        return "candidate_ready_for_planning"
    return "planning_review"


def ranking_key(candidate):
    """Rank readiness first, planning value second, exposure only as a tie-break."""
    action_tier = {
        "candidate_ready_for_planning": 0,
        "planning_review": 1,
        "collect_clearance_observation": 2,
    }
    evidence_tier = {
        "confirmed_absence": 0,
        "corroborated_likely_absence": 1,
        "supported_local_likely_absence": 2,
    }
    return (
        action_tier[candidate["next_action"]],
        evidence_tier[candidate["evidence_strength"]],
        -candidate["opportunity_score"],
        -candidate["rider_exposure_percentile"],
        candidate["physical_stop_id"],
    )


def build_candidate(
    *, physical_stop_id, primary_name, state, county, municipality,
    canonical_status, consensus_status, community_negative_count,
    evidence_conflict, consensus_conflict, opportunity_score,
    rider_exposure_percentile, review_priority_score, review_priority_tier,
    clearance_yes_count, clearance_no_count, negative_evidence,
):
    policy = classify_negative_evidence(canonical_status, negative_evidence)
    if (
        not policy["eligible"]
        or opportunity_score < INSTALLATION_OPPORTUNITY_THRESHOLD
        or evidence_conflict
        or consensus_conflict
    ):
        return None
    clearance_status = classify_clearance(
        clearance_yes_count, clearance_no_count
    )
    next_action = classify_next_action(canonical_status, clearance_status)
    if canonical_status == "confirmed_no":
        basis = "Canonical community consensus indicates no bench is present."
    elif policy["evidence_strength"] == "corroborated_likely_absence":
        basis = (
            "Multiple independent evidence classes indicate a bench is likely "
            "absent; absence is not yet confirmed."
        )
    else:
        basis = (
            "Supported local-jurisdiction inventory indicates a bench is likely "
            "absent; absence is not yet confirmed."
        )
    if clearance_status == "unknown":
        clearance = "Preliminary pass-through clearance has not been observed."
    elif clearance_status == "observed_clear":
        clearance = (
            "A field observation indicates apparent pass-through clearance; "
            "engineering feasibility is not established."
        )
    else:
        clearance = (
            "A field observation indicates constrained pass-through clearance; "
            "planning review is required."
        )
    return {
        "physical_stop_id": physical_stop_id,
        "primary_name": primary_name,
        "state": state,
        "county": county,
        "municipality": municipality,
        "canonical_status": canonical_status,
        "evidence_strength": policy["evidence_strength"],
        "local_negative_sources": policy["eligible_local_negative_sources"],
        "local_source_labels": [
            LOCAL_SOURCE_PUBLIC_LABELS[source]
            for source in policy["eligible_local_negative_sources"]
        ],
        "osm_negative": policy["osm_negative"],
        "community_negative_count": community_negative_count,
        "community_consensus_status": consensus_status,
        "opportunity_score": opportunity_score,
        "rider_exposure_percentile": rider_exposure_percentile,
        "review_priority_score": review_priority_score,
        "review_priority_tier": review_priority_tier,
        "clearance_status": clearance_status,
        "clearance_yes_count": clearance_yes_count,
        "clearance_no_count": clearance_no_count,
        "recommendation_confidence": policy["recommendation_confidence"],
        "rationale": [basis, clearance],
        "next_action": next_action,
        "verification_still_needed": canonical_status == "likely_no",
    }


def generate_candidates(database_path=None):
    conn = sqlite3.connect(database_path or DATABASE_PATH)
    cursor = conn.cursor()
    setup_table(cursor)
    cursor.execute("DELETE FROM bench_installation_candidates")
    rows = cursor.execute(
        """
        SELECT g.physical_stop_id, ps.primary_name, j.state, j.county,
               j.municipality, a.derived_status, a.consensus_status,
               a.community_no_count, a.osm_no, a.evidence_conflict,
               a.consensus_conflicts_with_other_evidence,
               io.opportunity_score, oa.rider_exposure_percentile,
               rp.review_priority_score, rp.priority_tier,
               COALESCE(clearance.yes_count,0), COALESCE(clearance.no_count,0)
        FROM stop_gtfs_status g
        JOIN physical_stops ps ON ps.id=g.physical_stop_id
        JOIN stop_jurisdiction j ON j.stop_id=g.physical_stop_id
        JOIN stop_amenity_status a
          ON a.physical_stop_id=g.physical_stop_id AND a.amenity_type='bench'
        JOIN improvement_opportunities io
          ON io.physical_stop_id=g.physical_stop_id
        JOIN opportunity_assessments oa
          ON oa.physical_stop_id=g.physical_stop_id
        LEFT JOIN stop_amenity_review_priority rp
          ON rp.physical_stop_id=g.physical_stop_id AND rp.amenity_type='bench'
        LEFT JOIN (
            SELECT physical_stop_id,
                   SUM(bench_feasible='yes') yes_count,
                   SUM(bench_feasible='no') no_count
            FROM stop_observations WHERE source='community_review'
            GROUP BY physical_stop_id
        ) clearance ON clearance.physical_stop_id=g.physical_stop_id
        WHERE g.current_gtfs=1
          AND a.derived_status IN ('confirmed_no','likely_no')
          AND a.local_yes_count=0 AND a.osm_yes=0 AND a.community_yes_count=0
        """
    ).fetchall()
    candidates = []
    placeholders = ",".join("?" for _ in ELIGIBLE_LOCAL_NEGATIVE_SOURCES)
    for row in rows:
        (stop_id, name, state, county, municipality, status, consensus,
         community_no, osm_no, evidence_conflict, consensus_conflict, score,
         exposure, review_score, review_tier, clearance_yes,
         clearance_no) = row
        local_rows = cursor.execute(
            f"""SELECT source,confidence FROM stop_amenity_evidence
                WHERE physical_stop_id=? AND amenity_type='bench' AND present=0
                  AND source IN ({placeholders})""",
            (stop_id, *sorted(ELIGIBLE_LOCAL_NEGATIVE_SOURCES)),
        ).fetchall()
        negative = {
            "high_local_sources": {
                source for source, confidence in local_rows
                if confidence == "high"
                and source_applies_to_jurisdiction(source, state, county)
            },
            "medium_local_sources": {
                source for source, confidence in local_rows
                if confidence == "medium"
                and source_applies_to_jurisdiction(source, state, county)
            },
            "osm_negative": bool(osm_no),
            "community_negative": community_no > 0,
        }
        candidate = build_candidate(
            physical_stop_id=stop_id, primary_name=name, state=state,
            county=county, municipality=municipality,
            canonical_status=status, consensus_status=consensus,
            community_negative_count=community_no,
            evidence_conflict=evidence_conflict,
            consensus_conflict=consensus_conflict,
            opportunity_score=score, rider_exposure_percentile=exposure,
            review_priority_score=review_score,
            review_priority_tier=review_tier,
            clearance_yes_count=clearance_yes,
            clearance_no_count=clearance_no, negative_evidence=negative,
        )
        if candidate:
            candidates.append(candidate)
    candidates.sort(key=ranking_key)
    for rank, candidate in enumerate(candidates, 1):
        cursor.execute(
            """
            INSERT INTO bench_installation_candidates VALUES (
                ?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,
                strftime('%Y-%m-%dT%H:%M:%SZ','now')
            )
            """,
            (
                candidate["physical_stop_id"], rank, candidate["primary_name"],
                candidate["state"], candidate["county"], candidate["municipality"],
                candidate["canonical_status"], candidate["evidence_strength"],
                json.dumps(candidate["local_source_labels"]),
                int(candidate["osm_negative"]), candidate["community_negative_count"],
                candidate["community_consensus_status"],
                candidate["opportunity_score"], candidate["rider_exposure_percentile"],
                candidate["review_priority_score"], candidate["review_priority_tier"],
                candidate["clearance_status"], candidate["clearance_yes_count"],
                candidate["clearance_no_count"],
                candidate["recommendation_confidence"],
                json.dumps(candidate["rationale"]), candidate["next_action"],
                int(candidate["verification_still_needed"]),
            ),
        )
    conn.commit()
    conn.close()
    print(f"Created {len(candidates):,} bench installation candidates")
    return len(candidates)


if __name__ == "__main__":
    generate_candidates()
