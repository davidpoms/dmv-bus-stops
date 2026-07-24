"""
Stop-level implementation detail view.
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


def get_stop_detail(stop_id):

    conn = sqlite3.connect(
        DATABASE_PATH
    )

    cursor = conn.cursor()


    cursor.execute(
        """
        SELECT

            ps.primary_name,

            io.opportunity_score,

            sii.impact_level

        FROM physical_stops ps

        JOIN improvement_opportunities io

            ON ps.id = io.physical_stop_id

        JOIN stop_improvement_impact sii

            ON ps.id = sii.physical_stop_id

        WHERE ps.id = ?;

        """,
        (stop_id,)
    )


    stop = cursor.fetchone()


    cursor.execute(
        """
        SELECT

            recommendation_type,

            project_status

        FROM improvement_projects

        WHERE physical_stop_id = ?;

        """,
        (stop_id,)
    )


    projects = cursor.fetchall()


    cursor.execute(
        """
        SELECT

            recommendation_type,

            old_status,

            new_status,

            changed_by

        FROM project_status_history

        WHERE physical_stop_id = ?;

        """,
        (stop_id,)
    )


    history = cursor.fetchall()


    conn.close()


    return {
        "stop": stop,
        "projects": projects,
        "history": history
    }


if __name__ == "__main__":

    detail = get_stop_detail(5478)

    print(detail)
