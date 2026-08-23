import sqlite3

db="src/database/dmv_bus_stops.db"

conn=sqlite3.connect(db)
conn.row_factory=sqlite3.Row
cur=conn.cursor()


print("=== PHYSICAL STOPS WITHOUT ROUTES ===")

print(cur.execute("""
SELECT COUNT(DISTINCT ps.id)
FROM physical_stops ps
JOIN physical_stop_members psm
ON ps.id = psm.physical_stop_id
LEFT JOIN stop_routes sr
ON psm.bus_stop_id = sr.stop_id
WHERE sr.id IS NULL
""").fetchone()[0])


print("\n=== WITH GTFS MAP ===")

print(cur.execute("""
SELECT COUNT(DISTINCT ps.id)
FROM physical_stops ps
JOIN physical_stop_members psm
ON ps.id = psm.physical_stop_id
JOIN gtfs_stop_map gsm
ON psm.bus_stop_id = gsm.bus_stop_id
LEFT JOIN stop_routes sr
ON psm.bus_stop_id = sr.stop_id
WHERE sr.id IS NULL
""").fetchone()[0])


print("\n=== WITHOUT GTFS MAP ===")

print(cur.execute("""
SELECT COUNT(DISTINCT ps.id)
FROM physical_stops ps
JOIN physical_stop_members psm
ON ps.id = psm.physical_stop_id
LEFT JOIN gtfs_stop_map gsm
ON psm.bus_stop_id = gsm.bus_stop_id
LEFT JOIN stop_routes sr
ON psm.bus_stop_id = sr.stop_id
WHERE sr.id IS NULL
AND gsm.bus_stop_id IS NULL
""").fetchone()[0])


print("\n=== SAMPLE WITH GTFS BUT NO ROUTES ===")

for r in cur.execute("""
SELECT
ps.id AS physical_stop_id,
psm.bus_stop_id,
bs.external_stop_id,
gsm.gtfs_stop_id
FROM physical_stops ps
JOIN physical_stop_members psm
ON ps.id=psm.physical_stop_id
JOIN bus_stops bs
ON psm.bus_stop_id=bs.id
JOIN gtfs_stop_map gsm
ON psm.bus_stop_id=gsm.bus_stop_id
LEFT JOIN stop_routes sr
ON psm.bus_stop_id=sr.stop_id
WHERE sr.id IS NULL
LIMIT 20
"""):
    print(dict(r))


conn.close()