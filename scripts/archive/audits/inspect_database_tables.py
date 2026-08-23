import sqlite3

DB = "src/database/dmv_bus_stops.db"

conn = sqlite3.connect(DB)
cur = conn.cursor()

print("\nTABLES:\n")

tables = cur.execute(
    """
    SELECT name
    FROM sqlite_master
    WHERE type='table'
    ORDER BY name
    """
).fetchall()

for t in tables:
    print("-", t[0])


print("\nVIEWS:\n")

views = cur.execute(
    """
    SELECT name
    FROM sqlite_master
    WHERE type='view'
    ORDER BY name
    """
).fetchall()

for v in views:
    print("-", v[0])


conn.close()