import sqlite3

DB = "src/database/dmv_bus_stops.db"

conn = sqlite3.connect(DB)
conn.row_factory = sqlite3.Row
c = conn.cursor()

rows = c.execute("""
SELECT
    ste.stop_id,
    ste.route_count,
    COUNT(br.route_id) AS backup_routes
FROM stop_transit_evidence ste
LEFT JOIN stop_routes sr
    ON ste.stop_id = sr.stop_id
LEFT JOIN stop_routes_bad_key_backup br
    ON ste.stop_id = br.stop_id
WHERE ste.route_count > 0
AND sr.route_id IS NULL
GROUP BY ste.stop_id
""").fetchall()


recoverable = 0
partial = 0
missing = 0

for r in rows:
    if r["backup_routes"] >= r["route_count"]:
        recoverable += 1
    elif r["backup_routes"] > 0:
        partial += 1
    else:
        missing += 1

print("Total missing stops:", len(rows))
print("Fully recoverable:", recoverable)
print("Partially recoverable:", partial)
print("No backup routes:", missing)

conn.close()