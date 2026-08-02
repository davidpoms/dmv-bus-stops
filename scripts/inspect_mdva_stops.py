import sqlite3

conn = sqlite3.connect("src/database/dmv_bus_stops.db")
cur = conn.cursor()

cur.execute("""
SELECT
    ps.id,
    ps.latitude,
    ps.longitude,
    sj.county,
    sj.municipality,
    sj.state
FROM physical_stops ps
JOIN stop_jurisdiction sj
    ON ps.id = sj.stop_id
WHERE sj.state='MD/VA'
ORDER BY ps.id
""")

rows = cur.fetchall()

print("MD/VA count:", len(rows))

for row in rows:
    print(row)

conn.close()
