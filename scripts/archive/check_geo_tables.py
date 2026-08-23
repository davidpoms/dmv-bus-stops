import sqlite3

conn = sqlite3.connect("src/database/dmv_bus_stops.db")
cur = conn.cursor()

for row in cur.execute("""
SELECT name
FROM sqlite_master
WHERE type='table'
AND (
    name LIKE '%summary%'
    OR name LIKE '%jurisdiction%'
)
ORDER BY name
"""):
    print(row[0])

conn.close()