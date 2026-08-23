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
    psm.physical_stop_id,
    1,
    COUNT(DISTINCT sr.route_id),
    'WMATA current GTFS via gtfs_stop_map'

FROM physical_stop_members psm

JOIN gtfs_stop_map gm
    ON gm.bus_stop_id = psm.bus_stop_id

JOIN stop_routes sr
    ON sr.stop_id = gm.bus_stop_id

GROUP BY psm.physical_stop_id

""")

conn.commit()

print(
    "Transit evidence rows:",
    cur.rowcount
)

print(
    "Stops with transit evidence:",
    cur.execute(
        "SELECT COUNT(*) FROM stop_transit_evidence"
    ).fetchone()[0]
)

conn.close()