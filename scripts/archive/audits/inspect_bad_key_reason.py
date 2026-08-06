import sqlite3

db = "src/database/dmv_bus_stops.db"

conn = sqlite3.connect(db)
conn.row_factory = sqlite3.Row
c = conn.cursor()

rows = c.execute("""
SELECT
    b.stop_id,
    b.route_id,
    CASE
        WHEN bs.stop_id IS NOT NULL THEN 'exists in bus_stops'
        ELSE 'missing from bus_stops'
    END AS status
FROM stop_routes_bad_key_backup b
LEFT JOIN bus_stops bs
    ON bs.stop_id = b.stop_id
LIMIT 50
""").fetchall()

for r in rows:
    print(dict(r))