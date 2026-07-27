"""
Create improvement project tracking table.

Turns identified improvement opportunities into
trackable implementation projects.
"""

import sqlite3
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
        CREATE TABLE IF NOT EXISTS improvement_projects (

            id INTEGER PRIMARY KEY,

            physical_stop_id INTEGER NOT NULL,

            recommendation_type TEXT,

            project_status TEXT DEFAULT 'identified',

            assigned_team TEXT,

            estimated_cost REAL,

            approved_date DATE,

            completed_date DATE,

            notes TEXT,

            created_at TIMESTAMP
                DEFAULT CURRENT_TIMESTAMP
        );
        """
    )


def create_projects():

    conn = sqlite3.connect(DATABASE_PATH)

    cursor = conn.cursor()

    setup_table(cursor)


    cursor.execute(
        """
        DELETE FROM improvement_projects;
        """
    )


    cursor.execute(
        """
        SELECT

            physical_stop_id,

            recommendation_type

        FROM project_priorities

        ORDER BY priority_rank;

        """
    )


    rows = cursor.fetchall()


    for row in rows:

        (
            stop_id,
            recommendation
        ) = row


        cursor.execute(
            """
            INSERT INTO improvement_projects
            (
                physical_stop_id,
                recommendation_type,
                project_status
            )

            VALUES (?, ?, ?);

            """,
            (
                stop_id,
                recommendation,
                "identified"
            )
        )


    conn.commit()

    conn.close()


    print(
        f"Created {len(rows):,} improvement projects"
    )


if __name__ == "__main__":

    create_projects()
