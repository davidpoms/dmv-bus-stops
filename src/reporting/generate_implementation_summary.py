"""
Generate citywide improvement implementation summary.
"""

import sqlite3
import json
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

JSON_OUTPUT = (
    BASE_DIR
    /
    "implementation_summary.json"
)

CSV_OUTPUT = (
    BASE_DIR
    /
    "implementation_summary.csv"
)


def generate_summary():

    conn = sqlite3.connect(
        DATABASE_PATH
    )

    cursor = conn.cursor()


    cursor.execute(
        """
        SELECT
            COUNT(*)
        FROM improvement_projects;
        """
    )

    total_projects = cursor.fetchone()[0]


    cursor.execute(
        """
        SELECT
            project_status,
            COUNT(*)

        FROM improvement_projects

        GROUP BY project_status;
        """
    )

    status_counts = {
        row[0]: row[1]
        for row in cursor.fetchall()
    }


    cursor.execute(
        """
        SELECT
            priority_level,
            COUNT(*)

        FROM stop_improvement_impact

        GROUP BY priority_level;
        """
    )

    impact_counts = {
        row[0]: row[1]
        for row in cursor.fetchall()
    }


    cursor.execute(
        """
        SELECT

            sii.physical_stop_id,

            ps.primary_name,

            sii.opportunity_score,

            sii.priority_level

        FROM stop_improvement_impact sii

        JOIN physical_stops ps

            ON sii.physical_stop_id = ps.id

        ORDER BY

            sii.opportunity_score DESC

        LIMIT 10;

        """
    )

    top_stops = [
        {
            "stop_id": row[0],
            "location": row[1],
            "score": row[2],
            "impact": row[3]
        }
        for row in cursor.fetchall()
    ]


    summary = {

        "total_projects":
            total_projects,

        "project_status":
            status_counts,

        "priority_levels":
            impact_counts,

        "top_priority_stops":
            top_stops
    }


    with open(
        JSON_OUTPUT,
        "w"
    ) as f:

        json.dump(
            summary,
            f,
            indent=2
        )


    with open(
        CSV_OUTPUT,
        "w",
        newline=""
    ) as f:

        writer = csv.writer(f)

        writer.writerow(
            [
                "stop_id",
                "location",
                "opportunity_score",
                "priority_level"
            ]
        )

        for stop in top_stops:

            writer.writerow(
                [
                    stop["stop_id"],
                    stop["location"],
                    stop["score"],
                    stop["impact"]
                ]
            )


    conn.close()


    print(
        f"Created summary for {total_projects} projects"
    )

    print(JSON_OUTPUT)

    print(CSV_OUTPUT)


if __name__ == "__main__":

    generate_summary()
