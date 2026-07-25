import sqlite3

DB = "src/database/dmv_bus_stops.db"

conn = sqlite3.connect(DB)
cur = conn.cursor()

count_before = cur.execute("""
    SELECT COUNT(*)
    FROM stop_reviews
""").fetchone()[0]

cur.execute("""
DELETE FROM stop_reviews
""")

conn.commit()

count_after = cur.execute("""
    SELECT COUNT(*)
    FROM stop_reviews
""").fetchone()[0]

conn.close()

print(f"Reviews before: {count_before}")
print(f"Reviews after: {count_after}")
