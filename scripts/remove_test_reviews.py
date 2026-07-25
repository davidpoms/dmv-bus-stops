import sqlite3

DB = "src/database/dmv_bus_stops.db"

conn = sqlite3.connect(DB)
cur = conn.cursor()

deleted = cur.execute(
    """
    DELETE FROM stop_reviews
    WHERE notes IN (
        'test',
        'development test only'
    )
    """
).rowcount

conn.commit()

remaining = cur.execute(
    """
    SELECT COUNT(*)
    FROM stop_reviews
    """
).fetchone()[0]

conn.close()

print(f"Deleted test reviews: {deleted}")
print(f"Remaining reviews: {remaining}")
