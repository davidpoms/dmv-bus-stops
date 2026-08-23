import sqlite3

conn = sqlite3.connect("src/database/dmv_bus_stops.db")

for row in conn.execute("PRAGMA table_info(stop_routes)"):
    print(row)

conn.close()