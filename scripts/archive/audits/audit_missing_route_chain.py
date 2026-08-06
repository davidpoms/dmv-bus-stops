import sqlite3

DB = "src/database/dmv_bus_stops.db"

conn = sqlite3.connect(DB)
conn.row_factory = sqlite3.Row
cur = conn.cursor()

print("\n=== BUS STOPS WITH NO ROUTES ===")

cur.execute("""
SELECT
    COUNT(*) as total
FROM bus_stops b
LEFT JOIN stop_routes sr
    ON sr.stop_id = b.id
WHERE sr.stop_id IS NULL
""")

print(dict(cur.fetchone()))


print("\n=== PHYSICAL STOPS WITH MEMBERS BUT NO ROUTES ===")

cur.execute("""
SELECT
    psm.physical_stop_id,
    COUNT(psm.bus_stop_id) AS members,
    GROUP_CONCAT(psm.bus_stop_id) AS bus_stop_ids
FROM physical_stop_members psm
LEFT JOIN stop_routes sr
    ON sr.stop_id = psm.bus_stop_id
WHERE sr.stop_id IS NULL
GROUP BY psm.physical_stop_id
ORDER BY members DESC
LIMIT 50
""")

for row in cur.fetchall():
    print(dict(row))


print("\n=== SAMPLE PHYSICAL STOP 3765 CHAIN ===")

cur.execute("""
SELECT
    ps.id AS physical_stop_id,
    psm.bus_stop_id,
    b.external_stop_id,
    gsm.gtfs_stop_id,
    sr.route_id
FROM physical_stops ps
JOIN physical_stop_members psm
    ON psm.physical_stop_id = ps.id
JOIN bus_stops b
    ON b.id = psm.bus_stop_id
LEFT JOIN gtfs_stop_map gsm
    ON gsm.bus_stop_id = b.id
LEFT JOIN stop_routes sr
    ON sr.stop_id = b.id
WHERE ps.id = 3765
""")

for row in cur.fetchall():
    print(dict(row))


conn.close()