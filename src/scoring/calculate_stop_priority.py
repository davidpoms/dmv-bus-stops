"""
DMV Bus Stops Intelligence Platform

Stop priority scoring engine.

Scoring inputs:
- GTFS stop-route relationships
- WMATA ridership snapshots

Normalization:
- Ridership snapshots contain monthly weekday totals
- Convert to average weekday daily demand

Output:
- stop_priority_snapshots
"""

import sqlite3
import json
import calendar
from datetime import datetime
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[2]

DATABASE_PATH = (
    BASE_DIR
    / "src"
    / "database"
    / "dmv_bus_stops.db"
)



def weekdays_in_month(date_string):

    """
    Calculate number of weekdays
    in the reporting month.
    """

    date = datetime.strptime(
        date_string,
        "%Y-%m-%d"
    )

    total = 0

    days = calendar.monthrange(
        date.year,
        date.month
    )[1]


    for day in range(
        1,
        days + 1
    ):

        weekday = datetime(
            date.year,
            date.month,
            day
        ).weekday()


        if weekday < 5:
            total += 1


    return total



def calculate_scores():

    conn = sqlite3.connect(
        DATABASE_PATH
    )

    cursor = conn.cursor()


    cursor.execute(
        """
        DELETE FROM stop_priority_snapshots;
        """
    )


    cursor.execute(
        """
        WITH route_demand AS (

            SELECT

                route_id,

                MAX(
                    weekday_boardings
                ) AS monthly_weekday_boardings,

                MAX(
                    period
                ) AS period


            FROM ridership_snapshots

            GROUP BY route_id

        ),


        normalized_routes AS (

            SELECT

                route_id,

                monthly_weekday_boardings,

                monthly_weekday_boardings
                /
                (
                    CASE

                    WHEN period IS NOT NULL

                    THEN

                        (
                        CAST(
                            strftime(
                                '%d',
                                date(
                                    period,
                                    'start of month',
                                    '+1 month',
                                    '-1 day'
                                )
                            )
                            AS INTEGER
                        )
                        )

                    ELSE 1

                    END
                )

                AS daily_estimate,


                period


            FROM route_demand

        )


        SELECT

            b.id,

            COUNT(
                DISTINCT sr.route_id
            ) AS routes_served,


            MAX(
                nr.daily_estimate
            ) AS average_daily_boardings,


            MAX(
                nr.monthly_weekday_boardings
            ) AS monthly_weekday_boardings,


            GROUP_CONCAT(
                DISTINCT sr.route_id
            ) AS routes


        FROM bus_stops b


        LEFT JOIN stop_routes sr

            ON b.gtfs_stop_id = sr.stop_id


        LEFT JOIN normalized_routes nr

            ON sr.route_id = nr.route_id


        GROUP BY b.id;

        """
    )


    rows = cursor.fetchall()


    if not rows:

        print(
            "No data found."
        )

        return



    max_daily = max(
        row[2] or 0
        for row in rows
    )


    max_routes = max(
        row[1] or 0
        for row in rows
    )


    ranked = []


    for row in rows:

        (
            stop_id,
            routes_served,
            daily_boardings,
            monthly_boardings,
            routes

        ) = row


        daily_boardings = (
            daily_boardings or 0
        )


        routes_served = (
            routes_served or 0
        )


        ridership_score = (

            daily_boardings
            /
            max_daily
            *
            100

            if max_daily

            else 0

        )


        route_score = (

            routes_served
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

            "monthly_weekday_boardings":
                monthly_boardings,

            "average_daily_weekday_boardings":
                round(
                    daily_boardings,
                    2
                ),

            "routes_served":
                routes_served,

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
