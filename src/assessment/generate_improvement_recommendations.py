"""Generate improvements from canonical shelter/bench status."""

import json
import sqlite3
from pathlib import Path

from src.assessment.interpretation import amenity_status_sentence


BASE_DIR = Path(__file__).resolve().parents[2]
DATABASE_PATH = BASE_DIR / "src" / "database" / "dmv_bus_stops.db"
ABSENCE_STATUSES = {"confirmed_no", "likely_no"}
VERIFICATION_STATUSES = {"likely_yes", "likely_no", "conflicting", "unknown"}
INSTALLATION_OPPORTUNITY_THRESHOLD = 70
ELIGIBLE_LOCAL_NEGATIVE_SOURCES = {
    "ALEXANDRIA",
    "MONTGOMERY_COUNTY_WMATA",
    "PRINCE_GEORGES_COUNTY_THEBUS",
}
LOCAL_SOURCE_JURISDICTIONS = {
    "ALEXANDRIA": ("VA", "Alexandria"),
    "MONTGOMERY_COUNTY_WMATA": ("MD", "Montgomery"),
    "PRINCE_GEORGES_COUNTY_THEBUS": ("MD", "Prince George's"),
}
PRELIMINARY_CLEARANCE_OBSERVATIONS_REQUIRED = 3


def setup_table(cursor):
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS improvement_recommendations (
            id INTEGER PRIMARY KEY,
            physical_stop_id INTEGER NOT NULL,
            recommendation_type TEXT NOT NULL,
            priority TEXT NOT NULL,
            reasons JSON,
            confidence TEXT,
            evidence JSON,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """
    )


def source_applies_to_jurisdiction(source, state, county):
    """Fail closed when local evidence is attached outside its authority."""
    return LOCAL_SOURCE_JURISDICTIONS.get(source) == (state, county)


def build_amenity_recommendations(
    amenity, status, opportunity_score, community_observation_count,
    negative_evidence=None, bench_clearance_yes_count=0,
    bench_clearance_no_count=0,
):
    """Return coherent physical-improvement or verification recommendations."""
    recommendations = []
    wording = amenity_status_sentence(amenity, status)
    negative_evidence = negative_evidence or {}
    high_local_sources = sorted(
        set(negative_evidence.get("high_local_sources", ()))
        & ELIGIBLE_LOCAL_NEGATIVE_SOURCES
    )
    medium_local_sources = sorted(
        set(negative_evidence.get("medium_local_sources", ()))
        & ELIGIBLE_LOCAL_NEGATIVE_SOURCES
    )
    osm_negative = bool(negative_evidence.get("osm_negative"))
    community_negative = bool(negative_evidence.get("community_negative"))
    corroborating_local = bool(high_local_sources or medium_local_sources)
    evidence_classes = [
        name for name, present in (
            ("local_jurisdiction", corroborating_local),
            ("identity_matched_osm", osm_negative),
            ("community_observation", community_negative),
        ) if present
    ]
    corroborated = len(evidence_classes) >= 2
    provenance_eligible = bool(high_local_sources) or corroborated
    status_eligible = status == "confirmed_no" or (
        status == "likely_no" and provenance_eligible
    )
    preliminary_clearance_observed = (
        bench_clearance_yes_count >= PRELIMINARY_CLEARANCE_OBSERVATIONS_REQUIRED
        and bench_clearance_no_count == 0
    )

    evidence = {
        "amenity_type": amenity,
        "canonical_status": status,
        "community_observation_count": community_observation_count,
        "opportunity_score": opportunity_score,
        "negative_evidence_classes": evidence_classes,
        "eligible_local_negative_sources": sorted(
            set(high_local_sources + medium_local_sources)
        ),
        "local_match_quality": (
            "high" if high_local_sources
            else "medium" if medium_local_sources
            else None
        ),
    }
    if amenity == "bench":
        evidence.update({
            "preliminary_bench_clearance_observed":
                preliminary_clearance_observed,
            "bench_clearance_yes_observations": bench_clearance_yes_count,
            "bench_clearance_no_observations": bench_clearance_no_count,
            "engineering_feasibility_established": False,
        })

    installation_allowed = (
        status_eligible
        and opportunity_score >= INSTALLATION_OPPORTUNITY_THRESHOLD
        and (amenity != "bench" or preliminary_clearance_observed)
    )
    if installation_allowed:
        if status == "confirmed_no":
            reasons = [wording]
        elif corroborated:
            reasons = [
                f"Multiple independent evidence classes indicate no {amenity} "
                "is present, but community consensus has not been reached."
            ]
        else:
            reasons = [
                f"Supported local-jurisdiction records indicate no {amenity} "
                "is present, but community consensus has not been reached."
            ]
        reasons.append(
            f"The stop meets the current planning threshold for {amenity} "
            "installation consideration."
        )
        if amenity == "bench":
            reasons.append(
                "Multiple preliminary field observations indicate apparent "
                "pass-through clearance; engineering feasibility is not established."
            )
        recommendations.append({
            "type": f"{amenity}_installation_candidate",
            "priority": "high",
            "confidence": "high" if status == "confirmed_no" else "medium",
            "evidence": evidence,
            "reasons": reasons,
        })
        return recommendations

    verification_relevant = (
        status == "conflicting"
        or (
            status in VERIFICATION_STATUSES
            and community_observation_count > 0
            and not installation_allowed
        )
    )
    if verification_relevant:
        recommendations.append({
            "type": f"{amenity}_presence_review",
            "priority": "high" if status == "conflicting" else "medium",
            "confidence": "high" if status == "conflicting" else "medium",
            "evidence": evidence,
            "reasons": [wording, f"Additional {amenity} verification is needed"],
        })
    return recommendations


def generate_recommendations(database_path=None):
    conn = sqlite3.connect(database_path or DATABASE_PATH)
    cursor = conn.cursor()
    setup_table(cursor)
    cursor.execute("DELETE FROM improvement_recommendations")
    rows = cursor.execute(
        """
        SELECT io.physical_stop_id, io.opportunity_score,
               bench.derived_status, shelter.derived_status,
               bench.community_observation_count,
               shelter.community_observation_count,
               sc.seating_type_consensus, sc.rider_comfort_consensus,
               sc.hostile_design_consensus,
               COALESCE(clearance.yes_count, 0),
               COALESCE(clearance.no_count, 0)
        FROM improvement_opportunities io
        JOIN stop_gtfs_status sgs
          ON sgs.physical_stop_id=io.physical_stop_id
         AND sgs.current_gtfs = 1
        JOIN stop_amenity_status bench
          ON bench.physical_stop_id=io.physical_stop_id
         AND bench.amenity_type='bench'
        JOIN stop_amenity_status shelter
          ON shelter.physical_stop_id=io.physical_stop_id
         AND shelter.amenity_type='shelter'
        LEFT JOIN stop_consensus sc ON sc.stop_id=io.physical_stop_id
        LEFT JOIN (
            SELECT physical_stop_id,
                   SUM(bench_feasible='yes') yes_count,
                   SUM(bench_feasible='no') no_count
            FROM stop_observations
            WHERE source='community_review'
            GROUP BY physical_stop_id
        ) clearance ON clearance.physical_stop_id=io.physical_stop_id
        ORDER BY io.opportunity_score DESC
        """
    ).fetchall()

    created = 0
    for row in rows:
        (stop_id, score, bench_status, shelter_status, bench_observations,
         shelter_observations, seating_type, comfort_category,
         hostile_design, clearance_yes_count, clearance_no_count) = row
        local_placeholders = ",".join(
            "?" for _ in ELIGIBLE_LOCAL_NEGATIVE_SOURCES
        )
        local_rows = cursor.execute(
            f"""
            SELECT amenity_type, confidence, source
            FROM stop_amenity_evidence
            WHERE physical_stop_id=? AND present=0
              AND source IN ({local_placeholders})
              AND amenity_type IN ('bench','shelter')
            """,
            (stop_id, *sorted(ELIGIBLE_LOCAL_NEGATIVE_SOURCES)),
        ).fetchall()
        geography = cursor.execute(
            "SELECT state, county FROM stop_jurisdiction WHERE stop_id=?",
            (stop_id,),
        ).fetchone()
        state, county = geography if geography else (None, None)
        local_negative = {
            amenity: {
                "high_local_sources": {
                    source for row_amenity, confidence, source in local_rows
                    if row_amenity == amenity and confidence == "high"
                    and source_applies_to_jurisdiction(source, state, county)
                },
                "medium_local_sources": {
                    source for row_amenity, confidence, source in local_rows
                    if row_amenity == amenity and confidence == "medium"
                    and source_applies_to_jurisdiction(source, state, county)
                },
                "osm_negative": bool(cursor.execute(
                    "SELECT osm_no FROM stop_amenity_status "
                    "WHERE physical_stop_id=? AND amenity_type=?",
                    (stop_id, amenity),
                ).fetchone()[0]),
                "community_negative": cursor.execute(
                    "SELECT community_no_count FROM stop_amenity_status "
                    "WHERE physical_stop_id=? AND amenity_type=?",
                    (stop_id, amenity),
                ).fetchone()[0] > 0,
            }
            for amenity, status in (
                ("bench", bench_status), ("shelter", shelter_status)
            )
        }
        recommendations = build_amenity_recommendations(
            "bench", bench_status, score, bench_observations,
            local_negative["bench"], clearance_yes_count, clearance_no_count,
        )
        recommendations.extend(build_amenity_recommendations(
            "shelter", shelter_status, score, shelter_observations,
            local_negative["shelter"],
        ))

        if not recommendations and (
            comfort_category in ("basic", "poor")
            or hostile_design in ("separators", "sloped")
        ):
            recommendations.append({
                "type": "comfort_upgrade_candidate",
                "priority": "medium",
                "confidence": "medium",
                "evidence": {
                    "canonical_bench_status": bench_status,
                    "seating_type_consensus": seating_type,
                    "rider_comfort_consensus": comfort_category,
                    "hostile_design_consensus": hostile_design,
                    "opportunity_score": score,
                },
                "reasons": [
                    "Existing waiting conditions may not provide adequate rider comfort",
                    "Community observations indicate an opportunity to improve rider comfort",
                ],
            })

        for recommendation in recommendations:
            cursor.execute(
                """
                INSERT INTO improvement_recommendations
                    (physical_stop_id,recommendation_type,priority,reasons,confidence,evidence)
                VALUES (?,?,?,?,?,?)
                """,
                (stop_id, recommendation["type"], recommendation["priority"],
                 json.dumps(recommendation["reasons"]),
                 recommendation["confidence"],
                 json.dumps(recommendation["evidence"])),
            )
            created += 1

    conn.commit()
    conn.close()
    print(f"Created {created} improvement recommendations")


if __name__ == "__main__":
    generate_recommendations()
