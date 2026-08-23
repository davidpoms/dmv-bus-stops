import sqlite3

DB = "src/database/dmv_bus_stops.db"

conn = sqlite3.connect(DB)
conn.row_factory = sqlite3.Row
c = conn.cursor()


rows = c.execute("""
SELECT
    ste.stop_id,
    bs.external_stop_id,
    bs.stop_name,
    bs.latitude,
    bs.longitude,
    gm.gtfs_stop_id

FROM stop_transit_evidence ste

JOIN bus_stops bs
    ON bs.id = ste.stop_id

LEFT JOIN gtfs_stop_map gm
    ON gm.bus_stop_id = bs.id

WHERE ste.gtfs_bus_stop = 1
AND ste.route_count = 0

LIMIT 50
""").fetchall()


print("Zero-route GTFS evidence samples:")
print("==============================")

for r in rows:
    print(dict(r))


print("\nTotal:")
print(
    c.execute("""
    SELECT COUNT(*)
    FROM stop_transit_evidence
    WHERE gtfs_bus_stop=1
    AND route_count=0
    """).fetchone()[0]
)


conn.close()