import sqlite3

DB="src/database/dmv_bus_stops.db"

conn=sqlite3.connect(DB)

rows=conn.execute(
"""
SELECT
    physical_stop_id,
    wmata_stop_id,
    match_distance_m,
    match_confidence
FROM stop_wmata_evidence
ORDER BY match_distance_m DESC
LIMIT 50;
"""
).fetchall()


for r in rows:
    print(r)

conn.close()
