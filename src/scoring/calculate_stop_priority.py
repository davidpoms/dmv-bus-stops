"""
DMV Bus Stops Intelligence Platform

Stop priority scoring engine.

Version 1 scoring:
- Highest route ridership serving the stop
- Number of routes serving the stop

Outputs:
    stop_priority_snapshots
"""

import sqlite3
import json
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[2]

DATABASE_PATH = (
    BASE_DIR
    / "src"
    / "database"
    / "dmv_bus_stops.db"
)



def calculate_scores():

    conn = sqlite3.connect(
        DATABASE_PATH
    )

    cursor = conn.cursor()


    # Clear previous snapshot
    cursor.execute(
        """
        DELETE FROM stop_priority_snapshots;
        """
    )


    # Build stop demand profile
    cursor.execute(
        """
        WITH route_demand AS (

            SELECT
                route_id,
                MAX(weekday_boardings) AS weekday_boardings

            FROM ridership_snapshots

            GROUP BY route_id

        ),


        stop_demand AS (

            SELECT

                b.id AS stop_id,

                COUNT(
                    DISTINCT sr.route_id
                ) AS route_count,


                COALESCE(
                    MAX(
                        rd.weekday_boardings
                    ),
                    0
                ) AS weekday_boardings,


                GROUP_CONCAT(
                    DISTINCT sr.route_id
                ) AS routes


            FROM bus_stops b


            LEFT JOIN stop_routes sr

                ON b.gtfs_stop_id = sr.stop_id


            LEFT JOIN route_demand rd

                ON sr.route_id = rd.route_id


            GROUP BY b.id

        )


        SELECT *
        FROM stop_demand;

        """
    )


    rows = cursor.fetchall()


    if not rows:

        print(
            "No stop data found."
        )

        return



    max_boardings = max(
        row[2]
        for row in rows
    )


    max_routes = max(
        row[1]
        for row in rows
    )


    ranked = []


    for (
        stop_id,
        route_count,
        weekday_boardings,
        routes
    ) in rows:


        ridership_score = (

            weekday_boardings
            /
            max_boardings
            *
            100

            if max_boardings

            else 0

        )


        route_score = (

            route_count
            /
            max_routes
            *
            100

            if max_routes

            else 0

        )


        priority_score = (

            ridership_score * 0.70

            +

            route_score * 0.30

        )


        factors = {

            "weekday_boardings":
                weekday_boardings,

            "routes_served":
                route_count,

            "routes":
                routes.split(",")
                if routes
                else [],

            "ridership_score":
                round(
                    ridership_score,
                    2
                ),

            "route_score":
                round(
                    route_score,
                    2
                )

        }


        ranked.append(

            (
                stop_id,
                priority_score,
                factors
            )

        )



    ranked.sort(

        key=lambda x: x[1],

        reverse=True

    )



    for rank, (
        stop_id,
        score,
        factors

    ) in enumerate(
        ranked,
        start=1
    ):


        cursor.execute(

            """
            INSERT INTO stop_priority_snapshots

            (
                stop_id,
                priority_score,
                priority_rank,
                factors
            )

            VALUES (?, ?, ?, ?)

            """,

            (

                stop_id,

                score,

                rank,

                json.dumps(
                    factors
                )

            )

        )


    conn.commit()

    conn.close()


    print(
        f"Scored {len(ranked):,} stops"
    )



if __name__ == "__main__":

    calculate_scores()
