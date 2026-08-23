import sqlite3

DB = "src/database/dmv_bus_stops.db"

conn = sqlite3.connect(DB)
conn.row_factory = sqlite3.Row
c = conn.cursor()


rows = c.execute("""
SELECT
    ste.stop_id,
    ste.route_count AS evidence_routes,
    COUNT(sr.id) AS actual_routes

FROM stop_transit_evidence ste

LEFT JOIN stop_routes sr
    ON sr.stop_id = ste.stop_id

WHERE ste.gtfs_bus_stop = 1

GROUP BY ste.stop_id

HAVING evidence_routes != actual_routes

ORDER BY ABS(evidence_routes - actual_routes) DESC
""").fetchall()


print("Transit evidence mismatches:", len(rows))

for r in rows[:50]:
    print(dict(r))


conn.close()