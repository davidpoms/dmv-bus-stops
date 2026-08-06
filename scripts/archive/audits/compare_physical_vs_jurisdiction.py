import sqlite3

DB = "src/database/dmv_bus_stops.db"

conn = sqlite3.connect(DB)
cur = conn.cursor()

cur.execute("""
SELECT
    ps.id,
    ps.latitude,
    ps.longitude,
    ps.state AS physical_state,
    sj.state AS jurisdiction_state,
    sj.county,
    sj.municipality
FROM physical_stops ps
JOIN stop_jurisdiction sj
    ON ps.id = sj.stop_id
WHERE ps.state != sj.state
LIMIT 50
""")

rows = cur.fetchall()

print("Mismatches:", len(rows))

for r in rows:
    print(r)

conn.close()