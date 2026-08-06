import sqlite3

DB = "src/database/dmv_bus_stops.db"

conn = sqlite3.connect(DB)
conn.row_factory = sqlite3.Row
c = conn.cursor()

rows = c.execute("""
SELECT
    ps.id AS physical_stop_id,
    ps.member_count,
    COUNT(psm.bus_stop_id) AS members
FROM physical_stops ps
LEFT JOIN physical_stop_members psm
    ON ps.id = psm.physical_stop_id
LEFT JOIN stop_routes sr
    ON ps.id = sr.stop_id
WHERE sr.stop_id IS NULL
GROUP BY ps.id
LIMIT 20
""").fetchall()

print("Physical stops with no routes:")
print()

for r in rows:
    print(dict(r))

conn.close()