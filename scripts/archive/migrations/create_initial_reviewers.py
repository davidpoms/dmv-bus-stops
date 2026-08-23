import sqlite3

DB = "src/database/dmv_bus_stops.db"

conn = sqlite3.connect(DB)
cur = conn.cursor()

reviewers = [
    ("reviewer_001", "Reviewer 001"),
    ("reviewer_002", "Reviewer 002"),
    ("reviewer_003", "Reviewer 003"),
    ("reviewer_004", "Reviewer 004"),
    ("reviewer_005", "Reviewer 005"),
]

for key, name in reviewers:
    cur.execute(
        """
        INSERT OR IGNORE INTO community_reviewers
        (
            reviewer_key,
            display_name
        )
        VALUES (?,?)
        """,
        (key, name)
    )

conn.commit()

print(
    "Reviewers:",
    cur.execute(
        "SELECT COUNT(*) FROM community_reviewers"
    ).fetchone()[0]
)

conn.close()
