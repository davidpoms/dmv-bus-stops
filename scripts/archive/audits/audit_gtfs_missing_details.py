import sqlite3

DB = "src/database/dmv_bus_stops.db"

conn = sqlite3.connect(DB)
conn.row_factory = sqlite3.Row
cur = conn.cursor()


print("=== MISSING GTFS STOP DETAIL ===")


cur.execute("""
SELECT
    b.id AS bus_stop_id,
    b.external_stop_id,
    b.stop_name,
    b.latitude,
    b.longitude

FROM bus_stops b

LEFT JOIN gtfs_stop_map g
    ON g.bus_stop_id = b.id

WHERE g.bus_stop_id IS NULL

LIMIT 50
""")


for r in cur.fetchall():
    print(dict(r))


print("\n=== COUNT BY EXTERNAL PREFIX ===")


cur.execute("""
SELECT
    substr(external_stop_id,1,1) prefix,
    COUNT(*) count

FROM bus_stops b

LEFT JOIN gtfs_stop_map g
    ON g.bus_stop_id=b.id

WHERE g.bus_stop_id IS NULL

GROUP BY prefix
""")


for r in cur.fetchall():
    print(dict(r))


conn.close()