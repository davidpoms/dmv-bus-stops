import sqlite3

DB = "src/database/dmv_bus_stops.db"

conn = sqlite3.connect(DB)
conn.row_factory = sqlite3.Row
cur = conn.cursor()


print("=== ROUTES SAMPLE ===")

cur.execute("""
SELECT *
FROM routes
LIMIT 20
""")

for r in cur.fetchall():
    print(dict(r))


print("\n=== BACKUP ROUTE CODES NOT FOUND ===")

cur.execute("""
SELECT DISTINCT sr.route_id

FROM stop_routes_backup sr

LEFT JOIN routes r
ON r.route_id = sr.route_id

WHERE r.id IS NULL

LIMIT 50
""")

missing = cur.fetchall()

print("Missing:", len(missing))

for r in missing:
    print(dict(r))


conn.close()