import sqlite3

conn = sqlite3.connect(
    "src/database/dmv_bus_stops.db"
)

rows = conn.execute(
    """
    SELECT
        id,
        reviewer_key,
        display_name,
        profile_created_at
    FROM community_reviewers
    ORDER BY id DESC
    LIMIT 10
    """
).fetchall()


for row in rows:
    print(row)