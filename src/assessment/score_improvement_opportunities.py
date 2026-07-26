"""
Score physical bus stop improvement opportunities.

Creates a review priority ranking based on:

- passenger demand
- route connectivity
- stop complexity

This is an evidence prioritization layer,
not a final recommendation engine.
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
        CREATE TABLE IF NOT EXISTS improvement_opportunities (

            id INTEGER PRIMARY KEY,

            physical_stop_id INTEGER NOT NULL,

            opportunity_score REAL,

            priority_rank INTEGER,

            factors JSON,

            created_at TIMESTAMP
                DEFAULT CURRENT_TIMESTAMP

        );
        """
    )


    cursor.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_opportunity_rank

        ON improvement_opportunities(
            priority_rank
        );
        """
    )



def normalize(value, maximum):

    if not value or maximum == 0:

        return 0

    return (
        value / maximum
    ) * 100



def score_opportunities():

    conn = sqlite3.connect(
        DATABASE_PATH
    )

    cursor = conn.cursor()


    setup_table(
        cursor
    )


    cursor.execute(
        """
        DELETE FROM improvement_opportunities;
        """
    )


    cursor.execute(
        """
        SELECT

            physical_stop_id,

            combined_route_weekday_boardings,

            highest_route_weekday_boardings,

            routes_served,

            wmata_stop_records


        FROM opportunity_assessments;
        """
    )


    rows = cursor.fetchall()


    if not rows:

        print(
            "No assessments found."
        )

        return



    max_daily = max(
        row[1]
        for row in rows
    )


    max_routes = max(
        row[3]
        for row in rows
    )


    max_records = max(
        row[4]
        for row in rows
    )



    scored = []



    for row in rows:

        (
            physical_stop_id,

            total_daily,

            highest_route,

            routes,

            records

        ) = row



        route_exposure_score = normalize(
            total_daily,
            max_daily
        )


        connectivity_score = normalize(
            routes,
            max_routes
        )


        physical_complexity_score = normalize(
            records,
            max_records
        )


        opportunity_score = (

            route_exposure_score * 0.70

            +

            connectivity_score * 0.25

            +

            physical_complexity_score * 0.05

        )


        factors = {

            "route_exposure": {

                "combined_route_weekday_boardings":
                    round(
                        total_daily,
                        2
                    ),

                "highest_route_weekday_boardings":
                    round(
                        highest_route,
                        2
                    ),

                "score":
                    round(
                        route_exposure_score,
                        2
                    )

            },


            "network": {

                "routes_served":
                    routes,

                "score":
                    round(
                        connectivity_score,
                        2
                    )

            },


            "physical": {

                "wmata_stop_records":
                    records,

                "score":
                    round(
                        physical_complexity_score,
                        2
                    )

            }

        }


        scored.append(
            (
                physical_stop_id,
                opportunity_score,
                factors
            )
        )



    scored.sort(
        key=lambda x: x[1],
        reverse=True
    )


    for rank, item in enumerate(
        scored,
        start=1
    ):

        cursor.execute(
            """
            INSERT INTO improvement_opportunities

            (

                physical_stop_id,

                opportunity_score,

                priority_rank,

                factors

            )

            VALUES (?, ?, ?, ?);

            """,
            (

                item[0],

                round(
                    item[1],
                    2
                ),

                rank,

                json.dumps(
                    item[2]
                )

            )
        )


    conn.commit()


    print(
        f"Scored {len(scored):,} physical stops"
    )


    print(
        "Top 10 opportunities:"
    )


    for item in scored[:10]:

        print(
            item[0],
            round(item[1], 2)
        )


    conn.close()



if __name__ == "__main__":

    score_opportunities()
