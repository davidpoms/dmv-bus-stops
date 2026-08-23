import sqlite3

conn = sqlite3.connect("src/database/dmv_bus_stops.db")

rows = conn.execute("""
SELECT
    id,
    stop_id,
    reviewer_id,
    scenario,
    status
FROM stop_review_assignments
ORDER BY id DESC
LIMIT 15
""").fetchall()

for row in rows:
    print(row)

conn.close()