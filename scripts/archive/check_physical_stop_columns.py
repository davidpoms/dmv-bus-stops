import sqlite3

conn = sqlite3.connect("src/database/dmv_bus_stops.db")
cur = conn.cursor()

print("physical_stops columns:")

for row in cur.execute("PRAGMA table_info(physical_stops)"):
    print(row[1])

conn.close()