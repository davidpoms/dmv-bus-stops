import sqlite3

DB="src/database/dmv_bus_stops.db"

conn=sqlite3.connect(DB)
conn.row_factory=sqlite3.Row
c=conn.cursor()


print("=== CURRENT GTFS MAP WITH NO ROUTES ===")

rows=c.execute("""
SELECT
    gm.bus_stop_id,
    gm.gtfs_stop_id,
    COUNT(b.route_id) AS backup_routes

FROM gtfs_stop_map gm

LEFT JOIN stop_routes sr
    ON sr.stop_id = gm.bus_stop_id

LEFT JOIN stop_routes_bad_key_backup b
    ON CAST(b.stop_id AS TEXT)=gm.gtfs_stop_id

WHERE sr.stop_id IS NULL

GROUP BY gm.bus_stop_id

HAVING backup_routes > 0

LIMIT 50
""").fetchall()

for r in rows:
    print(dict(r))


print("\n=== TOTAL RECOVERABLE FROM BAD KEY BACKUP ===")

row=c.execute("""
SELECT COUNT(DISTINCT gm.bus_stop_id)

FROM gtfs_stop_map gm

LEFT JOIN stop_routes sr
    ON sr.stop_id = gm.bus_stop_id

JOIN stop_routes_bad_key_backup b
    ON CAST(b.stop_id AS TEXT)=gm.gtfs_stop_id

WHERE sr.stop_id IS NULL
""").fetchone()

print(row[0])


conn.close()