import sqlite3

DB="src/database/dmv_bus_stops.db"

conn=sqlite3.connect(DB)
conn.row_factory=sqlite3.Row
cur=conn.cursor()

print("\n=== SAMPLE PHYSICAL STOP WITH NO ROUTES ===")

cur.execute("""
SELECT
    ps.id physical_stop_id,
    psm.bus_stop_id,
    bs.external_stop_id,
    g.gtfs_stop_id
FROM physical_stops ps
JOIN physical_stop_members psm
    ON ps.id = psm.physical_stop_id
JOIN bus_stops bs
    ON bs.id = psm.bus_stop_id
LEFT JOIN gtfs_stop_map g
    ON g.bus_stop_id = bs.id
LEFT JOIN stop_routes sr
    ON sr.stop_id = bs.id
WHERE sr.id IS NULL
LIMIT 20
""")

for r in cur.fetchall():
    print(dict(r))


print("\n=== CHECK WHETHER MEMBER BUS STOPS HAVE ROUTES ===")

cur.execute("""
SELECT
    psm.physical_stop_id,
    psm.bus_stop_id,
    COUNT(sr.id) route_count
FROM physical_stop_members psm
LEFT JOIN stop_routes sr
    ON sr.stop_id = psm.bus_stop_id
WHERE psm.physical_stop_id IN (
    SELECT ps.id
    FROM physical_stops ps
    LEFT JOIN physical_stop_members psm2
        ON ps.id=psm2.physical_stop_id
    LEFT JOIN stop_routes sr2
        ON sr2.stop_id=psm2.bus_stop_id
    GROUP BY ps.id
    HAVING COUNT(sr2.id)=0
)
GROUP BY psm.physical_stop_id, psm.bus_stop_id
LIMIT 30
""")

for r in cur.fetchall():
    print(dict(r))