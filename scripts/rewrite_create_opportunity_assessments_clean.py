from pathlib import Path
import shutil


BASE_DIR = Path(__file__).resolve().parents[1]

TARGET = (
    BASE_DIR
    / "src"
    / "assessment"
    / "create_opportunity_assessments.py"
)


BACKUP = TARGET.with_suffix(".backup_clean")


CONTENT = r'''
"""
Create physical stop opportunity assessments.

Combines:

- physical stop clusters
- route service
- ridership exposure
- priority scoring evidence
- infrastructure evidence

Creates an evidence layer for improvement review.
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

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS opportunity_assessments (

        id INTEGER PRIMARY KEY,

        physical_stop_id INTEGER NOT NULL,

        combined_route_weekday_boardings REAL,

        highest_route_weekday_boardings REAL,

        routes_served INTEGER,

        wmata_stop_records INTEGER,

        assessment_json JSON,

        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)



def create_assessments():

    conn = sqlite3.connect(
        DATABASE_PATH
    )

    cursor = conn.cursor()


    setup_table(cursor)


    cursor.execute(
        """
        DELETE FROM opportunity_assessments;
        """
    )


    cursor.execute(
        """
        SELECT id
        FROM physical_stops;
        """
    )

    stops = [
        r[0]
        for r in cursor.fetchall()
    ]


    created = 0


    for physical_stop_id in stops:


        cursor.execute(
            """
            SELECT COUNT(*)
            FROM physical_stop_members
            WHERE physical_stop_id = ?;
            """,
            (
                physical_stop_id,
            )
        )

        wmata_records = (
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
            r[0]
            for r in cursor.fetchall()
        ]


        combined = 0
        highest = 0


        if routes:

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
                );
                """,
                routes
            )


            ridership = cursor.fetchall()


            values = [
                row[1] / WEEKDAY_DIVISOR
                for row in ridership
                if row[1]
            ]


            if values:

                combined = sum(values)

                highest = max(values)



        cursor.execute(
            """
            SELECT factors

            FROM stop_priority_snapshots

            WHERE stop_id = ?

            ORDER BY calculated_date DESC

            LIMIT 1;
            """,
            (
                physical_stop_id,
            )
        )




        assessment = {

            "route_exposure": {

                "combined_route_weekday_boardings":
                    round(combined,2),

                "highest_route_weekday_boardings":
                    round(highest,2)

            },

            "network": {

                "routes_served":
                    len(routes),

                "routes":
                    routes

            },

            "physical": {

                "wmata_stop_records":
                    wmata_records

            },


        }


        cursor.execute(
            """
            INSERT INTO opportunity_assessments
            (
                physical_stop_id,
                combined_route_weekday_boardings,
                highest_route_weekday_boardings,
                routes_served,
                wmata_stop_records,
                assessment_json
            )

            VALUES (?, ?, ?, ?, ?, ?);

            """,
            (
                physical_stop_id,
                combined,
                highest,
                len(routes),
                wmata_records,
                json.dumps(assessment)
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
'''



def main():

    print("Creating backup...")

    shutil.copy(
        TARGET,
        BACKUP
    )


    TARGET.write_text(
        CONTENT,
        encoding="utf-8"
    )


    print(
        "Rewrite complete"
    )

    print(
        f"Backup: {BACKUP}"
    )



if __name__ == "__main__":
    main()