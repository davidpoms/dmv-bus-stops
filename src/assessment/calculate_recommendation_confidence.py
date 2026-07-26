"""
Calculate confidence for bus stop improvement recommendations.

Confidence is based on:
- opportunity score
- whether a volunteer review exists
- reviewer confidence (if available)
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
        CREATE TABLE IF NOT EXISTS recommendation_confidence (

            id INTEGER PRIMARY KEY,

            physical_stop_id INTEGER NOT NULL,

            opportunity_score REAL,

            evidence_status TEXT,

            confidence_level TEXT,

            created_at TIMESTAMP
                DEFAULT CURRENT_TIMESTAMP
        );
        """
    )


def calculate_confidence():

    conn = sqlite3.connect(DATABASE_PATH)

    cursor = conn.cursor()

    setup_table(cursor)


    cursor.execute(
        """
        DELETE FROM recommendation_confidence;
        """
    )


    cursor.execute(
        """
        SELECT

            io.physical_stop_id,

            io.opportunity_score,

            COUNT(o.id)

        FROM improvement_opportunities io

        LEFT JOIN stop_observations o

            ON io.physical_stop_id = o.physical_stop_id

        GROUP BY

            io.physical_stop_id,

            io.opportunity_score;

        """
    )


    rows = cursor.fetchall()


    for row in rows:

        (
            stop_id,
            score,
            review_count
        ) = row


        if review_count == 0:

            evidence_status = "unreviewed"

        else:

            evidence_status = "reviewed"


        if score >= 85 and review_count > 0:

            confidence = "high"

        elif score >= 70 or review_count > 0:

            confidence = "medium"

        else:

            confidence = "low"


        cursor.execute(
            """
            INSERT INTO recommendation_confidence
            (
                physical_stop_id,
                opportunity_score,
                evidence_status,
                confidence_level
            )

            VALUES (?, ?, ?, ?);

            """,
            (
                stop_id,
                score,
                evidence_status,
                confidence
            )
        )


    conn.commit()

    conn.close()


    print(
        f"Calculated confidence for {len(rows):,} stops"
    )


if __name__ == "__main__":

    calculate_confidence()
