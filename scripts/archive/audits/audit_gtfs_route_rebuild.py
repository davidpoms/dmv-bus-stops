import sqlite3

DB = "src/database/dmv_bus_stops.db"

conn = sqlite3.connect(DB)
conn.row_factory = sqlite3.Row
cur = conn.cursor()

print("=== GTFS STOP MAP SAMPLE ===")

for r in cur.execute("""
SELECT *
FROM gtfs_stop_map
LIMIT 5
"""):
    print(dict(r))


print("\n=== GTFS STOP MAP WITH ROUTES? ===")

print(
cur.execute("""
SELECT COUNT(*)
FROM gtfs_stop_map g
JOIN bus_stops b
ON g.bus_stop_id=b.id
JOIN stop_routes sr
ON sr.stop_id=b.id
""").fetchone()[0]
)


print("\n=== GTFS MAP WITHOUT ROUTES ===")

print(
cur.execute("""
SELECT COUNT(*)
FROM gtfs_stop_map g
JOIN bus_stops b
ON g.bus_stop_id=b.id
LEFT JOIN stop_routes sr
ON sr.stop_id=b.id
WHERE sr.id IS NULL
""").fetchone()[0]
)


print("\n=== SAMPLE RECOVERABLE ===")

for r in cur.execute("""
SELECT
g.bus_stop_id,
g.gtfs_stop_id,
b.external_stop_id
FROM gtfs_stop_map g
JOIN bus_stops b
ON g.bus_stop_id=b.id
LEFT JOIN stop_routes sr
ON sr.stop_id=b.id
WHERE sr.id IS NULL
LIMIT 20
"""):
    print(dict(r))