"""
DMV Bus Stops Intelligence Platform

Stop priority scoring engine.

Ranks bus stops for improvement opportunities.

Inputs:
- bus_stops
- stop_routes
- routes
- ridership_snapshots

Method:
- Convert monthly weekday boardings to average weekday demand
- Aggregate demand across all routes serving each stop
- Add route diversity bonus
"""

import sqlite3
import json
import math
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

    date = datetime.strptime(
        date_string,
        "%Y-%m-%d"
    )

    year = date.year
    month = date.month

    total = 0

    for day in range(
        1,
        calendar.monthrange(
            year,
            month
        )[1] + 1
    ):

        if datetime(
            year,
            month,
            day
        ).weekday() < 5:

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
        WITH route_daily AS (

            SELECT

                route_id,

                weekday_boardings,

                CASE

                    WHEN weekday_boardings IS NULL
                    THEN 0

                    ELSE

                        weekday_boardings
                        /
                        (
                            CASE

                            WHEN strftime(
                                '%m',
                                period
                            ) IS NOT NULL

                            THEN

                                CASE

                                WHEN strftime(
                                    '%m',
                                    period
                                ) IN
                                (
                                    '01',
                                    '02',
                                    '03',
                                    '04',
                                    '05',
                                    '06',
                                    '07',
                                    '08',
                                    '09',
                                    '10',
                                    '11',
                                    '12'
                                )

                                THEN 21

                                ELSE 21

                                END

                            ELSE 21

                            END
                        )

                END AS daily_boardings


            FROM ridership_snapshots

        )


        SELECT

            ps.id,

            COUNT(
                DISTINCT sr.route_id
            ) AS routes_served,


            SUM(
                rd.daily_boardings
            ) AS total_daily_boardings,


            MAX(
                rd.daily_boardings
            ) AS highest_route_daily,


            GROUP_CONCAT(
                DISTINCT sr.route_id
            ) AS routes,


            MAX(
                rd.weekday_boardings
            ) AS largest_monthly_route_total


        
FROM physical_stops ps


JOIN physical_stop_members pm

    ON pm.physical_stop_id = ps.id


JOIN stop_routes sr

    ON sr.stop_id = pm.bus_stop_id



	


        
JOIN routes r

    ON sr.route_id = r.id


LEFT JOIN
(
    SELECT
        route_id,
        weekday_boardings / 21.0 AS daily_boardings,
        weekday_boardings
    FROM ridership_snapshots
) rd

ON r.route_id = rd.route_id


        GROUP BY ps.id;

        """
    )


    rows = cursor.fetchall()


    if not rows:

        print(
            "No stop data found"
        )

        return



    max_score_base = max(

        math.log(
            1 + (row[2] or 0)
        )

        for row in rows

    )


    if max_score_base == 0:
        max_score_base = 1


    max_routes = max(

        row[1]

        for row in rows

    )



    results = []



    for row in rows:

        (
            stop_id,
            routes_served,
            total_daily,
            highest_route_daily,
            routes,
            largest_monthly

        ) = row


        total_daily = total_daily or 0


        demand_score = (

            math.log(
                1 + total_daily
            )
            /
            max_score_base
            *
            100

        )


        route_score = (

            routes_served
            /
            max_routes
            *
            100

        ) if max_routes else 0


        priority_score = (

            demand_score * 0.70

            +

            route_score * 0.30

        )


        factors = {

            "combined_route_weekday_boardings":
                round(
                    total_daily,
                    2
                ),

            "highest_route_weekday_boardings":
                round(
                    highest_route_daily or 0,
                    2
                ),

            "routes_served":
                routes_served,

            "routes":
                routes.split(",")
                if routes
                else [],

            "route_exposure_score":
                round(
                    demand_score,
                    2
                ),

            "route_score":
                round(
                    route_score,
                    2
                )

        }


        results.append(
            (
                stop_id,
                priority_score,
                factors
            )
        )



    results.sort(
        key=lambda x: x[1],
        reverse=True
    )



    for rank, item in enumerate(
        results,
        start=1
    ):

        stop_id, score, factors = item


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
        f"Scored {len(results):,} stops"
    )



if __name__ == "__main__":

    calculate_scores()
