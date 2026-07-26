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
    gtfs_source
)

SELECT
    id,
    1,
    'physical_stops'
FROM physical_stops

""")

conn.commit()

print(
    "Transit evidence rows:",
    cur.rowcount
)

conn.close()
