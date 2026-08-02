import sqlite3

conn = sqlite3.connect("src/database/dmv_bus_stops.db")

for row in conn.execute("""
SELECT state, COUNT(*)
FROM stop_jurisdiction
GROUP BY state
"""):
    print(row)

conn.close()