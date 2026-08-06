import sqlite3

db = "src/database/dmv_bus_stops.db"

conn = sqlite3.connect(db)
conn.row_factory = sqlite3.Row
cur = conn.cursor()

print("CURRENT stop_routes samples")
for r in cur.execute("""
SELECT *
FROM stop_routes
LIMIT 10
"""):
    print(dict(r))


print("\nJOIN TEST (stop_routes.route_id -> routes.id)")

for r in cur.execute("""
SELECT 
    sr.stop_id,
    sr.route_id,
    r.route_id AS route_code,
    r.route_name
FROM stop_routes sr
LEFT JOIN routes r
ON sr.route_id = r.id
LIMIT 10
"""):
    print(dict(r))


print("\nBACKUP JOIN TEST (backup.route_id -> routes.route_id)")

for r in cur.execute("""
SELECT 
    srb.stop_id,
    srb.route_id,
    r.id AS route_table_id,
    r.route_name
FROM stop_routes_backup srb
LEFT JOIN routes r
ON srb.route_id = r.route_id
LIMIT 10
"""):
    print(dict(r))