
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


def create_review_queue(database_path=None):

    conn = sqlite3.connect(
        database_path or DATABASE_PATH
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

    columns = {row[1] for row in cursor.execute("PRAGMA table_info(review_queue)")}
    additions = {
        "review_priority_score": "REAL",
        "priority_amenity": "TEXT",
        "shelter_review_priority": "REAL",
        "bench_review_priority": "REAL",
        "rider_exposure_percentile": "REAL",
        "priority_reason": "TEXT",
    }
    for name, sql_type in additions.items():
        if name not in columns:
            cursor.execute(f"ALTER TABLE review_queue ADD COLUMN {name} {sql_type}")


    cursor.execute(
        """
        DELETE FROM review_queue;
        """
    )


    priority_table_exists = cursor.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' "
        "AND name='stop_amenity_review_priority'"
    ).fetchone()
    if priority_table_exists:
        cursor.execute(
        """
        WITH amenity_rollup AS (
            SELECT physical_stop_id,
                   MAX(review_priority_score) review_priority_score,
                   MAX(CASE WHEN amenity_type='shelter' THEN review_priority_score END) shelter_priority,
                   MAX(CASE WHEN amenity_type='bench' THEN review_priority_score END) bench_priority,
                   MAX(rider_exposure_percentile) rider_percentile
            FROM stop_amenity_review_priority
            WHERE workflow_state != 'consensus_reached'
            GROUP BY physical_stop_id
        )
        SELECT DISTINCT

            io.physical_stop_id,
            io.priority_rank,
            io.opportunity_score,
            ps.primary_name,
            ar.review_priority_score,
            CASE WHEN ar.shelter_priority >= ar.bench_priority THEN 'shelter' ELSE 'bench' END,
            ar.shelter_priority,
            ar.bench_priority,
            ar.rider_percentile

        FROM improvement_opportunities io

        JOIN stop_gtfs_status sgs

            ON sgs.physical_stop_id = io.physical_stop_id

           AND sgs.current_gtfs = 1

        JOIN physical_stops ps

            ON io.physical_stop_id = ps.id

        JOIN amenity_rollup ar
            ON ar.physical_stop_id=io.physical_stop_id

        ORDER BY ar.review_priority_score DESC, io.priority_rank;

        """
        )
        rows = cursor.fetchall()
    else:
        rows = [(*row, None, None, None, None, None) for row in cursor.execute(
            """SELECT DISTINCT io.physical_stop_id,io.priority_rank,
               io.opportunity_score,ps.primary_name
               FROM improvement_opportunities io
               JOIN stop_gtfs_status s ON s.physical_stop_id=io.physical_stop_id
                                      AND s.current_gtfs=1
               JOIN physical_stops ps ON ps.id=io.physical_stop_id
               ORDER BY io.priority_rank"""
        ).fetchall()]


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
            , review_priority_score, priority_amenity,
            shelter_priority, bench_priority, rider_percentile

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
                , review_priority_score, priority_amenity,
                shelter_review_priority, bench_review_priority,
                rider_exposure_percentile, priority_reason
            )

            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);

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
                , review_priority_score, priority_amenity,
                shelter_priority, bench_priority, rider_percentile,
                (f"{priority_amenity} verification priority; rider exposure "
                 f"{round(rider_percentile)}th percentile")
                if priority_amenity is not None else None
            )
        )


    conn.commit()


    print(
        f"Created {len(rows):,} active-stop review tasks"
    )


    conn.close()


if __name__ == "__main__":

    create_review_queue()
