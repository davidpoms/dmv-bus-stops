import sqlite3

conn = sqlite3.connect("src/database/dmv_bus_stops.db")
c = conn.cursor()

for row in c.execute("""
SELECT name
FROM sqlite_master
WHERE type='table'
AND name LIKE '%gtfs%'
"""):
    print(row[0])

conn.close()