import sqlite3

DB = "src/database/dmv_bus_stops.db"

conn = sqlite3.connect(DB)
cur = conn.cursor()

cur.execute("""
INSERT INTO stop_osm_evidence
(
    stop_id,
    osm_bus_stop,
    osm_bench,
    osm_shelter,
    osm_feature_id,
    osm_tags,
    osm_snapshot_date,
    osm_source_file
)

SELECT
    ps.id,
    0,
    0,
    0,
    NULL,
    NULL,
    DATE('now'),
    'no OSM feature match'

FROM physical_stops ps

LEFT JOIN stop_osm_evidence ose
ON ps.id = ose.stop_id

WHERE ose.stop_id IS NULL;

""")

conn.commit()

print("Inserted negative evidence rows:", cur.rowcount)

conn.close()
