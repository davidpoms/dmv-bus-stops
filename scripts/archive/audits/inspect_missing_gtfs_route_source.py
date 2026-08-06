import sqlite3

DB="src/database/dmv_bus_stops.db"

conn=sqlite3.connect(DB)
conn.row_factory=sqlite3.Row
c=conn.cursor()


print("=== GTFS MAP WITH NO ROUTES ===")

rows=c.execute("""
SELECT
    gsm.bus_stop_id,
    gsm.gtfs_stop_id,
    COUNT(sr.route_id) AS routes
FROM gtfs_stop_map gsm

LEFT JOIN stop_routes sr
ON gsm.bus_stop_id = sr.stop_id

WHERE sr.route_id IS NULL

GROUP BY gsm.bus_stop_id

LIMIT 30
""").fetchall()


for r in rows:
    print(dict(r))


print("\n=== DOES GTFS STOP APPEAR IN BACKUP? ===")

rows=c.execute("""
SELECT
    gsm.bus_stop_id,
    gsm.gtfs_stop_id,
    COUNT(srb.route_id) AS backup_routes
FROM gtfs_stop_map gsm

LEFT JOIN stop_routes_backup srb
ON gsm.gtfs_stop_id = CAST(srb.stop_id AS TEXT)

WHERE gsm.bus_stop_id IN (
    SELECT gsm2.bus_stop_id
    FROM gtfs_stop_map gsm2
    LEFT JOIN stop_routes sr
    ON gsm2.bus_stop_id = sr.stop_id
    WHERE sr.route_id IS NULL
)

GROUP BY gsm.bus_stop_id

LIMIT 30
""").fetchall()


for r in rows:
    print(dict(r))


conn.close()