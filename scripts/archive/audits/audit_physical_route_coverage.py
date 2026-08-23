import sqlite3

DB = "src/database/dmv_bus_stops.db"

conn = sqlite3.connect(DB)
conn.row_factory = sqlite3.Row
c = conn.cursor()

print("=== PHYSICAL STOPS WITH ROUTES THROUGH MEMBERS ===")

rows = c.execute("""
SELECT
    COUNT(DISTINCT ps.id)
FROM physical_stops ps
JOIN physical_stop_members psm
    ON ps.id = psm.physical_stop_id
JOIN stop_routes sr
    ON psm.bus_stop_id = sr.stop_id
""").fetchone()

print(rows[0])

print()

print("=== PHYSICAL STOPS WITHOUT ROUTES THROUGH MEMBERS ===")

rows = c.execute("""
SELECT
    COUNT(*)
FROM physical_stops ps
WHERE NOT EXISTS (
    SELECT 1
    FROM physical_stop_members psm
    JOIN stop_routes sr
        ON psm.bus_stop_id = sr.stop_id
    WHERE psm.physical_stop_id = ps.id
)
""").fetchone()

print(rows[0])

print()

print("=== SAMPLE TRUE GAPS ===")

rows = c.execute("""
SELECT
    ps.id,
    ps.member_count
FROM physical_stops ps
WHERE NOT EXISTS (
    SELECT 1
    FROM physical_stop_members psm
    JOIN stop_routes sr
        ON psm.bus_stop_id = sr.stop_id
    WHERE psm.physical_stop_id = ps.id
)
LIMIT 20
""").fetchall()

for r in rows:
    print(dict(r))

conn.close()