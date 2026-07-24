"""
Create final project priority queue.

Combines improvement recommendations and impact scoring
into a funding-oriented project list.
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


def create_project_priorities():

    conn = sqlite3.connect(DATABASE_PATH)

    cursor = conn.cursor()


    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS project_priorities (

            id INTEGER PRIMARY KEY,

            physical_stop_id INTEGER NOT NULL,

            recommendation_type TEXT NOT NULL,

            location_name TEXT,

            opportunity_score REAL,

            impact_level TEXT,

            priority_rank INTEGER,

            justification TEXT,

            created_at TIMESTAMP
                DEFAULT CURRENT_TIMESTAMP

        );
        """
    )


    cursor.execute(
        """
        DELETE FROM project_priorities;
        """
    )


    cursor.execute(
        """
        SELECT

            ir.physical_stop_id,

            ir.recommendation_type,

            ps.primary_name,

            io.opportunity_score,

            sii.impact_level,

            io.priority_rank

        FROM improvement_recommendations ir


        JOIN improvement_opportunities io

            ON ir.physical_stop_id = io.physical_stop_id


        JOIN stop_improvement_impact sii

            ON ir.physical_stop_id = sii.physical_stop_id


        JOIN physical_stops ps

            ON ir.physical_stop_id = ps.id


        ORDER BY

            io.opportunity_score DESC;

        """
    )


    rows = cursor.fetchall()


    for row in rows:

        (
            stop_id,
            recommendation,
            location,
            score,
            impact,
            rank
        ) = row


        justification = (
            f"{impact} impact stop with "
            f"opportunity score {score:.2f}"
        )


        cursor.execute(
            """
            INSERT INTO project_priorities
            (
                physical_stop_id,
                recommendation_type,
                location_name,
                opportunity_score,
                impact_level,
                priority_rank,
                justification
            )

            VALUES (?, ?, ?, ?, ?, ?, ?);

            """,
            (
                stop_id,
                recommendation,
                location,
                score,
                impact,
                rank,
                justification
            )
        )


    conn.commit()

    conn.close()


    print(
        f"Created {len(rows)} project priorities"
    )


if __name__ == "__main__":

    create_project_priorities()
