import sqlite3

conn = sqlite3.connect("src/database/dmv_bus_stops.db")
cur = conn.cursor()

print("Views:")

for row in cur.execute("""
SELECT name, sql
FROM sqlite_master
WHERE type='view'
AND (
    sql LIKE '%ward%'
    OR sql LIKE '%county%'
    OR sql LIKE '%municipality%'
    OR sql LIKE '%anc%'
)
"""):
    print("\nVIEW:", row[0])
    print(row[1][:500])

conn.close()