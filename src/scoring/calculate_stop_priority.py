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
        WITH physical_stop_routes AS (

            SELECT DISTINCT

                psm.physical_stop_id,
                r.route_id

            FROM physical_stop_members psm

            JOIN stop_routes sr
                ON psm.bus_stop_id = sr.stop_id

            JOIN routes r
                ON sr.route_id = r.id

        ),

        route_exposure AS (

            SELECT

                route_id,

                MAX(weekday_boardings) AS weekday_boardings

            FROM ridership_snapshots

            WHERE period = (
                SELECT MAX(period)
                FROM ridership_snapshots
            )

            GROUP BY route_id

        )


        SELECT

            ps.id,

            COUNT(
                DISTINCT psr.route_id
            ) AS routes_served,


            SUM(
                rd.weekday_boardings
            ) AS combined_weekday_boardings,


            MAX(
                rd.weekday_boardings
            ) AS highest_route_weekday,


            GROUP_CONCAT(
                DISTINCT psr.route_id
            ) AS routes



FROM physical_stops ps


JOIN stop_gtfs_status sgs

    ON sgs.physical_stop_id = ps.id

   AND sgs.current_gtfs = 1


JOIN physical_stop_routes psr

    ON psr.physical_stop_id = ps.id






LEFT JOIN route_exposure rd

    ON psr.route_id = rd.route_id


        GROUP BY ps.id;

        """
    )


    rows = cursor.fetchall()


    if not rows:

        print(
            "No stop data found"
        )

        conn.commit()
        conn.close()
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
            combined_weekday,
            highest_route_weekday,
            routes

        ) = row


        combined_weekday = combined_weekday or 0


        demand_score = (

            math.log(
                1 + combined_weekday
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
                    combined_weekday,
                    2
                ),

            "highest_route_weekday_boardings":
                round(
                    highest_route_weekday or 0,
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
