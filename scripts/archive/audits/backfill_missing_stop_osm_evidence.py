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

    p.id,

    1,

    CASE
        WHEN o.tags LIKE '%"bench": "yes"%'
        THEN 1
        ELSE 0
    END,

    CASE
        WHEN o.tags LIKE '%"shelter": "yes"%'
        THEN 1
        ELSE 0
    END,

    o.id,

    o.tags,

    DATE('now'),

    'osm_features table'

FROM physical_stops p

JOIN osm_features o

ON o.lat BETWEEN p.latitude - 0.0003
             AND p.latitude + 0.0003

AND o.lon BETWEEN p.longitude - 0.0003
             AND p.longitude + 0.0003

WHERE o.tags LIKE '%"highway": "bus_stop"%'

AND NOT EXISTS (

    SELECT 1
    FROM stop_osm_evidence existing
    WHERE existing.stop_id = p.id

)

GROUP BY p.id

""")

conn.commit()

print(
    "Backfilled rows:",
    cur.rowcount
)

conn.close()
