import sqlite3

DB = "src/database/dmv_bus_stops.db"

conn = sqlite3.connect(DB)
conn.row_factory = sqlite3.Row
cur = conn.cursor()


print("\nUNMAPPED GTFS STOP AUDIT")
print("========================\n")


rows = cur.execute("""
SELECT
    b.id,
    b.external_stop_id,
    b.stop_name,
    b.latitude,
    b.longitude
FROM bus_stops b
LEFT JOIN gtfs_stop_map g
    ON b.id = g.bus_stop_id
WHERE g.bus_stop_id IS NULL
ORDER BY b.id
LIMIT 50
""").fetchall()


print("Sample unmapped stops:")

for r in rows:
    print(dict(r))


print("\nCounts:")
print("----------------")


total = cur.execute("""
SELECT COUNT(*)
FROM bus_stops b
LEFT JOIN gtfs_stop_map g
    ON b.id = g.bus_stop_id
WHERE g.bus_stop_id IS NULL
""").fetchone()[0]

print("Unmapped bus stops:", total)


with_routes = cur.execute("""
SELECT COUNT(DISTINCT b.id)
FROM bus_stops b
JOIN stop_transit_evidence e
    ON e.stop_id = b.id
LEFT JOIN gtfs_stop_map g
    ON g.bus_stop_id = b.id
WHERE e.route_count > 0
AND g.bus_stop_id IS NULL
""").fetchone()[0]


print(
    "Unmapped but evidence says routes exist:",
    with_routes
)


conn.close()