"""
Export prioritized bus stop improvement projects.

Combines:
- opportunity ranking
- impact scoring
- recommendations
- review evidence
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
    "priority_improvement_report.csv"
)


def export_priority_report():

    conn = sqlite3.connect(DATABASE_PATH)

    cursor = conn.cursor()


    cursor.execute(
        """
        SELECT

            io.priority_rank,

            io.physical_stop_id,

            ps.primary_name,

            io.opportunity_score,

            sii.impact_level,

            rc.evidence_status,

            rc.confidence_level,

            GROUP_CONCAT(
                DISTINCT ir.recommendation_type
            ),

            sr.notes

        FROM improvement_opportunities io


        JOIN physical_stops ps

            ON io.physical_stop_id = ps.id


        LEFT JOIN stop_improvement_impact sii

            ON io.physical_stop_id = sii.physical_stop_id


        LEFT JOIN improvement_recommendations ir

            ON io.physical_stop_id = ir.physical_stop_id


        LEFT JOIN stop_reviews sr

            ON io.physical_stop_id = sr.stop_id


        LEFT JOIN recommendation_confidence rc

            ON io.physical_stop_id = rc.physical_stop_id


        GROUP BY

            io.priority_rank,
            io.physical_stop_id,
            ps.primary_name,
            io.opportunity_score,
            sii.impact_level,
            sr.notes


        ORDER BY

            io.priority_rank;

        """
    )


    rows = cursor.fetchall()


    with open(
        OUTPUT_PATH,
        "w",
        newline=""
    ) as file:

        writer = csv.writer(file)

        writer.writerow(
            [
                "priority_rank",
                "stop_id",
                "location",
                "opportunity_score",
                "impact_level",
                "evidence_status",
                "confidence_level",
                "recommendations",
                "review_notes"
            ]
        )


        writer.writerows(rows)


    conn.close()


    print(
        f"Exported {len(rows):,} priority records"
    )

    print(
        OUTPUT_PATH
    )


if __name__ == "__main__":

    export_priority_report()
