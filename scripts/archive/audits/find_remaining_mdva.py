import sqlite3

conn = sqlite3.connect("src/database/dmv_bus_stops.db")
cur = conn.cursor()

cur.execute("""
SELECT
    ps.id,
    ps.latitude,
    ps.longitude,
    sj.county,
    sj.municipality
FROM physical_stops ps
LEFT JOIN stop_jurisdiction sj
    ON ps.id = sj.stop_id
WHERE ps.state='MD/VA'
""")

for row in cur.fetchall():
    print(row)

conn.close()