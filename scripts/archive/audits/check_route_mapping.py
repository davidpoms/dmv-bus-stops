import sqlite3

conn = sqlite3.connect("src/database/dmv_bus_stops.db")
c = conn.cursor()

rows = c.execute("""
SELECT id, route_id, route_name
FROM routes
WHERE route_id = 'D40'
""").fetchall()

print(rows)