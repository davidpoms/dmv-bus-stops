import sqlite3

DB = "src/database/dmv_bus_stops.db"

conn = sqlite3.connect(DB)
cur = conn.cursor()

cur.execute("""
DELETE FROM stop_transit_evidence
""")

cur.execute("""
INSERT INTO stop_transit_evidence
(
    stop_id,
    gtfs_bus_stop,
    route_count,
    source
)

SELECT
    pm.physical_stop_id,
    1,
    COUNT(DISTINCT sr.route_id),
    'GTFS stop_routes via physical mapping'

FROM physical_stop_members pm

JOIN stop_routes sr
    ON pm.bus_stop_id = sr.stop_id

GROUP BY pm.physical_stop_id

""")
conn.commit()

print(
    "Transit evidence rows:",
    cur.rowcount
)

conn.close()