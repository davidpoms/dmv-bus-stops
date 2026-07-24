"""
Update improvement recommendations using volunteer review data.
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


def update_recommendations():

    conn = sqlite3.connect(DATABASE_PATH)

    cursor = conn.cursor()


    cursor.execute(
        """
        SELECT

            stop_id,

            has_shelter,

            has_bench,

            concrete_pad_present,

            bench_location_feasible,

            curb_access_clear,

            notes

        FROM stop_reviews;

        """
    )


    reviews = cursor.fetchall()


    updated = 0


    for review in reviews:

        (
            stop_id,
            has_shelter,
            has_bench,
            concrete_pad_present,
            bench_location_feasible,
            curb_access_clear,
            notes
        ) = review


        recommendations = []


        if not has_bench and bench_location_feasible:

            recommendations.append(
                "bench_installation"
            )


        if not has_shelter:

            recommendations.append(
                "shelter_installation"
            )


        if not curb_access_clear:

            recommendations.append(
                "accessibility_improvement"
            )


        cursor.execute(
            """
            DELETE FROM improvement_recommendations

            WHERE physical_stop_id = ?;

            """,
            (
                stop_id,
            )
        )


        for recommendation in recommendations:

            cursor.execute(
                """
                INSERT INTO improvement_recommendations
                (
                    physical_stop_id,
                    recommendation_type,
                    priority,
                    reasons
                )

                VALUES (?, ?, ?, ?);

                """,
                (
                    stop_id,
                    recommendation,
                    "high",
                    json.dumps(
                        [
                            "Generated from volunteer review"
                        ]
                    )
                )
            )


        updated += 1


    conn.commit()

    conn.close()


    print(
        f"Updated recommendations for {updated} reviewed stops"
    )


if __name__ == "__main__":

    update_recommendations()
