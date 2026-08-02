import sqlite3

conn = sqlite3.connect("src/database/dmv_bus_stops.db")

rows = conn.execute(
    "PRAGMA table_info(review_queue)"
).fetchall()

for r in rows:
    print(r)