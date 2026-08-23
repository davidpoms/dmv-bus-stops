import sqlite3

conn = sqlite3.connect("src/database/dmv_bus_stops.db")
c = conn.cursor()

print("=== TABLES ===")

tables = c.execute("""
SELECT name
FROM sqlite_master
WHERE type='table'
ORDER BY name
""").fetchall()

for t in tables:
    name = t[0].lower()
    if (
        "route" in name
        or "trip" in name
        or "time" in name
        or "gtfs" in name
        or "stop" in name
    ):
        print(t[0])

conn.close()