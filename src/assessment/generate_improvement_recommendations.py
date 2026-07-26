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

            COALESCE(ste.gtfs_bus_stop,0)


        FROM improvement_opportunities io

        LEFT JOIN stop_osm_evidence ose

            ON ose.stop_id = io.physical_stop_id

        LEFT JOIN stop_transit_evidence ste

            ON ste.stop_id = io.physical_stop_id

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
            gtfs_bus_stop
        ) = row


        recommendations = []


        if opportunity_score >= 70 and not osm_bench:

            recommendations.append(
                {
                    "type": "bench_review",
                    "priority": "high",
                    "confidence": "medium",

                    "evidence": {
                        "opportunity_score": opportunity_score,
                        "osm_bench": osm_bench,
                        "osm_shelter": osm_shelter,
        "gtfs_bus_stop": gtfs_bus_stop
                    },

                    "reasons": [
                        "High route exposure opportunity score",
                        ("No bench mapped at active transit stop" if gtfs_bus_stop == 1 else "No bench mapped at active transit stop" if gtfs_bus_stop else "No bench mapped in OSM"),
                        "Volunteer verification needed"
                    ]
                }
            )


        if opportunity_score >= 80 and not osm_shelter:

            recommendations.append(
                {
                    "type": "shelter_review",
                    "priority": "high",
                    "confidence": "medium",

                    "evidence": {
                        "opportunity_score": opportunity_score,
                        "osm_bench": osm_bench,
                        "osm_shelter": osm_shelter,
        "gtfs_bus_stop": gtfs_bus_stop
                    },

                    "reasons": [
                        "High route exposure opportunity score",
                        ("No shelter mapped at active transit stop" if gtfs_bus_stop == 1 else "No shelter mapped at active transit stop" if gtfs_bus_stop else "No shelter mapped in OSM"),
                        "Shelter opportunity requires review"
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
