import sqlite3

DB = "src/database/dmv_bus_stops.db"

conn = sqlite3.connect(DB)
conn.row_factory = sqlite3.Row

query = """
SELECT
    ps.id,
    ps.latitude,
    ps.longitude,
    COUNT(w.id) AS wmata_records
FROM physical_stops ps
LEFT JOIN stop_wmata_evidence w
ON ps.id = w.physical_stop_id
WHERE NOT EXISTS (
    SELECT 1
    FROM physical_stop_members psm
    JOIN stop_routes sr
    ON sr.stop_id = psm.bus_stop_id
    WHERE psm.physical_stop_id = ps.id
)
GROUP BY ps.id
ORDER BY wmata_records DESC, ps.id
LIMIT 100;
"""

rows = conn.execute(query).fetchall()

print(f"Unverified physical stops found: {len(rows)}\n")

for row in rows:
    print(dict(row))

conn.close()