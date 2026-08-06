import sqlite3

DB = "src/database/dmv_bus_stops.db"

conn = sqlite3.connect(DB)
conn.row_factory = sqlite3.Row
c = conn.cursor()


rows = c.execute("""
SELECT
    srb.stop_id,
    COUNT(*) AS route_count,
    GROUP_CONCAT(DISTINCT srb.route_id) AS routes

FROM stop_routes_backup srb

LEFT JOIN gtfs_stop_map gm
    ON CAST(srb.stop_id AS TEXT)=gm.gtfs_stop_id

WHERE gm.gtfs_stop_id IS NULL

GROUP BY srb.stop_id

ORDER BY srb.stop_id
""").fetchall()


print("Orphan GTFS stops:", len(rows))

for r in rows:
    print(dict(r))


conn.close()