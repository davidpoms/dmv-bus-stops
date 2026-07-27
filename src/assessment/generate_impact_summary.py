"""
Generate public-facing impact summaries for bus stop improvements.
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
        CREATE TABLE IF NOT EXISTS stop_improvement_impact (

            id INTEGER PRIMARY KEY,

            physical_stop_id INTEGER NOT NULL,

            daily_route_exposure REAL,

            opportunity_score REAL,

            impact_level TEXT,

            recommendations JSON,

            summary TEXT,

            created_at TIMESTAMP
                DEFAULT CURRENT_TIMESTAMP
        );
        """
    )


def generate_impact_summary():

    conn = sqlite3.connect(DATABASE_PATH)

    cursor = conn.cursor()

    setup_table(cursor)

    cursor.execute(
        """
        DELETE FROM stop_improvement_impact;
        """
    )


    cursor.execute(
        """
        SELECT

            io.physical_stop_id,

            oa.combined_route_weekday_boardings,

            io.opportunity_score,

            oa.assessment_json,

            GROUP_CONCAT(
                ir.recommendation_type
            )

        FROM improvement_opportunities io

        JOIN opportunity_assessments oa

            ON io.physical_stop_id = oa.physical_stop_id

        LEFT JOIN improvement_recommendations ir

            ON io.physical_stop_id = ir.physical_stop_id

        GROUP BY

            io.physical_stop_id,

            oa.combined_route_weekday_boardings,

            io.opportunity_score,

            oa.assessment_json

        ORDER BY

            io.opportunity_score DESC;

        """
    )


    rows = cursor.fetchall()

    created = 0


    for row in rows:

        (
            stop_id,
            daily_route_exposure,
            opportunity_score,
            assessment_json,
            recommendations
        ) = row


        assessment = json.loads(
            assessment_json
        )


        if opportunity_score >= 75:

            impact_level = "very_high"

        elif opportunity_score >= 60:

            impact_level = "high"

        elif opportunity_score >= 45:

            impact_level = "medium"

        else:

            impact_level = "low"


        recommendation_list = []

        if recommendations:

            recommendation_list = list(
                set(
                    recommendations.split(",")
                )
            )


        # Generate opportunity-based recommendations
        # when no volunteer recommendations exist yet.

        if not recommendation_list:

            assessment_score = (
                assessment
                .get("route_exposure", {})
                .get(
                    "combined_route_weekday_boardings",
                    0
                )
            )


            if opportunity_score >= 70:

                recommendation_list.append(
                    "priority_review"
                )


            if assessment_score > 0:

                recommendation_list.append(
                    "ridership_based_improvement_review"
                )


        summary = (
            f"Bus stop with "
            f"{round(daily_route_exposure):,} combined weekday boardings across serving routes."
        )


        if recommendation_list:

            summary += (
                " Recommended improvements: "
                +
                ", ".join(recommendation_list)
                +
                "."
            )


        cursor.execute(
            """
            INSERT INTO stop_improvement_impact
            (
                physical_stop_id,
                daily_route_exposure,
                opportunity_score,
                impact_level,
                recommendations,
                summary
            )

            VALUES (?, ?, ?, ?, ?, ?);

            """,
            (
                stop_id,
                daily_route_exposure,
                opportunity_score,
                impact_level,
                json.dumps(recommendation_list),
                summary
            )
        )


        created += 1


    conn.commit()

    conn.close()


    print(
        f"Created {created} impact summaries"
    )


if __name__ == "__main__":

    generate_impact_summary()
