import sqlite3

conn = sqlite3.connect("src/database/dmv_bus_stops.db")

print("stop_routes sample:")
for row in conn.execute("""
SELECT *
FROM stop_routes
LIMIT 10
"""):
    print(row)

print("\nbus_stops sample:")
for row in conn.execute("""
SELECT *
FROM bus_stops
LIMIT 5
"""):
    print(row)

print("\nphysical members sample:")
for row in conn.execute("""
SELECT *
FROM physical_stop_members
LIMIT 5
"""):
    print(row)

conn.close()