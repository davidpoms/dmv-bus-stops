import sqlite3

conn = sqlite3.connect("src/database/dmv_bus_stops.db")

rows = conn.execute("""
SELECT name
FROM sqlite_master
WHERE type='view'
ORDER BY name
""").fetchall()

for row in rows:
    print(row[0])

conn.close()