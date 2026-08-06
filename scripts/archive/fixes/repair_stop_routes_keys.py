import sqlite3

db = "src/database/dmv_bus_stops.db"

conn = sqlite3.connect(db)
cur = conn.cursor()

print("Backing up current stop_routes...")

cur.execute("""
DROP TABLE IF EXISTS stop_routes_bad_key_backup
""")

cur.execute("""
CREATE TABLE stop_routes_bad_key_backup AS
SELECT *
FROM stop_routes
""")


print("Clearing stop_routes...")

cur.execute("""
DELETE FROM stop_routes
""")


print("Restoring route mappings with numeric route ids...")

cur.execute("""
INSERT INTO stop_routes(stop_id, route_id)
SELECT 
    srb.stop_id,
    r.id
FROM stop_routes_backup srb
JOIN routes r
    ON srb.route_id = r.route_id
""")


cur.execute("""
INSERT OR IGNORE INTO stop_routes(stop_id, route_id)
SELECT 
    srf.stop_id,
    r.id
FROM stop_routes_failed_rebuild_backup srf
JOIN routes r
    ON srf.route_id = r.route_id
""")


conn.commit()


count = cur.execute("""
SELECT COUNT(*)
FROM stop_routes
""").fetchone()[0]

print("New stop_routes count:", count)


print("\nSample repaired rows:")

for row in cur.execute("""
SELECT
    sr.stop_id,
    sr.route_id,
    r.route_id,
    r.route_name
FROM stop_routes sr
JOIN routes r
ON sr.route_id = r.id
LIMIT 10
"""):
    print(row)


conn.close()