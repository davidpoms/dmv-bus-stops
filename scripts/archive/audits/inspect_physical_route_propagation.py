import sqlite3

DB = "src/database/dmv_bus_stops.db"

conn = sqlite3.connect(DB)
conn.row_factory = sqlite3.Row
cur = conn.cursor()

print("\n=== MEMBER -> ROUTE CHAIN SAMPLE ===")

rows = cur.execute("""
SELECT
    psm.physical_stop_id,
    psm.bus_stop_id,
    sr.route_id,
    r.route_id AS route_key,
    r.route_name
FROM physical_stop_members psm
LEFT JOIN stop_routes sr
    ON sr.stop_id = psm.bus_stop_id
LEFT JOIN routes r
    ON r.id = sr.route_id
LIMIT 20
""").fetchall()

for r in rows:
    print(dict(r))


print("\n=== PHYSICAL STOPS WHERE MEMBERS HAVE ROUTES ===")

rows = cur.execute("""
SELECT
    psm.physical_stop_id,
    COUNT(DISTINCT sr.route_id) AS routes
FROM physical_stop_members psm
JOIN stop_routes sr
    ON sr.stop_id = psm.bus_stop_id
GROUP BY psm.physical_stop_id
LIMIT 20
""").fetchall()

for r in rows:
    print(dict(r))


print("\n=== PHYSICAL STOPS WHERE MEMBERS HAVE ZERO ROUTES ===")

rows = cur.execute("""
SELECT
    psm.physical_stop_id,
    COUNT(psm.bus_stop_id) AS members
FROM physical_stop_members psm
LEFT JOIN stop_routes sr
    ON sr.stop_id = psm.bus_stop_id
WHERE sr.route_id IS NULL
GROUP BY psm.physical_stop_id
LIMIT 20
""").fetchall()

for r in rows:
    print(dict(r))