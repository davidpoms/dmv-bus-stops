"""
Export bus stop improvement opportunities into review-friendly reports.
"""

import sqlite3
import csv
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

OUTPUT_PATH = (
    BASE_DIR
    /
    "improvement_report.csv"
)


def export_report():

    conn = sqlite3.connect(DATABASE_PATH)

    cursor = conn.cursor()


    cursor.execute(
        """
        SELECT

            sii.physical_stop_id,

            ps.primary_name,

            io.priority_rank,

            io.opportunity_score,

            sii.impact_level,

            sii.recommendations

        FROM stop_improvement_impact sii

        JOIN improvement_opportunities io

            ON sii.physical_stop_id = io.physical_stop_id

        JOIN physical_stops ps

            ON sii.physical_stop_id = ps.id

        ORDER BY

            io.priority_rank;

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
                "location",
                "priority_rank",
                "opportunity_score",
                "impact_level",
                "recommendations"
            ]
        )


        for row in rows:

            writer.writerow(row)


    conn.close()


    print(
        f"Exported {len(rows):,} improvement records"
    )

    print(
        OUTPUT_PATH
    )


if __name__ == "__main__":

    export_report()
