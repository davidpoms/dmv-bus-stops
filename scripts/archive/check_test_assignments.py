import sqlite3

conn = sqlite3.connect("src/database/dmv_bus_stops.db")

count = conn.execute(
    """
    SELECT COUNT(*)
    FROM stop_review_assignments
    WHERE stop_id=2108
    AND status='assigned'
    """
).fetchone()[0]

conn.close()

print(count)