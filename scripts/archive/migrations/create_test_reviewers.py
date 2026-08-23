import sqlite3

DB = "src/database/dmv_bus_stops.db"

conn = sqlite3.connect(DB)
cur = conn.cursor()

for name in [
    "test_reviewer_1",
    "test_reviewer_2",
    "test_reviewer_3",
    "test_reviewer_4",
    "test_reviewer_5",
]:

    cur.execute(
        """
        INSERT OR IGNORE INTO community_reviewers
        (
            reviewer_key,
            display_name
        )
        VALUES (?,?)
        """,
        (
            name,
            name
        )
    )

conn.commit()

print(
    cur.execute(
        "SELECT COUNT(*) FROM community_reviewers"
    ).fetchone()[0],
    "reviewers"
)

conn.close()
