import sqlite3
import random

DB = "src/database/dmv_bus_stops.db"

conn = sqlite3.connect(DB)
cur = conn.cursor()

reviewers = cur.execute("""
SELECT id
FROM community_reviewers
ORDER BY id
""").fetchall()

if not reviewers:
    raise Exception("No reviewers exist")

stops = cur.execute("""
SELECT id
FROM physical_stops
ORDER BY RANDOM()
LIMIT 100
""").fetchall()

created = 0

for (stop_id,) in stops:

    for (reviewer_id,) in reviewers[:3]:

        try:
            cur.execute(
                """
                INSERT INTO stop_review_assignments
                (
                    stop_id,
                    reviewer_id
                )
                VALUES (?,?)
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

print("Created assignments:", created)

print(
    "Total assignments:",
    cur.execute(
        "SELECT COUNT(*) FROM stop_review_assignments"
    ).fetchone()[0]
)

conn.close()
