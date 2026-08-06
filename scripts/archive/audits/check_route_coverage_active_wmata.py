import sqlite3

conn = sqlite3.connect(
    "src/database/dmv_bus_stops.db"
)

conn.row_factory = sqlite3.Row
cur = conn.cursor()


row = cur.execute(
"""
SELECT
    COUNT(*) total,
    SUM(
        CASE
            WHEN sr.stop_id IS NOT NULL
            THEN 1
            ELSE 0
        END
    ) with_routes
FROM active_wmata_evidence aw

JOIN physical_stops ps
    ON aw.physical_stop_id = ps.id

LEFT JOIN physical_stop_members psm
    ON ps.id = psm.physical_stop_id

LEFT JOIN bus_stops bs
    ON psm.bus_stop_id = bs.id

LEFT JOIN stop_routes sr
    ON bs.id = sr.stop_id
"""
).fetchone()


print(dict(row))