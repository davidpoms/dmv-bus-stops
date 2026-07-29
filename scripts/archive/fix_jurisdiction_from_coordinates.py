import sqlite3

db="src/database/dmv_bus_stops.db"

conn=sqlite3.connect(db)
cur=conn.cursor()

cur.execute("""
UPDATE physical_stops
SET jurisdiction =
CASE

WHEN state='DC'
THEN 'DC'

WHEN longitude < -77.12
THEN 'VA'

WHEN latitude < 38.85
AND longitude < -77.05
THEN 'VA'

ELSE 'MD'

END
""")

conn.commit()

print("Updated jurisdictions")

cur.execute("""
SELECT jurisdiction, COUNT(*)
FROM physical_stops
GROUP BY jurisdiction
""")

for row in cur.fetchall():
    print(row)

conn.close()
