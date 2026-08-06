"""
Create a volunteer pilot review round.

Assigns multiple reviewers to selected stops.
Designed for closed testing before public launch.
"""

import sqlite3
import random


DB = "src/database/dmv_bus_stops.db"

PILOT_STOPS = [
    5478,
    792,
    602,
    2339
]

REVIEWERS_PER_STOP = 3


conn = sqlite3.connect(DB)
cur = conn.cursor()


reviewers = cur.execute(
    """
    SELECT id
    FROM community_reviewers
    ORDER BY id
    """
).fetchall()


reviewer_ids = [
    r[0]
    for r in reviewers
]


if len(reviewer_ids) < REVIEWERS_PER_STOP:
    raise Exception(
        "Need at least 3 reviewers in community_reviewers"
    )


created = 0


for stop_id in PILOT_STOPS:

    assignments = random.sample(
        reviewer_ids,
        REVIEWERS_PER_STOP
    )

    for reviewer_id in assignments:

        try:

            cur.execute(
                """
                INSERT INTO stop_review_assignments
                (
                    stop_id,
                    reviewer_id,
                    status
                )

                VALUES
                (?, ?, 'assigned')

                """,
                (
                    stop_id,
                    reviewer_id
                )
            )

            created += 1

        except sqlite3.IntegrityError:
            pass


conn.commit()
conn.close()


print(
    f"Created {created} pilot assignments"
)
