"""
Generate improvement recommendations from stop reviews.

Converts volunteer observations into actionable
bus stop improvement opportunities.
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

            COALESCE(ose.osm_bench,0),

            COALESCE(ose.osm_shelter,0),

            COALESCE(ste.gtfs_bus_stop,0),

            COALESCE(sc.has_bench, NULL),

            COALESCE(sc.has_shelter, NULL),

            COALESCE(sc.ada_accessible, NULL),

            COALESCE(sc.confidence,0),

            COALESCE(sc.seating_type_consensus, NULL),

            COALESCE(sc.rider_comfort_consensus, NULL),

            COALESCE(sc.hostile_design_consensus, NULL),

            COALESCE(sc.bench_feasible, NULL)


        FROM improvement_opportunities io

        LEFT JOIN stop_osm_evidence ose

            ON ose.stop_id = io.physical_stop_id

        LEFT JOIN stop_transit_evidence ste

            ON ste.stop_id = io.physical_stop_id

        LEFT JOIN stop_consensus sc

            ON sc.stop_id = io.physical_stop_id

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

            bench_feasible

        ) = row


        recommendations = []



        if opportunity_score >= 70:

            evidence = {
                "opportunity_score": opportunity_score,
                "osm_bench": osm_bench,
                "osm_shelter": osm_shelter,
                "gtfs_bus_stop": gtfs_bus_stop,
                "seating_type_consensus": seating_type,
                "rider_comfort_consensus": comfort_category,
                "hostile_design_consensus": hostile_design,
                "bench_feasible": bench_feasible
            }


            if (
                seating_type == "none"
                or (
                    consensus_bench is False
                    and consensus_shelter is False
                )
                or (
                    seating_type is None
                    and not osm_bench
                    and not osm_shelter
                )
            ):

                recommendations.append(
                    {
                        "type": "bench_installation_candidate",
                        "priority": "high",
                        "confidence": "low",
                        "evidence": evidence,
                        "reasons": [
                            "High rider exposure opportunity score",
                            "No confirmed comfortable seating available",
                            "Evaluate bench installation feasibility"
                        ]
                    }
                )


            elif (
                comfort_category in ("basic", "poor")
                or hostile_design in ("separators", "sloped")
                or seating_type == "shelter_bench"
            ):

                recommendations.append(
                    {
                        "type": "comfort_upgrade_candidate",
                        "priority": "medium",
                        "confidence": "medium",
                        "evidence": evidence,
                        "reasons": [
                            "Existing seating is present but may not provide comfortable waiting conditions",
                            "Shelter seating does not necessarily represent high-quality seating",
                            "Evaluate opportunities for rider comfort improvements"
                        ]
                    }
                )


            elif seating_type in (None, "unknown"):

                recommendations.append(
                    {
                        "type": "seating_review_needed",
                        "priority": "medium",
                        "confidence": "low",
                        "evidence": evidence,
                        "reasons": [
                            "High rider exposure stop",
                            "Seating conditions require additional verification"
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
