import sqlite3

DB = "src/database/dmv_bus_stops.db"

conn = sqlite3.connect(DB)
conn.row_factory = sqlite3.Row
cur = conn.cursor()

print("=== GTFS STOP MAP COLUMNS ===")

cols = cur.execute("""
PRAGMA table_info(gtfs_stop_map)
""").fetchall()

for c in cols:
    print(c["name"])


print("\n=== SAMPLE GTFS STOP MAP ===")

rows = cur.execute("""
SELECT *
FROM gtfs_stop_map
LIMIT 10
""").fetchall()

for r in rows:
    print(dict(r))


print("\n=== BUS STOPS COLUMNS ===")

cols = cur.execute("""
PRAGMA table_info(bus_stops)
""").fetchall()

for c in cols:
    print(c["name"])


print("\n=== SAMPLE BUS STOPS ===")

rows = cur.execute("""
SELECT *
FROM bus_stops
LIMIT 5
""").fetchall()

for r in rows:
    print(dict(r))


conn.close()