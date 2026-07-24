"""
Export improvement projects into an operational dashboard CSV.
"""

import sqlite3
import csv
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

OUTPUT_PATH = (
    BASE_DIR
    /
    "project_implementation_report.csv"
)


def export_dashboard():

    conn = sqlite3.connect(
        DATABASE_PATH
    )

    cursor = conn.cursor()


    cursor.execute(
        """
        SELECT

            ip.physical_stop_id,

            ip.recommendation_type,

            ip.project_status,

            io.opportunity_score,

            sr.primary_name,

            ph.changed_by,

            ph.change_reason,

            ph.changed_at

        FROM improvement_projects ip


        LEFT JOIN improvement_opportunities io

            ON ip.physical_stop_id =
               io.physical_stop_id


        LEFT JOIN stop_improvement_impact sii

            ON ip.physical_stop_id =
               sii.physical_stop_id


        LEFT JOIN physical_stops sr

            ON ip.physical_stop_id =
               sr.id


        LEFT JOIN project_status_history ph

            ON ip.physical_stop_id =
               ph.physical_stop_id

            AND ip.recommendation_type =
                ph.recommendation_type


        ORDER BY

            io.opportunity_score DESC;

        """
    )


    rows = cursor.fetchall()


    with open(
        OUTPUT_PATH,
        "w",
        newline=""
    ) as f:

        writer = csv.writer(f)


        writer.writerow(
            [
                "stop_id",
                "recommendation",
                "project_status",
                "opportunity_score",
                "location",
                "changed_by",
                "change_reason",
                "last_update"
            ]
        )


        writer.writerows(rows)


    conn.close()


    print(
        f"Created {len(rows)} dashboard rows"
    )

    print(
        OUTPUT_PATH
    )


if __name__ == "__main__":

    export_dashboard()
