import sqlite3

db = "src/database/dmv_bus_stops.db"

conn = sqlite3.connect(db)
cur = conn.cursor()

cur.execute(
    """
    DELETE FROM stop_review_assignments
    WHERE reviewer_id=1
    AND status='assigned'
    """
)

print("Deleted rows:", cur.rowcount)

conn.commit()
conn.close()