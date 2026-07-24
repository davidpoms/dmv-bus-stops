"""
Create physical stop opportunity assessments.

Combines:

- physical stop clusters
- WMATA stop records
- routes served
- ridership evidence

Creates an evidence layer for future
bench/shelter/accessibility recommendations.
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


WEEKDAY_DIVISOR = 31



def setup_table(cursor):

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS opportunity_assessments (

            id INTEGER PRIMARY KEY,

            physical_stop_id INTEGER NOT NULL,

            average_daily_weekday_boardings REAL,

            highest_route_daily_boardings REAL,

            routes_served INTEGER,

            wmata_stop_records INTEGER,

            assessment_json JSON,

            created_at TIMESTAMP
                DEFAULT CURRENT_TIMESTAMP

        );
        """
    )


    cursor.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_opportunity_stop
        ON opportunity_assessments(
            physical_stop_id
        );
        """
    )



def create_assessments():

    conn = sqlite3.connect(
        DATABASE_PATH
    )

    cursor = conn.cursor()


    setup_table(
        cursor
    )


    cursor.execute(
        """
        DELETE FROM opportunity_assessments;
        """
    )


    cursor.execute(
        """
        SELECT
            id

        FROM physical_stops;
        """
    )


    physical_stops = [
        row[0]
        for row in cursor.fetchall()
    ]


    created = 0


    for physical_stop_id in physical_stops:


        cursor.execute(
            """
            SELECT
                COUNT(*)

            FROM physical_stop_members

            WHERE physical_stop_id = ?;

            """,
            (
                physical_stop_id,
            )
        )


        wmata_stop_records = (
            cursor.fetchone()[0]
        )



        cursor.execute(
            """
            SELECT DISTINCT
                sr.route_id

            FROM physical_stop_members pm

            JOIN stop_routes sr

                ON sr.stop_id = pm.bus_stop_id

            WHERE pm.physical_stop_id = ?;

            """,
            (
                physical_stop_id,
            )
        )


        routes = [
            row[0]
            for row in cursor.fetchall()
        ]


        if not routes:

            average_daily = 0
            highest_route_daily = 0

        else:


            placeholders = ",".join(
                "?"
                for _ in routes
            )


            cursor.execute(
                f"""
                SELECT

                    route_id,

                    weekday_boardings

                FROM ridership_snapshots

                WHERE route_id IN
                (
                    {placeholders}
                )

                ORDER BY weekday_boardings DESC;

                """,
                routes
            )


            ridership_rows = (
                cursor.fetchall()
            )


            if ridership_rows:


                daily_values = [
                    row[1] / WEEKDAY_DIVISOR
                    for row in ridership_rows
                    if row[1]
                ]


                average_daily = sum(
                    daily_values
                )


                highest_route_daily = (
                    max(daily_values)
                )


            else:

                average_daily = 0
                highest_route_daily = 0



        assessment = {

            "ridership": {

                "average_daily_weekday_boardings":
                    round(
                        average_daily,
                        2
                    ),

                "highest_route_daily_boardings":
                    round(
                        highest_route_daily,
                        2
                    )

            },


            "network": {

                "routes_served":
                    len(routes),

                "routes":
                    routes

            },


            "physical": {

                "wmata_stop_records":
                    wmata_stop_records

            }

        }



        cursor.execute(
            """
            INSERT INTO opportunity_assessments
            (

                physical_stop_id,

                average_daily_weekday_boardings,

                highest_route_daily_boardings,

                routes_served,

                wmata_stop_records,

                assessment_json

            )

            VALUES (?, ?, ?, ?, ?, ?);

            """,
            (

                physical_stop_id,

                average_daily,

                highest_route_daily,

                len(routes),

                wmata_stop_records,

                json.dumps(
                    assessment
                )

            )
        )


        created += 1



    conn.commit()

    conn.close()


    print(
        f"Created {created:,} opportunity assessments"
    )



if __name__ == "__main__":

    create_assessments()
