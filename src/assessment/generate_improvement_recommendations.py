"""
Generate improvement recommendations from stop reviews.

Recommendations are gated by opportunity score and distinguish
confirmed absence of seating from missing evidence.
"""

import sqlite3
import json
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[2]

DATABASE_PATH = (
    BASE_DIR
    /
    "src"
    /
    "database"
    /
    "dmv_bus_stops.db"
)


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

            created_at TIMESTAMP
                DEFAULT CURRENT_TIMESTAMP

        );
        """
    )


def generate_recommendations():

    conn = sqlite3.connect(DATABASE_PATH)

    cursor = conn.cursor()

    setup_table(cursor)

    cursor.execute(
        """
        DELETE FROM improvement_recommendations;
        """
    )

    cursor.execute(
        """
        SELECT

            io.physical_stop_id,

            io.opportunity_score,

            COALESCE(ose.osm_bench, 0),

            COALESCE(ose.osm_shelter, 0),

            COALESCE(ste.gtfs_bus_stop, 0),

            sc.has_bench,

            sc.has_shelter,

            sc.ada_accessible,

            COALESCE(sc.confidence, 0),

            sc.seating_type_consensus,

            sc.rider_comfort_consensus,

            sc.hostile_design_consensus,

            sc.bench_feasible,

            COALESCE(review_counts.review_count, 0)

        FROM improvement_opportunities io

        JOIN stop_gtfs_status sgs
            ON sgs.physical_stop_id = io.physical_stop_id
           AND sgs.current_gtfs = 1

        LEFT JOIN stop_osm_evidence ose
            ON ose.stop_id = io.physical_stop_id

        LEFT JOIN stop_transit_evidence ste
            ON ste.stop_id = io.physical_stop_id

        LEFT JOIN stop_consensus sc
            ON sc.stop_id = io.physical_stop_id

        LEFT JOIN (
            SELECT
                physical_stop_id,
                COUNT(*) AS review_count
            FROM stop_observations
            WHERE source = 'community_review'
            GROUP BY physical_stop_id
        ) review_counts
            ON review_counts.physical_stop_id = io.physical_stop_id

        ORDER BY io.opportunity_score DESC;

        """
    )

    rows = cursor.fetchall()

    created = 0

    for row in rows:

        (
            stop_id,
            opportunity_score,
            osm_bench,
            osm_shelter,
            gtfs_bus_stop,

            consensus_bench,
            consensus_shelter,
            consensus_ada,

            consensus_confidence,

            seating_type,
            comfort_category,
            hostile_design,

            bench_feasible,
            review_count

        ) = row

        recommendations = []

        evidence = {
            "opportunity_score": opportunity_score,
            "osm_bench": osm_bench,
            "osm_shelter": osm_shelter,
            "gtfs_bus_stop": gtfs_bus_stop,
            "community_review_count": review_count,
            "has_bench_consensus": consensus_bench,
            "has_shelter_consensus": consensus_shelter,
            "seating_type_consensus": seating_type,
            "rider_comfort_consensus": comfort_category,
            "hostile_design_consensus": hostile_design,
            "bench_feasible": bench_feasible,
            "consensus_confidence": consensus_confidence
        }

        #
        # 1. Confirmed community evidence that no bench exists,
        #    plus confirmed feasibility.
        #
        if (
            consensus_bench == 0
            and bench_feasible == 1
        ):

            confidence = (
                "high"
                if review_count >= 2 and consensus_confidence >= 0.75
                else "medium"
            )

            recommendations.append(
                {
                    "type": "bench_installation_candidate",
                    "priority": "high",
                    "confidence": confidence,
                    "evidence": evidence,
                    "reasons": [
                        "High rider exposure opportunity score",
                        "Community evidence indicates no bench is present",
                        "Community evidence indicates bench installation is feasible"
                    ]
                }
            )

        #
        # 2. Community evidence says no bench, but feasibility
        #    has not been established.
        #
        elif (
            consensus_bench == 0
            and bench_feasible is None
        ):

            recommendations.append(
                {
                    "type": "bench_feasibility_review",
                    "priority": "medium",
                    "confidence": (
                        "medium"
                        if review_count >= 2
                        else "low"
                    ),
                    "evidence": evidence,
                    "reasons": [
                        "Community evidence indicates no bench is present",
                        "Bench installation feasibility has not been established",
                        "Additional feasibility verification is needed"
                    ]
                }
            )

        #
        # 3. Existing seating / waiting environment appears
        #    uncomfortable or hostile.
        #
        elif (
            comfort_category in ("basic", "poor")
            or hostile_design in ("separators", "sloped")
        ):

            recommendations.append(
                {
                    "type": "comfort_upgrade_candidate",
                    "priority": "medium",
                    "confidence": (
                        "high"
                        if review_count >= 2 and consensus_confidence >= 0.75
                        else "medium"
                    ),
                    "evidence": evidence,
                    "reasons": [
                        "Existing waiting conditions may not provide adequate rider comfort",
                        "Community observations indicate an opportunity to improve rider comfort"
                    ]
                }
            )

        #
        # 4. A shelter exists, reviewers have confirmed bench
        #    installation is feasible, but bench presence itself
        #    remains unresolved.
        #
        elif (
            review_count > 0
            and consensus_bench is None
            and consensus_shelter == 1
            and bench_feasible == 1
        ):

            recommendations.append(
                {
                    "type": "bench_presence_review",
                    "priority": "medium",
                    "confidence": (
                        "high"
                        if review_count >= 2 and consensus_confidence >= 0.75
                        else "medium"
                    ),
                    "evidence": evidence,
                    "reasons": [
                        "High rider exposure stop",
                        "Community reviews confirm a shelter is present",
                        "Bench presence remains unresolved",
                        "Community evidence indicates bench installation is feasible"
                    ]
                }
            )

        #
        # 5. Community reviewers have inspected the stop, but
        #    seating information remains incomplete.
        #
        elif (
            review_count > 0
            and consensus_bench is None
            and seating_type in (None, "unknown")
        ):

            recommendations.append(
                {
                    "type": "seating_review_needed",
                    "priority": "medium",
                    "confidence": (
                        "high"
                        if review_count >= 2 and consensus_confidence >= 0.75
                        else "medium"
                    ),
                    "evidence": evidence,
                    "reasons": [
                        "High rider exposure stop",
                        "Community reviews exist but seating information remains incomplete",
                        "Additional seating verification is needed"
                    ]
                }
            )

        for recommendation in recommendations:

            cursor.execute(
                """
                INSERT INTO improvement_recommendations
                (
                    physical_stop_id,
                    recommendation_type,
                    priority,
                    reasons,
                    confidence,
                    evidence
                )

                VALUES (?, ?, ?, ?, ?, ?);

                """,
                (
                    stop_id,
                    recommendation["type"],
                    recommendation["priority"],
                    json.dumps(
                        recommendation["reasons"]
                    ),
                    recommendation["confidence"],
                    json.dumps(
                        recommendation["evidence"]
                    )
                )
            )

            created += 1

    conn.commit()

    conn.close()

    print(
        f"Created {created} improvement recommendations"
    )


if __name__ == "__main__":
    generate_recommendations()
