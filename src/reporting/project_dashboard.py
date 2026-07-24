"""
Read/query layer for improvement project dashboard.
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


def get_active_projects():

    conn = sqlite3.connect(
        DATABASE_PATH
    )

    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT

            ip.physical_stop_id,

            ps.primary_name,

            ip.recommendation_type,

            ip.project_status,

            io.opportunity_score

        FROM improvement_projects ip

        JOIN physical_stops ps

            ON ip.physical_stop_id = ps.id

        JOIN improvement_opportunities io

            ON ip.physical_stop_id =
               io.physical_stop_id

        WHERE ip.project_status != 'completed'

        ORDER BY
            io.opportunity_score DESC;

        """
    )

    rows = cursor.fetchall()

    conn.close()

    return rows


if __name__ == "__main__":

    for project in get_active_projects():

        print(project)
