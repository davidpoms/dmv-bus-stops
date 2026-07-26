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

            physical_stop_id,

            shelter_present,

            bench_present,

            bench_feasible,

            notes

        FROM stop_observations;

        """
    )


    reviews = cursor.fetchall()


    updated = 0


    for review in reviews:

        (
            physical_stop_id,
            shelter_present,
            bench_present,
            bench_feasible,
            notes
        ) = review


        recommendations = []


        if bench_present == 'no' and bench_feasible == 'yes':

            recommendations.append(
                "bench_installation"
            )


        if shelter_present == 'no':

            recommendations.append(
                "shelter_installation"
            )



        cursor.execute(
            """
            DELETE FROM improvement_recommendations

            WHERE physical_stop_id = ?;

            """,
            (
                physical_stop_id,
            )
        )


        for recommendation in recommendations:

            cursor.execute(
                """
                INSERT INTO improvement_recommendations
                (
                    physical_physical_stop_id,
                    recommendation_type,
                    priority,
                    reasons
                )

                VALUES (?, ?, ?, ?);

                """,
                (
                    physical_stop_id,
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
