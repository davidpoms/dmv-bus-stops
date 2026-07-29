"""
Create volunteer review queue for bus stop improvement opportunities.
"""

import sqlite3
import json
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[2]

DATABASE_PATH = (
    BASE_DIR
    / "src"
    / "database"
    / "dmv_bus_stops.db"
)


def create_review_queue():

    conn = sqlite3.connect(
        DATABASE_PATH
    )

    cursor = conn.cursor()


    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS review_queue (

            id INTEGER PRIMARY KEY,

            physical_stop_id INTEGER NOT NULL,

            priority_rank INTEGER,

            opportunity_score REAL,

            location_name TEXT,

            review_status TEXT DEFAULT 'pending',

            review_questions JSON,

            consensus_status TEXT DEFAULT 'pending',

            resolution_reason TEXT,

            verification_needed INTEGER DEFAULT 1,

            community_review_available INTEGER DEFAULT 1,

            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP

        );
        """
    )


    cursor.execute(
        """
        DELETE FROM review_queue;
        """
    )


    cursor.execute(
        """
        SELECT

            io.physical_stop_id,
            io.priority_rank,
            io.opportunity_score,
            ps.primary_name

        FROM improvement_opportunities io

        JOIN physical_stops ps

            ON io.physical_stop_id = ps.id

        ORDER BY io.priority_rank;
        """
    )


    rows = cursor.fetchall()


    questions = [
        "Is there currently a bench?",
        "Is there currently a shelter?",
        "Is the waiting area accessible?",
        "Is there enough physical space for improvement?",
        "Are there safety concerns?"
    ]


    for row in rows:

        (
            physical_stop_id,
            priority_rank,
            score,
            location_name
        ) = row


        cursor.execute(
            """
            INSERT INTO review_queue
            (
                physical_stop_id,
                priority_rank,
                opportunity_score,
                location_name,
                review_status,
                review_questions,
                consensus_status,
                verification_needed,
                community_review_available
            )

            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
            """,
            (
                physical_stop_id,
                priority_rank,
                score,
                location_name,
                "pending",
                json.dumps(questions),
                "pending",
                1,
                1
            )
        )


    conn.commit()


    print(
        f"Created {len(rows):,} review tasks"
    )


    conn.close()


if __name__ == "__main__":

    create_review_queue()
