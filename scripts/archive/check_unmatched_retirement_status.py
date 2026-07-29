import sqlite3


DB="src/database/dmv_bus_stops.db"


conn=sqlite3.connect(DB)


rows = conn.execute("""
SELECT
    p.id,
    p.primary_name,
    p.latitude,
    p.longitude,
    r.wmata_stop_id,
    r.note
FROM physical_stops p

LEFT JOIN stop_wmata_evidence w
ON p.id = w.physical_stop_id

JOIN wmata_retired_evidence r
ON ABS(p.latitude-r.latitude) < 0.0005
AND ABS(p.longitude-r.longitude) < 0.0005

WHERE w.physical_stop_id IS NULL

LIMIT 50;
""").fetchall()


print("Unmatched stops with retirement evidence:", len(rows))


for r in rows:
    print()
    print(r)


conn.close()
