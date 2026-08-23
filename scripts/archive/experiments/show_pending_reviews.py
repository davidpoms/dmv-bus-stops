"""
Show assigned reviews that still need volunteer submissions.
"""

import sqlite3


DB = "src/database/dmv_bus_stops.db"


conn = sqlite3.connect(DB)
cur = conn.cursor()


rows = cur.execute(
    """
    SELECT

        a.stop_id,
        a.reviewer_id,
        a.status,
        COUNT(o.id) AS observations


    FROM stop_review_assignments a

    LEFT JOIN stop_observations o

        ON o.physical_stop_id=a.stop_id
        AND o.reviewer_id=a.reviewer_id


    GROUP BY
        a.stop_id,
        a.reviewer_id


    HAVING observations = 0


    ORDER BY a.stop_id;

    """
).fetchall()


print()
print("Pending reviews")
print("----------------")

for stop, reviewer, status, count in rows:
    print(
        f"Stop {stop}: "
        f"reviewer {reviewer} "
        f"({status})"
    )


print("----------------")
print(
    f"Pending count: {len(rows)}"
)


conn.close()
