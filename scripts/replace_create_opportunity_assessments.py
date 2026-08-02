from pathlib import Path
import shutil


TARGET = Path(
    "src/assessment/create_opportunity_assessments.py"
)


BACKUP = TARGET.with_suffix(
    ".backup_final"
)


CONTENT = r'''
"""
Create physical stop opportunity assessments.

Uses:

- physical stops
- stop priority snapshots
- WMATA evidence

Creates the evidence layer used by
improvement opportunity scoring.
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
        """
    )



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
        SELECT

            ps.id,

            COALESCE(
                sps.factors,
                '{}'
            ),

            COUNT(pm.id)

        FROM physical_stops ps


        LEFT JOIN stop_priority_snapshots sps

            ON sps.stop_id = ps.id


        LEFT JOIN physical_stop_members pm

            ON pm.physical_stop_id = ps.id


        GROUP BY ps.id;

        """
    )


    rows = cursor.fetchall()


    created = 0


    for row in rows:

        (
            physical_stop_id,
            factors_json,
            wmata_records

        ) = row


        factors = {}

        try:

            factors = json.loads(
                factors_json
            )

        except Exception:

            pass



        combined = factors.get(
            "combined_route_weekday_boardings",
            0
        )


        highest = factors.get(
            "highest_route_weekday_boardings",
            0
        )


        routes_served = factors.get(
            "routes_served",
            0
        )


        routes = factors.get(
            "routes",
            []
        )


        assessment = {

            "route_exposure": {

                "combined_route_weekday_boardings":
                    combined,

                "highest_route_weekday_boardings":
                    highest

            },


            "network": {

                "routes_served":
                    routes_served,

                "routes":
                    routes

            },


            "physical": {

                "wmata_stop_records":
                    wmata_records

            },


            "priority_source":
                factors

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

                routes_served,

                wmata_records,

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


    print("Replacement complete")
    print("Backup:", BACKUP)



if __name__ == "__main__":
    main()