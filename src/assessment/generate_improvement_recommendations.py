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

            sr.stop_id,

            sr.has_shelter,

            sr.has_bench,

            sr.bench_location_feasible,

            sr.concrete_pad_present,

            sr.curb_access_clear,

            sr.bus_ramp_access_clear,

            sr.landing_zone_clear,

            sr.notes,

            io.opportunity_score

        FROM stop_reviews sr

        LEFT JOIN improvement_opportunities io

            ON sr.stop_id = io.physical_stop_id;

        """
    )


    rows = cursor.fetchall()


    created = 0


    for row in rows:

        (
            stop_id,
            has_shelter,
            has_bench,
            bench_feasible,
            concrete_pad,
            curb_access,
            ramp_access,
            landing_clear,
            notes,
            score
        ) = row


        recommendations = []


        if not has_bench and bench_feasible:

            recommendations.append(
                {
                    "type": "bench_installation",
                    "priority": "high",
                    "reasons": [
                        "No existing bench",
                        "Space appears available"
                    ]
                }
            )


        if not has_shelter and score and score >= 80:

            recommendations.append(
                {
                    "type": "shelter_installation",
                    "priority": "high",
                    "reasons": [
                        "High improvement opportunity score",
                        "No existing shelter"
                    ]
                }
            )


        accessibility_issues = []


        if not curb_access:

            accessibility_issues.append(
                "curb access unclear"
            )

        if not ramp_access:

            accessibility_issues.append(
                "bus ramp access unclear"
            )

        if not landing_clear:

            accessibility_issues.append(
                "landing zone unclear"
            )


        if accessibility_issues:

            recommendations.append(
                {
                    "type": "accessibility_review",
                    "priority": "medium",
                    "reasons": accessibility_issues
                }
            )


        for recommendation in recommendations:

            cursor.execute(
                """
                INSERT INTO improvement_recommendations (

                    physical_stop_id,

                    recommendation_type,

                    priority,

                    reasons

                )

                VALUES (?, ?, ?, ?);

                """,
                (
                    stop_id,
                    recommendation["type"],
                    recommendation["priority"],
                    json.dumps(
                        recommendation["reasons"]
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
