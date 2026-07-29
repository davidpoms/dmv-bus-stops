"""
Show which stops have enough completed reviewer observations
to generate consensus.
"""

import sqlite3


DB = "src/database/dmv_bus_stops.db"


conn = sqlite3.connect(DB)
cur = conn.cursor()


rows = cur.execute(
    """
    SELECT

        a.stop_id,

        COUNT(DISTINCT a.reviewer_id)
            AS assigned_reviewers,

        COUNT(DISTINCT o.reviewer_id)
            AS completed_reviews


    FROM stop_review_assignments a

    LEFT JOIN stop_observations o

        ON o.physical_stop_id = a.stop_id

        AND o.reviewer_id = a.reviewer_id


    WHERE a.status='completed'


    GROUP BY a.stop_id


    ORDER BY completed_reviews DESC

    LIMIT 20;

    """
).fetchall()


ready = 0


print()
print("Consensus readiness")
print("-------------------")


for stop, assigned, completed in rows:

    status = (
        "READY"
        if completed >= 3
        else "NEEDS REVIEWS"
    )

    if completed >= 3:
        ready += 1

    print(
        f"Stop {stop}: "
        f"{completed}/{assigned} completed "
        f"- {status}"
    )


print("-------------------")
print(
    f"Stops ready: {ready}"
)


conn.close()
