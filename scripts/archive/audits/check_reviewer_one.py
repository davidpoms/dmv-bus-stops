import sqlite3

conn = sqlite3.connect(
    "src/database/dmv_bus_stops.db"
)

row = conn.execute(
    """
    SELECT
        id,
        reviewer_key,
        display_name,
        profile_token,
        email,
        profile_created_at
    FROM community_reviewers
    WHERE id=1
    """
).fetchone()

print(row)