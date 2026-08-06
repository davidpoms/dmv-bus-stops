import sqlite3

DB = "src/database/dmv_bus_stops.db"

conn = sqlite3.connect(DB)
c = conn.cursor()


queries = {

"GTFS active":
"""
SELECT COUNT(*)
FROM stop_transit_evidence
WHERE gtfs_bus_stop=1
""",

"GTFS + opportunities":
"""
SELECT COUNT(*)
FROM stop_transit_evidence ste
JOIN improvement_opportunities io
ON ste.stop_id = io.physical_stop_id
WHERE ste.gtfs_bus_stop=1
""",

"GTFS + WMATA":
"""
SELECT COUNT(*)
FROM stop_transit_evidence ste
JOIN stop_wmata_evidence we
ON ste.stop_id = we.physical_stop_id
WHERE ste.gtfs_bus_stop=1
""",

"GTFS + jurisdiction":
"""
SELECT COUNT(*)
FROM stop_transit_evidence ste
JOIN stop_jurisdiction sj
ON ste.stop_id = sj.stop_id
WHERE ste.gtfs_bus_stop=1
""",

"GTFS + all dashboard joins":
"""
SELECT COUNT(DISTINCT ps.id)
FROM physical_stops ps

JOIN stop_transit_evidence ste
ON ps.id = ste.stop_id

JOIN improvement_opportunities io
ON ps.id = io.physical_stop_id

LEFT JOIN stop_wmata_evidence we
ON ps.id = we.physical_stop_id

LEFT JOIN stop_jurisdiction sj
ON ps.id = sj.stop_id

WHERE ste.gtfs_bus_stop=1
"""
}


for name, query in queries.items():
    print(name)
    print(c.execute(query).fetchone()[0])
    print()


conn.close()