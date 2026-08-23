import sqlite3

DB = "src/database/dmv_bus_stops.db"

conn = sqlite3.connect(DB)
cur = conn.cursor()

# Maryland
cur.execute("""
UPDATE stop_jurisdiction
SET state = 'MD'
WHERE state = 'MD/VA'
AND county IN (
    'Montgomery',
    'Prince George''s'
)
""")

# Virginia
cur.execute("""
UPDATE stop_jurisdiction
SET state = 'VA'
WHERE state = 'MD/VA'
AND county IN (
    'Arlington',
    'Alexandria',
    'Fairfax'
)
""")

conn.commit()

print("Updated rows:", cur.rowcount)

for row in cur.execute("""
SELECT state, COUNT(*)
FROM stop_jurisdiction
GROUP BY state
"""):
    print(row)

conn.close()