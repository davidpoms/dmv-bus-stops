import sqlite3

conn = sqlite3.connect("src/database/dmv_bus_stops.db")
c = conn.cursor()

print("=== ROUTE RELATED TABLES ===")
rows = c.execute("""
SELECT name
FROM sqlite_master
WHERE type='table'
AND name LIKE '%route%'
ORDER BY name
""").fetchall()

for r in rows:
    print(r[0])


print("\n=== TRIP RELATED TABLES ===")
rows = c.execute("""
SELECT name
FROM sqlite_master
WHERE type='table'
AND name LIKE '%trip%'
ORDER BY name
""").fetchall()

for r in rows:
    print(r[0])