import sqlite3

conn = sqlite3.connect("src/database/dmv_bus_stops.db")

rows = conn.execute(
    "PRAGMA table_info(stop_consensus)"
).fetchall()

print("stop_consensus columns:")

for r in rows:
    print(r[1])

conn.close()