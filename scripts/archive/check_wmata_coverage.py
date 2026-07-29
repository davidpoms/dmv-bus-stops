import sqlite3


DB="src/database/dmv_bus_stops.db"


conn=sqlite3.connect(DB)


total = conn.execute(
"""
SELECT COUNT(*)
FROM physical_stops
"""
).fetchone()[0]


matched = conn.execute(
"""
SELECT COUNT(DISTINCT physical_stop_id)
FROM stop_wmata_evidence
"""
).fetchone()[0]


missing = conn.execute(
"""
SELECT COUNT(*)
FROM physical_stops p

LEFT JOIN stop_wmata_evidence w
ON p.id=w.physical_stop_id

WHERE w.physical_stop_id IS NULL
"""
).fetchone()[0]


print(
    "Physical stops:",
    total
)

print(
    "WMATA matched:",
    matched
)

print(
    "Missing WMATA:",
    missing
)


conn.close()
