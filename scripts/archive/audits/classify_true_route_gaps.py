import sqlite3

DB = "src/database/dmv_bus_stops.db"

conn = sqlite3.connect(DB)
conn.row_factory = sqlite3.Row
c = conn.cursor()

print("=== TRUE ROUTE GAPS BY MEMBER COUNT ===")

rows = c.execute("""
SELECT
    ps.member_count,
    COUNT(*) AS count
FROM physical_stops ps
WHERE NOT EXISTS (
    SELECT 1
    FROM physical_stop_members psm
    JOIN stop_routes sr
        ON psm.bus_stop_id = sr.stop_id
    WHERE psm.physical_stop_id = ps.id
)
GROUP BY ps.member_count
ORDER BY count DESC
""").fetchall()

for r in rows:
    print(dict(r))


print()
print("=== TRUE GAPS WITH TRANSIT EVIDENCE ===")

row = c.execute("""
SELECT
    COUNT(*)
FROM physical_stops ps
JOIN physical_stop_members psm
    ON ps.id = psm.physical_stop_id
JOIN stop_transit_evidence ste
    ON psm.bus_stop_id = ste.stop_id
WHERE NOT EXISTS (
    SELECT 1
    FROM physical_stop_members psm2
    JOIN stop_routes sr
        ON psm2.bus_stop_id = sr.stop_id
    WHERE psm2.physical_stop_id = ps.id
)
""").fetchone()

print(row[0])


print()
print("=== TRUE GAPS WITH GTFS STOP BUT ZERO ROUTES ===")

rows = c.execute("""
SELECT
    ps.id AS physical_stop_id,
    psm.bus_stop_id,
    ste.route_count,
    ste.source
FROM physical_stops ps

JOIN physical_stop_members psm
    ON ps.id = psm.physical_stop_id

JOIN stop_transit_evidence ste
    ON psm.bus_stop_id = ste.stop_id

WHERE NOT EXISTS (
    SELECT 1
    FROM physical_stop_members psm2
    JOIN stop_routes sr
        ON psm2.bus_stop_id = sr.stop_id
    WHERE psm2.physical_stop_id = ps.id
)

LIMIT 25
""").fetchall()

for r in rows:
    print(dict(r))