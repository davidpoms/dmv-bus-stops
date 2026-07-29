import sqlite3

db = "src/database/dmv_bus_stops.db"

conn = sqlite3.connect(db)
cur = conn.cursor()

rows = cur.execute("""
SELECT name
FROM sqlite_master
WHERE type='table'
AND name LIKE '%osm%';
""").fetchall()

print("OSM-related tables:")
for row in rows:
    print(row[0])

conn.close()
