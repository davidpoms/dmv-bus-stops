"""
Create a complete 3-reviewer test cycle for one stop.

Used only for validating:
assignment -> observation -> consensus -> dashboard
"""

import sqlite3
from datetime import datetime


DB = "src/database/dmv_bus_stops.db"


STOP_ID = 5478

REVIEWERS = [
    6,
    8,
    10,
]


conn = sqlite3.connect(DB)
cur = conn.cursor()


for reviewer_id in REVIEWERS:

    # mark assignment complete
    cur.execute(
        """
        UPDATE stop_review_assignments

        SET
            status='completed',
            completed_at=CURRENT_TIMESTAMP

        WHERE
            stop_id=?
            AND reviewer_id=?
        """,
        (
            STOP_ID,
            reviewer_id,
        )
    )


    # create observation
    cur.execute(
        """
        INSERT INTO stop_observations
        (
            physical_stop_id,
            observer,
            reviewer_id,
            bench_present,
            bench_feasible,
            ada_clearance_possible,
            confidence,
            notes
        )

        VALUES
        (
            ?,
            ?,
            ?,
            '0',
            '1',
            '1',
            1.0,
            ?
        )

        """,
        (
            STOP_ID,
            f"test_reviewer_{reviewer_id}",
            reviewer_id,
            "Automated test observation"
        )
    )


conn.commit()
conn.close()


print(
    f"Created 3-reviewer test cycle for stop {STOP_ID}"
)
