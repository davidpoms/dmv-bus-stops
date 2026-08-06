import sqlite3

DB = "src/database/dmv_bus_stops.db"

conn = sqlite3.connect(DB)
conn.row_factory = sqlite3.Row
c = conn.cursor()

rows = c.execute("""
SELECT
    ste.stop_id,
    ste.route_count,
    COUNT(sr.route_id) AS current_routes
FROM stop_transit_evidence ste
LEFT JOIN stop_routes sr
    ON ste.stop_id = sr.stop_id
WHERE ste.route_count > 0
GROUP BY ste.stop_id
HAVING COUNT(sr.route_id) = 0
LIMIT 50
""").fetchall()

print("Stops with transit evidence but no current routes:")
print(len(rows))

for r in rows:
    print(dict(r))


print()
print("Total affected:")

print(
    c.execute("""
    SELECT COUNT(*)
    FROM stop_transit_evidence ste
    LEFT JOIN stop_routes sr
        ON ste.stop_id = sr.stop_id
    WHERE ste.route_count > 0
    AND sr.route_id IS NULL
    """).fetchone()[0]
)

conn.close()