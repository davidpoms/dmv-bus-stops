import sqlite3

conn = sqlite3.connect("src/database/dmv_bus_stops.db")

conn.execute(
    """
    DELETE FROM stop_review_assignments
    WHERE stop_id=2108
    AND status='assigned'
    """
)

conn.commit()
conn.close()

print("cleared")