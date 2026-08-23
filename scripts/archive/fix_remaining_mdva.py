import sqlite3

DB = "src/database/dmv_bus_stops.db"

conn = sqlite3.connect(DB)
cur = conn.cursor()

cur.execute("""
UPDATE physical_stops
SET state='MD'
WHERE state='MD/VA'
AND longitude > -77.2;
""")

cur.execute("""
UPDATE physical_stops
SET state='VA'
WHERE state='MD/VA'
AND longitude <= -77.2;
""")

print("Updated:", cur.rowcount)

conn.commit()

cur.execute("""
SELECT state, COUNT(*)
FROM physical_stops
GROUP BY state
""")

for row in cur.fetchall():
    print(row)

conn.close()