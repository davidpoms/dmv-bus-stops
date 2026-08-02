import sqlite3

conn = sqlite3.connect("src/database/dmv_bus_stops.db")

tables = [
    "community_reviewers",
    "reviewers",
    "stop_reviewers",
    "stop_review_assignments",
    "review_queue",
]

for t in tables:
    result = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
        (t,)
    ).fetchone()

    print(t, "YES" if result else "NO")