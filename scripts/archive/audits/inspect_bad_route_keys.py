import sqlite3

DB="src/database/dmv_bus_stops.db"

conn=sqlite3.connect(DB)
conn.row_factory=sqlite3.Row
c=conn.cursor()

rows=c.execute("""
SELECT
    sr.route_id,
    COUNT(*) as count
FROM stop_routes sr
LEFT JOIN routes r
    ON r.id = sr.route_id
WHERE r.id IS NULL
GROUP BY sr.route_id
ORDER BY count DESC
LIMIT 20
""").fetchall()

for r in rows:
    print(dict(r))

conn.close()